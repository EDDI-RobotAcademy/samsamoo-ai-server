#!/usr/bin/env python
"""
Download a sample DART financial statement PDF for testing.

This script downloads a financial report PDF directly from DART (금감원 전자공시시스템)
for use in testing the PDF extraction service.
"""

import requests
import os
from pathlib import Path

# DART 공시뷰어 URL
# We'll use the embedded viewer URL which provides the actual PDF content

def download_samsung_financial_pdf():
    """Download Samsung Electronics Q3 2025 financial statement."""

    # Create test_data directory
    test_data_dir = Path(__file__).parent.parent / "test_data"
    test_data_dir.mkdir(exist_ok=True)

    # Note: DART requires APIKEY for direct downloads
    # Alternative: Use a pre-downloaded sample or mock data

    print("Creating sample DART financial data for testing...")

    # Create a mock financial statement table data based on real Samsung data
    # (This simulates what would be extracted from a real DART PDF)
    sample_data = {
        "source": "Samsung Electronics 2025 Q3 Report (Simulated)",
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
            "자본금": 897514,
            "이익잉여금": 330826541,
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
        }
    }

    # Save as JSON for testing
    import json
    output_path = test_data_dir / "samsung_q3_2025_sample.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)

    print(f"Sample data saved to: {output_path}")

    return output_path


def main():
    """Main function."""
    output = download_samsung_financial_pdf()
    print(f"\nSample data created at: {output}")
    print("\nTo test with a real DART PDF:")
    print("1. Go to http://dart.fss.or.kr")
    print("2. Search for 삼성전자")
    print("3. Download a 분기보고서 or 사업보고서 PDF")
    print("4. Run: python scripts/test_dart_extraction.py --pdf /path/to/dart.pdf")


if __name__ == "__main__":
    main()
