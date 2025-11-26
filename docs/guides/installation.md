# Installation Guide

Detailed installation instructions for SamSamOO-AI-Server dependencies.

## Quick Start

### Windows (Recommended)
```bash
cd SamSamOO-AI-Server
install_requirements.bat
```

### Linux/Mac
```bash
cd SamSamOO-AI-Server
pip install -r requirements.txt
```

## Requirements Files

| File | Purpose | Platform |
|------|---------|----------|
| `requirements_financial.txt` | Full dependencies with OCR | Linux/Mac |
| `requirements_financial_windows.txt` | Windows-optimized (no OCR) | Windows |
| `requirements_xbrl.txt` | XBRL/DART API only | All |

## Dependencies by Category

### PDF Processing

| Package | Purpose | Windows | Linux/Mac |
|---------|---------|---------|-----------|
| pdfplumber | PDF text/table extraction | Yes | Yes |
| camelot-py[cv] | Advanced table extraction | Yes | Yes |
| pytesseract | OCR text recognition | No | Yes |
| pdf2image | PDF to image conversion | No | Yes |
| Pillow | Image processing | No | Yes |
| opencv-python | Image processing for camelot | Yes | Yes |
| ghostscript | PDF rendering | Yes | Yes |

### Data Processing

| Package | Purpose |
|---------|---------|
| pandas | Data manipulation |
| numpy | Numerical computing |

### LLM Integration

| Package | Purpose |
|---------|---------|
| openai | OpenAI GPT API |
| anthropic | Anthropic Claude API (optional) |

### Visualization

| Package | Purpose |
|---------|---------|
| matplotlib | Chart generation |
| seaborn | Statistical visualization |

### Report Generation

| Package | Purpose | Platform |
|---------|---------|----------|
| Jinja2 | Template rendering | All |
| xhtml2pdf | PDF generation | Windows |
| reportlab | Complex PDF layouts | Windows |
| WeasyPrint | PDF generation | Linux/Mac |

### XBRL Support

| Package | Purpose |
|---------|---------|
| ixbrlparse | Inline XBRL parsing |
| arelle-release | Full XBRL processing |
| beautifulsoup4 | HTML/XML parsing |
| lxml | XML backend |
| aiohttp | Async HTTP for DART API |

## System Dependencies

### Windows

**Required:**
- Ghostscript: https://www.ghostscript.com/download/gsdnld.html

**Optional (for OCR):**
- Tesseract OCR: https://github.com/tesseract-ocr/tesseract
- Poppler: https://github.com/oschwartz10612/poppler-windows/releases

**For WeasyPrint (if using full requirements):**
- GTK3 Runtime: https://github.com/nickvdyck/weasyprint-binaries

### Linux (Ubuntu/Debian)

```bash
# Required
sudo apt-get install ghostscript

# For OCR
sudo apt-get install tesseract-ocr poppler-utils

# For WeasyPrint
sudo apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0
```

### macOS

```bash
# Using Homebrew
brew install ghostscript tesseract poppler

# For WeasyPrint
brew install pango
```

## Installation Steps

### Step 1: Create Virtual Environment

**Using Conda (Recommended):**
```bash
conda create -n samsam python=3.10
conda activate samsam
```

**Using venv:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### Step 2: Upgrade pip

```bash
python -m pip install --upgrade pip
```

### Step 3: Install Dependencies

**Windows:**
```bash
pip install -r requirements.txt
```

**Linux/Mac:**
```bash
pip install -r requirements.txt
```

**XBRL Only:**
```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
python -c "import pdfplumber; import pandas; import openai; print('OK')"
```

## Troubleshooting

### WeasyPrint Errors (Windows)

If you see GTK-related errors:
1. Install GTK3 Runtime
2. Add GTK bin directory to PATH
3. Restart terminal
4. Or use `requirements_financial_windows.txt` instead

### Ghostscript Not Found

```
# Windows: Add to PATH
C:\Program Files\gs\gs10.02.1\bin

# Linux
sudo apt-get install ghostscript
```

### Camelot Import Error

```bash
pip uninstall camelot-py
pip install camelot-py[cv]
```

### OpenCV Errors

```bash
pip uninstall opencv-python opencv-python-headless
pip install opencv-python
```

## See Also

- [Getting Started](./getting-started.md)
- [LLM Providers](./llm-providers.md)
- [XBRL Analysis](./xbrl-analysis.md)
- [Troubleshooting](../troubleshooting/README.md)
