# Sample Visual Report

This is a demonstration of the financial analysis report output from the multi-provider LLM system.

## Report Overview

- **Statement ID**: 5
- **Analysis Date**: 2025-11-23
- **Provider**: Template (Fallback after OpenAI quota exhaustion)
- **Status**: SUCCESS

## Key Performance Indicators

| Metric | Value |
|--------|-------|
| Total Assets | $150,000,000 |
| Total Equity | $105,000,000 |
| Revenue | $220,000,000 |
| Net Income | $28,000,000 |

## Financial Ratios

### Liquidity Ratios

| Ratio | Value | Interpretation |
|-------|-------|----------------|
| Current Ratio | 3.44 | Strong liquidity position |
| Quick Ratio | 3.44 | Excellent short-term coverage |

### Leverage Ratios

| Ratio | Value | Interpretation |
|-------|-------|----------------|
| Equity Multiplier | 0.00 | Conservative capital structure |

## Processing Pipeline

| Stage | Status | Details |
|-------|--------|---------|
| PDF Extraction | SUCCESS | Tables extracted successfully |
| Ratio Calculation | SUCCESS | 4 ratios calculated |
| LLM Analysis | SUCCESS | Template fallback used |
| Report Generation | SUCCESS | PDF + HTML + Charts |

## Provider Behavior

This report demonstrates the multi-provider system's graceful degradation:

1. **OpenAI attempted** - Quota exhausted (HTTP 429)
2. **Automatic retry** - 3 retries with exponential backoff
3. **Fallback activated** - Template provider used
4. **Analysis completed** - Full report generated

## Generated Outputs

- PDF Report with charts
- HTML Report (interactive)
- 4 ratio visualization charts

## See Also

- [LLM Providers Guide](../guides/llm-providers.md)
- [Troubleshooting](../troubleshooting/README.md)
