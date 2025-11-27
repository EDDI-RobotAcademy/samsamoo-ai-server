from typing import List, Tuple
from notice.domain.notice import Notice
from notice.infrastructure.orm.notice_orm import NoticeORM
from config.database.session import SessionLocal
from sqlalchemy import func


class NoticeRepositoryImpl:
    def __init__(self):
        self.db = SessionLocal()

    def save(self, notice: Notice) -> Notice:
        if notice.id is None:
            orm = NoticeORM(title=notice.title, content=notice.content)
            self.db.add(orm)
            self.db.commit()
            self.db.refresh(orm)
            notice.id = orm.id
            notice.created_at = orm.created_at
        else:
            orm = self.db.get(NoticeORM, notice.id)
            if not orm:
                raise ValueError("Notice not found")
            orm.title = notice.title
            orm.content = notice.content
            self.db.commit()
            self.db.refresh(orm)
        return notice

    def find_by_id(self, notice_id: int) -> Notice | None:
        orm = self.db.get(NoticeORM, notice_id)
        if not orm:
            return None
        n = Notice(title=orm.title, content=orm.content)
        n.id = orm.id
        n.created_at = orm.created_at
        return n

    def delete(self, notice_id: int):
        orm = self.db.get(NoticeORM, notice_id)
        if orm:
            self.db.delete(orm)
            self.db.commit()

    def find_all(self, page: int = 1, size: int = 1000) -> tuple[list[Notice], int]:
        try:
            # ORM 모델로 query
            query = self.db.query(NoticeORM).order_by(NoticeORM.created_at.desc())

            # 페이징 적용
            orm_list = query.offset((page - 1) * size).limit(size).all()

            # total count
            total = self.db.query(func.count(NoticeORM.id)).scalar()

            # ORM -> 도메인 변환
            notices = []
            for o in orm_list:
                notice = Notice(o.title, o.content)
                notice.id = o.id
                notice.created_at = o.created_at
                notices.append(notice)

            return notices, total

        except Exception as e:
            self.db.rollback()
            raise e
