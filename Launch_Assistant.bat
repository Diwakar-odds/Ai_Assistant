@echo off
title Pulsar AI Assistant Desktop
echo ====================================================
echo Starting Pulsar AI Assistant Windows Desktop App...
echo ====================================================
cd /d %~dp0
call venv\Scripts\activate.bat
python desktop\launchers\windows_app.py
pause
