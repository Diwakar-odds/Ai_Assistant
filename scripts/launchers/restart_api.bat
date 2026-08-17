@echo off
echo Killing old server processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /PID %%a /F 2>nul
timeout /t 2 /nobreak >nul

echo Starting new server...
cd /d f:\bn\assitant
start /B python quickstart_api.py

timeout /t 10 /nobreak
echo.
echo Server should be running at http://127.0.0.1:8000
echo Dashboard at http://127.0.0.1:8000/
echo.
