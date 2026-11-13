@echo off
title Pulsar AI Assistant Launcher
cd /d "%~dp0"

echo ========================================================
echo   Starting Pulsar AI Assistant (Native Windows App)
echo ========================================================

REM Activate Python Virtual Environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Verify frontend dist exists, build if missing
if not exist "frontend\web-app\dist\index.html" (
    echo [INFO] Building React UI for first time launch...
    cd frontend\web-app
    call npm run build
    cd ..\..
)

echo [INFO] Launching Desktop Window and Ambient Mascot...
start "" "%CD%\venv\Scripts\pythonw.exe" "%CD%\desktop\app_launcher.py"

exit
