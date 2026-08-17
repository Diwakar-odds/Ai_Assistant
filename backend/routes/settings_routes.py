from flask import Blueprint, jsonify, request, send_from_directory, render_template, Response, stream_with_context
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request
import os, json, sys, time, datetime
try:
    from backend.modern_web_backend import logger, api_logger, get_current_context
except ImportError:
    pass
    

settings_bp = Blueprint('settings', __name__)


try:
    from backend.modern_web_backend import *
except ImportError:
    from modern_web_backend import *
@settings_bp.route('/api/language/detect', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_detect_language():
    """Detect language of text"""
    try:
        if not assistant.multilingual:
            return jsonify({"error": "Multilingual support not available"}), 503
        
        data = request.get_json()
        text = data.get('text')
        
        if not text:
            return jsonify({"error": "Text required"}), 400
        
        language_context = assistant.multilingual.detect_language(text)
        
        return jsonify({
            "detected_language": language_context.detected_language.value,
            "confidence": language_context.confidence,
            "original_text": text,
            "detected_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Language detection failed: {str(e)}"}), 500

@settings_bp.route('/api/language/translate', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("20 per minute")
def api_translate_text():
    """Translate text to target language"""
    try:
        if not assistant.multilingual:
            return jsonify({"error": "Multilingual support not available"}), 503
        
        data = request.get_json()
        text = data.get('text')
        target_language = data.get('target_language', 'en')
        
        if not text:
            return jsonify({"error": "Text required"}), 400
        
        from ai_assistant.multilingual import Language
        translated = assistant.multilingual.translate_text(text, Language(target_language))
        
        return jsonify({
            "original_text": text,
            "translated_text": translated,
            "target_language": target_language,
            "translated_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Translation failed: {str(e)}"}), 500

@settings_bp.route('/api/language/hinglish', methods=['POST'])
def process_hinglish():
    """Process Hinglish commands"""
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    if assistant.multilingual:
        result = assistant.multilingual.process_hinglish_command(text)
        return jsonify(result)
    else:
        return jsonify({"error": "Multilingual support not available"}), 503

@settings_bp.route('/api/language/preference', methods=['POST'])
def set_language_preference():
    """Set user language preference"""
    data = request.json
    language = data.get('language', 'hinglish')
    tts_language = data.get('tts_language', language)
    user_id = data.get('user_id', 'web_user')
    
    if assistant.multilingual:
        try:
            lang = Language(language)
            tts_lang = Language(tts_language)
            assistant.multilingual.set_language_preference(user_id, lang, tts_lang)
            assistant.current_language = language
            return jsonify({
                'message': f'Language preference set to {language}',
                'user_id': user_id
            })
        except ValueError as e:
            return jsonify({"error": f"Invalid language: {str(e)}"}), 400
    else:
        return jsonify({"error": "Multilingual support not available"}), 503

@settings_bp.route('/api/language/preference', methods=['GET'])
def get_language_preference():
    """Get current language preference"""
    user_id = request.args.get('user_id', 'web_user')
    
    if assistant.multilingual:
        lang, tts_lang = assistant.multilingual.get_language_preference(user_id)
        return jsonify({
            'language': lang.value,
            'tts_language': tts_lang.value,
            'user_id': user_id
        })
    else:
        return jsonify({
            'language': 'en',
            'tts_language': 'en',
            'user_id': user_id
        })

@settings_bp.route('/api/error/log', methods=['POST'])
def api_log_error():
    """Log frontend errors for monitoring"""
    try:
        error_data = request.get_json()
        
        # Log to proper logger instead of print
        logger.error(f"Frontend Error: {error_data.get('message', 'Unknown error')}")
        logger.error(f"URL: {error_data.get('url', 'Unknown')}")
        logger.error(f"Time: {error_data.get('timestamp', 'Unknown')}")
        
        # Create error log entry
        error_log = {
            'timestamp': error_data.get('timestamp', datetime.now().isoformat()),
            'message': error_data.get('message', ''),
            'stack': error_data.get('stack', ''),
            'component_stack': error_data.get('componentStack', ''),
            'user_agent': error_data.get('userAgent', ''),
            'url': error_data.get('url', ''),
        }
        
        # Save to proper error log file in logs directory
        log_file = Path('logs/errors/frontend_errors.json')
        try:
            if log_file.exists() and log_file.stat().st_size > 0:
                try:
                    with open(log_file, 'r') as f:
                        logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
            else:
                logs = []
            
            logs.append(error_log)
            
            # Keep only last 100 errors
            if len(logs) > 100:
                logs = logs[-100:]
            
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save error log: {e}")
        
        return jsonify({"success": True, "logged": True})
    
    except Exception as e:
        logger.error(f"Error logging endpoint failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@settings_bp.route('/api/settings/save', methods=['POST'])
def api_save_settings():
    """Save user settings"""
    try:
        settings_data = request.get_json()
        
        # Save settings to a file (in production, use a database)
        settings_file = Path(__file__).parent / 'user_settings.json'
        with open(settings_file, 'w') as f:
            json.dump(settings_data, f, indent=2)
        
        return jsonify({"success": True, "message": "Settings saved successfully"})
    
    except Exception as e:
        print(f"Failed to save settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@settings_bp.route('/api/settings/load')
def api_load_settings():
    """Load user settings"""
    try:
        settings_file = Path(__file__).parent / 'user_settings.json'
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
            return jsonify(settings)
        else:
            return jsonify({"settings": None})
    
    except Exception as e:
        print(f"Failed to load settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@settings_bp.route('/api/settings/all', methods=['GET'])
def api_get_all_settings():
    """Get all comprehensive settings - schema must match frontend SettingsDetail.tsx"""
    try:
        settings_file = Path(__file__).parent.parent.parent / 'data' / 'user_preferences' / 'settings.json'
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load secure keys
        from ai_assistant.utils.secure_storage import get_secure_key, save_secure_key
        
        google_gemini_key = get_secure_key('googleGemini')
        open_ai_key = get_secure_key('openAI')
        eleven_labs_key = get_secure_key('elevenLabs')
        
        # Backward compatibility / Migration:
        # If keyring is empty but environment variables are set, migrate them to keyring
        if not google_gemini_key and os.getenv('GOOGLE_GEMINI_API_KEY'):
            google_gemini_key = os.getenv('GOOGLE_GEMINI_API_KEY', '')
            save_secure_key('googleGemini', google_gemini_key)
        if not open_ai_key and os.getenv('OPENAI_API_KEY'):
            open_ai_key = os.getenv('OPENAI_API_KEY', '')
            save_secure_key('openAI', open_ai_key)
        if not eleven_labs_key and os.getenv('ELEVEN_LABS_API_KEY'):
            eleven_labs_key = os.getenv('ELEVEN_LABS_API_KEY', '')
            save_secure_key('elevenLabs', eleven_labs_key)
            
        # Default settings matching SettingsDetail.tsx interfaces exactly
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
                    "googleGemini": "********" if google_gemini_key else "",
                    "openAI": "********" if open_ai_key else "",
                    "elevenLabs": "********" if eleven_labs_key else ""
                },
                "permissions": {
                    "allowFileDeletion": os.getenv('ENABLE_FILE_DELETION', 'false').lower() == 'true',
                    "allowAppExecution": os.getenv('ENABLE_APP_EXECUTION', 'true').lower() == 'true',
                    "allowWebBrowsing": True,
                    "allowSystemControl": True
                },
                "encryption": {
                    "encryptDatabase": True,
                    "enablePinParams": False
                }
            },
            "ai": {
                "defaultProvider": "gemini",
                "defaultModel": "gemini-2.5-flash",
                "temperature": 0.7,
                "maxTokens": 2048,
                "contextWindow": 10,
                "safetySettings": {
                    "harassment": "BLOCK_MEDIUM_AND_ABOVE",
                    "hateSpeech": "BLOCK_MEDIUM_AND_ABOVE",
                    "sexuallyExplicit": "BLOCK_MEDIUM_AND_ABOVE",
                    "dangerousContent": "BLOCK_MEDIUM_AND_ABOVE"
                },
                "localLlm": {
                    "enabled": False,
                    "modelPath": "",
                    "useGpu": False
                }
            },
            "voice": {
                "tts": {
                    "engine": "edge_tts",
                    "voice_id": "en-US-AriaNeural",
                    "voice_name": "Aria",
                    "rate": 1.0,
                    "volume": 0.9,
                    "useCache": True,
                    "available_voices": AVAILABLE_VOICES
                },
                "stt": {
                    "engine": "whisper",
                    "model": "whisper-medium",
                    "sensitivity": 0.5,
                    "language": "en-US",
                    "continuous": True
                },
                "wakeWord": {
                    "enabled": False,
                    "phrases": ["hey assistant", "hey daddy"],
                    "sensitivity": 0.5
                }
            },
            "automation": {
                "autoUpdate": True,
                "autoBackup": "daily",
                "maxHistorySize": 1000,
                "smartHome": {
                    "enabled": False,
                    "provider": "none"
                }
            },
            "system": {
                "logLevel": "INFO",
                "maxLogSizeMb": 100,
                "minimizeToTray": True,
                "notifications": {
                    "desktop": True,
                    "sound": True
                }
            }
        }
        
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                saved_settings = json.load(f)
            
            # Wipe actual plain text keys from the JSON file if any were saved historically
            if "security" in saved_settings and "apiKeys" in saved_settings["security"]:
                saved_keys = saved_settings["security"]["apiKeys"]
                needs_rewrite = False
                for k, v in list(saved_keys.items()):
                    if v and v != "********":
                        # Move to keyring and remove from JSON
                        save_secure_key(k, v)
                        saved_keys[k] = "********"
                        needs_rewrite = True
                if needs_rewrite:
                    saved_settings["security"]["apiKeys"] = saved_keys
                    with open(settings_file, 'w', encoding='utf-8') as f:
                        json.dump(saved_settings, f, indent=2)

            # Deep merge: saved settings override defaults
            for key, value in saved_settings.items():
                if key in defaults and isinstance(defaults[key], dict) and isinstance(value, dict):
                    defaults[key].update(value)
                else:
                    defaults[key] = value
                    
            # ALWAYS override dynamically populated lists with system constants
            if "voice" in defaults and "tts" in defaults["voice"]:
                defaults["voice"]["tts"]["available_voices"] = AVAILABLE_VOICES
                print(f"[DEBUG api_get_all_settings] Merged available_voices length: {len(AVAILABLE_VOICES)}, first item: {AVAILABLE_VOICES[0]['name']}")
                
            settings = defaults
        else:
            settings = defaults
            # Save defaults on first load
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        
        return jsonify({"success": True, "settings": settings})
    
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@settings_bp.route('/api/settings/update', methods=['POST'])
@jwt_required(optional=True)
def api_update_settings():
    """Update specific settings with live hot-reload of critical values"""
    try:
        data = request.get_json()
        category = data.get('category')
        settings_data = data.get('settings')
        
        if not category or not settings_data:
            return jsonify({"success": False, "error": "Category and settings required"}), 400
        
        settings_file = Path(__file__).parent.parent.parent / 'data' / 'user_preferences' / 'settings.json'
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing settings
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                all_settings = json.load(f)
        else:
            all_settings = {}
        
        # === SECURE STORAGE INTERCEPT FOR API KEYS ===
        if category == 'security':
            from ai_assistant.utils.secure_storage import save_secure_key, delete_secure_key, get_secure_key
            api_keys = settings_data.get('apiKeys', {})
            
            # Map frontend settings keys to actual OS env names we hot-reload
            env_map = {
                "googleGemini": "GEMINI_API_KEY",
                "openAI": "OPENAI_API_KEY",
                "elevenLabs": "ELEVEN_LABS_API_KEY"
            }
            
            for key_name, key_val in list(api_keys.items()):
                if key_val == "********":
                    # Keep existing key in keyring, and load it to os.environ for hot-reload
                    actual_val = get_secure_key(key_name)
                    if actual_val and key_name in env_map:
                        os.environ[env_map[key_name]] = actual_val
                elif key_val == "":
                    # Delete key from keyring and clear from os.environ
                    delete_secure_key(key_name)
                    if key_name in env_map and env_map[key_name] in os.environ:
                        del os.environ[env_map[key_name]]
                else:
                    # Save new key to keyring and load it to os.environ
                    save_secure_key(key_name, key_val)
                    if key_name in env_map:
                        os.environ[env_map[key_name]] = key_val
                        logger.info(f"Ã°Å¸â€â€˜ Secure Key '{key_name}' updated & loaded at runtime")
            
            # Wipe actual values from settings_data before writing to JSON file
            cleaned_keys = {}
            for key_name in api_keys.keys():
                cleaned_keys[key_name] = "********" if get_secure_key(key_name) else ""
            settings_data['apiKeys'] = cleaned_keys
            
        # Update category in all_settings
        all_settings[category] = settings_data
        
        # Save JSON with masked values
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(all_settings, f, indent=2)
        
        if category == 'ai':
            provider = settings_data.get('defaultProvider')
            model = settings_data.get('defaultModel')
            if provider or model:
                logger.info(f"🤖 AI provider updated: {provider}, model: {model}")
                if provider == 'openai' and model:
                    os.environ["OPENAI_MODEL"] = model
                # Invalidate cached AI settings in chat handlers
                try:
                    import voice_service as chat_handlers
                    chat_handlers._ai_settings_mtime = 0  # Force cache invalidation
                except Exception:
                    pass
        
        # Hot-reload global LLM config if AI or Security settings change
        if category in ['ai', 'security']:
            try:
                from ai_assistant.ai.network_aware_llm import reload_global_config
                reload_global_config()
                logger.info("Global LLM config hot-reloaded due to settings change")
            except Exception as e:
                logger.warning(f"Could not hot-reload global LLM config: {e}")
        
        # Broadcast change to all connected clients via socket
        try:
            socketio.emit('settings_updated', {
                'category': category,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.warning(f"Could not broadcast settings_updated: {e}")
        
        return jsonify({
            "success": True,
            "message": f"{category.capitalize()} settings updated",
            "settings": all_settings
        })
    
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@settings_bp.route('/api/settings/reset', methods=['POST'])
@jwt_required(optional=True)
def api_reset_settings():
    """Reset settings to default"""
    try:
        data = request.get_json()
        category = data.get('category')  # Optional: reset specific category
        
        settings_file = Path(__file__).parent.parent.parent / 'data' / 'user_preferences' / 'settings.json'
        
        if category:
            # Reset specific category
            if settings_file.exists():
                with open(settings_file, 'r', encoding='utf-8') as f:
                    all_settings = json.load(f)
            else:
                all_settings = {}
            
            # Remove category
            if category in all_settings:
                del all_settings[category]
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(all_settings, f, indent=2)
            
            return jsonify({"success": True, "message": f"{category.capitalize()} settings reset"})
        else:
            # Reset all settings
            if settings_file.exists():
                settings_file.unlink()
            
            return jsonify({"success": True, "message": "All settings reset to default"})
    
    except Exception as e:
        logger.error(f"Failed to reset settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@settings_bp.route('/api/settings/export', methods=['GET'])
def api_export_settings():
    """Export settings as JSON"""
    try:
        settings_file = Path(__file__).parent.parent.parent / 'data' / 'user_preferences' / 'settings.json'
        
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        else:
            settings = {}
        
        return jsonify({
            "success": True,
            "data": settings,
            "exportedAt": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Failed to export settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@settings_bp.route('/api/settings/import', methods=['POST'])
def api_import_settings():
    """Import settings from JSON"""
    try:
        data = request.get_json()
        imported_settings = data.get('settings')
        
        if not imported_settings:
            return jsonify({"success": False, "error": "No settings data provided"}), 400
        
        settings_file = Path(__file__).parent.parent.parent / 'data' / 'user_preferences' / 'settings.json'
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(imported_settings, f, indent=2)
        
        return jsonify({
            "success": True,
            "message": "Settings imported successfully",
            "settings": imported_settings
        })
    
    except Exception as e:
        logger.error(f"Failed to import settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@settings_bp.route('/api/models/available', methods=['GET'])
@limiter.limit("30 per minute")
def api_get_available_models():
    """Get list of all available models with their providers"""
    try:
        models_list = []
        
        # Get models from router if available
        if ENHANCED_AI_AVAILABLE and enhanced_ai and enhanced_ai.router:
            router_models = enhanced_ai.router.models
            for model in router_models:
                models_list.append({
                    'id': model.name,
                    'name': model.name,
                    'provider': model.tier.value,
                    'tier': model.tier.value,
                    'max_tokens': model.max_tokens,
                    'cost_per_1k_tokens': model.cost_per_1k_tokens,
                    'avg_latency_ms': model.avg_latency_ms,
                    'capabilities': model.capabilities,
                    'priority': model.priority
                })
        else:
            # Fallback: provide default model list
            models_list = [
                {
                    'id': 'gemini-2.0-flash-exp',
                    'name': 'Gemini 2.0 Flash',
                    'provider': 'Google',
                    'tier': 'fast',
                    'max_tokens': 8192,
                    'cost_per_1k_tokens': 0.0001,
                    'avg_latency_ms': 500,
                    'capabilities': ['general', 'multimodal', 'coding'],
                    'priority': 10,
                    'description': 'Fast, cost-effective model for general queries'
                },
                {
                    'id': 'gpt-3.5-turbo',
                    'name': 'GPT-3.5 Turbo',
                    'provider': 'OpenAI',
                    'tier': 'standard',
                    'max_tokens': 4096,
                    'cost_per_1k_tokens': 0.002,
                    'avg_latency_ms': 1000,
                    'capabilities': ['general', 'coding', 'reasoning'],
                    'priority': 5,
                    'description': 'Balanced model for medium complexity tasks'
                },
                {
                    'id': 'gpt-4-turbo',
                    'name': 'GPT-4 Turbo',
                    'provider': 'OpenAI',
                    'tier': 'advanced',
                    'max_tokens': 8192,
                    'cost_per_1k_tokens': 0.03,
                    'avg_latency_ms': 3000,
                    'capabilities': ['general', 'coding', 'reasoning', 'creativity', 'math'],
                    'priority': 1,
                    'description': 'Most capable model for complex tasks'
                },
                {
                    'id': 'gemini-2.0-pro',
                    'name': 'Gemini 2.0 Pro',
                    'provider': 'Google',
                    'tier': 'advanced',
                    'max_tokens': 32768,
                    'cost_per_1k_tokens': 0.0025,
                    'avg_latency_ms': 2000,
                    'capabilities': ['general', 'multimodal', 'reasoning', 'coding'],
                    'priority': 2,
                    'description': 'Advanced multimodal model with large context'
                }
            ]
        
        # Group by provider
        by_provider = {}
        for model in models_list:
            provider = model.get('provider', 'Unknown')
            if provider not in by_provider:
                by_provider[provider] = []
            by_provider[provider].append(model)
        
        return jsonify({
            'success': True,
            'models': models_list,
            'by_provider': by_provider,
            'total_models': len(models_list),
            'providers': list(by_provider.keys()),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Get available models error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@settings_bp.route('/api/models/preference', methods=['GET'])
@jwt_required(optional=True)
def api_get_model_preference():
    """Get user's preferred model"""
    try:
        current_user = get_jwt_identity() or "anonymous"
        
        # Load preferences from file
        prefs_file = Path('data') / 'user_preferences' / f'{current_user}_model_pref.json'
        
        if prefs_file.exists():
            with open(prefs_file, 'r') as f:
                preference = json.load(f)
        else:
            # Default preference
            preference = {
                'preferred_model': 'gemini-2.0-flash-exp',
                'auto_route': True,
                'fallback_model': 'gpt-3.5-turbo',
                'max_cost_per_query': 0.01
            }
        
        return jsonify({
            'success': True,
            'preference': preference,
            'user': current_user,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Get model preference error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@settings_bp.route('/api/models/preference', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_set_model_preference():
    """Set user's preferred model"""
    try:
        current_user = get_jwt_identity() or "anonymous"
        data = request.get_json()
        
        preferred_model = data.get('preferred_model')
        auto_route = data.get('auto_route', True)
        fallback_model = data.get('fallback_model')
        max_cost_per_query = data.get('max_cost_per_query', 0.01)
        
        if not preferred_model:
            return jsonify({'success': False, 'error': 'preferred_model is required'}), 400
        
        # Save preference
        preference = {
            'preferred_model': preferred_model,
            'auto_route': auto_route,
            'fallback_model': fallback_model or 'gpt-3.5-turbo',
            'max_cost_per_query': max_cost_per_query,
            'updated_at': datetime.now().isoformat()
        }
        
        prefs_dir = Path('data') / 'user_preferences'
        prefs_dir.mkdir(parents=True, exist_ok=True)
        
        prefs_file = prefs_dir / f'{current_user}_model_pref.json'
        with open(prefs_file, 'w') as f:
            json.dump(preference, f, indent=2)
        
        logger.info(f"User {current_user} set preferred model to {preferred_model}")
        
        return jsonify({
            'success': True,
            'preference': preference,
            'message': f'Model preference saved: {preferred_model}',
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Set model preference error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@settings_bp.route('/api/models/stats', methods=['GET'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_get_model_stats():
    """Get usage statistics for each model"""
    try:
        current_user = get_jwt_identity() or "anonymous"
        
        stats = {}
        
        # Get stats from router if available
        if ENHANCED_AI_AVAILABLE and enhanced_ai and enhanced_ai.router:
            router_stats = enhanced_ai.router.get_stats()
            stats['routing'] = router_stats
        
        # Get stats from enhanced AI
        if ENHANCED_AI_AVAILABLE and enhanced_ai:
            ai_stats = enhanced_ai.get_stats()
            stats['enhanced_ai'] = ai_stats
        
        return jsonify({
            'success': True,
            'stats': stats,
            'user': current_user,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Get model stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@settings_bp.route('/api/models/compare', methods=['POST'])
@limiter.limit("20 per minute")
def api_compare_models():
    """Compare multiple models side by side"""
    try:
        data = request.get_json()
        model_ids = data.get('model_ids', [])
        
        if not model_ids or len(model_ids) < 2:
            return jsonify({'success': False, 'error': 'At least 2 model IDs required'}), 400
        
        # Get model details
        comparison = []
        
        if ENHANCED_AI_AVAILABLE and enhanced_ai and enhanced_ai.router:
            for model_id in model_ids:
                model = next((m for m in enhanced_ai.router.models if m.name == model_id), None)
                if model:
                    comparison.append({
                        'id': model.name,
                        'name': model.name,
                        'tier': model.tier.value,
                        'cost_per_1k_tokens': model.cost_per_1k_tokens,
                        'max_tokens': model.max_tokens,
                        'avg_latency_ms': model.avg_latency_ms,
                        'capabilities': model.capabilities
                    })
        
        return jsonify({
            'success': True,
            'comparison': comparison,
            'model_count': len(comparison),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Compare models error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@settings_bp.route('/api/models/providers', methods=['GET'])
@limiter.limit("30 per minute")
def api_get_providers():
    """Get list of all available LLM providers"""
    try:
        providers = [
            {
                'id': 'google',
                'name': 'Google',
                'description': 'Google Gemini models',
                'models': ['gemini-2.0-flash-exp', 'gemini-2.0-pro', 'gemini-1.5-pro'],
                'features': ['multimodal', 'fast', 'cost-effective'],
                'api_key_required': True,
                'status': 'active'
            },
            {
                'id': 'openai',
                'name': 'OpenAI',
                'description': 'GPT models from OpenAI',
                'models': ['gpt-3.5-turbo', 'gpt-4-turbo', 'gpt-4o'],
                'features': ['versatile', 'powerful', 'coding'],
                'api_key_required': True,
                'status': 'active'
            }
        ]
        
        return jsonify({
            'success': True,
            'providers': providers,
            'total_providers': len(providers),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Get providers error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500