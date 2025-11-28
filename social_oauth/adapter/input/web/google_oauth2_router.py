import json
import uuid
from fastapi import APIRouter, Response, Request, Cookie
from fastapi.responses import RedirectResponse

from account.application.usecase.account_usecase import AccountUseCase
from account.infrastructure.repository.account_repository_impl import AccountRepositoryImpl
from config.redis_config import get_redis
from social_oauth.application.usecase.google_oauth2_usecase import GoogleOAuth2UseCase
from social_oauth.infrastructure.service.google_oauth2_service import GoogleOAuth2Service

authentication_router = APIRouter()
service = GoogleOAuth2Service()
account_repository = AccountRepositoryImpl()
account_usecase = AccountUseCase(account_repository)
google_usecase = GoogleOAuth2UseCase(service)

redis_client = get_redis()


@authentication_router.get("/google")
async def redirect_to_google():
    url = google_usecase.get_authorization_url()
    print("[DEBUG] Redirecting to Google:", url)
    return RedirectResponse(url)


@authentication_router.get("/google/redirect")
async def process_google_redirect(
    response: Response,
    code: str,
    state: str | None = None
):
    print("[DEBUG] /google/redirect called")
    print("code:", code)
    print("state:", state)

    result = google_usecase.fetch_user_profile(code, state or "")
    profile = result["profile"]
    access_token = result["access_token"]
    print("profile:", profile)

    # 계정 생성/조회
    account = account_usecase.create_or_get_account(
        profile.get("email"),
        profile.get("name")
    )

    # 세션 ID 생성
    session_id = str(uuid.uuid4())
    print("[DEBUG] Generated session_id:", session_id)

    # Redis 저장 (user_id + 이메일 + 닉네임 + role + 토큰)
    redis_client.set(
        f"session:{session_id}",
        json.dumps({
            "user_id": account.id,
            "email": account.email,
            "nickname": account.nickname,
            "role": account.role,
            "access_token": str(access_token.access_token)
        }),
        ex=6 * 60 * 60
    )

    # HTTP-only 쿠키 발급
    redirect_response = RedirectResponse("http://localhost:3000", status_code=302)
    # 프론트 페이지
    redirect_response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=6 * 60 * 60
    )

    print("[DEBUG] Cookie set in RedirectResponse directly")
    return redirect_response


# ⭐ 프론트에서 사용하기 위한 /me 엔드포인트 추가
@authentication_router.get("/me")
async def auth_me(session_id: str | None = Cookie(None)):

    if not session_id:
        return {"isLoggedIn": False}

    redis_key = f"session:{session_id}"
    session_data = redis_client.get(redis_key)

    if not session_data:
        return {"isLoggedIn": False}

    if isinstance(session_data, bytes):
        session_data = session_data.decode("utf-8")

    session = json.loads(session_data)

    return {
        "isLoggedIn": True,
        "id": session["user_id"],
        "email": session["email"],
        "nickname": session["nickname"],
        "role": session["role"]
    }


# ⭐ /status 엔드포인트 (AuthContext에서 쓰는 경우)
@authentication_router.get("/status")
async def auth_status(request: Request, session_id: str | None = Cookie(None)):

    if not session_id:
        return {"isLoggedIn": False}

    redis_key = f"session:{session_id}"
    session_data = redis_client.get(redis_key)

    if not session_data:
        return {"isLoggedIn": False}

    if isinstance(session_data, bytes):
        session_data = session_data.decode("utf-8")

    session = json.loads(session_data)

    return {
        "isLoggedIn": True,
        "id": session.get("user_id"),
        "email": session.get("email"),
        "nickname": session.get("nickname"),
        "role": session.get("role")
    }


@authentication_router.post("/logout")
async def logout(response: Response, session_id: str | None = Cookie(None)):
    print("[DEBUG] /logout called")
    print("[DEBUG] Received session_id cookie:", session_id)

    if session_id:
        redis_key = f"session:{session_id}"
        redis_client.delete(redis_key)
        print(f"[DEBUG] Deleted session from Redis: {redis_key}")

    response.delete_cookie(key="session_id")
    print("[DEBUG] Cleared session_id cookie")

    return {"logged_out": True}
