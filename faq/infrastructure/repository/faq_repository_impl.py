from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, select

# 설정 및 포트, 도메인, ORM 임포트 (경로는 가정)
from config.database.session import SessionLocal, get_db_session
from faq.application.port.faq_repository_port import FAQRepositoryPort
from faq.domain.faq import FAQItem
from faq.infrastructure.orm.faq_orm import FAQ_ORM


class FAQRepositoryImpl(FAQRepositoryPort):
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

    def increment_view_count(self, faq_id: int) -> None:
        """
        FAQRepositoryPort의 추상 메서드 구현.
        실제 로직은 update_faq에서 처리되므로 여기서는 pass를 사용하거나
        예외를 발생시켜 사용을 방지할 수 있습니다.
        """
        pass

    def _build_filter_sql(self, base_sql: str, params: Dict[str, Any], **kwargs) -> str:
        """find_with_filters와 count_with_filters에서 공통으로 사용되는 SQL 필터 빌더"""
        sql = base_sql

        category = kwargs.get('category')
        query = kwargs.get('query')
        created_from = kwargs.get('created_from')
        created_to = kwargs.get('created_to')
        updated_from = kwargs.get('updated_from')
        updated_to = kwargs.get('updated_to')

        if category:
            sql += " AND category = :category"
            params["category"] = category
        if query:
            sql += " AND (MATCH(question, answer) AGAINST (:keyword IN BOOLEAN MODE))"
            params["keyword"] = query + "*"

        # 등록일 필터
        if created_from:
            sql += " AND created_at >= :created_from"
            params["created_from"] = created_from
        if created_to:
            created_to_next_day = created_to + timedelta(days=1)
            sql += " AND created_at < :created_to_next_day"
            params["created_to_next_day"] = created_to_next_day

        # 수정일 필터
        if updated_from:
            sql += " AND updated_at >= :updated_from"
            params["updated_from"] = updated_from
        if updated_to:
            updated_to_next_day = updated_to + timedelta(days=1)
            sql += " AND updated_at < :updated_to_next_day"
            params["updated_to_next_day"] = updated_to_next_day

        return sql

    # --- Repository Port 메서드 구현 ---

    def save(self, faq_item: FAQItem) -> FAQItem:
        db: Session = SessionLocal()
        try:
            # 💡 [인라인 변환] 도메인 객체 -> ORM 객체
            db_obj = FAQ_ORM(
                id=faq_item.id,
                question=faq_item.question,
                answer=faq_item.answer,
                category=faq_item.category,
                view_count=faq_item.view_count,
                is_published=faq_item.is_published,
                created_at=faq_item.created_at if faq_item.created_at else datetime.utcnow(),
                updated_at=faq_item.updated_at if faq_item.updated_at else datetime.utcnow()
            )

            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)

            # 💡 [인라인 변환] ORM 객체 -> 도메인 객체로 반환
            faq_item.id = db_obj.id
            faq_item.created_at = db_obj.created_at
            faq_item.updated_at = db_obj.updated_at
            # 나머지 필드는 이미 faq_item에 최신 상태로 반영되어 있음

        finally:
            db.close()
        return faq_item

    def find_all(self) -> List[FAQItem]:
        """모든 FAQ 항목 목록을 반환합니다."""
        db: Session = SessionLocal()
        faqs: List[FAQItem] = []
        try:
            stmt = select(FAQ_ORM)
            db_objs = db.execute(stmt).scalars().all()
            for obj in db_objs:
                # 💡 [인라인 변환] ORM 객체 -> 도메인 객체
                item = FAQItem(question=obj.question, answer=obj.answer, category=obj.category)
                item.id = obj.id
                item.view_count = obj.view_count
                item.is_published = obj.is_published
                item.created_at = obj.created_at
                item.updated_at = obj.updated_at
                faqs.append(item)
        finally:
            db.close()
        return faqs

    def find_by_id(self, faq_id: int) -> Optional[FAQItem]:
        """
        특정 ID를 가진 FAQ 항목을 반환합니다. (상세 조회)
        """
        db: Session = SessionLocal()
        try:
            # 💡 [쿼리] 매핑된 FAQ_ORM 사용
            stmt = select(FAQ_ORM).where(FAQ_ORM.id == faq_id)
            db_obj = db.execute(stmt).scalars().first()

            if db_obj is None:
                return None

            # 💡 [인라인 변환] ORM 객체 -> 도메인 객체
            item = FAQItem(question=db_obj.question, answer=db_obj.answer, category=db_obj.category)
            item.id = db_obj.id
            item.view_count = db_obj.view_count
            item.is_published = db_obj.is_published
            item.created_at = db_obj.created_at
            item.updated_at = db_obj.updated_at
            return item
        finally:
            db.close()

    def update_faq(self, faq_item: FAQItem) -> FAQItem:
        """
        FAQ 항목의 변경 사항(주로 view_count)을 DB에 반영하고 업데이트된 항목을 반환합니다.
        """
        db: Session = SessionLocal()
        try:
            # 1. 💡 [인라인 변환] 도메인 객체(view_count가 증가된 상태)를 ORM 객체로 변환
            orm_obj = FAQ_ORM(
                id=faq_item.id,
                question=faq_item.question,
                answer=faq_item.answer,
                category=faq_item.category,
                view_count=faq_item.view_count,
                is_published=faq_item.is_published,
                created_at=faq_item.created_at,
                updated_at=faq_item.updated_at
            )

            # 2. 🚨 핵심 수정: 매핑된 ORM 객체(orm_obj)를 merge에 전달하여 업데이트
            db.merge(orm_obj)
            db.commit()

            # 3. 💡 [인라인 변환] ORM 객체에서 DB 상태를 반영한 최종 도메인 객체 반환
            faq_item.id = orm_obj.id
            faq_item.question = orm_obj.question
            faq_item.answer = orm_obj.answer
            faq_item.category = orm_obj.category
            faq_item.view_count = orm_obj.view_count  # 증가된 값
            faq_item.is_published = orm_obj.is_published
            faq_item.created_at = orm_obj.created_at
            faq_item.updated_at = orm_obj.updated_at  # DB에서 onupdate된 값

            return faq_item

        except Exception as e:
            db.rollback()
            print(f"Error during FAQ update: {e}")
            raise
        finally:
            db.close()

    def count_with_filters(self, **kwargs) -> int:
        db: Session = SessionLocal()
        params = {}
        try:
            base_sql = "SELECT COUNT(id) AS total_count FROM faq_items WHERE 1=1"

            sql = self._build_filter_sql(base_sql, params, **kwargs)

            result = db.execute(text(sql), params).fetchone()
            return result.total_count if result and result.total_count is not None else 0
        finally:
            db.close()

    def find_with_filters(
            self,
            category: Optional[str] = None,
            query: Optional[str] = None,
            created_from: Optional[datetime] = None,
            created_to: Optional[datetime] = None,
            updated_from: Optional[datetime] = None,
            updated_to: Optional[datetime] = None,
            limit: int = 11,
            offset: int = 0
    ) -> List[FAQItem]:
        """
        검색 조건과 LIMIT/OFFSET 정보를 기반으로 FAQ 목록을 조회합니다.
        """
        db: Session = SessionLocal()
        faqs: List[FAQItem] = []
        params = {}

        try:
            base_sql = "SELECT * FROM faq_items WHERE 1=1"

            filter_kwargs = {
                'category': category,
                'query': query,
                'created_from': created_from,
                'created_to': created_to,
                'updated_from': updated_from,
                'updated_to': updated_to,
            }

            sql = self._build_filter_sql(base_sql, params, **filter_kwargs)

            sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset

            result = db.execute(text(sql), params).fetchall()

            for row in result:
                # 💡 [인라인 변환] SQL Row 객체에서 FAQItem 도메인 객체로 직접 매핑
                data = row._asdict() if hasattr(row, '_asdict') else dict(row)

                item = FAQItem(question=data['question'], answer=data['answer'], category=data['category'])
                item.id = data['id']
                item.view_count = data['view_count']
                item.is_published = data['is_published']
                item.created_at = data['created_at']
                item.updated_at = data['updated_at']
                faqs.append(item)

        finally:
            db.close()

        return faqs