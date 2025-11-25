from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional
import tempfile
import os
import logging

from account.adapter.input.web.session_helper import get_current_user
from financial_statement.adapter.input.web.request.create_statement_request import CreateStatementRequest
from financial_statement.adapter.input.web.request.upload_pdf_request import UploadPDFRequest
from financial_statement.adapter.input.web.response.statement_response import StatementResponse
from financial_statement.adapter.input.web.response.statement_list_response import StatementListResponse
from financial_statement.adapter.input.web.response.ratio_response import RatioListResponse, RatioItemResponse
from financial_statement.adapter.input.web.response.analysis_response import AnalysisReportResponse
from financial_statement.adapter.input.web.response.analysis_result_response import AnalysisResultResponse

from financial_statement.domain.financial_statement import StatementType
from financial_statement.application.usecase.financial_analysis_usecase import FinancialAnalysisUseCase
from financial_statement.infrastructure.repository.financial_repository_impl import FinancialRepositoryImpl
from financial_statement.infrastructure.service.pdf_extraction_service import PDFExtractionService
from financial_statement.infrastructure.service.ratio_calculation_service import RatioCalculationService
from financial_statement.infrastructure.service.llm_analysis_service import LLMAnalysisService
from financial_statement.infrastructure.service.report_generation_service import ReportGenerationService

logger = logging.getLogger(__name__)

# Initialize router
financial_statement_router = APIRouter(tags=["financial-statements"])

# Instantiate dependencies (following existing pattern)
repository = FinancialRepositoryImpl()
pdf_service = PDFExtractionService()
calculation_service = RatioCalculationService()
llm_service = LLMAnalysisService()
report_service = ReportGenerationService(template_dir="templates")
usecase = FinancialAnalysisUseCase(
    repository,
    pdf_service,
    calculation_service,
    llm_service,
    report_service
)

@financial_statement_router.get("/list", response_model=StatementListResponse)
async def list_user_statements(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user_id: int = Depends(get_current_user)
):
    """List all financial statements for current user with pagination"""
    statements = usecase.get_user_statements(user_id, page, size)

    # Check analysis progress for each statement to set proper status
    statements_with_status = []
    for stmt in statements:
        has_ratios = len(usecase.get_ratios(stmt.id)) > 0
        has_report = usecase.get_report(stmt.id) is not None
        statements_with_status.append((stmt, has_ratios, has_report))

    # TODO: Get total count from repository
    total = len(statements)  # Placeholder - should come from repository

    return StatementListResponse.from_domain_list(statements_with_status, page, size, total)

# ============================================================
# IMPORTANT: Static routes MUST come before dynamic /{id} routes
# Otherwise FastAPI will try to match "list" as a statement_id
# ============================================================

@financial_statement_router.get("/list", response_model=StatementListResponse)
async def list_user_statements(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user_id: int = Depends(get_current_user)
):
    """List all financial statements for current user with pagination"""
    statements = usecase.get_user_statements(user_id, page, size)

    # Check analysis progress for each statement to set proper status
    statements_with_status = []
    for stmt in statements:
        has_ratios = len(usecase.get_ratios(stmt.id)) > 0
        has_report = usecase.get_report(stmt.id) is not None
        statements_with_status.append((stmt, has_ratios, has_report))

    # TODO: Get total count from repository
    total = len(statements)  # Placeholder - should come from repository

    return StatementListResponse.from_domain_list(statements_with_status, page, size, total)


@financial_statement_router.post("/create", response_model=StatementResponse)
async def create_statement(
    request: CreateStatementRequest,
    user_id: int = Depends(get_current_user)
):
    """
    Create a new financial statement (metadata only, before PDF upload).

    - **company_name**: Company name
    - **statement_type**: "quarterly" or "annual"
    - **fiscal_year**: Fiscal year (1900-2100)
    - **fiscal_quarter**: Quarter number (1-4) if quarterly, None if annual
    """
    try:
        statement_type = StatementType(request.statement_type)

        statement = usecase.create_statement(
            user_id=user_id,
            company_name=request.company_name,
            statement_type=statement_type,
            fiscal_year=request.fiscal_year,
            fiscal_quarter=request.fiscal_quarter
        )

        return StatementResponse.from_domain(statement)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create statement: {e}")
        raise HTTPException(status_code=500, detail="Failed to create financial statement")


@financial_statement_router.post("/upload", response_model=StatementResponse)
async def upload_statement_pdf(
    statement_id: int = Query(..., gt=0),
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user)
):
    """
    Upload PDF for an existing statement and extract financial data (Stage 1 of pipeline).

    - **statement_id**: ID of the statement to upload PDF for
    - **file**: PDF file containing financial statements
    """
    try:
        # Verify ownership
        statement = usecase.get_statement(statement_id)
        if not statement:
            raise HTTPException(status_code=404, detail="Statement not found")

        if statement.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to upload to this statement")

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # TODO: Upload to S3 and get S3 key
            # For now, use local path as placeholder
            s3_key = f"financial_statements/user_{user_id}/statement_{statement_id}.pdf"

            # Process PDF (Stage 1: Extraction)
            updated_statement = usecase.upload_statement_pdf(
                statement_id=statement_id,
                pdf_path=tmp_path,
                s3_key=s3_key
            )

            return StatementResponse.from_domain(updated_statement)

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error during PDF upload: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to upload PDF: {e}")
        # Check if it's an extraction-related error (user error vs system error)
        error_message = str(e)
        if "Failed to extract" in error_message or "OCR is disabled" in error_message:
            # Extraction failure - likely user uploaded wrong file type
            raise HTTPException(status_code=400, detail=error_message)
        else:
            # System error - internal processing failure
            raise HTTPException(status_code=500, detail=f"Failed to process PDF: {error_message}")


@financial_statement_router.post("/analyze/{statement_id}", response_model=AnalysisResultResponse)
async def analyze_statement(
    statement_id: int,
    user_id: int = Depends(get_current_user)
):
    """
    Run complete analysis pipeline (Stages 2-4: Calculation, LLM Analysis, Report Generation).

    - **statement_id**: ID of the statement to analyze

    This endpoint executes:
    1. Stage 2: Calculate financial ratios
    2. Stage 3: Generate LLM analysis
    3. Stage 4: Create visual report and PDF
    """
    try:
        # Verify ownership
        statement = usecase.get_statement(statement_id)
        if not statement:
            raise HTTPException(status_code=404, detail="Statement not found")

        if statement.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to analyze this statement")

        if not statement.is_complete():
            raise HTTPException(status_code=400, detail="Statement is incomplete - PDF must be uploaded first")

        # Run analysis pipeline (async)
        result = await usecase.run_analysis_pipeline(statement_id)

        # Prepare response - analysis is complete so both ratios and report exist
        # Note: ratios may be empty if ratio calculation was skipped (fallback to LLM analysis)
        has_ratios = len(result["ratios"]) > 0
        ratio_calculation_skipped = result.get("ratio_calculation_skipped", False)

        statement_resp = StatementResponse.from_domain(result["statement"], has_ratios=has_ratios, has_report=True)
        ratios_resp = [RatioItemResponse.from_domain(r) for r in result["ratios"]]
        report_resp = AnalysisReportResponse.from_domain(result["report"])

        # TODO: Upload PDF to S3 and generate presigned URL
        # For now, use local download endpoint
        report_pdf_url = f"/financial-statements/{statement_id}/report/download"

        return AnalysisResultResponse(
            statement=statement_resp,
            ratios=ratios_resp,
            report=report_resp,
            report_pdf_url=report_pdf_url,
            ratio_calculation_skipped=ratio_calculation_skipped
        )

    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.error(f"Validation error during analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@financial_statement_router.get("/{statement_id}", response_model=StatementResponse)
async def get_statement(
    statement_id: int,
    user_id: int = Depends(get_current_user)
):
    """Get a single financial statement by ID"""
    statement = usecase.get_statement(statement_id)

    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    if statement.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this statement")

    # Check analysis progress to set proper status
    has_ratios = len(usecase.get_ratios(statement_id)) > 0
    has_report = usecase.get_report(statement_id) is not None

    return StatementResponse.from_domain(statement, has_ratios=has_ratios, has_report=has_report)


@financial_statement_router.get("/{statement_id}/ratios", response_model=RatioListResponse)
async def get_statement_ratios(
    statement_id: int,
    user_id: int = Depends(get_current_user)
):
    """Get all calculated ratios for a statement"""
    statement = usecase.get_statement(statement_id)

    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    if statement.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this statement")

    ratios = usecase.get_ratios(statement_id)
    return RatioListResponse.from_domain_list(statement_id, ratios)


@financial_statement_router.get("/{statement_id}/report", response_model=AnalysisReportResponse)
async def get_statement_report(
    statement_id: int,
    user_id: int = Depends(get_current_user)
):
    """Get analysis report for a statement"""
    statement = usecase.get_statement(statement_id)

    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    if statement.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this statement")

    report = usecase.get_report(statement_id)

    if not report:
        raise HTTPException(status_code=404, detail="Analysis report not found")

    return AnalysisReportResponse.from_domain(report)


@financial_statement_router.get("/{statement_id}/report/download")
async def download_report_pdf(
    statement_id: int,
    user_id: int = Depends(get_current_user)
):
    """Download PDF report for a statement"""
    statement = usecase.get_statement(statement_id)

    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    if statement.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to download this report")

    report = usecase.get_report(statement_id)

    if not report or not report.report_s3_key:
        raise HTTPException(status_code=404, detail="Report PDF not found")

    # For local development, serve from local filesystem
    # In production, this would download from S3
    pdf_path = report.report_s3_key  # Currently stores local path

    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found at path: {pdf_path}")
        raise HTTPException(status_code=404, detail="Report PDF file not found on disk")

    # Return file response
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"financial_report_{statement_id}.pdf"
    )


@financial_statement_router.get("/{statement_id}/report/download/md")
async def download_report_markdown(
    statement_id: int,
    user_id: int = Depends(get_current_user)
):
    """
    Download Markdown report for a statement.

    This endpoint generates a Markdown report on-demand with proper UTF-8 encoding,
    solving Korean character display issues that occur with PDF generation.

    - **statement_id**: ID of the statement to download report for
    """
    statement = usecase.get_statement(statement_id)

    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    if statement.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to download this report")

    report = usecase.get_report(statement_id)
    ratios = usecase.get_ratios(statement_id)

    if not report:
        raise HTTPException(status_code=404, detail="Analysis report not found. Run /analyze first.")

    if not statement.normalized_data:
        raise HTTPException(status_code=400, detail="Statement has no financial data")

    try:
        # Create temporary file for markdown
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md', encoding='utf-8') as tmp_file:
            md_path = tmp_file.name

        # Prepare financial data with metadata
        financial_data = statement.normalized_data.copy()
        financial_data['company_name'] = statement.company_name
        financial_data['fiscal_year'] = statement.fiscal_year
        financial_data['fiscal_quarter'] = statement.fiscal_quarter

        # Generate markdown report
        report_service.generate_markdown_report(
            report=report,
            financial_data=financial_data,
            ratios=ratios,
            output_path=md_path
        )

        # Return file response with UTF-8 content type
        return FileResponse(
            path=md_path,
            media_type="text/markdown; charset=utf-8",
            filename=f"financial_report_{statement_id}.md",
            headers={"Content-Disposition": f"attachment; filename=financial_report_{statement_id}.md"}
        )

    except Exception as e:
        logger.error(f"Failed to generate markdown report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate markdown report: {str(e)}")


@financial_statement_router.delete("/{statement_id}")
async def delete_statement(
    statement_id: int,
    user_id: int = Depends(get_current_user)
):
    """Delete a financial statement (owner only)"""
    try:
        success = usecase.delete_statement(statement_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Statement not found")

        return JSONResponse({"result": "deleted", "statement_id": statement_id})

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete statement: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete statement")


@financial_statement_router.post("/{statement_id}/renormalize")
async def renormalize_statement(
    statement_id: int,
    user_id: int = Depends(get_current_user)
):
    """
    Re-normalize existing statement data using improved DART extraction logic.

    This endpoint:
    1. Reads existing normalized_data from database
    2. Re-applies improved normalization (filtering notes, calculating missing totals)
    3. Updates the database with corrected data
    4. Returns comparison of before/after values

    Use this to fix statements that were extracted before DART improvements were added.
    """
    try:
        # Verify ownership
        statement = usecase.get_statement(statement_id)
        if not statement:
            raise HTTPException(status_code=404, detail="Statement not found")

        if statement.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this statement")

        if not statement.normalized_data:
            raise HTTPException(status_code=400, detail="Statement has no data to renormalize")

        # Get current data for comparison
        old_data = statement.normalized_data.copy()
        old_bs = old_data.get("balance_sheet", {})
        old_is = old_data.get("income_statement", {})

        # Re-normalize using improved logic
        new_bs = pdf_service._normalize_balance_sheet(old_bs)
        new_is = pdf_service._normalize_income_statement(old_is)

        # Update statement with new normalized data
        new_normalized_data = {
            "balance_sheet": new_bs,
            "income_statement": new_is,
            "cash_flow_statement": old_data.get("cash_flow_statement", {})
        }

        statement.set_normalized_data(new_normalized_data)
        repository.save_statement(statement)

        # Prepare comparison response
        key_bs_fields = ["total_assets", "total_liabilities", "total_equity",
                        "current_assets", "current_liabilities", "inventory"]
        key_is_fields = ["revenue", "operating_income", "net_income"]

        comparison = {
            "statement_id": statement_id,
            "balance_sheet_changes": {},
            "income_statement_changes": {}
        }

        for field in key_bs_fields:
            old_val = old_bs.get(field)
            new_val = new_bs.get(field)
            if old_val != new_val:
                comparison["balance_sheet_changes"][field] = {
                    "old": old_val,
                    "new": new_val
                }

        for field in key_is_fields:
            old_val = old_is.get(field)
            new_val = new_is.get(field)
            if old_val != new_val:
                comparison["income_statement_changes"][field] = {
                    "old": old_val,
                    "new": new_val
                }

        return JSONResponse({
            "result": "renormalized",
            "statement_id": statement_id,
            "changes": comparison,
            "message": "Data re-normalized. Run /analyze/{statement_id} to recalculate ratios."
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to renormalize statement: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to renormalize: {str(e)}")
