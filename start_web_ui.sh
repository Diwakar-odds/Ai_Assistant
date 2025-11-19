#!/bin/bash

echo "========================================"
echo "  YourDaddy Assistant - Modern Web UI  "
echo "========================================"
echo ""
echo "Starting Flask backend server..."
echo ""

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

# Check if Python is available
if ! command -v python &> /dev/null; then
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        echo "ERROR: Python is not installed or not in PATH"
        exit 1
    fi
else
    PYTHON_CMD="python"
fi

# Start the backend
$PYTHON_CMD modern_web_backend.py

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to start the backend server!"
    echo "Please make sure Python and required dependencies are installed."
    echo ""
    read -p "Press any key to continue..."
fi