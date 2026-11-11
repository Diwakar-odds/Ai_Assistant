@echo off
cd /d "%~dp0\.."
echo ========================================================
echo   Building Pulsar AI Assistant Windows App & Installer
echo ========================================================

REM 1. Build React frontend dist
echo.
echo [1/4] Building React Frontend with Vite...
cd frontend\web-app
call npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build failed!
    exit /b 1
)
cd ..\..

REM 2. Activate virtual environment
echo.
echo [2/4] Activating Python Environment...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM 3. Compile Main App & Uninstaller
echo.
echo [3/4] Compiling Pulsar_AI_Assistant and Uninstall_Pulsar...
python -m PyInstaller --clean --noconfirm ^
  --distpath="%CD%\dist_package" ^
  --workpath="%CD%\desktop\build" ^
  "%CD%\desktop\pyinstaller_specs\Pulsar_Assistant.spec"
if errorlevel 1 (
    echo [ERROR] Main app PyInstaller build failed!
    exit /b 1
)

python -m PyInstaller --clean --noconfirm ^
  --distpath="%CD%\dist_package" ^
  --workpath="%CD%\desktop\build" ^
  "%CD%\desktop\pyinstaller_specs\Uninstall_Pulsar.spec"
if errorlevel 1 (
    echo [ERROR] Uninstaller PyInstaller build failed!
    exit /b 1
)

REM 4. Compile Git-style Setup Wizard wrapping main app + uninstaller
echo.
echo [4/4] Compiling Setup_Pulsar.exe Installer Wizard...
python -m PyInstaller --clean --noconfirm ^
  --distpath="%CD%\dist_package" ^
  --workpath="%CD%\desktop\build" ^
  "%CD%\desktop\pyinstaller_specs\Setup_Pulsar.spec"
if errorlevel 1 (
    echo [ERROR] Setup wizard PyInstaller build failed!
    exit /b 1
)

echo.
echo ========================================================
echo  BUILD COMPLETE!
echo  - Installer Wizard : dist_package\Setup_Pulsar.exe
echo  - Uninstaller      : dist_package\Uninstall_Pulsar.exe
echo  - Portable Folder  : dist_package\Pulsar_AI_Assistant\
echo ========================================================
