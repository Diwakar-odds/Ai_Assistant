@echo off
title J.A.R.V.I.S. Environment Controller
echo.
echo [INIT] Checking Runtime Environment...

REM 1. Create .venv if it doesn't exist (One-time setup)
if not exist .venv (
    echo [SETUP] Creating isolated environment to fix dependency issues...
    python -m venv .venv
)

REM 2. Install critical missing libraries into the isolated environment (Fast Check)
echo [UPDATE] Verifying Neural Pathways (Dependencies)...
.venv\Scripts\python -m pip install pywinauto pyttsx3 psutil requests opencv-python pypiwin32 comtypes flask flask-socketio

REM 3. Launch the application using the STABLE environment
echo.
echo [LAUNCH] Starting J.A.R.V.I.S. Backend...
echo.
echo [INFO] Once started, open your browser to:
echo        http://localhost:5000
echo.
echo ---------------------------------------------------
cd /d "%~dp0.."
echo [INFO] Working Directory: %CD%
.venv\Scripts\python main.py --interface web
echo ---------------------------------------------------
echo [STOP] System halted.
pause
