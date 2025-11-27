from sqlalchemy import Column, BigInteger, String, Text, DateTime, func
from config.database.session import Base

class NoticeORM(Base):
    __tablename__ = "notice"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
