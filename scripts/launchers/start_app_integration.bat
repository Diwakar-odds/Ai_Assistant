@echo off
REM AI Assistant App Integration Startup Script (Windows)
REM This script starts the secure app integration system

echo 🤖 AI Assistant - App Integration System
echo ========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" if not exist ".venv" (
    echo ⚠️  Virtual environment not found. Creating one...
    python -m venv venv
    
    REM Activate virtual environment
    call venv\Scripts\activate.bat
    
    echo 📦 Installing dependencies...
    pip install -r requirements.txt
) else (
    REM Activate existing virtual environment
    if exist "venv\Scripts\activate.bat" (
        call venv\Scripts\activate.bat
    ) else (
        call .venv\Scripts\activate.bat
    )
)

REM Check if configuration exists
if not exist "config\app_integration.env" (
    echo ⚙️  Setting up configuration...
    
    if not exist "config\app_integration.env.example" (
        echo ❌ Configuration template not found. Please ensure all files are present.
        pause
        exit /b 1
    )
    
    REM Copy example configuration
    copy "config\app_integration.env.example" "config\app_integration.env"
    
    echo.
    echo 🔐 IMPORTANT SECURITY SETUP
    echo ==========================
    echo Please edit config\app_integration.env and set:
    echo 1. ADMIN_PASSWORD=your-secure-password
    echo 2. APP_SECRET_KEY=your-secret-key
    echo.
    pause
)

REM Set default environment variables
set INTEGRATION_API_PORT=5001
set ADMIN_PASSWORD=changeme123

REM Load environment variables from file
for /f "usebackq tokens=1,2 delims==" %%a in ("config\app_integration.env") do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" (
        set %%a=%%b
    )
)

if "%ADMIN_PASSWORD%"=="changeme123" (
    echo ⚠️  WARNING: Using default password. Please change ADMIN_PASSWORD in config\app_integration.env
)

REM Start the integration API server
echo.
echo 🚀 Starting App Integration API on port %INTEGRATION_API_PORT%...
echo 📱 Web interface will be available at: http://localhost:%INTEGRATION_API_PORT%
echo 🔧 CLI tool available at: python -m ai_assistant.cli.app_manager
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server
python -m ai_assistant.services.app_integration_api

pause