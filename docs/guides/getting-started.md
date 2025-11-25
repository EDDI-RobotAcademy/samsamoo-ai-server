# Getting Started

Quick setup guide for SamSamOO-AI-Server.

## Prerequisites

- Python 3.8-3.11
- MySQL Server
- Redis Server
- (Optional) Google OAuth credentials

## Installation

### 1. Clone and Setup Environment

```bash
cd SamSamOO-AI-Server
```

**Using Conda (Recommended):**
```bash
conda create -n samsam python=3.10
conda activate samsam
```

### 2. Install Dependencies

**Basic Installation:**
```bash
pip install fastapi pymysql redis PyPDF2 uvicorn tensorflow transformers torch torchvision
```

**For Financial Statement Analysis (Windows):**
```bash
pip install -r requirements.txt
```

**Or use the batch installer (Windows):**
```bash
install_requirements.bat
```

> See [Installation Guide](./installation.md) for detailed dependency information.

### 3. Configure Environment

Create `.env` or `.env.local` in the project root:

```env
# Server
APP_HOST=0.0.0.0
APP_PORT=33333

# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=fastapi_test_db
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Google OAuth (Optional)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:33333/authentication/google/redirect
CLIENT_REDIRECT_URL=http://localhost:3000
SESSION_TTL_SECONDS=3600

# AWS S3 (Optional)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=ap-northeast-2
AWS_S3_BUCKET=your_bucket

# LLM Provider
LLM_PROVIDER=auto
OPENAI_API_KEY=your_openai_key

# DART API (for XBRL analysis)
DART_API_KEY=your_dart_key
```

### 4. Start the Server

```bash
python app/main.py
# Or: python -m app.main
```

Server runs at: http://localhost:33333

## Verification

### Check Server Status
```bash
curl http://localhost:33333/
```

### Check API Documentation
- Swagger UI: http://localhost:33333/docs
- ReDoc: http://localhost:33333/redoc

### Test Financial Statement Endpoint
```bash
curl http://localhost:33333/financial-statements/list
```

## Next Steps

- [Detailed Installation Guide](./installation.md)
- [Configure LLM Providers](./llm-providers.md)
- [Set up XBRL Analysis](./xbrl-analysis.md)
- [Troubleshooting Guide](../troubleshooting/README.md)

## IDE Setup (PyCharm)

1. File → Settings (Ctrl+Alt+S)
2. Python Interpreter → Add Interpreter
3. Select Conda environment or create new
4. Apply and restart
