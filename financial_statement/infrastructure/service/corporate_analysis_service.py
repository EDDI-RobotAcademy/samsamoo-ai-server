"""
Corporate Analysis Service

LLM-powered corporate evaluation based on XBRL financial data.
Analyzes financial ratios and provides comprehensive corporate assessment.
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal

from financial_statement.domain.financial_ratio import FinancialRatio
from financial_statement.domain.xbrl_document import XBRLDocument
from financial_statement.infrastructure.service.llm_providers import LLMProviderFactory, BaseLLMProvider, TemplateProvider

logger = logging.getLogger(__name__)


class CorporateAnalysisError(Exception):
    """Custom exception for corporate analysis errors"""
    pass


class CorporateAnalysisService:
    """
    LLM-powered corporate analysis service.
    
    Provides comprehensive analysis of corporations based on:
    - XBRL financial statement data
    - Calculated financial ratios
    - Industry context and benchmarks
    
    Analysis types:
    - Executive Summary (경영진 요약)
    - Financial Health Assessment (재무 건전성 평가)
    - Profitability Analysis (수익성 분석)
    - Liquidity Analysis (유동성 분석)
    - Leverage Analysis (레버리지 분석)
    - Investment Recommendation (투자 권고)
    """
    
    # Industry benchmark ratios (Korean market averages)
    INDUSTRY_BENCHMARKS = {
        'manufacturing': {
            'ROA': 5.0,
            'ROE': 10.0,
            'PROFIT_MARGIN': 5.0,
            'CURRENT_RATIO': 1.5,
            'DEBT_RATIO': 0.5,
        },
        'technology': {
            'ROA': 8.0,
            'ROE': 15.0,
            'PROFIT_MARGIN': 10.0,
            'CURRENT_RATIO': 2.0,
            'DEBT_RATIO': 0.3,
        },
        'finance': {
            'ROA': 1.0,
            'ROE': 8.0,
            'PROFIT_MARGIN': 15.0,
            'CURRENT_RATIO': 1.2,
            'DEBT_RATIO': 0.8,
        },
        'retail': {
            'ROA': 4.0,
            'ROE': 12.0,
            'PROFIT_MARGIN': 3.0,
            'CURRENT_RATIO': 1.3,
            'DEBT_RATIO': 0.4,
        },
        'default': {
            'ROA': 5.0,
            'ROE': 10.0,
            'PROFIT_MARGIN': 5.0,
            'CURRENT_RATIO': 1.5,
            'DEBT_RATIO': 0.5,
        }
    }
    
    def __init__(self, provider: BaseLLMProvider = None):
        """
        Initialize service with LLM provider.
        
        Args:
            provider: LLM provider instance. Auto-detects if None.
        """
        if provider is None:
            provider = LLMProviderFactory.create_provider()
        
        self.provider = provider
        logger.info(f"Corporate Analysis Service initialized with {provider.get_provider_name()}")
    
    async def generate_comprehensive_analysis(
        self,
        corp_name: str,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio],
        fiscal_year: int,
        industry: str = 'default'
    ) -> Dict[str, Any]:
        """
        Generate comprehensive corporate analysis.
        
        Args:
            corp_name: Corporation name
            financial_data: Normalized financial data (balance_sheet, income_statement, etc.)
            ratios: List of calculated FinancialRatio objects
            fiscal_year: Fiscal year being analyzed
            industry: Industry category for benchmark comparison
            
        Returns:
            Complete analysis report with multiple sections
        """
        logger.info(f"Generating comprehensive analysis for {corp_name} ({fiscal_year})")
        
        # Prepare analysis context
        context = self._prepare_analysis_context(
            corp_name, financial_data, ratios, fiscal_year, industry
        )
        
        # Generate all analysis sections in parallel
        tasks = [
            self._generate_executive_summary(context),
            self._generate_financial_health_assessment(context),
            self._generate_ratio_analysis(context),
            self._generate_investment_recommendation(context),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        executive_summary = results[0] if not isinstance(results[0], Exception) else self._fallback_executive_summary(context)
        financial_health = results[1] if not isinstance(results[1], Exception) else self._fallback_financial_health(context)
        ratio_analysis = results[2] if not isinstance(results[2], Exception) else self._fallback_ratio_analysis(context)
        investment_recommendation = results[3] if not isinstance(results[3], Exception) else self._fallback_investment_recommendation(context)
        
        return {
            'corp_name': corp_name,
            'fiscal_year': fiscal_year,
            'analysis_date': context['analysis_date'],
            'executive_summary': executive_summary,
            'financial_health': financial_health,
            'ratio_analysis': ratio_analysis,
            'investment_recommendation': investment_recommendation,
            'raw_data': {
                'financial_data': financial_data,
                'ratios': [{'type': r.ratio_type, 'value': float(r.ratio_value)} for r in ratios],
                'benchmarks': self.INDUSTRY_BENCHMARKS.get(industry, self.INDUSTRY_BENCHMARKS['default'])
            }
        }
    
    def _prepare_analysis_context(
        self,
        corp_name: str,
        financial_data: Dict[str, Any],
        ratios: List[FinancialRatio],
        fiscal_year: int,
        industry: str
    ) -> Dict[str, Any]:
        """Prepare context dictionary for analysis prompts"""
        from datetime import datetime
        
        # Convert ratios to dictionary
        ratio_dict = {}
        for ratio in ratios:
            ratio_dict[ratio.ratio_type] = float(ratio.ratio_value)
        
        # Get benchmarks
        benchmarks = self.INDUSTRY_BENCHMARKS.get(industry, self.INDUSTRY_BENCHMARKS['default'])
        
        # Calculate deviations from benchmarks
        benchmark_comparison = {}
        for ratio_type, benchmark_value in benchmarks.items():
            if ratio_type in ratio_dict:
                actual = ratio_dict[ratio_type]
                diff = actual - benchmark_value
                diff_pct = (diff / benchmark_value * 100) if benchmark_value != 0 else 0
                benchmark_comparison[ratio_type] = {
                    'actual': actual,
                    'benchmark': benchmark_value,
                    'difference': diff,
                    'difference_percent': diff_pct,
                    'status': 'above' if diff > 0 else 'below' if diff < 0 else 'equal'
                }
        
        # Format financial data for display
        bs = financial_data.get('balance_sheet', {})
        is_data = financial_data.get('income_statement', {})
        cf = financial_data.get('cash_flow_statement', {})
        
        return {
            'corp_name': corp_name,
            'fiscal_year': fiscal_year,
            'industry': industry,
            'analysis_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'balance_sheet': bs,
            'income_statement': is_data,
            'cash_flow': cf,
            'ratios': ratio_dict,
            'benchmarks': benchmarks,
            'benchmark_comparison': benchmark_comparison,
            'total_assets': bs.get('total_assets', 0),
            'total_liabilities': bs.get('total_liabilities', 0),
            'total_equity': bs.get('total_equity', 0),
            'revenue': is_data.get('revenue', 0),
            'net_income': is_data.get('net_income', 0),
            'operating_income': is_data.get('operating_income', 0),
        }
    
    async def _generate_executive_summary(self, context: Dict[str, Any]) -> str:
        """Generate executive summary of corporate performance"""
        if isinstance(self.provider, TemplateProvider):
            return self._fallback_executive_summary(context)
        
        if not self.provider.is_available():
            return self._fallback_executive_summary(context)
        
        system_prompt = """당신은 한국 기업 분석 전문가입니다. 
재무제표 데이터를 바탕으로 경영진과 투자자를 위한 명확하고 통찰력 있는 분석을 제공합니다.
모든 응답은 한국어로 작성해야 합니다."""
        
        user_prompt = f"""다음 재무 데이터를 바탕으로 {context['corp_name']}의 {context['fiscal_year']}년 경영진 요약을 작성하세요.

**재무 현황:**
- 총자산: {self._format_krw(context['total_assets'])}
- 총부채: {self._format_krw(context['total_liabilities'])}
- 총자본: {self._format_krw(context['total_equity'])}
- 매출액: {self._format_krw(context['revenue'])}
- 영업이익: {self._format_krw(context['operating_income'])}
- 당기순이익: {self._format_krw(context['net_income'])}

**주요 재무비율:**
- ROA (총자산이익률): {context['ratios'].get('ROA', 'N/A')}%
- ROE (자기자본이익률): {context['ratios'].get('ROE', 'N/A')}%
- 부채비율: {context['ratios'].get('DEBT_RATIO', 'N/A')}
- 유동비율: {context['ratios'].get('CURRENT_RATIO', 'N/A')}

다음 구조로 경영진 요약을 작성하세요 (300단어 이내):
1. 전반적인 재무 건전성 평가 (1-2문장)
2. 주요 강점 (2-3개)
3. 개선이 필요한 영역 (1-2개)
4. 핵심 결론

전문적이고 객관적인 어조를 유지하세요."""

        try:
            return await self.provider.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1500,
                temperature=0.3
            )
        except Exception as e:
            logger.error(f"Executive summary generation failed: {e}")
            return self._fallback_executive_summary(context)
    
    async def _generate_financial_health_assessment(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed financial health assessment"""
        if isinstance(self.provider, TemplateProvider):
            return self._fallback_financial_health(context)
        
        if not self.provider.is_available():
            return self._fallback_financial_health(context)
        
        system_prompt = """당신은 기업 신용 분석 전문가입니다.
재무제표를 분석하여 기업의 재무 건전성을 평가합니다.
JSON 형식으로만 응답하세요."""
        
        benchmark_text = "\n".join([
            f"- {k}: 실제 {v['actual']:.2f} vs 업계평균 {v['benchmark']:.2f} ({v['status']})"
            for k, v in context['benchmark_comparison'].items()
        ])
        
        user_prompt = f"""다음 재무 데이터를 분석하여 {context['corp_name']}의 재무 건전성을 평가하세요.

**업계 평균 대비 비교:**
{benchmark_text}

다음 JSON 형식으로 응답하세요:
{{
    "overall_score": <1-100 사이의 점수>,
    "rating": "<AAA/AA/A/BBB/BB/B/CCC 중 하나>",
    "strengths": ["강점1", "강점2", "강점3"],
    "weaknesses": ["약점1", "약점2"],
    "key_risks": ["리스크1", "리스크2"],
    "improvement_areas": ["개선영역1", "개선영역2"],
    "summary": "<전체 평가 요약 (2-3문장)>"
}}"""

        try:
            result = await self.provider.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1500,
                temperature=0.3
            )
            return result
        except Exception as e:
            logger.error(f"Financial health assessment failed: {e}")
            return self._fallback_financial_health(context)
    
    async def _generate_ratio_analysis(self, context: Dict[str, Any]) -> str:
        """Generate detailed ratio analysis"""
        if isinstance(self.provider, TemplateProvider):
            return self._fallback_ratio_analysis(context)
        
        if not self.provider.is_available():
            return self._fallback_ratio_analysis(context)
        
        system_prompt = """당신은 재무비율 분석 전문가입니다.
각 재무비율의 의미를 해석하고 기업 경영에 대한 시사점을 도출합니다.
모든 응답은 한국어로 작성하세요."""
        
        ratios = context['ratios']
        benchmarks = context['benchmarks']
        
        user_prompt = f"""다음 {context['corp_name']}의 재무비율을 분석하세요.

**수익성 지표:**
- ROA (총자산이익률): {ratios.get('ROA', 'N/A')}% (업계평균: {benchmarks.get('ROA', 'N/A')}%)
- ROE (자기자본이익률): {ratios.get('ROE', 'N/A')}% (업계평균: {benchmarks.get('ROE', 'N/A')}%)
- 순이익률: {ratios.get('PROFIT_MARGIN', 'N/A')}% (업계평균: {benchmarks.get('PROFIT_MARGIN', 'N/A')}%)
- 영업이익률: {ratios.get('OPERATING_MARGIN', 'N/A')}%

**안정성 지표:**
- 유동비율: {ratios.get('CURRENT_RATIO', 'N/A')} (업계평균: {benchmarks.get('CURRENT_RATIO', 'N/A')})
- 당좌비율: {ratios.get('QUICK_RATIO', 'N/A')}
- 부채비율: {ratios.get('DEBT_RATIO', 'N/A')} (업계평균: {benchmarks.get('DEBT_RATIO', 'N/A')})

**효율성 지표:**
- 총자산회전율: {ratios.get('ASSET_TURNOVER', 'N/A')}
- 자기자본배율: {ratios.get('EQUITY_MULTIPLIER', 'N/A')}

각 카테고리별로 분석하세요 (400단어 이내):
1. 수익성 분석: 수익 창출 능력과 효율성
2. 안정성 분석: 단기 및 장기 재무 안정성
3. 효율성 분석: 자산 활용 효율성
4. 종합 평가: 전반적인 재무 성과와 시사점"""

        try:
            return await self.provider.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2000,
                temperature=0.3
            )
        except Exception as e:
            logger.error(f"Ratio analysis generation failed: {e}")
            return self._fallback_ratio_analysis(context)
    
    async def _generate_investment_recommendation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate investment recommendation based on analysis"""
        if isinstance(self.provider, TemplateProvider):
            return self._fallback_investment_recommendation(context)
        
        if not self.provider.is_available():
            return self._fallback_investment_recommendation(context)
        
        system_prompt = """당신은 증권 분석가입니다.
재무 데이터를 바탕으로 투자 의견을 제시합니다.
JSON 형식으로만 응답하세요.
주의: 이 분석은 참고용이며 실제 투자 결정에 대한 책임은 투자자에게 있습니다."""
        
        user_prompt = f"""{context['corp_name']}의 재무 분석을 바탕으로 투자 의견을 제시하세요.

**핵심 지표:**
- ROE: {context['ratios'].get('ROE', 'N/A')}%
- ROA: {context['ratios'].get('ROA', 'N/A')}%
- 부채비율: {context['ratios'].get('DEBT_RATIO', 'N/A')}
- 유동비율: {context['ratios'].get('CURRENT_RATIO', 'N/A')}
- 순이익률: {context['ratios'].get('PROFIT_MARGIN', 'N/A')}%

다음 JSON 형식으로 응답하세요:
{{
    "recommendation": "<매수/보유/매도 중 하나>",
    "confidence": "<높음/중간/낮음 중 하나>",
    "target_investor": "<성장형/가치형/안정형 중 하나>",
    "time_horizon": "<단기/중기/장기>",
    "key_positives": ["긍정요인1", "긍정요인2"],
    "key_negatives": ["부정요인1", "부정요인2"],
    "catalyst": "<주요 모니터링 요소>",
    "risk_factors": ["리스크1", "리스크2"],
    "summary": "<투자 의견 요약 (2-3문장)>",
    "disclaimer": "본 분석은 참고용이며, 투자 결정에 대한 책임은 투자자 본인에게 있습니다."
}}"""

        try:
            result = await self.provider.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1500,
                temperature=0.3
            )
            # Always add disclaimer
            result['disclaimer'] = "본 분석은 참고용이며, 투자 결정에 대한 책임은 투자자 본인에게 있습니다."
            return result
        except Exception as e:
            logger.error(f"Investment recommendation generation failed: {e}")
            return self._fallback_investment_recommendation(context)
    
    # Fallback methods for when LLM is unavailable
    def _fallback_executive_summary(self, context: Dict[str, Any]) -> str:
        """Template-based executive summary"""
        corp_name = context['corp_name']
        fiscal_year = context['fiscal_year']
        ratios = context['ratios']
        
        roe = ratios.get('ROE', 0)
        roa = ratios.get('ROA', 0)
        debt_ratio = ratios.get('DEBT_RATIO', 1)
        current_ratio = ratios.get('CURRENT_RATIO', 1)
        
        # Determine overall assessment
        if roe > 10 and debt_ratio < 0.5:
            assessment = "양호한 재무 상태를 유지하고 있습니다."
        elif roe > 5 and debt_ratio < 0.7:
            assessment = "안정적인 재무 구조를 보이고 있습니다."
        else:
            assessment = "재무 개선이 필요한 상황입니다."
        
        return f"""**{corp_name} {fiscal_year}년 경영진 요약**

**1. 전반적 재무 건전성**
{corp_name}은(는) {assessment}

**2. 주요 강점**
- ROE {roe:.1f}%로 자기자본 대비 수익 창출 능력 {'양호' if roe > 10 else '보통'}
- 유동비율 {current_ratio:.2f}로 단기 지급 능력 {'양호' if current_ratio > 1.5 else '보통'}

**3. 개선 필요 영역**
- 부채비율 {debt_ratio:.2f}로 {'재무 안정성 양호' if debt_ratio < 0.5 else '부채 관리 필요'}

**4. 핵심 결론**
{corp_name}의 {fiscal_year}년 재무 성과를 종합하면, {'전반적으로 건전한 재무 구조를 유지하고 있으며 지속적인 성장이 기대됩니다.' if roe > 8 and debt_ratio < 0.6 else '재무 구조 개선을 통한 경쟁력 강화가 필요합니다.'}
"""
    
    def _fallback_financial_health(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Template-based financial health assessment"""
        ratios = context['ratios']
        
        # Calculate score based on ratios
        score = 50  # Base score
        if ratios.get('ROE', 0) > 10:
            score += 15
        if ratios.get('DEBT_RATIO', 1) < 0.5:
            score += 15
        if ratios.get('CURRENT_RATIO', 0) > 1.5:
            score += 10
        if ratios.get('PROFIT_MARGIN', 0) > 5:
            score += 10
        
        score = min(100, max(0, score))
        
        # Determine rating
        if score >= 80:
            rating = 'AA'
        elif score >= 70:
            rating = 'A'
        elif score >= 60:
            rating = 'BBB'
        elif score >= 50:
            rating = 'BB'
        else:
            rating = 'B'
        
        return {
            'overall_score': score,
            'rating': rating,
            'strengths': ['재무제표 분석 완료', '주요 비율 산출 완료'],
            'weaknesses': ['상세 분석을 위해 LLM 서비스 활성화 필요'],
            'key_risks': ['시장 변동성', '산업 경쟁 심화'],
            'improvement_areas': ['수익성 개선', '비용 효율화'],
            'summary': f'{context["corp_name"]}의 재무 건전성 점수는 {score}점이며, 신용등급 {rating}에 해당합니다.'
        }
    
    def _fallback_ratio_analysis(self, context: Dict[str, Any]) -> str:
        """Template-based ratio analysis"""
        ratios = context['ratios']
        benchmarks = context['benchmarks']
        
        return f"""**{context['corp_name']} 재무비율 분석**

**1. 수익성 분석**
- ROA: {ratios.get('ROA', 'N/A')}% (업계평균: {benchmarks.get('ROA', 'N/A')}%)
- ROE: {ratios.get('ROE', 'N/A')}% (업계평균: {benchmarks.get('ROE', 'N/A')}%)
- 순이익률: {ratios.get('PROFIT_MARGIN', 'N/A')}%

**2. 안정성 분석**
- 유동비율: {ratios.get('CURRENT_RATIO', 'N/A')} (적정수준: 1.5 이상)
- 부채비율: {ratios.get('DEBT_RATIO', 'N/A')} (적정수준: 0.5 이하)

**3. 효율성 분석**
- 총자산회전율: {ratios.get('ASSET_TURNOVER', 'N/A')}

**4. 종합 평가**
재무비율 분석이 완료되었습니다. 상세한 해석을 위해 LLM 서비스를 활성화하세요.
"""
    
    def _fallback_investment_recommendation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Template-based investment recommendation"""
        ratios = context['ratios']
        
        roe = ratios.get('ROE', 0)
        debt_ratio = ratios.get('DEBT_RATIO', 1)
        
        if roe > 12 and debt_ratio < 0.4:
            recommendation = '매수'
            confidence = '중간'
        elif roe > 8 and debt_ratio < 0.6:
            recommendation = '보유'
            confidence = '중간'
        else:
            recommendation = '보유'
            confidence = '낮음'
        
        return {
            'recommendation': recommendation,
            'confidence': confidence,
            'target_investor': '가치형',
            'time_horizon': '중기',
            'key_positives': ['재무제표 기반 분석 완료'],
            'key_negatives': ['상세 분석 필요'],
            'catalyst': '실적 발표',
            'risk_factors': ['시장 리스크', '산업 리스크'],
            'summary': f'{context["corp_name"]}에 대해 {recommendation} 의견을 제시합니다.',
            'disclaimer': '본 분석은 참고용이며, 투자 결정에 대한 책임은 투자자 본인에게 있습니다.'
        }
    
    def _format_krw(self, value: float) -> str:
        """Format value as Korean Won"""
        if value is None or value == 0:
            return 'N/A'
        
        if abs(value) >= 1e12:
            return f"{value / 1e12:.2f}조원"
        elif abs(value) >= 1e8:
            return f"{value / 1e8:.2f}억원"
        elif abs(value) >= 1e4:
            return f"{value / 1e4:.2f}만원"
        else:
            return f"{value:,.0f}원"
