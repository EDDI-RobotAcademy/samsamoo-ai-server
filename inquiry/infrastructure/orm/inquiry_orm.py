from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from config.database.session import Base

class InquiryStatus(str, enum.Enum):
    WAIT = "WAIT"
    ANSWERED = "ANSWERED"

class InquiryORM(Base):
    __tablename__ = "inquiry"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(String(2000), nullable=False)
    answer = Column(String(2000), nullable=True)

    status = Column(Enum(InquiryStatus), default=InquiryStatus.WAIT, nullable=False)

    # 사용자 연결 (email 기준)
    user_email = Column(String(255), ForeignKey("account.email"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 정의 (optional)
    user = relationship("AccountORM", backref="inquiries", primaryjoin="InquiryORM.user_email == AccountORM.email")
