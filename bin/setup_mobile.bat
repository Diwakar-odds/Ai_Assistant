@echo off
REM Mobile Setup for Windows - No interaction needed
REM This batch file sets up mobile access automatically

echo ============================================================
echo   Mobile Setup for YourDaddy AI Assistant
echo ============================================================
echo.

REM Set UTF-8 encoding
chcp 65001 > nul 2>&1

echo Step 1: Installing mobile dependencies...
python -m pip install -q -r requirements_mobile.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies
    echo Please run: pip install -r requirements_mobile.txt
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

echo Step 2: Generating PWA icons...
python generate_pwa_icons.py
if %errorlevel% neq 0 (
    echo [WARNING] Icon generation failed - continuing anyway
)
echo.

echo Step 3: Checking configuration...
if exist "static\manifest.json" (
    echo [OK] PWA manifest found
) else (
    echo [WARNING] PWA manifest missing
)

if exist "static\service-worker.js" (
    echo [OK] Service worker found
) else (
    echo [WARNING] Service worker missing
)

if exist "templates\mobile_chat.html" (
    echo [OK] Mobile chat interface found
) else (
    echo [WARNING] Mobile chat interface missing
)
echo.

echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo Choose how to start:
echo   1. Local WiFi (fastest, most secure)
echo   2. Local WiFi with HTTPS (required for voice)
echo   3. Internet access via Ngrok
echo.
echo Or run manually:
echo   - Local:  python quick_mobile_start.py
echo   - HTTPS:  python mobile_server.py --https
echo   - Ngrok:  python mobile_server.py --ngrok
echo.

set /p choice="Enter choice (1-3) or press Enter to exit: "

if "%choice%"=="1" (
    echo.
    echo Starting local server...
    python quick_mobile_start.py
) else if "%choice%"=="2" (
    echo.
    echo Starting HTTPS server...
    python mobile_server.py --https
) else if "%choice%"=="3" (
    echo.
    echo Starting server with Ngrok...
    python mobile_server.py --ngrok
) else (
    echo.
    echo Setup complete! Run one of the commands above to start.
)

pause
