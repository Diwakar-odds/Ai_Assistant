# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Voice Blueprint - Complete Implementation

Handles all voice-related endpoints including status, history, control, and settings.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_blueprint(assistant):
    """Create and configure the voice blueprint"""
    bp = Blueprint('voice_routes', __name__, url_prefix='/api/voice')
    
    @bp.route('/status', methods=['GET'])
    def voice_status():
        """Get voice system status"""
        try:
            status = {
                "available": hasattr(assistant, 'voice_recognizer'),
                "listening": False,
                "timestamp": datetime.now().isoformat()
            }
            
            # Try to get actual voice status
            if hasattr(assistant, 'voice_recognizer') and assistant.voice_recognizer:
                try:
                    status["listening"] = getattr(assistant.voice_recognizer, 'is_listening', False)
                    status["engine"] = "advanced"
                except AttributeError:
                    pass
            
            return jsonify(status)
        except Exception as e:
            logger.error(f"Voice status error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/history', methods=['GET'])
    @jwt_required(optional=True)
    def voice_history():
        """Get voice command history"""
        try:
            # Return empty history for now
            # In production, this would query a database
            history = []
            return jsonify({
                "history": history,
                "count": len(history),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Voice history error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/start', methods=['POST'])
    @jwt_required(optional=True)
    def start_voice():
        """Start voice listening"""
        try:
            if hasattr(assistant, 'start_voice_listening'):
                result = assistant.start_voice_listening()
                return jsonify({
                    "success": True,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Voice features not available"
                }), 503
        except Exception as e:
            logger.error(f"Start voice error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/stop', methods=['POST'])
    @jwt_required(optional=True)
    def stop_voice():
        """Stop voice listening"""
        try:
            if hasattr(assistant, 'stop_voice_listening'):
                result = assistant.stop_voice_listening()
                return jsonify({
                    "success": True,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Voice features not available"
                }), 503
        except Exception as e:
            logger.error(f"Stop voice error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/settings', methods=['GET'])
    @jwt_required(optional=True)
    def get_voice_settings():
        """Get voice settings"""
        try:
            from ai_assistant.voice.voice_settings_manager import get_settings_manager
            settings_mgr = get_settings_manager()
            
            return jsonify({
                "success": True,
                "settings": settings_mgr.settings,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Get settings error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/settings', methods=['POST'])
    @jwt_required(optional=True)
    def update_voice_settings():
        """Update voice settings"""
        try:
            from ai_assistant.voice.voice_settings_manager import get_settings_manager
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            settings_mgr = get_settings_manager()
            
            # Update settings
            if "tts" in data:
                settings_mgr.settings["tts"].update(data["tts"])
            if "stt" in data:
                settings_mgr.settings["stt"].update(data["stt"])
            if "wake_word" in data:
                settings_mgr.settings["wake_word"].update(data["wake_word"])
            if "general" in data:
                settings_mgr.settings["general"].update(data["general"])
            
            # Save to file
            success = settings_mgr.save_settings()
            
            return jsonify({
                "success": success,
                "message": "Settings updated and saved" if success else "Failed to save settings",
                "settings": settings_mgr.settings,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Update settings error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/speak', methods=['POST'])
    @jwt_required(optional=True)
    def speak_text():
        """Text-to-speech endpoint"""
        try:
            data = request.get_json()
            text = data.get('text', '')
            
            if not text:
                return jsonify({"error": "No text provided"}), 400
            
            if hasattr(assistant, 'speak_text'):
                result = assistant.speak_text(text)
                return jsonify({
                    "success": True,
                    "text": text,
                    "spoken": result,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "TTS not available"
                }), 503
        except Exception as e:
            logger.error(f"Speak error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/recognize', methods=['POST'])
    @jwt_required(optional=True)
    def recognize_audio():
        """Speech-to-text endpoint"""
        try:
            # This would handle audio file upload in production
            return jsonify({
                "success": False,
                "error": "Audio recognition endpoint - file upload required"
            }), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    return bp
