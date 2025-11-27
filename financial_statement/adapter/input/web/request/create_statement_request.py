from pydantic import BaseModel, Field
from typing import Optional

class CreateStatementRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    statement_type: str = Field(..., pattern="^(quarterly|annual)$")
    fiscal_year: int = Field(..., ge=1900, le=2100)
    fiscal_quarter: Optional[int] = Field(None, ge=1, le=4)

    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Samsung Electronics",
                "statement_type": "quarterly",
                "fiscal_year": 2024,
                "fiscal_quarter": 1
            }
        }
