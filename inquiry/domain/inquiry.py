from typing import Optional
from datetime import datetime
from enum import Enum

class InquiryStatusEnum(str, Enum):
    WAIT = "WAIT"
    ANSWERED = "ANSWERED"

class Inquiry:
    def __init__(self, title: str, content: str, user_email: str, status: InquiryStatusEnum = InquiryStatusEnum.WAIT):
        self.id: Optional[int] = None
        self.title = title
        self.content = content
        self.answer: Optional[str] = None
        self.status = status
        self.user_email = user_email
        self.created_at: datetime = datetime.utcnow()
        self.updated_at: datetime = datetime.utcnow()

    def answer_inquiry(self, answer: str):
        self.answer = answer
        self.status = InquiryStatusEnum.ANSWERED
        self.updated_at = datetime.utcnow()
