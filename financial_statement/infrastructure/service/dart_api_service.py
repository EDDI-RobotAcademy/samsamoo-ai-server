"""
DART API Service Implementation

Integration with Korean DART (전자공시시스템) Open API
for fetching XBRL financial statements and corporation information.

API Documentation: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003
"""
import os
import io
import zipfile
import asyncio
import aiohttp
import logging
from datetime import date, datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

from financial_statement.application.port.xbrl_extraction_service_port import DARTXBRLServicePort
from financial_statement.domain.xbrl_document import XBRLDocument, ReportType, XBRLTaxonomy
from financial_statement.infrastructure.service.xbrl_extraction_service import XBRLExtractionService

logger = logging.getLogger(__name__)


class DARTAPIError(Exception):
    """Exception for DART API errors"""
    def __init__(self, message: str, status_code: str = None, error_code: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class DARTNotFoundError(DARTAPIError):
    """Exception when requested data is not found"""
    pass


class DARTRateLimitError(DARTAPIError):
    """Exception when rate limit is exceeded"""
    pass


class DARTAPIService(DARTXBRLServicePort):
    """
    Implementation of DART Open API integration.
    
    Requires DART API key from https://opendart.fss.or.kr/
    Set environment variable: DART_API_KEY
    
    Rate Limits:
    - 1,000 requests per day (basic plan)
    - 100 requests per minute
    """
    
    BASE_URL = "https://opendart.fss.or.kr/api"
    
    # DART API endpoints
    ENDPOINTS = {
        'corp_code': '/corpCode.xml',           # 고유번호 조회
        'company': '/company.json',              # 기업개황
        'fnltt_singl_acnt': '/fnlttSinglAcnt.json',  # 단일회사 전체 재무제표
        'fnltt_multi_acnt': '/fnlttMultiAcnt.json',  # 다중회사 재무제표
        'xbrl_taxonomy': '/xbrlTaxonomy.xml',    # XBRL 택사노미
        'list': '/list.json',                    # 공시검색
        'document': '/document.xml',             # 공시서류 원문
    }
    
    # Report type codes for DART API
    REPORT_TYPE_CODES = {
        ReportType.ANNUAL: '11011',        # 사업보고서
        ReportType.SEMI_ANNUAL: '11012',   # 반기보고서  
        ReportType.QUARTERLY: '11014',     # 분기보고서 (1분기)
    }
    
    # Financial statement type codes
    FS_TYPE_CODES = {
        'consolidated': 'CFS',   # 연결재무제표
        'separate': 'OFS',       # 개별재무제표
    }
    
    def __init__(self, api_key: str = None):
        """
        Initialize DART API service.
        
        Args:
            api_key: DART API key. If None, reads from DART_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('DART_API_KEY')
        if not self.api_key:
            logger.warning("DART_API_KEY not set - DART API calls will fail")
        
        self.xbrl_service = XBRLExtractionService()
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Cache for corporation list
        self._corp_list_cache: Optional[Dict[str, Dict]] = None
        self._corp_list_loaded: bool = False
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=60)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any],
        return_type: str = 'json'
    ) -> Any:
        """Make API request to DART"""
        if not self.api_key:
            raise DARTAPIError("DART_API_KEY not configured")
        
        params['crtfc_key'] = self.api_key
        url = f"{self.BASE_URL}{endpoint}"
        
        logger.debug(f"DART API request: {endpoint}")
        
        session = await self._get_session()
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 429:
                    raise DARTRateLimitError("Rate limit exceeded - max 100 requests/minute")
                
                if return_type == 'json':
                    data = await response.json()
                    self._check_api_response(data)
                    return data
                elif return_type == 'binary':
                    return await response.read()
                else:
                    return await response.text()
                    
        except aiohttp.ClientError as e:
            logger.error(f"DART API request failed: {e}")
            raise DARTAPIError(f"Network error: {e}")
    
    def _check_api_response(self, data: Dict):
        """Check API response for errors"""
        status = data.get('status', '000')
        
        if status == '000':
            return  # Success
        
        message = data.get('message', 'Unknown error')
        
        error_messages = {
            '010': 'Invalid API key',
            '011': 'No data available',
            '012': 'Parameter error',
            '013': 'Not registered IP',
            '020': 'Rate limit exceeded',
            '100': 'Required field missing',
            '800': 'System under maintenance',
            '900': 'Unknown data type requested',
        }
        
        error_msg = error_messages.get(status, message)
        
        if status == '011':
            raise DARTNotFoundError(error_msg, status_code=status)
        elif status == '020':
            raise DARTRateLimitError(error_msg, status_code=status)
        else:
            raise DARTAPIError(error_msg, status_code=status)
    
    async def _load_corp_list(self):
        """Load corporation code list from DART"""
        if self._corp_list_loaded:
            return
        
        logger.info("Loading DART corporation list...")
        
        try:
            # Download corp code XML file
            content = await self._make_request(
                self.ENDPOINTS['corp_code'],
                {},
                return_type='binary'
            )
            
            # Parse ZIP file containing XML
            self._corp_list_cache = {}
            
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                for name in zf.namelist():
                    if name.endswith('.xml'):
                        with zf.open(name) as f:
                            self._parse_corp_xml(f.read())
            
            self._corp_list_loaded = True
            logger.info(f"Loaded {len(self._corp_list_cache)} corporations")
            
        except Exception as e:
            logger.error(f"Failed to load corporation list: {e}")
            self._corp_list_cache = {}
    
    def _parse_corp_xml(self, content: bytes):
        """Parse corporation code XML"""
        from xml.etree import ElementTree as ET
        
        try:
            root = ET.fromstring(content)
            
            for corp in root.findall('.//list'):
                corp_code = corp.findtext('corp_code', '').strip()
                corp_name = corp.findtext('corp_name', '').strip()
                stock_code = corp.findtext('stock_code', '').strip()
                modify_date = corp.findtext('modify_date', '').strip()
                
                if corp_code:
                    self._corp_list_cache[corp_code] = {
                        'corp_code': corp_code,
                        'corp_name': corp_name,
                        'stock_code': stock_code,
                        'modify_date': modify_date,
                        'is_listed': bool(stock_code and stock_code.strip())
                    }
        except ET.ParseError as e:
            logger.warning(f"Failed to parse corp XML: {e}")
    
    async def search_corporation(
        self,
        corp_name: str
    ) -> List[Dict[str, str]]:
        """
        Search for corporations by name.
        
        Args:
            corp_name: Corporation name (partial match supported)
            
        Returns:
            List of matching corporations with corp_code and corp_name
        """
        await self._load_corp_list()
        
        if not self._corp_list_cache:
            return []
        
        results = []
        name_lower = corp_name.lower()
        
        for corp_data in self._corp_list_cache.values():
            if name_lower in corp_data['corp_name'].lower():
                results.append({
                    'corp_code': corp_data['corp_code'],
                    'corp_name': corp_data['corp_name'],
                    'stock_code': corp_data['stock_code'],
                    'is_listed': corp_data['is_listed']
                })
        
        # Sort by exact match first, then listed companies
        results.sort(key=lambda x: (
            x['corp_name'].lower() != name_lower,
            not x['is_listed'],
            x['corp_name']
        ))
        
        return results[:50]  # Limit results
    
    async def get_corp_info(
        self,
        corp_code: str
    ) -> Dict[str, Any]:
        """
        Get corporation basic information from DART.
        
        Args:
            corp_code: DART corporation code (8자리)
            
        Returns:
            Corporation information including name, stock code, industry, etc.
        """
        data = await self._make_request(
            self.ENDPOINTS['company'],
            {'corp_code': corp_code}
        )
        
        return {
            'corp_code': data.get('corp_code'),
            'corp_name': data.get('corp_name'),
            'corp_name_eng': data.get('corp_name_eng'),
            'stock_code': data.get('stock_code'),
            'ceo_name': data.get('ceo_nm'),
            'corporation_type': data.get('corp_cls'),  # Y: 유가, K: 코스닥, N: 코넥스, E: 기타
            'business_registration_number': data.get('bizr_no'),
            'address': data.get('adres'),
            'homepage': data.get('hm_url'),
            'phone': data.get('phn_no'),
            'fax': data.get('fax_no'),
            'industry_code': data.get('induty_code'),
            'establishment_date': data.get('est_dt'),
            'fiscal_month': data.get('acc_mt'),  # 결산월
        }
    
    async def download_xbrl(
        self,
        corp_code: str,
        fiscal_year: int,
        report_type: ReportType,
        consolidated: bool = True
    ) -> bytes:
        """
        Download XBRL financial statement from DART API.
        
        Uses the single company financial statement API which returns
        XBRL-format data that we can parse.
        
        Args:
            corp_code: DART corporation code (8자리)
            fiscal_year: Fiscal year (e.g., 2024)
            report_type: Annual, semi-annual, or quarterly
            consolidated: True for consolidated (연결), False for separate (개별)
            
        Returns:
            XBRL file content as bytes
        """
        reprt_code = self.REPORT_TYPE_CODES.get(report_type, '11011')
        fs_div = self.FS_TYPE_CODES['consolidated' if consolidated else 'separate']
        
        params = {
            'corp_code': corp_code,
            'bsns_year': str(fiscal_year),
            'reprt_code': reprt_code,
            'fs_div': fs_div,
        }
        
        logger.info(f"Downloading XBRL for {corp_code}, year={fiscal_year}, type={report_type.value}")
        
        # Use the single company full financial statement API
        data = await self._make_request(
            self.ENDPOINTS['fnltt_singl_acnt'],
            params
        )
        
        # The API returns JSON with financial data directly
        # We'll convert this to our internal format
        return self._convert_dart_response_to_xbrl(data, corp_code, fiscal_year)
    
    def _convert_dart_response_to_xbrl(
        self,
        data: Dict[str, Any],
        corp_code: str,
        fiscal_year: int
    ) -> bytes:
        """
        Convert DART JSON response to XBRL-like format.
        
        The DART API returns financial data in JSON format.
        We create a minimal XBRL-like XML structure for parsing.
        """
        import json
        
        # Store as JSON bytes that we'll parse differently
        result = {
            'source': 'dart_api',
            'corp_code': corp_code,
            'fiscal_year': fiscal_year,
            'data': data
        }
        
        return json.dumps(result, ensure_ascii=False).encode('utf-8')
    
    async def get_financial_statements(
        self,
        corp_code: str,
        fiscal_year: int,
        report_type: ReportType = ReportType.ANNUAL
    ) -> XBRLDocument:
        """
        Download and parse XBRL financial statements in one operation.
        
        Args:
            corp_code: DART corporation code
            fiscal_year: Fiscal year
            report_type: Report type
            
        Returns:
            Parsed XBRLDocument
        """
        # Get corporation info first
        corp_info = await self.get_corp_info(corp_code)
        corp_name = corp_info.get('corp_name', 'Unknown')
        
        # Get financial data from DART API
        fs_div = 'CFS'  # Consolidated by default
        reprt_code = self.REPORT_TYPE_CODES.get(report_type, '11011')
        
        params = {
            'corp_code': corp_code,
            'bsns_year': str(fiscal_year),
            'reprt_code': reprt_code,
            'fs_div': fs_div,
        }
        
        data = await self._make_request(
            self.ENDPOINTS['fnltt_singl_acnt'],
            params
        )
        
        # Create XBRL document from DART response
        doc = XBRLDocument(
            corp_code=corp_code,
            corp_name=corp_name,
            fiscal_year=fiscal_year,
            report_type=report_type,
            taxonomy=XBRLTaxonomy.KIFRS
        )
        
        # Parse DART financial statement list
        fs_list = data.get('list', [])
        
        for item in fs_list:
            # Create fact from each line item
            account_nm = item.get('account_nm', '')  # 계정명
            thstrm_amount = item.get('thstrm_amount', '')  # 당기금액
            frmtrm_amount = item.get('frmtrm_amount', '')  # 전기금액
            sj_div = item.get('sj_div', '')  # 재무제표구분 (BS, IS, CF)
            
            # Parse current period amount
            if thstrm_amount:
                value = self._parse_dart_amount(thstrm_amount)
                if value is not None:
                    from financial_statement.domain.xbrl_document import XBRLFact
                    fact = XBRLFact(
                        concept=f"dart:{account_nm}",
                        context_ref=f"current_{fiscal_year}",
                        value=value,
                        unit_ref='KRW'
                    )
                    doc.add_fact(fact)
        
        # Set period end date
        doc.period_end_date = date(fiscal_year, 12, 31)
        
        logger.info(f"Created XBRLDocument with {len(doc.facts)} facts from DART API")
        return doc
    
    def _parse_dart_amount(self, amount_str: str) -> Optional[float]:
        """Parse DART amount string to float"""
        if not amount_str or amount_str == '-':
            return None
        try:
            # Remove commas and parse
            cleaned = amount_str.replace(',', '').strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    async def list_available_reports(
        self,
        corp_code: str,
        begin_year: int,
        end_year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List available financial reports for a corporation.
        
        Uses DART disclosure search API to find available reports.
        
        Args:
            corp_code: DART corporation code
            begin_year: Start year
            end_year: End year (defaults to current year)
            
        Returns:
            List of available reports with dates and types
        """
        if end_year is None:
            end_year = datetime.now().year
        
        params = {
            'corp_code': corp_code,
            'bgn_de': f'{begin_year}0101',
            'end_de': f'{end_year}1231',
            'pblntf_ty': 'A',  # 정기공시
            'page_count': 100,
        }
        
        data = await self._make_request(
            self.ENDPOINTS['list'],
            params
        )
        
        reports = []
        for item in data.get('list', []):
            report_nm = item.get('report_nm', '')
            
            # Filter for financial statement reports
            if any(term in report_nm for term in ['사업보고서', '반기보고서', '분기보고서']):
                reports.append({
                    'rcept_no': item.get('rcept_no'),  # 접수번호
                    'corp_name': item.get('corp_name'),
                    'report_name': report_nm,
                    'rcept_dt': item.get('rcept_dt'),  # 접수일자
                    'flr_nm': item.get('flr_nm'),  # 공시제출인명
                })
        
        return reports
    
    async def get_financial_ratios_direct(
        self,
        corp_code: str,
        fiscal_year: int,
        report_type: ReportType = ReportType.ANNUAL
    ) -> Dict[str, Any]:
        """
        Get financial data directly from DART API and extract key ratios.
        
        This is a convenience method that extracts and calculates ratios
        without full XBRL parsing.
        
        Returns:
            Dictionary with financial data and calculated ratios
        """
        doc = await self.get_financial_statements(corp_code, fiscal_year, report_type)
        
        # Extract normalized data
        financial_data = self.xbrl_service.extract_financial_data(doc)
        
        return {
            'corp_code': corp_code,
            'corp_name': doc.corp_name,
            'fiscal_year': fiscal_year,
            'report_type': report_type.value,
            'financial_data': financial_data,
            'fact_count': len(doc.facts),
            'source': 'dart_api'
        }


# Synchronous wrapper for non-async contexts
class DARTAPIServiceSync:
    """Synchronous wrapper for DARTAPIService"""
    
    def __init__(self, api_key: str = None):
        self._async_service = DARTAPIService(api_key)
    
    def _run_async(self, coro):
        """Run async coroutine in sync context"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    def search_corporation(self, corp_name: str) -> List[Dict[str, str]]:
        return self._run_async(self._async_service.search_corporation(corp_name))
    
    def get_corp_info(self, corp_code: str) -> Dict[str, Any]:
        return self._run_async(self._async_service.get_corp_info(corp_code))
    
    def get_financial_statements(
        self,
        corp_code: str,
        fiscal_year: int,
        report_type: ReportType = ReportType.ANNUAL
    ) -> XBRLDocument:
        return self._run_async(
            self._async_service.get_financial_statements(corp_code, fiscal_year, report_type)
        )
    
    def get_financial_ratios_direct(
        self,
        corp_code: str,
        fiscal_year: int,
        report_type: ReportType = ReportType.ANNUAL
    ) -> Dict[str, Any]:
        return self._run_async(
            self._async_service.get_financial_ratios_direct(corp_code, fiscal_year, report_type)
        )
