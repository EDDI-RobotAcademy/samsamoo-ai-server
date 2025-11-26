"""
XBRL Analysis Domain Entity

Domain entity for XBRL-based financial analysis results.
Mirrors the structure of FinancialStatement but for XBRL data.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class XBRLAnalysisStatus(str, Enum):
    """Status of XBRL analysis workflow"""
    PENDING = "pending"               # Created, waiting for analysis
    EXTRACTING = "extracting"         # Extracting data from XBRL
    CALCULATING = "calculating"       # Calculating financial ratios
    ANALYZING = "analyzing"           # LLM analysis in progress
    GENERATING_REPORT = "generating"  # Report generation
    COMPLETED = "completed"           # Analysis complete
    FAILED = "failed"                 # Analysis failed


class XBRLSourceType(str, Enum):
    """Source of XBRL data"""
    UPLOAD = "upload"      # User uploaded file
    DART = "dart"          # Fetched from DART API


@dataclass
class XBRLAnalysis:
    """
    Domain entity representing an XBRL financial analysis.
    
    Stores the complete analysis workflow result including:
    - Corporation information
    - Extracted financial data
    - Calculated ratios
    - LLM analysis results
    - Generated reports
    """
    
    # Core identification
    corp_code: str
    corp_name: str
    fiscal_year: int
    report_type: str = "annual"  # annual, semi_annual, quarterly
    
    # User and ownership
    user_id: Optional[int] = None
    
    # Source information
    source_type: XBRLSourceType = XBRLSourceType.UPLOAD
    source_filename: Optional[str] = None
    
    # Status tracking
    status: XBRLAnalysisStatus = XBRLAnalysisStatus.PENDING
    
    # Extracted data
    financial_data: Dict[str, Any] = field(default_factory=dict)
    ratios_data: List[Dict[str, Any]] = field(default_factory=list)
    
    # LLM analysis results
    executive_summary: Optional[str] = None
    financial_health: Optional[Dict[str, Any]] = None
    ratio_analysis: Optional[str] = None
    investment_recommendation: Optional[Dict[str, Any]] = None
    
    # Report paths
    report_pdf_path: Optional[str] = None
    report_md_path: Optional[str] = None
    
    # Metadata
    fact_count: int = 0
    context_count: int = 0
    taxonomy: str = "kifrs"
    
    # Timestamps
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    analyzed_at: Optional[datetime] = None
    
    # Error tracking
    error_message: Optional[str] = None
    
    def is_complete(self) -> bool:
        """Check if analysis is complete"""
        return self.status == XBRLAnalysisStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if analysis failed"""
        return self.status == XBRLAnalysisStatus.FAILED
    
    def has_llm_analysis(self) -> bool:
        """Check if LLM analysis was performed"""
        return bool(self.executive_summary or self.ratio_analysis)
    
    def has_reports(self) -> bool:
        """Check if reports were generated"""
        return bool(self.report_pdf_path or self.report_md_path)
    
    def set_status(self, status: XBRLAnalysisStatus) -> None:
        """Update status and timestamp"""
        self.status = status
        self.updated_at = datetime.utcnow()
        if status == XBRLAnalysisStatus.COMPLETED:
            self.analyzed_at = datetime.utcnow()
    
    def set_financial_data(self, data: Dict[str, Any]) -> None:
        """Set extracted financial data"""
        self.financial_data = data
        self.updated_at = datetime.utcnow()
    
    def set_ratios(self, ratios: List[Dict[str, Any]]) -> None:
        """Set calculated ratios"""
        self.ratios_data = ratios
        self.updated_at = datetime.utcnow()
    
    def set_llm_analysis(
        self,
        executive_summary: Optional[str] = None,
        financial_health: Optional[Dict[str, Any]] = None,
        ratio_analysis: Optional[str] = None,
        investment_recommendation: Optional[Dict[str, Any]] = None
    ) -> None:
        """Set LLM analysis results"""
        if executive_summary:
            self.executive_summary = executive_summary
        if financial_health:
            self.financial_health = financial_health
        if ratio_analysis:
            self.ratio_analysis = ratio_analysis
        if investment_recommendation:
            self.investment_recommendation = investment_recommendation
        self.updated_at = datetime.utcnow()
    
    def set_report_paths(
        self,
        pdf_path: Optional[str] = None,
        md_path: Optional[str] = None
    ) -> None:
        """Set generated report paths"""
        if pdf_path:
            self.report_pdf_path = pdf_path
        if md_path:
            self.report_md_path = md_path
        self.updated_at = datetime.utcnow()
    
    def set_error(self, message: str) -> None:
        """Set error state"""
        self.status = XBRLAnalysisStatus.FAILED
        self.error_message = message
        self.updated_at = datetime.utcnow()
    
    def set_metadata(self, fact_count: int, context_count: int, taxonomy: str = "kifrs") -> None:
        """Set XBRL metadata"""
        self.fact_count = fact_count
        self.context_count = context_count
        self.taxonomy = taxonomy
        self.updated_at = datetime.utcnow()
    
    def get_balance_sheet(self) -> Dict[str, Any]:
        """Get balance sheet data"""
        return self.financial_data.get('balance_sheet', {})
    
    def get_income_statement(self) -> Dict[str, Any]:
        """Get income statement data"""
        return self.financial_data.get('income_statement', {})
    
    def get_cash_flow(self) -> Dict[str, Any]:
        """Get cash flow statement data"""
        return self.financial_data.get('cash_flow_statement', {}) or self.financial_data.get('cash_flow', {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'corp_code': self.corp_code,
            'corp_name': self.corp_name,
            'fiscal_year': self.fiscal_year,
            'report_type': self.report_type,
            'user_id': self.user_id,
            'source_type': self.source_type.value if isinstance(self.source_type, XBRLSourceType) else self.source_type,
            'source_filename': self.source_filename,
            'status': self.status.value if isinstance(self.status, XBRLAnalysisStatus) else self.status,
            'financial_data': self.financial_data,
            'ratios': self.ratios_data,
            'analysis': {
                'executive_summary': self.executive_summary,
                'financial_health': self.financial_health,
                'ratio_analysis': self.ratio_analysis,
                'investment_recommendation': self.investment_recommendation,
            } if self.has_llm_analysis() else None,
            'reports': {
                'pdf_path': self.report_pdf_path,
                'md_path': self.report_md_path,
            } if self.has_reports() else None,
            'metadata': {
                'fact_count': self.fact_count,
                'context_count': self.context_count,
                'taxonomy': self.taxonomy,
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'error_message': self.error_message,
        }
