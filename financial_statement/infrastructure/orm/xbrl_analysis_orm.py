"""
XBRL Analysis ORM Model

SQLAlchemy model for persisting XBRL analysis results.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from config.database.session import Base
from financial_statement.domain.xbrl_analysis import XBRLAnalysisStatus, XBRLSourceType


class XBRLAnalysisORM(Base):
    """
    SQLAlchemy ORM model for XBRL analysis records.
    
    Stores the complete XBRL analysis including:
    - Corporation identification
    - Extracted financial data
    - Calculated ratios
    - LLM analysis results
    - Report file paths
    """
    
    __tablename__ = "xbrl_analyses"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Corporation identification
    corp_code = Column(String(20), nullable=False, index=True)
    corp_name = Column(String(200), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    report_type = Column(String(20), default="annual")  # annual, semi_annual, quarterly
    
    # User ownership
    user_id = Column(Integer, nullable=True, index=True)
    
    # Source information
    source_type = Column(String(20), default="upload")  # upload, dart
    source_filename = Column(String(500), nullable=True)
    
    # Status tracking
    status = Column(String(20), default="pending", index=True)
    
    # Financial data (JSON)
    financial_data = Column(JSON, nullable=True)
    ratios_data = Column(JSON, nullable=True)
    
    # LLM analysis results
    executive_summary = Column(Text, nullable=True)
    financial_health = Column(JSON, nullable=True)
    ratio_analysis = Column(Text, nullable=True)
    investment_recommendation = Column(JSON, nullable=True)
    
    # Report paths
    report_pdf_path = Column(String(500), nullable=True)
    report_md_path = Column(String(500), nullable=True)
    
    # Metadata
    fact_count = Column(Integer, default=0)
    context_count = Column(Integer, default=0)
    taxonomy = Column(String(50), default="kifrs")
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    analyzed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<XBRLAnalysis(id={self.id}, corp_name='{self.corp_name}', fiscal_year={self.fiscal_year}, status='{self.status}')>"
