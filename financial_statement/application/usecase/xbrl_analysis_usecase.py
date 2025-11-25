"""
XBRL Analysis Use Case

Orchestrates the complete XBRL-based financial analysis workflow:
1. Fetch XBRL data from DART API
2. Parse and extract financial information
3. Calculate financial ratios
4. Generate LLM-powered corporate analysis
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from financial_statement.domain.xbrl_document import XBRLDocument, ReportType
from financial_statement.domain.financial_ratio import FinancialRatio
from financial_statement.infrastructure.service.dart_api_service import DARTAPIService, DARTNotFoundError
from financial_statement.infrastructure.service.xbrl_extraction_service import XBRLExtractionService
from financial_statement.infrastructure.service.ratio_calculation_service import RatioCalculationService
from financial_statement.infrastructure.service.corporate_analysis_service import CorporateAnalysisService

logger = logging.getLogger(__name__)


class XBRLAnalysisError(Exception):
    """Exception for XBRL analysis errors"""
    pass


class XBRLAnalysisUseCase:
    """
    Use case for XBRL-based corporate financial analysis.
    
    Provides a complete workflow from data acquisition to analysis:
    1. Search and retrieve corporation information
    2. Download and parse XBRL financial statements
    3. Extract and normalize financial data
    4. Calculate financial ratios
    5. Generate LLM-powered corporate analysis
    """
    
    def __init__(
        self,
        dart_service: DARTAPIService = None,
        xbrl_service: XBRLExtractionService = None,
        calculation_service: RatioCalculationService = None,
        analysis_service: CorporateAnalysisService = None
    ):
        """
        Initialize use case with required services.
        
        Args:
            dart_service: DART API service for fetching XBRL data
            xbrl_service: XBRL extraction service for parsing
            calculation_service: Ratio calculation service
            analysis_service: Corporate analysis service with LLM
        """
        self.dart_service = dart_service or DARTAPIService()
        self.xbrl_service = xbrl_service or XBRLExtractionService()
        self.calculation_service = calculation_service or RatioCalculationService()
        self.analysis_service = analysis_service or CorporateAnalysisService()
    
    async def search_corporation(self, corp_name: str) -> List[Dict[str, str]]:
        """
        Search for corporations by name.
        
        Args:
            corp_name: Corporation name (partial match supported)
            
        Returns:
            List of matching corporations with corp_code, corp_name, stock_code
        """
        logger.info(f"Searching for corporation: {corp_name}")
        return await self.dart_service.search_corporation(corp_name)
    
    async def get_corporation_info(self, corp_code: str) -> Dict[str, Any]:
        """
        Get detailed corporation information.
        
        Args:
            corp_code: DART corporation code (8자리)
            
        Returns:
            Corporation information including name, industry, etc.
        """
        logger.info(f"Getting corporation info for: {corp_code}")
        return await self.dart_service.get_corp_info(corp_code)
    
    async def analyze_corporation(
        self,
        corp_code: str,
        fiscal_year: int,
        report_type: ReportType = ReportType.ANNUAL,
        industry: str = 'default'
    ) -> Dict[str, Any]:
        """
        Complete corporate analysis workflow.
        
        This is the main entry point that:
        1. Fetches XBRL data from DART
        2. Parses and extracts financial information
        3. Calculates financial ratios
        4. Generates comprehensive LLM analysis
        
        Args:
            corp_code: DART corporation code
            fiscal_year: Fiscal year to analyze
            report_type: Type of report (annual, semi-annual, quarterly)
            industry: Industry category for benchmark comparison
            
        Returns:
            Complete analysis result with financial data, ratios, and LLM analysis
        """
        logger.info(f"Starting corporate analysis for {corp_code}, year={fiscal_year}")
        
        try:
            # Step 1: Get corporation info
            corp_info = await self.dart_service.get_corp_info(corp_code)
            corp_name = corp_info.get('corp_name', 'Unknown')
            logger.info(f"Analyzing: {corp_name}")
            
            # Step 2: Fetch XBRL financial statements
            xbrl_doc = await self.dart_service.get_financial_statements(
                corp_code, fiscal_year, report_type
            )
            logger.info(f"Fetched XBRL document with {len(xbrl_doc.facts)} facts")
            
            # Step 3: Extract normalized financial data
            financial_data = self.xbrl_service.extract_financial_data(xbrl_doc)
            logger.info(f"Extracted financial data: BS={len(financial_data.get('balance_sheet', {}))} items")
            
            # Step 4: Calculate financial ratios
            ratios = self.calculation_service.calculate_all_ratios(
                financial_data, 
                statement_id=0  # Using 0 as placeholder since not persisting
            )
            logger.info(f"Calculated {len(ratios)} financial ratios")
            
            # Step 5: Generate LLM analysis
            analysis = await self.analysis_service.generate_comprehensive_analysis(
                corp_name=corp_name,
                financial_data=financial_data,
                ratios=ratios,
                fiscal_year=fiscal_year,
                industry=industry
            )
            logger.info("Generated comprehensive LLM analysis")
            
            # Compile results
            result = {
                'status': 'success',
                'corp_code': corp_code,
                'corp_name': corp_name,
                'corp_info': corp_info,
                'fiscal_year': fiscal_year,
                'report_type': report_type.value,
                'financial_data': financial_data,
                'ratios': self._serialize_ratios(ratios),
                'analysis': analysis,
                'metadata': {
                    'fact_count': len(xbrl_doc.facts),
                    'taxonomy': xbrl_doc.taxonomy.value,
                    'analyzed_at': datetime.utcnow().isoformat(),
                    'source': 'dart_xbrl'
                }
            }
            
            return result
            
        except DARTNotFoundError as e:
            logger.warning(f"No XBRL data found: {e}")
            return {
                'status': 'not_found',
                'corp_code': corp_code,
                'fiscal_year': fiscal_year,
                'error': str(e),
                'message': f'{fiscal_year}년 {report_type.value} 재무제표를 찾을 수 없습니다.'
            }
            
        except Exception as e:
            logger.error(f"Corporate analysis failed: {e}")
            raise XBRLAnalysisError(f"Analysis failed: {e}")
    
    async def analyze_corporation_quick(
        self,
        corp_code: str,
        fiscal_year: int,
        report_type: ReportType = ReportType.ANNUAL
    ) -> Dict[str, Any]:
        """
        Quick corporate analysis without full LLM analysis.
        
        Returns financial data and ratios only, without LLM-powered insights.
        Faster and doesn't require LLM API key.
        
        Args:
            corp_code: DART corporation code
            fiscal_year: Fiscal year to analyze
            report_type: Type of report
            
        Returns:
            Financial data and calculated ratios
        """
        logger.info(f"Starting quick analysis for {corp_code}, year={fiscal_year}")
        
        try:
            # Get corporation info
            corp_info = await self.dart_service.get_corp_info(corp_code)
            corp_name = corp_info.get('corp_name', 'Unknown')
            
            # Fetch XBRL financial statements
            xbrl_doc = await self.dart_service.get_financial_statements(
                corp_code, fiscal_year, report_type
            )
            
            # Extract normalized financial data
            financial_data = self.xbrl_service.extract_financial_data(xbrl_doc)
            
            # Calculate financial ratios
            ratios = self.calculation_service.calculate_all_ratios(
                financial_data, 
                statement_id=0
            )
            
            return {
                'status': 'success',
                'corp_code': corp_code,
                'corp_name': corp_name,
                'fiscal_year': fiscal_year,
                'report_type': report_type.value,
                'financial_data': financial_data,
                'ratios': self._serialize_ratios(ratios),
                'metadata': {
                    'fact_count': len(xbrl_doc.facts),
                    'analyzed_at': datetime.utcnow().isoformat(),
                    'source': 'dart_xbrl',
                    'analysis_type': 'quick'
                }
            }
            
        except DARTNotFoundError as e:
            return {
                'status': 'not_found',
                'corp_code': corp_code,
                'fiscal_year': fiscal_year,
                'error': str(e)
            }
            
        except Exception as e:
            logger.error(f"Quick analysis failed: {e}")
            raise XBRLAnalysisError(f"Quick analysis failed: {e}")
    
    async def compare_corporations(
        self,
        corp_codes: List[str],
        fiscal_year: int,
        report_type: ReportType = ReportType.ANNUAL
    ) -> Dict[str, Any]:
        """
        Compare multiple corporations' financial metrics.
        
        Args:
            corp_codes: List of DART corporation codes
            fiscal_year: Fiscal year to compare
            report_type: Type of report
            
        Returns:
            Comparison data for all corporations
        """
        logger.info(f"Comparing {len(corp_codes)} corporations for year {fiscal_year}")
        
        results = []
        for corp_code in corp_codes[:10]:  # Limit to 10 corporations
            try:
                result = await self.analyze_corporation_quick(
                    corp_code, fiscal_year, report_type
                )
                if result['status'] == 'success':
                    results.append({
                        'corp_code': corp_code,
                        'corp_name': result['corp_name'],
                        'ratios': result['ratios'],
                        'key_metrics': self._extract_key_metrics(result['financial_data'])
                    })
            except Exception as e:
                logger.warning(f"Failed to analyze {corp_code}: {e}")
                results.append({
                    'corp_code': corp_code,
                    'error': str(e)
                })
        
        return {
            'fiscal_year': fiscal_year,
            'report_type': report_type.value,
            'corporations': results,
            'comparison_count': len(results)
        }
    
    async def get_historical_analysis(
        self,
        corp_code: str,
        start_year: int,
        end_year: int,
        report_type: ReportType = ReportType.ANNUAL
    ) -> Dict[str, Any]:
        """
        Get historical financial data and trends.
        
        Args:
            corp_code: DART corporation code
            start_year: Start fiscal year
            end_year: End fiscal year
            report_type: Type of report
            
        Returns:
            Historical financial data and trends
        """
        logger.info(f"Getting historical analysis for {corp_code}, {start_year}-{end_year}")
        
        # Get corporation info once
        corp_info = await self.dart_service.get_corp_info(corp_code)
        corp_name = corp_info.get('corp_name', 'Unknown')
        
        yearly_data = []
        for year in range(start_year, end_year + 1):
            try:
                result = await self.analyze_corporation_quick(
                    corp_code, year, report_type
                )
                if result['status'] == 'success':
                    yearly_data.append({
                        'year': year,
                        'financial_data': result['financial_data'],
                        'ratios': result['ratios']
                    })
            except Exception as e:
                logger.warning(f"Failed to get data for {year}: {e}")
        
        # Calculate trends if we have multiple years
        trends = self._calculate_trends(yearly_data) if len(yearly_data) > 1 else {}
        
        return {
            'corp_code': corp_code,
            'corp_name': corp_name,
            'start_year': start_year,
            'end_year': end_year,
            'yearly_data': yearly_data,
            'trends': trends,
            'data_years': len(yearly_data)
        }
    
    def _serialize_ratios(self, ratios: List[FinancialRatio]) -> List[Dict[str, Any]]:
        """Convert FinancialRatio objects to dictionaries"""
        return [
            {
                'type': r.ratio_type,
                'value': float(r.ratio_value),
                'formatted': r.as_percentage(),
                'category': self._get_ratio_category(r)
            }
            for r in ratios
        ]
    
    def _get_ratio_category(self, ratio: FinancialRatio) -> str:
        """Get the category of a financial ratio"""
        if ratio.is_profitability_ratio():
            return 'profitability'
        elif ratio.is_liquidity_ratio():
            return 'liquidity'
        elif ratio.is_leverage_ratio():
            return 'leverage'
        elif ratio.is_efficiency_ratio():
            return 'efficiency'
        return 'other'
    
    def _extract_key_metrics(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key financial metrics for comparison"""
        bs = financial_data.get('balance_sheet', {})
        is_data = financial_data.get('income_statement', {})
        
        return {
            'total_assets': bs.get('total_assets'),
            'total_equity': bs.get('total_equity'),
            'revenue': is_data.get('revenue'),
            'net_income': is_data.get('net_income'),
            'operating_income': is_data.get('operating_income')
        }
    
    def _calculate_trends(self, yearly_data: List[Dict]) -> Dict[str, Any]:
        """Calculate financial trends from historical data"""
        if len(yearly_data) < 2:
            return {}
        
        trends = {
            'revenue_growth': [],
            'net_income_growth': [],
            'asset_growth': [],
        }
        
        for i in range(1, len(yearly_data)):
            prev = yearly_data[i-1]
            curr = yearly_data[i]
            
            prev_is = prev['financial_data'].get('income_statement', {})
            curr_is = curr['financial_data'].get('income_statement', {})
            prev_bs = prev['financial_data'].get('balance_sheet', {})
            curr_bs = curr['financial_data'].get('balance_sheet', {})
            
            # Revenue growth
            prev_rev = prev_is.get('revenue', 0)
            curr_rev = curr_is.get('revenue', 0)
            if prev_rev and prev_rev != 0:
                trends['revenue_growth'].append({
                    'year': curr['year'],
                    'growth': ((curr_rev - prev_rev) / prev_rev) * 100
                })
            
            # Net income growth
            prev_ni = prev_is.get('net_income', 0)
            curr_ni = curr_is.get('net_income', 0)
            if prev_ni and prev_ni != 0:
                trends['net_income_growth'].append({
                    'year': curr['year'],
                    'growth': ((curr_ni - prev_ni) / prev_ni) * 100
                })
            
            # Asset growth
            prev_assets = prev_bs.get('total_assets', 0)
            curr_assets = curr_bs.get('total_assets', 0)
            if prev_assets and prev_assets != 0:
                trends['asset_growth'].append({
                    'year': curr['year'],
                    'growth': ((curr_assets - prev_assets) / prev_assets) * 100
                })
        
        return trends
    
    async def close(self):
        """Clean up resources"""
        await self.dart_service.close()
