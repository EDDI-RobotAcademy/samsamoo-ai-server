"""
Test script to verify PDF generation capabilities.
Run this to confirm your installation is working correctly.
"""

import sys
import os

def test_weasyprint():
    """Test WeasyPrint (requires GTK+)"""
    print("Testing WeasyPrint...")
    try:
        from weasyprint import HTML
        html_content = "<h1>Test PDF</h1><p>WeasyPrint is working!</p>"
        output_path = "test_weasyprint.pdf"
        HTML(string=html_content).write_pdf(output_path)
        print(f"✅ WeasyPrint working! PDF created: {output_path}")
        return True
    except ImportError as e:
        print(f"❌ WeasyPrint not installed: {e}")
        return False
    except OSError as e:
        print(f"❌ GTK+ libraries missing: {e}")
        print("   Install GTK3 Runtime to use WeasyPrint")
        return False
    except Exception as e:
        print(f"❌ WeasyPrint error: {e}")
        return False

def test_xhtml2pdf():
    """Test xhtml2pdf (Windows-friendly alternative)"""
    print("\nTesting xhtml2pdf...")
    try:
        from xhtml2pdf import pisa
        html_content = "<h1>Test PDF</h1><p>xhtml2pdf is working!</p>"
        output_path = "test_xhtml2pdf.pdf"

        with open(output_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)

        if pisa_status.err:
            print(f"❌ xhtml2pdf had {pisa_status.err} errors")
            return False

        print(f"✅ xhtml2pdf working! PDF created: {output_path}")
        return True
    except ImportError as e:
        print(f"❌ xhtml2pdf not installed: {e}")
        return False
    except Exception as e:
        print(f"❌ xhtml2pdf error: {e}")
        return False

def test_matplotlib():
    """Test matplotlib for chart generation"""
    print("\nTesting matplotlib...")
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        plt.figure(figsize=(8, 6))
        plt.plot([1, 2, 3, 4], [1, 4, 2, 3])
        plt.title("Test Chart")
        output_path = "test_chart.png"
        plt.savefig(output_path)
        plt.close()

        print(f"✅ matplotlib working! Chart created: {output_path}")
        return True
    except ImportError as e:
        print(f"❌ matplotlib not installed: {e}")
        return False
    except Exception as e:
        print(f"❌ matplotlib error: {e}")
        return False

def main():
    print("=" * 60)
    print("PDF Generation Capability Test")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    print("=" * 60)

    results = {
        "WeasyPrint": test_weasyprint(),
        "xhtml2pdf": test_xhtml2pdf(),
        "matplotlib": test_matplotlib()
    }

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    for library, success in results.items():
        status = "✅ Working" if success else "❌ Not Working"
        print(f"{library:15} {status}")

    print("\n" + "=" * 60)
    print("Recommendations:")
    print("=" * 60)

    if results["WeasyPrint"]:
        print("✅ Use the original report_generation_service.py")
    elif results["xhtml2pdf"]:
        print("✅ Use report_generation_service_xhtml2pdf.py")
        print("   Update your imports to use this alternative implementation")
    else:
        print("❌ No PDF library is working")
        print("   Install requirements: pip install -r requirements_financial_windows.txt")

    if not results["matplotlib"]:
        print("⚠️  matplotlib not working - chart generation will fail")
        print("   Install: pip install matplotlib seaborn")

if __name__ == "__main__":
    main()
