from datetime import datetime
from typing import Optional

from pydantic import BaseModel

class RegisterFAQResponse(BaseModel):
    """
    FAQ 등록 성공 후 반환되는 응답 DTO
    """
    id: Optional[int] # 등록 성공 후 DB에서 할당된 ID
    question: str      # 등록된 질문 내용
    category: str      # 등록된 카테고리
    created_at: datetime # 생성 시각