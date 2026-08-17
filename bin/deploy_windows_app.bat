@echo off
REM Deployment script for AI Assistant Windows App
REM This script builds the app and prepares it for website download
REM Non-interactive version

echo ================================================
echo AI Assistant - Windows App Deployment
echo ================================================
echo.

REM Step 1: Build the Windows App
echo Building Windows App...
call build_windows_app.bat
if errorlevel 1 (
    echo ERROR: Build failed.
    exit /b 1
)

REM Step 2: Create Zip Archive
echo.
echo Creating Zip Archive...
if exist "dist\AIAssistant" (
    powershell -Command "Compress-Archive -Path 'dist\AIAssistant' -DestinationPath 'AIAssistant.zip' -Force"
) else (
    echo ERROR: dist\AIAssistant folder not found.
    exit /b 1
)

REM Step 3: Move to Public Folder (if it exists) - otherwise keep in root
echo.
if exist "project\public" (
    echo Moving to Website Public Folder...
    move /Y "AIAssistant.zip" "project\public\"
    echo.
    echo ================================================
    echo Deployment Successful!
    echo ================================================
    echo File located at: project\public\AIAssistant.zip
) else (
    echo.
    echo ================================================
    echo Deployment Successful!
    echo ================================================
    echo File located at: AIAssistant.zip
)
