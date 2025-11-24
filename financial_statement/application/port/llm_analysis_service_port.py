from abc import ABC, abstractmethod
from typing import Dict, Any, List
from financial_statement.domain.financial_ratio import FinancialRatio


class LLMAnalysisServicePort(ABC):
    """
    Port interface for LLM-based analysis service.
    Stage 3 of the analysis pipeline - qualitative interpretation.
    """

    @abstractmethod
    async def generate_kpi_summary(
        self,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio]
    ) -> str:
        """
        Generate executive KPI summary using LLM.

        Args:
            financial_data: Normalized financial statement data
            ratios: Calculated financial ratios

        Returns:
            Natural language KPI summary (narrative text)

        Raises:
            LLMError: If LLM API call fails
        """
        pass

    @abstractmethod
    async def generate_statement_table_summary(
        self,
        financial_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate structured summary of financial statement tables using LLM.

        Args:
            financial_data: Normalized financial statement data

        Returns:
            Dictionary with summarized tables:
            {
                "balance_sheet_summary": {...},
                "income_statement_summary": {...},
                "key_highlights": [...]
            }

        Raises:
            LLMError: If LLM API call fails
        """
        pass

    @abstractmethod
    async def generate_ratio_analysis(
        self,
        ratios: List[FinancialRatio],
        financial_data: Dict[str, Any]
    ) -> str:
        """
        Generate interpretation and analysis of financial ratios using LLM.

        Args:
            ratios: Calculated financial ratios
            financial_data: Normalized financial statement data for context

        Returns:
            Natural language ratio analysis with insights

        Raises:
            LLMError: If LLM API call fails
        """
        pass

    @abstractmethod
    async def generate_complete_analysis(
        self,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio]
    ) -> Dict[str, Any]:
        """
        Generate complete LLM analysis (all three components in parallel).

        Args:
            financial_data: Normalized financial statement data
            ratios: Calculated financial ratios

        Returns:
            Dictionary with all analysis components:
            {
                "kpi_summary": "...",
                "statement_table_summary": {...},
                "ratio_analysis": "..."
            }

        Raises:
            LLMError: If LLM API call fails
        """
        pass
