import os
import sys
import time
from datetime import datetime
from flask import Blueprint, jsonify, request
from .common import (
    logger, api_logger, limiter, validate_input, get_assistant,
    jwt_required, get_jwt_identity, verify_jwt_in_request,
    ENABLE_VOICE, ENABLE_MULTIMODAL, ENABLE_CONVERSATIONAL_AI, ENABLE_SYSTEM_MONITORING
)

system_bp = Blueprint('system', __name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from ai_assistant.automation.app_discovery import get_apps_for_web, refresh_app_database
    from ai_assistant.automation.automation_tools_new import (
        smart_open_application, get_spotify_status,
        spotify_play_pause, spotify_next_track, spotify_previous_track
    )
    AUTOMATION_AVAILABLE = True
except ImportError:
    AUTOMATION_AVAILABLE = False

MULTIMODAL_AVAILABLE = ENABLE_MULTIMODAL
CONVERSATIONAL_AI_AVAILABLE = ENABLE_CONVERSATIONAL_AI
MULTILINGUAL_AVAILABLE = True
VOICE_AVAILABLE = ENABLE_VOICE
ENHANCED_AI_AVAILABLE = True
USAGE_ANALYZER_AVAILABLE = True

@system_bp.route('/api/status')
def api_status():
    """API status endpoint - Public"""
    authenticated = False
    try:
        verify_jwt_in_request(optional=True)
        authenticated = bool(get_jwt_identity())
    except Exception:
        pass
    
    learning_systems_available = False
    try:
        from learning_integration import LEARNING_SYSTEMS_AVAILABLE
        learning_systems_available = LEARNING_SYSTEMS_AVAILABLE
    except ImportError:
        pass
    
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "authenticated": authenticated,
        "services": {
            "automation": AUTOMATION_AVAILABLE,
            "multimodal": MULTIMODAL_AVAILABLE,
            "conversational_ai": CONVERSATIONAL_AI_AVAILABLE,
            "voice": VOICE_AVAILABLE,
            "system_monitoring": PSUTIL_AVAILABLE,
            "learning_systems": learning_systems_available,
            "enhanced_ai": ENHANCED_AI_AVAILABLE,
            "usage_analyzer": USAGE_ANALYZER_AVAILABLE
        }
    })

@system_bp.route('/api/startup/sequence', methods=['GET'])
@limiter.limit("10 per minute")
def api_startup_sequence():
    """Get complete startup sequence data (JARVIS-style)"""
    try:
        from startup_sequence import get_startup_sequence
        startup = get_startup_sequence()
        data = startup.get_startup_sequence_data()
        return jsonify({
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Startup sequence error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to generate startup sequence",
            "timestamp": datetime.now().isoformat()
        }), 500

@system_bp.route('/api/startup/diagnostics', methods=['GET'])
@limiter.limit("20 per minute")
def api_startup_diagnostics():
    """Get system diagnostics for startup sequence"""
    try:
        from startup_sequence import get_startup_sequence
        startup = get_startup_sequence()
        diagnostics = startup.get_system_diagnostics()
        return jsonify({
            "success": True,
            "diagnostics": diagnostics,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Startup diagnostics error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to get system diagnostics",
            "timestamp": datetime.now().isoformat()
        }), 500

@system_bp.route('/api/startup/briefing', methods=['GET'])
@limiter.limit("20 per minute")
def api_startup_briefing():
    """Get contextual briefing for startup sequence"""
    try:
        from startup_sequence import get_startup_sequence
        startup = get_startup_sequence()
        briefing = startup.get_contextual_briefing()
        return jsonify({
            "success": True,
            "briefing": briefing,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Startup briefing error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to get briefing",
            "timestamp": datetime.now().isoformat()
        }), 500

@system_bp.route('/api/system/stats')
@jwt_required()
@limiter.limit("60 per minute")
def api_system_stats():
    """Get real-time system statistics - PROTECTED"""
    try:
        assistant = get_assistant()
        if assistant and hasattr(assistant, 'get_real_time_system_stats'):
            stats = assistant.get_real_time_system_stats()
            return jsonify(stats)
        return jsonify({
            "cpu_percent": 0,
            "memory_percent": 0,
            "disk_percent": 0,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve system stats: {e}"}), 500

@system_bp.route('/api/features', methods=['GET'])
def api_features():
    """Get list of all available features and their status"""
    features = {
        "conversational_ai": CONVERSATIONAL_AI_AVAILABLE,
        "multimodal_ai": MULTIMODAL_AVAILABLE,
        "multilingual": MULTILINGUAL_AVAILABLE,
        "automation": AUTOMATION_AVAILABLE,
        "voice_recognition": VOICE_AVAILABLE,
        "modules": {
            "smart_automation": True,
            "enhanced_learning": True,
            "advanced_integration": True,
            "file_operations": True,
            "web_scraping": True,
            "music_control": True,
            "email_handler": True,
            "calendar_integration": True,
            "document_ocr": True,
            "memory_system": True,
            "system_monitoring": True,
            "taskbar_detection": True
        }
    }
    return jsonify(features)

@system_bp.route('/api/apps', methods=['GET'])
@limiter.limit("30 per minute")
def api_apps():
    """Get list of installed applications - PUBLIC"""
    try:
        if AUTOMATION_AVAILABLE:
            apps = get_apps_for_web()
            if not isinstance(apps, list):
                apps = []
        else:
            apps = [
                {"name": "Chrome", "path": "chrome.exe", "category": "Browser", "usage": 89, "description": "Google Chrome web browser"},
                {"name": "Mail", "path": "mail.exe", "category": "Communication", "usage": 76, "description": "Email application"},
                {"name": "Documents", "path": "word.exe", "category": "Productivity", "usage": 65, "description": "Document editor"},
                {"name": "Photos", "path": "photos.exe", "category": "Media", "usage": 52, "description": "Photo viewer"},
                {"name": "Videos", "path": "vlc.exe", "category": "Media", "usage": 43, "description": "Video player"},
                {"name": "Code", "path": "code.exe", "category": "Development", "usage": 92, "description": "Code editor"},
                {"name": "Terminal", "path": "cmd.exe", "category": "System Tools", "usage": 78, "description": "Command line interface"},
                {"name": "Calculator", "path": "calc.exe", "category": "System Tools", "usage": 45, "description": "Windows calculator"},
                {"name": "Notepad", "path": "notepad.exe", "category": "System Tools", "usage": 30, "description": "Simple text editor"}
            ]
        return jsonify(apps)
    except Exception as e:
        logger.error(f"Failed to get apps: {e}")
        return jsonify([]), 500

@system_bp.route('/api/apps/refresh', methods=['POST'])
@limiter.limit("5 per minute")
def api_refresh_apps():
    """Refresh/rescan installed applications"""
    try:
        if AUTOMATION_AVAILABLE:
            result = refresh_app_database()
            apps = get_apps_for_web()
            return jsonify({
                "success": True,
                "message": result,
                "total": len(apps),
                "apps": apps
            })
        else:
            return jsonify({"success": False, "message": "App discovery not available"}), 503
    except Exception as e:
        logger.error(f"Failed to refresh apps: {e}")
        return jsonify({"error": str(e)}), 500

@system_bp.route('/api/apps/launch', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("20 per minute")
def api_launch_app():
    """Launch an application"""
    try:
        current_user = get_jwt_identity() or "demo_user"
        data = request.get_json() or {}
        
        is_valid, error = validate_input(data, 'app_name', 'app_name')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        app_name = data['app_name']
        
        try:
            if AUTOMATION_AVAILABLE:
                result = smart_open_application(app_name)
                if "Error" in result or "not found" in result.lower():
                    if "youtube music" in app_name.lower():
                        import webbrowser
                        webbrowser.open('https://music.youtube.com')
                        result = "Opened YouTube Music in web browser"
                    elif "spotify" in app_name.lower():
                        import webbrowser
                        webbrowser.open('https://open.spotify.com')
                        result = "Opened Spotify in web browser"
                    else:
                        result = f"Attempted to launch {app_name} (result: {result})"
            else:
                result = f"Launched {app_name} (simulation mode)"
        except Exception as launch_error:
            result = f"Could not launch {app_name} directly: {launch_error}"
        
        return jsonify({
            "success": True,
            "message": result,
            "app_name": app_name,
            "user": current_user
        })
    except Exception as e:
        logger.error(f"Launch error: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to launch {data.get('app_name', 'application')}: {str(e)}"
        }), 500

@system_bp.route('/api/spotify/status')
@jwt_required()
@limiter.limit("30 per minute")
def api_spotify_status():
    """Get Spotify status - PROTECTED"""
    try:
        if AUTOMATION_AVAILABLE:
            status = get_spotify_status()
        else:
            status = {
                "is_playing": True,
                "track_name": "Midnight Dreams",
                "artist_name": "Synthwave Collective",
                "progress": 65,
                "duration": 240
            }
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": "Failed to retrieve Spotify status"}), 500

@system_bp.route('/api/spotify/control', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def api_spotify_control():
    """Control Spotify playback - PROTECTED"""
    try:
        current_user = get_jwt_identity()
        data = request.get_json() or {}
        action = data.get('action', '')
        
        if not action:
            return jsonify({"error": "No action provided"}), 400
        
        if AUTOMATION_AVAILABLE:
            if action == 'play_pause':
                result = spotify_play_pause()
            elif action == 'next':
                result = spotify_next_track()
            elif action == 'previous':
                result = spotify_previous_track()
            else:
                return jsonify({"error": "Unknown action"}), 400
        else:
            result = f"Spotify {action} executed (simulation mode)"
        
        return jsonify({
            "success": True,
            "message": result,
            "action": action,
            "user": current_user
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to control Spotify: {e}"
        }), 500

@system_bp.route('/api/activity')
@jwt_required()
def api_activity():
    """Get recent activity feed - PROTECTED"""
    activities = [
        {"time": "2 min ago", "action": "Launched Spotify", "status": "success"},
        {"time": "15 min ago", "action": "Weather update received", "status": "info"},
        {"time": "1 hour ago", "action": "Calendar sync completed", "status": "success"},
        {"time": "3 hours ago", "action": "System optimization", "status": "info"}
    ]