"""
XBRL Analysis Router

FastAPI router for XBRL-based corporate financial analysis endpoints.
Provides APIs for:
- Corporation search
- XBRL financial statement retrieval
- Financial ratio calculation
- LLM-powered corporate analysis
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import tempfile
import os

from financial_statement.domain.xbrl_document import ReportType
from financial_statement.application.usecase.xbrl_analysis_usecase import XBRLAnalysisUseCase, XBRLAnalysisError

logger = logging.getLogger(__name__)

# Initialize router
xbrl_router = APIRouter(tags=["xbrl-analysis"])

# Initialize use case (lazy initialization to allow for dependency injection later)
_usecase: Optional[XBRLAnalysisUseCase] = None


def get_usecase() -> XBRLAnalysisUseCase:
    """Get or create the XBRL analysis use case instance"""
    global _usecase
    if _usecase is None:
        _usecase = XBRLAnalysisUseCase()
    return _usecase


# Request/Response Models
class CorporationSearchRequest(BaseModel):
    """Request model for corporation search"""
    corp_name: str = Field(..., min_length=1, description="Corporation name to search")


class CorporationSearchResponse(BaseModel):
    """Response model for corporation search"""
    results: List[dict]
    count: int


class AnalysisRequest(BaseModel):
    """Request model for corporate analysis"""
    corp_code: str = Field(..., min_length=8, max_length=8, description="DART corporation code (8자리)")
    fiscal_year: int = Field(..., ge=2000, le=2100, description="Fiscal year to analyze")
    report_type: str = Field(default="annual", description="Report type: annual, semi_annual, quarterly")
    industry: str = Field(default="default", description="Industry for benchmark comparison")


class CompareRequest(BaseModel):
    """Request model for corporation comparison"""
    corp_codes: List[str] = Field(..., min_items=2, max_items=10, description="List of corporation codes to compare")
    fiscal_year: int = Field(..., ge=2000, le=2100)
    report_type: str = Field(default="annual")


class HistoricalRequest(BaseModel):
    """Request model for historical analysis"""
    corp_code: str = Field(..., min_length=8, max_length=8)
    start_year: int = Field(..., ge=2000, le=2100)
    end_year: int = Field(..., ge=2000, le=2100)
    report_type: str = Field(default="annual")


# Helper function to convert report type string to enum
def get_report_type(report_type_str: str) -> ReportType:
    """Convert report type string to ReportType enum"""
    mapping = {
        'annual': ReportType.ANNUAL,
        'semi_annual': ReportType.SEMI_ANNUAL,
        'quarterly': ReportType.QUARTERLY,
    }
    return mapping.get(report_type_str.lower(), ReportType.ANNUAL)


# Endpoints

@xbrl_router.get("/search")
async def search_corporation(
    corp_name: str = Query(..., min_length=1, description="Corporation name to search")
):
    """
    Search for corporations by name.
    
    Returns a list of matching corporations with their DART codes.
    
    - **corp_name**: Corporation name (partial match supported, e.g., "삼성")
    
    Example: /xbrl/search?corp_name=삼성전자
    """
    try:
        usecase = get_usecase()
        results = await usecase.search_corporation(corp_name)
        
        return JSONResponse({
            "results": results,
            "count": len(results),
            "query": corp_name
        })
        
    except Exception as e:
        logger.error(f"Corporation search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@xbrl_router.get("/corp/{corp_code}")
async def get_corporation_info(corp_code: str):
    """
    Get detailed corporation information.
    
    - **corp_code**: DART corporation code (8자리, e.g., "00126380")
    
    Returns corporation details including name, stock code, industry, etc.
    """
    if len(corp_code) != 8:
        raise HTTPException(status_code=400, detail="Corporation code must be 8 characters")
    
    try:
        usecase = get_usecase()
        info = await usecase.get_corporation_info(corp_code)
        return info
        
    except Exception as e:
        logger.error(f"Get corporation info failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get corporation info: {str(e)}")


@xbrl_router.post("/analyze")
async def analyze_corporation(request: AnalysisRequest):
    """
    Comprehensive corporate financial analysis.
    
    This endpoint performs complete analysis:
    1. Fetches XBRL financial statements from DART
    2. Parses and extracts financial data
    3. Calculates financial ratios (ROA, ROE, etc.)
    4. Generates LLM-powered analysis and recommendations
    
    - **corp_code**: DART corporation code (8자리)
    - **fiscal_year**: Fiscal year to analyze (e.g., 2023)
    - **report_type**: "annual", "semi_annual", or "quarterly"
    - **industry**: Industry for benchmark comparison ("default", "manufacturing", "technology", "finance", "retail")
    
    Requires DART_API_KEY and LLM API key (OPENAI_API_KEY or ANTHROPIC_API_KEY) in environment.
    """
    try:
        usecase = get_usecase()
        report_type = get_report_type(request.report_type)
        
        result = await usecase.analyze_corporation(
            corp_code=request.corp_code,
            fiscal_year=request.fiscal_year,
            report_type=report_type,
            industry=request.industry
        )
        
        return result
        
    except XBRLAnalysisError as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@xbrl_router.get("/analyze/quick")
async def analyze_corporation_quick(
    corp_code: str = Query(..., min_length=8, max_length=8, description="DART corporation code"),
    fiscal_year: int = Query(..., ge=2000, le=2100, description="Fiscal year"),
    report_type: str = Query(default="annual", description="Report type")
):
    """
    Quick corporate analysis without LLM analysis.
    
    Returns financial data and calculated ratios only.
    Faster and doesn't require LLM API key.
    
    - **corp_code**: DART corporation code (8자리)
    - **fiscal_year**: Fiscal year to analyze
    - **report_type**: "annual", "semi_annual", or "quarterly"
    
    Requires only DART_API_KEY in environment.
    """
    try:
        usecase = get_usecase()
        rt = get_report_type(report_type)
        
        result = await usecase.analyze_corporation_quick(
            corp_code=corp_code,
            fiscal_year=fiscal_year,
            report_type=rt
        )
        
        return result
        
    except XBRLAnalysisError as e:
        logger.error(f"Quick analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Quick analysis failed: {str(e)}")


@xbrl_router.post("/compare")
async def compare_corporations(request: CompareRequest):
    """
    Compare multiple corporations' financial metrics.
    
    Compares up to 10 corporations side by side.
    
    - **corp_codes**: List of DART corporation codes (2-10 corporations)
    - **fiscal_year**: Fiscal year for comparison
    - **report_type**: "annual", "semi_annual", or "quarterly"
    """
    if len(request.corp_codes) < 2:
        raise HTTPException(status_code=400, detail="At least 2 corporations required for comparison")
    
    if len(request.corp_codes) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 corporations for comparison")
    
    try:
        usecase = get_usecase()
        report_type = get_report_type(request.report_type)
        
        result = await usecase.compare_corporations(
            corp_codes=request.corp_codes,
            fiscal_year=request.fiscal_year,
            report_type=report_type
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@xbrl_router.get("/historical")
async def get_historical_analysis(
    corp_code: str = Query(..., min_length=8, max_length=8),
    start_year: int = Query(..., ge=2000, le=2100),
    end_year: int = Query(..., ge=2000, le=2100),
    report_type: str = Query(default="annual")
):
    """
    Get historical financial data and trends.
    
    Retrieves multi-year financial data and calculates trends.
    
    - **corp_code**: DART corporation code
    - **start_year**: Start fiscal year
    - **end_year**: End fiscal year
    - **report_type**: "annual", "semi_annual", or "quarterly"
    """
    if end_year < start_year:
        raise HTTPException(status_code=400, detail="end_year must be >= start_year")
    
    if end_year - start_year > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 year range allowed")
    
    try:
        usecase = get_usecase()
        rt = get_report_type(report_type)
        
        result = await usecase.get_historical_analysis(
            corp_code=corp_code,
            start_year=start_year,
            end_year=end_year,
            report_type=rt
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Historical analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Historical analysis failed: {str(e)}")


@xbrl_router.get("/ratios/{corp_code}")
async def get_financial_ratios(
    corp_code: str,
    fiscal_year: int = Query(..., ge=2000, le=2100),
    report_type: str = Query(default="annual")
):
    """
    Get calculated financial ratios for a corporation.
    
    Returns all calculated financial ratios:
    - Profitability: ROA, ROE, Profit Margin, Operating Margin
    - Liquidity: Current Ratio, Quick Ratio
    - Leverage: Debt Ratio, Equity Multiplier
    - Efficiency: Asset Turnover
    
    - **corp_code**: DART corporation code
    - **fiscal_year**: Fiscal year
    - **report_type**: "annual", "semi_annual", or "quarterly"
    """
    if len(corp_code) != 8:
        raise HTTPException(status_code=400, detail="Corporation code must be 8 characters")
    
    try:
        usecase = get_usecase()
        rt = get_report_type(report_type)
        
        result = await usecase.analyze_corporation_quick(
            corp_code=corp_code,
            fiscal_year=fiscal_year,
            report_type=rt
        )
        
        if result['status'] != 'success':
            raise HTTPException(status_code=404, detail=result.get('error', 'Data not found'))
        
        return {
            "corp_code": corp_code,
            "corp_name": result['corp_name'],
            "fiscal_year": fiscal_year,
            "ratios": result['ratios']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get ratios failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ratios: {str(e)}")


@xbrl_router.get("/available-reports/{corp_code}")
async def get_available_reports(
    corp_code: str,
    begin_year: int = Query(default=2020, ge=2000, le=2100),
    end_year: int = Query(default=None, ge=2000, le=2100)
):
    """
    List available financial reports for a corporation.
    
    Returns list of available reports from DART.
    
    - **corp_code**: DART corporation code
    - **begin_year**: Start year for search
    - **end_year**: End year for search (defaults to current year)
    """
    if len(corp_code) != 8:
        raise HTTPException(status_code=400, detail="Corporation code must be 8 characters")
    
    try:
        usecase = get_usecase()
        
        reports = await usecase.dart_service.list_available_reports(
            corp_code=corp_code,
            begin_year=begin_year,
            end_year=end_year
        )
        
        return {
            "corp_code": corp_code,
            "begin_year": begin_year,
            "end_year": end_year,
            "reports": reports,
            "count": len(reports)
        }
        
    except Exception as e:
        logger.error(f"Get available reports failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get reports: {str(e)}")


# File upload endpoints

@xbrl_router.post("/upload/analyze")
async def analyze_uploaded_xbrl(
    file: UploadFile = File(..., description="XBRL file (.html, .xhtml, .xml, .xbrl)"),
    corp_name: str = Form(default="Unknown", description="Corporation name"),
    fiscal_year: int = Form(default=2023, ge=2000, le=2100, description="Fiscal year"),
    industry: str = Form(default="default", description="Industry for benchmarking"),
    include_llm_analysis: bool = Form(default=False, description="Include LLM-powered analysis")
):
    """
    Upload and analyze an XBRL/iXBRL file.
    
    Accepts XBRL files in various formats:
    - iXBRL (Inline XBRL): .html, .xhtml, .htm
    - Standard XBRL: .xml, .xbrl
    - ZIP archives containing XBRL files: .zip
    
    **Parameters:**
    - **file**: XBRL file to upload
    - **corp_name**: Corporation name (for display purposes)
    - **fiscal_year**: Fiscal year of the report
    - **industry**: Industry category for benchmark comparison
    - **include_llm_analysis**: Set to true to include LLM-powered analysis (requires LLM API key)
    
    **Returns:**
    - Parsed financial data (balance sheet, income statement, cash flow)
    - Calculated financial ratios
    - LLM analysis (if requested and available)
    
    **Note:** This endpoint does NOT require DART_API_KEY as it processes uploaded files directly.
    """
    # Validate file extension
    allowed_extensions = {'.html', '.xhtml', '.htm', '.xml', '.xbrl', '.zip'}
    file_ext = os.path.splitext(file.filename or '')[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        if len(content) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB")
        
        # Get services
        from financial_statement.infrastructure.service.xbrl_extraction_service import XBRLExtractionService
        from financial_statement.infrastructure.service.ratio_calculation_service import RatioCalculationService
        from financial_statement.infrastructure.service.corporate_analysis_service import CorporateAnalysisService
        from financial_statement.domain.xbrl_document import ReportType, XBRLTaxonomy
        
        xbrl_service = XBRLExtractionService()
        calculation_service = RatioCalculationService()
        
        # Handle ZIP files
        if file_ext == '.zip':
            import zipfile
            import io
            
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, 'upload.zip')
                with open(zip_path, 'wb') as f:
                    f.write(content)
                
                # Extract and find XBRL file
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    xbrl_file = None
                    for name in zf.namelist():
                        if any(name.lower().endswith(ext) for ext in ['.html', '.xhtml', '.htm', '.xml', '.xbrl']):
                            xbrl_file = name
                            break
                    
                    if not xbrl_file:
                        raise HTTPException(status_code=400, detail="No XBRL file found in ZIP archive")
                    
                    content = zf.read(xbrl_file)
        
        # Parse XBRL content
        xbrl_doc = xbrl_service.parse_xbrl_content(
            content=content,
            corp_code="UPLOAD",
            corp_name=corp_name,
            fiscal_year=fiscal_year,
            report_type=ReportType.ANNUAL,
            taxonomy=XBRLTaxonomy.KIFRS
        )
        
        logger.info(f"Parsed uploaded XBRL: {len(xbrl_doc.facts)} facts")
        
        # Extract financial data
        financial_data = xbrl_service.extract_financial_data(xbrl_doc)
        
        # Validate extraction
        validation = xbrl_service.validate_xbrl_structure(xbrl_doc)
        
        # Calculate ratios
        ratios = []
        ratio_data = []
        try:
            ratios = calculation_service.calculate_all_ratios(financial_data, statement_id=0)
            ratio_data = [
                {
                    'type': r.ratio_type,
                    'value': float(r.ratio_value),
                    'formatted': r.as_percentage(),
                    'category': 'profitability' if r.is_profitability_ratio() else
                               'liquidity' if r.is_liquidity_ratio() else
                               'leverage' if r.is_leverage_ratio() else
                               'efficiency' if r.is_efficiency_ratio() else 'other'
                }
                for r in ratios
            ]
        except Exception as e:
            logger.warning(f"Ratio calculation failed: {e}")
            validation['warnings'].append(f"Ratio calculation partial: {str(e)}")
        
        # Prepare result
        result = {
            'status': 'success',
            'corp_name': corp_name,
            'fiscal_year': fiscal_year,
            'source': 'upload',
            'filename': file.filename,
            'financial_data': financial_data,
            'ratios': ratio_data,
            'validation': validation,
            'metadata': {
                'fact_count': len(xbrl_doc.facts),
                'context_count': len(xbrl_doc.contexts),
                'taxonomy': xbrl_doc.taxonomy.value,
                'available_concepts': len(xbrl_doc.get_available_concepts())
            }
        }
        
        # Include LLM analysis if requested
        if include_llm_analysis and ratios:
            try:
                analysis_service = CorporateAnalysisService()
                analysis = await analysis_service.generate_comprehensive_analysis(
                    corp_name=corp_name,
                    financial_data=financial_data,
                    ratios=ratios,
                    fiscal_year=fiscal_year,
                    industry=industry
                )
                result['analysis'] = analysis
            except Exception as e:
                logger.warning(f"LLM analysis failed: {e}")
                result['analysis_error'] = str(e)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"XBRL file analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@xbrl_router.post("/upload/ratios")
async def calculate_ratios_from_upload(
    file: UploadFile = File(..., description="XBRL file (.html, .xhtml, .xml, .xbrl)"),
    corp_name: str = Form(default="Unknown", description="Corporation name"),
    fiscal_year: int = Form(default=2023, ge=2000, le=2100, description="Fiscal year")
):
    """
    Quick ratio calculation from uploaded XBRL file.
    
    Simplified endpoint that only returns financial ratios without LLM analysis.
    Faster processing for users who only need ratio calculations.
    
    **Parameters:**
    - **file**: XBRL file to upload
    - **corp_name**: Corporation name (for display)
    - **fiscal_year**: Fiscal year of the report
    
    **Returns:**
    - Calculated financial ratios only
    """
    # Validate file extension
    allowed_extensions = {'.html', '.xhtml', '.htm', '.xml', '.xbrl', '.zip'}
    file_ext = os.path.splitext(file.filename or '')[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        from financial_statement.infrastructure.service.xbrl_extraction_service import XBRLExtractionService
        from financial_statement.infrastructure.service.ratio_calculation_service import RatioCalculationService
        from financial_statement.domain.xbrl_document import ReportType, XBRLTaxonomy
        
        xbrl_service = XBRLExtractionService()
        calculation_service = RatioCalculationService()
        
        # Handle ZIP files
        if file_ext == '.zip':
            import zipfile
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, 'upload.zip')
                with open(zip_path, 'wb') as f:
                    f.write(content)
                
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    xbrl_file = None
                    for name in zf.namelist():
                        if any(name.lower().endswith(ext) for ext in ['.html', '.xhtml', '.htm', '.xml', '.xbrl']):
                            xbrl_file = name
                            break
                    
                    if not xbrl_file:
                        raise HTTPException(status_code=400, detail="No XBRL file found in ZIP")
                    
                    content = zf.read(xbrl_file)
        
        # Parse XBRL
        xbrl_doc = xbrl_service.parse_xbrl_content(
            content=content,
            corp_code="UPLOAD",
            corp_name=corp_name,
            fiscal_year=fiscal_year,
            report_type=ReportType.ANNUAL,
            taxonomy=XBRLTaxonomy.KIFRS
        )
        
        # Extract and calculate
        financial_data = xbrl_service.extract_financial_data(xbrl_doc)
        ratios = calculation_service.calculate_all_ratios(financial_data, statement_id=0)
        
        return {
            'status': 'success',
            'corp_name': corp_name,
            'fiscal_year': fiscal_year,
            'filename': file.filename,
            'ratios': [
                {
                    'type': r.ratio_type,
                    'value': float(r.ratio_value),
                    'formatted': r.as_percentage(),
                }
                for r in ratios
            ],
            'summary': {
                'total_assets': financial_data.get('balance_sheet', {}).get('total_assets'),
                'total_equity': financial_data.get('balance_sheet', {}).get('total_equity'),
                'revenue': financial_data.get('income_statement', {}).get('revenue'),
                'net_income': financial_data.get('income_statement', {}).get('net_income'),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ratio calculation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")


@xbrl_router.post("/upload/parse")
async def parse_xbrl_file(
    file: UploadFile = File(..., description="XBRL file to parse"),
    include_all_concepts: bool = Form(default=False, description="Include all parsed concepts")
):
    """
    Parse XBRL file and return raw extracted data.
    
    Useful for debugging and understanding what data is available in the file.
    
    **Parameters:**
    - **file**: XBRL file to parse
    - **include_all_concepts**: If true, returns all parsed XBRL concepts
    
    **Returns:**
    - Raw extracted financial data
    - Validation results
    - Available concepts (if requested)
    """
    allowed_extensions = {'.html', '.xhtml', '.htm', '.xml', '.xbrl', '.zip'}
    file_ext = os.path.splitext(file.filename or '')[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        content = await file.read()
        
        from financial_statement.infrastructure.service.xbrl_extraction_service import XBRLExtractionService
        from financial_statement.domain.xbrl_document import ReportType, XBRLTaxonomy
        
        xbrl_service = XBRLExtractionService()
        
        # Handle ZIP
        if file_ext == '.zip':
            import zipfile
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, 'upload.zip')
                with open(zip_path, 'wb') as f:
                    f.write(content)
                
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    xbrl_file = None
                    for name in zf.namelist():
                        if any(name.lower().endswith(ext) for ext in ['.html', '.xhtml', '.htm', '.xml', '.xbrl']):
                            xbrl_file = name
                            break
                    
                    if not xbrl_file:
                        raise HTTPException(status_code=400, detail="No XBRL file found in ZIP")
                    
                    content = zf.read(xbrl_file)
        
        # Parse
        xbrl_doc = xbrl_service.parse_xbrl_content(
            content=content,
            corp_code="PARSE",
            corp_name="Parsed Document",
            fiscal_year=2023,
            report_type=ReportType.ANNUAL,
            taxonomy=XBRLTaxonomy.KIFRS
        )
        
        # Extract data
        financial_data = xbrl_service.extract_financial_data(xbrl_doc)
        validation = xbrl_service.validate_xbrl_structure(xbrl_doc)
        
        result = {
            'status': 'success',
            'filename': file.filename,
            'financial_data': financial_data,
            'validation': validation,
            'metadata': {
                'fact_count': len(xbrl_doc.facts),
                'context_count': len(xbrl_doc.contexts),
                'unit_count': len(xbrl_doc.units),
            }
        }
        
        if include_all_concepts:
            result['concepts'] = xbrl_service.get_available_concepts(xbrl_doc)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"XBRL parse failed: {e}")
        raise HTTPException(status_code=500, detail=f"Parse failed: {str(e)}")


# Health check endpoint
@xbrl_router.get("/health")
async def health_check():
    """
    Health check for XBRL analysis service.
    
    Returns service status and configuration.
    """
    import os
    
    dart_key_configured = bool(os.getenv('DART_API_KEY'))
    openai_key_configured = bool(os.getenv('OPENAI_API_KEY'))
    anthropic_key_configured = bool(os.getenv('ANTHROPIC_API_KEY'))
    
    return {
        "status": "healthy",
        "service": "xbrl-analysis",
        "configuration": {
            "dart_api_key": "configured" if dart_key_configured else "missing",
            "llm_provider": "openai" if openai_key_configured else ("anthropic" if anthropic_key_configured else "template"),
        },
        "capabilities": {
            "quick_analysis": dart_key_configured,
            "full_analysis": dart_key_configured and (openai_key_configured or anthropic_key_configured),
            "historical_analysis": dart_key_configured,
            "comparison": dart_key_configured,
        }
    }
