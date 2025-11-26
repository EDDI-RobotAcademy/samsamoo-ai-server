from abc import ABC, abstractmethod
from typing import Optional, List

from notice.domain.notice import Notice

class NoticeRepositoryPort(ABC):
    @abstractmethod
    def save(self, notice: Notice) -> Notice:
        """공지사항 저장"""
        pass

    @abstractmethod
    def find_by_id(self, notice_id: int) -> Optional[Notice]:
        """ID로 공지사항 조회"""
        pass

    @abstractmethod
    def find_by_author(self, author_id: str) -> List[Notice]:
        """작성자 ID로 공지사항 목록 조회"""
        pass

    @abstractmethod
    def find_all(self, page: int, size: int) -> List[Notice]:
        """페이징된 전체 공지사항 조회"""
        pass

    @abstractmethod
    def delete(self, notice_id: int) -> None:
        """공지사항 삭제"""
        pass
