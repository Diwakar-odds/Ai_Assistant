#!/usr/bin/env python3
"""
Simple Flask backend to serve the React UI
"""

import os
import sys
from flask import Flask, send_from_directory

# Create Flask app
app = Flask(__name__)

# Serve React Build (Bolt UI)
@app.route('/')
def index():
    """Serve React app build"""
    try:
        print("Serving React app from project/dist")
        return send_from_directory('project/dist', 'index.html')
    except Exception as e:
        print(f"React app serving error: {e}")
        return f"<h1>React App Error</h1><p>Error: {e}</p><p>Please ensure the React app is built in project/dist/</p>"

@app.route('/assets/<path:filename>')
def serve_react_assets(filename):
    """Serve React build assets"""
    try:
        return send_from_directory('project/dist/assets', filename)
    except Exception as e:
        print(f"Asset serving error: {e}")
        return "Asset not found", 404

@app.route('/<path:path>')
def serve_static_or_react(path):
    """Serve static files or fallback to React app"""
    # Handle old static files for backward compatibility
    if path.startswith('static/'):
        try:
            return send_from_directory('static', path[7:])
        except:
            pass
    
    # Handle common files
    elif path in ['favicon.ico', 'robots.txt', 'vite.svg']:
        try:
            return send_from_directory('project/dist', path)
        except:
            try:
                return send_from_directory('static', path)
            except:
                return "File not found", 404
    
    # For any other path, serve React app (SPA routing)
    try:
        return send_from_directory('project/dist', 'index.html')
    except Exception as e:
        print(f"React app fallback error: {e}")
        return f"<h1>App Error</h1><p>Could not serve React app: {e}</p>", 404

# Basic API endpoints to prevent React errors
@app.route('/api/status')
def api_status():
    """Basic status endpoint"""
    return {
        "status": "online",
        "message": "Simple React UI server",
        "version": "1.0.0"
    }

@app.route('/api/command', methods=['POST'])
def api_command():
    """Basic command endpoint"""
    return {
        "response": "Backend features are temporarily disabled. This is serving the React UI only.",
        "status": "limited_mode"
    }

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 YourDaddy Assistant - Simple React UI Server")
    print("=" * 60)
    print("🌐 Server starting on: http://localhost:5000")
    print("📱 React frontend (Bolt UI) will be served")
    print("⚠️  Backend features are temporarily disabled")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        app.run(host='127.0.0.1', port=5000, debug=False)
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)