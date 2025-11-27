from fastapi import APIRouter, Depends, HTTPException, status, Cookie
from typing import List

from account.adapter.input.web.session_helper import get_current_user
from inquiry.adapter.input.web.request.inquiry_request import InquiryCreateRequest, InquiryAnswerRequest, \
    InquiryUpdateRequest
from inquiry.adapter.input.web.response.inquiry_response import InquiryResponse
from inquiry.application.usecase.inquiry_usecase import InquiryUseCase
from account.domain.account import Account
from account.infrastructure.repository.account_repository_impl import AccountRepositoryImpl

inquiry_router = APIRouter(tags=["Inquiry"])

usecase = InquiryUseCase.get_instance()
account_repo = AccountRepositoryImpl()  # 이메일, role 조회용

def current_account(session_id: str = Cookie(None)) -> Account:
    """
    Redis 세션 기반으로 현재 Account 가져오기
    """
    user_id = get_current_user(session_id)
    account = account_repo.find_all_by_id([user_id])[0]
    if not account:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 사용자입니다.")
    return account


# 1:1 문의 생성
@inquiry_router.post("", response_model=InquiryResponse)
def create_inquiry(
    request: InquiryCreateRequest,
    current_user: Account = Depends(current_account)
):
    inquiry = usecase.create_inquiry(
        title=request.title,
        content=request.content,
        user_email=current_user.email
    )
    return InquiryResponse.from_domain(inquiry)


# 사용자 자기 문의 목록 조회
@inquiry_router.get("/me", response_model=List[InquiryResponse])
def get_my_inquiries(current_user: Account = Depends(current_account)):
    inquiries = usecase.get_my_inquiries(current_user.email)
    return [InquiryResponse.from_domain(i) for i in inquiries]

@inquiry_router.put("/me/{inquiry_id}", response_model=InquiryResponse)
def update_my_inquiry(
    inquiry_id: int,
    request: InquiryUpdateRequest,
    current_user: Account = Depends(current_account)
):
    try:
        inquiry = usecase.update_inquiry(
            inquiry_id=inquiry_id,
            title=request.title,
            content=request.content,
            current_user_email=current_user.email,
            current_user_role=current_user.role
        )
        return InquiryResponse.from_domain(inquiry)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found")


@inquiry_router.delete("/me/{inquiry_id}")
def delete_my_inquiry(
    inquiry_id: int,
    current_user: Account = Depends(current_account)
):
    try:
        usecase.delete_inquiry(
            inquiry_id=inquiry_id,
            current_user_email=current_user.email,
            current_user_role=current_user.role
        )
        return {"detail": "삭제 완료"}
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found")


# 관리자 전체 문의 조회
@inquiry_router.get("", response_model=List[InquiryResponse])
def get_all_inquiries(current_user: Account = Depends(current_account)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    inquiries = usecase.get_all_inquiries(current_user.role)
    return [InquiryResponse.from_domain(i) for i in inquiries]


# 단건 문의 조회
@inquiry_router.get("/{inquiry_id}", response_model=InquiryResponse)
def get_inquiry(
    inquiry_id: int,
    current_user: Account = Depends(current_account)
):
    try:
        inquiry = usecase.get_inquiry(inquiry_id, current_user.email, current_user.role)
        return InquiryResponse.from_domain(inquiry)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found")


# 관리자 답변 작성
@inquiry_router.post("/{inquiry_id}/answer", response_model=InquiryResponse)
def answer_inquiry(
    inquiry_id: int,
    request: InquiryAnswerRequest,
    current_user: Account = Depends(current_account)
):
    try:
        inquiry = usecase.answer_inquiry(inquiry_id, request.answer, current_user.role)
        return InquiryResponse.from_domain(inquiry)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found")
