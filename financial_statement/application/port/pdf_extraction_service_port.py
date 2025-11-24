from abc import ABC, abstractmethod
from typing import Dict, Any


class PDFExtractionServicePort(ABC):
    """
    Port interface for PDF extraction and normalization services.
    Stage 1 of the analysis pipeline.
    """

    @abstractmethod
    def extract_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract financial tables from PDF using PDFPlumber/Camelot.

        Args:
            pdf_path: Local path to PDF file

        Returns:
            Dictionary with extracted tables:
            {
                "balance_sheet": {...},
                "income_statement": {...},
                "cash_flow_statement": {...}  # optional
            }

        Raises:
            ExtractionError: If extraction fails
        """
        pass

    @abstractmethod
    def extract_from_scanned_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract financial tables from scanned PDF using OCR (Tesseract + LayoutLMv3).

        Args:
            pdf_path: Local path to scanned PDF file

        Returns:
            Dictionary with extracted tables (same format as extract_from_pdf)

        Raises:
            ExtractionError: If OCR fails
        """
        pass

    @abstractmethod
    def normalize_to_kifrs(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize extracted financial items to K-IFRS taxonomy.

        Args:
            extracted_data: Raw extracted data from PDF

        Returns:
            Normalized data with standardized K-IFRS item names

        Raises:
            ValidationError: If required items are missing
        """
        pass
