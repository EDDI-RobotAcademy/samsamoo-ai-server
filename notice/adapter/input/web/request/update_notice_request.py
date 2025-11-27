from pydantic import BaseModel

class UpdateNoticeRequest(BaseModel):
    title: str
    content: str
