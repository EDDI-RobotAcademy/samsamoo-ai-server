import json
import logging
from typing import Dict, Any, List
from .base_provider import BaseLLMProvider
from financial_statement.domain.financial_ratio import FinancialRatio

logger = logging.getLogger(__name__)


class TemplateProvider(BaseLLMProvider):
    """
    Template-based provider that generates analysis without external LLM API.
    Always available as fallback option.
    """

    def __init__(self):
        logger.info("Template provider initialized (no API required)")

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.3
    ) -> str:
        """Generate template-based text response"""
        return "Template-based analysis (no LLM API used)"

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Generate template-based JSON response"""
        return {"note": "Template-based analysis (no LLM API used)"}

    def is_available(self) -> bool:
        """Template provider is always available"""
        return True

    def get_provider_name(self) -> str:
        """Get provider name"""
        return "Template (No AI)"

    # Template-specific methods for financial analysis
    def create_kpi_summary(self, financial_data: Dict[str, Any], ratios: List[FinancialRatio]) -> str:
        """Create template-based KPI summary"""
        bs = financial_data.get("balance_sheet", {})
        is_data = financial_data.get("income_statement", {})

        return f"""Financial KPI Summary

Key Financial Metrics:
• Total Assets: ${bs.get('total_assets', 0):,.0f}
• Total Equity: ${bs.get('total_equity', 0):,.0f}
• Revenue: ${is_data.get('revenue', 0):,.0f}
• Net Income: ${is_data.get('net_income', 0):,.0f}

Calculated Ratios: {len(ratios)} financial ratios have been computed.
Please review the detailed ratio analysis section for comprehensive insights.

Note: This is a template-based summary generated without AI analysis."""

    def create_table_summary(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create template-based table summary"""
        bs = financial_data.get("balance_sheet", {})
        is_data = financial_data.get("income_statement", {})

        return {
            "balance_sheet_summary": {
                "total_assets": bs.get("total_assets", 0),
                "total_liabilities": bs.get("total_liabilities", 0),
                "total_equity": bs.get("total_equity", 0),
                "key_insights": "Balance sheet extracted successfully from financial statement"
            },
            "income_statement_summary": {
                "revenue": is_data.get("revenue", 0),
                "net_income": is_data.get("net_income", 0),
                "profitability": "See ratio analysis for detailed profitability metrics",
                "key_insights": "Income statement extracted successfully from financial statement"
            },
            "key_highlights": [
                f"Total Assets: ${bs.get('total_assets', 0):,.0f}",
                f"Revenue: ${is_data.get('revenue', 0):,.0f}",
                f"Net Income: ${is_data.get('net_income', 0):,.0f}"
            ]
        }

    def create_ratio_analysis(self, ratios: List[FinancialRatio]) -> str:
        """Create template-based ratio analysis"""
        analysis_parts = ["Financial Ratio Analysis\n"]

        # Group ratios by category
        profitability = [r for r in ratios if r.is_profitability_ratio()]
        liquidity = [r for r in ratios if r.is_liquidity_ratio()]
        leverage = [r for r in ratios if r.is_leverage_ratio()]
        efficiency = [r for r in ratios if r.is_efficiency_ratio()]

        if profitability:
            analysis_parts.append("\n📊 Profitability Ratios:")
            for ratio in profitability:
                analysis_parts.append(f"  • {ratio.ratio_type}: {ratio.as_percentage()}")
            analysis_parts.append("  → Measures company's ability to generate profit from operations")

        if liquidity:
            analysis_parts.append("\n💧 Liquidity Ratios:")
            for ratio in liquidity:
                analysis_parts.append(f"  • {ratio.ratio_type}: {ratio.as_percentage()}")
            analysis_parts.append("  → Indicates ability to meet short-term obligations")

        if leverage:
            analysis_parts.append("\n⚖️ Leverage Ratios:")
            for ratio in leverage:
                analysis_parts.append(f"  • {ratio.ratio_type}: {ratio.as_percentage()}")
            analysis_parts.append("  → Shows financial structure and debt management")

        if efficiency:
            analysis_parts.append("\n⚡ Efficiency Ratios:")
            for ratio in efficiency:
                analysis_parts.append(f"  • {ratio.ratio_type}: {ratio.as_percentage()}")
            analysis_parts.append("  → Reflects how effectively assets are utilized")

        analysis_parts.append("\n---")
        analysis_parts.append("Note: This is a template-based analysis generated without AI.")
        analysis_parts.append("For detailed interpretation, consider using an AI provider.")

        return "\n".join(analysis_parts)
