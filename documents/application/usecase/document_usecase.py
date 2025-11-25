from datetime import datetime
from typing import List, Optional
from documents.domain.document import Document
from documents.infrastructure.repository.document_repository_impl import DocumentRepositoryImpl


class DocumentUseCase:
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.repository = DocumentRepositoryImpl.getInstance()

        return cls.__instance

    @classmethod
    def getInstance(cls):
        if cls.__instance is None:
            cls.__instance = cls()

        return cls.__instance

    def register_document(self, file_name: str, s3_key: str, uploader_id: int) -> Document:
        doc = Document.create(file_name, s3_key, uploader_id)
        return self.repository.save(doc)

    def list_documents(self) -> List[Document]:
        return self.repository.find_all()

    def search_documents(
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
        return self.repository.find_with_filters(
            id=id,
            file_name=file_name,
            uploaded_from=uploaded_from,
            uploaded_to=uploaded_to,
            updated_from=updated_from,
            updated_to=updated_to,
            page=page,
            size=size
        )
