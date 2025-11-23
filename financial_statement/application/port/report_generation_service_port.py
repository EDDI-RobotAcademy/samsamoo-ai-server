from abc import ABC, abstractmethod
from typing import Dict, Any, List
from financial_statement.domain.financial_ratio import FinancialRatio
from financial_statement.domain.analysis_report import AnalysisReport


class ReportGenerationServicePort(ABC):
    """
    Port interface for report generation service.
    Stage 4 of the analysis pipeline - visualization and PDF creation.
    """

    @abstractmethod
    def generate_ratio_charts(
        self,
        ratios: List[FinancialRatio],
        output_dir: str
    ) -> List[str]:
        """
        Generate matplotlib charts for financial ratios.

        Args:
            ratios: Calculated financial ratios
            output_dir: Directory to save chart images

        Returns:
            List of paths to generated chart images

        Raises:
            ChartGenerationError: If chart generation fails
        """
        pass

    @abstractmethod
    def generate_trend_charts(
        self,
        historical_data: List[Dict[str, Any]],
        output_dir: str
    ) -> List[str]:
        """
        Generate trend charts for multi-period analysis.

        Args:
            historical_data: List of financial statements over time
            output_dir: Directory to save chart images

        Returns:
            List of paths to generated chart images

        Raises:
            ChartGenerationError: If chart generation fails
        """
        pass

    @abstractmethod
    def generate_pdf_report(
        self,
        report: AnalysisReport,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio],
        chart_paths: List[str],
        output_path: str
    ) -> str:
        """
        Generate complete PDF report using Jinja2 templates and WeasyPrint.

        Args:
            report: AnalysisReport with LLM-generated content
            financial_data: Normalized financial statement data
            ratios: Calculated financial ratios
            chart_paths: Paths to generated chart images
            output_path: Path where PDF should be saved

        Returns:
            Path to generated PDF file

        Raises:
            ReportGenerationError: If PDF generation fails
        """
        pass

    @abstractmethod
    def generate_html_report(
        self,
        report: AnalysisReport,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio],
        chart_paths: List[str]
    ) -> str:
        """
        Generate HTML report using Jinja2 templates (intermediate step for PDF).

        Args:
            report: AnalysisReport with LLM-generated content
            financial_data: Normalized financial statement data
            ratios: Calculated financial ratios
            chart_paths: Paths to generated chart images

        Returns:
            HTML string for the report

        Raises:
            ReportGenerationError: If HTML generation fails
        """
        pass
