@echo off
REM Quick start for React mobile development
REM Starts dev server accessible on network

echo ============================================================
echo   Starting YourDaddy AI React App (Mobile-Ready)
echo ============================================================
echo.

chcp 65001 > nul 2>&1

cd project

echo Installing dependencies (if needed)...
call npm install

echo.
echo Starting development server...
echo.
echo The app will be accessible on your network.
echo You can access it from your phone using your computer's IP.
echo.

call npm run dev

pause
