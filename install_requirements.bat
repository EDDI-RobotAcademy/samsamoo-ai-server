@echo off
REM Installation script for SamSamOO-AI-Server financial requirements
REM Prerequisites: GTK3 Runtime must be installed first

echo ========================================
echo Installing Financial Requirements
echo ========================================
echo.

REM Navigate to project directory
cd /d "%~dp0"

echo Step 1: Checking Python version...
python --version
echo.

echo Step 2: Upgrading pip...
python -m pip install --upgrade pip
echo.

echo Step 3: Installing financial requirements...
pip install -r requirements_financial.txt
echo.

echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo If you encountered errors with WeasyPrint:
echo 1. Ensure GTK3 Runtime is installed
echo 2. Verify GTK bin directory is in your PATH
echo 3. Restart your terminal after PATH changes
echo.
pause
