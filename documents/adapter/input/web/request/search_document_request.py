from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class DocumentSearchRequest(BaseModel):
    file_name: Optional[str] = Field(None, description="파일 이름 기준 검색")
    uploaded_from: Optional[datetime] = Field(None, description="등록일 검색 시작 (YYYY-MM-DD)")
    uploaded_to: Optional[datetime] = Field(None, description="등록일 검색 종료 (YYYY-MM-DD)")
    updated_from: Optional[datetime] = Field(None, description="수정일 검색 시작 (YYYY-MM-DD)")
    updated_to: Optional[datetime] = Field(None, description="수정일 검색 종료 (YYYY-MM-DD)")
    page: int = Field(1, ge=1, description="페이지 번호, 1 이상")
    size: int = Field(10, ge=1, le=100, description="한 페이지 문서 수, 1~100")