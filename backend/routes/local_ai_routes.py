import os
import time
from pathlib import Path
from datetime import datetime
from flask import Blueprint, jsonify, request
from .common import logger, limiter, BACKGROUND_INIT, jwt_required

local_ai_bp = Blueprint('local_ai', __name__)

# State variables for local AI
local_ai_manager = None
local_ai_initialized = False

try:
    from ai_assistant.ai.local_ai_manager import LocalAIManager
    LOCAL_AI_AVAILABLE = True
except ImportError:
    LOCAL_AI_AVAILABLE = False
    LocalAIManager = None

def _log_api(endpoint, method, request_data=None):
    try:
        from utils.session_activity_logger import log_api_request
        log_api_request(endpoint=endpoint, method=method, user_id='default', request_data=request_data)
    except Exception:
        pass

@local_ai_bp.route('/api/local-ai/status', methods=['GET'])
@limiter.limit("10 per minute")
def api_local_ai_status():
    """Get local AI initialization status for debugging"""
    try:
        return jsonify({
            "success": True,
            "local_ai_available": LOCAL_AI_AVAILABLE,
            "local_ai_initialized": local_ai_initialized,
            "local_ai_manager_loaded": local_ai_manager is not None,
            "current_model": local_ai_manager.current_model if local_ai_manager else None,
            "background_init_enabled": BACKGROUND_INIT,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@local_ai_bp.route('/api/local_ai/status', methods=['GET'])
@limiter.limit("30 per minute")
def local_ai_status():
    """Get local AI status and info"""
    try:
        if not LOCAL_AI_AVAILABLE:
            return jsonify({
                'success': True,
                'available': False,
                'message': 'Local AI not installed. Run: pip install llama-cpp-python'
            })
        
        status = {
            'success': True,
            'available': True,
            'initialized': local_ai_initialized,
            'model_loaded': local_ai_manager is not None and getattr(local_ai_manager, 'current_model', None) is not None
        }
        
        if local_ai_initialized and local_ai_manager:
            status['model_info'] = {
                'name': local_ai_manager.model_config.name if getattr(local_ai_manager, 'model_config', None) else None,
                'context_length': local_ai_manager.model_config.context_length if getattr(local_ai_manager, 'model_config', None) else None,
                'threads': local_ai_manager.model_config.threads if getattr(local_ai_manager, 'model_config', None) else None
            }
            status['stats'] = local_ai_manager.get_stats() if hasattr(local_ai_manager, 'get_stats') else {}
        else:
            status['message'] = 'No model loaded. Download TinyLlama or Qwen2 model.'
        
        return jsonify(status)
    
    except Exception as e:
        logger.error(f"Local AI status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@local_ai_bp.route('/api/local_ai/chat', methods=['POST'])
@limiter.limit("20 per minute")
def local_ai_chat():
    """Chat with local AI model"""
    try:
        if not local_ai_initialized or not local_ai_manager:
            return jsonify({
                'success': False,
                'error': 'Local AI not initialized. Check /api/local_ai/status'
            }), 503
        
        data = request.json or {}
        message = data.get('message', '')
        max_tokens = data.get('max_tokens', 512)
        temperature = data.get('temperature', 0.7)
        use_history = data.get('use_history', True)
        
        if not message:
            return jsonify({'success': False, 'error': 'No message provided'}), 400
        
        _log_api('/api/local_ai/chat', 'POST', {'message_length': len(message)})
        
        start_time = time.time()
        
        if use_history:
            response = local_ai_manager.chat(message, max_tokens=max_tokens)
        else:
            response = local_ai_manager.generate(
                message,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False
            )
        
        elapsed = time.time() - start_time
        
        return jsonify({
            'success': True,
            'response': response,
            'stats': {
                'elapsed_time': round(elapsed, 2),
                'avg_tokens_per_sec': getattr(local_ai_manager, 'stats', {}).get('avg_tokens_per_sec', 0) if hasattr(local_ai_manager, 'stats') else 0,
                'total_queries': getattr(local_ai_manager, 'stats', {}).get('total_queries', 0) if hasattr(local_ai_manager, 'stats') else 0
            },
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Local AI chat error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@local_ai_bp.route('/api/local_ai/reset', methods=['POST'])
@limiter.limit("10 per minute")
def local_ai_reset():
    """Reset local AI conversation history"""
    try:
        if not local_ai_initialized or not local_ai_manager:
            return jsonify({
                'success': False,
                'error': 'Local AI not initialized'
            }), 503
        
        local_ai_manager.clear_history()
        
        return jsonify({
            'success': True,
            'message': 'Conversation history cleared'
        })
    
    except Exception as e:
        logger.error(f"Local AI reset error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@local_ai_bp.route('/api/local_ai/stats', methods=['GET'])
@limiter.limit("30 per minute")
def local_ai_stats():
    """Get local AI performance statistics"""
    try:
        if not local_ai_initialized or not local_ai_manager:
            return jsonify({
                'success': False,
                'error': 'Local AI not initialized'
            }), 503
        
        stats = local_ai_manager.get_stats() if hasattr(local_ai_manager, 'get_stats') else {}
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Local AI stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@local_ai_bp.route('/api/local_ai/load_model', methods=['POST'])
@limiter.limit("5 per minute")
def local_ai_load_model():
    """Load a specific local model"""
    global local_ai_manager, local_ai_initialized
    
    try:
        if not LOCAL_AI_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'Local AI not available. Install llama-cpp-python'
            }), 503
        
        data = request.json or {}
        model_name = data.get('model_name', 'tinyllama')
        threads = data.get('threads', 4)
        
        if not local_ai_manager:
            local_ai_manager = LocalAIManager()
        
        model_paths = {
            'tinyllama': 'model/local_models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf',
            'qwen2': 'model/local_models/qwen2-0_5b-instruct-q4_k_m.gguf'
        }
        
        model_path = model_paths.get(model_name)
        if not model_path:
            return jsonify({
                'success': False,
                'error': f'Unknown model: {model_name}. Choose from: {list(model_paths.keys())}'
            }), 400
        
        if not Path(model_path).exists():
            return jsonify({
                'success': False,
                'error': f'Model file not found: {model_path}',
                'download_instructions': 'Run: huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf --local-dir model/local_models'
            }), 404
        
        if local_ai_manager.load_model(str(model_path), threads=threads):
            local_ai_initialized = True
            return jsonify({
                'success': True,
                'message': f'Model {model_name} loaded successfully',
                'model_info': {
                    'name': local_ai_manager.model_config.name if getattr(local_ai_manager, 'model_config', None) else model_name,
                    'path': str(model_path),
                    'threads': threads
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to load model'
            }), 500
    
    except Exception as e:
        logger.error(f"Local AI load model error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@local_ai_bp.route('/api/local_ai/unload', methods=['POST'])
@limiter.limit("10 per minute")
def local_ai_unload():
    """Unload local AI model from memory"""
    global local_ai_initialized
    
    try:
        if local_ai_manager:
            local_ai_manager.unload_model()
            local_ai_initialized = False
            
            return jsonify({
                'success': True,
                'message': 'Model unloaded from memory'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No model loaded'
            }), 400
    
    except Exception as e:
        logger.error(f"Local AI unload error: {e}")