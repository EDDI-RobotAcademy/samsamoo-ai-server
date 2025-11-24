from abc import ABC, abstractmethod
from typing import List, Dict, Any
from financial_statement.domain.financial_ratio import FinancialRatio


class CalculationServicePort(ABC):
    """
    Port interface for financial ratio calculation service.
    Stage 2 of the analysis pipeline - pure deterministic calculations.
    """

    @abstractmethod
    def calculate_profitability_ratios(self, financial_data: Dict[str, Any]) -> List[FinancialRatio]:
        """
        Calculate profitability ratios (ROA, ROE, ROI, profit margins).

        Args:
            financial_data: Normalized financial statement data

        Returns:
            List of FinancialRatio objects for profitability metrics

        Raises:
            CalculationError: If required data is missing or invalid
        """
        pass

    @abstractmethod
    def calculate_liquidity_ratios(self, financial_data: Dict[str, Any]) -> List[FinancialRatio]:
        """
        Calculate liquidity ratios (current ratio, quick ratio).

        Args:
            financial_data: Normalized financial statement data

        Returns:
            List of FinancialRatio objects for liquidity metrics

        Raises:
            CalculationError: If required data is missing or invalid
        """
        pass

    @abstractmethod
    def calculate_leverage_ratios(self, financial_data: Dict[str, Any]) -> List[FinancialRatio]:
        """
        Calculate leverage ratios (debt ratio, equity multiplier).

        Args:
            financial_data: Normalized financial statement data

        Returns:
            List of FinancialRatio objects for leverage metrics

        Raises:
            CalculationError: If required data is missing or invalid
        """
        pass

    @abstractmethod
    def calculate_efficiency_ratios(self, financial_data: Dict[str, Any]) -> List[FinancialRatio]:
        """
        Calculate efficiency ratios (asset turnover).

        Args:
            financial_data: Normalized financial statement data

        Returns:
            List of FinancialRatio objects for efficiency metrics

        Raises:
            CalculationError: If required data is missing or invalid
        """
        pass

    @abstractmethod
    def calculate_all_ratios(self, financial_data: Dict[str, Any], statement_id: int) -> List[FinancialRatio]:
        """
        Calculate all available financial ratios.

        Args:
            financial_data: Normalized financial statement data
            statement_id: ID of the financial statement

        Returns:
            List of all calculated FinancialRatio objects

        Raises:
            CalculationError: If required data is missing or invalid
        """
        pass
