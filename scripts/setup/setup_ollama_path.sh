#!/bin/bash
# Ollama PATH Setup Script for Windows Git Bash
# This script adds Ollama to your PATH permanently

OLLAMA_PATH="/c/Users/hp/AppData/Local/Programs/Ollama"

# Check if Ollama exists
if [ ! -d "$OLLAMA_PATH" ]; then
    echo "❌ Ollama not found at: $OLLAMA_PATH"
    echo "Please install Ollama from https://ollama.ai"
    exit 1
fi

# Check if already in PATH
if [[ ":$PATH:" == *":$OLLAMA_PATH:"* ]]; then
    echo "✅ Ollama is already in PATH"
    ollama --version
    exit 0
fi

# Add to current session
export PATH="$OLLAMA_PATH:$PATH"
echo "✅ Added Ollama to PATH for current session"
echo "Ollama path: $OLLAMA_PATH"

# Verify
ollama --version

echo ""
echo "To make this permanent, add this line to your ~/.bashrc:"
echo "export PATH=\"$OLLAMA_PATH:\$PATH\""
echo ""
echo "Or run: bash setup_ollama_path.sh to set it up"
