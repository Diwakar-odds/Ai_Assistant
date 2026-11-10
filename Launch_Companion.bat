@echo off
title Pulsar Floating Companion
cd /d "%~dp0"
if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" "desktop\companion_app.py"
) else (
    start "" python "desktop\companion_app.py"
)
exit
