from pydantic import BaseModel
from typing import List
from datetime import datetime

class RatioItemResponse(BaseModel):
    id: int
    ratio_type: str
    ratio_value: str  # Formatted as string with percentage
    calculated_at: datetime

    @classmethod
    def from_domain(cls, ratio):
        return cls(
            id=ratio.id,
            ratio_type=ratio.ratio_type,
            ratio_value=ratio.as_percentage(),
            calculated_at=ratio.calculated_at
        )

class RatioListResponse(BaseModel):
    statement_id: int
    ratios: List[RatioItemResponse]
    total_count: int

    @classmethod
    def from_domain_list(cls, statement_id, ratios):
        return cls(
            statement_id=statement_id,
            ratios=[RatioItemResponse.from_domain(r) for r in ratios],
            total_count=len(ratios)
        )
