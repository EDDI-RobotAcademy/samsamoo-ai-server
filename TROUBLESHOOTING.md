# Troubleshooting Guide

## Fontconfig Error / PDF Generation Crash

### Problem
```
Fontconfig error: Cannot load default config file: No such file: (null)
[Program crashes after HTML report generation]
```

### Root Cause
WeasyPrint library requires GTK+ libraries and Fontconfig, which are not available by default on Windows systems.

### Solution
The application has been configured to use **xhtml2pdf** (Windows-compatible alternative) instead of WeasyPrint.

### Verification
1. Ensure Windows-compatible requirements are installed:
   ```bash
   pip install -r requirements_financial_windows.txt
   ```

2. Verify xhtml2pdf is installed:
   ```bash
   pip show xhtml2pdf
   ```

3. Check the router imports xhtml2pdf version:
   ```python
   # In financial_statement/adapter/input/web/financial_statement_router.py
   from financial_statement.infrastructure.service.report_generation_service_xhtml2pdf import ReportGenerationService
   ```

### If Issues Persist

**Check installed packages:**
```bash
pip list | grep -i "xhtml2pdf\|weasyprint"
```

**Reinstall xhtml2pdf:**
```bash
pip uninstall xhtml2pdf -y
pip install xhtml2pdf reportlab
```

**Verify Python version:**
- xhtml2pdf works best with Python 3.8-3.11
- Check: `python --version`

### Alternative: Use WeasyPrint (Linux/Mac)
If you're on Linux or Mac and want to use WeasyPrint:

1. Install system dependencies:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
   
   # macOS
   brew install pango gdk-pixbuf libffi
   ```

2. Install Python package:
   ```bash
   pip install -r requirements_financial.txt
   ```

3. Update router import:
   ```python
   from financial_statement.infrastructure.service.report_generation_service import ReportGenerationService
   ```

## Template Not Found Error

### Problem
```
ERROR: Failed to generate HTML report: 'financial_report.html' not found in search path: 'templates'
```

### Root Cause
Template path mismatch - the template is located at `templates/financial_reports/financial_report.html` but code was looking for `templates/financial_report.html`.

### Solution
**Already Fixed** - The template path has been corrected in `report_generation_service_xhtml2pdf.py`:
```python
template = self.jinja_env.get_template("financial_reports/financial_report.html")
```

### Verification
1. Restart the backend server
2. Attempt PDF generation
3. Should see: `INFO: PDF report generated successfully`

## Report Page Fails to Open (501 Not Implemented)

### Problem
```
Analysis succeeds but report page fails to open
GET /financial-statements/{id}/report/download returns 501 Not Implemented
```

### Root Cause
The PDF download endpoint was originally a placeholder expecting S3 integration. PDFs were generated to temp directories that got cleaned up, making them unavailable for download.

### Solution
**Already Fixed** - The system now:
1. Stores PDFs persistently in `generated_reports/statement_{id}/`
2. Serves PDFs directly from the local filesystem
3. Downloads work immediately without S3 setup

### Verification
1. Restart the backend server
2. Run analysis: `POST /financial-statements/analyze/{id}`
3. Download report: `GET /financial-statements/{id}/report/download`
4. PDF should download successfully

### Generated Files Location
```
SamSamOO-AI-Server/
└── generated_reports/
    └── statement_{id}/
        ├── report_{id}.pdf
        └── charts/
            ├── profitability_ratios.png
            ├── liquidity_ratios.png
            └── ...
```

**Note:** `generated_reports/` is in `.gitignore` and will persist across server restarts.

## Stage 2 Progression Issue (Fixed: 2025-11-24)

### Problem
After Stage 2 (ratio calculation) completes, users cannot progress to Stage 3 (LLM analysis). The frontend shows that Stage 2 is done, but there's no way to trigger the next stages. The "Run Analysis" button disappears and never shows "analysis_complete" status.

### Root Cause
Backend successfully runs all 4 stages when analyze endpoint is called, but `StatementResponse.from_domain()` only set status to `"metadata_only"` or `"pdf_uploaded"`. The frontend expects these status values:
- `"metadata_only"`: No PDF uploaded yet
- `"pdf_uploaded"`: Stage 1 complete (PDF extracted and normalized)
- `"ratios_calculated"`: Stage 2 complete (financial ratios calculated)
- `"analysis_complete"`: Stage 3-4 complete (LLM analysis and report generated)

Without proper status progression, the frontend workflow breaks - the UI doesn't know what stage the analysis is in and can't display the correct actions.

### Solution
**Already Fixed** - The system now properly tracks analysis progress:

1. **Updated `StatementResponse.from_domain()`** to accept `has_ratios` and `has_report` parameters:
   ```python
   def from_domain(cls, statement, has_ratios: bool = False, has_report: bool = False):
       if statement.normalized_data is None:
           status = "metadata_only"
       elif has_report:
           status = "analysis_complete"  # Stage 4 complete
       elif has_ratios:
           status = "ratios_calculated"  # Stage 2 complete
       elif statement.is_complete():
           status = "pdf_uploaded"       # Stage 1 complete
       else:
           status = "metadata_only"
   ```

2. **Modified router endpoints** to check database for ratios and reports:
   - `GET /financial-statements/{id}`: Queries database to check if ratios and reports exist
   - `POST /financial-statements/analyze/{id}`: Returns status "analysis_complete"
   - `GET /financial-statements/list`: Checks status for each statement

### Files Modified
- `financial_statement/adapter/input/web/response/statement_response.py`: Added status determination logic
- `financial_statement/adapter/input/web/financial_statement_router.py`: Updated endpoints to pass analysis progress
- `financial_statement/adapter/input/web/response/statement_list_response.py`: Handle status tuples

### Verification
```bash
# 1. Create statement and upload PDF (should show status: "pdf_uploaded")
curl -X POST "http://localhost:33333/financial-statements/create" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Test Corp", "statement_type": "quarterly", "fiscal_year": 2024, "fiscal_quarter": 1}' \
  --cookie-jar cookies.txt

# Upload PDF
curl -X POST "http://localhost:33333/financial-statements/upload?statement_id=1" \
  -F "file=@financial_statement.pdf" \
  --cookie cookies.txt

# 2. Check status after upload (should be "pdf_uploaded")
curl -X GET "http://localhost:33333/financial-statements/1" --cookie cookies.txt | grep status

# 3. Run analysis (executes all 4 stages)
curl -X POST "http://localhost:33333/financial-statements/analyze/1" --cookie cookies.txt

# 4. Check status after analysis (should be "analysis_complete")
curl -X GET "http://localhost:33333/financial-statements/1" --cookie cookies.txt | grep status
```

### Expected Frontend Behavior After Fix
1. **After PDF upload (Stage 1)**: Status shows "pdf_uploaded", button shows "분석 실행 (Stage 2-4)"
2. **During analysis**: Button disabled with text "분석 중..."
3. **After analysis complete**: Status shows "analysis_complete", button shows "PDF 리포트 다운로드"
4. **Chart page**: Report data is displayed with visualizations

## Frontend Report Display Error (Fixed: 2025-11-24)

### Problem
```
Application error: a client-side exception has occurred while loading localhost
Error occurs when trying to view or download financial statement report
```

### Root Cause
**Type mismatch** between frontend TypeScript interface and backend API response structure:

**Frontend expected** (`types/financial-statement.ts`):
```typescript
interface AnalysisReport {
    summary: string;
    insights: string[];
    recommendations: string[];
}
```

**Backend returned** (`analysis_response.py`):
```python
class AnalysisReportResponse:
    kpi_summary: Optional[str]
    statement_table_summary: Optional[Dict[str, Any]]
    ratio_analysis: Optional[str]
```

When React tried to render `report.summary`, `report.insights`, or `report.recommendations` (which don't exist), it caused a client-side rendering exception.

### Solution
**Already Fixed** - Updated frontend to match backend response structure:

1. **Updated TypeScript interface** (`types/financial-statement.ts`):
   ```typescript
   export interface AnalysisReport {
       kpi_summary: string | null;
       statement_table_summary: Record<string, any> | null;
       ratio_analysis: string | null;
       report_s3_key: string | null;
       is_complete: boolean;
   }
   ```

2. **Updated React component** (`app/financial-statements/[id]/page.tsx`):
   - Changed `report.summary` → `report.kpi_summary`
   - Changed `report.insights` array → removed (not in backend)
   - Changed `report.recommendations` array → removed (not in backend)
   - Added `report.statement_table_summary` display
   - Added `report.ratio_analysis` display

### Files Modified
- `SamSamOO-Frontend/types/financial-statement.ts`: Updated interface to match backend
- `SamSamOO-Frontend/app/financial-statements/[id]/page.tsx`: Updated report rendering logic

### Verification
```bash
# 1. Restart frontend dev server
cd SamSamOO-Frontend
npm run dev

# 2. Navigate to financial statement detail page
# 3. Click "분석 실행 (Stage 2-4)" button
# 4. Page should load successfully showing:
#    - KPI 요약 (if available)
#    - 재무제표 요약 (if available)
#    - 비율 분석 (if available)
# 5. Click "PDF 리포트 다운로드" - should download PDF without error
```

### Expected Behavior After Fix
- Page loads without "Application error" message
- Analysis report displays correctly with actual backend data structure
- PDF download button works properly
- No client-side rendering exceptions in browser console

## Ratio Display Runtime Error (Fixed: 2025-11-24)

### Problem
```
Runtime TypeError: Cannot read properties of undefined (reading 'toFixed')
app/financial-statements/[id]/page.tsx (279:103)

Error occurs when displaying financial ratios after analysis completes
```

### Root Cause
**Type mismatch** between frontend TypeScript interface and backend ratio response structure:

**Frontend expected** (`types/financial-statement.ts`):
```typescript
interface FinancialRatio {
    category: string;
    ratio_name: string;
    value: number;  // Tried to call value.toFixed(2)
    description?: string;
}
```

**Backend returned** (`ratio_response.py`):
```python
class RatioItemResponse:
    ratio_type: str        # Not "ratio_name"
    ratio_value: str       # Already formatted as percentage string, not number
    calculated_at: datetime
```

When React tried to call `ratio.value.toFixed(2)`, `value` was `undefined`, causing the runtime error.

### Solution
**Already Fixed** - Updated frontend to match backend response structure:

1. **Updated TypeScript interface** (`types/financial-statement.ts`):
   ```typescript
   export interface FinancialRatio {
       id: number;
       ratio_type: string;           // Backend field name
       ratio_value: string;          // Pre-formatted string (e.g., "15.5%")
       calculated_at: string;
   }
   ```

2. **Updated React component** (`app/financial-statements/[id]/page.tsx`):
   - Removed `groupRatiosByCategory()` function (no category field)
   - Added `getRatioDisplayName()` to map ratio types to friendly names
   - Changed `ratio.value.toFixed(2)` → `ratio.ratio_value` (display string directly)
   - Removed category grouping, display all ratios in grid
   - Added calculation timestamp display

### Files Modified
- `SamSamOO-Frontend/types/financial-statement.ts`: Updated FinancialRatio interface
- `SamSamOO-Frontend/app/financial-statements/[id]/page.tsx`: Updated ratio display logic

### Verification
```bash
# 1. Restart frontend dev server
cd SamSamOO-Frontend
npm run dev

# 2. Navigate to financial statement detail page
# 3. Run analysis: Click "분석 실행 (Stage 2-4)"
# 4. After analysis completes, ratios should display without error:
#    - Each ratio shows as a card with friendly name
#    - Value displayed as formatted percentage (e.g., "15.5%")
#    - Calculation date shown below
```

### Expected Behavior After Fix
- No runtime errors when displaying ratios
- Ratios display with user-friendly names (e.g., "Return on Assets (ROA)")
- Values show as pre-formatted percentages from backend
- Grid layout without category grouping
- Calculation timestamps visible for each ratio

## Other Common Issues

### MySQL Connection Errors
See `CLAUDE.md` section "Database Connection Errors"

### Redis Connection Errors
See `CLAUDE.md` section "Authentication Not Working"

### Google OAuth Errors
See `CLAUDE.md` section "Google OAuth Errors"
