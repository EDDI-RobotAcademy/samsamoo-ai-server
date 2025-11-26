"""
XBRL Document Domain Entity

Represents parsed XBRL financial statement data with support for
Korean DART (K-IFRS/K-GAAP) and international XBRL taxonomies.
"""
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field


class XBRLTaxonomy(Enum):
    """Supported XBRL taxonomies"""
    KIFRS = "kifrs"          # Korean IFRS
    KGAAP = "kgaap"          # Korean GAAP
    IFRS = "ifrs"            # International IFRS
    US_GAAP = "us-gaap"      # US GAAP
    UNKNOWN = "unknown"


class ReportType(Enum):
    """Financial report types"""
    ANNUAL = "annual"           # 사업보고서
    SEMI_ANNUAL = "semi_annual" # 반기보고서
    QUARTERLY = "quarterly"     # 분기보고서
    CONSOLIDATED = "consolidated"
    SEPARATE = "separate"


@dataclass
class XBRLContext:
    """
    XBRL Context representing a specific reporting period and entity.
    
    XBRL contexts define the "who, what, when" for reported facts:
    - Entity: The reporting company
    - Period: Instant (point in time) or duration (period of time)
    - Scenario/Segment: Additional dimensional qualifiers
    """
    context_id: str
    entity_identifier: str  # Company stock code or identifier
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    instant: Optional[date] = None  # For balance sheet items (point in time)
    scenario: Optional[str] = None  # consolidated vs separate
    
    @property
    def is_instant(self) -> bool:
        """Check if this context represents an instant (point in time)"""
        return self.instant is not None
    
    @property
    def is_duration(self) -> bool:
        """Check if this context represents a duration (period)"""
        return self.period_start is not None and self.period_end is not None
    
    def __repr__(self):
        if self.is_instant:
            return f"XBRLContext(id={self.context_id}, instant={self.instant})"
        return f"XBRLContext(id={self.context_id}, period={self.period_start} to {self.period_end})"


@dataclass
class XBRLFact:
    """
    XBRL Fact representing a single reported value.
    
    A fact is the combination of:
    - Concept (what is being reported - e.g., "Assets")
    - Context (who, when)
    - Value (the numeric or text value)
    - Unit (currency, shares, etc.)
    """
    concept: str              # e.g., "ifrs-full:Assets", "kifrs:자산총계"
    context_ref: str          # Reference to XBRLContext
    value: Any                # Numeric value or text
    unit_ref: Optional[str] = None  # e.g., "KRW", "USD", "shares"
    decimals: Optional[int] = None  # Precision indicator
    scale: Optional[int] = None     # Scale factor (e.g., 1000 for thousands)
    
    # Parsed metadata
    namespace: Optional[str] = None  # e.g., "ifrs-full", "kifrs"
    local_name: Optional[str] = None  # e.g., "Assets", "자산총계"
    label: Optional[str] = None       # Korean label e.g., "자산총계", "부채총계"
    
    @property
    def numeric_value(self) -> Optional[float]:
        """Get numeric value with scale applied"""
        if self.value is None:
            return None
        try:
            val = float(self.value)
            if self.scale:
                val *= (10 ** self.scale)
            return val
        except (ValueError, TypeError):
            return None
    
    @property
    def is_monetary(self) -> bool:
        """Check if this fact represents a monetary value"""
        return self.unit_ref is not None and self.unit_ref.upper() in ['KRW', 'USD', 'EUR', 'JPY', 'CNY']
    
    def __repr__(self):
        return f"XBRLFact(concept={self.concept}, value={self.value}, unit={self.unit_ref})"


@dataclass 
class XBRLUnit:
    """XBRL Unit definition"""
    unit_id: str
    measure: str  # e.g., "iso4217:KRW", "xbrli:shares"
    
    @property
    def currency_code(self) -> Optional[str]:
        """Extract currency code if this is a currency unit"""
        if self.measure.startswith("iso4217:"):
            return self.measure.split(":")[1]
        return None


class XBRLDocument:
    """
    Domain entity representing a parsed XBRL financial statement document.
    
    This entity holds the complete structured data extracted from an XBRL file,
    including all contexts, units, and facts, with methods for extracting
    specific financial statement components.
    """
    
    def __init__(
        self,
        corp_code: str,
        corp_name: str,
        fiscal_year: int,
        report_type: ReportType,
        taxonomy: XBRLTaxonomy = XBRLTaxonomy.KIFRS
    ):
        self.id: Optional[int] = None
        self.corp_code = corp_code          # DART 고유번호
        self.corp_name = corp_name
        self.fiscal_year = fiscal_year
        self.report_type = report_type
        self.taxonomy = taxonomy
        
        # XBRL components
        self.contexts: Dict[str, XBRLContext] = {}
        self.units: Dict[str, XBRLUnit] = {}
        self.facts: List[XBRLFact] = []
        
        # Metadata
        self.source_file: Optional[str] = None
        self.filing_date: Optional[date] = None
        self.period_end_date: Optional[date] = None
        self.created_at: datetime = datetime.utcnow()
        
        self._validate()
    
    def _validate(self):
        """Validate business rules"""
        if not self.corp_code or len(self.corp_code.strip()) == 0:
            raise ValueError("Corporation code cannot be empty")
        if self.fiscal_year < 1990 or self.fiscal_year > 2100:
            raise ValueError(f"Invalid fiscal year: {self.fiscal_year}")
    
    def add_context(self, context: XBRLContext):
        """Add a context definition"""
        self.contexts[context.context_id] = context
    
    def add_unit(self, unit: XBRLUnit):
        """Add a unit definition"""
        self.units[unit.unit_id] = unit
    
    def add_fact(self, fact: XBRLFact):
        """Add a fact (reported value)"""
        self.facts.append(fact)
    
    def get_context(self, context_ref: str) -> Optional[XBRLContext]:
        """Get context by reference ID"""
        return self.contexts.get(context_ref)
    
    def get_unit(self, unit_ref: str) -> Optional[XBRLUnit]:
        """Get unit by reference ID"""
        return self.units.get(unit_ref)
    
    def get_facts_by_concept(self, concept_pattern: str) -> List[XBRLFact]:
        """
        Get all facts matching a concept pattern.
        Supports partial matching for flexibility across taxonomies.
        """
        matching = []
        pattern_lower = concept_pattern.lower()
        for fact in self.facts:
            if pattern_lower in fact.concept.lower():
                matching.append(fact)
        return matching
    
    def get_current_period_facts(self) -> List[XBRLFact]:
        """Get facts for the current reporting period"""
        current_period = []
        for fact in self.facts:
            context = self.get_context(fact.context_ref)
            if context:
                # For instant contexts, check if it's the period end date
                if context.is_instant and context.instant == self.period_end_date:
                    current_period.append(fact)
                # For duration contexts, check period end
                elif context.is_duration and context.period_end == self.period_end_date:
                    current_period.append(fact)
        return current_period
    
    def extract_balance_sheet(self) -> Dict[str, Any]:
        """
        Extract balance sheet items from XBRL facts.
        Maps XBRL concepts to standardized field names.
        """
        # K-IFRS concept mappings for balance sheet
        concept_mappings = {
            # Assets
            'total_assets': ['Assets', '자산총계', 'TotalAssets'],
            'current_assets': ['CurrentAssets', '유동자산', '유동자산합계'],
            'non_current_assets': ['NoncurrentAssets', '비유동자산', '비유동자산합계'],
            'cash': ['CashAndCashEquivalents', '현금및현금성자산', '현금및예치금'],
            'inventory': ['Inventories', '재고자산'],
            'trade_receivables': ['TradeAndOtherReceivables', '매출채권', '매출채권및기타채권'],
            
            # Liabilities
            'total_liabilities': ['Liabilities', '부채총계', 'TotalLiabilities'],
            'current_liabilities': ['CurrentLiabilities', '유동부채', '유동부채합계'],
            'non_current_liabilities': ['NoncurrentLiabilities', '비유동부채', '비유동부채합계'],
            'trade_payables': ['TradeAndOtherPayables', '매입채무', '매입채무및기타채무'],
            'borrowings': ['Borrowings', '차입금', '단기차입금'],
            
            # Equity
            'total_equity': ['Equity', '자본총계', 'TotalEquity', 'StockholdersEquity'],
            'share_capital': ['IssuedCapital', '자본금', '보통주자본금'],
            'retained_earnings': ['RetainedEarnings', '이익잉여금', '미처분이익잉여금'],
        }
        
        balance_sheet = {}
        current_facts = self.get_current_period_facts()
        
        for field_name, concepts in concept_mappings.items():
            for concept in concepts:
                facts = [f for f in current_facts if concept.lower() in f.concept.lower()]
                if facts:
                    # Use the first matching fact's numeric value
                    value = facts[0].numeric_value
                    if value is not None:
                        balance_sheet[field_name] = value
                        break
        
        return balance_sheet
    
    def extract_income_statement(self) -> Dict[str, Any]:
        """
        Extract income statement items from XBRL facts.
        Maps XBRL concepts to standardized field names.
        """
        # K-IFRS concept mappings for income statement
        concept_mappings = {
            'revenue': ['Revenue', '매출액', '수익', 'SalesRevenue', '영업수익'],
            'cost_of_sales': ['CostOfSales', '매출원가', '영업비용'],
            'gross_profit': ['GrossProfit', '매출총이익', '영업이익_매출총이익'],
            'operating_income': ['ProfitLossFromOperatingActivities', '영업이익', 'OperatingProfit'],
            'operating_expenses': ['OperatingExpenses', '판매비와관리비', '판관비'],
            'interest_expense': ['InterestExpense', '이자비용', '금융비용'],
            'interest_income': ['InterestIncome', '이자수익', '금융수익'],
            'income_before_tax': ['ProfitLossBeforeTax', '법인세비용차감전순이익', '세전이익'],
            'income_tax_expense': ['IncomeTaxExpense', '법인세비용'],
            'net_income': ['ProfitLoss', '당기순이익', 'NetIncome', '당기순이익(손실)'],
            'eps': ['BasicEarningsLossPerShare', '기본주당이익', 'EarningsPerShare'],
        }
        
        income_statement = {}
        current_facts = self.get_current_period_facts()
        
        for field_name, concepts in concept_mappings.items():
            for concept in concepts:
                facts = [f for f in current_facts if concept.lower() in f.concept.lower()]
                if facts:
                    value = facts[0].numeric_value
                    if value is not None:
                        income_statement[field_name] = value
                        break
        
        return income_statement
    
    def extract_cash_flow(self) -> Dict[str, Any]:
        """
        Extract cash flow statement items from XBRL facts.
        """
        concept_mappings = {
            'operating_cash_flow': ['CashFlowsFromUsedInOperatingActivities', '영업활동현금흐름'],
            'investing_cash_flow': ['CashFlowsFromUsedInInvestingActivities', '투자활동현금흐름'],
            'financing_cash_flow': ['CashFlowsFromUsedInFinancingActivities', '재무활동현금흐름'],
            'net_cash_flow': ['IncreaseDecreaseInCashAndCashEquivalents', '현금및현금성자산의순증감'],
            'capex': ['PurchaseOfPropertyPlantAndEquipment', '유형자산의취득'],
            'depreciation': ['DepreciationAndAmortisation', '감가상각비'],
        }
        
        cash_flow = {}
        current_facts = self.get_current_period_facts()
        
        for field_name, concepts in concept_mappings.items():
            for concept in concepts:
                facts = [f for f in current_facts if concept.lower() in f.concept.lower()]
                if facts:
                    value = facts[0].numeric_value
                    if value is not None:
                        cash_flow[field_name] = value
                        break
        
        return cash_flow
    
    def to_normalized_data(self) -> Dict[str, Any]:
        """
        Convert XBRL document to normalized financial data format
        compatible with existing ratio calculation service.
        """
        return {
            'balance_sheet': self.extract_balance_sheet(),
            'income_statement': self.extract_income_statement(),
            'cash_flow_statement': self.extract_cash_flow(),
            'metadata': {
                'corp_code': self.corp_code,
                'corp_name': self.corp_name,
                'fiscal_year': self.fiscal_year,
                'report_type': self.report_type.value,
                'taxonomy': self.taxonomy.value,
                'period_end_date': self.period_end_date.isoformat() if self.period_end_date else None,
                'source': 'xbrl'
            }
        }
    
    def get_fact_count(self) -> int:
        """Get total number of facts in document"""
        return len(self.facts)
    
    def get_available_concepts(self) -> List[str]:
        """Get list of all unique concepts in the document"""
        return list(set(fact.concept for fact in self.facts))
    
    def is_complete(self) -> bool:
        """Check if document has minimum required data for analysis"""
        bs = self.extract_balance_sheet()
        is_stmt = self.extract_income_statement()
        
        required_bs = ['total_assets', 'total_liabilities', 'total_equity']
        required_is = ['revenue', 'net_income']
        
        has_bs = all(field in bs for field in required_bs)
        has_is = any(field in is_stmt for field in required_is)
        
        return has_bs and has_is
    
    def __repr__(self):
        return (
            f"XBRLDocument(corp={self.corp_name}, year={self.fiscal_year}, "
            f"type={self.report_type.value}, facts={len(self.facts)})"
        )
