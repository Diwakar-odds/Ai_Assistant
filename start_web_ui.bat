@echo off
echo ========================================
echo   YourDaddy Assistant - Modern Web UI
echo ========================================
echo.
echo Starting Flask backend server...
echo.

cd /d %~dp0
python modern_web_backend.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to start the backend server!
    echo Please make sure Python and required dependencies are installed.
    echo.
    pause
)