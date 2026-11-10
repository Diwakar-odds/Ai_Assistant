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

echo [1/3] Starting Python Backend Server...
:: Start the backend in a new command window
start "Pulsar Backend" cmd /k "cd backend && python modern_web_backend.py"

echo [2/3] Starting React Frontend...
cd frontend\web-app
:: Ensure dependencies are installed just in case
if not exist "node_modules\" (
    echo Installing React dependencies...
    call npm install
)

:: Start the frontend in a new command window
start "Pulsar Frontend" cmd /k "npm run dev"

cd /d "%~dp0"
echo [3/3] Launching Floating Desktop Mascot Robot...
if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" "desktop\companion_app.py"
) else (
    start "" python "desktop\companion_app.py"
)

echo.
echo ===================================================
echo     SUCCESS! Pulsar Assistant is Running.
echo ===================================================
echo - Web Dashboard: http://localhost:5173
echo - Floating Robot: Active on your desktop screen!
echo.
pause
