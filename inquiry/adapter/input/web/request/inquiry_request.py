from pydantic import BaseModel
from enum import Enum

class InquiryStatusEnum(str, Enum):
    WAIT = "WAIT"
    ANSWERED = "ANSWERED"

# 문의 생성 요청
class InquiryCreateRequest(BaseModel):
    title: str
    content: str

# 관리자 답변 요청
class InquiryAnswerRequest(BaseModel):
    answer: str

class InquiryUpdateRequest(BaseModel):
    title: str  # 수정할 제목
    content: str  # 수정할 내용