@echo off
echo ================================================
echo    YourDaddy Assistant - Professional Launcher
echo ================================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Navigate to project directory
cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo 🔧 Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Launch the assistant
echo 🚀 Starting YourDaddy Assistant...
python launch_assistant.py

REM Keep window open on error
if %errorlevel% neq 0 (
    echo.
    echo ❌ Assistant failed to start - check errors above
    pause
)