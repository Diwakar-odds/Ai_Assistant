#!/bin/bash

echo "============================================================"
echo "Starting YourDaddy Assistant Web UI"
echo "============================================================"
echo ""

# Start backend in background
echo "Starting backend server..."
.venv/Scripts/python.exe modern_web_backend.py &
BACKEND_PID=$!

# Wait for backend to initialize
sleep 3

# Start frontend (this will run in foreground)
echo "Starting frontend server..."
cd project
npm run dev

# When frontend is stopped (Ctrl+C), kill backend too
kill $BACKEND_PID 2>/dev/null
