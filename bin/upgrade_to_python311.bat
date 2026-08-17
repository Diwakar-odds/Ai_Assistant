@echo off
REM Python 3.11 Upgrade Script for AI Assistant
REM ============================================

echo ========================================
echo Python 3.11 Upgrade Script
echo ========================================
echo.

REM Step 1: Check if Python 3.11 is installed
echo [1/5] Checking Python 3.11 installation...
py -3.11 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python 3.11 is not installed!
    echo.
    echo Please install Python 3.11 manually:
    echo 1. Download from: https://www.python.org/downloads/release/python-3119/
    echo 2. Run the installer
    echo 3. Check "Add Python to PATH"
    echo 4. Run this script again
    echo.
    echo Or use winget:
    echo    winget install Python.Python.3.11
    pause
    exit /b 1
)

py -3.11 --version
echo Python 3.11 is installed!
echo.

REM Step 2: Backup current virtual environment
echo [2/5] Backing up current environment...
if exist .venv_backup (
    rmdir /s /q .venv_backup
)
if exist .venv (
    move .venv .venv_backup
    echo Backed up .venv to .venv_backup
) else (
    echo No existing .venv found
)
echo.

REM Step 3: Create new virtual environment with Python 3.11
echo [3/5] Creating new virtual environment with Python 3.11...
py -3.11 -m venv .venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment!
    pause
    exit /b 1
)
echo Virtual environment created successfully!
echo.

REM Step 4: Activate and upgrade pip
echo [4/5] Activating environment and upgrading pip...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
echo.

REM Step 5: Install dependencies
echo [5/5] Installing project dependencies...
echo This may take several minutes...
echo.
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo WARNING: Some packages failed to install!
    echo Check the error messages above.
    echo You may need to install some packages manually.
    echo.
) else (
    echo.
    echo ========================================
    echo SUCCESS! Python 3.11 upgrade complete!
    echo ========================================
    echo.
)

REM Verify installation
echo Verification:
python --version
echo.

echo Next steps:
echo 1. Test your application: python main.py
echo 2. If everything works, delete backup: rmdir /s /q .venv_backup
echo 3. If issues occur, restore backup: move .venv_backup .venv
echo.
pause
