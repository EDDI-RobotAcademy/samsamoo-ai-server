from abc import ABC, abstractmethod
from typing import List, Optional

from inquiry.domain.inquiry import Inquiry


class InquiryRepositoryPort(ABC):
    @abstractmethod
    def save(self, inquiry: Inquiry) -> Inquiry:
        pass

    @abstractmethod
    def find_by_id(self, inquiry_id: int) -> Optional[Inquiry]:
        pass

    @abstractmethod
    def find_by_user_email(self, user_email: str) -> List[Inquiry]:
        pass

    @abstractmethod
    def find_all(self) -> List[Inquiry]:
        pass

    @abstractmethod
    def update(self, inquiry: Inquiry) -> Inquiry:
        pass

    @abstractmethod
    def delete(self, inquiry):
        pass