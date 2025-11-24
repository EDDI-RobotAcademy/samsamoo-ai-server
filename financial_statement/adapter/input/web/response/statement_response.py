from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class StatementResponse(BaseModel):
    id: int
    user_id: int
    company_name: str
    statement_type: str
    fiscal_year: int
    fiscal_quarter: Optional[int]
    s3_key: Optional[str]
    status: str  # Pipeline status: metadata_only, pdf_uploaded, ratios_calculated, analysis_complete
    has_normalized_data: bool
    is_complete: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, statement, has_ratios: bool = False, has_report: bool = False):
        """
        Convert domain entity to response model.

        Args:
            statement: FinancialStatement domain entity
            has_ratios: Whether financial ratios have been calculated (Stage 2)
            has_report: Whether analysis report has been generated (Stage 3-4)
        """
        # Determine pipeline status based on available data
        if statement.normalized_data is None:
            status = "metadata_only"
        elif has_report:
            # Stage 4 complete: Report generated
            status = "analysis_complete"
        elif has_ratios:
            # Stage 2 complete: Ratios calculated
            status = "ratios_calculated"
        elif statement.is_complete():
            # Stage 1 complete: PDF uploaded and normalized
            status = "pdf_uploaded"
        else:
            status = "metadata_only"

        return cls(
            id=statement.id,
            user_id=statement.user_id,
            company_name=statement.company_name,
            statement_type=statement.statement_type.value,
            fiscal_year=statement.fiscal_year,
            fiscal_quarter=statement.fiscal_quarter,
            s3_key=statement.s3_key,
            status=status,
            has_normalized_data=statement.normalized_data is not None,
            is_complete=statement.is_complete(),
            created_at=statement.created_at,
            updated_at=statement.updated_at
        )

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 123,
                "company_name": "Samsung Electronics",
                "statement_type": "quarterly",
                "fiscal_year": 2024,
                "fiscal_quarter": 1,
                "s3_key": "financial_statements/samsung_2024q1.pdf",
                "has_normalized_data": True,
                "is_complete": True,
                "created_at": "2024-01-15T10:00:00",
                "updated_at": "2024-01-15T10:05:00"
            }
        }
