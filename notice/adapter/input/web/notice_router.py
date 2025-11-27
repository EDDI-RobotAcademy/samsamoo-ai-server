import json
from fastapi import APIRouter, Request, Depends, HTTPException
from typing import List

from notice.adapter.input.web.request.create_notice_request import CreateNoticeRequest
from notice.adapter.input.web.request.update_notice_request import UpdateNoticeRequest
from notice.application.usecase.notice_usecase import NoticeUsecase
from notice.infrastructure.repository.notice_repository_impl import NoticeRepositoryImpl

from config.redis_config import get_redis

redis_client = get_redis()
notice_router = APIRouter(tags=["notice"])

# Repository & Usecase
notice_repository = NoticeRepositoryImpl()
notice_usecase = NoticeUsecase(notice_repository)


# ===============================
# 🔥 ADMIN 권한 체크 (최종 버전)
# ===============================
def admin_required(request: Request):
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(status_code=403, detail="로그인이 필요합니다.")

    session_data = redis_client.get(f"session:{session_id}")
    if not session_data:
        raise HTTPException(status_code=403, detail="세션이 유효하지 않습니다.")

    if isinstance(session_data, bytes):
        session_data = session_data.decode("utf-8")

    session_dict = json.loads(session_data)

    role = session_dict.get("role")

    if role != "ADMIN":
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")

    return session_dict


# ===============================
# 🔥 CRUD
# ===============================

# 1) 공지 생성
@notice_router.post("/create")
def create_notice(
    request_data: CreateNoticeRequest,
    admin_session: dict = Depends(admin_required)
):
    notice = notice_usecase.create_notice(
        title=request_data.title,
        content=request_data.content
    )

    return {
        "id": notice.id,
        "title": notice.title,
        "content": notice.content,
        "created_at": notice.created_at.isoformat()
    }


# 2) 공지 수정
@notice_router.put("/update/{notice_id}")
def update_notice(
    notice_id: int,
    request_data: UpdateNoticeRequest,
    admin_session: dict = Depends(admin_required)
):
    updated_notice = notice_usecase.update_notice(
        notice_id,
        request_data.title,
        request_data.content
    )

    if not updated_notice:
        raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다.")

    return {
        "id": updated_notice.id,
        "title": updated_notice.title,
        "content": updated_notice.content,
        "created_at": updated_notice.created_at.isoformat()
    }


# 3) 공지 삭제
@notice_router.delete("/delete/{notice_id}")
def delete_notice(
    notice_id: int,
    admin_session: dict = Depends(admin_required)
):
    success = notice_usecase.delete_notice(notice_id)

    if not success:
        raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다.")

    return {"detail": "삭제 완료"}


# 4) 공지 목록
@notice_router.get("/list")
def list_notices():
    notices = notice_usecase.list_notices()

    return {
        "notices": [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "created_at": n.created_at.isoformat()
            }
            for n in notices
        ]
    }


# 5) 공지 상세조회 (edit 페이지에서 사용)
@notice_router.get("/{notice_id}")
def get_notice(notice_id: int):
    notice = notice_usecase.get_notice(notice_id)

    if not notice:
        raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다.")

    return {
        "id": notice.id,
        "title": notice.title,
        "content": notice.content,
        "created_at": notice.created_at.isoformat()
    }
