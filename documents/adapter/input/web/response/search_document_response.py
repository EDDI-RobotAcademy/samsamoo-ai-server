from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class DocumentItemResponse(BaseModel):
    id: int
    file_name: str
    uploader_id: int
    uploaded_at: datetime
    updated_at: datetime

class DocumentSearchResponse(BaseModel):
    total: int
    page: int
    size: int
    data: List[DocumentItemResponse]
    message: Optional[str] = None