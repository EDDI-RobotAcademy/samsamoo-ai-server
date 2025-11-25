from typing import Optional
from datetime import datetime


class FAQItem:
    def __init__(self, question: str, answer: str, category: str):
        self.id: Optional[int] = None
        self.question = question
        self.answer = answer
        self.category = category
        self.view_count: int = 0
        self.is_published: bool = True
        self.created_at: datetime = datetime.utcnow()
        self.updated_at: datetime = datetime.utcnow()

    @classmethod
    def create(cls, question: str, answer: str, category: str) -> "FAQItem":
        if not question:
            raise ValueError("Question cannot be empty")
        if not answer:
            raise ValueError("Answer cannot be empty")
        if not category:
            raise ValueError("Category cannot be empty")
        return cls(question, answer, category)

    def update(self, question: Optional[str] = None, answer: Optional[str] = None, category: Optional[str] = None):
        # 업데이트 로직 (위의 2-B 내용)
        is_updated = False

        if question is not None:
            if not question:
                raise ValueError("Question cannot be empty")
            self.question = question
            is_updated = True

        if answer is not None:
            if not answer:
                raise ValueError("Answer cannot be empty")
            self.answer = answer
            is_updated = True

        if category is not None:
            if not category:
                raise ValueError("Category cannot be empty")
            self.category = category
            is_updated = True

        if is_updated:
            self.updated_at = datetime.utcnow()

    def increment_view_count(self):
        self.view_count += 1

    def toggle_publication_status(self):
        self.is_published = not self.is_published
        self.updated_at = datetime.utcnow()