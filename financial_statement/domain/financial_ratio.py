from datetime import datetime
from typing import Optional
from decimal import Decimal


class FinancialRatio:
    """
    Domain entity representing a calculated financial ratio.
    Immutable value object with validation.
    """

    # Ratio type constants
    ROA = "ROA"  # Return on Assets
    ROE = "ROE"  # Return on Equity
    ROI = "ROI"  # Return on Investment
    DEBT_RATIO = "DEBT_RATIO"
    CURRENT_RATIO = "CURRENT_RATIO"
    QUICK_RATIO = "QUICK_RATIO"
    PROFIT_MARGIN = "PROFIT_MARGIN"
    OPERATING_MARGIN = "OPERATING_MARGIN"
    ASSET_TURNOVER = "ASSET_TURNOVER"
    EQUITY_MULTIPLIER = "EQUITY_MULTIPLIER"

    VALID_RATIO_TYPES = {
        ROA, ROE, ROI, DEBT_RATIO, CURRENT_RATIO, QUICK_RATIO,
        PROFIT_MARGIN, OPERATING_MARGIN, ASSET_TURNOVER, EQUITY_MULTIPLIER
    }

    def __init__(
        self,
        statement_id: int,
        ratio_type: str,
        ratio_value: Decimal
    ):
        self.id: Optional[int] = None
        self.statement_id = statement_id
        self.ratio_type = ratio_type
        self.ratio_value = ratio_value
        self.calculated_at: datetime = datetime.utcnow()

        self._validate()

    def _validate(self):
        """Validate business rules for financial ratios"""
        if self.ratio_type not in self.VALID_RATIO_TYPES:
            raise ValueError(f"Invalid ratio type: {self.ratio_type}")

        # Allow statement_id=0 as temporary placeholder during construction
        # The calculation service will set the correct ID before saving
        if self.statement_id is None or self.statement_id < 0:
            raise ValueError("Statement ID cannot be negative or None")

        # Validate ratio value bounds (detect obvious calculation errors)
        self._validate_ratio_bounds()

    def _validate_ratio_bounds(self):
        """
        Validate ratio values are within reasonable bounds.
        These are sanity checks to catch calculation errors.
        """
        value = float(self.ratio_value)

        # Ratios that should be percentages (0-100% typically, but can exceed)
        percentage_ratios = {
            self.ROA, self.ROE, self.ROI,
            self.PROFIT_MARGIN, self.OPERATING_MARGIN
        }

        # Ratios that should be positive
        positive_ratios = {
            self.CURRENT_RATIO, self.QUICK_RATIO,
            self.ASSET_TURNOVER, self.EQUITY_MULTIPLIER
        }

        # Check percentage ratios (allow negative for losses, but flag extremes)
        if self.ratio_type in percentage_ratios:
            if value < -100 or value > 500:
                raise ValueError(
                    f"{self.ratio_type} value {value} is outside reasonable bounds "
                    f"(-100% to 500%)"
                )

        # Check positive ratios
        if self.ratio_type in positive_ratios:
            if value < 0:
                raise ValueError(
                    f"{self.ratio_type} must be positive, got {value}"
                )
            if value > 1000:
                raise ValueError(
                    f"{self.ratio_type} value {value} seems unreasonably high (>1000)"
                )

        # Debt ratio should be between 0 and 10 (1000%)
        if self.ratio_type == self.DEBT_RATIO:
            if value < 0 or value > 10:
                raise ValueError(
                    f"Debt ratio {value} is outside reasonable bounds (0 to 10)"
                )

    def as_percentage(self) -> str:
        """Format ratio as percentage string"""
        if self.ratio_type in {
            self.ROA, self.ROE, self.ROI,
            self.PROFIT_MARGIN, self.OPERATING_MARGIN
        }:
            return f"{float(self.ratio_value):.2f}%"
        return f"{float(self.ratio_value):.4f}"

    def is_profitability_ratio(self) -> bool:
        """Check if this is a profitability ratio"""
        return self.ratio_type in {self.ROA, self.ROE, self.ROI, self.PROFIT_MARGIN, self.OPERATING_MARGIN}

    def is_liquidity_ratio(self) -> bool:
        """Check if this is a liquidity ratio"""
        return self.ratio_type in {self.CURRENT_RATIO, self.QUICK_RATIO}

    def is_leverage_ratio(self) -> bool:
        """Check if this is a leverage ratio"""
        return self.ratio_type in {self.DEBT_RATIO, self.EQUITY_MULTIPLIER}

    def is_efficiency_ratio(self) -> bool:
        """Check if this is an efficiency ratio"""
        return self.ratio_type in {self.ASSET_TURNOVER}

    def __repr__(self):
        return (
            f"FinancialRatio(id={self.id}, type={self.ratio_type}, "
            f"value={self.as_percentage()}, statement_id={self.statement_id})"
        )

    def __eq__(self, other):
        if not isinstance(other, FinancialRatio):
            return False
        return (
            self.statement_id == other.statement_id and
            self.ratio_type == other.ratio_type and
            self.ratio_value == other.ratio_value
        )

    def __hash__(self):
        return hash((self.statement_id, self.ratio_type, self.ratio_value))
