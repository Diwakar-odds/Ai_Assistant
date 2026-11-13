# Install Optional Dependencies for AI Assistant
# This script resolves the warnings shown during desktop app startup.

echo "Installing Text-to-Speech (TTS)..."
pip install pyttsx3

echo "Installing Wake Word Detection..."
pip install pocketsphinx

echo "Installing Voice Activity Detection..."
pip install webrtcvad

echo "Installing Anthropic Claude Streaming..."
pip install anthropic

echo "Installing FastAPI for Learning Systems..."
pip install fastapi uvicorn

echo "All optional dependencies installed successfully!"
