from typing import Optional
from datetime import datetime

class Notice:
    def __init__(self, title: str, content: str):
        self.id: Optional[int] = None
        self.title = title
        self.content = content
        self.created_at: datetime = datetime.utcnow()

    @classmethod
    def create(cls, title: str, content: str) -> "Notice":
        if not title:
            raise ValueError("Title cannot be empty")
        if not content:
            raise ValueError("Content cannot be empty")
        return cls(title, content)

    def update(self, title: str, content: str):
        self.title = title
        self.content = content


