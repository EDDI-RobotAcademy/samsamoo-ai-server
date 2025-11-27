from typing import List
from notice.domain.notice import Notice

class NoticeUsecase:
    def __init__(self, repository):
        self.repository = repository

    def create_notice(self, title: str, content: str) -> Notice:
        notice = Notice.create(title, content)
        return self.repository.save(notice)

    def get_notice(self, notice_id: int) -> Notice | None:
        notice = self.repository.find_by_id(notice_id)
        if not notice:
            raise ValueError("Notice not found")
        return notice

    def update_notice(self, notice_id: int, title: str | None, content: str | None) -> Notice:
        notice = self.repository.find_by_id(notice_id)
        if not notice:
            raise ValueError("Notice not found")
        notice.update(title, content)
        return self.repository.save(notice)

    def delete_notice(self, notice_id: int) -> bool:
        self.repository.delete(notice_id)
        return True

    def list_notices(self) -> List[Notice]:
        notices, _ = self.repository.find_all()
        return notices
