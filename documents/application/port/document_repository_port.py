from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from documents.domain.document import Document

class DocumentRepositoryPort(ABC):
    @abstractmethod
    def save(self, document: Document) -> Document:
        pass

    @abstractmethod
    def find_all(self) -> List[Document]:
        pass

    @abstractmethod
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
        pass