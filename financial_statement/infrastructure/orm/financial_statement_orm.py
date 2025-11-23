from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Enum as SQLEnum
from config.database.session import Base
from datetime import datetime
import enum


class StatementTypeEnum(enum.Enum):
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class FinancialStatementORM(Base):
    """SQLAlchemy ORM model for financial statements table"""

    __tablename__ = "financial_statements"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("account.id"), nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    statement_type = Column(SQLEnum(StatementTypeEnum), nullable=False)
    fiscal_year = Column(Integer, nullable=False, index=True)
    fiscal_quarter = Column(Integer, nullable=True)
    s3_key = Column(String(500), nullable=True)
    normalized_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<FinancialStatementORM(id={self.id}, company={self.company_name}, "
            f"type={self.statement_type.value if self.statement_type else None}, "
            f"year={self.fiscal_year})>"
        )
