import pdfplumber
import camelot
# import pytesseract  # OCR disabled
# from PIL import Image  # OCR disabled
from typing import Dict, Any, List
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
    """

    def __init__(self):
        self.table_confidence_threshold = 0.7
        self.ocr_fallback_enabled = False  # OCR disabled

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
                        parsed_table = self._parse_financial_table(table)
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
                    parsed_table = self._parse_financial_table_from_dataframe(df)
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
        """Normalize balance sheet items to K-IFRS standard names"""
        # K-IFRS mapping table with Korean variations (including spaced versions)
        mapping = {
            # Assets (자산) - multiple variations
            "자산총계": "total_assets",
            "자 산 총 계": "total_assets",
            "총자산": "total_assets",
            "총 자 산": "total_assets",
            "자산": "total_assets",
            "자 산": "total_assets",
            "자산계": "total_assets",
            "자 산 계": "total_assets",
            "유동자산": "current_assets",
            "유 동 자 산": "current_assets",
            "유동자산계": "current_assets",
            "비유동자산": "non_current_assets",
            "비 유 동 자 산": "non_current_assets",
            "비유동자산계": "non_current_assets",
            "현금및현금성자산": "cash_and_equivalents",
            "현 금 및 현 금 성 자 산": "cash_and_equivalents",
            "재고자산": "inventory",
            "재 고 자 산": "inventory",

            # Liabilities (부채) - multiple variations
            "부채총계": "total_liabilities",
            "부 채 총 계": "total_liabilities",
            "총부채": "total_liabilities",
            "총 부 채": "total_liabilities",
            "부채": "total_liabilities",
            "부 채": "total_liabilities",
            "부채계": "total_liabilities",
            "부 채 계": "total_liabilities",
            "유동부채": "current_liabilities",
            "유 동 부 채": "current_liabilities",
            "유동부채계": "current_liabilities",
            "비유동부채": "non_current_liabilities",
            "비 유 동 부 채": "non_current_liabilities",
            "비유동부채계": "non_current_liabilities",

            # Equity (자본) - multiple variations
            "자본총계": "total_equity",
            "자 본 총 계": "total_equity",
            "총자본": "total_equity",
            "총 자 본": "total_equity",
            "자본": "total_equity",
            "자 본": "total_equity",
            "자본계": "total_equity",
            "자 본 계": "total_equity",
            "지배기업소유주지분": "total_equity",
            "지 배 기 업 소 유 주 지 분": "total_equity",
            "자본금": "capital_stock",
            "자 본 금": "capital_stock",
            "이익잉여금": "retained_earnings",
            "이 익 잉 여 금": "retained_earnings",
        }

        normalized = {}
        for raw_key, raw_value in raw_data.items():
            # Remove spaces from raw_key for better matching
            cleaned_key = raw_key.replace(" ", "")
            normalized_key = mapping.get(cleaned_key, mapping.get(raw_key, raw_key))

            # Debug logging for unmapped keys
            if normalized_key == raw_key and normalized_key not in mapping:
                logger.debug(f"Unmapped balance sheet key: '{raw_key}' (cleaned: '{cleaned_key}')")

            normalized[normalized_key] = raw_value

        # Log summary of mapped vs unmapped
        mapped_standard_keys = [k for k in normalized.keys() if k in ["total_assets", "total_liabilities", "total_equity", "current_assets", "non_current_assets", "current_liabilities", "non_current_liabilities", "cash_and_equivalents", "inventory", "capital_stock", "retained_earnings"]]
        logger.info(f"Balance sheet normalization: {len(mapped_standard_keys)} standard K-IFRS fields mapped from {len(raw_data)} raw items")

        return normalized

    def _normalize_income_statement(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize income statement items to K-IFRS standard names"""
        # K-IFRS mapping table with Korean variations (including spaced versions)
        mapping = {
            # Revenue
            "매출액": "revenue",
            "매 출 액": "revenue",
            "수익": "revenue",
            "수 익": "revenue",
            "매출": "revenue",
            "매 출": "revenue",

            # Operating income
            "영업이익": "operating_income",
            "영 업 이 익": "operating_income",

            # Net income
            "당기순이익": "net_income",
            "당 기 순 이 익": "net_income",
            "분기순이익": "net_income",
            "분 기 순 이 익": "net_income",
            "순이익": "net_income",
            "순 이 익": "net_income",

            # Cost and expenses
            "매출원가": "cost_of_revenue",
            "매 출 원 가": "cost_of_revenue",
            "판매비와관리비": "operating_expenses",
            "판 매 비 와 관 리 비": "operating_expenses",
            "영업외수익": "non_operating_income",
            "영 업 외 수 익": "non_operating_income",
            "영업외비용": "non_operating_expenses",
            "영 업 외 비 용": "non_operating_expenses",
            "법인세비용": "income_tax_expense",
            "법 인 세 비 용": "income_tax_expense",
        }

        normalized = {}
        for raw_key, raw_value in raw_data.items():
            # Remove spaces from raw_key for better matching
            cleaned_key = raw_key.replace(" ", "")
            normalized_key = mapping.get(cleaned_key, mapping.get(raw_key, raw_key))
            normalized[normalized_key] = raw_value

        return normalized

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

    def _parse_financial_table(self, table: List[List[str]]) -> Dict[str, Any]:
        """Parse table rows into dictionary of financial items"""
        parsed = {}

        for row in table:
            if len(row) < 2:
                continue

            # Assume first column is item name, second is value
            item_name = str(row[0]).strip() if row[0] else ""
            value_str = str(row[1]).strip() if row[1] else "0"

            if item_name and value_str:
                # Clean and convert value
                parsed[item_name] = self._parse_financial_value(value_str)

        return parsed

    def _parse_financial_table_from_dataframe(self, df) -> Dict[str, Any]:
        """Parse DataFrame into dictionary of financial items"""
        parsed = {}

        for idx, row in df.iterrows():
            if len(row) < 2:
                continue

            item_name = str(row[0]).strip()
            value_str = str(row[1]).strip()

            if item_name and value_str:
                parsed[item_name] = self._parse_financial_value(value_str)

        return parsed

    def _parse_financial_value(self, value_str: str) -> float:
        """Parse financial value string to float"""
        # Remove common formatting (commas, parentheses, currency symbols)
        cleaned = value_str.replace(',', '').replace('(', '-').replace(')', '')
        cleaned = cleaned.replace('₩', '').replace('$', '').strip()

        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not parse value: {value_str}")
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
