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
        """
        Convert list of domain entities to response model.

        Args:
            statements: List of (statement, has_ratios, has_report) tuples or just statement objects
            page: Current page number
            size: Page size
            total: Total number of items
        """
        pages = (total + size - 1) // size if total > 0 else 0  # Calculate total pages

        # Handle both tuple format and plain statement format for backward compatibility
        items = []
        for item in statements:
            if isinstance(item, tuple):
                stmt, has_ratios, has_report = item
                items.append(StatementResponse.from_domain(stmt, has_ratios=has_ratios, has_report=has_report))
            else:
                items.append(StatementResponse.from_domain(item))

        return cls(
            items=items,
            page=page,
            size=size,
            total=total,
            pages=pages
        )
