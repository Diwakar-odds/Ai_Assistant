from flask import Blueprint, jsonify, request, send_from_directory, render_template, Response, stream_with_context
import os, json, sys, time
from datetime import datetime, date
from pathlib import Path
from settings_manager import (
    DEFAULTS, invalidate_cache, AVAILABLE_PROVIDERS,
    deep_merge_settings, build_merged_settings,
    update_settings_and_sync, reset_all_llm_sessions,
    get_settings_file, get_logs_root, complete_onboarding_settings,
)
try:
    from ai_assistant.utils.multilingual import Language
except Exception:
    Language = None
# from ai_assistant.multilingual import Language
from .common import (
    logger, api_logger, limiter, assistant, validate_input, sanitize_command,
    get_current_context, jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request,
    ENABLE_VOICE, ENABLE_MULTIMODAL, ENABLE_CONVERSATIONAL_AI, get_socketio
)

try:
    from ai_assistant.core.enhanced_integration import get_enhanced_ai
    enhanced_ai = get_enhanced_ai()
    ENHANCED_AI_AVAILABLE = enhanced_ai is not None
except Exception:
    enhanced_ai = None
    ENHANCED_AI_AVAILABLE = False

try:
    from backend.voice_service import AVAILABLE_VOICES
except ImportError:
    try:
        from voice_service import AVAILABLE_VOICES
    except ImportError:
        AVAILABLE_VOICES = []

settings_bp = Blueprint('settings', __name__)
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
        
        from ai_assistant.utils.multilingual import Language
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
        
        # Save to proper error log file in writable logs directory
        log_file = get_logs_root() / 'errors' / 'frontend_errors.json'
        log_file.parent.mkdir(parents=True, exist_ok=True)
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
        settings_file = get_settings_file()
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=2)
        invalidate_cache()
        return jsonify({"success": True, "message": "Settings saved successfully"})
    
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@settings_bp.route('/api/settings/load')
def api_load_settings():
    """Load user settings"""
    try:
        settings_file = get_settings_file()
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            return jsonify(settings)
        else:
            return jsonify({"settings": None})
    
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

_deep_merge_settings = deep_merge_settings


def _build_merged_settings(saved_settings: dict) -> dict:
    return build_merged_settings(saved_settings, AVAILABLE_VOICES)


@settings_bp.route('/api/settings/all', methods=['GET'])
def api_get_all_settings():
    """Get all comprehensive settings - schema must match frontend SettingsDetail.tsx"""
    try:
        settings_file = get_settings_file()
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load secure keys
        from ai_assistant.utils.secure_storage import get_secure_key, save_secure_key
        
        google_gemini_key = get_secure_key('googleGemini')
        open_ai_key = get_secure_key('openAI')
        eleven_labs_key = get_secure_key('elevenLabs')
        
        # Backward compatibility / Migration:
        # If keyring is empty but environment variables are set, migrate them to keyring
        env_gemini = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_GEMINI_API_KEY')
        if not google_gemini_key and env_gemini:
            google_gemini_key = env_gemini
            save_secure_key('googleGemini', google_gemini_key)
        if not open_ai_key and os.getenv('OPENAI_API_KEY'):
            open_ai_key = os.getenv('OPENAI_API_KEY', '')
            save_secure_key('openAI', open_ai_key)
        if not eleven_labs_key and os.getenv('ELEVEN_LABS_API_KEY'):
            eleven_labs_key = os.getenv('ELEVEN_LABS_API_KEY', '')
            save_secure_key('elevenLabs', eleven_labs_key)
            
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

            settings = _build_merged_settings(saved_settings)
        else:
            settings = _build_merged_settings({})
            # Save defaults on first load
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
            settings = _build_merged_settings(settings)
        
        return jsonify({"success": True, "settings": settings})
    
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@settings_bp.route('/api/settings/update', methods=['POST'])
@jwt_required(optional=True)
def api_update_settings():
    """Update specific settings via single settings_manager pipeline with live sync."""
    try:
        data = request.get_json() or {}
        category = data.get('category')
        settings_data = data.get('settings')

        if not category or not settings_data:
            return jsonify({"success": False, "error": "Category and settings required"}), 400

        result = update_settings_and_sync(category, settings_data)
        if not result.get("success"):
            return jsonify(result), 400

        return jsonify({
            "success": True,
            "message": result.get("message", f"{category.capitalize()} settings updated"),
            "settings": result["settings"]
        })

    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route('/api/settings/complete_onboarding', methods=['POST'])
@jwt_required(optional=True)
def api_complete_onboarding():
    """Complete first-run onboarding and persist initial user choices."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        result = complete_onboarding_settings(data)
        return jsonify(result), (200 if result.get("success") else 400)
    except Exception as e:
        logger.error(f"Failed to complete onboarding: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@settings_bp.route('/api/settings/reset', methods=['POST'])
@jwt_required(optional=True)
def api_reset_settings():
    """Reset settings to default"""
    try:
        data = request.get_json() or {}
        category = data.get('category')  # Optional: reset specific category
        
        settings_file = get_settings_file()
        
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
            
            try:
                invalidate_cache()
                reset_all_llm_sessions()
                from ai_assistant.ai.network_aware_llm import reload_global_config
                reload_global_config()
            except Exception:
                pass

            merged_settings = _build_merged_settings(all_settings)
            try:
                sio = get_socketio()
                if sio:
                    sio.emit('settings_updated', {
                        'category': category,
                        'settings': merged_settings.get(category, {}),
                        'all_settings': merged_settings,
                        'timestamp': datetime.now().isoformat(),
                    })
            except Exception:
                pass
            return jsonify({
                "success": True,
                "message": f"{category.capitalize()} settings reset",
                "settings": merged_settings
            })
        else:
            # Reset all settings
            if settings_file.exists():
                settings_file.unlink()
            try:
                invalidate_cache()
                reset_all_llm_sessions()
                from ai_assistant.ai.network_aware_llm import reload_global_config
                reload_global_config()
            except Exception:
                pass

            merged_settings = _build_merged_settings({})
            try:
                sio = get_socketio()
                if sio:
                    sio.emit('settings_updated', {
                        'category': 'all',
                        'settings': merged_settings,
                        'all_settings': merged_settings,
                        'timestamp': datetime.now().isoformat(),
                    })
            except Exception:
                pass
            
            return jsonify({
                "success": True,
                "message": "All settings reset to default",
                "settings": merged_settings
            })
    
    except Exception as e:
        logger.error(f"Failed to reset settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@settings_bp.route('/api/settings/export', methods=['GET'])
def api_export_settings():
    """Export settings as JSON"""
    try:
        settings_file = get_settings_file()
        
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
        
        settings_file = get_settings_file()
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(imported_settings, f, indent=2)

        try:
            invalidate_cache()
            reset_all_llm_sessions()
            from ai_assistant.ai.network_aware_llm import reload_global_config
            reload_global_config()
        except Exception:
            pass

        merged_settings = _build_merged_settings(imported_settings)
        try:
            sio = get_socketio()
            if sio:
                sio.emit('settings_updated', {
                    'category': 'all',
                    'settings': merged_settings,
                    'all_settings': merged_settings,
                    'timestamp': datetime.now().isoformat(),
                })
        except Exception:
            pass
        
        return jsonify({
            "success": True,
            "message": "Settings imported successfully",
            "settings": merged_settings
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
        prefs_file = get_settings_file().parent / f'{current_user}_model_pref.json'
        
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
        
        prefs_dir = get_settings_file().parent
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
@settings_bp.route('/api/providers', methods=['GET'])
@limiter.limit("30 per minute")
def api_get_providers():
    """Get list of all available LLM providers"""
    try:
        providers = AVAILABLE_PROVIDERS
        
        return jsonify({
            'success': True,
            'providers': providers,
            'total_providers': len(providers),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Get providers error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Storage & Cache Maintenance Endpoints
# ============================================================================

@settings_bp.route('/api/settings/clean_voice_cache', methods=['POST', 'OPTIONS'])
@jwt_required(optional=True)
def api_clean_voice_cache():
    """Delete synthesized voice cache audio files (.mp3, .wav, .cache) to free disk space."""
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        from settings_manager import get_writable_root, get_bundle_root

        target_dirs = set()
        for base in [
            get_writable_root() / 'data' / 'voice_cache',
            get_bundle_root() / 'data' / 'voice_cache',
            Path(__file__).resolve().parent.parent / 'data' / 'voice_cache',
            Path(__file__).resolve().parent.parent.parent / 'data' / 'voice_cache',
            Path(__file__).resolve().parent.parent.parent / 'core_ai' / 'src' / 'data' / 'voice_cache',
        ]:
            if base.exists() and base.is_dir():
                target_dirs.add(base.resolve())

        total_bytes = 0
        files_count = 0

        for d in target_dirs:
            try:
                for f in d.iterdir():
                    if f.is_file() and (f.suffix.lower() in ('.mp3', '.wav', '.ogg', '.cache', '.tmp') or 'edge_' in f.name):
                        try:
                            f_size = f.stat().st_size
                            f.unlink(missing_ok=True)
                            total_bytes += f_size
                            files_count += 1
                        except Exception as e:
                            logger.debug(f"Could not remove audio cache file {f}: {e}")
            except Exception as d_err:
                logger.debug(f"Error scanning dir {d}: {d_err}")

        # Also purge in-memory preview cache
        try:
            try:
                import voice_service
            except ImportError:
                import backend.voice_service as voice_service
            if hasattr(voice_service, 'preview_cache') and hasattr(voice_service.preview_cache, 'cache'):
                voice_service.preview_cache.cache.clear()
        except Exception:
            pass

        freed_mb = round(total_bytes / (1024 * 1024), 2)
        return jsonify({
            'success': True,
            'files_removed': files_count,
            'freed_mb': freed_mb,
            'message': f"Voice audio cache cleaned: {files_count} files removed ({freed_mb} MB freed)"
        }), 200
    except Exception as e:
        logger.error(f"Clean voice cache failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/api/settings/clean_chat_history', methods=['POST', 'OPTIONS'])
@jwt_required(optional=True)
def api_clean_chat_history():
    """Reset chat sessions and clear cached conversation context files."""
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        from settings_manager import get_writable_root, get_bundle_root

        # 1. Reset unified chat session store
        cleared_sessions = 0
        try:
            try:
                from utils.chat_session_store import get_session_store
            except ImportError:
                from backend.utils.chat_session_store import get_session_store
            store = get_session_store()
            cleared_sessions = store.clear_history()
            store.start_new_session(reason="user_storage_cleanup")
        except Exception as store_err:
            logger.warning(f"Session store reset error: {store_err}")

        # 2. Clean temporary conversation_context_*.json files
        search_dirs = set()
        for base in [
            get_writable_root() / 'data',
            get_bundle_root() / 'data',
            Path(__file__).resolve().parent.parent / 'data',
            Path(__file__).resolve().parent.parent.parent / 'data',
            Path(__file__).resolve().parent.parent / 'data' / 'sessions',
        ]:
            if base.exists() and base.is_dir():
                search_dirs.add(base.resolve())

        total_bytes = 0
        files_count = 0

        for d in search_dirs:
            try:
                for f in d.glob('conversation_context_*.json'):
                    try:
                        f_size = f.stat().st_size
                        f.unlink(missing_ok=True)
                        total_bytes += f_size
                        files_count += 1
                    except Exception as e:
                        logger.debug(f"Could not remove conversation context file {f}: {e}")
            except Exception as d_err:
                logger.debug(f"Error scanning dir {d}: {d_err}")

        freed_mb = round(total_bytes / (1024 * 1024), 2)
        return jsonify({
            'success': True,
            'sessions_cleared': cleared_sessions,
            'files_removed': files_count,
            'freed_mb': freed_mb,
            'message': f"Chat history and conversation contexts cleared ({freed_mb} MB freed)"
        }), 200
    except Exception as e:
        logger.error(f"Clean chat history failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/api/settings/clean_logs', methods=['POST', 'OPTIONS'])
@jwt_required(optional=True)
def api_clean_logs():
    """Truncate or remove log files in logs directory to recover disk space."""
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        from settings_manager import get_logs_root, get_bundle_root

        log_dirs = set()
        for base in [
            get_logs_root(),
            get_bundle_root() / 'logs',
            Path(__file__).resolve().parent.parent.parent / 'logs',
        ]:
            if base.exists() and base.is_dir():
                log_dirs.add(base.resolve())

        total_bytes = 0
        files_count = 0

        for d in log_dirs:
            try:
                for f in d.iterdir():
                    if not f.is_file():
                        continue
                    fname = f.name.lower()
                    if '.log' in fname or fname.endswith(('.old', '.bak', '.txt')):
                        try:
                            f_size = f.stat().st_size
                            # If rotated/backup log, delete file
                            if any(part in fname for part in ('.old', '.bak', '.log.')):
                                f.unlink(missing_ok=True)
                            else:
                                # For active log file, truncate to 0 bytes without breaking file handles
                                with open(f, 'w', encoding='utf-8') as truncate_target:
                                    truncate_target.write('')
                            total_bytes += f_size
                            files_count += 1
                        except Exception as e:
                            logger.debug(f"Could not clean log file {f}: {e}")
            except Exception as d_err:
                logger.debug(f"Error scanning log dir {d}: {d_err}")

        freed_mb = round(total_bytes / (1024 * 1024), 2)
        return jsonify({
            'success': True,
            'files_cleaned': files_count,
            'freed_mb': freed_mb,
            'message': f"Application logs cleaned: {files_count} files cleared ({freed_mb} MB freed)"
        }), 200
    except Exception as e:
        logger.error(f"Clean logs failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/api/voice/dictionary', methods=['GET', 'POST', 'OPTIONS'])
def api_voice_dictionary():
    """Retrieve or update user-defined phonetic vocabulary & grammar dictionary."""
    if request.method == 'OPTIONS':
        return ('', 204)

    try:
        from ai_assistant.voice.vocabulary_registry import get_vocabulary_registry
        reg = get_vocabulary_registry()

        if request.method == 'POST':
            payload = request.get_json() or {}
            updated = reg.update_dictionary_data(payload)
            sio = get_socketio()
            if sio:
                try:
                    sio.emit('dictionary_updated', updated)
                except Exception:
                    pass
            return jsonify({'success': True, 'dictionary': updated}), 200

        # GET request
        return jsonify({'success': True, 'dictionary': reg.get_dictionary_data()}), 200
    except Exception as exc:
        logger.error(f"Voice dictionary endpoint error: {exc}")
        return jsonify({'success': False, 'error': str(exc)}), 500
