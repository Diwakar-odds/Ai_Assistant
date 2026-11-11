import time
from datetime import datetime
from flask import Blueprint, jsonify, request
from .common import logger, limiter, BACKGROUND_INIT

local_ai_bp = Blueprint('local_ai', __name__)

try:
    from ai_assistant.ai.gguf_model_manager import get_gguf_manager, llama_cpp_available
    GGUF_AVAILABLE = bool(llama_cpp_available())
except Exception:
    get_gguf_manager = None
    GGUF_AVAILABLE = False

try:
    from settings_manager import discover_gguf_models, get_provider, get_model, reset_all_llm_sessions
except Exception:
    discover_gguf_models = lambda: []  # type: ignore
    get_provider = lambda: 'gguf'  # type: ignore
    get_model = lambda: 'pulsar-final-q4_k_m'  # type: ignore
    reset_all_llm_sessions = lambda: None  # type: ignore


def _get_gguf_status() -> dict:
    discovered = []
    try:
        discovered = list(discover_gguf_models() or [])
    except Exception:
        discovered = []
    status = {
        'available': GGUF_AVAILABLE,
        'loaded': False,
        'loaded_model': None,
        'available_models': discovered,
    }
    if get_gguf_manager is not None:
        try:
            mgr = get_gguf_manager()
            st = mgr.get_status() if hasattr(mgr, 'get_status') else {}
            status.update(st)
            # Normalize available_models -> discovered stems for frontend consistency
            if discovered:
                status['available_models'] = discovered
            elif isinstance(st.get('available_models'), list):
                status['available_models'] = [
                    (m.get('id') if isinstance(m, dict) else str(m))
                    for m in st.get('available_models', [])
                ]
        except Exception as e:
            status['error'] = str(e)
    return status


def _log_api(endpoint, method, request_data=None):
    try:
        from utils.session_activity_logger import log_api_request
        log_api_request(endpoint=endpoint, method=method, user_id='default', request_data=request_data)
    except Exception:
        pass


@local_ai_bp.route('/api/local-ai/status', methods=['GET'])
@limiter.limit("30 per minute")
def api_local_ai_status():
    """Get local AI (GGUF) initialization status."""
    try:
        gguf_st = _get_gguf_status()
        active_prov = (get_provider() or 'gguf').lower()
        return jsonify({
            "success": True,
            "active_provider": active_prov,
            "active_model": get_model(),
            "local_ai_available": bool(gguf_st.get('available')),
            "local_ai_initialized": bool(gguf_st.get('loaded')),
            "gguf_loaded": bool(gguf_st.get('loaded')),
            "current_model": gguf_st.get('loaded_model'),
            "gguf": gguf_st,
            "available_gguf_models": gguf_st.get('available_models', []),
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
    """Get local AI (GGUF) status and info."""
    try:
        gguf_st = _get_gguf_status()
        if not gguf_st.get('available'):
            return jsonify({
                'success': True,
                'available': False,
                'gguf': gguf_st,
                'available_gguf_models': gguf_st.get('available_models', []),
                'message': 'Local GGUF runtime not available. Install llama-cpp-python.'
            })

        active_model_name = gguf_st.get('loaded_model')
        status = {
            'success': True,
            'available': True,
            'initialized': bool(gguf_st.get('loaded')),
            'model_loaded': bool(gguf_st.get('loaded')),
            'current_model': active_model_name,
            'available_gguf_models': gguf_st.get('available_models', []),
            'gguf': gguf_st,
        }

        if gguf_st.get('loaded'):
            status['model_info'] = {
                'provider': 'gguf',
                'name': active_model_name,
                'path': gguf_st.get('loaded_path'),
                'n_ctx': gguf_st.get('n_ctx'),
                'n_gpu_layers': gguf_st.get('n_gpu_layers'),
            }
        else:
            status['message'] = (
                f"Ready. Available GGUF models: {gguf_st.get('available_models', [])}"
                if gguf_st.get('available_models')
                else 'No local GGUF model found in models directory.'
            )

        return jsonify(status)

    except Exception as e:
        logger.error(f"Local AI status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@local_ai_bp.route('/api/local_ai/chat', methods=['POST'])
@limiter.limit("20 per minute")
def local_ai_chat():
    """Chat directly with local GGUF model."""
    try:
        data = request.json or {}
        message = data.get('message', '')
        max_tokens = int(data.get('max_tokens', 512))
        temperature = float(data.get('temperature', 0.7))
        req_model = data.get('model')

        if not message:
            return jsonify({'success': False, 'error': 'No message provided'}), 400

        _log_api('/api/local_ai/chat', 'POST', {'message_length': len(message)})

        if not GGUF_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'Local GGUF runtime (llama-cpp-python) is not available. Check /api/local_ai/status'
            }), 503

        gguf_st = _get_gguf_status()
        from ai_assistant.ai.llm_provider import GGUFProvider, LLMFactory

        raw_target = req_model or gguf_st.get('loaded_model') or (
            get_model() if (get_provider() or '').lower() == 'gguf' else 'pulsar-final-q4_k_m'
        )
        target_model = LLMFactory.sanitize_model_for_provider('gguf', raw_target)

        start_time = time.time()
        gguf = GGUFProvider(model=target_model)
        msgs = [
            {"role": "system", "content": "You are Pulsar, a smart, concise AI assistant created by Diwakar."},
            {"role": "user", "content": message},
        ]
        response = gguf.generate_response(msgs, temperature=temperature, max_tokens=max_tokens)
        elapsed = time.time() - start_time
        if str(response).strip().startswith("Error:"):
            return jsonify({'success': False, 'error': response, 'provider': 'gguf', 'model': target_model}), 503

        return jsonify({
            'success': True,
            'response': response,
            'provider': 'gguf',
            'model': target_model,
            'stats': {'elapsed_time': round(elapsed, 2)},
            'timestamp': datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Local AI chat error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@local_ai_bp.route('/api/local_ai/reset', methods=['POST'])
@limiter.limit("10 per minute")
def local_ai_reset():
    """Reset local AI conversation history."""
    try:
        reset_all_llm_sessions()
        return jsonify({
            'success': True,
            'message': 'Local AI conversation history cleared'
        })
    except Exception as e:
        logger.error(f"Local AI reset error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@local_ai_bp.route('/api/local_ai/stats', methods=['GET'])
@limiter.limit("30 per minute")
def local_ai_stats():
    """Get local AI performance statistics."""
    try:
        gguf_st = _get_gguf_status()
        return jsonify({
            'success': True,
            'stats': {'gguf': gguf_st, **gguf_st},
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Local AI stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@local_ai_bp.route('/api/local_ai/load_model', methods=['POST'])
@limiter.limit("10 per minute")
def local_ai_load_model():
    """Load a specific local GGUF model."""
    try:
        data = request.json or {}
        raw_name = str(data.get('model_name') or data.get('model') or 'pulsar-final-q4_k_m').strip()
        from ai_assistant.ai.llm_provider import LLMFactory
        model_name = LLMFactory.sanitize_model_for_provider('gguf', raw_name)

        if not GGUF_AVAILABLE or get_gguf_manager is None:
            return jsonify({
                'success': False,
                'error': 'llama-cpp-python is not available for GGUF loading'
            }), 503

        mgr = get_gguf_manager()
        mgr.get_model(model_name)
        st = mgr.get_status()
        return jsonify({
            'success': True,
            'message': f"GGUF model '{st.get('loaded_model') or model_name}' loaded successfully",
            'provider': 'gguf',
            'model_info': st,
        })

    except FileNotFoundError as fnf:
        return jsonify({'success': False, 'error': str(fnf)}), 404
    except Exception as e:
        logger.error(f"Local AI load model error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@local_ai_bp.route('/api/local_ai/unload', methods=['POST'])
@limiter.limit("10 per minute")
def local_ai_unload():
    """Unload local GGUF model from memory."""
    try:
        unloaded = []
        if get_gguf_manager is not None:
            try:
                mgr = get_gguf_manager()
                if mgr.is_loaded():
                    mgr.unload_model()
                    unloaded.append('gguf')
            except Exception as ge:
                logger.warning(f"GGUF unload warning: {ge}")

        if unloaded:
            return jsonify({
                'success': True,
                'unloaded': unloaded,
                'message': f"Model unloaded from memory ({', '.join(unloaded)})"
            })
        return jsonify({
            'success': False,
            'error': 'No model loaded'
        }), 400

    except Exception as e:
        logger.error(f"Local AI unload error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500