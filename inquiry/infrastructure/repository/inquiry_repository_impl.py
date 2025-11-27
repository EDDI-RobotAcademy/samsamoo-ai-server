from typing import List, Optional

from config.database.session import get_db_session, SessionLocal
from inquiry.application.port.inquiry_repository_port import InquiryRepositoryPort
from inquiry.domain.inquiry import Inquiry, InquiryStatusEnum
from inquiry.infrastructure.orm.inquiry_orm import InquiryORM
from sqlalchemy.orm import Session


class InquiryRepositoryImpl(InquiryRepositoryPort):
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)

        return cls.__instance

    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def __init__(self):
        if not hasattr(self, 'db'):
            self.db: Session = get_db_session()

    def save(self, inquiry: Inquiry) -> Inquiry:
        db: Session = SessionLocal()
        try:
            orm_inquiry = InquiryORM(
                title=inquiry.title,
                content=inquiry.content,
                user_email=inquiry.user_email,
                status=inquiry.status.value
            )
            db.add(orm_inquiry)
            db.commit()
            db.refresh(orm_inquiry)

            inquiry.id = orm_inquiry.id
            inquiry.created_at = orm_inquiry.created_at
            inquiry.updated_at = orm_inquiry.updated_at
        finally:
            db.close()
        return inquiry

    def find_by_id(self, inquiry_id: int) -> Optional[Inquiry]:
        db: Session = SessionLocal()
        try:
            orm_inquiry = db.query(InquiryORM).filter(InquiryORM.id == inquiry_id).first()
            if orm_inquiry is None:
                return None
            inquiry = Inquiry(
                title=orm_inquiry.title,
                content=orm_inquiry.content,
                user_email=orm_inquiry.user_email,
                status=InquiryStatusEnum(orm_inquiry.status)
            )
            inquiry.id = orm_inquiry.id
            inquiry.answer = orm_inquiry.answer
            inquiry.created_at = orm_inquiry.created_at
            inquiry.updated_at = orm_inquiry.updated_at
            return inquiry
        finally:
            db.close()

    def find_by_user_email(self, user_email: str) -> List[Inquiry]:
        db: Session = SessionLocal()
        try:
            orm_list = db.query(InquiryORM).filter(InquiryORM.user_email == user_email).all()
            inquiries: List[Inquiry] = []
            for o in orm_list:
                i = Inquiry(
                    title=o.title,
                    content=o.content,
                    user_email=o.user_email,
                    status=InquiryStatusEnum(o.status)
                )
                i.id = o.id
                i.answer = o.answer
                i.created_at = o.created_at
                i.updated_at = o.updated_at
                inquiries.append(i)
            return inquiries
        finally:
            db.close()

    def find_all(self) -> List[Inquiry]:
        db: Session = SessionLocal()
        try:
            orm_list = db.query(InquiryORM).all()
            inquiries: List[Inquiry] = []
            for o in orm_list:
                i = Inquiry(
                    title=o.title,
                    content=o.content,
                    user_email=o.user_email,
                    status=InquiryStatusEnum(o.status)
                )
                i.id = o.id
                i.answer = o.answer
                i.created_at = o.created_at
                i.updated_at = o.updated_at
                inquiries.append(i)
            return inquiries
        finally:
            db.close()

    def update(self, inquiry: Inquiry) -> Inquiry:
        db: Session = SessionLocal()
        try:
            orm_inquiry = db.query(InquiryORM).filter(InquiryORM.id == inquiry.id).first()
            if orm_inquiry is None:
                raise ValueError("Inquiry not found")

            orm_inquiry.title = inquiry.title
            orm_inquiry.content = inquiry.content
            orm_inquiry.answer = inquiry.answer
            orm_inquiry.status = inquiry.status.value
            db.commit()
            db.refresh(orm_inquiry)

            inquiry.updated_at = orm_inquiry.updated_at
            return inquiry
        finally:
            db.close()

    def delete(self, inquiry: Inquiry):
        db: Session = SessionLocal()
        try:
            # 실제 ORM 객체 조회
            orm_inquiry = db.query(InquiryORM).filter(InquiryORM.id == inquiry.id).first()
            if orm_inquiry is None:
                raise ValueError("Inquiry not found")

            db.delete(orm_inquiry)
            db.commit()
        finally:
            db.close()
