import asyncio
import os
import tempfile
import logging
from typing import Dict, Any, List, Optional
from financial_statement.domain.financial_statement import FinancialStatement, StatementType
from financial_statement.domain.analysis_report import AnalysisReport
from financial_statement.application.port.financial_repository_port import FinancialRepositoryPort
from financial_statement.application.port.pdf_extraction_service_port import PDFExtractionServicePort
from financial_statement.application.port.calculation_service_port import CalculationServicePort
from financial_statement.application.port.llm_analysis_service_port import LLMAnalysisServicePort
from financial_statement.application.port.report_generation_service_port import ReportGenerationServicePort
from financial_statement.infrastructure.validation.pipeline_validator import PipelineValidator, ValidationError

logger = logging.getLogger(__name__)


class FinancialAnalysisUseCase:
    """
    Use case for financial statement analysis pipeline.
    Orchestrates the 4-stage analysis process with validation between stages.

    Pipeline:
    1. PDF Extraction → Normalized Data
    2. Ratio Calculation → Financial Ratios
    3. LLM Analysis → Qualitative Insights
    4. Report Generation → PDF Report
    """

    def __init__(
        self,
        repository: FinancialRepositoryPort,
        pdf_service: PDFExtractionServicePort,
        calculation_service: CalculationServicePort,
        llm_service: LLMAnalysisServicePort,
        report_service: ReportGenerationServicePort
    ):
        self.repository = repository
        self.pdf_service = pdf_service
        self.calculation_service = calculation_service
        self.llm_service = llm_service
        self.report_service = report_service
        self.validator = PipelineValidator()

    def create_statement(
        self,
        user_id: int,
        company_name: str,
        statement_type: StatementType,
        fiscal_year: int,
        fiscal_quarter: Optional[int] = None
    ) -> FinancialStatement:
        """Create a new financial statement (metadata only, before PDF upload)"""
        logger.info(f"Creating financial statement for {company_name} - {fiscal_year}")

        statement = FinancialStatement(
            company_name=company_name,
            statement_type=statement_type,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            user_id=user_id
        )

        saved_statement = self.repository.save_statement(statement)
        logger.info(f"Created statement with ID: {saved_statement.id}")

        return saved_statement

    def upload_statement_pdf(
        self,
        statement_id: int,
        pdf_path: str,
        s3_key: str
    ) -> FinancialStatement:
        """
        Upload PDF and extract financial data (Stage 1 of pipeline).

        Args:
            statement_id: ID of the statement to update
            pdf_path: Local path to PDF file
            s3_key: S3 key where PDF was uploaded

        Returns:
            Updated FinancialStatement with normalized data
        """
        logger.info(f"Processing PDF for statement {statement_id}")

        # Fetch statement
        statement = self.repository.find_statement_by_id(statement_id)
        if not statement:
            raise ValueError(f"Statement {statement_id} not found")

        try:
            # Stage 1: Extract from PDF
            logger.info("Stage 1: Extracting financial data from PDF")
            extracted_data = self.pdf_service.extract_from_pdf(pdf_path)

            # Normalize to K-IFRS
            normalized_data = self.pdf_service.normalize_to_kifrs(extracted_data)

            # Validation: Stage 1 → Stage 2
            self.validator.validate_stage1_output(normalized_data)

            # Update statement
            statement.set_s3_key(s3_key)
            statement.set_normalized_data(normalized_data)

            # Save
            updated_statement = self.repository.save_statement(statement)
            logger.info(f"PDF processing complete for statement {statement_id}")

            return updated_statement

        except ValidationError as e:
            logger.error(f"Validation failed during PDF processing: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to process PDF for statement {statement_id}: {e}")
            raise

    async def run_analysis_pipeline(
        self,
        statement_id: int
    ) -> Dict[str, Any]:
        """
        Run the complete 4-stage analysis pipeline.

        Args:
            statement_id: ID of the statement to analyze

        Returns:
            Dictionary with analysis results:
            {
                "statement": FinancialStatement,
                "ratios": List[FinancialRatio],
                "report": AnalysisReport,
                "report_pdf_path": str
            }
        """
        logger.info(f"Starting analysis pipeline for statement {statement_id}")

        # Fetch statement
        statement = self.repository.find_statement_by_id(statement_id)
        if not statement:
            raise ValueError(f"Statement {statement_id} not found")

        if not statement.is_complete():
            raise ValueError("Statement is incomplete - PDF must be uploaded first")

        try:
            # Stage 2: Calculate Financial Ratios
            logger.info("Stage 2: Calculating financial ratios")
            ratios = self.calculation_service.calculate_all_ratios(
                statement.normalized_data,
                statement_id
            )

            # Validation: Stage 2 → Stage 3
            self.validator.validate_stage2_output(ratios)

            # Save ratios
            saved_ratios = self.repository.save_ratios(ratios)
            logger.info(f"Calculated and saved {len(saved_ratios)} financial ratios")

            # Stage 3: LLM Analysis
            logger.info("Stage 3: Generating LLM analysis")
            analysis_result = await self.llm_service.generate_complete_analysis(
                statement.normalized_data,
                saved_ratios
            )

            # Validation: Stage 3 → Stage 4
            self.validator.validate_stage3_output(analysis_result)

            # Create analysis report
            report = AnalysisReport(statement_id=statement_id)
            report.set_kpi_summary(analysis_result["kpi_summary"])
            report.set_statement_table_summary(analysis_result["statement_table_summary"])
            report.set_ratio_analysis(analysis_result["ratio_analysis"])

            # Stage 4: Generate Report and Charts
            logger.info("Stage 4: Generating visual report")
            report_result = await self._generate_report(
                statement,
                saved_ratios,
                report
            )

            # Update report with S3 key
            report.set_report_s3_key(report_result["report_s3_key"])

            # Save report
            saved_report = self.repository.save_report(report)
            logger.info(f"Saved analysis report with ID: {saved_report.id}")

            # Final validation
            self.validator.validate_final_output(
                statement,
                saved_ratios,
                saved_report,
                report_result["chart_paths"]
            )

            result = {
                "statement": statement,
                "ratios": saved_ratios,
                "report": saved_report,
                "report_pdf_path": report_result["pdf_path"],
                "chart_paths": report_result["chart_paths"]
            }

            logger.info(f"Analysis pipeline completed successfully for statement {statement_id}")
            return result

        except ValidationError as e:
            logger.error(f"Validation failed during analysis pipeline: {e}")
            raise
        except Exception as e:
            logger.error(f"Analysis pipeline failed for statement {statement_id}: {e}")
            raise

    async def _generate_report(
        self,
        statement: FinancialStatement,
        ratios: List,
        report: AnalysisReport
    ) -> Dict[str, Any]:
        """
        Generate charts and PDF report.
        Helper method for Stage 4.
        """
        # Create temporary directory for outputs
        temp_dir = tempfile.mkdtemp(prefix="financial_report_")
        chart_dir = os.path.join(temp_dir, "charts")
        os.makedirs(chart_dir, exist_ok=True)

        try:
            # Generate charts
            chart_paths = self.report_service.generate_ratio_charts(
                ratios,
                chart_dir
            )

            # Generate PDF report
            pdf_path = os.path.join(temp_dir, f"report_{statement.id}.pdf")
            self.report_service.generate_pdf_report(
                report,
                statement.normalized_data,
                ratios,
                chart_paths,
                pdf_path
            )

            # TODO: Upload PDF to S3 and get S3 key
            # For now, return local path
            s3_key = f"reports/statement_{statement.id}_report.pdf"

            return {
                "pdf_path": pdf_path,
                "chart_paths": chart_paths,
                "report_s3_key": s3_key
            }

        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            raise

    def get_statement(self, statement_id: int) -> Optional[FinancialStatement]:
        """Get a financial statement by ID"""
        return self.repository.find_statement_by_id(statement_id)

    def get_user_statements(
        self,
        user_id: int,
        page: int = 1,
        size: int = 10
    ) -> List[FinancialStatement]:
        """Get all financial statements for a user"""
        return self.repository.find_statements_by_user_id(user_id, page, size)

    def get_ratios(self, statement_id: int) -> List:
        """Get all ratios for a statement"""
        return self.repository.find_ratios_by_statement_id(statement_id)

    def get_report(self, statement_id: int) -> Optional[AnalysisReport]:
        """Get analysis report for a statement"""
        return self.repository.find_report_by_statement_id(statement_id)

    def delete_statement(self, statement_id: int, user_id: int) -> bool:
        """
        Delete a financial statement (owner only).

        Args:
            statement_id: ID of statement to delete
            user_id: ID of requesting user

        Returns:
            True if deleted, False if not found or unauthorized
        """
        statement = self.repository.find_statement_by_id(statement_id)

        if not statement:
            return False

        if statement.user_id != user_id:
            raise PermissionError(f"User {user_id} is not authorized to delete statement {statement_id}")

        return self.repository.delete_statement(statement_id)
