from abc import ABC, abstractmethod
from typing import Optional, List
from financial_statement.domain.financial_statement import FinancialStatement
from financial_statement.domain.financial_ratio import FinancialRatio
from financial_statement.domain.analysis_report import AnalysisReport


class FinancialRepositoryPort(ABC):
    """
    Port interface for financial statement repository.
    Defines contracts for persistence operations.
    """

    @abstractmethod
    def save_statement(self, statement: FinancialStatement) -> FinancialStatement:
        """Save or update a financial statement"""
        pass

    @abstractmethod
    def find_statement_by_id(self, statement_id: int) -> Optional[FinancialStatement]:
        """Find a financial statement by ID"""
        pass

    @abstractmethod
    def find_statements_by_user_id(self, user_id: int, page: int = 1, size: int = 10) -> List[FinancialStatement]:
        """Find all financial statements for a user with pagination"""
        pass

    @abstractmethod
    def delete_statement(self, statement_id: int) -> bool:
        """Delete a financial statement"""
        pass

    @abstractmethod
    def save_ratios(self, ratios: List[FinancialRatio]) -> List[FinancialRatio]:
        """Save multiple financial ratios"""
        pass

    @abstractmethod
    def find_ratios_by_statement_id(self, statement_id: int) -> List[FinancialRatio]:
        """Find all ratios for a financial statement"""
        pass

    @abstractmethod
    def save_report(self, report: AnalysisReport) -> AnalysisReport:
        """Save or update an analysis report"""
        pass

    @abstractmethod
    def find_report_by_statement_id(self, statement_id: int) -> Optional[AnalysisReport]:
        """Find analysis report for a financial statement"""
        pass

    @abstractmethod
    def delete_report(self, report_id: int) -> bool:
        """Delete an analysis report"""
        pass
