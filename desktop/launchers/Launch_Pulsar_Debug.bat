@echo off
title Pulsar AI Assistant - Debug Mode
cd /d "%~dp0"

echo ========================================================
echo   Starting Pulsar AI Assistant (Debug Console Mode)
echo ========================================================

REM Activate Python Virtual Environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Verify frontend dist exists, build if missing
if not exist "frontend\web-app\dist\index.html" (
    echo [INFO] Building React UI...
    cd frontend\web-app
    call npm run build
    cd ..\..
)

echo [INFO] Starting Desktop App with live logging...
python "%CD%\desktop\app_launcher.py"

pause
