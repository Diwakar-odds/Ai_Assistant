@echo off
TITLE Pulsar AI Assistant Launcher
color 0A

echo ===================================================
echo     Starting Pulsar AI Assistant
echo ===================================================
echo.

:: Change to the directory of this script
cd /d "%~dp0"

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: Check if node is installed
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed. Please install Node.js to run the frontend.
    pause
    exit /b
)

:: Check if python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)

echo [1/1] Starting Pulsar AI Assistant Desktop App (Paradigm B: Native Host + Headless Core on Port 5000)...
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe web.py --open %*
) else (
    python web.py --open %*
)
pause
