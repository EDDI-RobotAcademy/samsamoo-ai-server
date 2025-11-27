from pydantic import BaseModel
from datetime import datetime
from notice.domain.notice import Notice

class NoticeResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: str
