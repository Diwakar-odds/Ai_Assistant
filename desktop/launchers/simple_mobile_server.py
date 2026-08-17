#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple standalone mobile server for testing
Serves the mobile interface without the full backend complexity
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.system('chcp 65001 > nul 2>&1')

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import socket

app = Flask(__name__)
CORS(app)

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

@app.route('/')
def index():
    """Serve mobile chat interface"""
    try:
        return render_template('mobile_chat.html')
    except:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>YourDaddy AI Mobile</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    text-align: center;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                }
                .container {
                    max-width: 600px;
                }
                h1 { font-size: 2.5em; margin-bottom: 20px; }
                p { font-size: 1.2em; margin-bottom: 15px; }
                .status { background: rgba(255,255,255,0.2); padding: 20px; border-radius: 10px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 YourDaddy AI Mobile</h1>
                <div class="status">
                    <h2>✅ Server is Running!</h2>
                    <p>Mobile interface is active</p>
                </div>
                <p>Your AI assistant is ready to chat!</p>
                <p><strong>Next steps:</strong></p>
                <p>1. Add this page to your home screen</p>
                <p>2. Connect your full backend server</p>
                <p>3. Start chatting with your AI</p>
            </div>
        </body>
        </html>
        """

@app.route('/static/manifest.json')
def manifest():
    """Serve PWA manifest"""
    return send_from_directory('static', 'manifest.json')

@app.route('/static/service-worker.js')
def service_worker():
    """Serve service worker"""
    return send_from_directory('static', 'service-worker.js')

@app.route('/api/test')
def api_test():
    """Test API endpoint"""
    return jsonify({
        'success': True,
        'message': 'Mobile server is working!',
        'features': [
            'PWA support',
            'Mobile-optimized interface',
            'Ready for AI integration'
        ]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    local_ip = get_local_ip()
    
    print("="*60)
    print("🚀 YourDaddy AI - Simple Mobile Server")
    print("="*60)
    print(f"\n📱 Access from your phone:")
    print(f"   Local:  http://{local_ip}:{port}")
    print(f"   Device: http://localhost:{port}")
    print(f"\n💡 Tip: For full features, run the main backend server")
    print("="*60 + "\n")
    
    try:
        app.run(host=host, port=port, debug=True)
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("\nTroubleshooting:")
        print(f"  - Port {port} might be in use")
        print(f"  - Try: python {__file__} --port 8080")
        sys.exit(1)
