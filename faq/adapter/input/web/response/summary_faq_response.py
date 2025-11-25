from pydantic import BaseModel
from datetime import datetime

class FAQSummary(BaseModel):
    """
    FAQ 검색 결과 목록의 개별 항목을 요약한 DTO
    """
    id: int
    question: str
    answer_preview: str  # 답변의 짧은 미리보기 (예: 100자 이내)
    category: str
    view_count: int
    created_at: datetime