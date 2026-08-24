# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
User Preferences Blueprint

Handles user preferences and settings management using persistent file storage.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import logging
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to settings file
# Assuming this runs from src/ai_assistant/services/backend or similar, 
# we need to find the project root. 
# Based on file structure: f:\bn\assitant\src\ai_assistant\services\backend\blueprints\preferences.py
# Config is at: f:\bn\assitant\config\app_settings.json

def get_settings_path():
    """Get absolute path to app_settings.json"""
    # Go up from blueprints -> backend -> services -> ai_assistant -> src -> root -> config
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent.parent.parent.parent.parent.parent
    # Actually, simpler to rely on CWD if set correctly, or relative to this file
    # Let's try to find 'config' directory relative to project root
    # Using the path we know: f:/bn/assitant/config/app_settings.json
    # And this file is: f:/bn/assitant/src/ai_assistant/services/backend/blueprints/preferences.py
    # ../../../../../../config/app_settings.json
    settings_path = current_dir.parent.parent.parent.parent.parent.joinpath('config', 'app_settings.json')
    
    # Fallback to absolute if needed (or env var)
    if not settings_path.parent.exists():
        # Try finding root by looking for marker files
        root = Path(os.getcwd())
        if (root / 'config').exists():
            settings_path = root / 'config' / 'app_settings.json'
            
    return settings_path

def load_settings():
    """Load settings from file"""
    path = get_settings_path()
    if not path.exists():
        return {}
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading settings from {path}: {e}")
        return {}

def save_settings_to_file(settings):
    """Save settings to file"""
    path = get_settings_path()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving settings to {path}: {e}")
        return False

def create_blueprint(assistant=None):
    """Create and configure the settings blueprint"""
    bp = Blueprint('preferences', __name__, url_prefix='/api/settings')
    
    @bp.route('/all', methods=['GET'])
    def get_all_settings():
        """Get all settings"""
        try:
            settings = load_settings()
            
            # DYNAMICALLY INJECT VOICES
            try:
                from voice_service import AVAILABLE_VOICES
                if "voice" not in settings:
                    settings["voice"] = {}
                if "tts" not in settings["voice"]:
                    settings["voice"]["tts"] = {}
                settings["voice"]["tts"]["available_voices"] = AVAILABLE_VOICES
            except Exception as e:
                logger.error(f"Failed to inject AVAILABLE_VOICES: {e}")
                
            return jsonify({
                "success": True,
                "settings": settings,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Get all settings error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
            
    @bp.route('/complete_onboarding', methods=['POST'])
    def complete_onboarding():
        """Mark onboarding as completed"""
        try:
            current_settings = load_settings()
            current_settings["onboarded"] = True
            if save_settings_to_file(current_settings):
                return jsonify({"success": True})
            return jsonify({"success": False, "error": "Failed to save"}), 500
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @bp.route('/update', methods=['POST'])
    def update_settings():
        """Update settings for a category"""
        try:
            data = request.get_json()
            category = data.get('category')
            new_settings = data.get('settings')
            
            if not category or not new_settings:
                return jsonify({"success": False, "error": "Missing category or settings data"}), 400
            
            current_settings = load_settings()
            
            # Update specific category
            current_settings[category] = new_settings
            
            if save_settings_to_file(current_settings):
                return jsonify({
                    "success": True,
                    "settings": current_settings,
                    "message": "Settings saved successfully"
                })
            else:
                return jsonify({"success": False, "error": "Failed to write to settings file"}), 500
                
        except Exception as e:
            logger.error(f"Update settings error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/reset', methods=['POST'])
    def reset_settings():
        """Reset settings to defaults or clear specific category"""
        try:
            data = request.get_json() or {}
            category = data.get('category')
            
            # Default settings structure matching app_settings.json
            defaults = {
              "general": {
                "language": "en-US",
                "secondaryLanguage": "hi-IN",
                "enableHinglish": True,
                "theme": "dark",
                "animations": True,
                "startOnBoot": False
              },
              "security": {
                "apiKeys": {
                  "googleGemini": "",
                  "openAI": "",
                  "elevenLabs": ""
                },
                "permissions": {
                  "allowFileDeletion": False,
                  "allowAppExecution": True,
                  "allowWebBrowsing": True,
                  "allowSystemControl": True
                },
                "encryption": {
                  "encryptDatabase": True,
                  "enablePinParams": False
                }
              },
              "ai": {
                "defaultProvider": "google",
                "defaultModel": "gemini-2.0-flash",
                "temperature": 0.7,
                "maxTokens": 4096,
                "contextWindow": 10,
                "safetySettings": {
                  "harassment": "BLOCK_MEDIUM_AND_ABOVE",
                  "hateSpeech": "BLOCK_MEDIUM_AND_ABOVE",
                  "sexuallyExplicit": "BLOCK_MEDIUM_AND_ABOVE",
                  "dangerousContent": "BLOCK_MEDIUM_AND_ABOVE"
                },
                "localLlm": {
                  "enabled": False,
                  "modelPath": "model/local_models",
                  "useGpu": False
                }
              },
              "voice": {
                "tts": {
                  "engine": "edge_tts",
                  "voice": "en-US-AriaNeural",
                  "rate": 1.0,
                  "volume": 0.9,
                  "useCache": True
                },
                "stt": {
                  "engine": "whisper_api",
                  "model": "whisper-1",
                  "sensitivity": 0.5,
                  "language": "auto",
                  "continuous": True
                },
                "wakeWord": {
                  "enabled": True,
                  "phrases": ["hey daddy", "hey assistant", "ok jarvis"],
                  "sensitivity": 0.6
                }
              },
              "automation": {
                "autoUpdate": True,
                "autoBackup": "weekly",
                "maxHistorySize": 1000,
                "smartHome": {
                  "enabled": False,
                  "provider": "none"
                }
              },
              "system": {
                "logLevel": "INFO",
                "maxLogSizeMb": 10,
                "minimizeToTray": True,
                "notifications": {
                  "desktop": True,
                  "sound": True
                }
              }
            }
            
            current_settings = load_settings()
            
            if category:
                if category in defaults:
                    current_settings[category] = defaults[category]
                else:
                    return jsonify({"success": False, "error": f"Unknown category: {category}"}), 400
            else:
                # Reset all
                current_settings = defaults
                
            if save_settings_to_file(current_settings):
                return jsonify({
                    "success": True,
                    "message": f"Settings {'category ' + category if category else 'all'} reset successfully",
                    "settings": current_settings
                })
            else:
                return jsonify({"success": False, "error": "Failed to save reset settings"}), 500
                
        except Exception as e:
            logger.error(f"Reset settings error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/export', methods=['GET'])
    def export_settings():
        """Export settings as JSON"""
        try:
            settings = load_settings()
            return jsonify({
                "success": True,
                "data": settings
            })
        except Exception as e:
            logger.error(f"Export settings error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/import', methods=['POST'])
    def import_settings():
        """Import settings from JSON"""
        try:
            data = request.get_json()
            settings_to_import = data.get('settings')
            
            if not settings_to_import:
                return jsonify({"success": False, "error": "No settings data provided"}), 400
                
            if save_settings_to_file(settings_to_import):
                return jsonify({
                    "success": True,
                    "message": "Settings imported successfully",
                    "settings": settings_to_import
                })
            else:
                return jsonify({"success": False, "error": "Failed to save imported settings"}), 500
                
        except Exception as e:
            logger.error(f"Import settings error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    return bp
