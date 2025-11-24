import asyncio
import json
import logging
from typing import Dict, Any, List
from financial_statement.domain.financial_ratio import FinancialRatio
from financial_statement.application.port.llm_analysis_service_port import LLMAnalysisServicePort
from .llm_providers import LLMProviderFactory, BaseLLMProvider, TemplateProvider

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Custom exception for LLM errors"""
    pass


class LLMAnalysisServiceV2(LLMAnalysisServicePort):
    """
    Multi-provider LLM analysis service implementation.
    Stage 3 of the analysis pipeline - qualitative interpretation.

    Supports multiple LLM providers:
    - OpenAI (GPT-4o, GPT-4-turbo, GPT-3.5-turbo)
    - Anthropic (Claude-3.5-sonnet, Claude-3-opus)
    - Template (No AI, always available)

    Configuration via environment variables:
    - LLM_PROVIDER: "openai", "anthropic", "template", or "auto" (default)
    - OPENAI_API_KEY, OPENAI_MODEL
    - ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    """

    def __init__(self, provider: BaseLLMProvider = None):
        """
        Initialize service with a specific provider or auto-detect.

        Args:
            provider: BaseLLMProvider instance (optional, will auto-detect if None)
        """
        if provider is None:
            provider = LLMProviderFactory.create_provider()

        self.provider = provider
        logger.info(f"LLM Analysis Service initialized with provider: {provider.get_provider_name()}")

    async def generate_kpi_summary(
        self,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio]
    ) -> str:
        """
        Generate executive KPI summary using configured LLM provider.
        Falls back to template-based summary if provider fails.
        """
        logger.info("Generating KPI summary")

        # Use template provider's specialized method if available
        if isinstance(self.provider, TemplateProvider):
            return self.provider.create_kpi_summary(financial_data, ratios)

        # Check if provider is available
        if not self.provider.is_available():
            logger.warning("LLM provider unavailable, using template fallback")
            template = TemplateProvider()
            return template.create_kpi_summary(financial_data, ratios)

        try:
            # Prepare context for LLM
            context = self.provider.prepare_kpi_context(financial_data, ratios)

            system_prompt = "You are an expert financial analyst specializing in corporate financial analysis and KPI interpretation."

            user_prompt = f"""You are a financial analyst. Provide a concise executive summary of the key performance indicators (KPIs) for this company.

Financial Data:
{context}

Generate a professional KPI summary (maximum 300 words) covering:
1. Overall financial health assessment
2. Key strengths and weaknesses
3. Critical metrics that stand out
4. Brief comparison to industry standards if applicable

Focus on actionable insights for executives."""

            result = await self.provider.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2000,
                temperature=0.3
            )

            logger.info("KPI summary generated successfully")
            return result

        except Exception as e:
            logger.error(f"Failed to generate KPI summary with {self.provider.get_provider_name()}: {e}")
            logger.info("Falling back to template-based summary")
            template = TemplateProvider()
            return template.create_kpi_summary(financial_data, ratios)

    async def generate_statement_table_summary(
        self,
        financial_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate structured summary of financial statement tables.
        Falls back to template-based summary if provider fails.
        """
        logger.info("Generating statement table summary")

        # Use template provider's specialized method if available
        if isinstance(self.provider, TemplateProvider):
            return self.provider.create_table_summary(financial_data)

        # Check if provider is available
        if not self.provider.is_available():
            logger.warning("LLM provider unavailable, using template fallback")
            template = TemplateProvider()
            return template.create_table_summary(financial_data)

        try:
            bs = financial_data.get("balance_sheet", {})
            is_data = financial_data.get("income_statement", {})

            system_prompt = "You are an expert financial analyst. Respond only with valid JSON."

            user_prompt = f"""Analyze these financial statements and provide a structured summary.

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

            result = await self.provider.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2000,
                temperature=0.3
            )

            logger.info("Statement table summary generated successfully")
            return result

        except Exception as e:
            logger.error(f"Failed to generate table summary with {self.provider.get_provider_name()}: {e}")
            logger.info("Falling back to template-based summary")
            template = TemplateProvider()
            return template.create_table_summary(financial_data)

    async def generate_ratio_analysis(
        self,
        ratios: List[FinancialRatio],
        financial_data: Dict[str, Any]
    ) -> str:
        """
        Generate interpretation and analysis of financial ratios.
        Falls back to template-based analysis if provider fails.
        """
        logger.info("Generating ratio analysis")

        # Use template provider's specialized method if available
        if isinstance(self.provider, TemplateProvider):
            return self.provider.create_ratio_analysis(ratios)

        # Check if provider is available
        if not self.provider.is_available():
            logger.warning("LLM provider unavailable, using template fallback")
            template = TemplateProvider()
            return template.create_ratio_analysis(ratios)

        try:
            # Organize ratios by category
            ratio_context = self.provider.prepare_ratio_context(ratios, financial_data)

            system_prompt = "You are an expert financial analyst specializing in ratio analysis and corporate finance."

            user_prompt = f"""You are a financial analyst. Analyze these financial ratios and provide professional insights.

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

            result = await self.provider.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2000,
                temperature=0.3
            )

            logger.info("Ratio analysis generated successfully")
            return result

        except Exception as e:
            logger.error(f"Failed to generate ratio analysis with {self.provider.get_provider_name()}: {e}")
            logger.info("Falling back to template-based analysis")
            template = TemplateProvider()
            return template.create_ratio_analysis(ratios)

    async def generate_complete_analysis(
        self,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio]
    ) -> Dict[str, Any]:
        """
        Generate complete LLM analysis (all three components in parallel).
        Uses asyncio.gather for concurrent API calls to improve performance.
        Automatically falls back to template-based analysis if provider fails.
        """
        logger.info(f"Generating complete analysis with {self.provider.get_provider_name()}")

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

            # Handle any exceptions from parallel execution
            if isinstance(kpi_summary, Exception):
                logger.error(f"KPI summary failed: {kpi_summary}")
                template = TemplateProvider()
                kpi_summary = template.create_kpi_summary(financial_data, ratios)

            if isinstance(table_summary, Exception):
                logger.error(f"Table summary failed: {table_summary}")
                template = TemplateProvider()
                table_summary = template.create_table_summary(financial_data)

            if isinstance(ratio_analysis, Exception):
                logger.error(f"Ratio analysis failed: {ratio_analysis}")
                template = TemplateProvider()
                ratio_analysis = template.create_ratio_analysis(ratios)

            result = {
                "kpi_summary": kpi_summary,
                "statement_table_summary": table_summary,
                "ratio_analysis": ratio_analysis
            }

            logger.info("Complete analysis generated successfully")
            return result

        except Exception as e:
            logger.error(f"Failed to generate complete analysis: {e}")
            raise LLMError(f"Complete analysis generation failed: {e}")
