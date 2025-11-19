# YourDaddy Assistant - Simplified Web Backend
"""
Simplified Flask backend to serve the web interface with basic functionality
"""

from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, 
    get_jwt_identity
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import sys
import time
import threading
import json
from datetime import datetime, timedelta
from pathlib import Path
import re
import secrets
import logging
import webbrowser
import subprocess

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    sys.stderr.reconfigure(encoding='utf-8') if hasattr(sys.stderr, 'reconfigure') else None

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Security Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Initialize JWT
jwt = JWTManager(app)

# Initialize Rate Limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri="memory://"
)

# CORS Configuration
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5000,http://127.0.0.1:3000,http://127.0.0.1:5000').split(',')
CORS(app, resources={
    r"/api/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Initialize SocketIO
socketio = SocketIO(
    app, 
    cors_allowed_origins=ALLOWED_ORIGINS,
    async_mode='threading',
    engineio_logger=False
)

# User Management
USERS_DB = {
    "admin": {
        "password_hash": generate_password_hash(os.getenv('ADMIN_PASSWORD', 'changeme123')),
        "role": "admin"
    }
}

# Input Validation Patterns
VALIDATION_PATTERNS = {
    'command': re.compile(r'^[\w\s\-.,!?@#$%()+=:;"\']+$'),
    'app_name': re.compile(r'^[\w\s\-.]+$'),
    'username': re.compile(r'^[a-zA-Z0-9_]{3,20}$'),
}

def validate_input(data, field, pattern_name):
    """Validate input data against pattern"""
    if not data or field not in data:
        return False, f"{field} is required"
    
    value = data[field]
    if not isinstance(value, str):
        return False, f"{field} must be a string"
    
    if len(value) > 1000:
        return False, f"{field} is too long (max 1000 characters)"
    
    pattern = VALIDATION_PATTERNS.get(pattern_name)
    if pattern and not pattern.match(value):
        return False, f"{field} contains invalid characters"
    
    return True, None

# Try to import automation tools, but provide fallbacks if they fail
try:
    from modules.app_discovery import get_apps_for_web, smart_open_application
    AUTOMATION_AVAILABLE = True
    print("✅ Basic automation tools loaded")
except ImportError as e:
    print(f"⚠️ Automation tools not available: {e}")
    AUTOMATION_AVAILABLE = False
    
    def get_apps_for_web():
        return [
            {"name": "Chrome", "path": "chrome.exe", "category": "Web Browsers", "usage": 95, "description": "Web browser"},
            {"name": "YouTube Music", "path": "youtube_music.exe", "category": "Media", "usage": 75, "description": "Music streaming"},
            {"name": "Spotify", "path": "spotify.exe", "category": "Media", "usage": 88, "description": "Music streaming"},
            {"name": "Discord", "path": "discord.exe", "category": "Communication", "usage": 90, "description": "Gaming chat"},
            {"name": "VS Code", "path": "code.exe", "category": "Development", "usage": 90, "description": "Code editor"},
            {"name": "Notepad", "path": "notepad.exe", "category": "System Tools", "usage": 30, "description": "Simple text editor"}
        ]
    
    def smart_open_application(app_name):
        # Simple fallback launcher
        app_lower = app_name.lower()
        if "youtube music" in app_lower:
            webbrowser.open('https://music.youtube.com')
            return "✅ Opened YouTube Music in web browser"
        elif "spotify" in app_lower:
            webbrowser.open('https://open.spotify.com')
            return "✅ Opened Spotify in web browser"
        elif "chrome" in app_lower:
            try:
                subprocess.Popen(['chrome.exe'])
                return f"✅ Opened {app_name}"
            except:
                webbrowser.open('https://google.com')
                return f"✅ Opened {app_name} via web browser"
        else:
            return f"🔍 Searched for {app_name}, but could not find it installed"

# Routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_web_app(path):
    """Serve web application"""
    if path.startswith('static/'):
        return send_from_directory('static', path[7:])
    elif path and path != 'favicon.ico':
        try:
            return send_from_directory('static', path)
        except:
            pass
    return render_template('index.html')

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def api_login():
    """Authenticate user and return JWT token"""
    try:
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'username', 'username')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        if 'password' not in data:
            return jsonify({"error": "Password is required"}), 400
        
        username = data['username']
        password = data['password']
        
        # Check credentials
        user = USERS_DB.get(username)
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Create tokens
        access_token = create_access_token(
            identity=username,
            additional_claims={"role": user['role']}
        )
        
        return jsonify({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 86400,
            "user": {
                "username": username,
                "role": user['role']
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Login failed"}), 500

@app.route('/api/apps')
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_apps():
    """Get list of installed applications"""
    try:
        apps = get_apps_for_web()
        return jsonify({
            "apps": apps,
            "total": len(apps),
            "categories": list(set(app.get('category', 'Unknown') for app in apps))
        })
    except Exception as e:
        return jsonify({"error": "Failed to retrieve applications"}), 500

@app.route('/api/apps/launch', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("20 per minute")
def api_launch_app():
    """Launch an application"""
    try:
        current_user = get_jwt_identity() or "demo_user"
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'app_name', 'app_name')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        app_name = data['app_name']
        
        try:
            result = smart_open_application(app_name)
        except Exception as launch_error:
            # Fallback for common applications
            app_lower = app_name.lower()
            if "youtube music" in app_lower:
                webbrowser.open('https://music.youtube.com')
                result = "✅ Opened YouTube Music in web browser"
            elif "spotify" in app_lower:
                webbrowser.open('https://open.spotify.com')
                result = "✅ Opened Spotify in web browser"
            else:
                result = f"⚠️ Could not launch {app_name} directly: {launch_error}"
        
        return jsonify({
            "success": True,
            "message": result,
            "app_name": app_name,
            "user": current_user
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to launch {data.get('app_name', 'application')}: {str(e)}"
        }), 500

@app.route('/api/command', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_command():
    """Process a command"""
    try:
        current_user = get_jwt_identity() or "demo_user"
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'command', 'command')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        command = data['command'].strip()
        cmd_lower = command.lower()
        
        # Process basic commands
        response = ""
        if any(word in cmd_lower for word in ['hello', 'hi', 'hey']):
            response = "Hello! How can I assist you today?"
        elif 'time' in cmd_lower:
            response = f"Current time: {datetime.now().strftime('%H:%M:%S')}"
        elif 'date' in cmd_lower:
            response = f"Current date: {datetime.now().strftime('%Y-%m-%d')}"
        elif any(word in cmd_lower for word in ['open', 'launch', 'start']):
            app_name = cmd_lower
            for word in ['open', 'launch', 'start', 'run']:
                app_name = app_name.replace(word, '')
            app_name = app_name.strip()
            result = smart_open_application(app_name)
            response = result
        elif 'search' in cmd_lower:
            query = cmd_lower.replace('search', '').strip()
            webbrowser.open(f'https://www.google.com/search?q={query}')
            response = f"🔍 Searching for: {query}"
        else:
            response = f"I received your command: {command}. This is a basic demo version."
        
        return jsonify({
            "success": True,
            "response": response,
            "user": current_user
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Command processing failed: {str(e)}"
        }), 500

@app.route('/api/status')
@limiter.limit("60 per minute")
def api_status():
    """Get system status"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0-simplified"
    })

# Socket.IO Events
@socketio.on('connect')
def handle_connect():
    emit('response', {'message': 'Connected to YourDaddy Assistant'})

@socketio.on('command')
def handle_command(data):
    command = data.get('text', '')
    # Process command (same logic as API endpoint)
    cmd_lower = command.lower()
    
    response = ""
    if any(word in cmd_lower for word in ['hello', 'hi', 'hey']):
        response = "Hello! How can I assist you today?"
    elif any(word in cmd_lower for word in ['open', 'launch', 'start']):
        app_name = cmd_lower
        for word in ['open', 'launch', 'start', 'run']:
            app_name = app_name.replace(word, '')
        app_name = app_name.strip()
        result = smart_open_application(app_name)
        response = result
    else:
        response = f"Command received: {command}"
    
    emit('response', {'message': response})

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 YourDaddy Assistant - Simplified Web Backend")
    print("=" * 60)
    print("🌐 Server starting on: http://localhost:5000")
    print("📱 Web interface available")
    print("⚡ Real-time features enabled via WebSockets")
    print("🔧 API endpoints available at /api/*")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        host = os.getenv('HOST', '127.0.0.1')
        port = int(os.getenv('PORT', 5000))
        
        print(f"🔒 Security: JWT authentication enabled")
        print(f"🔒 Security: Rate limiting enabled")
        print(f"🔒 Security: Host binding: {host}")
        print("")
        print(f"⚠️  Default credentials: username='admin', password='{os.getenv('ADMIN_PASSWORD', 'changeme123')}'")
        print("")
        
        socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)