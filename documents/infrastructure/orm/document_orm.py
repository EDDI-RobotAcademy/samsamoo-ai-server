from sqlalchemy import Column, Integer, String, DateTime, Index
from datetime import datetime
from config.database.session import Base

class DocumentORM(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    s3_key = Column(String(255), nullable=False)
    uploader_id = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index(
            'idx_file_name_fulltext',
            file_name,
            postgresql_using='gin',
            mysql_prefix='FULLTEXT',
        ),
    )