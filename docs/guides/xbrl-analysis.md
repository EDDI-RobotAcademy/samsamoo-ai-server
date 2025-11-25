# XBRL Financial Analysis Guide

## Overview

This module provides XBRL-based corporate financial analysis capabilities, integrating with the Korean DART (전자공시시스템) API to fetch, parse, and analyze financial statements in XBRL format.

## Features

### 1. XBRL Data Acquisition
- **DART API Integration**: Direct integration with Korean DART Open API
- **Corporation Search**: Search for corporations by name
- **Financial Statement Download**: Fetch annual, semi-annual, and quarterly reports
- **Multiple Taxonomies**: Support for K-IFRS, K-GAAP, and international XBRL standards

### 2. Financial Ratio Calculation
- **Profitability Ratios**: ROA, ROE, Profit Margin, Operating Margin
- **Liquidity Ratios**: Current Ratio, Quick Ratio
- **Leverage Ratios**: Debt Ratio, Equity Multiplier
- **Efficiency Ratios**: Asset Turnover

### 3. LLM-Powered Analysis
- **Executive Summary**: High-level financial health assessment
- **Financial Health Rating**: Credit rating-style scoring (AAA to B)
- **Ratio Analysis**: Detailed interpretation of financial ratios
- **Investment Recommendation**: Buy/Hold/Sell recommendations with risk factors

### 4. Additional Features
- **Historical Analysis**: Multi-year trend analysis
- **Corporation Comparison**: Side-by-side comparison of multiple companies
- **Industry Benchmarking**: Compare ratios against industry averages

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Add to your `.env` file:

```env
# DART API (Required for XBRL analysis)
DART_API_KEY=your_dart_api_key

# LLM Provider (Optional - for full analysis)
OPENAI_API_KEY=your_openai_key
# OR
ANTHROPIC_API_KEY=your_anthropic_key
```

### 3. Get DART API Key

1. Visit [Open DART](https://opendart.fss.or.kr/)
2. Register for an account
3. Apply for API key
4. Copy your API key to `.env`

## API Endpoints

### Corporation Search
```
GET /xbrl/search?corp_name=삼성전자
```

Returns list of matching corporations with their DART codes.

### Corporation Information
```
GET /xbrl/corp/{corp_code}
```

Returns detailed corporation information.

### Quick Analysis (No LLM Required)
```
GET /xbrl/analyze/quick?corp_code=00126380&fiscal_year=2023
```

Returns financial data and calculated ratios without LLM analysis.

### Full Analysis (LLM Required)
```
POST /xbrl/analyze
{
    "corp_code": "00126380",
    "fiscal_year": 2023,
    "report_type": "annual",
    "industry": "technology"
}
```

Returns comprehensive analysis including LLM-generated insights.

### Financial Ratios Only
```
GET /xbrl/ratios/{corp_code}?fiscal_year=2023
```

Returns calculated financial ratios for a corporation.

### Historical Analysis
```
GET /xbrl/historical?corp_code=00126380&start_year=2020&end_year=2023
```

Returns multi-year financial data and trends.

### Corporation Comparison
```
POST /xbrl/compare
{
    "corp_codes": ["00126380", "00164742"],
    "fiscal_year": 2023
}
```

Compares multiple corporations side-by-side.

### Available Reports
```
GET /xbrl/available-reports/{corp_code}?begin_year=2020
```

Lists available financial reports for a corporation.

### Health Check
```
GET /xbrl/health
```

Returns service status and configuration.

## Usage Examples

### Python Client Example

```python
import httpx
import asyncio

async def analyze_samsung():
    async with httpx.AsyncClient() as client:
        # Search for corporation
        search_result = await client.get(
            "http://localhost:33333/xbrl/search",
            params={"corp_name": "삼성전자"}
        )
        corps = search_result.json()["results"]
        
        if corps:
            corp_code = corps[0]["corp_code"]
            
            # Get full analysis
            analysis = await client.post(
                "http://localhost:33333/xbrl/analyze",
                json={
                    "corp_code": corp_code,
                    "fiscal_year": 2023,
                    "report_type": "annual",
                    "industry": "technology"
                }
            )
            return analysis.json()

# Run
result = asyncio.run(analyze_samsung())
print(result["analysis"]["executive_summary"])
```

### cURL Examples

```bash
# Search for corporation
curl "http://localhost:33333/xbrl/search?corp_name=삼성전자"

# Quick analysis
curl "http://localhost:33333/xbrl/analyze/quick?corp_code=00126380&fiscal_year=2023"

# Full analysis
curl -X POST "http://localhost:33333/xbrl/analyze" \
  -H "Content-Type: application/json" \
  -d '{"corp_code":"00126380","fiscal_year":2023,"industry":"technology"}'
```

## Architecture

### Components

```
financial_statement/
├── domain/
│   └── xbrl_document.py          # XBRL domain entities
├── application/
│   ├── port/
│   │   └── xbrl_extraction_service_port.py
│   └── usecase/
│       └── xbrl_analysis_usecase.py
├── infrastructure/
│   └── service/
│       ├── dart_api_service.py           # DART API integration
│       ├── xbrl_extraction_service.py    # XBRL parsing
│       └── corporate_analysis_service.py # LLM analysis
└── adapter/
    └── input/web/
        └── xbrl_router.py                # API endpoints
```

### Data Flow

1. **Request** → XBRL Router
2. **Use Case** orchestrates:
   - DART API Service → Fetch XBRL data
   - XBRL Extraction Service → Parse and normalize
   - Ratio Calculation Service → Calculate ratios
   - Corporate Analysis Service → Generate LLM analysis
3. **Response** ← Complete analysis result

## K-IFRS Concept Mappings

The system maps Korean IFRS concepts to standardized field names:

| Standardized Field | K-IFRS Concepts |
|-------------------|-----------------|
| `total_assets` | 자산총계, Assets |
| `total_liabilities` | 부채총계, Liabilities |
| `total_equity` | 자본총계, Equity |
| `revenue` | 매출액, Revenue, 영업수익 |
| `net_income` | 당기순이익, ProfitLoss |
| `operating_income` | 영업이익, OperatingProfit |

## Industry Benchmarks

Available industry categories for comparison:
- `manufacturing`: Manufacturing sector benchmarks
- `technology`: Technology sector benchmarks
- `finance`: Financial sector benchmarks
- `retail`: Retail sector benchmarks
- `default`: General market averages

## Rate Limits

DART API has the following limits:
- 1,000 requests per day (basic plan)
- 100 requests per minute

The service implements automatic rate limiting awareness.

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `DART_API_KEY not configured` | Missing API key | Add `DART_API_KEY` to `.env` |
| `No data found` | No XBRL data available | Check fiscal year and report type |
| `Rate limit exceeded` | Too many requests | Wait before retrying |
| `Analysis failed` | LLM error | Check LLM API key configuration |

## Troubleshooting

### Missing Financial Data

If some financial items are missing:
1. Check the fiscal year - data may not be available
2. Try different report types (annual vs quarterly)
3. Some companies may not file certain items

### LLM Analysis Not Working

1. Verify LLM API key is set
2. Check `/xbrl/health` endpoint for configuration status
3. Use `/xbrl/analyze/quick` for analysis without LLM

### Korean Character Encoding

Ensure your environment supports UTF-8 encoding for Korean corporation names.

## Contributing

When adding new features:
1. Follow hexagonal architecture patterns
2. Add new concepts to `KIFRS_*_MAPPINGS` dictionaries
3. Update tests and documentation
