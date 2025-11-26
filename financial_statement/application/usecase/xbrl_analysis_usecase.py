"""
XBRL Analysis Use Case

Orchestrates the complete XBRL-based financial analysis workflow:
1. Fetch XBRL data from DART API or uploaded file
2. Parse and extract financial information
3. Calculate financial ratios
4. Generate LLM-powered corporate analysis
5. Generate PDF/Markdown reports
6. Persist analysis results to database

Enhanced to match PDF analysis feature parity.
"""
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from financial_statement.domain.xbrl_document import XBRLDocument, ReportType, XBRLTaxonomy
from financial_statement.domain.financial_ratio import FinancialRatio
from financial_statement.domain.analysis_report import AnalysisReport
from financial_statement.domain.xbrl_analysis import XBRLAnalysis, XBRLAnalysisStatus, XBRLSourceType
from financial_statement.infrastructure.service.dart_api_service import DARTAPIService, DARTNotFoundError
from financial_statement.infrastructure.service.xbrl_extraction_service import XBRLExtractionService
from financial_statement.infrastructure.service.ratio_calculation_service import RatioCalculationService
from financial_statement.infrastructure.service.corporate_analysis_service import CorporateAnalysisService
from financial_statement.infrastructure.service.report_generation_service import ReportGenerationService
from financial_statement.infrastructure.repository.xbrl_analysis_repository_impl import XBRLAnalysisRepositoryImpl
from financial_statement.application.port.xbrl_analysis_repository_port import XBRLAnalysisRepositoryPort

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
        analysis_service: CorporateAnalysisService = None,
        report_service: ReportGenerationService = None,
        repository: XBRLAnalysisRepositoryPort = None
    ):
        """
        Initialize use case with required services.
        
        Args:
            dart_service: DART API service for fetching XBRL data
            xbrl_service: XBRL extraction service for parsing
            calculation_service: Ratio calculation service
            analysis_service: Corporate analysis service with LLM
            report_service: Report generation service for PDF/Markdown
            repository: Repository for persisting analysis results
        """
        self.dart_service = dart_service or DARTAPIService()
        self.xbrl_service = xbrl_service or XBRLExtractionService()
        self.calculation_service = calculation_service or RatioCalculationService()
        self.analysis_service = analysis_service or CorporateAnalysisService()
        self.report_service = report_service or ReportGenerationService(template_dir="templates")
        self.repository = repository or XBRLAnalysisRepositoryImpl()
    
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
                statement_id=0,  # Using 0 as placeholder since not persisting
                skip_statement_id_validation=True
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
                statement_id=0,
                skip_statement_id_validation=True
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
    
    # ============================================================
    # Enhanced Methods with Persistence (PDF Analysis Parity)
    # ============================================================
    
    async def create_analysis(
        self,
        corp_code: str,
        corp_name: str,
        fiscal_year: int,
        user_id: Optional[int] = None,
        report_type: str = "annual",
        source_type: XBRLSourceType = XBRLSourceType.UPLOAD,
        source_filename: Optional[str] = None
    ) -> XBRLAnalysis:
        """
        Create a new XBRL analysis record (metadata only).
        
        Args:
            corp_code: Corporation code
            corp_name: Corporation name
            fiscal_year: Fiscal year
            user_id: Optional user ID for ownership
            report_type: Report type (annual, semi_annual, quarterly)
            source_type: Source of XBRL data
            source_filename: Original filename if uploaded
            
        Returns:
            Created XBRLAnalysis entity
        """
        logger.info(f"Creating XBRL analysis for {corp_name} ({fiscal_year})")
        
        analysis = XBRLAnalysis(
            corp_code=corp_code,
            corp_name=corp_name,
            fiscal_year=fiscal_year,
            user_id=user_id,
            report_type=report_type,
            source_type=source_type,
            source_filename=source_filename,
            status=XBRLAnalysisStatus.PENDING
        )
        
        saved = self.repository.save(analysis)
        logger.info(f"Created XBRL analysis with ID: {saved.id}")
        return saved
    
    async def run_full_analysis_pipeline(
        self,
        analysis_id: int,
        xbrl_content: bytes,
        industry: str = "default",
        include_llm: bool = True,
        generate_reports: bool = True
    ) -> XBRLAnalysis:
        """
        Run the complete analysis pipeline for an XBRL analysis.
        
        Pipeline stages:
        1. Parse XBRL content
        2. Extract financial data
        3. Calculate financial ratios
        4. Generate LLM analysis (optional)
        5. Generate reports (optional)
        
        Args:
            analysis_id: ID of the analysis record
            xbrl_content: Raw XBRL content bytes
            industry: Industry for benchmark comparison
            include_llm: Whether to include LLM analysis
            generate_reports: Whether to generate PDF/Markdown reports
            
        Returns:
            Updated XBRLAnalysis with all results
        """
        # Get the analysis record
        analysis = self.repository.find_by_id(analysis_id)
        if not analysis:
            raise XBRLAnalysisError(f"Analysis {analysis_id} not found")
        
        logger.info(f"Running full analysis pipeline for {analysis.corp_name} (ID: {analysis_id})")
        
        try:
            # Stage 1: Parse XBRL
            analysis.set_status(XBRLAnalysisStatus.EXTRACTING)
            self.repository.save(analysis)
            
            xbrl_doc = self.xbrl_service.parse_xbrl_content(
                content=xbrl_content,
                corp_code=analysis.corp_code,
                corp_name=analysis.corp_name,
                fiscal_year=analysis.fiscal_year,
                report_type=ReportType.ANNUAL,
                taxonomy=XBRLTaxonomy.KIFRS
            )
            
            analysis.set_metadata(
                fact_count=len(xbrl_doc.facts),
                context_count=len(xbrl_doc.contexts),
                taxonomy=xbrl_doc.taxonomy.value
            )
            
            # Stage 2: Extract financial data
            financial_data = self.xbrl_service.extract_financial_data(xbrl_doc)
            analysis.set_financial_data(financial_data)
            logger.info(f"Extracted financial data: BS={len(financial_data.get('balance_sheet', {}))} items")
            
            # Stage 3: Calculate ratios
            analysis.set_status(XBRLAnalysisStatus.CALCULATING)
            self.repository.save(analysis)
            
            ratios = self.calculation_service.calculate_all_ratios(
                financial_data,
                statement_id=analysis_id,
                skip_statement_id_validation=True
            )
            analysis.set_ratios(self._serialize_ratios(ratios))
            logger.info(f"Calculated {len(ratios)} financial ratios")
            
            # Stage 4: LLM Analysis (optional)
            if include_llm:
                analysis.set_status(XBRLAnalysisStatus.ANALYZING)
                self.repository.save(analysis)
                
                try:
                    llm_result = await self.analysis_service.generate_comprehensive_analysis(
                        corp_name=analysis.corp_name,
                        financial_data=financial_data,
                        ratios=ratios,
                        fiscal_year=analysis.fiscal_year,
                        industry=industry
                    )
                    
                    analysis.set_llm_analysis(
                        executive_summary=llm_result.get('executive_summary'),
                        financial_health=llm_result.get('financial_health'),
                        ratio_analysis=llm_result.get('ratio_analysis'),
                        investment_recommendation=llm_result.get('investment_recommendation')
                    )
                    logger.info("Generated LLM analysis")
                except Exception as e:
                    logger.warning(f"LLM analysis failed: {e}")
                    # Continue without LLM analysis
            
            # Stage 5: Generate Reports (optional)
            if generate_reports:
                analysis.set_status(XBRLAnalysisStatus.GENERATING_REPORT)
                self.repository.save(analysis)
                
                try:
                    report_paths = await self._generate_analysis_reports(analysis, ratios)
                    analysis.set_report_paths(
                        pdf_path=report_paths.get('pdf_path'),
                        md_path=report_paths.get('md_path')
                    )
                    logger.info(f"Generated reports: PDF={report_paths.get('pdf_path')}, MD={report_paths.get('md_path')}")
                except Exception as e:
                    logger.warning(f"Report generation failed: {e}")
                    # Continue without reports
            
            # Mark as complete
            analysis.set_status(XBRLAnalysisStatus.COMPLETED)
            saved = self.repository.save(analysis)
            
            logger.info(f"Analysis pipeline completed for {analysis.corp_name}")
            return saved
            
        except Exception as e:
            logger.error(f"Analysis pipeline failed: {e}")
            analysis.set_error(str(e))
            self.repository.save(analysis)
            raise XBRLAnalysisError(f"Analysis pipeline failed: {e}")
    
    async def _generate_analysis_reports(
        self,
        analysis: XBRLAnalysis,
        ratios: List[FinancialRatio]
    ) -> Dict[str, str]:
        """
        Generate PDF and Markdown reports for analysis.
        
        Args:
            analysis: XBRLAnalysis entity with data
            ratios: List of calculated ratios
            
        Returns:
            Dictionary with pdf_path and md_path
        """
        # Create output directory
        reports_dir = os.path.join(os.getcwd(), "generated_reports", "xbrl")
        analysis_dir = os.path.join(reports_dir, f"analysis_{analysis.id}")
        chart_dir = os.path.join(analysis_dir, "charts")
        os.makedirs(chart_dir, exist_ok=True)
        
        result = {}
        
        # Create AnalysisReport for compatibility with report service
        report = AnalysisReport(statement_id=analysis.id)
        report.set_kpi_summary(analysis.executive_summary or "")
        report.set_ratio_analysis(analysis.ratio_analysis or "")
        
        # Prepare financial data with metadata
        financial_data = analysis.financial_data.copy()
        financial_data['company_name'] = analysis.corp_name
        financial_data['fiscal_year'] = analysis.fiscal_year
        
        try:
            # Generate charts
            chart_paths = []
            if ratios:
                chart_paths = self.report_service.generate_ratio_charts(ratios, chart_dir)
            
            # Generate PDF report
            pdf_path = os.path.join(analysis_dir, f"xbrl_report_{analysis.id}.pdf")
            self.report_service.generate_pdf_report(
                report=report,
                financial_data=financial_data,
                ratios=ratios,
                chart_paths=chart_paths,
                output_path=pdf_path
            )
            result['pdf_path'] = pdf_path
            
        except Exception as e:
            logger.warning(f"PDF generation failed: {e}")
        
        try:
            # Generate Markdown report
            md_path = os.path.join(analysis_dir, f"xbrl_report_{analysis.id}.md")
            self.report_service.generate_markdown_report(
                report=report,
                financial_data=financial_data,
                ratios=ratios,
                output_path=md_path
            )
            result['md_path'] = md_path
            
        except Exception as e:
            logger.warning(f"Markdown generation failed: {e}")
        
        return result
    
    # ============================================================
    # CRUD Operations for Analysis Records
    # ============================================================
    
    def get_analysis(self, analysis_id: int) -> Optional[XBRLAnalysis]:
        """Get an analysis by ID"""
        return self.repository.find_by_id(analysis_id)
    
    def get_user_analyses(
        self,
        user_id: int,
        page: int = 1,
        size: int = 10
    ) -> List[XBRLAnalysis]:
        """Get all analyses for a user with pagination"""
        return self.repository.find_by_user_id(user_id, page, size)
    
    def count_user_analyses(self, user_id: int) -> int:
        """Count total analyses for a user"""
        return self.repository.count_by_user_id(user_id)
    
    def get_corp_analyses(
        self,
        corp_code: str,
        fiscal_year: Optional[int] = None
    ) -> List[XBRLAnalysis]:
        """Get analyses by corporation code"""
        return self.repository.find_by_corp_code(corp_code, fiscal_year)
    
    def delete_analysis(self, analysis_id: int, user_id: int) -> bool:
        """
        Delete an analysis (owner only).
        
        Args:
            analysis_id: Analysis ID to delete
            user_id: User ID for ownership check
            
        Returns:
            True if deleted, False if not found or unauthorized
        """
        analysis = self.repository.find_by_id(analysis_id)
        
        if not analysis:
            return False
        
        if analysis.user_id and analysis.user_id != user_id:
            raise PermissionError(f"User {user_id} is not authorized to delete analysis {analysis_id}")
        
        # Clean up report files
        if analysis.report_pdf_path and os.path.exists(analysis.report_pdf_path):
            try:
                os.remove(analysis.report_pdf_path)
            except Exception as e:
                logger.warning(f"Failed to delete PDF: {e}")
        
        if analysis.report_md_path and os.path.exists(analysis.report_md_path):
            try:
                os.remove(analysis.report_md_path)
            except Exception as e:
                logger.warning(f"Failed to delete MD: {e}")
        
        return self.repository.delete(analysis_id)
    
    def get_report_path(self, analysis_id: int, format: str = "pdf") -> Optional[str]:
        """
        Get the report file path for an analysis.
        
        Args:
            analysis_id: Analysis ID
            format: Report format (pdf or md)
            
        Returns:
            File path if exists, None otherwise
        """
        analysis = self.repository.find_by_id(analysis_id)
        if not analysis:
            return None
        
        if format == "md":
            return analysis.report_md_path
        return analysis.report_pdf_path
