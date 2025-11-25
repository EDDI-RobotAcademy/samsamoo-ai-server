"""
XBRL Extraction Service Implementation

Parses XBRL files and extracts financial data using multiple parsing strategies:
1. ixbrlparse for iXBRL files
2. lxml/BeautifulSoup for standard XBRL
3. Built-in XML parsing for simple structures
"""
import os
import re
import zipfile
import tempfile
import logging
from datetime import date, datetime
from typing import Optional, Dict, Any, List, Tuple
from xml.etree import ElementTree as ET

from financial_statement.application.port.xbrl_extraction_service_port import XBRLExtractionServicePort
from financial_statement.domain.xbrl_document import (
    XBRLDocument, XBRLContext, XBRLFact, XBRLUnit,
    XBRLTaxonomy, ReportType
)

logger = logging.getLogger(__name__)


class XBRLParseError(Exception):
    """Custom exception for XBRL parsing errors"""
    pass


class XBRLExtractionService(XBRLExtractionServicePort):
    """
    Implementation of XBRL extraction service.
    
    Supports multiple XBRL formats:
    - Standard XBRL 2.1 XML files
    - Inline XBRL (iXBRL) HTML files
    - ZIP archives containing XBRL files
    
    Optimized for Korean DART (K-IFRS, K-GAAP) taxonomies.
    """
    
    # Common XBRL namespaces
    NAMESPACES = {
        'xbrli': 'http://www.xbrl.org/2003/instance',
        'link': 'http://www.xbrl.org/2003/linkbase',
        'xlink': 'http://www.w3.org/1999/xlink',
        'iso4217': 'http://www.xbrl.org/2003/iso4217',
        'ifrs-full': 'http://xbrl.ifrs.org/taxonomy/2023-03-23/ifrs-full',
        'kifrs': 'http://xbrl.fss.or.kr/taxonomy/kifrs',
        'dart': 'http://dart.fss.or.kr/taxonomy',
    }
    
    # K-IFRS to standardized field mappings
    # Based on official DART taxonomy from K-IFRS_Account_List.xlsx
    # Element IDs use underscore format (ifrs-full_Assets) in DART XBRL files
    KIFRS_BALANCE_SHEET_MAPPINGS = {
        # Assets - Official: ifrs-full_Assets (자산총계)
        'total_assets': [
            # Official DART element IDs (underscore format)
            'ifrs-full_Assets', 'dart_Assets',
            # Colon format variants (some parsers convert to this)
            'ifrs-full:Assets', 'dart:Assets',
            # Plain names
            'Assets', 'TotalAssets',
            # Korean labels from DART taxonomy
            '자산총계', '자산', '총자산', '자산 총계', '자산합계',
        ],
        'current_assets': [
            # Official: ifrs-full_CurrentAssets (유동자산)
            'ifrs-full_CurrentAssets', 'dart_CurrentAssets',
            'ifrs-full:CurrentAssets', 'dart:CurrentAssets',
            'CurrentAssets',
            '유동자산', '유동 자산', '유동자산합계',
        ],
        'non_current_assets': [
            # Official: ifrs-full_NoncurrentAssets (비유동자산)
            'ifrs-full_NoncurrentAssets', 'dart_NoncurrentAssets',
            'ifrs-full:NoncurrentAssets', 'dart:NoncurrentAssets',
            'NoncurrentAssets', 'NonCurrentAssets',
            '비유동자산', '비유동 자산', '비유동자산합계', '고정자산',
        ],
        'cash': [
            # Official: ifrs-full_CashAndCashEquivalents (현금및현금성자산)
            'ifrs-full_CashAndCashEquivalents', 'dart_CashAndCashEquivalents',
            'ifrs-full:CashAndCashEquivalents', 'dart:CashAndCashEquivalents',
            'CashAndCashEquivalents', 'Cash',
            '현금및현금성자산', '현금및예치금', '현금', '현금성자산',
        ],
        'inventory': [
            # Official: ifrs-full_Inventories (재고자산)
            'ifrs-full_Inventories', 'dart_Inventories',
            'ifrs-full:Inventories', 'dart:Inventories',
            'Inventories',
            '재고자산',
        ],
        'trade_receivables': [
            # Official: ifrs-full_TradeAndOtherCurrentReceivables (매출채권 및 기타유동채권)
            'ifrs-full_TradeAndOtherCurrentReceivables', 'dart_ShortTermTradeReceivable',
            'ifrs-full:TradeAndOtherCurrentReceivables', 'dart:ShortTermTradeReceivable',
            'TradeAndOtherCurrentReceivables', 'TradeReceivables',
            '매출채권 및 기타유동채권', '매출채권', '매출채권및기타채권',
        ],

        # Liabilities - Official: ifrs-full_Liabilities (부채총계)
        'total_liabilities': [
            'ifrs-full_Liabilities', 'dart_Liabilities',
            'ifrs-full:Liabilities', 'dart:Liabilities',
            'Liabilities', 'TotalLiabilities',
            '부채총계', '부채', '총부채', '부채 총계', '부채합계',
        ],
        'current_liabilities': [
            # Official: ifrs-full_CurrentLiabilities (유동부채)
            'ifrs-full_CurrentLiabilities', 'dart_CurrentLiabilities',
            'ifrs-full:CurrentLiabilities', 'dart:CurrentLiabilities',
            'CurrentLiabilities',
            '유동부채', '유동 부채', '유동부채합계',
        ],
        'non_current_liabilities': [
            # Official: ifrs-full_NoncurrentLiabilities (비유동부채)
            'ifrs-full_NoncurrentLiabilities', 'dart_NoncurrentLiabilities',
            'ifrs-full:NoncurrentLiabilities', 'dart:NoncurrentLiabilities',
            'NoncurrentLiabilities', 'NonCurrentLiabilities',
            '비유동부채', '비유동 부채', '비유동부채합계', '고정부채',
        ],
        'trade_payables': [
            # Official: ifrs-full_TradeAndOtherCurrentPayables (매입채무 및 기타유동채무)
            'ifrs-full_TradeAndOtherCurrentPayables', 'dart_TradePayables',
            'ifrs-full:TradeAndOtherCurrentPayables', 'dart:TradePayables',
            'TradeAndOtherCurrentPayables', 'TradePayables',
            '매입채무 및 기타유동채무', '매입채무', '매입채무및기타채무',
        ],

        # Equity - Official: ifrs-full_Equity (자본총계)
        'total_equity': [
            'ifrs-full_Equity', 'dart_Equity',
            'ifrs-full:Equity', 'dart:Equity',
            # Parent company equity
            'ifrs-full_EquityAttributableToOwnersOfParent',
            'ifrs-full:EquityAttributableToOwnersOfParent',
            'Equity', 'TotalEquity', 'StockholdersEquity',
            '자본총계', '자본', '총자본', '자본 총계', '자본합계',
            '자기자본', '순자산', '지배기업의 소유주에게 귀속되는 자본',
        ],
        'share_capital': [
            # Official: ifrs-full_IssuedCapital (자본금)
            'ifrs-full_IssuedCapital', 'dart_IssuedCapitalOfCommonStock',
            'ifrs-full:IssuedCapital', 'dart:IssuedCapital',
            'IssuedCapital',
            '자본금', '보통주자본금', '우선주자본금',
        ],
        'retained_earnings': [
            # Official: ifrs-full_RetainedEarnings (이익잉여금)
            'ifrs-full_RetainedEarnings', 'dart_RetainedEarnings',
            'ifrs-full:RetainedEarnings', 'dart:RetainedEarnings',
            'RetainedEarnings',
            '이익잉여금', '미처분이익잉여금',
        ],
    }
    
    # Income Statement mappings based on official DART taxonomy
    KIFRS_INCOME_STATEMENT_MAPPINGS = {
        'revenue': [
            # Official: ifrs-full_Revenue (수익(매출액))
            'ifrs-full_Revenue', 'dart_Revenue',
            'ifrs-full:Revenue', 'dart:Revenue',
            'Revenue', 'SalesRevenue', 'TotalRevenue',
            # Korean labels
            '수익(매출액)', '매출액', '수익', '영업수익',
            '매출', '총매출액', '영업 수익', '순매출액', '매출수익',
        ],
        'cost_of_sales': [
            # Official: ifrs-full_CostOfSales (매출원가)
            'ifrs-full_CostOfSales', 'dart_CostOfSales',
            'ifrs-full:CostOfSales', 'dart:CostOfSales',
            'CostOfSales',
            '매출원가', '영업비용',
        ],
        'gross_profit': [
            # Official: ifrs-full_GrossProfit (매출총이익)
            'ifrs-full_GrossProfit', 'dart_GrossProfit',
            'ifrs-full:GrossProfit', 'dart:GrossProfit',
            'GrossProfit',
            '매출총이익',
        ],
        'operating_income': [
            # Official: dart_OperatingIncomeLoss (영업이익(손실))
            'dart_OperatingIncomeLoss', 'ifrs-full_ProfitLossFromOperatingActivities',
            'dart:OperatingIncomeLoss', 'ifrs-full:ProfitLossFromOperatingActivities',
            'OperatingIncomeLoss', 'OperatingProfit', 'OperatingIncome',
            '영업이익(손실)', '영업이익', '영업 이익', '영업손익',
        ],
        'operating_expenses': [
            # Official: ifrs-full_SellingGeneralAndAdministrativeExpense
            'ifrs-full_SellingGeneralAndAdministrativeExpense',
            'ifrs-full:SellingGeneralAndAdministrativeExpense',
            'SellingGeneralAndAdministrativeExpense', 'OperatingExpenses',
            '판매비와관리비', '판관비',
        ],
        'interest_expense': [
            # Official: dart_InterestExpenseFinanceExpense (이자비용)
            'dart_InterestExpenseFinanceExpense', 'ifrs-full_InterestExpense',
            'dart:InterestExpenseFinanceExpense', 'ifrs-full:InterestExpense',
            'InterestExpense',
            '이자비용', '금융비용',
        ],
        'interest_income': [
            # Official: dart_InterestIncomeFinanceIncome (이자수익)
            'dart_InterestIncomeFinanceIncome', 'ifrs-full_InterestIncome',
            'dart:InterestIncomeFinanceIncome', 'ifrs-full:InterestIncome',
            'InterestIncome',
            '이자수익', '금융수익',
        ],
        'income_before_tax': [
            # Official: ifrs-full_ProfitLossBeforeTax (법인세비용차감전순이익(손실))
            'ifrs-full_ProfitLossBeforeTax', 'dart_ProfitLossBeforeTax',
            'ifrs-full:ProfitLossBeforeTax', 'dart:ProfitLossBeforeTax',
            'ProfitLossBeforeTax', 'ProfitBeforeTax',
            '법인세비용차감전순이익(손실)', '법인세비용차감전순이익', '세전이익',
        ],
        'income_tax_expense': [
            # Official: ifrs-full_IncomeTaxExpenseContinuingOperations (법인세비용)
            'ifrs-full_IncomeTaxExpenseContinuingOperations', 'ifrs-full_IncomeTaxExpense',
            'dart_IncomeTaxExpense',
            'ifrs-full:IncomeTaxExpenseContinuingOperations', 'ifrs-full:IncomeTaxExpense',
            'IncomeTaxExpense', 'IncomeTaxExpenseContinuingOperations',
            '법인세비용',
        ],
        'net_income': [
            # Official: ifrs-full_ProfitLoss (당기순이익(손실))
            'ifrs-full_ProfitLoss', 'dart_ProfitLoss',
            'ifrs-full:ProfitLoss', 'dart:ProfitLoss',
            # Parent company attributable profit
            'ifrs-full_ProfitLossAttributableToOwnersOfParent',
            'ifrs-full:ProfitLossAttributableToOwnersOfParent',
            'ProfitLossAttributableToOwnersOfParent',
            # Continuing operations
            'ifrs-full_ProfitLossFromContinuingOperations',
            'ifrs-full:ProfitLossFromContinuingOperations',
            'ProfitLossFromContinuingOperations',
            # Plain names
            'ProfitLoss', 'NetIncome', 'Profit', 'NetProfit',
            # Korean labels from DART taxonomy
            '당기순이익(손실)', '당기순이익', '순이익', '당기 순이익',
            '당기순손익', '계속영업이익(손실)',
            '지배기업의 소유주에게 귀속되는 당기순이익(손실)',
            '지배기업의 소유주에게 귀속되는 당기순이익',
            '지배기업소유주지분순이익', '지배기업의소유주에게귀속되는순이익',
            # Quarterly report variants
            '분기순이익', '분기순이익(손실)', '연결분기순이익',
            '연결당기순이익', '연결당기순이익(손실)',
            '당기순이익(지배)',
        ],
        'eps': [
            'ifrs-full:BasicEarningsLossPerShare', 'EarningsPerShare',
            '기본주당이익', 'dart:EarningsPerShare', '주당순이익'
        ],
    }
    
    # Cash Flow Statement mappings based on official DART taxonomy
    KIFRS_CASH_FLOW_MAPPINGS = {
        'operating_cash_flow': [
            # Official: ifrs-full_CashFlowsFromUsedInOperatingActivities (영업활동현금흐름)
            'ifrs-full_CashFlowsFromUsedInOperatingActivities',
            'ifrs-full:CashFlowsFromUsedInOperatingActivities',
            'CashFlowsFromUsedInOperatingActivities',
            '영업활동현금흐름', '영업활동 현금흐름', '영업활동으로 인한 현금흐름',
        ],
        'investing_cash_flow': [
            # Official: ifrs-full_CashFlowsFromUsedInInvestingActivities (투자활동현금흐름)
            'ifrs-full_CashFlowsFromUsedInInvestingActivities',
            'ifrs-full:CashFlowsFromUsedInInvestingActivities',
            'CashFlowsFromUsedInInvestingActivities',
            '투자활동현금흐름', '투자활동 현금흐름', '투자활동으로 인한 현금흐름',
        ],
        'financing_cash_flow': [
            # Official: ifrs-full_CashFlowsFromUsedInFinancingActivities (재무활동현금흐름)
            'ifrs-full_CashFlowsFromUsedInFinancingActivities',
            'ifrs-full:CashFlowsFromUsedInFinancingActivities',
            'CashFlowsFromUsedInFinancingActivities',
            '재무활동현금흐름', '재무활동 현금흐름', '재무활동으로 인한 현금흐름',
        ],
        'net_cash_flow': [
            # Official: ifrs-full_IncreaseDecreaseInCashAndCashEquivalents (현금및현금성자산의순증가(감소))
            'ifrs-full_IncreaseDecreaseInCashAndCashEquivalents',
            'ifrs-full:IncreaseDecreaseInCashAndCashEquivalents',
            'IncreaseDecreaseInCashAndCashEquivalents',
            # Before exchange rate effect
            'ifrs-full_IncreaseDecreaseInCashAndCashEquivalentsBeforeEffectOfExchangeRateChanges',
            '현금및현금성자산의순증가(감소)', '현금및현금성자산의 순증감',
            '환율변동효과 반영전 현금및현금성자산의 순증가(감소)',
        ],
        'capex': [
            # Official: ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities
            'ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities',
            'ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities',
            'PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities',
            # Legacy format
            'ifrs-full_PurchaseOfPropertyPlantAndEquipment',
            'ifrs-full:PurchaseOfPropertyPlantAndEquipment',
            # DART specific
            'dart_PurchaseOfOtherPropertyPlantAndEquipment',
            '유형자산의 취득', '유형자산의취득', '유형자산취득',
        ],
        'depreciation': [
            # Official: dart_DepreciationExpense (감가상각비)
            'dart_DepreciationExpense', 'dart:DepreciationExpense',
            # IFRS standard
            'ifrs-full_DepreciationAndAmortisationExpense',
            'ifrs-full:DepreciationAndAmortisationExpense',
            'DepreciationAndAmortisationExpense', 'DepreciationExpense',
            '감가상각비', '감가상각',
        ],
        'amortization': [
            # Official: dart_AmortisationExpense (무형자산상각비)
            'dart_AmortisationExpense', 'dart:AmortisationExpense',
            'ifrs-full_AmortisationExpense', 'ifrs-full:AmortisationExpense',
            'AmortisationExpense',
            '무형자산상각비', '상각비',
        ],
        'beginning_cash': [
            # Official: dart_CashAndCashEquivalentsAtBeginningOfPeriodCf (기초현금및현금성자산)
            'dart_CashAndCashEquivalentsAtBeginningOfPeriodCf',
            'dart:CashAndCashEquivalentsAtBeginningOfPeriodCf',
            '기초현금및현금성자산', '기초 현금및현금성자산',
        ],
        'ending_cash': [
            # Official: dart_CashAndCashEquivalentsAtEndOfPeriodCf (기말현금및현금성자산)
            'dart_CashAndCashEquivalentsAtEndOfPeriodCf',
            'dart:CashAndCashEquivalentsAtEndOfPeriodCf',
            '기말현금및현금성자산', '기말 현금및현금성자산',
        ],
    }
    
    def __init__(self):
        self._try_import_ixbrlparse()
    
    def _try_import_ixbrlparse(self):
        """Try to import ixbrlparse for iXBRL support"""
        try:
            import ixbrlparse
            self._ixbrlparse = ixbrlparse
            self._has_ixbrlparse = True
            logger.info("ixbrlparse available for iXBRL parsing")
        except ImportError:
            self._ixbrlparse = None
            self._has_ixbrlparse = False
            logger.warning("ixbrlparse not available - iXBRL support limited")
    
    def parse_xbrl_file(
        self,
        file_path: str,
        corp_code: str,
        corp_name: str,
        fiscal_year: int,
        report_type: ReportType
    ) -> XBRLDocument:
        """Parse a local XBRL file"""
        logger.info(f"Parsing XBRL file: {file_path}")
        
        if not os.path.exists(file_path):
            raise XBRLParseError(f"File not found: {file_path}")
        
        # Handle ZIP archives
        if file_path.endswith('.zip'):
            return self._parse_xbrl_zip(
                file_path, corp_code, corp_name, fiscal_year, report_type
            )
        
        # Read file content
        with open(file_path, 'rb') as f:
            content = f.read()
        
        return self.parse_xbrl_content(
            content, corp_code, corp_name, fiscal_year, report_type
        )
    
    def _parse_xbrl_zip(
        self,
        zip_path: str,
        corp_code: str,
        corp_name: str,
        fiscal_year: int,
        report_type: ReportType
    ) -> XBRLDocument:
        """Parse XBRL from a ZIP archive"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_dir)
            
            # Find XBRL file in extracted contents
            xbrl_file = None
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    if f.endswith(('.xml', '.xbrl', '.html', '.htm')):
                        # Prefer files with 'instance' in name
                        if 'instance' in f.lower() or xbrl_file is None:
                            xbrl_file = os.path.join(root, f)
            
            if not xbrl_file:
                raise XBRLParseError("No XBRL file found in ZIP archive")
            
            with open(xbrl_file, 'rb') as f:
                content = f.read()
            
            return self.parse_xbrl_content(
                content, corp_code, corp_name, fiscal_year, report_type
            )
    
    def parse_xbrl_content(
        self,
        content: bytes,
        corp_code: str,
        corp_name: str,
        fiscal_year: int,
        report_type: ReportType,
        taxonomy: XBRLTaxonomy = XBRLTaxonomy.KIFRS
    ) -> XBRLDocument:
        """Parse XBRL content from bytes"""
        logger.info(f"Parsing XBRL content for {corp_name} ({fiscal_year})")
        
        # Create document
        doc = XBRLDocument(
            corp_code=corp_code,
            corp_name=corp_name,
            fiscal_year=fiscal_year,
            report_type=report_type,
            taxonomy=taxonomy
        )
        
        # Try to decode content
        try:
            content_str = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                content_str = content.decode('euc-kr')
            except UnicodeDecodeError:
                content_str = content.decode('utf-8', errors='ignore')
        
        # Detect if iXBRL (HTML-based) or standard XBRL (XML-based)
        if self._is_ixbrl(content_str):
            self._parse_ixbrl(content_str, doc)
        else:
            self._parse_standard_xbrl(content_str, doc)
        
        logger.info(f"Parsed {len(doc.facts)} facts from XBRL content")
        return doc
    
    def _is_ixbrl(self, content: str) -> bool:
        """Detect if content is iXBRL (inline XBRL in HTML)"""
        content_lower = content.lower()
        return (
            '<html' in content_lower or
            '<!doctype html' in content_lower or
            '<ix:' in content_lower
        )
    
    def _parse_ixbrl(self, content: str, doc: XBRLDocument):
        """Parse inline XBRL using ixbrlparse or fallback"""
        if self._has_ixbrlparse:
            self._parse_ixbrl_with_library(content, doc)
        else:
            self._parse_ixbrl_manual(content, doc)
    
    def _parse_ixbrl_with_library(self, content: str, doc: XBRLDocument):
        """Parse iXBRL using ixbrlparse library"""
        try:
            from ixbrlparse import IXBRL
            
            # Parse with ixbrlparse
            ixbrl = IXBRL(content)
            
            # Extract contexts
            for ctx_id, ctx_data in ixbrl.contexts.items():
                context = XBRLContext(
                    context_id=ctx_id,
                    entity_identifier=doc.corp_code
                )
                
                # Parse period
                if hasattr(ctx_data, 'instant'):
                    context.instant = ctx_data.instant
                elif hasattr(ctx_data, 'startdate') and hasattr(ctx_data, 'enddate'):
                    context.period_start = ctx_data.startdate
                    context.period_end = ctx_data.enddate
                
                doc.add_context(context)
            
            # Extract units
            for unit_id, unit_data in ixbrl.units.items():
                unit = XBRLUnit(unit_id=unit_id, measure=str(unit_data))
                doc.add_unit(unit)
            
            # Extract numeric facts
            for item in ixbrl.numeric:
                fact = XBRLFact(
                    concept=item.name,
                    context_ref=item.context if hasattr(item, 'context') else '',
                    value=item.value,
                    unit_ref=item.unit if hasattr(item, 'unit') else None,
                    decimals=item.decimals if hasattr(item, 'decimals') else None
                )
                doc.add_fact(fact)
            
            # Extract non-numeric facts
            for item in ixbrl.nonnumeric:
                fact = XBRLFact(
                    concept=item.name,
                    context_ref=item.context if hasattr(item, 'context') else '',
                    value=item.value
                )
                doc.add_fact(fact)
            
            logger.info(f"Parsed iXBRL with library: {len(doc.facts)} facts")
            
        except Exception as e:
            logger.warning(f"ixbrlparse failed, falling back to manual: {e}")
            self._parse_ixbrl_manual(content, doc)
    
    def _parse_ixbrl_manual(self, content: str, doc: XBRLDocument):
        """Manual iXBRL parsing using BeautifulSoup with Korean support"""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(content, 'lxml')

            # Find all ix:nonFraction elements (numeric values)
            for elem in soup.find_all(re.compile(r'ix:nonfraction', re.I)):
                concept = elem.get('name', '')
                context_ref = elem.get('contextref', '')
                unit_ref = elem.get('unitref', '')
                decimals = elem.get('decimals', '')
                value = elem.get_text(strip=True)

                # Parse sign if present
                sign = elem.get('sign', '')
                if sign == '-' and value:
                    value = f"-{value}"

                # Also capture the Korean label if present in attributes or nearby
                label = elem.get('label', '') or elem.get('title', '')

                fact = XBRLFact(
                    concept=concept,
                    context_ref=context_ref,
                    value=self._parse_numeric_value(value),
                    unit_ref=unit_ref if unit_ref else None,
                    decimals=int(decimals) if decimals and decimals.lstrip('-').isdigit() else None
                )
                # Store Korean label for mapping
                if label:
                    fact.label = label
                doc.add_fact(fact)

            # Find all ix:nonNumeric elements (text values)
            for elem in soup.find_all(re.compile(r'ix:nonnumeric', re.I)):
                concept = elem.get('name', '')
                context_ref = elem.get('contextref', '')
                value = elem.get_text(strip=True)

                fact = XBRLFact(
                    concept=concept,
                    context_ref=context_ref,
                    value=value
                )
                doc.add_fact(fact)

            # Also look for Korean DART-specific elements (dart:xxx tags)
            for elem in soup.find_all(re.compile(r'^dart:', re.I)):
                tag_name = elem.name
                concept = f"dart:{tag_name.split(':')[-1] if ':' in str(tag_name) else tag_name}"
                context_ref = elem.get('contextref', '')
                value = elem.get_text(strip=True)

                numeric_val = self._parse_numeric_value(value)
                fact = XBRLFact(
                    concept=concept,
                    context_ref=context_ref,
                    value=numeric_val if numeric_val is not None else value
                )
                doc.add_fact(fact)

            # Try to parse table-based financial data (common in Korean DART files)
            if len(doc.facts) == 0:
                logger.info("No ix: elements found, trying table-based parsing")
                self._parse_table_based_data(soup, doc)

            # Extract Korean labels from label linkbase or inline labels
            self._extract_korean_labels(soup, doc)

            logger.info(f"Parsed iXBRL manually: {len(doc.facts)} facts")

        except ImportError:
            logger.error("BeautifulSoup not available for iXBRL parsing")
            raise XBRLParseError("BeautifulSoup required for iXBRL parsing")

    def _parse_table_based_data(self, soup, doc: 'XBRLDocument'):
        """
        Parse financial data from HTML tables when standard iXBRL elements are not found.
        Common in Korean DART filings that embed data in tables.
        """
        # Korean financial statement keywords to look for
        financial_keywords = {
            # Balance Sheet items
            '자산총계': 'total_assets',
            '자산': 'total_assets',
            '부채총계': 'total_liabilities',
            '부채': 'total_liabilities',
            '자본총계': 'total_equity',
            '자본': 'total_equity',
            '유동자산': 'current_assets',
            '비유동자산': 'non_current_assets',
            '유동부채': 'current_liabilities',
            '비유동부채': 'non_current_liabilities',
            '현금및현금성자산': 'cash',
            '재고자산': 'inventory',
            '매출채권': 'trade_receivables',
            '이익잉여금': 'retained_earnings',
            # Income Statement items
            '매출액': 'revenue',
            '수익': 'revenue',
            '영업수익': 'revenue',
            '매출원가': 'cost_of_sales',
            '매출총이익': 'gross_profit',
            '영업이익': 'operating_income',
            '당기순이익': 'net_income',
            '순이익': 'net_income',
            '법인세비용': 'income_tax_expense',
            '이자비용': 'interest_expense',
            # Cash Flow items
            '영업활동현금흐름': 'operating_cash_flow',
            '투자활동현금흐름': 'investing_cash_flow',
            '재무활동현금흐름': 'financing_cash_flow',
        }

        # Find all tables
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    # First cell is usually the label
                    label_text = cells[0].get_text(strip=True)

                    # Check if this label matches any financial keyword
                    for korean_key, english_key in financial_keywords.items():
                        if korean_key in label_text:
                            # Try to find numeric value in subsequent cells
                            for cell in cells[1:]:
                                cell_text = cell.get_text(strip=True)
                                # Remove commas and try to parse as number
                                numeric_val = self._parse_numeric_value(cell_text)
                                if numeric_val is not None and numeric_val != 0:
                                    fact = XBRLFact(
                                        concept=english_key,
                                        context_ref='current',
                                        value=numeric_val
                                    )
                                    fact.label = korean_key
                                    doc.add_fact(fact)
                                    logger.debug(f"Found {korean_key} = {numeric_val}")
                                    break
                            break

        # Also try to find data in spans/divs with specific patterns
        for span in soup.find_all(['span', 'div', 'p']):
            text = span.get_text(strip=True)
            for korean_key, english_key in financial_keywords.items():
                if korean_key in text:
                    # Look for a number nearby
                    parent = span.parent
                    if parent:
                        siblings = parent.find_all(['span', 'div', 'td'])
                        for sibling in siblings:
                            sibling_text = sibling.get_text(strip=True)
                            numeric_val = self._parse_numeric_value(sibling_text)
                            if numeric_val is not None and numeric_val != 0:
                                # Check if we already have this fact
                                existing = any(f.concept == english_key for f in doc.facts)
                                if not existing:
                                    fact = XBRLFact(
                                        concept=english_key,
                                        context_ref='current',
                                        value=numeric_val
                                    )
                                    fact.label = korean_key
                                    doc.add_fact(fact)
                                break
    

    def _extract_korean_labels(self, soup, doc: 'XBRLDocument'):
        """Extract Korean labels from various sources in the iXBRL document"""
        # Korean label mappings extracted from document
        korean_label_map = {}
        
        # 1. Look for label linkbase references
        for link in soup.find_all(re.compile(r'link:label', re.I)):
            label_text = link.get_text(strip=True)
            role = link.get('xlink:role', '') or link.get('role', '')
            label_id = link.get('xlink:label', '') or link.get('id', '')
            
            if label_text and any(ord(c) > 127 for c in label_text):  # Contains Korean
                korean_label_map[label_id] = label_text
        
        # 2. Look for hidden Korean text that maps to concepts
        for hidden in soup.find_all(['span', 'div'], style=re.compile(r'display:\s*none', re.I)):
            text = hidden.get_text(strip=True)
            if text and any(ord(c) > 127 for c in text):  # Contains Korean
                # Find adjacent ix:nonFraction element
                sibling = hidden.find_next_sibling(re.compile(r'ix:nonfraction', re.I))
                if sibling:
                    concept = sibling.get('name', '')
                    if concept:
                        korean_label_map[concept] = text
        
        # 3. Look for Korean text in table headers that might indicate concept meaning
        korean_concept_hints = {
            '자산총계': ['total_assets', 'assets'],
            '자산': ['total_assets', 'assets'],
            '부채총계': ['total_liabilities', 'liabilities'],
            '부채': ['total_liabilities', 'liabilities'],
            '자본총계': ['total_equity', 'equity'],
            '자본': ['total_equity', 'equity'],
            '유동자산': ['current_assets'],
            '비유동자산': ['non_current_assets'],
            '유동부채': ['current_liabilities'],
            '비유동부채': ['non_current_liabilities'],
            '현금및현금성자산': ['cash', 'cash_and_equivalents'],
            '매출액': ['revenue', 'sales'],
            '영업이익': ['operating_income'],
            '당기순이익': ['net_income'],
            '매출원가': ['cost_of_sales'],
            '판매비와관리비': ['operating_expenses'],
            '이자비용': ['interest_expense'],
            '법인세비용': ['income_tax_expense'],
            '영업활동현금흐름': ['operating_cash_flow'],
            '투자활동현금흐름': ['investing_cash_flow'],
            '재무활동현금흐름': ['financing_cash_flow'],
            '매출채권': ['trade_receivables'],
            '재고자산': ['inventory'],
            '이익잉여금': ['retained_earnings'],
        }
        
        # Update facts with Korean labels where found
        for fact in doc.facts:
            # Check if fact concept matches any Korean label
            for korean_text, concept_hints in korean_concept_hints.items():
                if korean_text in fact.concept or (fact.label and korean_text in fact.label):
                    # Store the Korean label for later mapping
                    fact.label = korean_text
                    break
            
            # Also check the label map
            if fact.concept in korean_label_map:
                fact.label = korean_label_map[fact.concept]

    def _parse_standard_xbrl(self, content: str, doc: XBRLDocument):
        """Parse standard XBRL XML"""
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            raise XBRLParseError(f"Invalid XML: {e}")
        
        # Build namespace map from root
        nsmap = {}
        for prefix, uri in root.attrib.items():
            if prefix.startswith('{'):
                continue
            if prefix.startswith('xmlns:'):
                nsmap[prefix[6:]] = uri
            elif prefix == 'xmlns':
                nsmap[''] = uri
        
        # Parse contexts
        for ctx_elem in root.iter():
            if ctx_elem.tag.endswith('}context') or ctx_elem.tag == 'context':
                self._parse_context_element(ctx_elem, doc)
        
        # Parse units
        for unit_elem in root.iter():
            if unit_elem.tag.endswith('}unit') or unit_elem.tag == 'unit':
                self._parse_unit_element(unit_elem, doc)
        
        # Parse facts (elements with contextRef attribute)
        for elem in root.iter():
            context_ref = elem.get('contextRef')
            if context_ref:
                self._parse_fact_element(elem, doc)
        
        logger.info(f"Parsed standard XBRL: {len(doc.facts)} facts")
    
    def _parse_context_element(self, elem: ET.Element, doc: XBRLDocument):
        """Parse a context element"""
        ctx_id = elem.get('id', '')
        if not ctx_id:
            return
        
        context = XBRLContext(
            context_id=ctx_id,
            entity_identifier=doc.corp_code
        )
        
        # Parse entity identifier
        for child in elem.iter():
            tag = child.tag.split('}')[-1].lower() if '}' in child.tag else child.tag.lower()
            
            if tag == 'identifier':
                context.entity_identifier = child.text or doc.corp_code
            elif tag == 'instant':
                context.instant = self._parse_date(child.text)
            elif tag == 'startdate':
                context.period_start = self._parse_date(child.text)
            elif tag == 'enddate':
                context.period_end = self._parse_date(child.text)
        
        doc.add_context(context)
    
    def _parse_unit_element(self, elem: ET.Element, doc: XBRLDocument):
        """Parse a unit element"""
        unit_id = elem.get('id', '')
        if not unit_id:
            return
        
        measure = ''
        for child in elem.iter():
            tag = child.tag.split('}')[-1].lower() if '}' in child.tag else child.tag.lower()
            if tag == 'measure':
                measure = child.text or ''
                break
        
        unit = XBRLUnit(unit_id=unit_id, measure=measure)
        doc.add_unit(unit)
    
    def _parse_fact_element(self, elem: ET.Element, doc: XBRLDocument):
        """Parse a fact element"""
        # Get concept name from tag
        tag = elem.tag
        if '}' in tag:
            ns, local_name = tag[1:].split('}')
            concept = f"{self._get_ns_prefix(ns)}:{local_name}"
        else:
            concept = tag
        
        context_ref = elem.get('contextRef', '')
        unit_ref = elem.get('unitRef')
        decimals = elem.get('decimals')
        
        # Parse value
        value = elem.text
        if value:
            value = value.strip()
            # Try to parse as number
            numeric_value = self._parse_numeric_value(value)
            if numeric_value is not None:
                value = numeric_value
        
        fact = XBRLFact(
            concept=concept,
            context_ref=context_ref,
            value=value,
            unit_ref=unit_ref,
            decimals=int(decimals) if decimals and decimals.lstrip('-').isdigit() else None,
            namespace=concept.split(':')[0] if ':' in concept else None,
            local_name=concept.split(':')[1] if ':' in concept else concept
        )
        doc.add_fact(fact)
    
    def _get_ns_prefix(self, uri: str) -> str:
        """Get namespace prefix from URI"""
        for prefix, ns_uri in self.NAMESPACES.items():
            if uri == ns_uri or uri.startswith(ns_uri):
                return prefix
        # Extract last part of URI as prefix
        return uri.split('/')[-1] or 'ns'
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            try:
                return datetime.strptime(date_str.strip()[:10], '%Y-%m-%d').date()
            except ValueError:
                return None
    
    def _parse_numeric_value(self, value_str: str) -> Optional[float]:
        """Parse string to numeric value"""
        if not value_str:
            return None
        try:
            # Remove commas and whitespace
            cleaned = re.sub(r'[,\s]', '', str(value_str))
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    def extract_financial_data(
        self,
        xbrl_doc: XBRLDocument
    ) -> Dict[str, Any]:
        """
        Extract normalized financial data from XBRL document.
        Maps XBRL concepts to standardized field names.
        """
        logger.info(f"Extracting financial data from {xbrl_doc.corp_name}")
        
        # Get all facts
        all_facts = xbrl_doc.facts
        
        # Build concept-to-value map for current period
        # Include both concept name and Korean labels for better matching
        fact_values = {}

        def normalize_korean(text: str) -> str:
            """Normalize Korean text by removing all whitespace variations"""
            if not text:
                return text
            # Remove regular spaces, full-width spaces, and other whitespace
            return text.replace(" ", "").replace("\u3000", "").replace("\t", "").replace("\n", "").strip()

        for fact in all_facts:
            if fact.numeric_value is not None:
                # Store by lowercase concept
                concept_key = fact.concept.lower()
                fact_values[concept_key] = fact.numeric_value

                # Also store by original concept (for Korean)
                fact_values[fact.concept] = fact.numeric_value

                # Store normalized version (no spaces)
                normalized_concept = normalize_korean(fact.concept)
                fact_values[normalized_concept] = fact.numeric_value
                fact_values[normalized_concept.lower()] = fact.numeric_value

                # Store by Korean label if available
                if hasattr(fact, 'label') and fact.label:
                    fact_values[fact.label] = fact.numeric_value
                    fact_values[fact.label.lower()] = fact.numeric_value
                    # Also store normalized label
                    normalized_label = normalize_korean(fact.label)
                    fact_values[normalized_label] = fact.numeric_value
                    fact_values[normalized_label.lower()] = fact.numeric_value

                # Store by local_name if available
                if fact.local_name:
                    fact_values[fact.local_name.lower()] = fact.numeric_value
                    fact_values[fact.local_name] = fact.numeric_value
                    normalized_local = normalize_korean(fact.local_name)
                    fact_values[normalized_local] = fact.numeric_value

        # Log available fact keys for debugging (sample of Korean keys)
        korean_keys = [k for k in fact_values.keys() if any(ord(c) > 127 for c in str(k))][:20]
        logger.info(f"Sample Korean fact keys: {korean_keys}")
        logger.info(f"Total fact_values entries: {len(fact_values)}")

        # Extract each section using mappings
        balance_sheet = self._map_concepts(fact_values, self.KIFRS_BALANCE_SHEET_MAPPINGS)
        income_statement = self._map_concepts(fact_values, self.KIFRS_INCOME_STATEMENT_MAPPINGS)
        cash_flow = self._map_concepts(fact_values, self.KIFRS_CASH_FLOW_MAPPINGS)
        
        # Validate and calculate missing totals
        balance_sheet = self._validate_balance_sheet(balance_sheet)
        income_statement = self._validate_income_statement(income_statement)
        
        result = {
            'balance_sheet': balance_sheet,
            'income_statement': income_statement,
            'cash_flow_statement': cash_flow
        }
        
        logger.info(f"Extracted: BS={len(balance_sheet)} items, IS={len(income_statement)} items, CF={len(cash_flow)} items")
        return result
    
    def _map_concepts(
        self,
        fact_values: Dict[str, float],
        mappings: Dict[str, List[str]]
    ) -> Dict[str, float]:
        """Map XBRL concepts to standardized field names with Korean support"""
        result = {}

        def normalize_text(text: str) -> str:
            """Normalize text by removing all whitespace variations"""
            if not text:
                return text
            return text.replace(" ", "").replace("\u3000", "").replace("\t", "").replace("\n", "").strip()

        for field_name, concepts in mappings.items():
            for concept in concepts:
                concept_lower = concept.lower()
                concept_normalized = normalize_text(concept)
                concept_normalized_lower = concept_normalized.lower()

                # 1. Try exact match first (case-insensitive for English, exact for Korean)
                if concept_lower in fact_values:
                    result[field_name] = fact_values[concept_lower]
                    logger.debug(f"Mapped {field_name} via lowercase: '{concept_lower}' = {result[field_name]}")
                    break
                # 2. Try exact match with original case (important for Korean)
                if concept in fact_values:
                    result[field_name] = fact_values[concept]
                    logger.debug(f"Mapped {field_name} via exact: '{concept}' = {result[field_name]}")
                    break
                # 3. Try with spaces removed (normalized)
                if concept_normalized in fact_values:
                    result[field_name] = fact_values[concept_normalized]
                    logger.debug(f"Mapped {field_name} via normalized: '{concept_normalized}' = {result[field_name]}")
                    break
                # 4. Try normalized lowercase
                if concept_normalized_lower in fact_values:
                    result[field_name] = fact_values[concept_normalized_lower]
                    logger.debug(f"Mapped {field_name} via normalized_lower: '{concept_normalized_lower}' = {result[field_name]}")
                    break

                # 5. Try partial/substring match
                for fact_concept, value in fact_values.items():
                    if not isinstance(fact_concept, str):
                        continue
                    fact_concept_lower = fact_concept.lower()
                    fact_normalized = normalize_text(fact_concept)
                    fact_normalized_lower = fact_normalized.lower()

                    # Check if the concept appears anywhere in the fact concept
                    if concept_lower in fact_concept_lower:
                        result[field_name] = value
                        logger.debug(f"Matched {field_name}: '{concept}' found in '{fact_concept}'")
                        break
                    if concept_normalized in fact_normalized:
                        result[field_name] = value
                        logger.debug(f"Matched {field_name}: '{concept_normalized}' found in '{fact_normalized}'")
                        break
                    if concept_normalized_lower in fact_normalized_lower:
                        result[field_name] = value
                        logger.debug(f"Matched {field_name}: '{concept_normalized_lower}' found in '{fact_normalized_lower}'")
                        break
                if field_name in result:
                    break

            # Log mapping result for important fields
            if field_name in result:
                logger.info(f"✓ Mapped '{field_name}' = {result[field_name]}")
            elif field_name in ['net_income', 'revenue', 'total_assets', 'total_equity', 'total_liabilities', 'operating_income']:
                logger.warning(f"✗ Could not map critical field '{field_name}'. Concepts tried: {concepts[:5]}...")

        return result
    
    def _validate_balance_sheet(self, bs: Dict[str, float]) -> Dict[str, float]:
        """Validate and calculate missing balance sheet items"""
        logger.info(f"Balance sheet before validation: {list(bs.keys())}")

        # Calculate total assets if missing
        if 'total_assets' not in bs or bs.get('total_assets', 0) == 0:
            current = bs.get('current_assets', 0)
            non_current = bs.get('non_current_assets', 0)
            if current or non_current:
                bs['total_assets'] = current + non_current
                logger.info(f"Calculated total_assets: {bs['total_assets']}")

        # Calculate total liabilities if missing
        if 'total_liabilities' not in bs or bs.get('total_liabilities', 0) == 0:
            current = bs.get('current_liabilities', 0)
            non_current = bs.get('non_current_liabilities', 0)
            if current or non_current:
                bs['total_liabilities'] = current + non_current
                logger.info(f"Calculated total_liabilities: {bs['total_liabilities']}")

        # Calculate total equity if missing (Assets = Liabilities + Equity)
        if 'total_equity' not in bs or bs.get('total_equity', 0) == 0:
            assets = bs.get('total_assets', 0)
            liabilities = bs.get('total_liabilities', 0)
            if assets and liabilities:
                bs['total_equity'] = assets - liabilities
                logger.info(f"Calculated total_equity: {bs['total_equity']}")

        # If we have total_assets but not breakdown, estimate current_assets
        # (common pattern: current = total - non_current)
        if 'current_assets' not in bs or bs.get('current_assets', 0) == 0:
            total = bs.get('total_assets', 0)
            non_current = bs.get('non_current_assets', 0)
            if total and non_current:
                bs['current_assets'] = total - non_current
                logger.info(f"Calculated current_assets: {bs['current_assets']}")

        # Same for liabilities
        if 'current_liabilities' not in bs or bs.get('current_liabilities', 0) == 0:
            total = bs.get('total_liabilities', 0)
            non_current = bs.get('non_current_liabilities', 0)
            if total and non_current:
                bs['current_liabilities'] = total - non_current
                logger.info(f"Calculated current_liabilities: {bs['current_liabilities']}")

        # Set inventory to 0 if not present (affects Quick Ratio calculation)
        if 'inventory' not in bs:
            bs['inventory'] = 0
            logger.debug("Inventory not found, defaulting to 0")

        # Log final state for debugging
        critical_fields = ['total_assets', 'total_liabilities', 'total_equity',
                          'current_assets', 'current_liabilities', 'inventory']
        for field in critical_fields:
            value = bs.get(field, 'MISSING')
            if value == 'MISSING' or value == 0:
                logger.warning(f"Balance sheet field '{field}' is {value}")

        logger.info(f"Balance sheet validation complete: {len(bs)} fields")
        return bs
    
    def _validate_income_statement(self, is_data: Dict[str, float]) -> Dict[str, float]:
        """Validate and calculate missing income statement items"""
        # Log current state for debugging
        logger.info(f"Income statement before validation: {list(is_data.keys())}")

        # Calculate gross profit if missing
        if 'gross_profit' not in is_data:
            revenue = is_data.get('revenue', 0)
            cost = is_data.get('cost_of_sales', 0)
            if revenue:
                is_data['gross_profit'] = revenue - cost
                logger.info(f"Calculated gross_profit: {is_data['gross_profit']}")

        # Calculate net_income if missing but we have income_before_tax and income_tax_expense
        if 'net_income' not in is_data or is_data.get('net_income', 0) == 0:
            income_before_tax = is_data.get('income_before_tax', 0)
            tax_expense = is_data.get('income_tax_expense', 0)

            if income_before_tax:
                calculated_net = income_before_tax - tax_expense
                is_data['net_income'] = calculated_net
                logger.info(f"Calculated net_income from income_before_tax - tax: {calculated_net}")
            else:
                # Try calculating from operating_income if no tax info
                operating_income = is_data.get('operating_income', 0)
                if operating_income and 'net_income' not in is_data:
                    # Use operating_income as fallback estimate (not ideal but better than 0)
                    logger.warning(f"net_income not found, using operating_income as fallback: {operating_income}")
                    is_data['net_income'] = operating_income

        # Log final state
        net_income = is_data.get('net_income', 0)
        operating_income = is_data.get('operating_income', 0)
        revenue = is_data.get('revenue', 0)
        logger.info(f"Income statement validation complete: revenue={revenue}, operating_income={operating_income}, net_income={net_income}")

        return is_data
    
    def get_available_concepts(
        self,
        xbrl_doc: XBRLDocument,
        filter_pattern: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of available XBRL concepts"""
        concepts = []
        seen = set()
        
        for fact in xbrl_doc.facts:
            if fact.concept in seen:
                continue
            seen.add(fact.concept)
            
            if filter_pattern:
                if filter_pattern.lower() not in fact.concept.lower():
                    continue
            
            concepts.append({
                'concept': fact.concept,
                'namespace': fact.namespace,
                'local_name': fact.local_name,
                'has_numeric_value': fact.numeric_value is not None,
                'sample_value': fact.value
            })
        
        return sorted(concepts, key=lambda x: x['concept'])
    
    def validate_xbrl_structure(
        self,
        xbrl_doc: XBRLDocument
    ) -> Dict[str, Any]:
        """Validate XBRL document structure"""
        warnings = []
        errors = []
        
        # Check contexts
        if not xbrl_doc.contexts:
            warnings.append("No contexts found in document")
        
        # Check facts
        if not xbrl_doc.facts:
            errors.append("No facts found in document")
        
        # Check required financial data
        bs = xbrl_doc.extract_balance_sheet()
        is_data = xbrl_doc.extract_income_statement()
        
        required_bs = ['total_assets', 'total_liabilities', 'total_equity']
        for field in required_bs:
            if field not in bs:
                warnings.append(f"Missing balance sheet item: {field}")
        
        required_is = ['revenue', 'net_income']
        for field in required_is:
            if field not in is_data:
                warnings.append(f"Missing income statement item: {field}")
        
        # Accounting equation check
        if all(k in bs for k in ['total_assets', 'total_liabilities', 'total_equity']):
            diff = abs(bs['total_assets'] - (bs['total_liabilities'] + bs['total_equity']))
            if diff > 1:  # Allow for rounding
                warnings.append(f"Accounting equation imbalance: Assets - (Liabilities + Equity) = {diff}")
        
        return {
            'valid': len(errors) == 0,
            'complete': len(warnings) == 0,
            'fact_count': len(xbrl_doc.facts),
            'context_count': len(xbrl_doc.contexts),
            'errors': errors,
            'warnings': warnings
        }
