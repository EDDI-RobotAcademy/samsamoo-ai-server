#!/usr/bin/env python
"""
Test script for DART PDF extraction improvements.

This script tests the PDFExtractionService with sample DART financial documents
to verify correct extraction of:
1. Balance sheet items (자산총계, 부채총계, 자본총계, etc.)
2. Income statement items (매출액, 영업이익, 당기순이익, etc.)
3. Proper column selection (cumulative values for income statement)
4. Note reference removal (주X patterns)

Usage:
    cd SamSamOO-AI-Server
    python scripts/test_dart_extraction.py [--pdf PATH]
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Direct import to avoid chain imports of optional dependencies
import importlib.util
spec = importlib.util.spec_from_file_location(
    "pdf_extraction_service",
    str(Path(__file__).parent.parent / "financial_statement" / "infrastructure" / "service" / "pdf_extraction_service.py")
)
pdf_extraction_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pdf_extraction_module)
PDFExtractionService = pdf_extraction_module.PDFExtractionService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_item_name_cleaning():
    """Test the _clean_item_name method with various DART patterns."""
    service = PDFExtractionService()

    test_cases = [
        ("현금및현금성자산 (주3,26)", "현금및현금성자산"),
        ("매출액 (주27)", "매출액"),
        ("기본주당이익 (단위 : 원)", "기본주당이익"),
        ("Ⅰ.유동자산", "유동자산"),
        ("II.비유동자산", "비유동자산"),
        ("1.매출원가", "매출원가"),
        ("자산총계 (주석 3)", "자산총계"),
        ("  재고자산  ", "재고자산"),
        ("영업이익(손실)", "영업이익"),
    ]

    print("\n" + "="*60)
    print("TEST: Item Name Cleaning")
    print("="*60)

    passed = 0
    failed = 0

    for input_val, expected in test_cases:
        result = service._clean_item_name(input_val)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status}: '{input_val}' -> '{result}' (expected: '{expected}')")

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_value_parsing():
    """Test the _parse_financial_value method with various formats."""
    service = PDFExtractionService()

    test_cases = [
        ("523,659,586", 523659586.0),
        ("1,234,567", 1234567.0),
        ("(1,234)", -1234.0),
        ("-1234", -1234.0),
        ("△1,234", -1234.0),
        ("▲1,234", -1234.0),
        ("-", 0.0),
        ("—", 0.0),
        ("", 0.0),
        ("₩1,234", 1234.0),
        ("$1,234", 1234.0),
        ("123\n456", 123456.0),  # Multi-line value
    ]

    print("\n" + "="*60)
    print("TEST: Value Parsing")
    print("="*60)

    passed = 0
    failed = 0

    for input_val, expected in test_cases:
        result = service._parse_financial_value(input_val)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status}: '{input_val}' -> {result} (expected: {expected})")

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_notes_row_detection():
    """Test the _is_notes_row method."""
    service = PDFExtractionService()

    test_cases = [
        # Should be detected as notes (True)
        ("삼성전자㈜", True),
        ("Samsung Electronics Co., Ltd", True),
        ("(*1) 주석 참조", True),
        ("관계기업 투자", True),
        ("종속기업 지분", True),
        ("구 분", True),
        ("과 목", True),

        # Should NOT be detected as notes (False)
        ("유동자산", False),
        ("자산총계", False),
        ("매출액", False),
        ("영업이익", False),
        ("현금및현금성자산", False),
    ]

    print("\n" + "="*60)
    print("TEST: Notes Row Detection")
    print("="*60)

    passed = 0
    failed = 0

    for input_val, expected in test_cases:
        result = service._is_notes_row(input_val)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status}: '{input_val}' -> {result} (expected: {expected})")

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_aggregate_row_detection():
    """Test the _is_aggregate_row method."""
    service = PDFExtractionService()

    test_cases = [
        # Should be detected as aggregate (True)
        ("자산총계", True),
        ("부채총계", True),
        ("자본총계", True),
        ("유동자산", True),
        ("비유동자산", True),
        ("매출액", True),
        ("영업이익", True),
        ("당기순이익", True),

        # Should NOT be detected as aggregate (False)
        ("현금및현금성자산", False),
        ("재고자산", False),
        ("단기차입금", False),
    ]

    print("\n" + "="*60)
    print("TEST: Aggregate Row Detection")
    print("="*60)

    passed = 0
    failed = 0

    for input_val, expected in test_cases:
        result = service._is_aggregate_row(input_val)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status}: '{input_val}' -> {result} (expected: {expected})")

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_pdf_extraction(pdf_path: str):
    """Test full PDF extraction pipeline."""
    print("\n" + "="*60)
    print(f"TEST: PDF Extraction - {pdf_path}")
    print("="*60)

    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return False

    service = PDFExtractionService()

    try:
        # Extract raw data
        print("\n1. Extracting tables from PDF...")
        raw_data = service.extract_from_pdf(pdf_path)

        print(f"\nRaw extraction results:")
        print(f"  - Balance sheet items: {len(raw_data.get('balance_sheet', {}))}")
        print(f"  - Income statement items: {len(raw_data.get('income_statement', {}))}")
        print(f"  - Cash flow items: {len(raw_data.get('cash_flow_statement', {}))}")

        # Show sample raw data
        if raw_data.get('balance_sheet'):
            print(f"\n  Sample balance sheet items:")
            for key, value in list(raw_data['balance_sheet'].items())[:5]:
                print(f"    {key}: {value:,.0f}")

        if raw_data.get('income_statement'):
            print(f"\n  Sample income statement items:")
            for key, value in list(raw_data['income_statement'].items())[:5]:
                print(f"    {key}: {value:,.0f}")

        # Normalize to K-IFRS
        print("\n2. Normalizing to K-IFRS taxonomy...")
        normalized = service.normalize_to_kifrs(raw_data)

        print(f"\nNormalized results:")
        print(f"  - Balance sheet fields: {list(normalized.get('balance_sheet', {}).keys())}")
        print(f"  - Income statement fields: {list(normalized.get('income_statement', {}).keys())}")

        # Show key normalized values
        bs = normalized.get('balance_sheet', {})
        is_data = normalized.get('income_statement', {})

        print(f"\n  Key balance sheet values:")
        for key in ['total_assets', 'total_liabilities', 'total_equity', 'current_assets', 'inventory']:
            if key in bs:
                print(f"    {key}: {bs[key]:,.0f}")

        print(f"\n  Key income statement values:")
        for key in ['revenue', 'operating_income', 'net_income', 'gross_profit']:
            if key in is_data:
                print(f"    {key}: {is_data[key]:,.0f}")

        # Validation
        print("\n3. Validation...")
        required_bs = ['total_assets', 'total_liabilities', 'total_equity']
        required_is = ['revenue', 'operating_income', 'net_income']

        bs_valid = all(key in bs and bs[key] > 0 for key in required_bs)
        is_valid = all(key in is_data and is_data[key] != 0 for key in required_is)

        if bs_valid:
            print("  ✅ Balance sheet: All required fields present with values")
        else:
            missing = [k for k in required_bs if k not in bs or bs.get(k, 0) == 0]
            print(f"  ❌ Balance sheet: Missing or zero fields: {missing}")

        if is_valid:
            print("  ✅ Income statement: All required fields present with values")
        else:
            missing = [k for k in required_is if k not in is_data or is_data.get(k) == 0]
            print(f"  ❌ Income statement: Missing or zero fields: {missing}")

        # Check accounting equation
        if bs_valid:
            total_assets = bs.get('total_assets', 0)
            total_liabilities = bs.get('total_liabilities', 0)
            total_equity = bs.get('total_equity', 0)
            equation_check = abs(total_assets - (total_liabilities + total_equity))

            if equation_check < 1000:  # Allow small rounding differences
                print(f"  ✅ Accounting equation: Assets ({total_assets:,.0f}) = Liabilities ({total_liabilities:,.0f}) + Equity ({total_equity:,.0f})")
            else:
                print(f"  ⚠️ Accounting equation mismatch: {total_assets:,.0f} ≠ {total_liabilities:,.0f} + {total_equity:,.0f} (diff: {equation_check:,.0f})")

        return bs_valid and is_valid

    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_normalization_with_sample_data():
    """Test normalization using sample Samsung data."""
    print("\n" + "="*60)
    print("TEST: Normalization with Sample Data")
    print("="*60)

    # Sample data simulating extracted DART data (with note references)
    raw_data = {
        "balance_sheet": {
            "유동자산 (주3,26)": 229440881,
            "비유동자산": 294218705,
            "자산총계": 523659586,
            "유동부채": 87259259,
            "비유동부채": 22898833,
            "부채총계": 110158092,
            "자본총계": 413501494,
            "재고자산 (주5)": 50332392,
            "현금및현금성자산": 62847291,
        },
        "income_statement": {
            "매출액 (주27)": 239768567,
            "매출원가": 152649117,
            "매출총이익": 87119450,
            "판매비와관리비": 63592059,
            "영업이익": 23527391,
            "법인세비용차감전순이익": 28764182,
            "법인세비용": 3199122,
            "분기순이익": 25565060,
        },
        "cash_flow_statement": {}
    }

    service = PDFExtractionService()

    try:
        # Normalize
        print("\n1. Normalizing sample data...")
        normalized = service.normalize_to_kifrs(raw_data)

        bs = normalized.get('balance_sheet', {})
        is_data = normalized.get('income_statement', {})

        # Check balance sheet mappings
        print("\n2. Checking balance sheet normalization...")
        bs_expected = {
            "total_assets": 523659586,
            "total_liabilities": 110158092,
            "total_equity": 413501494,
            "current_assets": 229440881,
            "non_current_assets": 294218705,
            "current_liabilities": 87259259,
            "non_current_liabilities": 22898833,
            "inventory": 50332392,
            "cash_and_equivalents": 62847291,
        }

        bs_passed = 0
        bs_failed = 0
        for key, expected in bs_expected.items():
            actual = bs.get(key)
            if actual == expected:
                print(f"  ✅ {key}: {actual:,.0f}")
                bs_passed += 1
            else:
                print(f"  ❌ {key}: {actual} (expected: {expected})")
                bs_failed += 1

        # Check income statement mappings
        print("\n3. Checking income statement normalization...")
        is_expected = {
            "revenue": 239768567,
            "cost_of_revenue": 152649117,
            "gross_profit": 87119450,
            "operating_expenses": 63592059,
            "operating_income": 23527391,
            "income_before_tax": 28764182,
            "income_tax_expense": 3199122,
            "net_income": 25565060,
        }

        is_passed = 0
        is_failed = 0
        for key, expected in is_expected.items():
            actual = is_data.get(key)
            if actual == expected:
                print(f"  ✅ {key}: {actual:,.0f}")
                is_passed += 1
            else:
                print(f"  ❌ {key}: {actual} (expected: {expected})")
                is_failed += 1

        # Summary
        total_passed = bs_passed + is_passed
        total_failed = bs_failed + is_failed
        print(f"\nResults: {total_passed} passed, {total_failed} failed")

        # Check accounting equation
        print("\n4. Verifying accounting equation...")
        total_assets = bs.get('total_assets', 0)
        total_liabilities = bs.get('total_liabilities', 0)
        total_equity = bs.get('total_equity', 0)

        if total_assets == total_liabilities + total_equity:
            print(f"  ✅ Assets ({total_assets:,.0f}) = Liabilities ({total_liabilities:,.0f}) + Equity ({total_equity:,.0f})")
        else:
            diff = total_assets - (total_liabilities + total_equity)
            print(f"  ⚠️ Difference of {diff:,.0f}")

        # Calculate expected ratios for verification
        print("\n5. Sample ratio calculations (for verification)...")
        if total_equity > 0:
            net_income = is_data.get('net_income', 0)
            roe = (net_income / total_equity) * 100
            print(f"  ROE: {roe:.2f}%")

        current_assets = bs.get('current_assets', 0)
        current_liabilities = bs.get('current_liabilities', 0)
        if current_liabilities > 0:
            current_ratio = current_assets / current_liabilities
            print(f"  Current Ratio: {current_ratio:.4f}")

            inventory = bs.get('inventory', 0)
            quick_ratio = (current_assets - inventory) / current_liabilities
            print(f"  Quick Ratio: {quick_ratio:.4f}")

        if total_equity > 0:
            equity_multiplier = total_assets / total_equity
            print(f"  Equity Multiplier: {equity_multiplier:.4f}")

        return total_failed == 0

    except Exception as e:
        print(f"❌ Normalization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("DART PDF EXTRACTION TEST SUITE")
    print("="*60)

    results = []

    # Unit tests
    results.append(("Item Name Cleaning", test_item_name_cleaning()))
    results.append(("Value Parsing", test_value_parsing()))
    results.append(("Notes Row Detection", test_notes_row_detection()))
    results.append(("Aggregate Row Detection", test_aggregate_row_detection()))

    # Normalization test with sample data
    results.append(("Normalization with Sample Data", test_normalization_with_sample_data()))

    # PDF extraction test (if PDF path provided)
    if len(sys.argv) > 1 and sys.argv[1] == '--pdf':
        pdf_path = sys.argv[2] if len(sys.argv) > 2 else None
        if pdf_path:
            results.append(("PDF Extraction", test_pdf_extraction(pdf_path)))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("All tests passed! ✅")
    else:
        print("Some tests failed! ❌")
    print("="*60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
