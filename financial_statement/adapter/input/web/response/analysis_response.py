from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class AnalysisReportResponse(BaseModel):
    id: int
    statement_id: int
    kpi_summary: Optional[str]
    statement_table_summary: Optional[Dict[str, Any]]
    ratio_analysis: Optional[str]
    report_s3_key: Optional[str]
    is_complete: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, report):
        return cls(
            id=report.id,
            statement_id=report.statement_id,
            kpi_summary=report.kpi_summary,
            statement_table_summary=report.statement_table_summary,
            ratio_analysis=report.ratio_analysis,
            report_s3_key=report.report_s3_key,
            is_complete=report.is_complete(),
            created_at=report.created_at
        )
