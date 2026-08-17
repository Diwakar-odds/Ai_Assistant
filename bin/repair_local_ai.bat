@echo off
echoString
echo ==========================================
echo  REPAIRING LOCAL AI INSTALLATION
echo ==========================================

echo.
echo 1. Cleaning up broken installation...
.venv\Scripts\pip uninstall -y llama-cpp-python

echo.
echo 2. Installing compatible pre-built version (0.2.90)...
echo    This bypasses compilation and uses a pre-made Windows wheel.
.venv\Scripts\pip install llama-cpp-python==0.2.90 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu --no-cache-dir

echo.
echo 3. Verifying installation...
.venv\Scripts\python test_local_ai.py

echo.
echo ==========================================
echo If you still see [WinError 1114], you may need to install 
echo the "Visual C++ Redistributable" from Microsoft.
echo ==========================================
pause
