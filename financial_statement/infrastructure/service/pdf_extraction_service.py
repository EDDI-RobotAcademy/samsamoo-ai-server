import pdfplumber
import camelot
import re
from typing import Dict, Any, List, Optional, Tuple
import logging
from financial_statement.application.port.pdf_extraction_service_port import PDFExtractionServicePort

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Custom exception for extraction errors"""
    pass


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class PDFExtractionService(PDFExtractionServicePort):
    """
    Implementation of PDF extraction service using PDFPlumber, Camelot, and OCR.
    Stage 1 of the analysis pipeline.

    Optimized for DART (금융감독원 전자공시시스템) financial statement format.

    DART Document Structure (based on Samsung Electronics 분기보고서):
    - Balance Sheet: 유동자산, 비유동자산, 자산총계, 유동부채, 비유동부채, 부채총계, 자본총계
    - Income Statement: 매출액, 매출원가, 매출총이익, 영업이익, 분기순이익/당기순이익
    - Items have note references like (주3,26), (주5) that need to be stripped
    - Values are comma-separated millions of won (백만원)
    """

    # Company name suffixes to identify subsidiary/notes tables
    COMPANY_SUFFIXES = [
        '㈜', '(주)', 'Ltd.', 'Ltd', 'Inc.', 'Inc', 'Co.', 'Co',
        'LLC', 'LLC.', 'GmbH', 'B.V.', 'S.A.', 'Pte.', 'Ltda.',
        'Corporation', 'Corp.', 'Corp', 'Limited'
    ]

    # Patterns indicating notes/footnotes section (to be skipped)
    NOTES_INDICATORS = [
        '(*', '주석', '(*1)', '(*2)', '(*3)',
        '관계기업', '종속기업', '지분법',
        '세부내역', '상세내역', '내역서'
    ]

    # Regex pattern to strip note references from item names
    # Matches patterns like (주3), (주3,26), (주 3), (주석3), etc.
    NOTE_REFERENCE_PATTERN = re.compile(r'\s*\(주\s*[\d,\s\.]+\)\s*|\s*\(주석\s*[\d,\s\.]+\)\s*')

    # Regex pattern to match unit indicators that should be removed
    UNIT_PATTERN = re.compile(r'\s*\(단위\s*:\s*[^)]+\)\s*')

    # DART income statement column patterns
    # DART quarterly reports have: 과목 | 당분기 3개월 | 당분기 누적 | 전분기 3개월 | 전분기 누적
    # We want the "당분기 누적" (current period cumulative) column
    CURRENT_PERIOD_PATTERNS = ['당분기누적', '당기누적', '당분기말', '당기말', '당분기', '당기']
    CUMULATIVE_PATTERNS = ['누적', '년', '반기', '기말']

    def __init__(self):
        self.table_confidence_threshold = 0.7
        self.ocr_fallback_enabled = False  # OCR disabled
        self.in_notes_section = False  # Track if we're in notes section

    def _clean_item_name(self, item_name: str) -> str:
        """
        Clean item name by removing note references and normalizing spaces.

        Examples:
        - "현금및현금성자산 (주3,26)" -> "현금및현금성자산"
        - "매출액 (주27)" -> "매출액"
        - "기본주당이익 (단위 : 원)" -> "기본주당이익"
        - "Ⅰ.유동자산" -> "유동자산"
        """
        if not item_name:
            return ""

        # Remove note references like (주3), (주3,26)
        cleaned = self.NOTE_REFERENCE_PATTERN.sub('', item_name)

        # Remove unit indicators like (단위 : 원), (단위 : 백만원)
        cleaned = self.UNIT_PATTERN.sub('', cleaned)

        # Remove Roman numeral prefixes (Ⅰ., Ⅱ., I., II., 1., 2., etc.)
        cleaned = re.sub(r'^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩIVXivx\d]+\.\s*', '', cleaned)

        # Remove other common suffixes in parentheses
        cleaned = re.sub(r'\s*\([^)]*\)\s*$', '', cleaned)

        # Remove leading/trailing whitespace and normalize internal whitespace
        cleaned = ' '.join(cleaned.split())

        return cleaned.strip()

    def extract_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract financial tables from PDF using PDFPlumber first, fallback to Camelot.

        Strategy:
        1. Try PDFPlumber (better for structured PDFs with embedded tables)
        2. If low confidence, try Camelot (better for visual table detection)
        3. If both fail and OCR enabled, try OCR fallback
        """
        logger.info(f"Starting PDF extraction from: {pdf_path}")

        try:
            # Try PDFPlumber first
            result = self._extract_with_pdfplumber(pdf_path)
            if self._has_sufficient_data(result):
                logger.info("PDF extraction successful with PDFPlumber")
                return result
            else:
                logger.warning("PDFPlumber: Insufficient financial data extracted, trying Camelot")
        except Exception as e:
            logger.warning(f"PDFPlumber extraction failed: {e}")

        try:
            # Fallback to Camelot
            result = self._extract_with_camelot(pdf_path)
            if self._has_sufficient_data(result):
                logger.info("PDF extraction successful with Camelot")
                return result
            else:
                logger.warning("Camelot: Insufficient financial data extracted")
        except Exception as e:
            logger.warning(f"Camelot extraction failed: {e}")

        # If both fail, try OCR if enabled
        if self.ocr_fallback_enabled:
            logger.info("Attempting OCR fallback")
            return self.extract_from_scanned_pdf(pdf_path)

        # Build detailed error message
        error_msg = (
            "Failed to extract financial tables from PDF. "
            "This could mean: (1) PDF contains no tables, "
            "(2) PDF is scanned/image-based (OCR is disabled), "
            "(3) Table format is not supported by extraction tools. "
            "Please ensure PDF contains structured financial statement tables (balance sheet, income statement)."
        )
        logger.error(error_msg)
        raise ExtractionError(error_msg)

    def _extract_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """Extract tables using PDFPlumber"""
        extracted_data = {
            "balance_sheet": {},
            "income_statement": {},
            "cash_flow_statement": {}
        }

        total_tables = 0
        identified_tables = 0

        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"PDFPlumber: Processing {len(pdf.pages)} pages")

            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                total_tables += len(tables)

                if tables:
                    logger.info(f"PDFPlumber: Found {len(tables)} table(s) on page {page_num + 1}")

                for table in tables:
                    # Identify table type based on keywords in first rows
                    table_type = self._identify_table_type(table)

                    if table_type:
                        identified_tables += 1
                        # Pass statement_type to use correct column detection
                        parsed_table = self._parse_financial_table(table, statement_type=table_type)
                        item_count = len(parsed_table)
                        extracted_data[table_type].update(parsed_table)
                        logger.info(f"PDFPlumber: Identified {table_type} table on page {page_num + 1} ({item_count} items extracted)")
                    else:
                        # Debug: Log unidentified table headers
                        if table and len(table) > 0:
                            header_preview = " ".join([str(cell) for row in table[:3] for cell in row if cell])[:150]
                            logger.info(f"PDFPlumber: Unidentified table on page {page_num + 1}, header preview: '{header_preview}'")

        logger.info(f"PDFPlumber: Total tables found: {total_tables}, Financial tables identified: {identified_tables}")
        logger.info(f"PDFPlumber: Extracted data summary - Balance sheet items: {len(extracted_data['balance_sheet'])}, Income statement items: {len(extracted_data['income_statement'])}, Cash flow items: {len(extracted_data['cash_flow_statement'])}")
        return extracted_data

    def _extract_with_camelot(self, pdf_path: str) -> Dict[str, Any]:
        """Extract tables using Camelot"""
        extracted_data = {
            "balance_sheet": {},
            "income_statement": {},
            "cash_flow_statement": {}
        }

        # Try lattice mode first (tables with borders)
        logger.info("Camelot: Attempting table extraction (lattice mode)")
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice', suppress_stdout=True)

        if len(tables) == 0:
            # Fallback to stream mode (tables without borders)
            logger.info("Camelot: No tables with lattice mode, trying stream mode")
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream', suppress_stdout=True)

        if len(tables) == 0:
            logger.warning("Camelot: No tables found in PDF")
        else:
            logger.info(f"Camelot: Found {len(tables)} table(s)")

        high_confidence_tables = 0
        identified_tables = 0

        for idx, table in enumerate(tables):
            accuracy = table.parsing_report['accuracy']
            logger.info(f"Camelot: Table {idx + 1} accuracy: {accuracy:.1f}% (threshold: {self.table_confidence_threshold * 100}%)")

            if accuracy >= self.table_confidence_threshold * 100:
                high_confidence_tables += 1
                df = table.df
                table_type = self._identify_table_type_from_dataframe(df)

                if table_type:
                    identified_tables += 1
                    # Pass statement_type for correct column detection
                    parsed_table = self._parse_financial_table_from_dataframe(df, statement_type=table_type)
                    extracted_data[table_type].update(parsed_table)
                    logger.info(f"Camelot: Identified {table_type} table")
            else:
                logger.warning(f"Camelot: Table {idx + 1} accuracy too low ({accuracy:.1f}%), skipping")

        logger.info(f"Camelot: High-confidence tables: {high_confidence_tables}, Financial tables identified: {identified_tables}")
        return extracted_data

    def extract_from_scanned_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract from scanned PDF using OCR.

        NOTE: OCR functionality has been disabled.
        This method will raise an error if called.
        """
        logger.error(f"OCR extraction attempted but is disabled: {pdf_path}")
        raise ExtractionError(
            "OCR extraction is disabled. "
            "Only native PDF text and table extraction (PDFPlumber/Camelot) is supported. "
            "Scanned PDFs or image-based PDFs cannot be processed."
        )

    def normalize_to_kifrs(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize extracted financial items to K-IFRS taxonomy.
        Uses rule-based mapping table for standardization.
        """
        logger.info("Normalizing to K-IFRS taxonomy")

        # Debug: Log sample of raw keys for troubleshooting
        if "balance_sheet" in extracted_data:
            bs_keys = list(extracted_data["balance_sheet"].keys())[:5]
            logger.info(f"Sample balance sheet raw keys: {bs_keys}")

        normalized = {
            "balance_sheet": {},
            "income_statement": {},
            "cash_flow_statement": {}
        }

        # Normalize balance sheet
        if "balance_sheet" in extracted_data:
            normalized["balance_sheet"] = self._normalize_balance_sheet(
                extracted_data["balance_sheet"]
            )

        # Normalize income statement
        if "income_statement" in extracted_data:
            normalized["income_statement"] = self._normalize_income_statement(
                extracted_data["income_statement"]
            )

        # Normalize cash flow statement (optional)
        if "cash_flow_statement" in extracted_data:
            normalized["cash_flow_statement"] = self._normalize_cash_flow(
                extracted_data["cash_flow_statement"]
            )

        # Validate required fields are present
        self._validate_normalized_data(normalized)

        return normalized

    def _normalize_balance_sheet(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize balance sheet items to K-IFRS standard names.

        Enhanced for DART format with comprehensive Korean term mapping.
        """
        # K-IFRS mapping table with Korean variations (including spaced versions)
        # Priority order matters - more specific terms should map first
        mapping = {
            # Assets (자산) - DART-specific patterns first
            "자산총계": "total_assets",
            "자산 총계": "total_assets",
            "자 산 총 계": "total_assets",
            "총자산": "total_assets",
            "총 자 산": "total_assets",
            "자산계": "total_assets",
            "자 산 계": "total_assets",
            "Ⅰ.자산": "total_assets",
            "I.자산": "total_assets",

            # Current Assets
            "유동자산": "current_assets",
            "유 동 자 산": "current_assets",
            "유동자산계": "current_assets",
            "유동자산 계": "current_assets",
            "Ⅰ.유동자산": "current_assets",
            "I.유동자산": "current_assets",
            "1.유동자산": "current_assets",

            # Non-current Assets
            "비유동자산": "non_current_assets",
            "비 유 동 자 산": "non_current_assets",
            "비유동자산계": "non_current_assets",
            "Ⅱ.비유동자산": "non_current_assets",
            "II.비유동자산": "non_current_assets",
            "2.비유동자산": "non_current_assets",

            # Cash
            "현금및현금성자산": "cash_and_equivalents",
            "현 금 및 현 금 성 자 산": "cash_and_equivalents",
            "현금및현금등가물": "cash_and_equivalents",

            # Inventory
            "재고자산": "inventory",
            "재 고 자 산": "inventory",

            # Liabilities (부채) - DART-specific patterns
            "부채총계": "total_liabilities",
            "부채 총계": "total_liabilities",
            "부 채 총 계": "total_liabilities",
            "총부채": "total_liabilities",
            "총 부 채": "total_liabilities",
            "부채계": "total_liabilities",
            "부 채 계": "total_liabilities",
            "Ⅱ.부채": "total_liabilities",
            "II.부채": "total_liabilities",

            # Current Liabilities
            "유동부채": "current_liabilities",
            "유 동 부 채": "current_liabilities",
            "유동부채계": "current_liabilities",
            "Ⅰ.유동부채": "current_liabilities",
            "I.유동부채": "current_liabilities",
            "1.유동부채": "current_liabilities",

            # Non-current Liabilities
            "비유동부채": "non_current_liabilities",
            "비 유 동 부 채": "non_current_liabilities",
            "비유동부채계": "non_current_liabilities",
            "Ⅱ.비유동부채": "non_current_liabilities",
            "II.비유동부채": "non_current_liabilities",
            "2.비유동부채": "non_current_liabilities",

            # Equity (자본) - DART-specific patterns
            "자본총계": "total_equity",
            "자본 총계": "total_equity",
            "자 본 총 계": "total_equity",
            "총자본": "total_equity",
            "총 자 본": "total_equity",
            "자본계": "total_equity",
            "자 본 계": "total_equity",
            "Ⅲ.자본": "total_equity",
            "III.자본": "total_equity",
            "지배기업소유주지분": "total_equity",
            "지 배 기 업 소 유 주 지 분": "total_equity",
            "지배기업의소유주에게귀속되는자본": "total_equity",

            # Other equity items
            "자본금": "capital_stock",
            "자 본 금": "capital_stock",
            "이익잉여금": "retained_earnings",
            "이 익 잉 여 금": "retained_earnings",
        }

        normalized = {}
        for raw_key, raw_value in raw_data.items():
            # Clean the raw key: remove note references, spaces, special chars
            cleaned_key = self._clean_item_name(raw_key)
            cleaned_key_no_space = cleaned_key.replace(" ", "").replace("\n", "")

            # Try multiple matching strategies
            normalized_key = None

            # 1. Exact match with original key
            if raw_key in mapping:
                normalized_key = mapping[raw_key]

            # 2. Match with cleaned key (note references removed)
            if not normalized_key and cleaned_key in mapping:
                normalized_key = mapping[cleaned_key]

            # 3. Match with cleaned key (no spaces)
            if not normalized_key and cleaned_key_no_space in mapping:
                normalized_key = mapping[cleaned_key_no_space]

            # 4. Fallback to original key
            if not normalized_key:
                normalized_key = cleaned_key if cleaned_key else raw_key

            # Debug logging for unmapped keys (only if it looks like a financial term)
            if normalized_key not in mapping.values():
                if any(kw in cleaned_key_no_space for kw in ['자산', '부채', '자본', '유동', '비유동']):
                    logger.debug(f"Unmapped balance sheet key: '{raw_key}' -> '{cleaned_key}' (no match)")

            normalized[normalized_key] = raw_value

        # Post-process: Calculate missing totals from components if possible
        normalized = self._calculate_missing_balance_sheet_totals(normalized)

        # Log summary of mapped vs unmapped
        standard_keys = ["total_assets", "total_liabilities", "total_equity",
                        "current_assets", "non_current_assets",
                        "current_liabilities", "non_current_liabilities",
                        "cash_and_equivalents", "inventory", "capital_stock", "retained_earnings"]
        mapped_standard_keys = [k for k in normalized.keys() if k in standard_keys]
        logger.info(f"Balance sheet normalization: {len(mapped_standard_keys)} standard K-IFRS fields mapped from {len(raw_data)} raw items")
        logger.info(f"Mapped fields: {mapped_standard_keys}")

        return normalized

    def _calculate_missing_balance_sheet_totals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate missing aggregate totals from components.

        DART accounting equation: Total Assets = Total Liabilities + Total Equity
        """
        # Calculate total_assets if missing but we have components
        if "total_assets" not in data or data.get("total_assets", 0) == 0:
            current = data.get("current_assets", 0)
            non_current = data.get("non_current_assets", 0)
            if current > 0 or non_current > 0:
                data["total_assets"] = current + non_current
                logger.info(f"Calculated total_assets from components: {data['total_assets']}")

        # Calculate total_assets from accounting equation if still missing
        if "total_assets" not in data or data.get("total_assets", 0) == 0:
            liabilities = data.get("total_liabilities", 0)
            equity = data.get("total_equity", 0)
            if liabilities > 0 and equity > 0:
                data["total_assets"] = liabilities + equity
                logger.info(f"Calculated total_assets from accounting equation: {data['total_assets']}")

        # Calculate total_liabilities if missing
        if "total_liabilities" not in data or data.get("total_liabilities", 0) == 0:
            current = data.get("current_liabilities", 0)
            non_current = data.get("non_current_liabilities", 0)
            if current > 0 or non_current > 0:
                data["total_liabilities"] = current + non_current
                logger.info(f"Calculated total_liabilities from components: {data['total_liabilities']}")

        return data

    def _normalize_income_statement(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize income statement items to K-IFRS standard names.

        Enhanced for DART format with comprehensive Korean term mapping.
        """
        # K-IFRS mapping table with Korean variations (including spaced versions)
        mapping = {
            # Revenue (매출액) - DART patterns
            "매출액": "revenue",
            "매 출 액": "revenue",
            "수익": "revenue",
            "수 익": "revenue",
            "매출": "revenue",
            "매 출": "revenue",
            "Ⅰ.매출액": "revenue",
            "I.매출액": "revenue",
            "1.매출액": "revenue",
            "영업수익": "revenue",
            "영 업 수 익": "revenue",

            # Cost of Revenue
            "매출원가": "cost_of_revenue",
            "매 출 원 가": "cost_of_revenue",
            "Ⅱ.매출원가": "cost_of_revenue",
            "II.매출원가": "cost_of_revenue",
            "2.매출원가": "cost_of_revenue",

            # Gross Profit
            "매출총이익": "gross_profit",
            "매 출 총 이 익": "gross_profit",
            "Ⅲ.매출총이익": "gross_profit",
            "III.매출총이익": "gross_profit",

            # Operating expenses
            "판매비와관리비": "operating_expenses",
            "판 매 비 와 관 리 비": "operating_expenses",
            "판관비": "operating_expenses",
            "Ⅳ.판매비와관리비": "operating_expenses",
            "IV.판매비와관리비": "operating_expenses",

            # Operating income (영업이익) - DART patterns
            "영업이익": "operating_income",
            "영 업 이 익": "operating_income",
            "Ⅴ.영업이익": "operating_income",
            "V.영업이익": "operating_income",
            "영업이익(손실)": "operating_income",
            "영업손익": "operating_income",

            # Non-operating items
            "영업외수익": "non_operating_income",
            "영 업 외 수 익": "non_operating_income",
            "기타수익": "non_operating_income",
            "영업외비용": "non_operating_expenses",
            "영 업 외 비 용": "non_operating_expenses",
            "기타비용": "non_operating_expenses",
            "금융수익": "finance_income",
            "금융비용": "finance_cost",

            # Pre-tax income
            "법인세비용차감전순이익": "income_before_tax",
            "법인세비용차감전계속영업이익": "income_before_tax",
            "법인세차감전이익": "income_before_tax",
            "세전이익": "income_before_tax",

            # Tax expense
            "법인세비용": "income_tax_expense",
            "법 인 세 비 용": "income_tax_expense",

            # Net income (당기순이익) - DART patterns
            "당기순이익": "net_income",
            "당 기 순 이 익": "net_income",
            "분기순이익": "net_income",
            "분 기 순 이 익": "net_income",
            "순이익": "net_income",
            "순 이 익": "net_income",
            "당기순이익(손실)": "net_income",
            "분기순이익(손실)": "net_income",
            "연결당기순이익": "net_income",
            "연결분기순이익": "net_income",
            "Ⅶ.당기순이익": "net_income",
            "VII.당기순이익": "net_income",

            # Comprehensive income
            "총포괄이익": "comprehensive_income",
            "총포괄손익": "comprehensive_income",
            "당기총포괄이익": "comprehensive_income",
            "분기총포괄이익": "comprehensive_income",

            # EPS (Earnings Per Share)
            "기본주당이익": "basic_eps",
            "희석주당이익": "diluted_eps",
            "주당순이익": "basic_eps",
        }

        normalized = {}
        for raw_key, raw_value in raw_data.items():
            # Clean the raw key: remove note references, spaces, special chars
            cleaned_key = self._clean_item_name(raw_key)
            cleaned_key_no_space = cleaned_key.replace(" ", "").replace("\n", "")

            # Try multiple matching strategies
            normalized_key = None

            # 1. Exact match with original key
            if raw_key in mapping:
                normalized_key = mapping[raw_key]

            # 2. Match with cleaned key (note references removed)
            if not normalized_key and cleaned_key in mapping:
                normalized_key = mapping[cleaned_key]

            # 3. Match with cleaned key (no spaces)
            if not normalized_key and cleaned_key_no_space in mapping:
                normalized_key = mapping[cleaned_key_no_space]

            # 4. Fallback to cleaned key
            if not normalized_key:
                normalized_key = cleaned_key if cleaned_key else raw_key

            # Debug logging for unmapped income statement keys
            if normalized_key not in mapping.values():
                if any(kw in cleaned_key_no_space for kw in ['매출', '이익', '손익', '비용', '수익']):
                    logger.debug(f"Unmapped income statement key: '{raw_key}' -> '{cleaned_key}' (no match)")

            normalized[normalized_key] = raw_value

        # Post-process: Calculate missing items if possible
        normalized = self._calculate_missing_income_items(normalized)

        # Log summary
        standard_keys = ["revenue", "cost_of_revenue", "gross_profit", "operating_expenses",
                        "operating_income", "income_before_tax", "income_tax_expense", "net_income"]
        mapped_standard_keys = [k for k in normalized.keys() if k in standard_keys]
        logger.info(f"Income statement normalization: {len(mapped_standard_keys)} standard fields mapped")
        logger.info(f"Mapped income fields: {mapped_standard_keys}")

        return normalized

    def _calculate_missing_income_items(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate missing income statement items from available data."""

        # Calculate gross_profit if missing
        if "gross_profit" not in data or data.get("gross_profit", 0) == 0:
            revenue = data.get("revenue", 0)
            cost = data.get("cost_of_revenue", 0)
            if revenue > 0 and cost > 0:
                data["gross_profit"] = revenue - cost
                logger.info(f"Calculated gross_profit: {data['gross_profit']}")

        # Calculate operating_income if missing
        if "operating_income" not in data or data.get("operating_income", 0) == 0:
            gross_profit = data.get("gross_profit", 0)
            operating_exp = data.get("operating_expenses", 0)
            if gross_profit > 0:
                data["operating_income"] = gross_profit - operating_exp
                logger.info(f"Calculated operating_income: {data['operating_income']}")

        return data

    def _normalize_cash_flow(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize cash flow statement items to K-IFRS standard names"""
        mapping = {
            "영업활동으로인한현금흐름": "cash_from_operations",
            "투자활동으로인한현금흐름": "cash_from_investing",
            "재무활동으로인한현금흐름": "cash_from_financing",
        }

        normalized = {}
        for raw_key, raw_value in raw_data.items():
            normalized_key = mapping.get(raw_key, raw_key)
            normalized[normalized_key] = raw_value

        return normalized

    def _identify_table_type(self, table: List[List[str]]) -> str:
        """Identify if table is balance sheet, income statement, or cash flow"""
        if not table or len(table) < 2:
            return None

        # Check first few rows for keywords
        header_text = " ".join([str(cell) for row in table[:5] for cell in row if cell]).lower()

        # Primary statements (full tables)
        if any(keyword in header_text for keyword in ["재무상태표", "대차대조표", "balance sheet"]):
            return "balance_sheet"
        elif any(keyword in header_text for keyword in ["손익계산서", "포괄손익계산서", "income statement", "profit or loss"]):
            return "income_statement"
        elif any(keyword in header_text for keyword in ["현금흐름표", "cash flow"]):
            return "cash_flow_statement"

        # Fallback: Look for specific financial items in table body (notes/supplementary tables)
        # This catches tables with key financial data even without main statement headers
        table_content = " ".join([str(cell) for row in table for cell in row if cell]).lower()

        # Balance sheet indicators (assets, liabilities, equity)
        if any(keyword in table_content for keyword in ["자산", "부채", "자본", "asset", "liability", "equity"]):
            if any(keyword in table_content for keyword in ["당분기말", "전기말", "current period", "end of period"]):
                return "balance_sheet"

        # Income statement indicators (revenue, expenses, income)
        if any(keyword in table_content for keyword in ["매출액", "영업이익", "당기순이익", "revenue", "operating income", "net income"]):
            if any(keyword in table_content for keyword in ["당분기", "전분기", "current quarter", "previous quarter"]):
                return "income_statement"

        return None

    def _identify_table_type_from_dataframe(self, df) -> str:
        """Identify table type from pandas DataFrame"""
        if df.empty or len(df) < 2:
            return None

        # Check header rows
        header_text = " ".join(df.iloc[:min(5, len(df))].astype(str).values.flatten()).lower()

        # Primary statements
        if any(keyword in header_text for keyword in ["재무상태표", "대차대조표", "balance sheet"]):
            return "balance_sheet"
        elif any(keyword in header_text for keyword in ["손익계산서", "포괄손익계산서", "income statement", "profit or loss"]):
            return "income_statement"
        elif any(keyword in header_text for keyword in ["현금흐름표", "cash flow"]):
            return "cash_flow_statement"

        # Fallback: Check entire dataframe content
        df_content = " ".join(df.astype(str).values.flatten()).lower()

        # Balance sheet indicators
        if any(keyword in df_content for keyword in ["자산", "부채", "자본", "asset", "liability", "equity"]):
            if any(keyword in df_content for keyword in ["당분기말", "전기말", "current period", "end of period"]):
                return "balance_sheet"

        # Income statement indicators
        if any(keyword in df_content for keyword in ["매출액", "영업이익", "당기순이익", "revenue", "operating income", "net income"]):
            if any(keyword in df_content for keyword in ["당분기", "전분기", "current quarter", "previous quarter"]):
                return "income_statement"

        return None

    def _is_notes_row(self, item_name: str) -> bool:
        """
        Check if a row belongs to notes/footnotes section (should be skipped).

        DART reports include subsidiary details and notes that should not be
        extracted as main financial statement items.
        """
        if not item_name:
            return False

        # Check for note reference markers like (*1), (*2)
        if re.search(r'\(\*\d*\)', item_name):
            return True

        # Check for company name suffixes (subsidiary tables)
        for suffix in self.COMPANY_SUFFIXES:
            if suffix in item_name:
                return True

        # Check for notes section indicators
        for indicator in self.NOTES_INDICATORS:
            if indicator in item_name:
                return True

        # Skip header rows that got parsed as data
        header_keywords = ['요약', '구 분', '과 목', '기 업 명', '구분', '과목']
        if any(keyword in item_name for keyword in header_keywords):
            return True

        return False

    def _is_aggregate_row(self, item_name: str) -> bool:
        """
        Check if a row is an aggregate/total row (important for extraction).

        DART format uses specific patterns for totals:
        - 자산총계, 부채총계, 자본총계
        - Rows ending with 계 (total)
        """
        if not item_name:
            return False

        aggregate_patterns = [
            '자산총계', '부채총계', '자본총계',
            '자산 총계', '부채 총계', '자본 총계',
            '유동자산', '비유동자산', '유동부채', '비유동부채',
            '매출액', '영업이익', '당기순이익', '분기순이익',
            '법인세비용차감전순이익'
        ]

        # Check exact matches for key aggregates
        cleaned = item_name.replace(" ", "")
        if cleaned in [p.replace(" ", "") for p in aggregate_patterns]:
            return True

        return False

    def _find_value_column_index(self, table: List[List[str]], statement_type: str = "balance_sheet") -> int:
        """
        Find the correct column index for current period values in DART tables.

        DART Balance Sheet structure:
        | 과목 | 당분기말/당기말 | 전분기말/전기말 |

        DART Income Statement structure (quarterly):
        | 과목 | 당분기 3개월 | 당분기 누적 | 전분기 3개월 | 전분기 누적 |
        We want "당분기 누적" (current period cumulative) for income statements.

        Returns the index of the column containing current period values.
        """
        if not table or len(table) < 2:
            return 1  # Default to second column

        # Build a map of column indices to their header text
        column_headers = {}
        for row in table[:5]:  # Check first 5 rows for headers
            for idx, cell in enumerate(row):
                cell_str = str(cell).strip().replace(" ", "") if cell else ""
                if cell_str and idx > 0:  # Skip first column (item names)
                    if idx not in column_headers:
                        column_headers[idx] = cell_str
                    else:
                        column_headers[idx] += " " + cell_str

        logger.debug(f"Column headers detected: {column_headers}")

        # For income statements, prefer cumulative columns (누적)
        if statement_type == "income_statement":
            # First priority: "당분기 누적" or "당기 누적"
            for idx, header in column_headers.items():
                header_clean = header.replace(" ", "")
                if '당' in header_clean and '누적' in header_clean:
                    logger.debug(f"Found current period cumulative column at index {idx}: {header}")
                    return idx

            # Second priority: Any "당분기" or "당기" column (not 3개월)
            for idx, header in column_headers.items():
                header_clean = header.replace(" ", "")
                if ('당분기' in header_clean or '당기' in header_clean) and '3개월' not in header_clean:
                    logger.debug(f"Found current period column at index {idx}: {header}")
                    return idx

        # For balance sheets, look for current period end (당분기말/당기말)
        for idx, header in column_headers.items():
            header_clean = header.replace(" ", "")
            if any(kw in header_clean for kw in ['당분기말', '당기말', '당분기', '당기']):
                logger.debug(f"Found balance sheet current period column at index {idx}: {header}")
                return idx

        # Check for fiscal period indicators like "제 57 기"
        for idx, header in column_headers.items():
            if re.search(r'제\s*\d+\s*기', header):
                logger.debug(f"Found fiscal period column at index {idx}: {header}")
                return idx

        # Default: second column (index 1) is usually current period
        logger.debug("Using default column index 1")
        return 1

    def _parse_financial_table(self, table: List[List[str]], statement_type: str = "balance_sheet") -> Dict[str, Any]:
        """
        Parse table rows into dictionary of financial items.

        Enhanced for DART format:
        - Cleans item names by removing note references (주X)
        - Skips notes/footnotes rows
        - Handles multi-column tables (picks current period for balance sheet, cumulative for income statement)
        - Prioritizes aggregate/total rows
        """
        parsed = {}

        # Find the correct value column based on statement type
        value_col_idx = self._find_value_column_index(table, statement_type)
        logger.debug(f"Using column index {value_col_idx} for {statement_type} values")

        for row in table:
            if len(row) < 2:
                continue

            # Get item name (always first column)
            raw_item_name = str(row[0]).strip() if row[0] else ""

            # Skip empty names, notes rows, and header rows
            if not raw_item_name or self._is_notes_row(raw_item_name):
                continue

            # Clean the item name (remove note references)
            item_name = self._clean_item_name(raw_item_name)
            if not item_name:
                continue

            # Get value from the appropriate column
            value_str = ""
            if value_col_idx < len(row) and row[value_col_idx]:
                value_str = str(row[value_col_idx]).strip()
            elif len(row) > 1 and row[1]:
                # Fallback to second column
                value_str = str(row[1]).strip()

            if not value_str or value_str == "0":
                continue

            # Parse and store value
            value = self._parse_financial_value(value_str)

            # Only store if it's a meaningful value (not 0.0 from failed parsing)
            if value != 0.0 or value_str in ["0", "0.0", "-"]:
                # For aggregate rows, ensure they overwrite non-aggregate entries
                if self._is_aggregate_row(item_name):
                    parsed[item_name] = value
                    logger.debug(f"Extracted aggregate: {item_name} = {value}")
                elif item_name not in parsed:
                    # Only add non-aggregate if key doesn't exist
                    parsed[item_name] = value

        return parsed

    def _find_value_column_index_df(self, df, statement_type: str = "balance_sheet") -> int:
        """Find correct value column index for DataFrame (Camelot extraction)."""
        if df.empty or len(df) < 2:
            return 1

        # Build column headers map
        column_headers = {}
        for row_idx in range(min(5, len(df))):
            for col_idx, cell in enumerate(df.iloc[row_idx]):
                cell_str = str(cell).strip().replace(" ", "") if cell else ""
                if cell_str and col_idx > 0:
                    if col_idx not in column_headers:
                        column_headers[col_idx] = cell_str
                    else:
                        column_headers[col_idx] += " " + cell_str

        # For income statements, prefer cumulative columns
        if statement_type == "income_statement":
            for idx, header in column_headers.items():
                header_clean = header.replace(" ", "")
                if '당' in header_clean and '누적' in header_clean:
                    return idx
            for idx, header in column_headers.items():
                header_clean = header.replace(" ", "")
                if ('당분기' in header_clean or '당기' in header_clean) and '3개월' not in header_clean:
                    return idx

        # For balance sheets
        for idx, header in column_headers.items():
            header_clean = header.replace(" ", "")
            if any(kw in header_clean for kw in ['당분기말', '당기말', '당분기', '당기']):
                return idx

        return 1

    def _parse_financial_table_from_dataframe(self, df, statement_type: str = "balance_sheet") -> Dict[str, Any]:
        """
        Parse DataFrame into dictionary of financial items.

        Enhanced for DART format with notes filtering and item name cleaning.
        """
        parsed = {}

        value_col_idx = self._find_value_column_index_df(df, statement_type)

        for idx, row in df.iterrows():
            if len(row) < 2:
                continue

            raw_item_name = str(row.iloc[0]).strip() if row.iloc[0] else ""

            # Skip notes rows
            if not raw_item_name or self._is_notes_row(raw_item_name):
                continue

            # Clean the item name (remove note references)
            item_name = self._clean_item_name(raw_item_name)
            if not item_name:
                continue

            # Get value from appropriate column
            value_str = ""
            if value_col_idx < len(row):
                value_str = str(row.iloc[value_col_idx]).strip()
            elif len(row) > 1:
                value_str = str(row.iloc[1]).strip()

            if not value_str:
                continue

            value = self._parse_financial_value(value_str)

            if value != 0.0 or value_str in ["0", "0.0", "-"]:
                if self._is_aggregate_row(item_name):
                    parsed[item_name] = value
                elif item_name not in parsed:
                    parsed[item_name] = value

        return parsed

    def _parse_financial_value(self, value_str: str) -> float:
        """
        Parse financial value string to float.

        Handles DART-specific formats:
        - Comma-separated numbers: "523,659,586"
        - Negative in parentheses: "(1,234)"
        - Korean won symbol: "₩1,234"
        - Dash for zero: "-"
        - Empty/whitespace: ""
        - Multi-line values
        """
        if not value_str:
            return 0.0

        # Handle newlines (multi-line cells)
        value_str = value_str.replace('\n', ' ').strip()

        # Handle empty or dash values
        if value_str in ['-', '—', '－', '']:
            return 0.0

        # Remove common formatting
        cleaned = value_str
        cleaned = cleaned.replace(',', '')  # Remove thousands separators
        cleaned = cleaned.replace('₩', '')  # Remove Korean won symbol
        cleaned = cleaned.replace('$', '')  # Remove dollar sign
        cleaned = cleaned.replace(' ', '')  # Remove spaces

        # Handle negative numbers in parentheses: (1234) -> -1234
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]
        # Handle Korean negative indicator △ or ▲
        if cleaned.startswith('△') or cleaned.startswith('▲'):
            cleaned = '-' + cleaned[1:]

        cleaned = cleaned.strip()

        # Final validation - should only contain digits, decimal point, and minus sign
        if not cleaned:
            return 0.0

        try:
            return float(cleaned)
        except ValueError:
            # Try to extract just the numeric part
            numeric_match = re.search(r'-?[\d.]+', cleaned)
            if numeric_match:
                try:
                    return float(numeric_match.group())
                except ValueError:
                    pass
            logger.debug(f"Could not parse value: '{value_str}' -> '{cleaned}'")
            return 0.0

    def _parse_ocr_text(self, pages_text: List[str]) -> Dict[str, Any]:
        """
        Parse OCR-extracted text to financial data.
        This is a placeholder - production would need sophisticated NLP.
        """
        # This would require NLP/pattern matching to extract structured data from text
        # For now, return minimal structure
        return {
            "balance_sheet": {
                "total_assets": 0,
                "total_liabilities": 0,
                "total_equity": 0
            },
            "income_statement": {
                "revenue": 0,
                "operating_income": 0,
                "net_income": 0
            }
        }

    def _has_sufficient_data(self, data: Dict[str, Any]) -> bool:
        """Check if extracted data has minimum required fields"""
        bs = data.get("balance_sheet", {})
        is_data = data.get("income_statement", {})
        cf = data.get("cash_flow_statement", {})

        # Minimum requirement: at least one item from any financial statement
        # This allows processing with partial data (e.g., balance sheet only)
        return len(bs) > 0 or len(is_data) > 0 or len(cf) > 0

    def _validate_normalized_data(self, data: Dict[str, Any]):
        """Validate normalized data has required K-IFRS fields"""
        required_bs = ["total_assets", "total_liabilities", "total_equity"]
        required_is = ["revenue", "operating_income", "net_income"]

        # Check balance sheet fields (log warnings instead of raising errors)
        bs = data.get("balance_sheet", {})
        missing_bs_fields = [field for field in required_bs if field not in bs]
        if missing_bs_fields:
            logger.warning(f"Missing balance sheet fields: {', '.join(missing_bs_fields)}. Proceeding with available data.")

        # Check income statement fields (log warnings instead of raising errors)
        is_data = data.get("income_statement", {})
        missing_is_fields = [field for field in required_is if field not in is_data]
        if missing_is_fields:
            logger.warning(f"Missing income statement fields: {', '.join(missing_is_fields)}. Proceeding with available data.")

        # Only raise error if completely empty (no data at all)
        if not bs and not is_data and not data.get("cash_flow_statement", {}):
            raise ValidationError("No financial data could be extracted from the document")
