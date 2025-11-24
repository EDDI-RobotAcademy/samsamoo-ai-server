from typing import Optional, List
import logging
from decimal import Decimal
from config.database.session import SessionLocal
from financial_statement.application.port.financial_repository_port import FinancialRepositoryPort
from financial_statement.domain.financial_statement import FinancialStatement, StatementType
from financial_statement.domain.financial_ratio import FinancialRatio
from financial_statement.domain.analysis_report import AnalysisReport
from financial_statement.infrastructure.orm.financial_statement_orm import FinancialStatementORM, StatementTypeEnum
from financial_statement.infrastructure.orm.financial_ratio_orm import FinancialRatioORM
from financial_statement.infrastructure.orm.analysis_report_orm import AnalysisReportORM

logger = logging.getLogger(__name__)


class FinancialRepositoryImpl(FinancialRepositoryPort):
    """
    Implementation of financial repository using SQLAlchemy.
    Handles mapping between domain entities and ORM models.
    """

    def __init__(self):
        self.db = SessionLocal()

    def save_statement(self, statement: FinancialStatement) -> FinancialStatement:
        """Save or update a financial statement"""
        try:
            if statement.id is None:
                # Create new
                orm = FinancialStatementORM(
                    user_id=statement.user_id,
                    company_name=statement.company_name,
                    statement_type=StatementTypeEnum[statement.statement_type.name],
                    fiscal_year=statement.fiscal_year,
                    fiscal_quarter=statement.fiscal_quarter,
                    s3_key=statement.s3_key,
                    normalized_data=statement.normalized_data,
                    created_at=statement.created_at,
                    updated_at=statement.updated_at
                )
                self.db.add(orm)
                self.db.commit()
                self.db.refresh(orm)

                statement.id = orm.id
                logger.info(f"Created financial statement with ID: {statement.id}")
            else:
                # Update existing
                orm = self.db.query(FinancialStatementORM).filter(
                    FinancialStatementORM.id == statement.id
                ).first()

                if orm:
                    orm.company_name = statement.company_name
                    orm.statement_type = StatementTypeEnum[statement.statement_type.name]
                    orm.fiscal_year = statement.fiscal_year
                    orm.fiscal_quarter = statement.fiscal_quarter
                    orm.s3_key = statement.s3_key
                    orm.normalized_data = statement.normalized_data
                    orm.updated_at = statement.updated_at

                    self.db.commit()
                    logger.info(f"Updated financial statement ID: {statement.id}")

            return statement

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save financial statement: {e}")
            raise

    def find_statement_by_id(self, statement_id: int) -> Optional[FinancialStatement]:
        """Find a financial statement by ID"""
        try:
            orm = self.db.query(FinancialStatementORM).filter(
                FinancialStatementORM.id == statement_id
            ).first()

            if not orm:
                return None

            return self._orm_to_statement(orm)

        except Exception as e:
            logger.error(f"Failed to find statement by ID {statement_id}: {e}")
            raise

    def find_statements_by_user_id(
        self,
        user_id: int,
        page: int = 1,
        size: int = 10
    ) -> List[FinancialStatement]:
        """Find all financial statements for a user with pagination"""
        try:
            offset = (page - 1) * size

            orms = self.db.query(FinancialStatementORM).filter(
                FinancialStatementORM.user_id == user_id
            ).order_by(
                FinancialStatementORM.fiscal_year.desc(),
                FinancialStatementORM.fiscal_quarter.desc()
            ).offset(offset).limit(size).all()

            statements = [self._orm_to_statement(orm) for orm in orms]
            logger.info(f"Found {len(statements)} statements for user {user_id}")

            return statements

        except Exception as e:
            logger.error(f"Failed to find statements for user {user_id}: {e}")
            raise

    def delete_statement(self, statement_id: int) -> bool:
        """Delete a financial statement"""
        try:
            # Delete associated ratios and report first
            self.db.query(FinancialRatioORM).filter(
                FinancialRatioORM.statement_id == statement_id
            ).delete()

            self.db.query(AnalysisReportORM).filter(
                AnalysisReportORM.statement_id == statement_id
            ).delete()

            # Delete statement
            deleted_count = self.db.query(FinancialStatementORM).filter(
                FinancialStatementORM.id == statement_id
            ).delete()

            self.db.commit()

            if deleted_count > 0:
                logger.info(f"Deleted financial statement ID: {statement_id}")
                return True
            else:
                logger.warning(f"Financial statement ID {statement_id} not found for deletion")
                return False

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete statement {statement_id}: {e}")
            raise

    def save_ratios(self, ratios: List[FinancialRatio]) -> List[FinancialRatio]:
        """Save multiple financial ratios"""
        try:
            for ratio in ratios:
                if ratio.id is None:
                    # Create new
                    orm = FinancialRatioORM(
                        statement_id=ratio.statement_id,
                        ratio_type=ratio.ratio_type,
                        ratio_value=ratio.ratio_value,
                        calculated_at=ratio.calculated_at
                    )
                    self.db.add(orm)
                    self.db.flush()  # Get ID without committing
                    ratio.id = orm.id

            self.db.commit()
            logger.info(f"Saved {len(ratios)} financial ratios")

            return ratios

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save ratios: {e}")
            raise

    def find_ratios_by_statement_id(self, statement_id: int) -> List[FinancialRatio]:
        """Find all ratios for a financial statement"""
        try:
            orms = self.db.query(FinancialRatioORM).filter(
                FinancialRatioORM.statement_id == statement_id
            ).all()

            ratios = [self._orm_to_ratio(orm) for orm in orms]
            logger.info(f"Found {len(ratios)} ratios for statement {statement_id}")

            return ratios

        except Exception as e:
            logger.error(f"Failed to find ratios for statement {statement_id}: {e}")
            raise

    def save_report(self, report: AnalysisReport) -> AnalysisReport:
        """Save or update an analysis report"""
        try:
            if report.id is None:
                # Create new
                orm = AnalysisReportORM(
                    statement_id=report.statement_id,
                    kpi_summary=report.kpi_summary,
                    statement_table_summary=report.statement_table_summary,
                    ratio_analysis=report.ratio_analysis,
                    report_s3_key=report.report_s3_key,
                    created_at=report.created_at
                )
                self.db.add(orm)
                self.db.commit()
                self.db.refresh(orm)

                report.id = orm.id
                logger.info(f"Created analysis report with ID: {report.id}")
            else:
                # Update existing
                orm = self.db.query(AnalysisReportORM).filter(
                    AnalysisReportORM.id == report.id
                ).first()

                if orm:
                    orm.kpi_summary = report.kpi_summary
                    orm.statement_table_summary = report.statement_table_summary
                    orm.ratio_analysis = report.ratio_analysis
                    orm.report_s3_key = report.report_s3_key

                    self.db.commit()
                    logger.info(f"Updated analysis report ID: {report.id}")

            return report

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save analysis report: {e}")
            raise

    def find_report_by_statement_id(self, statement_id: int) -> Optional[AnalysisReport]:
        """Find analysis report for a financial statement"""
        try:
            orm = self.db.query(AnalysisReportORM).filter(
                AnalysisReportORM.statement_id == statement_id
            ).first()

            if not orm:
                return None

            return self._orm_to_report(orm)

        except Exception as e:
            logger.error(f"Failed to find report for statement {statement_id}: {e}")
            raise

    def delete_report(self, report_id: int) -> bool:
        """Delete an analysis report"""
        try:
            deleted_count = self.db.query(AnalysisReportORM).filter(
                AnalysisReportORM.id == report_id
            ).delete()

            self.db.commit()

            if deleted_count > 0:
                logger.info(f"Deleted analysis report ID: {report_id}")
                return True
            else:
                logger.warning(f"Analysis report ID {report_id} not found for deletion")
                return False

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete report {report_id}: {e}")
            raise

    def _orm_to_statement(self, orm: FinancialStatementORM) -> FinancialStatement:
        """Convert ORM model to domain entity"""
        statement = FinancialStatement(
            company_name=orm.company_name,
            statement_type=StatementType[orm.statement_type.name],
            fiscal_year=orm.fiscal_year,
            fiscal_quarter=orm.fiscal_quarter,
            user_id=orm.user_id
        )

        statement.id = orm.id
        statement.s3_key = orm.s3_key
        statement.normalized_data = orm.normalized_data
        statement.created_at = orm.created_at
        statement.updated_at = orm.updated_at

        return statement

    def _orm_to_ratio(self, orm: FinancialRatioORM) -> FinancialRatio:
        """Convert ORM model to domain entity"""
        ratio = FinancialRatio(
            statement_id=orm.statement_id,
            ratio_type=orm.ratio_type,
            ratio_value=Decimal(str(orm.ratio_value))
        )

        ratio.id = orm.id
        ratio.calculated_at = orm.calculated_at

        return ratio

    def _orm_to_report(self, orm: AnalysisReportORM) -> AnalysisReport:
        """Convert ORM model to domain entity"""
        report = AnalysisReport(
            statement_id=orm.statement_id,
            kpi_summary=orm.kpi_summary,
            statement_table_summary=orm.statement_table_summary,
            ratio_analysis=orm.ratio_analysis,
            report_s3_key=orm.report_s3_key
        )

        report.id = orm.id
        report.created_at = orm.created_at

        return report

    def __del__(self):
        """Close database session on cleanup"""
        if hasattr(self, 'db'):
            self.db.close()
