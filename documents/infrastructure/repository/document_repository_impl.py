from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from config.database.session import SessionLocal
from documents.application.port.document_repository_port import DocumentRepositoryPort
from documents.domain.document import Document
from documents.infrastructure.orm.document_orm import DocumentORM


class DocumentRepositoryImpl(DocumentRepositoryPort):
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    @classmethod
    def getInstance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def save(self, document: Document) -> Document:

        db: Session = SessionLocal()
        try:
            db_obj = DocumentORM(
                file_name=document.file_name,
                s3_key=document.s3_key,
                uploader_id=document.uploader_id,
            )
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            # DB에서 받은 id와 timestamp를 도메인 객체에 반영
            document.id = db_obj.id
            document.uploaded_at = db_obj.uploaded_at
            document.updated_at = db_obj.updated_at
        finally:
            db.close()

        return document

    def find_all(self) -> List[Document]:
        """
        DB에 있는 모든 문서를 도메인 객체로 반환
        """
        db: Session = SessionLocal()
        documents: List[Document] = []
        try:
            db_objs = db.query(DocumentORM).all()
            for obj in db_objs:
                doc = Document(
                    file_name=obj.file_name,
                    s3_key=obj.s3_key,
                    uploader_id=obj.uploader_id
                )
                doc.id = obj.id
                doc.uploaded_at = obj.uploaded_at
                doc.updated_at = obj.updated_at
                documents.append(doc)
        finally:
            db.close()

        return documents

    def find_with_filters(
            self,
            id: Optional[int] = None,
            file_name: Optional[str] = None,
            uploaded_from: Optional[datetime] = None,
            uploaded_to: Optional[datetime] = None,
            updated_from: Optional[datetime] = None,
            updated_to: Optional[datetime] = None,
            page: int = 1,
            size: int = 10
    ) -> List[Document]:
        db: Session = SessionLocal()
        documents: List[Document] = []

        try:
            offset = (page - 1) * size

            sql = "SELECT * FROM documents WHERE 1=1"
            params = {}

            # Full-Text 검색
            if file_name:
                sql += " AND MATCH(file_name) AGAINST (:keyword IN BOOLEAN MODE)"
                params["keyword"] = file_name + "*"

            # 업로드 날짜 필터
            if uploaded_from:
                sql += " AND uploaded_at >= :uploaded_from"
                params["uploaded_from"] = uploaded_from
            if uploaded_to:
                # 1. 1일을 더하여 다음 날 00:00:00를 경계로 설정
                uploaded_to_next_day = uploaded_to + timedelta(days=1)

                # 2. SQL 조건은 '미만'으로 변경
                sql += " AND uploaded_at < :uploaded_to_next_day"
                params["uploaded_to_next_day"] = uploaded_to_next_day

            # 수정 날짜 필터
            if updated_from:
                sql += " AND updated_at >= :updated_from"
                params["updated_from"] = updated_from
            if updated_to:
                # 1. 1일을 더하여 다음 날 00:00:00를 경계로 설정
                updated_to_next_day = updated_to + timedelta(days=1)

                # 2. SQL 조건은 '미만'으로 변경
                sql += " AND updated_at < :updated_to_next_day"
                params["uploaded_to_next_day"] = updated_to_next_day

            # 페이징
            sql += " LIMIT :size OFFSET :offset"
            params["size"] = size
            params["offset"] = offset

            db_objs = db.execute(text(sql), params).fetchall()

            for obj in db_objs:
                doc = Document(
                    file_name=obj.file_name,
                    s3_key=obj.s3_key,
                    uploader_id=obj.uploader_id
                )
                doc.id = obj.id
                doc.uploaded_at = obj.uploaded_at
                doc.updated_at = obj.updated_at
                documents.append(doc)

        finally:
            db.close()

        return documents

