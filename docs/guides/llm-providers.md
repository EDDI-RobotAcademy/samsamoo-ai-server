# Multi-Provider LLM System

The financial statement analysis system supports multiple LLM providers with automatic failover and graceful degradation.

## Features

- **Multiple Providers**: OpenAI, Anthropic, Template-based
- **Auto-Detection**: Automatically selects available provider
- **Graceful Fallback**: Uses templates if API fails
- **Zero-Configuration Option**: Template provider works immediately

## Quick Start

### Option 1: Template Provider (No API Required)

```env
LLM_PROVIDER=template
```
Works immediately without any API keys.

### Option 2: OpenAI

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o  # or gpt-3.5-turbo
```
Get API key: https://platform.openai.com/api-keys

### Option 3: Anthropic

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```
Get API key: https://console.anthropic.com/

Requires: `pip install anthropic`

### Option 4: Auto-Detect (Recommended)

```env
LLM_PROVIDER=auto
OPENAI_API_KEY=sk-...  # Will use if available
```

## Provider Comparison

| Feature | Template | OpenAI | Anthropic |
|---------|----------|---------|-----------|
| Setup | None | API Key | API Key + pip |
| Cost | Free | Pay-per-use | Pay-per-use |
| Speed | Instant | 2-5s | 2-5s |
| Quality | Basic | Excellent | Excellent |
| Offline | Yes | No | No |

## Available Models

### OpenAI
- `gpt-4o` - Best quality (recommended)
- `gpt-4-turbo` - Fast, high quality
- `gpt-3.5-turbo` - Cost-effective

### Anthropic
- `claude-3-5-sonnet-20241022` - Best balance
- `claude-3-opus-20240229` - Highest quality

## Error Handling

The system handles errors gracefully:

| Scenario | Behavior |
|----------|----------|
| API Key Missing | Falls back to template |
| Quota Exhausted (429) | Falls back to template |
| Network Error | Falls back to template |
| Invalid Response | Falls back to template |

**Result**: Analysis always completes successfully.

## Architecture

```
financial_statement/infrastructure/service/llm_providers/
├── base_provider.py       # Abstract base class
├── openai_provider.py     # OpenAI implementation
├── anthropic_provider.py  # Anthropic implementation
├── template_provider.py   # Template fallback
└── provider_factory.py    # Auto-detection factory
```

## Usage in Code

```python
from financial_statement.infrastructure.service.llm_analysis_service import LLMAnalysisService

# Auto-detect provider
service = LLMAnalysisService()

# Explicit provider
from financial_statement.infrastructure.service.llm_providers import TemplateProvider
service = LLMAnalysisService(provider=TemplateProvider())
```

## Monitoring

Check server logs for provider status:

```
INFO: LLM Analysis Service initialized with provider: OpenAI (gpt-4o)
INFO: Generating complete analysis with OpenAI (gpt-4o)
```

On fallback:
```
ERROR: Failed to generate KPI summary with OpenAI: Error code: 429
WARNING: OpenAI quota exceeded
INFO: Falling back to template-based summary
```

## Best Practices

### Development
```env
LLM_PROVIDER=template
```
Fast, free, works offline.

### Production
```env
LLM_PROVIDER=auto
OPENAI_API_KEY=sk-...
```
Automatic failover to templates.

### Cost Optimization
```env
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-3.5-turbo
```
Good quality at lower cost.
