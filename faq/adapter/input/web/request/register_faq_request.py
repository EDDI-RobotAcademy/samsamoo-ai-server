from pydantic import BaseModel, Field

class RegisterFAQRequest(BaseModel):
    """
    FAQ 등록을 위한 요청 DTO
    """
    question: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="FAQ 질문 내용"
    )
    answer: str = Field(
        ...,
        min_length=10,
        description="FAQ 답변 내용"
    )
    category: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="FAQ 카테고리 (예: 결제, 배송)"
    )