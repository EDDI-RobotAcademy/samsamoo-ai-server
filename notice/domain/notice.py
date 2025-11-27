from sqlalchemy import Column, Integer, String, DateTime
from config.database.session import Base
from datetime import datetime

class Notice(Base):
    __tablename__ = "notice"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    content = Column(String(2000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
