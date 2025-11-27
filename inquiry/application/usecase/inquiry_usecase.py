from typing import List

from inquiry.domain.inquiry import Inquiry
from inquiry.infrastructure.repository.inquiry_repository_impl import InquiryRepositoryImpl


class InquiryUseCase:
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.inquiry_repo = InquiryRepositoryImpl.get_instance()
        return cls.__instance

    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    # 1:1 문의 생성
    def create_inquiry(self, title: str, content: str, user_email: str) -> Inquiry:
        inquiry = Inquiry(title=title, content=content, user_email=user_email)
        return self.inquiry_repo.save(inquiry)

    # 단건 조회 (권한 체크 포함)
    def get_inquiry(self, inquiry_id: int, current_user_email: str, current_user_role: str) -> Inquiry:
        inquiry = self.inquiry_repo.find_by_id(inquiry_id)
        if inquiry is None:
            raise ValueError("Inquiry not found")
        # User는 자기 이메일만 접근 가능, Admin은 전체 가능
        if current_user_role != "ADMIN" and inquiry.user_email != current_user_email:
            raise PermissionError("Access denied")
        return inquiry

    # 사용자 자기 문의 목록 조회
    def get_my_inquiries(self, user_email: str) -> List[Inquiry]:
        return self.inquiry_repo.find_by_user_email(user_email)

    # 관리자 전체 문의 조회
    def get_all_inquiries(self, current_user_role: str) -> List[Inquiry]:
        if current_user_role != "ADMIN":
            raise PermissionError("Access denied")
        return self.inquiry_repo.find_all()

    # 답변 작성 (관리자만 가능)
    def answer_inquiry(self, inquiry_id: int, answer: str, current_user_role: str) -> Inquiry:
        if current_user_role != "ADMIN":
            raise PermissionError("Access denied")
        inquiry = self.inquiry_repo.find_by_id(inquiry_id)
        if inquiry is None:
            raise ValueError("Inquiry not found")
        inquiry.answer_inquiry(answer)
        return self.inquiry_repo.update(inquiry)


    # 문의 수정 (USER: 본인만, ADMIN: 전체)
    def update_inquiry(self, inquiry_id: int, title: str, content: str,
                       current_user_email: str, current_user_role: str) -> Inquiry:
        inquiry = self.inquiry_repo.find_by_id(inquiry_id)
        if inquiry is None:
            raise ValueError("Inquiry not found")
        if current_user_role != "ADMIN" and inquiry.user_email != current_user_email:
            raise PermissionError("Access denied")
        inquiry.title = title
        inquiry.content = content
        return self.inquiry_repo.update(inquiry)

    # 문의 삭제 (USER: 본인만, ADMIN: 전체)
    def delete_inquiry(self, inquiry_id: int, current_user_email: str, current_user_role: str) -> None:
        inquiry = self.inquiry_repo.find_by_id(inquiry_id)
        if inquiry is None:
            raise ValueError("Inquiry not found")
        if current_user_role != "ADMIN" and inquiry.user_email != current_user_email:
            raise PermissionError("Access denied")
        self.inquiry_repo.delete(inquiry)