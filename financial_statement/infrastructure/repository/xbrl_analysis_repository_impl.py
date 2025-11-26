"""
XBRL Analysis Repository Implementation

SQLAlchemy-based implementation of XBRLAnalysisRepositoryPort.
"""
import logging
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from config.database.session import SessionLocal
from financial_statement.application.port.xbrl_analysis_repository_port import XBRLAnalysisRepositoryPort
from financial_statement.domain.xbrl_analysis import XBRLAnalysis, XBRLAnalysisStatus, XBRLSourceType
from financial_statement.infrastructure.orm.xbrl_analysis_orm import XBRLAnalysisORM

logger = logging.getLogger(__name__)


class XBRLAnalysisRepositoryImpl(XBRLAnalysisRepositoryPort):
    """
    SQLAlchemy implementation of XBRL analysis repository.
    """
    
    def __init__(self, session: Session = None):
        """Initialize with optional session for testing"""
        self._session = session
    
    def _get_session(self) -> Session:
        """Get database session"""
        if self._session:
            return self._session
        return SessionLocal()
    
    def _to_domain(self, orm: XBRLAnalysisORM) -> XBRLAnalysis:
        """Convert ORM model to domain entity"""
        return XBRLAnalysis(
            id=orm.id,
            corp_code=orm.corp_code,
            corp_name=orm.corp_name,
            fiscal_year=orm.fiscal_year,
            report_type=orm.report_type,
            user_id=orm.user_id,
            source_type=XBRLSourceType(orm.source_type) if orm.source_type else XBRLSourceType.UPLOAD,
            source_filename=orm.source_filename,
            status=XBRLAnalysisStatus(orm.status) if orm.status else XBRLAnalysisStatus.PENDING,
            financial_data=orm.financial_data or {},
            ratios_data=orm.ratios_data or [],
            executive_summary=orm.executive_summary,
            financial_health=orm.financial_health,
            ratio_analysis=orm.ratio_analysis,
            investment_recommendation=orm.investment_recommendation,
            report_pdf_path=orm.report_pdf_path,
            report_md_path=orm.report_md_path,
            fact_count=orm.fact_count or 0,
            context_count=orm.context_count or 0,
            taxonomy=orm.taxonomy or "kifrs",
            error_message=orm.error_message,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            analyzed_at=orm.analyzed_at,
        )
    
    def _to_orm(self, analysis: XBRLAnalysis) -> XBRLAnalysisORM:
        """Convert domain entity to ORM model"""
        return XBRLAnalysisORM(
            id=analysis.id,
            corp_code=analysis.corp_code,
            corp_name=analysis.corp_name,
            fiscal_year=analysis.fiscal_year,
            report_type=analysis.report_type,
            user_id=analysis.user_id,
            source_type=analysis.source_type.value if isinstance(analysis.source_type, XBRLSourceType) else analysis.source_type,
            source_filename=analysis.source_filename,
            status=analysis.status.value if isinstance(analysis.status, XBRLAnalysisStatus) else analysis.status,
            financial_data=analysis.financial_data,
            ratios_data=analysis.ratios_data,
            executive_summary=analysis.executive_summary,
            financial_health=analysis.financial_health,
            ratio_analysis=analysis.ratio_analysis,
            investment_recommendation=analysis.investment_recommendation,
            report_pdf_path=analysis.report_pdf_path,
            report_md_path=analysis.report_md_path,
            fact_count=analysis.fact_count,
            context_count=analysis.context_count,
            taxonomy=analysis.taxonomy,
            error_message=analysis.error_message,
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
            analyzed_at=analysis.analyzed_at,
        )
    
    def save(self, analysis: XBRLAnalysis) -> XBRLAnalysis:
        """Save or update an XBRL analysis"""
        session = self._get_session()
        try:
            if analysis.id:
                # Update existing
                orm = session.query(XBRLAnalysisORM).filter(
                    XBRLAnalysisORM.id == analysis.id
                ).first()
                
                if orm:
                    orm.corp_code = analysis.corp_code
                    orm.corp_name = analysis.corp_name
                    orm.fiscal_year = analysis.fiscal_year
                    orm.report_type = analysis.report_type
                    orm.user_id = analysis.user_id
                    orm.source_type = analysis.source_type.value if isinstance(analysis.source_type, XBRLSourceType) else analysis.source_type
                    orm.source_filename = analysis.source_filename
                    orm.status = analysis.status.value if isinstance(analysis.status, XBRLAnalysisStatus) else analysis.status
                    orm.financial_data = analysis.financial_data
                    orm.ratios_data = analysis.ratios_data
                    orm.executive_summary = analysis.executive_summary
                    orm.financial_health = analysis.financial_health
                    orm.ratio_analysis = analysis.ratio_analysis
                    orm.investment_recommendation = analysis.investment_recommendation
                    orm.report_pdf_path = analysis.report_pdf_path
                    orm.report_md_path = analysis.report_md_path
                    orm.fact_count = analysis.fact_count
                    orm.context_count = analysis.context_count
                    orm.taxonomy = analysis.taxonomy
                    orm.error_message = analysis.error_message
                    orm.updated_at = datetime.utcnow()
                    orm.analyzed_at = analysis.analyzed_at
                    
                    session.commit()
                    session.refresh(orm)
                    return self._to_domain(orm)
            
            # Create new
            orm = self._to_orm(analysis)
            session.add(orm)
            session.commit()
            session.refresh(orm)
            
            logger.info(f"Saved XBRL analysis: {orm.id} for {orm.corp_name}")
            return self._to_domain(orm)
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save XBRL analysis: {e}")
            raise
        finally:
            if not self._session:
                session.close()
    
    def find_by_id(self, analysis_id: int) -> Optional[XBRLAnalysis]:
        """Find analysis by ID"""
        session = self._get_session()
        try:
            orm = session.query(XBRLAnalysisORM).filter(
                XBRLAnalysisORM.id == analysis_id
            ).first()
            
            return self._to_domain(orm) if orm else None
            
        finally:
            if not self._session:
                session.close()
    
    def find_by_user_id(
        self,
        user_id: int,
        page: int = 1,
        size: int = 10
    ) -> List[XBRLAnalysis]:
        """Find all analyses for a user with pagination"""
        session = self._get_session()
        try:
            offset = (page - 1) * size
            
            orms = session.query(XBRLAnalysisORM).filter(
                XBRLAnalysisORM.user_id == user_id
            ).order_by(
                XBRLAnalysisORM.created_at.desc()
            ).offset(offset).limit(size).all()
            
            return [self._to_domain(orm) for orm in orms]
            
        finally:
            if not self._session:
                session.close()
    
    def find_by_corp_code(
        self,
        corp_code: str,
        fiscal_year: Optional[int] = None
    ) -> List[XBRLAnalysis]:
        """Find analyses by corporation code"""
        session = self._get_session()
        try:
            query = session.query(XBRLAnalysisORM).filter(
                XBRLAnalysisORM.corp_code == corp_code
            )
            
            if fiscal_year:
                query = query.filter(XBRLAnalysisORM.fiscal_year == fiscal_year)
            
            orms = query.order_by(XBRLAnalysisORM.fiscal_year.desc()).all()
            
            return [self._to_domain(orm) for orm in orms]
            
        finally:
            if not self._session:
                session.close()
    
    def count_by_user_id(self, user_id: int) -> int:
        """Count total analyses for a user"""
        session = self._get_session()
        try:
            return session.query(XBRLAnalysisORM).filter(
                XBRLAnalysisORM.user_id == user_id
            ).count()
            
        finally:
            if not self._session:
                session.close()
    
    def delete(self, analysis_id: int) -> bool:
        """Delete an analysis by ID"""
        session = self._get_session()
        try:
            orm = session.query(XBRLAnalysisORM).filter(
                XBRLAnalysisORM.id == analysis_id
            ).first()
            
            if orm:
                session.delete(orm)
                session.commit()
                logger.info(f"Deleted XBRL analysis: {analysis_id}")
                return True
            
            return False
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete XBRL analysis: {e}")
            raise
        finally:
            if not self._session:
                session.close()
    
    def update_status(
        self,
        analysis_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """Update analysis status"""
        session = self._get_session()
        try:
            orm = session.query(XBRLAnalysisORM).filter(
                XBRLAnalysisORM.id == analysis_id
            ).first()
            
            if orm:
                orm.status = status
                orm.error_message = error_message
                orm.updated_at = datetime.utcnow()
                
                if status == "completed":
                    orm.analyzed_at = datetime.utcnow()
                
                session.commit()
                logger.info(f"Updated XBRL analysis {analysis_id} status to {status}")
                return True
            
            return False
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update XBRL analysis status: {e}")
            raise
        finally:
            if not self._session:
                session.close()
