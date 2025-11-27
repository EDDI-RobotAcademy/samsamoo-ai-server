from typing import List
from pydantic import BaseModel
from notice.adapter.input.web.response.notice_response import NoticeResponse
from notice.domain.notice import Notice

class NoticeListResponse(BaseModel):
    notices: List[NoticeResponse]  # boards → notices로 변경
    total: int
    page: int
    size: int

    @classmethod
    def from_notices(
        cls,
        notices: list[Notice],  # boards → notices
        page: int,
        size: int,
        total: int
    ):
        return cls(
            notices=[NoticeResponse.from_notice(n) for n in notices],  # from_board → from_notice
            total=total,
            page=page,
            size=size
        )
