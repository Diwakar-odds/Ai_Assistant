@echo off
REM Build Windows App and Package for Distribution
echo ================================================
echo Building AI Assistant Windows App
echo ================================================
echo.

REM Step 1: Install all dependencies
echo [1/4] Installing dependencies...
pip install pyinstaller pywebview pythonnet pillow flask flask-socketio flask-cors psutil requests beautifulsoup4

REM Step 2: Build the executable
echo.
echo [2/4] Building executable with PyInstaller...
pyinstaller --clean --noconfirm ^
    --name "AI-Assistant" ^
    --onedir ^
    --windowed ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "config;config" ^
    --hidden-import "ai_assistant" ^
    --hidden-import "flask" ^
    --hidden-import "flask_socketio" ^
    --hidden-import "webview" ^
    windows_app.py

REM Step 3: Create installer folder
echo.
echo [3/4] Creating distribution package...
if exist "dist\AI-Assistant-Installer" rmdir /s /q "dist\AI-Assistant-Installer"
mkdir "dist\AI-Assistant-Installer"
xcopy /E /I /Y "dist\AI-Assistant" "dist\AI-Assistant-Installer\AI-Assistant"

REM Copy README and instructions
copy "WINDOWS_APP_README.md" "dist\AI-Assistant-Installer\README.txt"

REM Create a simple run script
echo @echo off > "dist\AI-Assistant-Installer\Run-AI-Assistant.bat"
echo start AI-Assistant\AI-Assistant.exe >> "dist\AI-Assistant-Installer\Run-AI-Assistant.bat"

REM Step 4: Create ZIP file
echo.
echo [4/4] Creating ZIP file for distribution...
powershell Compress-Archive -Path "dist\AI-Assistant-Installer\*" -DestinationPath "dist\AI-Assistant-Windows.zip" -Force

echo.
echo ================================================
echo ✓ Build Complete!
echo ================================================
echo.
echo Files created:
echo   - dist\AI-Assistant-Windows.zip (Ready for website download)
echo   - dist\AI-Assistant-Installer\ (Uncompressed files)
echo.
echo Next steps:
echo 1. Upload AI-Assistant-Windows.zip to your website
echo 2. Add download link on your website
echo 3. Users download, extract, and run Run-AI-Assistant.bat
echo.
pause
