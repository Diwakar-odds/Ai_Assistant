@echo off
REM Build script for AI Assistant Windows Desktop App
REM This script builds the Windows executable using PyInstaller
REM Non-interactive version
REM Using the project's virtual environment

echo ================================================
echo AI Assistant - Windows App Build Script
echo ================================================
echo.

REM Set the path to the virtual environment's Python
set VENV_PYTHON=..\.venv\Scripts\python.exe
set VENV_PIPELINER=..\.venv\Scripts\pyinstaller.exe

REM Check if the virtual environment exists
if not exist "%VENV_PYTHON%" (
    echo ERROR: Virtual environment not found at %VENV_PYTHON%
    echo Please run setup or create a virtual environment first.
    exit /b 1
)

REM Check if Python is installed in the virtual environment
"%VENV_PYTHON%" --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed in the virtual environment
    exit /b 1
)

echo Step 1: Installing required dependencies...
"%VENV_PYTHON%" -m pip install --upgrade pip
"%VENV_PYTHON%" -m pip install pywebview pyinstaller pillow

echo.
echo Step 2: Building Windows executable...
"%VENV_PIPELINER%" ..\YourDaddy_Assistant.spec --clean --noconfirm

echo.
if exist "dist\AIAssistant\AIAssistant.exe" (
    echo ================================================
    echo ✓ Build completed successfully!
    echo ================================================
    echo.
    echo Your Windows app is located at:
    echo   dist\AIAssistant\AIAssistant.exe
    echo.
) else (
    echo ================================================
    echo ✗ Build failed!
    echo ================================================
    echo Please check the error messages above.
    exit /b 1
)