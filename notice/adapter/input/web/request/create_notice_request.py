from pydantic import BaseModel

class CreateNoticeRequest(BaseModel):
    title: str
    content: str
