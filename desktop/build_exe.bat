@echo off
cd /d "%~dp0\.."
echo ============================================
echo  Building YourDaddy Assistant (.exe)
echo ============================================

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo.
echo [1/2] Verifying Dependencies...
python -m pip install pyinstaller pywebview

echo.
echo [2/2] Running PyInstaller...
python -m PyInstaller --name="YourDaddy_Assistant" ^
  --windowed ^
  --icon="%CD%\assets\icon.ico" ^
  --add-data="%CD%\backend;backend" ^
  --add-data="%CD%\core_ai;core_ai" ^
  --add-data="%CD%\shared;shared" ^
  --add-data="%CD%\frontend\web-app\dist;frontend\web-app\dist" ^
  --hidden-import="flask" ^
  --hidden-import="flask_socketio" ^
  --hidden-import="pywinauto" ^
  --hidden-import="speech_recognition" ^
  --hidden-import="sqlite3" ^
  --hidden-import="webview" ^
  --clean ^
  --noconfirm ^
  --distpath="%CD%\dist_package" ^
  --workpath="%CD%\desktop\build" ^
  --specpath="%CD%\desktop\pyinstaller_specs" ^
  "%CD%\desktop\app_launcher.py"

echo.
echo ============================================
echo  BUILD COMPLETE! 
echo  Executable is in the dist_package folder.
echo ============================================
