#!/bin/bash

# AI Assistant App Integration Startup Script
# This script starts the secure app integration system

echo "🤖 AI Assistant - App Integration System"
echo "========================================"

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python -m venv venv
    
    # Activate virtual environment
    if [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate  # Windows
    else
        source venv/bin/activate      # Linux/Mac
    fi
    
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
else
    # Activate existing virtual environment
    if [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate  # Windows
    elif [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate  # Windows
    elif [ -f "venv/bin/activate" ]; then
        source venv/bin/activate      # Linux/Mac
    else
        source .venv/bin/activate     # Linux/Mac
    fi
fi

# Check if configuration exists
if [ ! -f "config/app_integration.env" ]; then
    echo "⚙️  Setting up configuration..."
    
    if [ ! -f "config/app_integration.env.example" ]; then
        echo "❌ Configuration template not found. Please ensure all files are present."
        exit 1
    fi
    
    # Copy example configuration
    cp config/app_integration.env.example config/app_integration.env
    
    echo ""
    echo "🔐 IMPORTANT SECURITY SETUP"
    echo "=========================="
    echo "Please edit config/app_integration.env and set:"
    echo "1. ADMIN_PASSWORD=your-secure-password"
    echo "2. APP_SECRET_KEY=your-secret-key"
    echo ""
    read -p "Press Enter after you've updated the configuration..."
fi

# Load environment variables
if [ -f "config/app_integration.env" ]; then
    export $(cat config/app_integration.env | grep -v '#' | xargs)
fi

# Set default values if not provided
export INTEGRATION_API_PORT=${INTEGRATION_API_PORT:-5001}
export ADMIN_PASSWORD=${ADMIN_PASSWORD:-changeme123}

if [ "$ADMIN_PASSWORD" == "changeme123" ]; then
    echo "⚠️  WARNING: Using default password. Please change ADMIN_PASSWORD in config/app_integration.env"
fi

# Start the integration API server
echo ""
echo "🚀 Starting App Integration API on port $INTEGRATION_API_PORT..."
echo "📱 Web interface will be available at: http://localhost:$INTEGRATION_API_PORT"
echo "🔧 CLI tool available at: python -m ai_assistant.cli.app_manager"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python -m ai_assistant.services.app_integration_api