from typing import Dict, Any, List
import logging
from financial_statement.domain.financial_ratio import FinancialRatio

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class PipelineValidator:
    """
    Validation layer between pipeline stages.
    Ensures data quality and completeness at each stage transition.
    """

    @staticmethod
    def validate_stage1_output(extracted_data: Dict[str, Any]) -> bool:
        """
        Validate Stage 1 (PDF Extraction) → Stage 2 (Calculation) transition.

        Checks:
        - Required sections present (balance_sheet, income_statement)
        - Required financial items extracted
        - Values are numeric and reasonable

        Note: Validation is lenient to allow processing with partial data.
        Missing fields will generate warnings but not block processing.
        """
        logger.info("Validating Stage 1 output")

        try:
            # Check required sections
            if "balance_sheet" not in extracted_data:
                logger.warning("Missing balance_sheet section in extracted data")
                extracted_data["balance_sheet"] = {}

            if "income_statement" not in extracted_data:
                logger.warning("Missing income_statement section in extracted data")
                extracted_data["income_statement"] = {}

            bs = extracted_data["balance_sheet"]
            is_data = extracted_data["income_statement"]

            # Check if completely empty
            if not bs and not is_data:
                raise ValidationError("No financial data extracted - both balance sheet and income statement are empty")

            # Validate balance sheet items (warnings only)
            required_bs_items = ["total_assets", "total_liabilities", "total_equity"]
            missing_bs = []
            for item in required_bs_items:
                if item not in bs:
                    missing_bs.append(item)
                else:
                    value = bs[item]
                    if not isinstance(value, (int, float)):
                        logger.warning(f"Balance sheet item {item} is not numeric: {value}")
                    elif value < 0:
                        logger.warning(f"Negative value for {item}: {value}")

            if missing_bs:
                logger.warning(f"Missing balance sheet items: {', '.join(missing_bs)}. Proceeding with available data.")

            # Validate balance sheet equation (if all items present)
            if "total_assets" in bs and "total_liabilities" in bs and "total_equity" in bs:
                try:
                    assets = float(bs["total_assets"])
                    liabilities = float(bs["total_liabilities"])
                    equity = float(bs["total_equity"])

                    balance_check = abs(assets - (liabilities + equity))
                    tolerance = assets * 0.01  # 1% tolerance for rounding

                    if balance_check > tolerance:
                        logger.warning(
                            f"Balance sheet equation mismatch: "
                            f"Assets={assets}, Liabilities+Equity={liabilities + equity}, "
                            f"Difference={balance_check}"
                        )
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not validate balance sheet equation: {e}")

            # Validate income statement items (warnings only)
            required_is_items = ["revenue", "operating_income", "net_income"]
            missing_is = []
            for item in required_is_items:
                if item not in is_data:
                    missing_is.append(item)
                else:
                    value = is_data[item]
                    if not isinstance(value, (int, float)):
                        logger.warning(f"Income statement item {item} is not numeric: {value}")

            if missing_is:
                logger.warning(f"Missing income statement items: {', '.join(missing_is)}. Proceeding with available data.")

            # Sanity check: revenue should generally be positive (if present)
            if "revenue" in is_data:
                try:
                    revenue = float(is_data["revenue"])
                    if revenue <= 0:
                        logger.warning(f"Revenue is not positive: {revenue}")
                except (ValueError, TypeError):
                    logger.warning("Could not validate revenue value")

            logger.info("Stage 1 output validation passed (with warnings for missing data)")
            return True

        except ValidationError as e:
            logger.error(f"Stage 1 validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Stage 1 validation: {e}")
            raise ValidationError(f"Stage 1 validation error: {e}")

    @staticmethod
    def validate_stage2_output(ratios: List[FinancialRatio]) -> bool:
        """
        Validate Stage 2 (Calculation) → Stage 3 (LLM Analysis) transition.

        Checks:
        - At least one ratio calculated successfully
        - Ratio values are within reasonable bounds
        - No NaN or infinite values
        """
        logger.info("Validating Stage 2 output")

        try:
            if not ratios or len(ratios) == 0:
                raise ValidationError("No ratios calculated - cannot proceed to analysis")

            # Check minimum ratio coverage
            ratio_types = {r.ratio_type for r in ratios}

            # At least one profitability ratio
            profitability_ratios = {
                FinancialRatio.ROA, FinancialRatio.ROE, FinancialRatio.PROFIT_MARGIN
            }
            if not ratio_types.intersection(profitability_ratios):
                logger.warning("No profitability ratios calculated")

            # Validate each ratio
            for ratio in ratios:
                # Check for invalid values
                value = float(ratio.ratio_value)

                if value != value:  # Check for NaN
                    raise ValidationError(f"Ratio {ratio.ratio_type} has NaN value")

                if abs(value) == float('inf'):
                    raise ValidationError(f"Ratio {ratio.ratio_type} has infinite value")

                # Ratios are already validated by domain entity, but double-check
                try:
                    ratio._validate_ratio_bounds()
                except ValueError as e:
                    raise ValidationError(f"Ratio validation failed: {e}")

            logger.info(f"Stage 2 output validation passed ({len(ratios)} ratios)")
            return True

        except ValidationError as e:
            logger.error(f"Stage 2 validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Stage 2 validation: {e}")
            raise ValidationError(f"Stage 2 validation error: {e}")

    @staticmethod
    def validate_stage3_output(analysis_result: Dict[str, Any]) -> bool:
        """
        Validate Stage 3 (LLM Analysis) → Stage 4 (Report Generation) transition.

        Checks:
        - All required analysis sections present
        - Text content is not empty or truncated
        - JSON structure is valid
        """
        logger.info("Validating Stage 3 output")

        try:
            # Check required keys
            required_keys = ["kpi_summary", "statement_table_summary", "ratio_analysis"]
            for key in required_keys:
                if key not in analysis_result:
                    raise ValidationError(f"Missing required analysis section: {key}")

            # Validate KPI summary
            kpi_summary = analysis_result["kpi_summary"]
            if not isinstance(kpi_summary, str):
                raise ValidationError("KPI summary is not a string")

            if len(kpi_summary.strip()) < 50:
                raise ValidationError(f"KPI summary too short ({len(kpi_summary)} chars) - likely truncated")

            if len(kpi_summary) > 5000:
                logger.warning(f"KPI summary very long ({len(kpi_summary)} chars)")

            # Validate statement table summary
            table_summary = analysis_result["statement_table_summary"]
            if not isinstance(table_summary, dict):
                raise ValidationError("Statement table summary is not a dictionary")

            required_table_keys = ["balance_sheet_summary", "income_statement_summary"]
            for key in required_table_keys:
                if key not in table_summary:
                    raise ValidationError(f"Missing {key} in statement table summary")

            # Validate ratio analysis
            ratio_analysis = analysis_result["ratio_analysis"]
            if not isinstance(ratio_analysis, str):
                raise ValidationError("Ratio analysis is not a string")

            if len(ratio_analysis.strip()) < 50:
                raise ValidationError(f"Ratio analysis too short ({len(ratio_analysis)} chars) - likely truncated")

            if len(ratio_analysis) > 5000:
                logger.warning(f"Ratio analysis very long ({len(ratio_analysis)} chars)")

            logger.info("Stage 3 output validation passed")
            return True

        except ValidationError as e:
            logger.error(f"Stage 3 validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Stage 3 validation: {e}")
            raise ValidationError(f"Stage 3 validation error: {e}")

    @staticmethod
    def validate_final_output(
        statement: Any,
        ratios: List[FinancialRatio],
        report: Any,
        chart_paths: List[str]
    ) -> bool:
        """
        Final validation before returning results to user.

        Checks:
        - All pipeline stages completed successfully
        - Data consistency across components
        - Output files exist (charts, PDFs)
        """
        logger.info("Performing final output validation")

        try:
            # Validate statement
            if not statement.is_complete():
                raise ValidationError("Financial statement is incomplete")

            # Validate ratios
            if not ratios or len(ratios) == 0:
                raise ValidationError("No ratios generated")

            # Validate report
            if not report.is_complete():
                logger.warning("Analysis report is incomplete")

            # Validate chart files
            import os
            for chart_path in chart_paths:
                if not os.path.exists(chart_path):
                    logger.warning(f"Chart file missing: {chart_path}")

            logger.info("Final output validation passed")
            return True

        except ValidationError as e:
            logger.error(f"Final validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in final validation: {e}")
            raise ValidationError(f"Final validation error: {e}")
