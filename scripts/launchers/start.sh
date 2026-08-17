#!/bin/bash

echo "================================================================"
echo "   YourDaddy AI Assistant - Secure Launcher (Linux/macOS)"
echo "================================================================"
echo "🔐 This launcher includes  authentication for security"
echo "💡 Use --skip-auth to bypass  for development"
echo "⚙️  Use --setup- to configure/change your "
echo "================================================================"

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
if [ -f ".venv/bin/activate" ]; then
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

# Parse command line arguments
TARGET="$1"
MODE="$2"

show_menu() {
    echo ""
    echo "Available launch options:"
    echo "  1. app          - Launch main YourDaddy Assistant application"
    echo "  2. backend      - Start unified backend server only"
    echo "  3. web          - Start web UI (backend + frontend)"
    echo "  4. test         - Run comprehensive tests"
    echo "  5. setup        - Run setup and configuration"
    echo "  6. setup-    - Setup or change  authentication"
    echo "  7. debug        - Start in debug mode"
    echo ""
    read -p "Select option (1-7): " choice
    
    case $choice in
        1) TARGET="app" ;;
        2) TARGET="backend" ;;
        3) TARGET="web" ;;
        4) TARGET="test" ;;
        5) TARGET="setup" ;;
        6) TARGET="setup-" ;;
        7) TARGET="debug" ;;
        *) echo "Invalid choice. Exiting..."; exit 1 ;;
    esac
}

if [ -z "$TARGET" ]; then
    show_menu
fi

echo ""
echo "🚀 Launching: $TARGET"
echo "================================================================"

case $TARGET in
    "app")
        echo "🔐 Starting YourDaddy Assistant (Desktop Mode)..."
        $PYTHON_CMD main.py --interface desktop
        ;;
    "backend")
        echo "🔐 Starting YourDaddy Assistant (Backend Only)..."
        $PYTHON_CMD main.py --interface web --port 5000
        ;;
    "web")
        echo "🔐 Starting YourDaddy Assistant (Web Interface)..."
        $PYTHON_CMD main.py --interface web --port 5000 &
        BACKEND_PID=$!
        
        echo "Waiting for backend to initialize..."
        sleep 5
        
        if [ -f "project/package.json" ]; then
            echo "Starting frontend server..."
            cd project
            npm run dev &
            FRONTEND_PID=$!
            cd ..
            
            echo ""
            echo "================================================================"
            echo "Both servers are running:"
            echo "  - Backend:  http://localhost:5000 (PID: $BACKEND_PID)"
            echo "  - Frontend: http://localhost:5173 (PID: $FRONTEND_PID)"
            echo ""
            echo "Press Ctrl+C to stop all servers"
            echo "================================================================"
            
            # Wait for user interrupt
            trap "echo 'Stopg servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT
            wait
        else
            echo "Frontend project not found. Backend only running at http://localhost:5000"
            echo "Press Ctrl+C to stop the backend server"
            wait $BACKEND_PID
        fi
        ;;
    "test")
        echo "🧪 Running tests..."
        $PYTHON_CMD -m pytest tests/ -v
        ;;
    "setup")
        echo "⚙️ Running setup..."
        if [ -f "scripts/setup/setup.py" ]; then
            $PYTHON_CMD scripts/setup/setup.py
        else
            echo "❌ Setup script not found"
            exit 1
        fi
        ;;
    "setup-")
        echo "🔐  Management..."
        $PYTHON_CMD setup_.py
        ;;
    "debug")
        echo "🐛 Starting in debug mode (authentication disabled)..."
        $PYTHON_CMD main.py --verbose --interface cli --skip-auth
        ;;
    *)
        echo "❌ Unknown target: $TARGET"
        echo ""
        echo "Usage: $0 [app|backend|web|test|setup|setup-|debug] [mode]"
        echo "Example: $0 app"
        echo "         $0 backend"
        echo "         $0 web"
        echo "         $0 setup-"
        exit 1
        ;;
esac

# Handle errors
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Error occurred (Exit code: $?)"
    echo "Press Enter to exit..."
    read
fi