from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey
from config.database.session import Base
from datetime import datetime


class AnalysisReportORM(Base):
    """SQLAlchemy ORM model for analysis reports table"""

    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    statement_id = Column(Integer, ForeignKey("financial_statements.id"), nullable=False, unique=True, index=True)
    kpi_summary = Column(Text, nullable=True)
    statement_table_summary = Column(JSON, nullable=True)
    ratio_analysis = Column(Text, nullable=True)
    report_s3_key = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<AnalysisReportORM(id={self.id}, statement_id={self.statement_id})>"
