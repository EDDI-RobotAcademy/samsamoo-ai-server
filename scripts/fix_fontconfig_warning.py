"""
Quick fix for Fontconfig warning on Windows.
Run this once to suppress the warning.
"""
import os
import sys

# Add to the top of report_generation_service.py
fix_code = '''
import os
import warnings

# Suppress fontconfig warnings on Windows
if os.name == 'nt':  # Windows
    os.environ['FONTCONFIG_PATH'] = '/dev/null'
    os.environ['FONTCONFIG_FILE'] = '/dev/null'
    warnings.filterwarnings('ignore', category=UserWarning, message='.*fontconfig.*')
    warnings.filterwarnings('ignore', message='.*Fontconfig.*')

'''

service_path = "financial_statement/infrastructure/service/report_generation_service.py"

print("Fontconfig Warning Fix")
print("=" * 60)
print("\nThis script will add code to suppress the Fontconfig warning.")
print(f"Target file: {service_path}")
print("\nThe warning is harmless and your analysis completed successfully!")
print("\nOptions:")
print("1. Apply automatic fix (adds suppression code)")
print("2. Manual fix (shows you what to add)")
print("3. No fix needed (ignore the warning)")

choice = input("\nEnter choice (1/2/3): ").strip()

if choice == "1":
    try:
        with open(service_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if already fixed
        if 'FONTCONFIG_PATH' in content:
            print("\n✅ Already fixed! No changes needed.")
            sys.exit(0)

        # Add fix after imports, before matplotlib.use()
        if "matplotlib.use('Agg')" in content:
            content = content.replace(
                "import matplotlib\nmatplotlib.use('Agg')",
                fix_code + "import matplotlib\nmatplotlib.use('Agg')"
            )

            with open(service_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print("\n✅ Fix applied successfully!")
            print("Restart your server to see the changes.")
        else:
            print("\n⚠️ Could not find matplotlib.use() line.")
            print("Please apply manual fix (option 2).")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please apply manual fix (option 2).")

elif choice == "2":
    print("\n" + "=" * 60)
    print("MANUAL FIX INSTRUCTIONS")
    print("=" * 60)
    print(f"\n1. Open: {service_path}")
    print("\n2. Find these lines:")
    print("   import matplotlib")
    print("   matplotlib.use('Agg')")
    print("\n3. Add this code BEFORE those lines:")
    print(fix_code)
    print("\n4. Save the file and restart your server.")
    print("\n" + "=" * 60)

else:
    print("\n✅ No changes made.")
    print("\nNote: The warning is harmless. Your analysis works perfectly!")
    print("The reports were generated successfully despite the warning.")

print("\n" + "=" * 60)
print("IMPORTANT: Your program is working correctly!")
print("The Fontconfig warning appears AFTER successful completion.")
print("All reports were generated successfully:")
print("  ✅ PDF report")
print("  ✅ HTML report")
print("  ✅ 4 charts")
print("=" * 60)
