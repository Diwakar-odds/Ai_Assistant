from flask import Blueprint, jsonify, request, send_from_directory, render_template, Response, stream_with_context
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request
import os, json, sys, time, datetime
try:
    from backend.modern_web_backend import logger, api_logger, get_current_context
except ImportError:
    pass
    

taskbar_bp = Blueprint('taskbar', __name__)


try:
    from backend.modern_web_backend import *
except ImportError:
    from modern_web_backend import *
@taskbar_bp.route('/api/taskbar/detect', methods=['GET'])
@jwt_required()
def api_detect_taskbar():
    """Detect and analyze taskbar applications"""
    try:
        from ai_assistant.automation.app_discovery import detect_taskbar_apps
        
        result = detect_taskbar_apps()
        
        return jsonify({
            "success": True,
            "taskbar_analysis": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Taskbar detection error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@taskbar_bp.route('/api/taskbar/capabilities', methods=['GET'])
def api_taskbar_capabilities():
    """Check taskbar detection capabilities"""
    try:
        from ai_assistant.automation.app_discovery import can_see_taskbar
        
        result = can_see_taskbar()
        
        return jsonify({
            "success": True,
            "capabilities": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Taskbar capabilities check error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@taskbar_bp.route('/api/taskbar/find-app', methods=['POST'])
@jwt_required()
def api_find_app_in_taskbar():
    """Find a specific application in taskbar"""
    try:
        from ai_assistant.automation.app_discovery import TaskbarDetector
        
        data = request.get_json()
        app_name = data.get('app_name')
        
        if not app_name:
            return jsonify({"success": False, "error": "App name required"}), 400
        
        detector = TaskbarDetector()
        result = detector.find_specific_app_in_taskbar(app_name)
        
        return jsonify({
            "success": True,
            "app_search_result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"App search error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@taskbar_bp.route('/api/taskbar/running-apps', methods=['GET'])
@jwt_required()
def api_get_running_apps():
    """Get list of running applications"""
    try:
        from ai_assistant.automation.app_discovery import TaskbarDetector
        
        detector = TaskbarDetector()
        result = detector.get_running_applications()
        
        return jsonify({
            "success": True,
            "running_apps": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Running apps detection error: {e}")