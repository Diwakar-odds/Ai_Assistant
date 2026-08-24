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
if exist ".venv\Scripts\activate.bat" (
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

echo [1/2] Starting Python Backend Server...
:: Start the backend in a new command window
start "Pulsar Backend" cmd /k "cd backend && python modern_web_backend.py"

echo [2/2] Starting React Frontend...
cd frontend\web-app
:: Ensure dependencies are installed just in case
if not exist "node_modules\" (
    echo Installing React dependencies...
    call npm install
)

:: Start the frontend in a new command window
start "Pulsar Frontend" cmd /k "npm run dev"

echo.
echo ===================================================
echo     SUCCESS! The Assistant is starting up.
echo ===================================================
echo Backend API will be available at: http://localhost:5000
echo Frontend UI will be available at: http://localhost:5173
echo.
echo Two new terminal windows have opened. Keep them running!
pause
