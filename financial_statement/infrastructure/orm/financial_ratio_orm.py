from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, ForeignKey
from config.database.session import Base
from datetime import datetime


class FinancialRatioORM(Base):
    """SQLAlchemy ORM model for financial ratios table"""

    __tablename__ = "financial_ratios"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    statement_id = Column(Integer, ForeignKey("financial_statements.id"), nullable=False, index=True)
    ratio_type = Column(String(50), nullable=False, index=True)
    ratio_value = Column(DECIMAL(10, 4), nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return (
            f"<FinancialRatioORM(id={self.id}, type={self.ratio_type}, "
            f"value={self.ratio_value}, statement_id={self.statement_id})>"
        )
