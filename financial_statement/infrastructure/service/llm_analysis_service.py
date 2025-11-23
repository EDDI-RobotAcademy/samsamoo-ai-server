import asyncio
import json
import os
from typing import Dict, Any, List
import logging
from openai import AsyncOpenAI
from financial_statement.domain.financial_ratio import FinancialRatio
from financial_statement.application.port.llm_analysis_service_port import LLMAnalysisServicePort

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Custom exception for LLM errors"""
    pass


class LLMAnalysisService(LLMAnalysisServicePort):
    """
    Implementation of LLM analysis service using OpenAI API.
    Stage 3 of the analysis pipeline - qualitative interpretation.

    Uses async/await for parallel API calls to improve performance.
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")

        # Allow disabling LLM analysis via environment variable
        disable_llm = os.getenv("DISABLE_LLM_ANALYSIS", "false").lower() == "true"

        if not api_key or disable_llm:
            if disable_llm:
                logger.warning("LLM analysis disabled via DISABLE_LLM_ANALYSIS environment variable")
            else:
                logger.warning("OPENAI_API_KEY not set - LLM analysis will be skipped")
            self.client = None
            self.api_available = False
        else:
            self.client = AsyncOpenAI(api_key=api_key)
            self.api_available = True

        # Use gpt-4o or gpt-4-turbo (gpt-4 legacy model requires special access)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")  # Default to GPT-4o for financial analysis
        self.max_tokens = 2000
        self.temperature = 0.3  # Lower temperature for more consistent financial analysis

    async def generate_kpi_summary(
        self,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio]
    ) -> str:
        """
        Generate executive KPI summary using LLM.
        Focuses on key performance indicators and overall financial health.
        """
        logger.info("Generating KPI summary with LLM")

        try:
            # Prepare context for LLM
            context = self._prepare_kpi_context(financial_data, ratios)

            prompt = f"""You are a financial analyst. Provide a concise executive summary of the key performance indicators (KPIs) for this company.

Financial Data:
{context}

Generate a professional KPI summary (maximum 300 words) covering:
1. Overall financial health assessment
2. Key strengths and weaknesses
3. Critical metrics that stand out
4. Brief comparison to industry standards if applicable

Focus on actionable insights for executives."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert financial analyst specializing in corporate financial analysis and KPI interpretation."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            kpi_summary = response.choices[0].message.content.strip()
            logger.info("KPI summary generated successfully")
            return kpi_summary

        except Exception as e:
            logger.error(f"Failed to generate KPI summary: {e}")
            raise LLMError(f"LLM API call failed for KPI summary: {e}")

    async def generate_statement_table_summary(
        self,
        financial_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate structured summary of financial statement tables using LLM.
        Returns key highlights and simplified representations.
        """
        logger.info("Generating statement table summary with LLM")

        try:
            bs = financial_data.get("balance_sheet", {})
            is_data = financial_data.get("income_statement", {})

            prompt = f"""Analyze these financial statements and provide a structured summary.

Balance Sheet:
{json.dumps(bs, indent=2)}

Income Statement:
{json.dumps(is_data, indent=2)}

Provide your response in JSON format with the following structure:
{{
    "balance_sheet_summary": {{
        "total_assets": <value>,
        "total_liabilities": <value>,
        "total_equity": <value>,
        "key_insights": "<brief insight about balance sheet>"
    }},
    "income_statement_summary": {{
        "revenue": <value>,
        "net_income": <value>,
        "profitability": "<brief assessment>",
        "key_insights": "<brief insight about income statement>"
    }},
    "key_highlights": [
        "<highlight 1>",
        "<highlight 2>",
        "<highlight 3>"
    ]
}}

Be concise and focus on the most important information."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert financial analyst. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content.strip()
            table_summary = json.loads(content)

            logger.info("Statement table summary generated successfully")
            return table_summary

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            # Return fallback structure
            return self._create_fallback_table_summary(financial_data)
        except Exception as e:
            logger.error(f"Failed to generate table summary: {e}")
            raise LLMError(f"LLM API call failed for table summary: {e}")

    async def generate_ratio_analysis(
        self,
        ratios: List[FinancialRatio],
        financial_data: Dict[str, Any]
    ) -> str:
        """
        Generate interpretation and analysis of financial ratios using LLM.
        Provides insights on profitability, liquidity, leverage, and efficiency.
        """
        logger.info("Generating ratio analysis with LLM")

        try:
            # Organize ratios by category
            ratio_context = self._prepare_ratio_context(ratios, financial_data)

            prompt = f"""You are a financial analyst. Analyze these financial ratios and provide professional insights.

Financial Ratios:
{ratio_context}

Provide a comprehensive ratio analysis (maximum 400 words) covering:
1. Profitability Analysis: ROA, ROE, profit margins
2. Liquidity Analysis: Current ratio, quick ratio
3. Leverage Analysis: Debt ratio, financial stability
4. Efficiency Analysis: Asset turnover, operational efficiency

For each category:
- Interpret what the ratios indicate
- Identify strengths and weaknesses
- Provide actionable recommendations

Focus on practical insights for business decision-making."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert financial analyst specializing in ratio analysis and corporate finance."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            ratio_analysis = response.choices[0].message.content.strip()
            logger.info("Ratio analysis generated successfully")
            return ratio_analysis

        except Exception as e:
            logger.error(f"Failed to generate ratio analysis: {e}")
            raise LLMError(f"LLM API call failed for ratio analysis: {e}")

    async def generate_complete_analysis(
        self,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio]
    ) -> Dict[str, Any]:
        """
        Generate complete LLM analysis (all three components in parallel).
        Uses asyncio.gather for concurrent API calls to improve performance.
        Skips API calls if API is unavailable (uses fallback templates immediately).
        """
        # Check if API is available - skip LLM calls if not
        if not self.api_available:
            logger.warning("OpenAI API unavailable - using template-based analysis only")
            return {
                "kpi_summary": self._create_fallback_kpi_summary(financial_data, ratios),
                "statement_table_summary": self._create_fallback_table_summary(financial_data),
                "ratio_analysis": self._create_fallback_ratio_analysis(ratios)
            }

        logger.info("Generating complete LLM analysis (parallel execution)")

        try:
            # Execute all three analyses in parallel
            kpi_task = self.generate_kpi_summary(financial_data, ratios)
            table_task = self.generate_statement_table_summary(financial_data)
            ratio_task = self.generate_ratio_analysis(ratios, financial_data)

            kpi_summary, table_summary, ratio_analysis = await asyncio.gather(
                kpi_task,
                table_task,
                ratio_task,
                return_exceptions=True
            )

            # Check for exceptions and mark API as unavailable if quota errors occur
            if isinstance(kpi_summary, Exception):
                logger.error(f"KPI summary failed: {kpi_summary}")
                if "insufficient_quota" in str(kpi_summary) or "429" in str(kpi_summary):
                    self.api_available = False
                    logger.warning("OpenAI API quota exceeded - disabling future API calls")
                kpi_summary = self._create_fallback_kpi_summary(financial_data, ratios)

            if isinstance(table_summary, Exception):
                logger.error(f"Table summary failed: {table_summary}")
                if "insufficient_quota" in str(table_summary) or "429" in str(table_summary):
                    self.api_available = False
                    logger.warning("OpenAI API quota exceeded - disabling future API calls")
                table_summary = self._create_fallback_table_summary(financial_data)

            if isinstance(ratio_analysis, Exception):
                logger.error(f"Ratio analysis failed: {ratio_analysis}")
                if "insufficient_quota" in str(ratio_analysis) or "429" in str(ratio_analysis):
                    self.api_available = False
                    logger.warning("OpenAI API quota exceeded - disabling future API calls")
                ratio_analysis = self._create_fallback_ratio_analysis(ratios)

            result = {
                "kpi_summary": kpi_summary,
                "statement_table_summary": table_summary,
                "ratio_analysis": ratio_analysis
            }

            logger.info("Complete LLM analysis generated successfully")
            return result

        except Exception as e:
            logger.error(f"Failed to generate complete analysis: {e}")
            raise LLMError(f"Complete analysis generation failed: {e}")

    def _prepare_kpi_context(self, financial_data: Dict[str, Any], ratios: List[FinancialRatio]) -> str:
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

    def _prepare_ratio_context(self, ratios: List[FinancialRatio], financial_data: Dict[str, Any]) -> str:
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

    def _create_fallback_kpi_summary(self, financial_data: Dict[str, Any], ratios: List[FinancialRatio]) -> str:
        """Create template-based KPI summary if LLM fails"""
        bs = financial_data.get("balance_sheet", {})
        is_data = financial_data.get("income_statement", {})

        return f"""Financial KPI Summary (Template-Based)

Total Assets: {bs.get('total_assets', 0):,.0f}
Total Equity: {bs.get('total_equity', 0):,.0f}
Revenue: {is_data.get('revenue', 0):,.0f}
Net Income: {is_data.get('net_income', 0):,.0f}

The company has calculated {len(ratios)} financial ratios for detailed analysis.
Please review the detailed ratio analysis section for comprehensive insights.

Note: This is a template-based summary. LLM analysis was unavailable."""

    def _create_fallback_table_summary(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create template-based table summary if LLM fails"""
        bs = financial_data.get("balance_sheet", {})
        is_data = financial_data.get("income_statement", {})

        return {
            "balance_sheet_summary": {
                "total_assets": bs.get("total_assets", 0),
                "total_liabilities": bs.get("total_liabilities", 0),
                "total_equity": bs.get("total_equity", 0),
                "key_insights": "Template-based summary - LLM analysis unavailable"
            },
            "income_statement_summary": {
                "revenue": is_data.get("revenue", 0),
                "net_income": is_data.get("net_income", 0),
                "profitability": "See ratio analysis for profitability assessment",
                "key_insights": "Template-based summary - LLM analysis unavailable"
            },
            "key_highlights": [
                "Financial data extracted successfully",
                "Ratios calculated using standard formulas",
                "Detailed analysis available in ratio section"
            ]
        }

    def _create_fallback_ratio_analysis(self, ratios: List[FinancialRatio]) -> str:
        """Create template-based ratio analysis if LLM fails"""
        analysis_parts = ["Financial Ratio Analysis (Template-Based)\n"]

        # Group ratios by category
        profitability = [r for r in ratios if r.is_profitability_ratio()]
        liquidity = [r for r in ratios if r.is_liquidity_ratio()]
        leverage = [r for r in ratios if r.is_leverage_ratio()]
        efficiency = [r for r in ratios if r.is_efficiency_ratio()]

        if profitability:
            analysis_parts.append("\nProfitability Ratios:")
            for ratio in profitability:
                analysis_parts.append(f"- {ratio.ratio_type}: {ratio.as_percentage()}")

        if liquidity:
            analysis_parts.append("\nLiquidity Ratios:")
            for ratio in liquidity:
                analysis_parts.append(f"- {ratio.ratio_type}: {ratio.as_percentage()}")

        if leverage:
            analysis_parts.append("\nLeverage Ratios:")
            for ratio in leverage:
                analysis_parts.append(f"- {ratio.ratio_type}: {ratio.as_percentage()}")

        if efficiency:
            analysis_parts.append("\nEfficiency Ratios:")
            for ratio in efficiency:
                analysis_parts.append(f"- {ratio.ratio_type}: {ratio.as_percentage()}")

        analysis_parts.append("\nNote: This is a template-based summary. LLM interpretation was unavailable.")

        return "\n".join(analysis_parts)
