"""
XBRL Analysis Repository Port

Abstract interface for XBRL analysis data persistence.
Following hexagonal architecture principles.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from financial_statement.domain.xbrl_analysis import XBRLAnalysis


class XBRLAnalysisRepositoryPort(ABC):
    """
    Port interface for XBRL analysis repository operations.
    
    Implementations must provide methods for:
    - Saving analysis results
    - Retrieving analyses by ID, user, corporation
    - Updating analysis status
    - Deleting analyses
    """
    
    @abstractmethod
    def save(self, analysis: XBRLAnalysis) -> XBRLAnalysis:
        """
        Save or update an XBRL analysis.
        
        Args:
            analysis: XBRLAnalysis domain entity
            
        Returns:
            Saved analysis with ID populated
        """
        pass
    
    @abstractmethod
    def find_by_id(self, analysis_id: int) -> Optional[XBRLAnalysis]:
        """
        Find analysis by ID.
        
        Args:
            analysis_id: Analysis record ID
            
        Returns:
            XBRLAnalysis if found, None otherwise
        """
        pass
    
    @abstractmethod
    def find_by_user_id(
        self,
        user_id: int,
        page: int = 1,
        size: int = 10
    ) -> List[XBRLAnalysis]:
        """
        Find all analyses for a user with pagination.
        
        Args:
            user_id: User ID
            page: Page number (1-indexed)
            size: Page size
            
        Returns:
            List of XBRLAnalysis entities
        """
        pass
    
    @abstractmethod
    def find_by_corp_code(
        self,
        corp_code: str,
        fiscal_year: Optional[int] = None
    ) -> List[XBRLAnalysis]:
        """
        Find analyses by corporation code.
        
        Args:
            corp_code: DART corporation code
            fiscal_year: Optional fiscal year filter
            
        Returns:
            List of matching analyses
        """
        pass
    
    @abstractmethod
    def count_by_user_id(self, user_id: int) -> int:
        """
        Count total analyses for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Total count
        """
        pass
    
    @abstractmethod
    def delete(self, analysis_id: int) -> bool:
        """
        Delete an analysis by ID.
        
        Args:
            analysis_id: Analysis ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    def update_status(
        self,
        analysis_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update analysis status.
        
        Args:
            analysis_id: Analysis ID
            status: New status string
            error_message: Optional error message if failed
            
        Returns:
            True if updated, False if not found
        """
        pass
