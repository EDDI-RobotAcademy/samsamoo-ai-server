from abc import ABC, abstractmethod
from typing import Dict, Any, List
from financial_statement.domain.financial_ratio import FinancialRatio


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    Each provider implements the core LLM interaction methods.
    """

    @abstractmethod
    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.3
    ) -> str:
        """Generate text completion from prompts"""
        pass

    @abstractmethod
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Generate structured JSON response from prompts"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is properly configured and available"""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this provider"""
        pass

    # Helper methods for context preparation (shared across providers)
    def prepare_kpi_context(self, financial_data: Dict[str, Any], ratios: List[FinancialRatio]) -> str:
        """Prepare concise context for KPI summary generation"""
        bs = financial_data.get("balance_sheet", {})
        is_data = financial_data.get("income_statement", {})

        context_parts = [
            f"Total Assets: {bs.get('total_assets', 0):,.0f}",
            f"Total Equity: {bs.get('total_equity', 0):,.0f}",
            f"Revenue: {is_data.get('revenue', 0):,.0f}",
            f"Net Income: {is_data.get('net_income', 0):,.0f}",
            "\nKey Ratios:"
        ]

        for ratio in ratios[:8]:  # Include top 8 ratios
            context_parts.append(f"- {ratio.ratio_type}: {ratio.as_percentage()}")

        return "\n".join(context_parts)

    def prepare_ratio_context(self, ratios: List[FinancialRatio], financial_data: Dict[str, Any]) -> str:
        """Prepare structured context for ratio analysis"""
        categories = {
            "Profitability Ratios": [],
            "Liquidity Ratios": [],
            "Leverage Ratios": [],
            "Efficiency Ratios": []
        }

        for ratio in ratios:
            if ratio.is_profitability_ratio():
                categories["Profitability Ratios"].append(f"- {ratio.ratio_type}: {ratio.as_percentage()}")
            elif ratio.is_liquidity_ratio():
                categories["Liquidity Ratios"].append(f"- {ratio.ratio_type}: {ratio.as_percentage()}")
            elif ratio.is_leverage_ratio():
                categories["Leverage Ratios"].append(f"- {ratio.ratio_type}: {ratio.as_percentage()}")
            elif ratio.is_efficiency_ratio():
                categories["Efficiency Ratios"].append(f"- {ratio.ratio_type}: {ratio.as_percentage()}")

        context_parts = []
        for category, items in categories.items():
            if items:
                context_parts.append(f"\n{category}:")
                context_parts.extend(items)

        return "\n".join(context_parts)
