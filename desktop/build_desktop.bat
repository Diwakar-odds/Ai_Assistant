@echo off
cd /d "%~dp0"
echo ============================================
echo  Building YourDaddy Assistant Desktop App
echo ============================================
call .venv\Scripts\activate.bat

echo.
echo [1/3] Building Main App (YourDaddy_Assistant)...
pyinstaller --name="YourDaddy_Assistant" ^
  --windowed ^
  --icon="assets\icon.ico" ^
  --add-data="config;config" ^
  --add-data="data;data" ^
  --add-data="src\project\dist;web_assets" ^
  --paths="src\ai_assistant" ^
  --paths="src\ai_assistant\modules" ^
  --hidden-import="ai_assistant.multimodal" ^
  --hidden-import="ai_assistant.modules.conversational_ai" ^
  --hidden-import="ai_assistant.multilingual" ^
  --hidden-import="ai_assistant.modules.advanced_chat_system" ^
  --hidden-import="ai_assistant.modules.llm_provider" ^
  --hidden-import="webview" ^
  --hidden-import="flask" ^
  --hidden-import="flask_socketio" ^
  --hidden-import="engineio.async_drivers.threading" ^
  --exclude-module="tensorflow" ^
  --exclude-module="torch" ^
  --exclude-module="torchvision" ^
  --exclude-module="torchaudio" ^
  --exclude-module="numba" ^
  --exclude-module="llvmlite" ^
  --exclude-module="scipy" ^
  --exclude-module="sklearn" ^
  --exclude-module="scikit-learn" ^
  --exclude-module="cv2" ^
  --exclude-module="opencv-python" ^
  --exclude-module="onnxruntime" ^
  --exclude-module="pvporcupine" ^
  --exclude-module="matplotlib" ^
  --onedir ^
  --noconfirm ^
  --clean ^
  src\ai_assistant\apps\modern_desktop_app.py

echo.
echo [2/3] Building Uninstaller (Uninstall_YourDaddy.exe)...
pyinstaller --name="Uninstall_YourDaddy" ^
  --windowed ^
  --onefile ^
  --icon="assets\icon.ico" ^
  --noconfirm ^
  --clean ^
  src\ai_assistant\apps\uninstaller.py

echo.
echo [3/3] Building Setup Wizard (Setup_YourDaddy.exe)...
pyinstaller --name="Setup_YourDaddy" ^
  --windowed ^
  --onefile ^
  --icon="assets\icon.ico" ^
  --add-data="dist\YourDaddy_Assistant;YourDaddy_Assistant" ^
  --add-data="dist\Uninstall_YourDaddy.exe;." ^
  --add-data="assets\icon.ico;." ^
  --add-data="config;config" ^
  --noconfirm ^
  --clean ^
  src\ai_assistant\apps\installer.py

echo.
echo ============================================
echo  Build Complete!
echo ============================================
echo.
echo Output files in 'dist' folder:
echo   - Setup_YourDaddy.exe    (Give this to users)
echo   - YourDaddy_Assistant.exe (Main app, bundled inside Setup)
echo   - Uninstall_YourDaddy.exe (Uninstaller, bundled inside Setup)
echo.
