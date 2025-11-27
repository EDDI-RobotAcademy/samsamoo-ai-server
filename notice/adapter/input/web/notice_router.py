import os
from dotenv import load_dotenv
from fastapi import HTTPException

from notice.adapter.input.web.request.create_notice_request import CreateNoticeRequest
from notice.adapter.input.web.request.update_notice_request import UpdateNoticeRequest
from fastapi import APIRouter
from typing import List
from notice.application.usecase.notice_usecase import NoticeUsecase
from notice.infrastructure.repository.notice_repository_impl import NoticeRepositoryImpl
from fastapi import Request, Depends
from config.redis_config import get_redis



load_dotenv()

redis_client = get_redis()

ADMIN_GOOGLE_EMAILS = os.getenv("ADMIN_GOOGLE_EMAILS", "").split(",")

notice_router = APIRouter(tags=["notice"])

# 🔥 repository 인스턴스 생성
notice_repository = NoticeRepositoryImpl()

# 🔥 usecase에 repository 주입
notice_usecase = NoticeUsecase(notice_repository)


# ---------------- 공통 함수 ----------------
def admin_required(request: Request):
    ADMIN_GOOGLE_EMAILS = os.getenv("ADMIN_GOOGLE_EMAILS", "").split(",")
    print(ADMIN_GOOGLE_EMAILS)
    # 여기서 request에서 user_email 가져오기
    user_email = getattr(request.state, "user_email", None)

    if not user_email:
        # 쿠키나 헤더에서 세션 id 확인 후 Redis에서 가져와도 됨
        session_id = request.cookies.get("session_id")
        if session_id:
            session_data = redis_client.get(f"session:{session_id}")
            if session_data:
                import json
                session_dict = json.loads(session_data)
                user_email = session_dict.get("email")

    return user_email in ADMIN_GOOGLE_EMAILS
# ---------------- CRUD ----------------

@notice_router.post("/create")
def create_notice(
    request_data: CreateNoticeRequest,
    admin_email: str = Depends(admin_required)
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


@notice_router.put("/update/{notice_id}")
def update_notice(
    notice_id: int,
    request_data: UpdateNoticeRequest,
    admin_email: str = Depends(admin_required)
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


@notice_router.delete("/delete/{notice_id}")
def delete_notice(
    notice_id: int,
    admin_email: str = Depends(admin_required)
):
    success = notice_usecase.delete_notice(notice_id)

    if not success:
        raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다.")

    return {"detail": "삭제 완료"}

@notice_router.get("/list")
def list_notices(request: Request):
    notices = notice_usecase.list_notices()

    print(request)
    # 관리자 체크
    is_admin = admin_required(request)
    print("is_admin: "+str(is_admin))
    return {
        "is_admin": is_admin,
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