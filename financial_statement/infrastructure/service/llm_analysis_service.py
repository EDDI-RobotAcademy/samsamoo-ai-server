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

            system_prompt = "You are an expert financial analyst specializing in corporate financial analysis and KPI interpretation. You must respond in Korean language (한국어)."

            user_prompt = f"""당신은 재무 분석 전문가입니다. 이 회사의 핵심 성과 지표(KPI)에 대한 간결한 경영진 요약을 제공하십시오.

재무 데이터:
{context}

다음을 포함하는 전문적인 KPI 요약을 한국어로 작성하십시오 (최대 300단어):
1. 전반적인 재무 건전성 평가
2. 주요 강점과 약점
3. 눈에 띄는 핵심 지표
4. 해당되는 경우 업계 표준과의 간단한 비교

경영진을 위한 실행 가능한 인사이트에 집중하십시오.

**중요: 모든 응답은 반드시 한국어로 작성해야 합니다.**"""

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

            system_prompt = "You are an expert financial analyst. Respond only with valid JSON. All text content in the JSON must be in Korean language (한국어)."

            user_prompt = f"""이 재무제표를 분석하고 구조화된 요약을 제공하십시오.

대차대조표:
{json.dumps(bs, indent=2)}

손익계산서:
{json.dumps(is_data, indent=2)}

다음 구조의 JSON 형식으로 응답을 제공하십시오 (모든 텍스트는 한국어로):
{{
    "balance_sheet_summary": {{
        "total_assets": <value>,
        "total_liabilities": <value>,
        "total_equity": <value>,
        "key_insights": "<대차대조표에 대한 간단한 인사이트>"
    }},
    "income_statement_summary": {{
        "revenue": <value>,
        "net_income": <value>,
        "profitability": "<수익성 간단 평가>",
        "key_insights": "<손익계산서에 대한 간단한 인사이트>"
    }},
    "key_highlights": [
        "<주요 포인트 1>",
        "<주요 포인트 2>",
        "<주요 포인트 3>"
    ]
}}

간결하게 작성하고 가장 중요한 정보에 집중하십시오.

**중요: JSON 내의 모든 텍스트 필드는 반드시 한국어로 작성해야 합니다.**"""

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
        If no ratios are provided, performs direct LLM analysis of raw financial data.
        """
        logger.info("Generating ratio analysis")

        # Handle case where ratio calculation failed - analyze raw data directly
        if not ratios or len(ratios) == 0:
            logger.info("No ratios provided - performing direct LLM analysis of financial data")
            return await self._generate_direct_financial_analysis(financial_data)

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

            system_prompt = "You are an expert financial analyst specializing in ratio analysis and corporate finance. You must respond in Korean language (한국어)."

            user_prompt = f"""당신은 재무 분석 전문가입니다. 이 재무 비율들을 분석하고 전문적인 인사이트를 제공하십시오.

재무 비율:
{ratio_context}

다음을 포함하는 포괄적인 비율 분석을 한국어로 작성하십시오 (최대 400단어):
1. 수익성 분석: ROA, ROE, 이익률
2. 유동성 분석: 유동비율, 당좌비율
3. 레버리지 분석: 부채비율, 재무 안정성
4. 효율성 분석: 자산회전율, 운영 효율성

각 카테고리에 대해:
- 비율이 무엇을 나타내는지 해석
- 강점과 약점 식별
- 실행 가능한 권장사항 제공

비즈니스 의사결정을 위한 실용적인 인사이트에 집중하십시오.

**중요: 모든 응답은 반드시 한국어로 작성해야 합니다.**"""

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

    async def _generate_direct_financial_analysis(
        self,
        financial_data: Dict[str, Any]
    ) -> str:
        """
        Generate direct analysis of raw financial data when ratio calculation fails.
        LLM analyzes the extracted data directly without pre-calculated ratios.

        Args:
            financial_data: Normalized financial data from PDF extraction

        Returns:
            String containing LLM analysis of financial data
        """
        logger.info("Generating direct financial analysis (ratio calculation was skipped)")

        # Use template if no LLM available
        if isinstance(self.provider, TemplateProvider) or not self.provider.is_available():
            logger.warning("LLM provider unavailable for direct analysis, using template")
            return self._create_direct_analysis_template(financial_data)

        try:
            bs = financial_data.get("balance_sheet", {})
            is_data = financial_data.get("income_statement", {})

            system_prompt = "You are an expert financial analyst. Analyze the raw financial data directly and provide comprehensive insights. You must respond in Korean language (한국어)."

            user_prompt = f"""당신은 재무 분석 전문가입니다. 아래의 추출된 재무 데이터를 직접 분석하고 전문적인 인사이트를 제공하십시오.

참고: 재무비율 자동 계산이 실패하여 원본 데이터를 직접 분석합니다.

대차대조표 데이터:
{json.dumps(bs, indent=2, ensure_ascii=False)}

손익계산서 데이터:
{json.dumps(is_data, indent=2, ensure_ascii=False)}

다음을 포함하는 포괄적인 재무 분석을 한국어로 작성하십시오 (최대 500단어):

1. **재무 상태 분석**
   - 자산 구조 분석 (자산 구성 및 품질)
   - 부채 구조 분석 (레버리지 수준)
   - 자본 건전성 평가

2. **수익성 분석**
   - 매출 및 수익 추세
   - 영업이익과 순이익 분석
   - 수익 마진 평가

3. **재무 건전성 종합 평가**
   - 주요 강점
   - 주의가 필요한 영역
   - 개선 권장사항

4. **주요 재무비율 추정** (가능한 경우)
   - 데이터에서 계산 가능한 비율들을 직접 계산하여 제시

비즈니스 의사결정을 위한 실용적인 인사이트에 집중하십시오.

**중요: 모든 응답은 반드시 한국어로 작성해야 합니다.**"""

            result = await self.provider.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2500,
                temperature=0.3
            )

            logger.info("Direct financial analysis generated successfully")
            return result

        except Exception as e:
            logger.error(f"Failed to generate direct analysis: {e}")
            return self._create_direct_analysis_template(financial_data)

    def _create_direct_analysis_template(self, financial_data: Dict[str, Any]) -> str:
        """
        Create template-based direct analysis when LLM is unavailable.

        Args:
            financial_data: Normalized financial data

        Returns:
            Template string with basic financial analysis
        """
        bs = financial_data.get("balance_sheet", {})
        is_data = financial_data.get("income_statement", {})

        # Extract key values with defaults
        total_assets = bs.get("total_assets", 0)
        total_liabilities = bs.get("total_liabilities", 0)
        total_equity = bs.get("total_equity", 0)
        revenue = is_data.get("revenue", 0)
        net_income = is_data.get("net_income", 0)
        operating_income = is_data.get("operating_income", 0)

        analysis_parts = [
            "📊 재무 데이터 직접 분석",
            "",
            "⚠️ 참고: 재무비율 자동 계산이 실패하여 원본 데이터를 직접 분석했습니다.",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "📈 대차대조표 요약:",
        ]

        if total_assets:
            analysis_parts.append(f"  • 총자산: {total_assets:,.0f}원")
        if total_liabilities:
            analysis_parts.append(f"  • 총부채: {total_liabilities:,.0f}원")
        if total_equity:
            analysis_parts.append(f"  • 총자본: {total_equity:,.0f}원")

        analysis_parts.extend([
            "",
            "💰 손익계산서 요약:",
        ])

        if revenue:
            analysis_parts.append(f"  • 매출액: {revenue:,.0f}원")
        if operating_income:
            analysis_parts.append(f"  • 영업이익: {operating_income:,.0f}원")
        if net_income:
            analysis_parts.append(f"  • 당기순이익: {net_income:,.0f}원")

        # Calculate basic ratios if possible
        analysis_parts.extend([
            "",
            "📐 계산 가능한 기본 비율:",
        ])

        calculated_any = False
        if total_assets and total_liabilities:
            debt_ratio = (total_liabilities / total_assets) * 100
            analysis_parts.append(f"  • 부채비율: {debt_ratio:.2f}%")
            calculated_any = True

        if total_equity and net_income:
            roe = (net_income / total_equity) * 100
            analysis_parts.append(f"  • ROE (자기자본이익률): {roe:.2f}%")
            calculated_any = True

        if revenue and net_income:
            profit_margin = (net_income / revenue) * 100
            analysis_parts.append(f"  • 순이익률: {profit_margin:.2f}%")
            calculated_any = True

        if not calculated_any:
            analysis_parts.append("  • 비율 계산에 필요한 데이터가 부족합니다.")

        analysis_parts.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "💡 권장사항:",
            "  • LLM API를 활성화하면 더 상세한 분석을 받을 수 있습니다.",
            "  • 재무제표의 데이터 품질을 확인해 주세요.",
            "  • 필요시 원본 PDF 파일을 다시 업로드해 주세요.",
        ])

        return "\n".join(analysis_parts)

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


# Alias for backward compatibility
LLMAnalysisService = LLMAnalysisServiceV2
