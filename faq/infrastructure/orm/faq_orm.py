from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index
from datetime import datetime
from config.database.session import Base


class FAQ_ORM(Base):
    __tablename__ = 'faq_items'

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    view_count = Column(Integer, default=0, nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index(
            'ft_question_answer',
            question,
            answer,
            # MySQLDialect에서 FULLTEXT를 사용하도록 명시
            mysql_prefix='FULLTEXT',
        )
    ),

    def __repr__(self):
        return f"<FAQ_ORM(id={self.id}, category='{self.category}')>"