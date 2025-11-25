"""
Alternative implementation using xhtml2pdf instead of WeasyPrint.
This version works on Windows without requiring GTK+ libraries.

To use this version:
1. Install: pip install -r requirements.txt
2. Replace import in your code:
   from financial_statement.infrastructure.service.report_generation_service_xhtml2pdf import ReportGenerationService
"""

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server environments
import seaborn as sns
from jinja2 import Template, Environment, FileSystemLoader
from xhtml2pdf import pisa  # Windows-compatible PDF library
from xhtml2pdf.default import DEFAULT_FONT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from typing import Dict, Any, List
import os
import logging
from datetime import datetime
from io import BytesIO
from financial_statement.domain.financial_ratio import FinancialRatio
from financial_statement.domain.analysis_report import AnalysisReport
from financial_statement.application.port.report_generation_service_port import ReportGenerationServicePort

logger = logging.getLogger(__name__)

# Register Korean fonts for xhtml2pdf/reportlab
def _register_korean_fonts():
    """Register Korean fonts for PDF generation"""
    # Common Korean font paths on Windows
    font_paths = [
        # Windows fonts
        "C:/Windows/Fonts/malgun.ttf",  # Malgun Gothic (맑은 고딕)
        "C:/Windows/Fonts/malgunbd.ttf",  # Malgun Gothic Bold
        "C:/Windows/Fonts/gulim.ttc",  # Gulim
        "C:/Windows/Fonts/batang.ttc",  # Batang
        # Linux fonts
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansKR-Regular.otf",
        # Mac fonts
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    ]

    registered = False
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font_name = os.path.basename(font_path).split('.')[0]
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                logger.info(f"Registered Korean font: {font_name} from {font_path}")
                registered = True
                break
            except Exception as e:
                logger.warning(f"Failed to register font {font_path}: {e}")

    if not registered:
        logger.warning("No Korean font found. PDF reports may not display Korean text correctly.")

    return registered

# Try to register Korean fonts at module load
_korean_font_registered = _register_korean_fonts()

# Set matplotlib style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 10


class ChartGenerationError(Exception):
    """Custom exception for chart generation errors"""
    pass


class ReportGenerationError(Exception):
    """Custom exception for report generation errors"""
    pass


class ReportGenerationService(ReportGenerationServicePort):
    """
    Implementation of report generation service using xhtml2pdf.
    Windows-compatible alternative to WeasyPrint (no GTK+ required).
    Stage 4 of the analysis pipeline - visualization and PDF creation.
    """

    def __init__(self, template_dir: str = "templates"):
        self.template_dir = template_dir
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

    def generate_ratio_charts(
        self,
        ratios: List[FinancialRatio],
        output_dir: str
    ) -> List[str]:
        """
        Generate matplotlib charts for financial ratios.
        Creates separate charts for each ratio category.
        """
        logger.info(f"Generating ratio charts in {output_dir}")

        os.makedirs(output_dir, exist_ok=True)
        chart_paths = []

        try:
            # Group ratios by category
            profitability = [r for r in ratios if r.is_profitability_ratio()]
            liquidity = [r for r in ratios if r.is_liquidity_ratio()]
            leverage = [r for r in ratios if r.is_leverage_ratio()]
            efficiency = [r for r in ratios if r.is_efficiency_ratio()]

            # Generate profitability chart
            if profitability:
                path = self._create_bar_chart(
                    profitability,
                    "Profitability Ratios",
                    os.path.join(output_dir, "profitability_ratios.png")
                )
                chart_paths.append(path)

            # Generate liquidity chart
            if liquidity:
                path = self._create_bar_chart(
                    liquidity,
                    "Liquidity Ratios",
                    os.path.join(output_dir, "liquidity_ratios.png")
                )
                chart_paths.append(path)

            # Generate leverage chart
            if leverage:
                path = self._create_bar_chart(
                    leverage,
                    "Leverage Ratios",
                    os.path.join(output_dir, "leverage_ratios.png")
                )
                chart_paths.append(path)

            # Generate efficiency chart
            if efficiency:
                path = self._create_bar_chart(
                    efficiency,
                    "Efficiency Ratios",
                    os.path.join(output_dir, "efficiency_ratios.png")
                )
                chart_paths.append(path)

            # Generate comprehensive ratio overview
            if ratios:
                path = self._create_ratio_overview_chart(
                    ratios,
                    os.path.join(output_dir, "ratio_overview.png")
                )
                chart_paths.append(path)

            logger.info(f"Generated {len(chart_paths)} ratio charts")
            return chart_paths

        except Exception as e:
            logger.error(f"Failed to generate ratio charts: {e}")
            raise ChartGenerationError(f"Chart generation failed: {e}")

    def generate_trend_charts(
        self,
        historical_data: List[Dict[str, Any]],
        output_dir: str
    ) -> List[str]:
        """
        Generate trend charts for multi-period analysis.
        Shows key metrics over time.
        """
        logger.info(f"Generating trend charts in {output_dir}")

        os.makedirs(output_dir, exist_ok=True)
        chart_paths = []

        try:
            if len(historical_data) < 2:
                logger.warning("Not enough historical data for trend analysis")
                return chart_paths

            # Extract time series data
            periods = []
            revenues = []
            net_incomes = []
            total_assets = []

            for data in historical_data:
                period = f"{data.get('fiscal_year', 'N/A')}Q{data.get('fiscal_quarter', '')}"
                periods.append(period)

                is_data = data.get('income_statement', {})
                bs_data = data.get('balance_sheet', {})

                revenues.append(is_data.get('revenue', 0))
                net_incomes.append(is_data.get('net_income', 0))
                total_assets.append(bs_data.get('total_assets', 0))

            # Generate revenue trend chart
            path = self._create_line_chart(
                periods,
                revenues,
                "Revenue Trend",
                "Revenue",
                os.path.join(output_dir, "revenue_trend.png")
            )
            chart_paths.append(path)

            # Generate net income trend chart
            path = self._create_line_chart(
                periods,
                net_incomes,
                "Net Income Trend",
                "Net Income",
                os.path.join(output_dir, "net_income_trend.png")
            )
            chart_paths.append(path)

            # Generate asset trend chart
            path = self._create_line_chart(
                periods,
                total_assets,
                "Total Assets Trend",
                "Total Assets",
                os.path.join(output_dir, "assets_trend.png")
            )
            chart_paths.append(path)

            logger.info(f"Generated {len(chart_paths)} trend charts")
            return chart_paths

        except Exception as e:
            logger.error(f"Failed to generate trend charts: {e}")
            raise ChartGenerationError(f"Trend chart generation failed: {e}")

    def generate_pdf_report(
        self,
        report: AnalysisReport,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio],
        chart_paths: List[str],
        output_path: str
    ) -> str:
        """
        Generate complete PDF report using Jinja2 templates and xhtml2pdf.
        Windows-compatible alternative to WeasyPrint.
        """
        logger.info(f"Generating PDF report at {output_path}")

        try:
            # Generate HTML first
            html_content = self.generate_html_report(
                report,
                financial_data,
                ratios,
                chart_paths
            )

            # Convert HTML to PDF using xhtml2pdf with UTF-8 encoding
            with open(output_path, "wb") as pdf_file:
                # Encode HTML content as UTF-8 bytes for proper Korean support
                html_bytes = html_content.encode('utf-8')
                pisa_status = pisa.CreatePDF(
                    html_bytes,
                    dest=pdf_file,
                    encoding='utf-8'
                )

            if pisa_status.err:
                raise ReportGenerationError(f"PDF generation had {pisa_status.err} errors")

            logger.info(f"PDF report generated successfully at {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            raise ReportGenerationError(f"PDF generation failed: {e}")

    def generate_html_report(
        self,
        report: AnalysisReport,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio],
        chart_paths: List[str]
    ) -> str:
        """
        Generate HTML report using Jinja2 templates.
        """
        logger.info("Generating HTML report")

        try:
            # Load template
            template = self.jinja_env.get_template("financial_reports/financial_report.html")

            # Prepare template data
            context = {
                "report": report,
                "financial_data": financial_data,
                "ratios": ratios,
                "chart_paths": chart_paths,
                "generation_date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "balance_sheet": financial_data.get("balance_sheet", {}),
                "income_statement": financial_data.get("income_statement", {}),
                "profitability_ratios": [r for r in ratios if r.is_profitability_ratio()],
                "liquidity_ratios": [r for r in ratios if r.is_liquidity_ratio()],
                "leverage_ratios": [r for r in ratios if r.is_leverage_ratio()],
                "efficiency_ratios": [r for r in ratios if r.is_efficiency_ratio()],
            }

            # Render template
            html_content = template.render(**context)

            logger.info("HTML report generated successfully")
            return html_content

        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")
            raise ReportGenerationError(f"HTML generation failed: {e}")

    def _create_bar_chart(
        self,
        ratios: List[FinancialRatio],
        title: str,
        output_path: str
    ) -> str:
        """Create a bar chart for a group of ratios"""
        plt.figure(figsize=(10, 6))

        ratio_names = [r.ratio_type.replace('_', ' ').title() for r in ratios]
        ratio_values = [float(r.ratio_value) for r in ratios]

        colors = sns.color_palette("husl", len(ratios))
        plt.bar(ratio_names, ratio_values, color=colors, alpha=0.8, edgecolor='black')

        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Ratio Type', fontsize=12)
        plt.ylabel('Value', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()

        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return output_path

    def _create_ratio_overview_chart(
        self,
        ratios: List[FinancialRatio],
        output_path: str
    ) -> str:
        """Create a comprehensive overview chart of all ratios"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Financial Ratios Overview', fontsize=16, fontweight='bold')

        # Group ratios
        profitability = [r for r in ratios if r.is_profitability_ratio()]
        liquidity = [r for r in ratios if r.is_liquidity_ratio()]
        leverage = [r for r in ratios if r.is_leverage_ratio()]
        efficiency = [r for r in ratios if r.is_efficiency_ratio()]

        # Plot each category
        categories = [
            (profitability, "Profitability", axes[0, 0]),
            (liquidity, "Liquidity", axes[0, 1]),
            (leverage, "Leverage", axes[1, 0]),
            (efficiency, "Efficiency", axes[1, 1])
        ]

        for ratio_group, title, ax in categories:
            if ratio_group:
                names = [r.ratio_type.replace('_', ' ') for r in ratio_group]
                values = [float(r.ratio_value) for r in ratio_group]

                ax.barh(names, values, color=sns.color_palette("Set2", len(names)))
                ax.set_title(title, fontweight='bold')
                ax.set_xlabel('Value')
                ax.grid(axis='x', alpha=0.3)
            else:
                ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
                ax.set_title(title, fontweight='bold')

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return output_path

    def _create_line_chart(
        self,
        periods: List[str],
        values: List[float],
        title: str,
        ylabel: str,
        output_path: str
    ) -> str:
        """Create a line chart for trend analysis"""
        plt.figure(figsize=(12, 6))

        plt.plot(periods, values, marker='o', linewidth=2, markersize=8, color='#2E86AB')
        plt.fill_between(range(len(periods)), values, alpha=0.3, color='#2E86AB')

        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Period', fontsize=12)
        plt.ylabel(ylabel, fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3)

        # Format y-axis with thousands separator
        ax = plt.gca()
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        return output_path

    def generate_markdown_report(
        self,
        report: AnalysisReport,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio],
        output_path: str
    ) -> str:
        """
        Generate Markdown report for LLM analysis summary.
        Korean text displays correctly without font encoding issues.
        """
        logger.info(f"Generating Markdown report at {output_path}")

        try:
            # Build markdown content
            lines = []

            # Header
            company_name = financial_data.get('company_name', 'N/A')
            fiscal_year = financial_data.get('fiscal_year', 'N/A')
            fiscal_quarter = financial_data.get('fiscal_quarter', '')
            generation_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            lines.append(f"# 재무분석 보고서 (Financial Analysis Report)")
            lines.append("")
            lines.append(f"**회사명 (Company):** {company_name}")
            lines.append(f"**회계기간 (Period):** {fiscal_year}" + (f" Q{fiscal_quarter}" if fiscal_quarter else ""))
            lines.append(f"**생성일시 (Generated):** {generation_date}")
            lines.append("")
            lines.append("---")
            lines.append("")

            # Executive Summary / KPI Summary
            lines.append("## 핵심 요약 (Executive Summary)")
            lines.append("")
            if report and report.kpi_summary:
                lines.append(report.kpi_summary)
            else:
                lines.append("*분석 요약이 생성되지 않았습니다. (No summary generated)*")
            lines.append("")
            lines.append("---")
            lines.append("")

            # Financial Statements Overview
            lines.append("## 재무제표 개요 (Financial Statements Overview)")
            lines.append("")

            # Balance Sheet
            balance_sheet = financial_data.get('balance_sheet', {})
            lines.append("### 재무상태표 (Balance Sheet)")
            lines.append("")
            lines.append("| 항목 (Item) | 금액 (Amount) |")
            lines.append("|-------------|---------------|")
            lines.append(f"| 총자산 (Total Assets) | {balance_sheet.get('total_assets', 0):,.0f} |")
            lines.append(f"| 총부채 (Total Liabilities) | {balance_sheet.get('total_liabilities', 0):,.0f} |")
            lines.append(f"| 총자본 (Total Equity) | {balance_sheet.get('total_equity', 0):,.0f} |")
            lines.append("")

            # Income Statement
            income_statement = financial_data.get('income_statement', {})
            lines.append("### 손익계산서 (Income Statement)")
            lines.append("")
            lines.append("| 항목 (Item) | 금액 (Amount) |")
            lines.append("|-------------|---------------|")
            lines.append(f"| 매출액 (Revenue) | {income_statement.get('revenue', 0):,.0f} |")
            lines.append(f"| 영업이익 (Operating Income) | {income_statement.get('operating_income', 0):,.0f} |")
            lines.append(f"| 당기순이익 (Net Income) | {income_statement.get('net_income', 0):,.0f} |")
            lines.append("")
            lines.append("---")
            lines.append("")

            # Financial Ratios
            lines.append("## 재무비율 분석 (Financial Ratio Analysis)")
            lines.append("")

            # Group ratios by category
            profitability = [r for r in ratios if r.is_profitability_ratio()]
            liquidity = [r for r in ratios if r.is_liquidity_ratio()]
            leverage = [r for r in ratios if r.is_leverage_ratio()]
            efficiency = [r for r in ratios if r.is_efficiency_ratio()]

            if profitability:
                lines.append("### 수익성 비율 (Profitability Ratios)")
                lines.append("")
                lines.append("| 비율 (Ratio) | 값 (Value) |")
                lines.append("|--------------|------------|")
                for ratio in profitability:
                    lines.append(f"| {ratio.ratio_type} | {ratio.as_percentage()} |")
                lines.append("")

            if liquidity:
                lines.append("### 유동성 비율 (Liquidity Ratios)")
                lines.append("")
                lines.append("| 비율 (Ratio) | 값 (Value) |")
                lines.append("|--------------|------------|")
                for ratio in liquidity:
                    lines.append(f"| {ratio.ratio_type} | {ratio.as_percentage()} |")
                lines.append("")

            if leverage:
                lines.append("### 레버리지 비율 (Leverage Ratios)")
                lines.append("")
                lines.append("| 비율 (Ratio) | 값 (Value) |")
                lines.append("|--------------|------------|")
                for ratio in leverage:
                    lines.append(f"| {ratio.ratio_type} | {ratio.as_percentage()} |")
                lines.append("")

            if efficiency:
                lines.append("### 효율성 비율 (Efficiency Ratios)")
                lines.append("")
                lines.append("| 비율 (Ratio) | 값 (Value) |")
                lines.append("|--------------|------------|")
                for ratio in efficiency:
                    lines.append(f"| {ratio.ratio_type} | {ratio.as_percentage()} |")
                lines.append("")

            # Ratio Analysis Interpretation
            lines.append("### 비율 분석 해석 (Ratio Analysis Interpretation)")
            lines.append("")
            if report and report.ratio_analysis:
                lines.append(report.ratio_analysis)
            else:
                lines.append("*비율 분석이 생성되지 않았습니다. (No ratio analysis generated)*")
            lines.append("")
            lines.append("---")
            lines.append("")

            # Footer
            lines.append("*이 보고서는 AI 기반 재무분석 시스템에 의해 자동 생성되었습니다.*")
            lines.append("")
            lines.append("*This report was generated automatically using AI-powered financial analysis.*")

            # Write to file with UTF-8 encoding
            markdown_content = "\n".join(lines)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            logger.info(f"Markdown report generated successfully at {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate Markdown report: {e}")
            raise ReportGenerationError(f"Markdown generation failed: {e}")
