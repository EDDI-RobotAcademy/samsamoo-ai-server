from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SearchFAQRequest(BaseModel):
    """
    FAQ 검색 조건을 위한 요청 DTO (파일 검색 요청 구조 기반)
    """
    # 카테고리 이름 기준 검색
    category: Optional[str] = Field(
        None,
        max_length=100,
        description="카테고리 이름 기준 검색"
    )

    # 질문/답변 내용 키워드 검색
    query: Optional[str] = Field(
        None,
        min_length=2,
        max_length=255,
        description="질문 또는 답변 내용 키워드 검색"
    )

    # 등록일 검색 시작/종료
    created_from: Optional[datetime] = Field(
        None,
        description="등록일 검색 시작 (YYYY-MM-DDTHH:MM:SS)"
    )
    created_to: Optional[datetime] = Field(
        None,
        description="등록일 검색 종료 (YYYY-MM-DDTHH:MM:SS)"
    )

    # 수정일 검색 시작/종료
    updated_from: Optional[datetime] = Field(
        None,
        description="수정일 검색 시작 (YYYY-MM-DDTHH:MM:SS)"
    )
    updated_to: Optional[datetime] = Field(
        None,
        description="수정일 검색 종료 (YYYY-MM-DDTHH:MM:SS)"
    )

    page: int = 0  # 0부터 시작하는 페이지 번호 (프론트엔드가 보냄)
    size: int = 10  # 한 페이지당 항목 수 (프론트엔드가 보냄)