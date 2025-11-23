from pydantic import BaseModel
from typing import List
from .statement_response import StatementResponse

class StatementListResponse(BaseModel):
    items: List[StatementResponse]  # Changed from 'statements' to match frontend expectation
    page: int
    size: int
    total: int
    pages: int  # Total number of pages

    @classmethod
    def from_domain_list(cls, statements, page, size, total):
        pages = (total + size - 1) // size if total > 0 else 0  # Calculate total pages
        return cls(
            items=[StatementResponse.from_domain(s) for s in statements],
            page=page,
            size=size,
            total=total,
            pages=pages
        )
