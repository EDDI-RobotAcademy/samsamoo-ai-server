"""
Test script for multi-provider LLM system.
Demonstrates provider selection and generates a complete financial analysis report.
"""
import asyncio
import os
import sys
from decimal import Decimal
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from financial_statement.domain.financial_ratio import FinancialRatio
# Import directly from module files to avoid loading other services
import importlib.util

# Load provider modules directly
spec = importlib.util.spec_from_file_location(
    "llm_providers",
    os.path.join(os.path.dirname(__file__),
                 "financial_statement/infrastructure/service/llm_providers/__init__.py")
)
llm_providers = importlib.util.module_from_spec(spec)
sys.modules["llm_providers"] = llm_providers
spec.loader.exec_module(llm_providers)

spec_v2 = importlib.util.spec_from_file_location(
    "llm_analysis_service_v2",
    os.path.join(os.path.dirname(__file__),
                 "financial_statement/infrastructure/service/llm_analysis_service_v2.py")
)
llm_service = importlib.util.module_from_spec(spec_v2)
sys.modules["llm_analysis_service_v2"] = llm_service

# Load FinancialRatio domain class
spec_ratio = importlib.util.spec_from_file_location(
    "financial_ratio",
    os.path.join(os.path.dirname(__file__),
                 "financial_statement/domain/financial_ratio.py")
)
financial_ratio = importlib.util.module_from_spec(spec_ratio)
sys.modules["financial_ratio"] = financial_ratio
spec_ratio.loader.exec_module(financial_ratio)

# Now load the service
spec_v2.loader.exec_module(llm_service)

LLMProviderFactory = llm_providers.LLMProviderFactory
TemplateProvider = llm_providers.TemplateProvider
OpenAIProvider = llm_providers.OpenAIProvider
AnthropicProvider = llm_providers.AnthropicProvider
LLMAnalysisServiceV2 = llm_service.LLMAnalysisServiceV2
FinancialRatio = financial_ratio.FinancialRatio


# Sample financial data for testing
SAMPLE_FINANCIAL_DATA = {
    "balance_sheet": {
        "total_assets": 150000000,
        "current_assets": 65000000,
        "total_liabilities": 45000000,
        "current_liabilities": 18900000,
        "total_equity": 105000000
    },
    "income_statement": {
        "revenue": 220000000,
        "net_income": 28000000,
        "operating_income": 35000000,
        "cost_of_goods_sold": 130000000
    }
}

# Sample financial ratios
SAMPLE_RATIOS = [
    FinancialRatio(
        id=1,
        statement_id=1,
        ratio_type="CURRENT_RATIO",
        ratio_value=Decimal("3.4392"),
        calculated_at=datetime.now()
    ),
    FinancialRatio(
        id=2,
        statement_id=1,
        ratio_type="QUICK_RATIO",
        ratio_value=Decimal("3.4392"),
        calculated_at=datetime.now()
    ),
    FinancialRatio(
        id=3,
        statement_id=1,
        ratio_type="ROA",
        ratio_value=Decimal("18.67"),
        calculated_at=datetime.now()
    ),
    FinancialRatio(
        id=4,
        statement_id=1,
        ratio_type="ROE",
        ratio_value=Decimal("26.67"),
        calculated_at=datetime.now()
    ),
    FinancialRatio(
        id=5,
        statement_id=1,
        ratio_type="DEBT_TO_EQUITY",
        ratio_value=Decimal("0.4286"),
        calculated_at=datetime.now()
    ),
    FinancialRatio(
        id=6,
        statement_id=1,
        ratio_type="PROFIT_MARGIN",
        ratio_value=Decimal("12.73"),
        calculated_at=datetime.now()
    )
]


async def test_provider(provider_name: str, provider):
    """Test a specific LLM provider"""
    print(f"\n{'='*80}")
    print(f"Testing Provider: {provider.get_provider_name()}")
    print(f"Available: {provider.is_available()}")
    print(f"{'='*80}\n")

    # Create service with this provider
    service = LLMAnalysisServiceV2(provider=provider)

    try:
        # Generate complete analysis
        result = await service.generate_complete_analysis(
            financial_data=SAMPLE_FINANCIAL_DATA,
            ratios=SAMPLE_RATIOS
        )

        # Display results
        print("✅ Analysis completed successfully!\n")

        print("📊 KPI Summary:")
        print("-" * 80)
        print(result["kpi_summary"])

        print("\n📋 Statement Table Summary:")
        print("-" * 80)
        import json
        print(json.dumps(result["statement_table_summary"], indent=2))

        print("\n📈 Ratio Analysis:")
        print("-" * 80)
        print(result["ratio_analysis"])

        return True

    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return False


async def main():
    """Main test function"""
    print("="*80)
    print("Multi-Provider LLM System Test")
    print("="*80)

    # Show available providers
    available = LLMProviderFactory.get_available_providers()
    print("\n📦 Available Providers:")
    for provider_type, info in available.items():
        status = "✅ Configured" if info["configured"] else "⚠️  Not Configured"
        print(f"  • {info['name']}: {status}")
        print(f"    Models: {', '.join(info['models'])}")

    # Test with Template Provider (always works)
    print("\n" + "="*80)
    print("TEST 1: Template Provider (No AI)")
    print("="*80)
    template_provider = TemplateProvider()
    await test_provider("template", template_provider)

    # Test with auto-detected provider
    print("\n" + "="*80)
    print("TEST 2: Auto-Detected Provider")
    print("="*80)
    auto_provider = LLMProviderFactory.create_provider()
    await test_provider("auto", auto_provider)

    # Show configuration instructions
    print("\n" + "="*80)
    print("Configuration Instructions")
    print("="*80)
    print("""
Add to your .env file to configure LLM providers:

# Auto-detect provider (default)
LLM_PROVIDER=auto

# Or specify a provider explicitly:
# LLM_PROVIDER=openai
# LLM_PROVIDER=anthropic
# LLM_PROVIDER=template

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o  # or gpt-4-turbo, gpt-3.5-turbo

# Anthropic Configuration (requires: pip install anthropic)
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022  # or claude-3-opus-20240229

# Template provider (no configuration needed, always available)
    """)

    print("\n✅ All tests completed!")


if __name__ == "__main__":
    # Set template provider for testing (works without any API keys)
    os.environ["LLM_PROVIDER"] = "template"

    asyncio.run(main())
