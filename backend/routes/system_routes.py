from flask import Blueprint, jsonify, request, send_from_directory, render_template, Response, stream_with_context
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request
import os, json, sys, time, datetime
try:
    from backend.modern_web_backend import logger, api_logger, get_current_context
except ImportError:
    pass
    

system_bp = Blueprint('system', __name__)


try:
    from backend.modern_web_backend import *
except ImportError:
    from modern_web_backend import *
@system_bp.route('/api/status')
def api_status():
    """API status endpoint - Public"""
    authenticated = False
    try:
        verify_jwt_in_request(optional=True)
        authenticated = bool(get_jwt_identity())
    except Exception:
        pass
    
    # Check learning systems availability
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
            # NEW ADVANCED FEATURES
            "enhanced_ai": ENHANCED_AI_AVAILABLE,
            "usage_analyzer": USAGE_ANALYZER_AVAILABLE,
            "semantic_cache": ENHANCED_AI_AVAILABLE and enhanced_ai and enhanced_ai.cache is not None,
            "model_router": ENHANCED_AI_AVAILABLE and enhanced_ai and enhanced_ai.router is not None,
            "streaming": ENHANCED_AI_AVAILABLE and enhanced_ai and enhanced_ai.streaming is not None,
            "emotion_detection": ENHANCED_AI_AVAILABLE and enhanced_ai and enhanced_ai.emotion_detector is not None,
            "visual_verification": ENHANCED_AI_AVAILABLE and enhanced_ai and enhanced_ai.verifier is not None
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
        stats = assistant.get_real_time_system_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": "Failed to retrieve system stats"}), 500

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

@limiter.limit("30 per minute")
def api_apps():
    """Get list of installed applications - PUBLIC"""
    try:
        if AUTOMATION_AVAILABLE:
            apps = get_apps_for_web()
            # Ensure it's always a list
            if not isinstance(apps, list):
                apps = []
        else:
            # Fallback app list - MUST be an array, not object
            apps = [
                {"name": "Chrome", "path": "chrome.exe", "category": "Browser", "usage": 89, "description": "Google Chrome web browser"},
                {"name": "Mail", "path": "mail.exe", "category": "Communication", "usage": 76, "description": "Email application"},
                {"name": "Documents", "path": "word.exe", "category": "Productivity", "usage": 65, "description": "Document editor"},
                {"name": "Photos", "path": "photos.exe", "category": "Media", "usage": 52, "description": "Photo viewer"},
                {"name": "Videos", "path": "vlc.exe", "category": "Media", "usage": 43, "description": "Video player"},
                {"name": "Code", "path": "code.exe", "category": "Development", "usage": 92, "description": "Code editor"},
                {"name": "Database", "path": "pgadmin.exe", "category": "Development", "usage": 67, "description": "Database administration"},
                {"name": "Terminal", "path": "cmd.exe", "category": "System Tools", "usage": 78, "description": "Command line interface"},
                {"name": "Calculator", "path": "calc.exe", "category": "System Tools", "usage": 45, "description": "Windows calculator"},
                {"name": "Notepad", "path": "notepad.exe", "category": "System Tools", "usage": 30, "description": "Simple text editor"},
                {"name": "Paint", "path": "mspaint.exe", "category": "System Tools", "usage": 25, "description": "Image editor"},
                {"name": "Control Panel", "path": "control.exe", "category": "System Tools", "usage": 20, "description": "System settings"},
                {"name": "Task Manager", "path": "taskmgr.exe", "category": "System Tools", "usage": 35, "description": "Process manager"}
            ]
        
        # Always return array directly
        return jsonify(apps)
    except Exception as e:
        logger.error(f"Failed to get apps: {e}")
        # Return empty array on error, not error object
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
@jwt_required(optional=True)  # Optional authentication for demo purposes
@limiter.limit("20 per minute")
def api_launch_app():
    """Launch an application - DEMO MODE"""
    try:
        current_user = get_jwt_identity() or "demo_user"
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'app_name', 'app_name')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        app_name = data['app_name']
        
        try:
            if AUTOMATION_AVAILABLE:
                result = smart_open_application(app_name)
                if "Error" in result or "not found" in result.lower():
                    # Try alternative approaches for common apps
                    if "youtube music" in app_name.lower():
                        # Try opening YouTube Music via web
                        import webbrowser
                        webbrowser.open('https://music.youtube.com')
                        result = "Opened YouTube Music in web browser"
                    elif "spotify" in app_name.lower():
                        # Try opening Spotify via web
                        import webbrowser
                        webbrowser.open('https://open.spotify.com')
                        result = "Opened Spotify in web browser"
                    else:
                        result = f"Attempted to launch {app_name} (result: {result})"
            else:
                result = f"Launched {app_name} (simulation mode)"
        except Exception as launch_error:
            # Fallback for common applications
            if "youtube music" in app_name.lower():
                import webbrowser
                webbrowser.open('https://music.youtube.com')
                result = "Opened YouTube Music in web browser"
            elif "spotify" in app_name.lower():
                import webbrowser
                webbrowser.open('https://open.spotify.com')
                result = "Opened Spotify in web browser"
            else:
                result = f"Could not launch {app_name} directly, but command was received"
        
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
        data = request.get_json()
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
            "error": "Failed to control Spotify"
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