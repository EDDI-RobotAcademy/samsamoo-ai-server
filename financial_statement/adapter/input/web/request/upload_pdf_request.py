from pydantic import BaseModel, Field

class UploadPDFRequest(BaseModel):
    statement_id: int = Field(..., gt=0)
    s3_key: str = Field(..., min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "statement_id": 1,
                "s3_key": "financial_statements/samsung_2024q1.pdf"
            }
        }
