# SamSamOO-AI-Server

AI-powered financial statement analysis backend with multi-provider LLM support.

## Features

- **Financial Statement Analysis**: PDF/Excel document processing with automated ratio calculation
- **Multi-Provider LLM System**: OpenAI, Anthropic, or template-based analysis with automatic failover
- **XBRL/DART Integration**: Korean corporate financial data via DART API
- **Hexagonal Architecture**: Clean separation of domain, application, and infrastructure layers
- **OAuth Authentication**: Google OAuth2 with Redis session management

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env.local
# Edit .env.local with your credentials

# Run the server
python app/main.py
```

Server runs at: http://localhost:33333

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](./docs/guides/getting-started.md) | Setup and installation guide |
| [LLM Providers](./docs/guides/llm-providers.md) | Multi-provider LLM configuration |
| [XBRL Analysis](./docs/guides/xbrl-analysis.md) | DART API integration guide |
| [Architecture](./docs/architecture/hexagonal.md) | Hexagonal architecture overview |
| [Troubleshooting](./docs/troubleshooting/README.md) | Common issues and solutions |

## API Documentation

- **Swagger UI**: http://localhost:33333/docs
- **ReDoc**: http://localhost:33333/redoc

## Project Structure

```
SamSamOO-AI-Server/
├── account/               # User account management
├── board/                 # Authenticated boards
├── anonymous_board/       # Public boards
├── documents/             # Document management
├── documents_multi_agents/# Multi-agent processing
├── financial_statement/   # Financial analysis (main feature)
├── social_oauth/          # OAuth authentication
├── config/                # Database, Redis configuration
├── app/                   # FastAPI application entry
├── docs/                  # Documentation
└── scripts/               # Utility scripts
```

## Environment Configuration

Create `.env.local` in the project root:

```env
# Server
APP_HOST=0.0.0.0
APP_PORT=33333

# Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=fastapi_test_db
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# LLM Provider (openai/anthropic/template/auto)
LLM_PROVIDER=auto
OPENAI_API_KEY=your_key

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_secret
```

See [Getting Started](./docs/guides/getting-started.md) for complete setup instructions.

## Technology Stack

- **Framework**: FastAPI with Uvicorn
- **Database**: MySQL with SQLAlchemy ORM
- **Cache**: Redis for session management
- **AI/ML**: OpenAI, Anthropic, LangChain
- **Document Processing**: pdfplumber, camelot-py, pytesseract
- **Data Analysis**: pandas, numpy, matplotlib

## License

Private repository.
