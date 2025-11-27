from config.database.session import SessionLocal
from notice.domain.notice import Notice

class NoticeRepositoryImpl:

    def __init__(self):
        self.db = SessionLocal()

    def create_notice(self, title, content):
        notice = Notice(title=title, content=content)
        self.db.add(notice)
        self.db.commit()
        self.db.refresh(notice)
        return notice

    def update_notice(self, notice_id, title, content):
        notice = self.db.query(Notice).filter(Notice.id == notice_id).first()
        if not notice:
            return None
        notice.title = title
        notice.content = content
        self.db.commit()
        self.db.refresh(notice)
        return notice

    def delete_notice(self, notice_id):
        notice = self.db.query(Notice).filter(Notice.id == notice_id).first()
        if not notice:
            return False
        self.db.delete(notice)
        self.db.commit()
        return True

    def list_notices(self):
        return self.db.query(Notice).order_by(Notice.created_at.desc()).all()

    def get_notice_by_id(self, notice_id: int):
        return self.db.query(Notice).filter(Notice.id == notice_id).first()
