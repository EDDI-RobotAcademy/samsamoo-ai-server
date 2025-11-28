import os
import logging
from datetime import datetime
from typing import Dict, Any, List

import matplotlib
matplotlib.use('Agg')  # 서버 환경용 비대화형 백엔드
import matplotlib.pyplot as plt
import seaborn as sns

from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa  # Windows-compatible PDF library
from xhtml2pdf.default import DEFAULT_FONT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from financial_statement.domain.financial_ratio import FinancialRatio
from financial_statement.domain.analysis_report import AnalysisReport
from financial_statement.application.port.report_generation_service_port import ReportGenerationServicePort

logger = logging.getLogger(__name__)

# Register Korean fonts for xhtml2pdf/reportlab
def _register_korean_fonts(base_dir: str = "resources/fonts") -> str:
    """
    resources/fonts 내부의 한글 폰트를 등록.
    성공 시 등록된 폰트 이름을 반환(예: 'malgun'), 실패 시 '' 반환.
    """
    font_candidates = [
        ("malgun", "malgun.ttf"),                 # 맑은 고딕
        ("malgunbd", "malgunbd.ttf"),             # 맑은 고딕 Bold
        ("gulim", "gulim.ttc"),                   # 굴림
        ("batang", "batang.ttc"),                 # 바탕
        ("NanumGothic", "NanumGothic.ttf"),       # 나눔고딕
        ("NotoSansKR", "NotoSansKR-Regular.otf"), # 노토 산스
        ("AppleSDGothicNeo", "AppleSDGothicNeo.ttc"), # macOS
    ]

    if not os.path.exists(base_dir):
        logger.warning(f"⚠️ Font directory not found: {base_dir}")
        return ""

    logger.info(f"🔍 Searching fonts in: {os.path.abspath(base_dir)}")
    for font_name, filename in font_candidates:
        font_path = os.path.join(base_dir, filename)
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                logger.info(f"✅ Registered Korean font: {font_name} ({font_path})")
                return font_name
            except Exception as e:
                logger.warning(f"⚠️ Failed to register font {font_path}: {e}")
        else:
            logger.debug(f"Font not found: {font_path}")

    logger.warning("⚠️ No Korean font found in resources/fonts. PDF may not display Korean text properly.")
    return ""


# Set matplotlib style
def _set_default_pdf_font(font_name: str):
    """
    xhtml2pdf 기본 폰트를 한글 폰트로 매핑.
    템플릿에서 font-family를 지정하지 않아도 안전하게 렌더링되도록 함.
    """
    if not font_name:
        logger.warning("⚠️ No font name provided for DEFAULT_FONT mapping.")
        return
    try:
        DEFAULT_FONT["helvetica"] = font_name
        DEFAULT_FONT["times"] = font_name
        DEFAULT_FONT["courier"] = font_name
        DEFAULT_FONT["cid"] = font_name
        logger.info(f"✅ Set xhtml2pdf DEFAULT_FONT to: {font_name}")
        logger.info(f"[DEFAULT_FONT mapping] {DEFAULT_FONT}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to set DEFAULT_FONT mapping: {e}")


# 모듈 로드 시 1회만 등록/매핑 (중복 등록 제거)
_REGISTERED_FONT = _register_korean_fonts("resources/fonts")
if _REGISTERED_FONT:
    _set_default_pdf_font(_REGISTERED_FONT)

# Matplotlib 스타일(서버 기본값)
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 10


class ChartGenerationError(Exception):
    pass


class ReportGenerationError(Exception):
    pass


class ReportGenerationService(ReportGenerationServicePort):
    """
    XHTML2PDF 기반 PDF 생성 서비스.(GTK+ 불필요 / Windows 호환)
    Implementation of report generation service using xhtml2pdf.
    Windows-compatible alternative to WeasyPrint (no GTK+ required).
    Stage 4 of the analysis pipeline - visualization and PDF creation.
    """

    def __init__(self, template_dir: str = "templates"):
        self.template_dir = template_dir
        # HTML 오토이스케이프 활성화
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True
        )

    # -------------------------
    # 차트 생성(그룹/개요/트렌드)
    # -------------------------
    def generate_ratio_charts(
        self,
        ratios: List[FinancialRatio],
        output_dir: str
    ) -> List[str]:
        logger.info(f"Generating ratio charts in {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        chart_paths: List[str] = []
        try:
            # Group ratios by category
            profitability = [r for r in ratios if r.is_profitability_ratio()]
            liquidity = [r for r in ratios if r.is_liquidity_ratio()]
            leverage = [r for r in ratios if r.is_leverage_ratio()]
            efficiency = [r for r in ratios if r.is_efficiency_ratio()]

            # Generate profitability chart
            if profitability:
                chart_paths.append(self._create_bar_chart(
                    profitability, "Profitability Ratios",
                    os.path.join(output_dir, "profitability_ratios.png")
                ))

            # Generate liquidity chart
            if liquidity:
                chart_paths.append(self._create_bar_chart(
                    liquidity, "Liquidity Ratios",
                    os.path.join(output_dir, "liquidity_ratios.png")
                ))

            # Generate leverage chart
            if leverage:
                chart_paths.append(self._create_bar_chart(
                    leverage, "Leverage Ratios",
                    os.path.join(output_dir, "leverage_ratios.png")
                ))

            # Generate efficiency chart
            if efficiency:
                chart_paths.append(self._create_bar_chart(
                    efficiency, "Efficiency Ratios",
                    os.path.join(output_dir, "efficiency_ratios.png")
                ))

            # Generate comprehensive ratio overview
            if ratios:
                chart_paths.append(self._create_ratio_overview_chart(
                    ratios, os.path.join(output_dir, "ratio_overview.png")
                ))

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
        chart_paths: List[str] = []
        try:
            if len(historical_data) < 2:
                logger.warning("Not enough historical data for trend analysis")
                return chart_paths

            periods, revenues, net_incomes, total_assets = [], [], [], []
            for data in historical_data:
                period = f"{data.get('fiscal_year', 'N/A')}Q{data.get('fiscal_quarter', '')}"
                periods.append(period)
                is_data = data.get('income_statement', {})
                bs_data = data.get('balance_sheet', {})
                revenues.append(is_data.get('revenue', 0))
                net_incomes.append(is_data.get('net_income', 0))
                total_assets.append(bs_data.get('total_assets', 0))

            # Generate revenue trend chart
            chart_paths.append(self._create_line_chart(
                periods, revenues, "Revenue Trend", "Revenue",
                os.path.join(output_dir, "revenue_trend.png")
            ))

            # Generate net income trend chart
            chart_paths.append(self._create_line_chart(
                periods, net_incomes, "Net Income Trend", "Net Income",
                os.path.join(output_dir, "net_income_trend.png")
            ))

            # Generate asset trend chart
            chart_paths.append(self._create_line_chart(
                periods, total_assets, "Total Assets Trend", "Total Assets",
                os.path.join(output_dir, "assets_trend.png")
            ))
            logger.info(f"Generated {len(chart_paths)} trend charts")
            return chart_paths
        except Exception as e:
            logger.error(f"Failed to generate trend charts: {e}")
            raise ChartGenerationError(f"Trend chart generation failed: {e}")

    # -------------
    # PDF 생성 본체
    # -------------
    def generate_pdf_report(
        self,
        report: AnalysisReport,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio],
        chart_paths: List[str],
        output_path: str
    ) -> str:
        logger.info(f"Generating PDF report at {output_path}")
        try:
            # (옵션) 차트 경로를 file:/// 절대경로로 통일 → xhtml2pdf 경로 인식 안정화
            normalized_chart_paths = [
                p if str(p).startswith("http")
                else f"file:///{os.path.abspath(p)}".replace("\\", "/")
                for p in chart_paths
            ]

            html_content = self.generate_html_report(
                report, financial_data, ratios, normalized_chart_paths
            )
            # Convert HTML to PDF using xhtml2pdf with UTF-8 encoding
            # UTF-8 바이트로 변환 후 PDF 생성
            html_bytes = html_content.encode("utf-8")
            logger.info(f"[PDF HTML bytes length]: {len(html_bytes)}")

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as pdf_file:
                pisa_status = pisa.CreatePDF(
                    html_bytes,
                    dest=pdf_file,
                    encoding="utf-8"
                )

            if pisa_status.err:
                raise ReportGenerationError(f"PDF generation had {pisa_status.err} errors")

            logger.info(f"PDF report generated successfully at {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            raise ReportGenerationError(f"PDF generation failed: {e}")

    # -------------
    # HTML 렌더링
    # -------------
    def generate_html_report(
        self,
        report: AnalysisReport,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio],
        chart_paths: List[str]
    ) -> str:
        logger.info("Generating HTML report")
        try:
            # Load template
            template = self.jinja_env.get_template("financial_reports/financial_report.html")
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
                # 템플릿에서 사용: 등록된 폰트 이름(예: 'malgun')
                "default_font": _REGISTERED_FONT or "sans-serif",
            }
            # Render template
            html_content = template.render(**context)
            logger.info("HTML report generated successfully")
            return html_content
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")
            raise ReportGenerationError(f"HTML generation failed: {e}")

    # -----------------
    # 내부 차트 유틸리티
    # -----------------
    def _create_bar_chart(
        self,
        ratios: List[FinancialRatio],
        title: str,
        output_path: str
    ) -> str:
        plt.figure(figsize=(10, 6))
        names = [r.ratio_type.replace('_', ' ').title() for r in ratios]
        values = [float(r.ratio_value) for r in ratios]
        colors = sns.color_palette("husl", len(ratios))

        plt.bar(names, values, color=colors, alpha=0.8, edgecolor='black')
        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Ratio Type', fontsize=12)
        plt.ylabel('Value', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        return output_path

    def _create_ratio_overview_chart(
        self,
        ratios: List[FinancialRatio],
        output_path: str
    ) -> str:
        import numpy as np
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Financial Ratios Overview', fontsize=16, fontweight='bold')

        profitability = [r for r in ratios if r.is_profitability_ratio()]
        liquidity = [r for r in ratios if r.is_liquidity_ratio()]
        leverage = [r for r in ratios if r.is_leverage_ratio()]
        efficiency = [r for r in ratios if r.is_efficiency_ratio()]

        groups = [
            (profitability, "Profitability", axes[0, 0]),
            (liquidity, "Liquidity", axes[0, 1]),
            (leverage, "Leverage", axes[1, 0]),
            (efficiency, "Efficiency", axes[1, 1]),
        ]

        for group, title, ax in groups:
            if group:
                names = [r.ratio_type.replace('_', ' ') for r in group]
                values = [float(r.ratio_value) for r in group]
                ax.barh(names, values, color=sns.color_palette("Set2", len(names)))
                ax.set_title(title, fontweight='bold')
                ax.set_xlabel('Value')
                ax.grid(axis='x', alpha=0.3)
            else:
                ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
                ax.set_title(title, fontweight='bold')

        plt.tight_layout()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
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
        plt.figure(figsize=(12, 6))
        plt.plot(periods, values, marker='o', linewidth=2, markersize=8, color='#2E86AB')
        plt.fill_between(range(len(periods)), values, alpha=0.3, color='#2E86AB')

        plt.title(title, fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Period', fontsize=12)
        plt.ylabel(ylabel, fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3)

        ax = plt.gca()
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))

        plt.tight_layout()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
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
