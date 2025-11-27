from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from inquiry.adapter.input.web.request.inquiry_request import InquiryStatusEnum
from inquiry.domain.inquiry import Inquiry


class InquiryResponse(BaseModel):
    id: int
    title: str
    content: str
    answer: Optional[str] = None
    status: InquiryStatusEnum
    user_email: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True  # SQLAlchemy ORM 객체도 바로 변환 가능

    @classmethod
    def from_domain(cls, inquiry: Inquiry):
        return cls(
            id=inquiry.id,
            title=inquiry.title,
            content=inquiry.content,
            answer=inquiry.answer,
            user_email=inquiry.user_email,
            status=inquiry.status,
            created_at=inquiry.created_at,  # datetime 그대로
            updated_at=inquiry.updated_at,
        )