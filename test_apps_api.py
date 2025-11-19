#!/usr/bin/env python3
"""
Simple test server to verify the apps API works without complex dependencies
"""

from flask import Flask, jsonify
from modules.app_discovery import get_apps_for_web
import json

app = Flask(__name__)

@app.route('/api/apps')
def api_apps():
    """Get list of installed applications"""
    try:
        apps = get_apps_for_web()
        return jsonify(apps)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/apps/system')
def api_system_apps():
    """Get only system tools applications"""
    try:
        apps = get_apps_for_web()
        system_apps = [app for app in apps if app['category'] == 'System Tools']
        return jsonify(system_apps)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting simple apps API test server...")
    print("📋 Endpoints:")
    print("  - http://localhost:5001/api/apps (all apps)")
    print("  - http://localhost:5001/api/apps/system (system apps only)")
    app.run(host='127.0.0.1', port=5001, debug=False)