import pandas as pd
from typing import List, Dict, Any
from decimal import Decimal
import logging
from financial_statement.domain.financial_ratio import FinancialRatio
from financial_statement.application.port.calculation_service_port import CalculationServicePort

logger = logging.getLogger(__name__)


class CalculationError(Exception):
    """Custom exception for calculation errors"""
    pass


class RatioCalculationService(CalculationServicePort):
    """
    Implementation of ratio calculation service using pandas.
    Stage 2 of the analysis pipeline - pure deterministic calculations.

    CRITICAL: NO LLM USAGE - All calculations must be deterministic and auditable.
    """

    def calculate_profitability_ratios(self, financial_data: Dict[str, Any]) -> List[FinancialRatio]:
        """Calculate ROA, ROE, ROI, and profit margins"""
        logger.info("Calculating profitability ratios")

        ratios = []
        bs = financial_data.get("balance_sheet", {})
        is_data = financial_data.get("income_statement", {})

        # Log input values for debugging
        net_income = float(is_data.get("net_income", 0))
        total_assets = float(bs.get("total_assets", 0))
        total_equity = float(bs.get("total_equity", 0))
        revenue = float(is_data.get("revenue", 0))
        operating_income = float(is_data.get("operating_income", 0))

        logger.info(f"Profitability inputs: net_income={net_income}, total_assets={total_assets}, "
                   f"total_equity={total_equity}, revenue={revenue}, operating_income={operating_income}")

        try:
            # ROA = Net Income / Total Assets
            if total_assets > 0:
                roa = (net_income / total_assets) * 100
                ratios.append(FinancialRatio(
                    statement_id=0,  # Will be set by use case
                    ratio_type=FinancialRatio.ROA,
                    ratio_value=Decimal(str(round(roa, 4)))
                ))
                logger.info(f"ROA calculated: {roa:.4f}%")
            else:
                logger.warning("ROA skipped: total_assets is 0")

            # ROE = Net Income / Total Equity
            if total_equity > 0:
                roe = (net_income / total_equity) * 100
                ratios.append(FinancialRatio(
                    statement_id=0,
                    ratio_type=FinancialRatio.ROE,
                    ratio_value=Decimal(str(round(roe, 4)))
                ))
                logger.info(f"ROE calculated: {roe:.4f}%")
            else:
                logger.warning("ROE skipped: total_equity is 0")

            # Profit Margin = Net Income / Revenue
            if revenue > 0:
                profit_margin = (net_income / revenue) * 100
                ratios.append(FinancialRatio(
                    statement_id=0,
                    ratio_type=FinancialRatio.PROFIT_MARGIN,
                    ratio_value=Decimal(str(round(profit_margin, 4)))
                ))
                logger.info(f"Profit Margin calculated: {profit_margin:.4f}%")
            else:
                logger.warning("Profit Margin skipped: revenue is 0")

            # Operating Margin = Operating Income / Revenue
            if revenue > 0:
                operating_margin = (operating_income / revenue) * 100
                ratios.append(FinancialRatio(
                    statement_id=0,
                    ratio_type=FinancialRatio.OPERATING_MARGIN,
                    ratio_value=Decimal(str(round(operating_margin, 4)))
                ))
                logger.info(f"Operating Margin calculated: {operating_margin:.4f}%")
            else:
                logger.warning("Operating Margin skipped: revenue is 0")

        except Exception as e:
            logger.error(f"Error calculating profitability ratios: {e}")
            raise CalculationError(f"Failed to calculate profitability ratios: {e}")

        logger.info(f"Calculated {len(ratios)} profitability ratios")
        return ratios

    def calculate_liquidity_ratios(self, financial_data: Dict[str, Any]) -> List[FinancialRatio]:
        """Calculate current ratio and quick ratio"""
        logger.info("Calculating liquidity ratios")

        ratios = []
        bs = financial_data.get("balance_sheet", {})

        # Log input values for debugging
        current_assets = float(bs.get("current_assets", 0))
        current_liabilities = float(bs.get("current_liabilities", 0))
        inventory = float(bs.get("inventory", 0))

        logger.info(f"Liquidity inputs: current_assets={current_assets}, "
                   f"current_liabilities={current_liabilities}, inventory={inventory}")

        try:
            # Current Ratio = Current Assets / Current Liabilities
            if current_liabilities > 0:
                current_ratio = current_assets / current_liabilities
                ratios.append(FinancialRatio(
                    statement_id=0,
                    ratio_type=FinancialRatio.CURRENT_RATIO,
                    ratio_value=Decimal(str(round(current_ratio, 4)))
                ))
                logger.info(f"Current Ratio calculated: {current_ratio:.4f}")
            else:
                logger.warning("Current Ratio skipped: current_liabilities is 0")

            # Quick Ratio = (Current Assets - Inventory) / Current Liabilities
            if current_liabilities > 0:
                quick_ratio = (current_assets - inventory) / current_liabilities
                ratios.append(FinancialRatio(
                    statement_id=0,
                    ratio_type=FinancialRatio.QUICK_RATIO,
                    ratio_value=Decimal(str(round(quick_ratio, 4)))
                ))
                logger.info(f"Quick Ratio calculated: {quick_ratio:.4f}")
            else:
                logger.warning("Quick Ratio skipped: current_liabilities is 0")

        except Exception as e:
            logger.error(f"Error calculating liquidity ratios: {e}")
            raise CalculationError(f"Failed to calculate liquidity ratios: {e}")

        logger.info(f"Calculated {len(ratios)} liquidity ratios")
        return ratios

    def calculate_leverage_ratios(self, financial_data: Dict[str, Any]) -> List[FinancialRatio]:
        """Calculate debt ratio and equity multiplier"""
        logger.info("Calculating leverage ratios")

        ratios = []
        bs = financial_data.get("balance_sheet", {})

        # Log input values for debugging
        total_assets = float(bs.get("total_assets", 0))
        total_liabilities = float(bs.get("total_liabilities", 0))
        total_equity = float(bs.get("total_equity", 0))

        logger.info(f"Leverage inputs: total_assets={total_assets}, "
                   f"total_liabilities={total_liabilities}, total_equity={total_equity}")

        try:
            # Debt Ratio = Total Liabilities / Total Assets
            if total_assets > 0:
                debt_ratio = total_liabilities / total_assets
                ratios.append(FinancialRatio(
                    statement_id=0,
                    ratio_type=FinancialRatio.DEBT_RATIO,
                    ratio_value=Decimal(str(round(debt_ratio, 4)))
                ))
                logger.info(f"Debt Ratio calculated: {debt_ratio:.4f}")
            else:
                logger.warning("Debt Ratio skipped: total_assets is 0")

            # Equity Multiplier = Total Assets / Total Equity
            if total_equity > 0:
                equity_multiplier = total_assets / total_equity
                ratios.append(FinancialRatio(
                    statement_id=0,
                    ratio_type=FinancialRatio.EQUITY_MULTIPLIER,
                    ratio_value=Decimal(str(round(equity_multiplier, 4)))
                ))
                logger.info(f"Equity Multiplier calculated: {equity_multiplier:.4f}")
            else:
                logger.warning("Equity Multiplier skipped: total_equity is 0")

        except Exception as e:
            logger.error(f"Error calculating leverage ratios: {e}")
            raise CalculationError(f"Failed to calculate leverage ratios: {e}")

        logger.info(f"Calculated {len(ratios)} leverage ratios")
        return ratios

    def calculate_efficiency_ratios(self, financial_data: Dict[str, Any]) -> List[FinancialRatio]:
        """Calculate asset turnover ratio"""
        logger.info("Calculating efficiency ratios")

        ratios = []
        bs = financial_data.get("balance_sheet", {})
        is_data = financial_data.get("income_statement", {})

        # Log input values for debugging
        revenue = float(is_data.get("revenue", 0))
        total_assets = float(bs.get("total_assets", 0))

        logger.info(f"Efficiency inputs: revenue={revenue}, total_assets={total_assets}")

        try:
            # Asset Turnover = Revenue / Total Assets
            if total_assets > 0:
                asset_turnover = revenue / total_assets
                ratios.append(FinancialRatio(
                    statement_id=0,
                    ratio_type=FinancialRatio.ASSET_TURNOVER,
                    ratio_value=Decimal(str(round(asset_turnover, 4)))
                ))
                logger.info(f"Asset Turnover calculated: {asset_turnover:.4f}")
            else:
                logger.warning("Asset Turnover skipped: total_assets is 0")

        except Exception as e:
            logger.error(f"Error calculating efficiency ratios: {e}")
            raise CalculationError(f"Failed to calculate efficiency ratios: {e}")

        logger.info(f"Calculated {len(ratios)} efficiency ratios")
        return ratios

    def calculate_all_ratios(
        self,
        financial_data: Dict[str, Any],
        statement_id: int = 0,
        skip_statement_id_validation: bool = False
    ) -> List[FinancialRatio]:
        """
        Calculate all available financial ratios.
        Returns partial results if some calculations fail (graceful degradation).

        Args:
            financial_data: Extracted financial data with balance_sheet, income_statement
            statement_id: ID of the financial statement (0 for non-persisted XBRL analysis)
            skip_statement_id_validation: If True, skip validation of statement_id > 0
                                         (useful for XBRL analysis without DB persistence)
        """
        logger.info(f"Calculating all ratios for statement {statement_id}")

        all_ratios = []

        # Try each ratio category, collect whatever succeeds
        try:
            profitability = self.calculate_profitability_ratios(financial_data)
            all_ratios.extend(profitability)
        except CalculationError as e:
            logger.warning(f"Profitability ratios failed: {e}")

        try:
            liquidity = self.calculate_liquidity_ratios(financial_data)
            all_ratios.extend(liquidity)
        except CalculationError as e:
            logger.warning(f"Liquidity ratios failed: {e}")

        try:
            leverage = self.calculate_leverage_ratios(financial_data)
            all_ratios.extend(leverage)
        except CalculationError as e:
            logger.warning(f"Leverage ratios failed: {e}")

        try:
            efficiency = self.calculate_efficiency_ratios(financial_data)
            all_ratios.extend(efficiency)
        except CalculationError as e:
            logger.warning(f"Efficiency ratios failed: {e}")

        # Set statement_id for all ratios
        for ratio in all_ratios:
            ratio.statement_id = statement_id

        if len(all_ratios) == 0:
            raise CalculationError("Failed to calculate any financial ratios")

        # Final validation: ensure all ratios have valid statement_id (unless skipped for XBRL)
        if not skip_statement_id_validation:
            for ratio in all_ratios:
                if ratio.statement_id <= 0:
                    raise CalculationError(f"Ratio {ratio.ratio_type} has invalid statement_id: {ratio.statement_id}")

        logger.info(f"Successfully calculated {len(all_ratios)} ratios total")
        return all_ratios

    def calculate_yoy_growth(self, current_data: Dict[str, Any], previous_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate year-over-year growth rates for key metrics.
        This is a helper method, not part of the port interface.
        """
        logger.info("Calculating YoY growth rates")

        growth_rates = {}

        try:
            # Revenue growth
            current_revenue = float(current_data.get("income_statement", {}).get("revenue", 0))
            previous_revenue = float(previous_data.get("income_statement", {}).get("revenue", 0))

            if previous_revenue > 0:
                revenue_growth = ((current_revenue - previous_revenue) / previous_revenue) * 100
                growth_rates["revenue_growth"] = round(revenue_growth, 2)

            # Net income growth
            current_ni = float(current_data.get("income_statement", {}).get("net_income", 0))
            previous_ni = float(previous_data.get("income_statement", {}).get("net_income", 0))

            if previous_ni > 0:
                ni_growth = ((current_ni - previous_ni) / previous_ni) * 100
                growth_rates["net_income_growth"] = round(ni_growth, 2)

            # Asset growth
            current_assets = float(current_data.get("balance_sheet", {}).get("total_assets", 0))
            previous_assets = float(previous_data.get("balance_sheet", {}).get("total_assets", 0))

            if previous_assets > 0:
                asset_growth = ((current_assets - previous_assets) / previous_assets) * 100
                growth_rates["asset_growth"] = round(asset_growth, 2)

        except Exception as e:
            logger.warning(f"Error calculating some growth rates: {e}")

        return growth_rates

    def validate_calculation_inputs(self, financial_data: Dict[str, Any]) -> bool:
        """
        Validate that financial data has minimum required fields for calculations.
        Raises CalculationError if validation fails.
        """
        bs = financial_data.get("balance_sheet", {})
        is_data = financial_data.get("income_statement", {})

        required_bs_fields = ["total_assets", "total_liabilities", "total_equity"]
        required_is_fields = ["revenue", "net_income"]

        for field in required_bs_fields:
            if field not in bs:
                raise CalculationError(f"Missing required balance sheet field: {field}")
            if bs[field] is None:
                raise CalculationError(f"Balance sheet field {field} is None")

        for field in required_is_fields:
            if field not in is_data:
                raise CalculationError(f"Missing required income statement field: {field}")
            if is_data[field] is None:
                raise CalculationError(f"Income statement field {field} is None")

        return True
