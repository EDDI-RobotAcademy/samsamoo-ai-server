from typing import List, Optional

from pydantic import BaseModel

from faq.adapter.input.web.response.summary_faq_response import FAQSummary


class SearchFAQResponse(BaseModel):
    """
    FAQ 검색 결과 목록 및 페이지네이션 정보를 포함하는 응답 DTO
    """
    items: List[FAQSummary]  # 요약된 FAQ 항목 목록
    has_next: bool  # 👈 다음 페이지에 항목이 더 있는지 여부
    message: Optional[str] = None