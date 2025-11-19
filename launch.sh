#!/bin/bash
echo "================================================"
echo "   YourDaddy Assistant - Professional Launcher"
echo "================================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python is not installed or not in PATH"
    echo "Please install Python 3.8+ from https://python.org"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# Navigate to project directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

# Launch the assistant
echo "🚀 Starting YourDaddy Assistant..."
$PYTHON_CMD launch_assistant.py

# Check exit status
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Assistant failed to start - check errors above"
    read -p "Press Enter to exit..."
fi