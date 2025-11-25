from typing import List, Tuple

from faq.domain.faq import FAQItem
from faq.infrastructure.repository.faq_repository_impl import FAQRepositoryImpl


class FAQUseCase:
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.faq_repo = FAQRepositoryImpl.get_instance()
        return cls.__instance

    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def get_faq_detail(self, faq_id: int) -> FAQItem:
        """
        FAQ 항목을 ID로 조회하고, 조회수를 1 증가시킨 후 업데이트된 항목을 반환합니다.
        """
        # 1. 항목 조회 (ID 기반)
        # find_by_id는 Repository에 이미 정의되어 있어야 합니다.
        faq_item = self.faq_repo.find_by_id(faq_id)

        if not faq_item:
            # 항목이 없는 경우 예외를 발생시킵니다.
            # 이 예외는 라우터에서 404로 변환됩니다.
            # 실제 예외 경로는 프로젝트 구조에 따라 다를 수 있습니다.
            raise Exception(f"FAQ ID {faq_id} not found")

            # 2. 조회수 증가
        faq_item.view_count += 1

        # 3. 업데이트 (조회수 증가분 반영)
        # update_faq는 Repository에 정의되어 있어야 합니다.
        updated_faq_item = self.faq_repo.update_faq(faq_item)

        return updated_faq_item

    def register_faq(self, question: str, answer: str, category: str) -> FAQItem:
        faq = FAQItem.create(question, answer, category)
        return self.faq_repo.save(faq)

    def list_faqs(self) -> List[FAQItem]:
        return self.faq_repo.find_all()

    def count_faqs(self, **kwargs) -> int:
        """검색 조건에 맞는 FAQ 항목의 총 개수를 반환합니다."""
        return self.faq_repo.count_with_filters(**kwargs)

    # 🚨 수정: 반환 타입을 (List[FAQItem], bool)로 변경 및 무한 스크롤 로직 적용
    def search_faqs(self, **kwargs) -> Tuple[List[FAQItem], bool]:
        """
        검색 조건과 무한 스크롤을 위해 size + 1만큼 항목을 조회합니다.
        (category, query, created_from, ..., page, size 등의 인수를 받음)
        """
        # 1. 요청된 page와 size를 추출 (기본값 설정)
        # 💡 pop()을 사용하여 kwargs에서 해당 키를 제거하면, Repository에 잘못 전달되는 것을 방지합니다.
        page = kwargs.pop('page', 0)
        size = kwargs.pop('size', 10)

        # 2. Repository에 전달할 offset과 limit을 계산합니다.

        # 2-A. OFFSET 계산: Use Case에서 page를 사용하는 부분 (경고 해결)
        offset = page * size

        # 2-B. LIMIT 계산: size + 1 (다음 페이지 존재 여부 확인용)
        limit = size + 1

        # 3. Repository에 전달할 인자 딕셔너리 준비
        # kwargs는 이제 page와 size가 제거된 순수 필터 조건만 남아있습니다.
        repo_kwargs = {
            **kwargs,
            'limit': limit,  # 💡 Repository Port의 매개변수와 일치
            'offset': offset  # 💡 Repository Port의 매개변수와 일치
        }

        # 4. Repository 호출 (limit=size+1, offset=page*size 전달)
        items_with_extra: List[FAQItem] = self.faq_repo.find_with_filters(**repo_kwargs)

        # 5. has_next 판별: 조회된 항목 수가 요청된 size보다 크면 다음 페이지가 존재함
        has_next = len(items_with_extra) > size

        # 6. 응답할 FAQ 항목 리스트 (요청된 size만큼만 슬라이싱)
        faq_items = items_with_extra[:size]

        # 7. (항목 리스트, 다음 페이지 존재 여부) 반환
        return faq_items, has_next