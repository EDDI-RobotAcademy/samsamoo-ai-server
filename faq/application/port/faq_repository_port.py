from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from faq.domain.faq import FAQItem  # 도메인 객체 임포트 (포트는 도메인을 의존함)


class FAQRepositoryPort(ABC):
    """
    FAQ 데이터 접근 기능을 정의하는 추상 인터페이스 (Port)

    인프라스트럭처 계층의 Repository 구현체는 반드시 이 인터페이스를 상속받아야 합니다.
    """

    @abstractmethod
    def save(self, faq_item: FAQItem) -> FAQItem:
        """
        FAQ 항목을 저장하거나 업데이트하고, ID가 할당된 FAQItem 객체를 반환합니다.
        """
        pass

    @abstractmethod
    def find_all(self) -> List[FAQItem]:
        """
        모든 FAQ 항목 목록을 반환합니다.
        """
        pass

    @abstractmethod
    def find_by_id(self, faq_id: int) -> Optional[FAQItem]:
        """
        특정 ID를 가진 FAQ 항목을 반환합니다. (상세 조회)
        """
        pass

    @abstractmethod
    def update_faq(self, faq_item: FAQItem) -> FAQItem:
        pass

    @abstractmethod
    def increment_view_count(self, faq_id: int) -> None:
        """
        특정 ID를 가진 FAQ 항목의 조회수를 1 증가시킵니다.
        """
        pass

    @abstractmethod
    def count_with_filters(
            self,
            category: Optional[str] = None,
            query: Optional[str] = None,
            created_from: Optional[datetime] = None,
            created_to: Optional[datetime] = None,
            updated_from: Optional[datetime] = None,
            updated_to: Optional[datetime] = None
    ) -> int:
        """검색 조건에 맞는 FAQ 항목의 총 개수를 반환합니다."""
        pass

    @abstractmethod
    def find_with_filters(
            self,
            category: Optional[str] = None,
            query: Optional[str] = None,
            created_from: Optional[datetime] = None,
            created_to: Optional[datetime] = None,
            updated_from: Optional[datetime] = None,
            updated_to: Optional[datetime] = None,
            # 💡 변경: 무한 스크롤을 위해 limit과 offset을 명시적으로 받습니다.
            limit: int = 11,  # UseCase에서 size + 1로 요청합니다.
            offset: int = 0
    ) -> List[FAQItem]:
        """
        검색 조건과 LIMIT/OFFSET 정보를 기반으로 FAQ 목록을 조회합니다.
        """
        pass