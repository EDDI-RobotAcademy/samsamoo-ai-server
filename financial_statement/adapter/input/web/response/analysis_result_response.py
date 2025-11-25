from pydantic import BaseModel
from typing import List, Optional
from .statement_response import StatementResponse
from .ratio_response import RatioItemResponse
from .analysis_response import AnalysisReportResponse

class AnalysisResultResponse(BaseModel):
    """Complete analysis pipeline result"""
    statement: StatementResponse
    ratios: List[RatioItemResponse]
    report: AnalysisReportResponse
    report_pdf_url: str  # S3 presigned URL or download endpoint
    ratio_calculation_skipped: Optional[bool] = False  # True if ratio calc failed and LLM analyzed raw data

    class Config:
        json_schema_extra = {
            "example": {
                "statement": {"id": 1, "company_name": "Samsung Electronics"},
                "ratios": [{"ratio_type": "ROA", "ratio_value": "5.23%"}],
                "report": {"id": 1, "kpi_summary": "Strong profitability..."},
                "report_pdf_url": "/financial-statements/1/report.pdf",
                "ratio_calculation_skipped": False
            }
        }
