from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class StatementType(Enum):
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class FinancialStatement:
    """
    Domain entity representing a financial statement.
    Pure business logic with no framework dependencies.
    """

    def __init__(
        self,
        company_name: str,
        statement_type: StatementType,
        fiscal_year: int,
        fiscal_quarter: Optional[int] = None,
        user_id: Optional[int] = None
    ):
        self.id: Optional[int] = None
        self.user_id = user_id
        self.company_name = company_name
        self.statement_type = statement_type
        self.fiscal_year = fiscal_year
        self.fiscal_quarter = fiscal_quarter
        self.s3_key: Optional[str] = None
        self.normalized_data: Optional[Dict[str, Any]] = None
        self.created_at: datetime = datetime.utcnow()
        self.updated_at: datetime = datetime.utcnow()

        self._validate()

    def _validate(self):
        """Validate business rules"""
        if not self.company_name or len(self.company_name.strip()) == 0:
            raise ValueError("Company name cannot be empty")

        if self.fiscal_year < 1900 or self.fiscal_year > 2100:
            raise ValueError(f"Invalid fiscal year: {self.fiscal_year}")

        if self.statement_type == StatementType.QUARTERLY:
            if self.fiscal_quarter is None:
                raise ValueError("Quarterly statements must have fiscal_quarter")
            if self.fiscal_quarter not in [1, 2, 3, 4]:
                raise ValueError(f"Invalid fiscal quarter: {self.fiscal_quarter}")

        if self.statement_type == StatementType.ANNUAL:
            if self.fiscal_quarter is not None:
                raise ValueError("Annual statements should not have fiscal_quarter")

    def set_s3_key(self, s3_key: str):
        """Set S3 key for uploaded PDF"""
        if not s3_key or len(s3_key.strip()) == 0:
            raise ValueError("S3 key cannot be empty")
        self.s3_key = s3_key
        self.updated_at = datetime.utcnow()

    def set_normalized_data(self, data: Dict[str, Any]):
        """
        Set normalized financial data after extraction.

        Note: Validation is lenient to allow processing with partial data.
        Only raises error if data is completely empty.
        """
        # Ensure sections exist (create empty if missing)
        if "balance_sheet" not in data:
            data["balance_sheet"] = {}
        if "income_statement" not in data:
            data["income_statement"] = {}

        balance_sheet = data.get("balance_sheet", {})
        income_statement = data.get("income_statement", {})

        # Only raise error if both sections are completely empty
        if not balance_sheet and not income_statement:
            raise ValueError("Normalized data cannot be completely empty - at least one statement must have data")

        # Log warnings for missing items but don't block
        import logging
        logger = logging.getLogger(__name__)

        required_bs_items = ["total_assets", "total_liabilities", "total_equity"]
        missing_bs = [item for item in required_bs_items if item not in balance_sheet]
        if missing_bs:
            logger.warning(f"Missing balance sheet items: {', '.join(missing_bs)}")

        required_is_items = ["revenue", "operating_income", "net_income"]
        missing_is = [item for item in required_is_items if item not in income_statement]
        if missing_is:
            logger.warning(f"Missing income statement items: {', '.join(missing_is)}")

        self.normalized_data = data
        self.updated_at = datetime.utcnow()

    def get_balance_sheet_data(self) -> Optional[Dict[str, Any]]:
        """Extract balance sheet from normalized data"""
        if self.normalized_data is None:
            return None
        return self.normalized_data.get("balance_sheet")

    def get_income_statement_data(self) -> Optional[Dict[str, Any]]:
        """Extract income statement from normalized data"""
        if self.normalized_data is None:
            return None
        return self.normalized_data.get("income_statement")

    def get_cash_flow_data(self) -> Optional[Dict[str, Any]]:
        """Extract cash flow statement from normalized data"""
        if self.normalized_data is None:
            return None
        return self.normalized_data.get("cash_flow_statement")

    def is_complete(self) -> bool:
        """Check if statement has all required data for analysis"""
        return (
            self.s3_key is not None and
            self.normalized_data is not None and
            self.get_balance_sheet_data() is not None and
            self.get_income_statement_data() is not None
        )

    def __repr__(self):
        return (
            f"FinancialStatement(id={self.id}, company={self.company_name}, "
            f"type={self.statement_type.value}, year={self.fiscal_year}, "
            f"quarter={self.fiscal_quarter})"
        )
