"""
XBRL Extraction Service Port

Abstract interface for XBRL document parsing and extraction services.
Implementations can support different XBRL sources (DART, SEC, local files).
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from financial_statement.domain.xbrl_document import XBRLDocument, XBRLTaxonomy, ReportType


class XBRLExtractionServicePort(ABC):
    """
    Port interface for XBRL extraction services.
    
    This abstracts the complexity of XBRL parsing and allows different
    implementations for various data sources (DART API, local files, etc.)
    """
    
    @abstractmethod
    def parse_xbrl_file(
        self,
        file_path: str,
        corp_code: str,
        corp_name: str,
        fiscal_year: int,
        report_type: ReportType
    ) -> XBRLDocument:
        """
        Parse a local XBRL file and extract financial data.
        
        Args:
            file_path: Path to the XBRL file (XML or ZIP)
            corp_code: Corporation code (DART 고유번호)
            corp_name: Corporation name
            fiscal_year: Fiscal year of the report
            report_type: Type of report (annual, quarterly, etc.)
            
        Returns:
            XBRLDocument containing parsed data
            
        Raises:
            XBRLParseError: If parsing fails
        """
        pass
    
    @abstractmethod
    def parse_xbrl_content(
        self,
        content: bytes,
        corp_code: str,
        corp_name: str,
        fiscal_year: int,
        report_type: ReportType,
        taxonomy: XBRLTaxonomy = XBRLTaxonomy.KIFRS
    ) -> XBRLDocument:
        """
        Parse XBRL content from bytes (e.g., API response).
        
        Args:
            content: Raw XBRL content as bytes
            corp_code: Corporation code
            corp_name: Corporation name
            fiscal_year: Fiscal year
            report_type: Report type
            taxonomy: XBRL taxonomy standard
            
        Returns:
            XBRLDocument containing parsed data
        """
        pass
    
    @abstractmethod
    def extract_financial_data(
        self,
        xbrl_doc: XBRLDocument
    ) -> Dict[str, Any]:
        """
        Extract normalized financial data from parsed XBRL document.
        
        This converts XBRL concepts to a standardized format compatible
        with the existing ratio calculation service.
        
        Args:
            xbrl_doc: Parsed XBRLDocument
            
        Returns:
            Dictionary with balance_sheet, income_statement, cash_flow_statement
        """
        pass
    
    @abstractmethod
    def get_available_concepts(
        self,
        xbrl_doc: XBRLDocument,
        filter_pattern: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of available XBRL concepts in the document.
        
        Useful for debugging and understanding what data is available.
        
        Args:
            xbrl_doc: Parsed XBRLDocument
            filter_pattern: Optional pattern to filter concepts
            
        Returns:
            List of concept metadata dictionaries
        """
        pass
    
    @abstractmethod
    def validate_xbrl_structure(
        self,
        xbrl_doc: XBRLDocument,
        financial_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate XBRL document structure and completeness.

        Args:
            xbrl_doc: The parsed XBRL document
            financial_data: Optional pre-extracted financial data for accurate validation

        Returns:
            Validation result with status and any warnings/errors
        """
        pass


class DARTXBRLServicePort(ABC):
    """
    Port interface for DART-specific XBRL operations.
    
    Handles integration with Korean DART (전자공시시스템) API
    for fetching XBRL financial statements.
    """
    
    @abstractmethod
    async def search_corporation(
        self,
        corp_name: str
    ) -> List[Dict[str, str]]:
        """
        Search for corporations by name.
        
        Args:
            corp_name: Corporation name (partial match supported)
            
        Returns:
            List of matching corporations with corp_code and corp_name
        """
        pass
    
    @abstractmethod
    async def download_xbrl(
        self,
        corp_code: str,
        fiscal_year: int,
        report_type: ReportType,
        consolidated: bool = True
    ) -> bytes:
        """
        Download XBRL financial statement from DART API.
        
        Args:
            corp_code: DART corporation code (8자리)
            fiscal_year: Fiscal year (e.g., 2024)
            report_type: Annual, semi-annual, or quarterly
            consolidated: True for consolidated, False for separate
            
        Returns:
            XBRL file content as bytes
            
        Raises:
            DARTAPIError: If API call fails
            NotFoundError: If no data found for the query
        """
        pass
    
    @abstractmethod
    async def get_financial_statements(
        self,
        corp_code: str,
        fiscal_year: int,
        report_type: ReportType = ReportType.ANNUAL
    ) -> XBRLDocument:
        """
        Download and parse XBRL financial statements in one operation.
        
        This is a convenience method that combines download_xbrl
        and parse_xbrl_content.
        
        Args:
            corp_code: DART corporation code
            fiscal_year: Fiscal year
            report_type: Report type
            
        Returns:
            Parsed XBRLDocument
        """
        pass
    
    @abstractmethod
    async def get_corp_info(
        self,
        corp_code: str
    ) -> Dict[str, Any]:
        """
        Get corporation basic information from DART.
        
        Args:
            corp_code: DART corporation code
            
        Returns:
            Corporation information including name, stock code, industry, etc.
        """
        pass
    
    @abstractmethod
    async def list_available_reports(
        self,
        corp_code: str,
        begin_year: int,
        end_year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List available financial reports for a corporation.
        
        Args:
            corp_code: DART corporation code
            begin_year: Start year
            end_year: End year (defaults to current year)
            
        Returns:
            List of available reports with dates and types
        """
        pass
