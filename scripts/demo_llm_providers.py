"""
Standalone demonstration of multi-provider LLM system.
Shows how the new provider system works without full app dependencies.
"""
import asyncio
import os
from decimal import Decimal
from datetime import datetime


# Mock FinancialRatio class for standalone demo
class FinancialRatio:
    def __init__(self, id, statement_id, ratio_type, ratio_value, calculated_at):
        self.id = id
        self.statement_id = statement_id
        self.ratio_type = ratio_type
        self.ratio_value = ratio_value
        self.calculated_at = calculated_at

    def as_percentage(self):
        return f"{float(self.ratio_value):.2f}%"

    def is_profitability_ratio(self):
        return self.ratio_type in ["ROA", "ROE", "PROFIT_MARGIN", "GROSS_MARGIN"]

    def is_liquidity_ratio(self):
        return self.ratio_type in ["CURRENT_RATIO", "QUICK_RATIO", "CASH_RATIO"]

    def is_leverage_ratio(self):
        return self.ratio_type in ["DEBT_TO_EQUITY", "DEBT_RATIO", "EQUITY_MULTIPLIER"]

    def is_efficiency_ratio(self):
        return self.ratio_type in ["ASSET_TURNOVER", "INVENTORY_TURNOVER"]


# Sample financial data
SAMPLE_DATA = {
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
        "operating_income": 35000000
    }
}

SAMPLE_RATIOS = [
    FinancialRatio(1, 1, "CURRENT_RATIO", Decimal("3.44"), datetime.now()),
    FinancialRatio(2, 1, "QUICK_RATIO", Decimal("3.44"), datetime.now()),
    FinancialRatio(3, 1, "ROA", Decimal("18.67"), datetime.now()),
    FinancialRatio(4, 1, "ROE", Decimal("26.67"), datetime.now()),
    FinancialRatio(5, 1, "DEBT_TO_EQUITY", Decimal("0.43"), datetime.now()),
    FinancialRatio(6, 1, "PROFIT_MARGIN", Decimal("12.73"), datetime.now()),
]


def print_section(title, char="="):
    print(f"\n{char*80}")
    print(f"{title}")
    print(f"{char*80}\n")


async def demo_template_provider():
    """Demonstrate template provider (no AI)"""
    print_section("DEMONSTRATION: Template Provider (No AI Required)", "=")

    # Import template provider
    from financial_statement.infrastructure.service.llm_providers.template_provider import TemplateProvider

    provider = TemplateProvider()

    print(f"✅ Provider: {provider.get_provider_name()}")
    print(f"✅ Available: {provider.is_available()}")

    print_section("1. KPI Summary", "-")
    kpi_summary = provider.create_kpi_summary(SAMPLE_DATA, SAMPLE_RATIOS)
    print(kpi_summary)

    print_section("2. Table Summary", "-")
    table_summary = provider.create_table_summary(SAMPLE_DATA)
    import json
    print(json.dumps(table_summary, indent=2))

    print_section("3. Ratio Analysis", "-")
    ratio_analysis = provider.create_ratio_analysis(SAMPLE_RATIOS)
    print(ratio_analysis)


def demo_provider_factory():
    """Demonstrate provider factory"""
    print_section("DEMONSTRATION: Provider Factory", "=")

    from financial_statement.infrastructure.service.llm_providers.provider_factory import LLMProviderFactory

    # Show available providers
    available = LLMProviderFactory.get_available_providers()
    print("📦 Available Providers:\n")

    for provider_type, info in available.items():
        status = "✅ Configured" if info["configured"] else "⚠️  Not Configured"
        print(f"  {info['name']}: {status}")
        print(f"    Type: {provider_type}")
        print(f"    Models: {', '.join(info['models'])}")
        print()

    # Create provider
    print_section("Creating Provider with Auto-Detection", "-")
    os.environ["LLM_PROVIDER"] = "template"  # Force template for demo
    provider = LLMProviderFactory.create_provider()
    print(f"✅ Created Provider: {provider.get_provider_name()}")
    print(f"✅ Is Available: {provider.is_available()}")


def show_configuration_guide():
    """Show configuration instructions"""
    print_section("CONFIGURATION GUIDE", "=")

    print("""
🔧 How to Configure LLM Providers

Add these settings to your .env file:

1️⃣  CHOOSE A PROVIDER:
   LLM_PROVIDER=auto          # Auto-detect (default)
   LLM_PROVIDER=openai        # Force OpenAI
   LLM_PROVIDER=anthropic     # Force Anthropic Claude
   LLM_PROVIDER=template      # Use templates (no AI)

2️⃣  OPENAI CONFIGURATION:
   OPENAI_API_KEY=sk-...      # Your OpenAI API key
   OPENAI_MODEL=gpt-4o        # Model: gpt-4o, gpt-4-turbo, gpt-3.5-turbo

3️⃣  ANTHROPIC CONFIGURATION:
   ANTHROPIC_API_KEY=sk-...   # Your Anthropic API key
   ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

4️⃣  NO CONFIGURATION NEEDED FOR TEMPLATE PROVIDER!
   Template provider works immediately without any API keys.

📚 Features:
   ✅ Automatic fallback to templates if API fails
   ✅ Graceful quota exhaustion handling
   ✅ Parallel analysis generation
   ✅ Provider-specific optimizations
   ✅ Zero-downtime switching between providers

🔗 Get API Keys:
   OpenAI: https://platform.openai.com/api-keys
   Anthropic: https://console.anthropic.com/

💡 Pro Tips:
   • Use template provider during development (free, instant)
   • Use gpt-3.5-turbo for cost-effective production
   • Use gpt-4o or Claude for highest quality analysis
   • System automatically falls back to templates if quota exhausted
    """)


def main():
    """Main demonstration"""
    print_section("Multi-Provider LLM System - Complete Demo", "=")

    print("""
This demonstration shows the new multi-provider LLM system for
financial statement analysis.

Key Features:
✅ Multiple LLM providers (OpenAI, Anthropic, Template)
✅ Automatic provider detection and selection
✅ Graceful fallback to templates
✅ Zero-configuration template provider
✅ Easy provider switching via environment variables
    """)

    # Demo 1: Provider Factory
    demo_provider_factory()

    # Demo 2: Template Provider
    asyncio.run(demo_template_provider())

    # Demo 3: Configuration Guide
    show_configuration_guide()

    print_section("✅ Demo Complete!", "=")
    print("""
Next Steps:
1. Update your .env file with LLM provider settings
2. Choose your provider (or use 'auto' for automatic detection)
3. Run your financial statement analysis
4. System will automatically use templates if API unavailable

The system is production-ready and handles all edge cases gracefully!
    """)


if __name__ == "__main__":
    main()
