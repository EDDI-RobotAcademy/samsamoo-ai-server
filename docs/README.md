# SamSamOO-AI-Server Documentation

Comprehensive documentation for the financial statement analysis backend.

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Getting Started](./guides/getting-started.md) | Quick setup guide |
| [Installation](./guides/installation.md) | Detailed dependency installation |
| [API Reference](./api/README.md) | Endpoint documentation |
| [Architecture](./architecture/hexagonal.md) | System architecture |
| [Development](./development/README.md) | Development guide |
| [Troubleshooting](./troubleshooting/README.md) | Common issues |

## Documentation Structure

```
docs/
├── README.md                    # This file - documentation index
├── guides/
│   ├── getting-started.md       # Setup, configuration, quick start
│   ├── installation.md          # Detailed dependency installation
│   ├── llm-providers.md         # Multi-provider LLM configuration
│   └── xbrl-analysis.md         # XBRL/DART integration
├── api/
│   └── README.md                # API endpoint reference
├── architecture/
│   ├── hexagonal.md             # Architecture patterns (English)
│   └── hexagonal-kr.md          # Architecture patterns (Korean)
├── development/
│   └── README.md                # Development guidelines
├── examples/
│   ├── README.md                # Examples overview
│   └── visual-report-sample.md  # Sample report output
└── troubleshooting/
    └── README.md                # Common issues and solutions
```

## Guides

### [Getting Started](./guides/getting-started.md)
Quick setup and configuration guide.

### [Installation](./guides/installation.md)
Detailed dependency installation with platform-specific instructions.

### [LLM Providers](./guides/llm-providers.md)
Configure OpenAI, Anthropic, or template-based analysis with automatic failover.

### [XBRL Analysis](./guides/xbrl-analysis.md)
Korean corporate financial data via DART API integration.

## Architecture

### [Hexagonal Architecture](./architecture/hexagonal.md)
Clean architecture with domain, application, infrastructure, and adapter layers.

### [Hexagonal Architecture (Korean)](./architecture/hexagonal-kr.md)
한국어로 작성된 헥사고날 아키텍처 설명.

## Development

### [Development Guide](./development/README.md)
Guidelines for adding features and extending the system.

### [Scripts](../scripts/README.md)
Development and testing scripts documentation.

## API

### [API Reference](./api/README.md)
REST API endpoints and authentication flow.

### Interactive Docs
- **Swagger UI**: http://localhost:33333/docs
- **ReDoc**: http://localhost:33333/redoc

## Examples

### [Sample Reports](./examples/README.md)
Example outputs from the financial analysis system.

## Key Features

### Financial Statement Analysis Pipeline
1. **PDF Extraction** - Tables and data extraction via pdfplumber
2. **Ratio Calculation** - Automated financial ratio computation
3. **LLM Analysis** - AI-powered insights generation
4. **Report Generation** - PDF/HTML reports with charts

### Multi-Provider LLM System
- **OpenAI**: GPT-4o, GPT-3.5-turbo
- **Anthropic**: Claude-3.5
- **Template**: Rule-based fallback (no API required)
- **Auto-detection**: Automatic provider selection

### XBRL/DART Integration
- Korean corporate financial data
- K-IFRS statement parsing
- Historical analysis and comparison

## Related Documentation

- [Main README](../README.md) - Project overview
- [Scripts](../scripts/README.md) - Development scripts

## Contributing

1. Follow [Development Guide](./development/README.md)
2. Maintain [Architecture](./architecture/hexagonal.md) patterns
3. Update documentation for new features
