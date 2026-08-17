@echo off
setlocal enabledelayedexpansion

echo ================================================================
echo    YourDaddy AI Assistant - Secure Launcher (Windows)
echo ================================================================
echo 🔐 This launcher includes  authentication for security
echo 💡 Use --skip-auth to bypass  for development
echo ⚙️  Use --setup- to configure/change your 
echo ================================================================

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
if exist ".venv\Scripts\activate.bat" (
    echo 🔧 Activating virtual environment...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo 🔧 Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Parse command line arguments
set "MODE="
set "TARGET="

if "%~1"=="" (
    goto :show_menu
)

set "TARGET=%~1"
if not "%~2"=="" set "MODE=%~2"

goto :launch_target

:show_menu
echo.
echo Available launch options:
echo   1. app          - Launch main YourDaddy Assistant application
echo   2. backend      - Start unified backend server only
echo   3. web          - Start web UI (backend + frontend)
echo   4. test         - Run comprehensive tests
echo   5. setup        - Run setup and configuration
echo   6. setup-    - Setup or change  authentication
echo   7. debug        - Start in debug mode
echo.
set /p choice="Select option (1-7): "

if "%choice%"=="1" set "TARGET=app"
if "%choice%"=="2" set "TARGET=backend"
if "%choice%"=="3" set "TARGET=web"
if "%choice%"=="4" set "TARGET=test"
if "%choice%"=="5" set "TARGET=setup"
if "%choice%"=="6" set "TARGET=setup-"
if "%choice%"=="7" set "TARGET=debug"

if "%TARGET%"=="" (
    echo Invalid choice. Exiting...
    pause
    exit /b 1
)

:launch_target
echo.
echo 🚀 Launching: %TARGET%
echo ================================================================

if "%TARGET%"=="app" (
    echo 🔐 Starting YourDaddy Assistant (Desktop Mode)...
    python main.py --interface desktop
) else if "%TARGET%"=="backend" (
    echo 🔐 Starting YourDaddy Assistant (Backend Only)...
    python main.py --interface web --port 5000
) else if "%TARGET%"=="web" (
    echo 🔐 Starting YourDaddy Assistant (Web Interface)...
    python main.py --interface web --port 5000
    
    if exist "project\package.json" (
        echo Starting frontend server in separate window...
        start "Frontend Server" cmd /k "cd /d %~dp0\project && npm run dev"
        echo.
        echo ================================================================
        echo Both servers are starting:
        echo   - Backend:  http://localhost:5000
        echo   - Frontend: http://localhost:5173
        echo ================================================================
    ) else (
        echo Frontend project not found. Backend only running at http://localhost:5000
    )
) else if "%TARGET%"=="test" (
    echo 🧪 Running tests...
    python -m pytest tests/ -v
) else if "%TARGET%"=="setup" (
    echo ⚙️ Running setup...
    python scripts/setup/setup.py
) else if "%TARGET%"=="setup-" (
    echo 🔐  Management...
    python setup_.py
) else if "%TARGET%"=="debug" (
    echo 🐛 Starting in debug mode (authentication disabled)...
    python main.py --verbose --interface cli --skip-auth
) else (
    echo ❌ Unknown target: %TARGET%
    pause
    exit /b 1
)

REM Keep window open on error
if %errorlevel% neq 0 (
    echo.
    echo ❌ Error occurred (Exit code: %errorlevel%)
    echo Press any key to exit...
    pause >nul
)

endlocal