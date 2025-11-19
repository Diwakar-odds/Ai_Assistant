@echo off
echo ============================================================
echo Starting YourDaddy Assistant Web UI
echo ============================================================
echo.

REM Start backend server in a new window
start "Backend Server" cmd /k "cd /d %~dp0 && .venv\Scripts\python.exe modern_web_backend.py"

REM Wait a few seconds for backend to initialize
timeout /t 5 /nobreak >nul

REM Start frontend dev server in a new window
start "Frontend Server" cmd /k "cd /d %~dp0\project && npm run dev"

echo.
echo ============================================================
echo Both servers are starting in separate windows:
echo   - Backend:  http://localhost:5000
echo   - Frontend: http://localhost:5173
echo ============================================================
echo.
echo Press any key to exit this window (servers will keep running)
pause >nul
