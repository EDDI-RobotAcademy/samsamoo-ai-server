"""Quick demo of multi-provider LLM system - Direct execution"""
import sys
import os

# Add path
sys.path.insert(0, os.path.dirname(__file__))

from decimal import Decimal
from datetime import datetime


# Mock FinancialRatio
class FinancialRatio:
    def __init__(self, id, statement_id, ratio_type, ratio_value, calculated_at):
        self.id, self.statement_id = id, statement_id
        self.ratio_type, self.ratio_value, self.calculated_at = ratio_type, ratio_value, calculated_at

    def as_percentage(self):
        return f"{float(self.ratio_value):.2f}%"

    def is_profitability_ratio(self):
        return self.ratio_type in ["ROA", "ROE", "PROFIT_MARGIN"]

    def is_liquidity_ratio(self):
        return self.ratio_type in ["CURRENT_RATIO", "QUICK_RATIO"]

    def is_leverage_ratio(self):
        return self.ratio_type in ["DEBT_TO_EQUITY", "DEBT_RATIO"]

    def is_efficiency_ratio(self):
        return self.ratio_type in ["ASSET_TURNOVER"]


# Load template provider directly
exec(open("financial_statement/infrastructure/service/llm_providers/base_provider.py").read())
exec(open("financial_statement/infrastructure/service/llm_providers/template_provider.py").read())

# Sample data
data = {
    "balance_sheet": {"total_assets": 150000000, "current_assets": 65000000,
                      "total_liabilities": 45000000, "current_liabilities": 18900000,
                      "total_equity": 105000000},
    "income_statement": {"revenue": 220000000, "net_income": 28000000}
}

ratios = [
    FinancialRatio(1, 1, "CURRENT_RATIO", Decimal("3.44"), datetime.now()),
    FinancialRatio(2, 1, "QUICK_RATIO", Decimal("3.44"), datetime.now()),
    FinancialRatio(3, 1, "ROA", Decimal("18.67"), datetime.now()),
    FinancialRatio(4, 1, "ROE", Decimal("26.67"), datetime.now()),
    FinancialRatio(5, 1, "DEBT_TO_EQUITY", Decimal("0.43"), datetime.now()),
    FinancialRatio(6, 1, "PROFIT_MARGIN", Decimal("12.73"), datetime.now()),
]

print("="*80)
print("MULTI-PROVIDER LLM SYSTEM - DEMONSTRATION REPORT")
print("="*80)

provider = TemplateProvider()
print(f"\n✅ Provider: {provider.get_provider_name()}")
print(f"✅ Status: Always Available (No API Required)")

print("\n" + "="*80)
print("1. KPI SUMMARY")
print("="*80)
print(provider.create_kpi_summary(data, ratios))

print("\n" + "="*80)
print("2. TABLE SUMMARY")
print("="*80)
import json
print(json.dumps(provider.create_table_summary(data), indent=2))

print("\n" + "="*80)
print("3. RATIO ANALYSIS")
print("="*80)
print(provider.create_ratio_analysis(ratios))

print("\n" + "="*80)
print("PROVIDER CONFIGURATION OPTIONS")
print("="*80)
print("""
Add to .env file:

# Provider Selection
LLM_PROVIDER=auto          # Auto-detect (default)
LLM_PROVIDER=openai        # OpenAI GPT
LLM_PROVIDER=anthropic     # Anthropic Claude
LLM_PROVIDER=template      # Template only (no AI)

# OpenAI
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o        # gpt-4o, gpt-4-turbo, gpt-3.5-turbo

# Anthropic (requires: pip install anthropic)
ANTHROPIC_API_KEY=your_key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

✅ Template provider: No configuration needed!
✅ Auto-fallback: System uses templates if API fails
✅ Zero-downtime: Switch providers without restart
""")

print("="*80)
print("✅ DEMONSTRATION COMPLETE!")
print("="*80)
print("\nFeatures Implemented:")
print("  ✅ Multiple LLM providers (OpenAI, Anthropic, Template)")
print("  ✅ Automatic provider detection and failover")
print("  ✅ Template-based analysis (works without any API)")
print("  ✅ Graceful quota exhaustion handling")
print("  ✅ Provider-specific optimizations")
print("\nNext: Update .env and choose your preferred provider!")
