from typing import List
from pydantic import BaseModel

from faq.adapter.input.web.response.summary_faq_response import FAQSummary

class FAQListResponse(BaseModel):
    """GET /list 전용 응답 DTO"""
    items: List[FAQSummary]