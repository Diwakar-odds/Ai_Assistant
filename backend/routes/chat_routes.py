from flask import Blueprint, jsonify, request, send_from_directory, render_template, Response, stream_with_context
import os, json, sys, time, logging, threading
from datetime import datetime
from settings_manager import get_provider, get_model
from .common import (
    logger, api_logger, limiter, validate_input, sanitize_command,
    assistant, socketio, learning_router, get_current_context,
    jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request,
    ENABLE_VOICE, ENABLE_MULTIMODAL, ENABLE_CONVERSATIONAL_AI
)

try:
    from ai_assistant.core.enhanced_integration import get_enhanced_ai
    enhanced_ai = get_enhanced_ai()
    ENHANCED_AI_AVAILABLE = enhanced_ai is not None
except Exception:
    enhanced_ai = None
    ENHANCED_AI_AVAILABLE = False

try:
    from ai_assistant.ai.auto_learning_router import AutoLearningRouter
    LEARNING_ROUTER_AVAILABLE = True
except Exception:
    LEARNING_ROUTER_AVAILABLE = False

try:
    from ai_assistant.ai.usage_pattern_analyzer import UsagePatternAnalyzer
    usage_analyzer = UsagePatternAnalyzer()
    USAGE_ANALYZER_AVAILABLE = True
except Exception:
    usage_analyzer = None
    USAGE_ANALYZER_AVAILABLE = False

try:
    from ai_assistant.ai.llm_provider import UnifiedChatInterface, LLMFactory, is_local_provider
    LLM_PROVIDER_AVAILABLE = True
except Exception:
    UnifiedChatInterface = None
    LLM_PROVIDER_AVAILABLE = False

    class LLMFactory:  # type: ignore[no-redef]
        @staticmethod
        def normalize_provider(provider):
            return (provider or "gemini").strip().lower()

        @staticmethod
        def sanitize_model_for_provider(provider, model):
            return model or ""

    def is_local_provider(provider):  # type: ignore[no-redef]
        return (provider or "").strip().lower() in ("gguf", "local", "offline")

try:
    from ai_assistant.automation.automation_engine import SmartAutomationEngine
    AUTOMATION_AVAILABLE = True
except Exception:
    AUTOMATION_AVAILABLE = False

try:
    from ai_assistant.ai.memory import save_to_memory, search_memory
except Exception:
    def save_to_memory(speaker, content): return "Saved"
    def search_memory(query, limit=10): return []

chat_session_lock = threading.Lock()
chat_sessions = {}


def _get_chat_store():
    try:
        from utils.chat_session_store import get_session_store
    except ImportError:
        from backend.utils.chat_session_store import get_session_store
    return get_session_store()


def clear_chat_sessions():
    """Clear cached SSE chat sessions so subsequent requests pick up updated settings."""
    with chat_session_lock:
        chat_sessions.clear()


def _maybe_speak_http_command(data: dict, response_text: str, success: bool = True, interrupt: bool = True, intent: str = None) -> None:
    """Speak HTTP /api/command responses on the single unified backend speaker using centralized gating."""
    if not response_text:
        return
    try:
        from ai_assistant.core.jarvis_persona import should_speak_for_request
        if not should_speak_for_request(data, intent=intent, default_for_chat=False):
            return
        if not success and not (data.get('speak') or str(data.get('source', '')).lower() == 'voice'):
            return
        from ai_assistant.voice.tts_output_service import get_tts_service
        get_tts_service().speak(response_text, interrupt=interrupt, source=str(data.get('source', 'http_command')))
    except Exception:
        pass

chat_bp = Blueprint('chat', __name__)
@chat_bp.route('/api/chat', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("60 per minute")
def api_chat():
    """Enhanced chat endpoint with full AI integration and learning"""
    start_time = time.time()
    try:
        current_user = get_jwt_identity() or "anonymous"
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'message', 'command')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        message = sanitize_command(data['message'])
        raw_user_message = message
        source = str(data.get('source') or 'chat')
        context = data.get('context', {})
        image_data = data.get('image', None)
        
        if not message and not image_data:
            return jsonify({"error": "No message or image provided"}), 400

        store = _get_chat_store()
        sess_id = store.get_current_session().get('id')
        boot_id = store.get_boot_id()
        user_msg_id = str(data.get('client_message_id') or '').strip() or store.next_message_id('chat_user')
        ai_msg_id = store.next_message_id('chat_ai')
        is_voice_src = any(t in source.lower() for t in ('voice', 'companion', 'whisper', 'google'))
        if raw_user_message:
            store.record_message(
                'user',
                raw_user_message,
                source=source,
                is_voice=is_voice_src,
                message_id=user_msg_id,
                expected_session_id=sess_id,
            )

        try:
            from telemetry_tracer import telemetry
            telemetry.log_inbound(f"WEB_APP ({request.remote_addr or '127.0.0.1'})", message)
        except Exception:
            pass

        # === PRIORITY 0: Voice / Mode Control Commands (Zero LLM calls) ===
        if message and not image_data:
            try:
                from ai_assistant.core.local_command_normalizer import (
                    parse_voice_control_command,
                    execute_voice_control_command,
                )
                vc_parsed = parse_voice_control_command(message)
                if vc_parsed:
                    vc_res = execute_voice_control_command(vc_parsed)
                    vc_ok = bool(vc_res.get("success", True))
                    vc_resp = vc_res.get("response", "")
                    vc_prov = vc_res.get("provider", "local_voice_control")
                    vc_model = vc_res.get("model", get_model())
                    if vc_resp:
                        store.record_message(
                            'ai',
                            vc_resp,
                            source='local_voice_control',
                            is_voice=False,
                            message_id=ai_msg_id,
                            provider=vc_prov,
                            model=vc_model,
                            intent='voice_control',
                            success=vc_ok,
                            expected_session_id=sess_id,
                        )
                    return jsonify({
                        "success": vc_ok,
                        "message": raw_user_message,
                        "response": vc_resp,
                        "features_used": ["voice_control"],
                        "provider": vc_prov,
                        "model": vc_model,
                        "execution_meta": vc_res.get("execution_meta", {}),
                        "user": current_user,
                        "session_id": sess_id,
                        "message_id": ai_msg_id,
                        "user_message_id": user_msg_id,
                        "boot_id": boot_id,
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as vc_err:
                logger.debug(f"Voice control check skipped in api_chat: {vc_err}")

        # === NEW: Multi-step Task Chain Orchestration ===
        try:
            from ai_assistant.integrations.orchestrator_integration import should_use_orchestrator, process_with_orchestrator
            
            if should_use_orchestrator(message):
                logger.info(f" Multi-step command detected: {message}")
                orch_result = process_with_orchestrator(message, context)
                
                if orch_result['success']:
                    store.record_message(
                        'ai',
                        orch_result['response'],
                        source='multi_step_orchestration',
                        is_voice=False,
                        message_id=ai_msg_id,
                        intent='orchestrator',
                        success=True,
                        activity_kind='action',
                        activity_title='Orchestrated workflow completed',
                        expected_session_id=sess_id,
                    )
                    return jsonify({
                        "success": True,
                        "message": raw_user_message,
                        "response": orch_result['response'],
                        "orchestrated": True,
                        "steps_completed": orch_result['steps_completed'],
                        "total_steps": orch_result['total_steps'],
                        "features_used": ["multi_step_orchestration"],
                        "user": current_user,
                        "session_id": sess_id,
                        "message_id": ai_msg_id,
                        "user_message_id": user_msg_id,
                        "boot_id": boot_id,
                        "timestamp": datetime.now().isoformat()
                    })
                elif not orch_result.get('fallback'):
                    # Hard error, don't fallback
                    err_txt = orch_result.get('error', 'Multi-step execution failed')
                    store.record_message(
                        'ai',
                        err_txt,
                        source='multi_step_orchestration',
                        is_voice=False,
                        message_id=ai_msg_id,
                        intent='orchestrator',
                        success=False,
                        expected_session_id=sess_id,
                    )
                    return jsonify({
                        "error": err_txt,
                        "orchestrated": True,
                        "session_id": sess_id,
                        "message_id": ai_msg_id,
                        "user_message_id": user_msg_id,
                        "boot_id": boot_id,
                        "timestamp": datetime.now().isoformat()
                    }), 500
                else:
                    logger.warning("Orchestrator unavailable/failed, using fallback")
                    # Continue to normal processing below
        except Exception as orch_error:
            logger.warning(f"Orchestrator error, falling back: {orch_error}")
            # Continue to normal processing
        # === END: Multi-step Orchestration ===

        # Local Tier-1 fast dispatch for direct app/system commands sent over /api/chat
        if message and not image_data:
            try:
                from agent_brain import get_agent_brain
                brain = get_agent_brain()
                fast_res = brain._try_fast_dispatch(message)
                if fast_res is not None:
                    meta = fast_res.get("execution_meta", {})
                    fast_ok = bool(fast_res.get("success", True))
                    fast_resp = fast_res.get("response", "")
                    fast_prov = meta.get("provider_used", "local_fast_dispatch")
                    fast_model = meta.get("model_used", "deterministic")
                    if fast_resp:
                        store.record_message(
                            'ai',
                            fast_resp,
                            source='local_fast_dispatch',
                            is_voice=False,
                            message_id=ai_msg_id,
                            provider=fast_prov,
                            model=fast_model,
                            intent=fast_res.get("intent"),
                            success=fast_ok,
                            activity_kind=('action' if fast_ok else 'error'),
                            expected_session_id=sess_id,
                        )
                    return jsonify({
                        "success": fast_ok,
                        "message": raw_user_message,
                        "response": fast_resp,
                        "card": fast_res.get("card"),
                        "features_used": ["local_fast_dispatch"],
                        "provider": fast_prov,
                        "model": fast_model,
                        "execution_meta": meta,
                        "user": current_user,
                        "session_id": sess_id,
                        "message_id": ai_msg_id,
                        "user_message_id": user_msg_id,
                        "boot_id": boot_id,
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as fast_err:
                logger.debug(f"Local fast dispatch check skipped in api_chat: {fast_err}")

        # Extract preferences (honoring offline_mode & local provider isolation)
        offline_mode = bool(data.get('offline_mode', False))
        raw_prov = str(data.get('provider') or '').strip().lower()
        if offline_mode and not is_local_provider(raw_prov):
            provider_preference = 'gguf'
        elif raw_prov:
            provider_preference = LLMFactory.normalize_provider(raw_prov)
        else:
            provider_preference = None
        raw_model = data.get('model')
        model_preference = (
            LLMFactory.sanitize_model_for_provider(provider_preference, raw_model)
            if provider_preference
            else raw_model
        )
        
        # Apply learning-enhanced response generation
        try:
            from ai_assistant.integrations.learning_integration import get_learning_assistant
            learning_assistant = get_learning_assistant(current_user)
            if learning_assistant.systems_active:
                # Enhance message with context-aware generation
                message = learning_assistant.generate_intelligent_response(message, context)
                logger.info("Applied learning-enhanced response generation")
        except Exception as e:
            logger.warning(f"Learning enhancement skipped: {e}")
        
        try:
            # Process with full AI capabilities
            response = assistant.process_enhanced_chat(
                message, context, image_data,
                model_preference=model_preference,
                provider_preference=provider_preference
            )

            try:
                from telemetry_tracer import telemetry
                lat = (time.time() - start_time) * 1000
                p = response.get("provider") or get_provider()
                m = response.get("model") or get_model()
                telemetry.log_router("CHAT_QUERY", f"{p} ({m})")
                telemetry.log_compute(lat, status="200 OK")
                telemetry.log_dispatch(["Web UI (HTTP)", "Frontend Sync"], response.get("response"))
            except Exception:
                pass
            
            resp_text = str(response.get("response", ""))
            resp_ok = not resp_text.strip().startswith("Error:")
            resp_prov = response.get("provider") or provider_preference or get_provider()
            resp_model = response.get("model") or model_preference or get_model()
            if resp_text:
                store.record_message(
                    'ai',
                    resp_text,
                    source='enhanced_chat',
                    is_voice=False,
                    message_id=ai_msg_id,
                    provider=resp_prov,
                    model=resp_model,
                    success=resp_ok,
                    expected_session_id=sess_id,
                )
                if resp_ok and raw_user_message and store.get_current_session().get('id') == sess_id:
                    try:
                        from ai_assistant.ai.memory_retrieval import persist_turn_to_conversation_ai
                        threading.Thread(
                            target=persist_turn_to_conversation_ai,
                            args=(raw_user_message, resp_text),
                            kwargs={'source': source, 'session_id': sess_id},
                            daemon=True,
                        ).start()
                    except Exception:
                        pass
            return jsonify({
                "success": resp_ok,
                "error": resp_text if not resp_ok else None,
                "message": raw_user_message,
                "response": resp_text,
                "features_used": response.get("features_used", []),
                "suggestions": response.get("suggestions", []),
                "mood": response.get("mood", "neutral"),
                "context_id": response.get("context_id"),
                "provider": resp_prov,
                "model": resp_model,
                "user": current_user,
                "session_id": sess_id,
                "message_id": ai_msg_id,
                "user_message_id": user_msg_id,
                "boot_id": boot_id,
                "timestamp": datetime.now().isoformat()
            }), (200 if resp_ok else 502)
        except Exception as fallback_error:
            logger.error(f"Fallback error in api_chat: {fallback_error}")
            err_resp = f"I'm sorry, I encountered an internal error: {fallback_error}"
            fb_prov = provider_preference or get_provider()
            fb_model = model_preference or get_model()
            store.record_message(
                'ai',
                err_resp,
                source='safe_fallback',
                is_voice=False,
                message_id=ai_msg_id,
                provider=fb_prov,
                model=fb_model,
                success=False,
                expected_session_id=sess_id,
            )
            return jsonify({
                "success": False,
                "error": str(fallback_error),
                "message": raw_user_message,
                "response": err_resp,
                "features_used": ["safe_fallback"],
                "provider": fb_prov,
                "model": fb_model,
                "suggestions": [],
                "user": current_user,
                "session_id": sess_id,
                "message_id": ai_msg_id,
                "user_message_id": user_msg_id,
                "boot_id": boot_id,
                "timestamp": datetime.now().isoformat()
            }), 500
                
    except Exception as e:
        logging.error(f"Chat API error: {str(e)}")
        return jsonify({"error": f"Chat processing failed: {str(e)[:200]}"}), 500

@chat_bp.route('/api/command', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_command():
    """Process text command - Protected"""
    try:
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'command', 'command')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        command = sanitize_command(data['command'])
        
        if not command:
            return jsonify({"error": "No command provided"}), 400

        src_str = str(data.get('source') or 'http_command')
        is_voice_cmd = any(t in src_str.lower() for t in ('voice', 'companion', 'whisper', 'google'))
        store = _get_chat_store()
        sess_id = store.get_current_session().get('id')
        boot_id = store.get_boot_id()
        user_msg_id = str(data.get('client_message_id') or '').strip() or store.next_message_id('cmd_user')
        ai_msg_id = store.next_message_id('cmd_ai')
        store.record_message(
            'user',
            command,
            source=src_str,
            is_voice=is_voice_cmd,
            message_id=user_msg_id,
            expected_session_id=sess_id,
        )

        # === PRIORITY 0: Voice / Mode Control Commands (Zero LLM calls) ===
        try:
            from ai_assistant.core.local_command_normalizer import (
                parse_voice_control_command,
                execute_voice_control_command,
            )
            vc_parsed = parse_voice_control_command(command)
            if vc_parsed:
                vc_res = execute_voice_control_command(vc_parsed)
                resp_text = vc_res.get("response", "")
                vc_ok = vc_res.get("success", True)
                vc_prov = vc_res.get("provider", "local_voice_control")
                vc_model = vc_res.get("model", get_model())
                if vc_res.get("tts"):
                    _maybe_speak_http_command(data, resp_text, success=vc_ok)
                if resp_text:
                    store.record_message(
                        'ai',
                        resp_text,
                        source='local_voice_control',
                        is_voice=False,
                        message_id=ai_msg_id,
                        provider=vc_prov,
                        model=vc_model,
                        intent='voice_control',
                        success=bool(vc_ok),
                        expected_session_id=sess_id,
                    )
                return jsonify({
                    "success": vc_ok,
                    "command": command,
                    "response": resp_text,
                    "provider": vc_prov,
                    "model": vc_model,
                    "execution_meta": vc_res.get("execution_meta", {}),
                    "session_id": sess_id,
                    "message_id": ai_msg_id,
                    "user_message_id": user_msg_id,
                    "boot_id": boot_id,
                    "skip_tts": True,
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as vc_err:
            logger.debug(f"Voice control check skipped in api_command: {vc_err}")

        # === NEW: Multi-step Task Chain Orchestration ===
        try:
            from ai_assistant.integrations.orchestrator_integration import should_use_orchestrator, process_with_orchestrator
            
            if should_use_orchestrator(command):
                logger.info(f" Multi-step command detected: {command}")
                orch_result = process_with_orchestrator(command, {})
                
                if orch_result['success']:
                    _maybe_speak_http_command(data, orch_result.get('response', ''), success=True)
                    store.record_message(
                        'ai',
                        orch_result['response'],
                        source='multi_step_orchestration',
                        is_voice=False,
                        message_id=ai_msg_id,
                        intent='orchestrator',
                        success=True,
                        activity_kind='action',
                        activity_title='Orchestrated workflow completed',
                        expected_session_id=sess_id,
                    )
                    return jsonify({
                        "success": True,
                        "command": command,
                        "response": orch_result['response'],
                        "orchestrated": True,
                        "steps_completed": orch_result['steps_completed'],
                        "total_steps": orch_result['total_steps'],
                        "session_id": sess_id,
                        "message_id": ai_msg_id,
                        "user_message_id": user_msg_id,
                        "boot_id": boot_id,
                        "skip_tts": True,
                        "timestamp": datetime.now().isoformat()
                    })
                elif not orch_result.get('fallback'):
                    # Hard error, don't fallback
                    err_txt = orch_result.get('error', 'Multi-step execution failed')
                    store.record_message(
                        'ai',
                        err_txt,
                        source='multi_step_orchestration',
                        is_voice=False,
                        message_id=ai_msg_id,
                        intent='orchestrator',
                        success=False,
                        expected_session_id=sess_id,
                    )
                    return jsonify({
                        "success": False,
                        "error": err_txt,
                        "orchestrated": True,
                        "command": command,
                        "session_id": sess_id,
                        "message_id": ai_msg_id,
                        "user_message_id": user_msg_id,
                        "boot_id": boot_id,
                        "timestamp": datetime.now().isoformat()
                    }), 500
                else:
                    logger.warning("Orchestrator unavailable/failed, using fallback")
                    # Continue to normal processing below
        except Exception as orch_error:
            logger.warning(f"Orchestrator error, falling back: {orch_error}")
            # Continue to normal processing
        # === END: Multi-step Orchestration ===
        
        # Resolve provider/model/offline_mode consistently (local requests NEVER route to cloud)
        offline_mode = bool(data.get('offline_mode', False))
        raw_prov = str(data.get('provider') or '').strip().lower()
        norm_prov = LLMFactory.normalize_provider(raw_prov) if raw_prov else ''
        if offline_mode and not is_local_provider(norm_prov):
            preferred_provider = 'gguf'
        else:
            preferred_provider = norm_prov or LLMFactory.normalize_provider(get_provider() or 'gguf') or 'gguf'
        raw_model = data.get('model') or (
            get_model() if preferred_provider == LLMFactory.normalize_provider(get_provider()) else None
        )
        preferred_model = LLMFactory.sanitize_model_for_provider(preferred_provider, raw_model)
        logger.info(f"   Command received: {command[:30]}... (provider={preferred_provider}, offline={offline_mode})")

        # Process command with unified JARVIS lifecycle (pre-report -> AgentBrain -> post-report)
        try:
            model_pref = {
                'provider': preferred_provider,
                'model': preferred_model,
                'offline_mode': offline_mode,
            }

            from ai_assistant.core.jarvis_persona import get_lifecycle_coordinator, should_speak_for_request
            coordinator = get_lifecycle_coordinator()
            wants_speak = should_speak_for_request(data, default_for_chat=False)
            turn_id = coordinator.begin_turn(command, source=src_str, speak=wants_speak)
            pre_report = coordinator.emit_pre_report(turn_id, command, source=src_str, speak=wants_speak)
            if pre_report:
                store.record_activity(
                    'pre_report',
                    'Task started',
                    pre_report,
                    source=src_str,
                    status='running',
                    provider=preferred_provider,
                    model=preferred_model,
                    expected_session_id=sess_id,
                )

            from agent_brain import get_agent_brain
            brain = get_agent_brain()
            result = brain.process_command(command, source=src_str, model_preference=model_pref)

            if isinstance(result, dict):
                response = result.get('response', '')
                meta = result.get('execution_meta', {})
                card = result.get('card')
                res_intent = result.get('intent')
            else:
                response = str(result)
                meta = {}
                card = None
                res_intent = None

            actual_p = meta.get('provider_used') or preferred_provider
            actual_m = meta.get('model_used') or preferred_model
            is_ok = bool(result.get('success', True)) if isinstance(result, dict) else True

            formatted_resp, _ = coordinator.complete_turn(
                turn_id,
                command,
                response,
                success=is_ok,
                intent=res_intent,
                source=src_str,
                speak=wants_speak,
            )

            recorded_text = formatted_resp or ((result.get('error') or response) if (isinstance(result, dict) and not is_ok) else response)
            if recorded_text:
                store.record_message(
                    'ai',
                    recorded_text,
                    source=src_str,
                    is_voice=False,
                    message_id=ai_msg_id,
                    provider=actual_p,
                    model=actual_m,
                    intent=res_intent,
                    success=is_ok,
                    activity_kind=('action' if (is_ok and res_intent) else ('response' if is_ok else 'error')),
                    expected_session_id=sess_id,
                )

            return jsonify({
                "success": is_ok,
                "error": (result.get('error') or response) if (isinstance(result, dict) and not is_ok) else None,
                "command": command,
                "pre_report": pre_report,
                "response": formatted_resp,
                "card": card,
                "provider": actual_p,
                "model": actual_m,
                "execution_meta": meta,
                "session_id": sess_id,
                "message_id": ai_msg_id,
                "user_message_id": user_msg_id,
                "boot_id": boot_id,
                "skip_tts": True,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as cmd_error:
            err_msg = f"Command processing failed: {str(cmd_error)}"
            store.record_message(
                'ai',
                err_msg,
                source=src_str,
                is_voice=False,
                message_id=ai_msg_id,
                provider=preferred_provider,
                model=preferred_model,
                success=False,
                expected_session_id=sess_id,
            )
            return jsonify({
                "success": False,
                "error": err_msg,
                "command": command,
                "provider": preferred_provider,
                "model": preferred_model,
                "session_id": sess_id,
                "message_id": ai_msg_id,
                "user_message_id": user_msg_id,
                "boot_id": boot_id,
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        api_logger.error(f"Command API error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@chat_bp.route('/api/enhanced/chat', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("60 per minute")
async def api_enhanced_chat():
    """Enhanced chat with all advanced features: caching, routing, streaming, emotion detection"""
    try:
        if not ENHANCED_AI_AVAILABLE:
            return jsonify({
                "error": "Enhanced AI not available. Run: pip install diskcache sentence-transformers",
                "fallback": True
            }), 503
        
        current_user = get_jwt_identity() or "anonymous"
        data = request.get_json()
        
        message = data.get('message', '')
        if not message:
            return jsonify({"error": "No message provided"}), 400
        
        # Optional parameters
        enable_cache = data.get('enable_cache', True)
        enable_streaming = data.get('enable_streaming', False)
        audio_path = data.get('audio_path', None)  # For emotion detection
        context = data.get('context', {})
        
        # Process with enhanced AI
        result = await enhanced_ai.process_query(
            query=message,
            context=context,
            enable_cache=enable_cache,
            enable_streaming=enable_streaming,
            audio_path=audio_path
        )
        
        # Log for learning
        if LEARNING_ROUTER_AVAILABLE and learning_router:
            learning_router.route_conversation(message, result['text'], current_user)
        
        return jsonify({
            "success": True,
            "message": message,
            "response": result['text'],
            "metadata": {
                "model": result['model'],
                "cached": result['cached'],
                "emotion": result.get('emotion'),
                "complexity": result.get('complexity', 0),
                "time_ms": result['time_ms'],
                "tokens": result.get('tokens', 0),
                "cost_usd": result.get('cost_usd', 0)
            },
            "features_used": ["enhanced_ai", "semantic_cache", "model_routing"],
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Enhanced chat error: {e}")
        return jsonify({
            "error": str(e),
            "success": False
        }), 500

@chat_bp.route('/api/enhanced/stats', methods=['GET'])
@limiter.limit("30 per minute")
def api_enhanced_stats():
    """Get comprehensive stats for all advanced features"""
    try:
        if not ENHANCED_AI_AVAILABLE:
            return jsonify({"error": "Enhanced AI not available"}), 503
        
        stats = enhanced_ai.get_stats()
        
        return jsonify({
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Enhanced stats error: {e}")
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/enhanced/cache/clear', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def api_clear_cache():
    """Clear the semantic response cache"""
    try:
        if not ENHANCED_AI_AVAILABLE:
            return jsonify({"error": "Enhanced AI not available"}), 503
        
        if enhanced_ai.cache:
            enhanced_ai.cache.invalidate()  # Clear all cache
            
            return jsonify({
                "success": True,
                "message": "Cache cleared successfully",
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({"error": "Cache not available"}), 503
        
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/usage-analysis', methods=['GET'])
@jwt_required(optional=True)
@limiter.limit("10 per minute")
def api_usage_analysis():
    """Get usage pattern analysis and training data"""
    try:
        if not USAGE_ANALYZER_AVAILABLE:
            return jsonify({"error": "Usage analyzer not available"}), 503
        
        days_back = int(request.args.get('days', 30))
        
        # Run analysis
        results = usage_analyzer.analyze_all(days_back=days_back)
        
        return jsonify({
            "success": True,
            "analysis": {
                "common_commands": results.get('common_commands', [])[:10],
                "frequent_topics": results.get('frequent_topics', [])[:10],
                "time_patterns": results.get('time_patterns', {}),
                "app_usage": results.get('app_usage', {}),
                "command_sequences": results.get('command_sequences', [])[:5],
                "preferences": results.get('preferences', {}),
                "training_data_count": len(results.get('training_data', []))
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Usage analysis error: {e}")
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/usage-analysis/export', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def api_export_training_data():
    """Export training data for fine-tuning"""
    try:
        if not USAGE_ANALYZER_AVAILABLE:
            return jsonify({"error": "Usage analyzer not available"}), 503
        
        data = request.get_json()
        format_type = data.get('format', 'openai')  # 'openai' or 'huggingface'
        days_back = data.get('days', 30)
        
        # Analyze
        results = usage_analyzer.analyze_all(days_back=days_back)
        
        # Export
        output_path = f"data/training/finetuning_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        exported_file = usage_analyzer.export_for_finetuning(output_path, format=format_type)
        
        return jsonify({
            "success": True,
            "file_path": exported_file,
            "examples_count": len(results.get('training_data', [])),
            "format": format_type,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Export training data error: {e}")
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/automation/verify', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
async def api_verify_automation():
    """Verify automation action using visual verification"""
    try:
        if not ENHANCED_AI_AVAILABLE:
            return jsonify({"error": "Visual verification not available"}), 503
        
        data = request.get_json()
        action_name = data.get('action_name', 'automation')
        app_name = data.get('app_name', None)
        
        # Verify automation
        result = await enhanced_ai.verify_automation(action_name, app_name)
        
        return jsonify({
            "success": result['success'],
            "verification": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Automation verification error: {e}")
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/chat/stream', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_chat_stream():
    """
    Stream chat response token-by-token via Server-Sent Events.
    Provides real-time response generation with response count tracking.
    """
    try:
        current_user = get_jwt_identity() or "anonymous"
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'message', 'command')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        message = sanitize_command(data['message'])
        session_id = data.get('session_id', f"{current_user}_{int(time.time())}")
        req_offline = bool(data.get('offline_mode', False))
        req_prov_raw = str(data.get('provider') or '').strip().lower()
        req_model_raw = data.get('model')
        source = str(data.get('source') or 'chat_stream')
        
        if not message:
            return jsonify({"error": "No message provided"}), 400

        store = _get_chat_store()
        active_sess_id = store.get_current_session().get('id')
        boot_id = store.get_boot_id()
        user_msg_id = str(data.get('client_message_id') or '').strip() or store.next_message_id('stream_user')
        ai_msg_id = store.next_message_id('stream_ai')
        is_voice_src = any(t in source.lower() for t in ('voice', 'companion', 'whisper', 'google'))
        store.record_message(
            'user',
            message,
            source=source,
            is_voice=is_voice_src,
            message_id=user_msg_id,
            expected_session_id=active_sess_id,
        )

        # Priority-0 voice/barge-in/mode control guard so stop phrases never hit streaming LLM
        try:
            from ai_assistant.core.local_command_normalizer import (
                parse_voice_control_command,
                execute_voice_control_command,
            )
            vc_parsed = parse_voice_control_command(message)
            if vc_parsed:
                vc_res = execute_voice_control_command(vc_parsed)
                vc_ok = bool(vc_res.get("success", True))
                vc_resp = str(vc_res.get("response", "") or "")
                vc_prov = vc_res.get("provider", "local_voice_control")
                vc_model = vc_res.get("model", get_model())
                if vc_resp:
                    store.record_message(
                        'ai',
                        vc_resp,
                        source='local_voice_control',
                        is_voice=False,
                        message_id=ai_msg_id,
                        provider=vc_prov,
                        model=vc_model,
                        intent='voice_control',
                        success=vc_ok,
                        expected_session_id=active_sess_id,
                    )

                def _vc_stream():
                    if vc_resp:
                        yield f"data: {json.dumps({'token': vc_resp, 'count': 1, 'partial': vc_resp, 'provider': vc_prov, 'model': vc_model, 'stream_id': ai_msg_id, 'session_id': active_sess_id})}\n\n"
                    yield f"data: {json.dumps({'done': True, 'tokens': 1 if vc_resp else 0, 'full_response': vc_resp, 'provider': vc_prov, 'model': vc_model, 'user': current_user, 'session_id': active_sess_id, 'message_id': ai_msg_id, 'user_message_id': user_msg_id, 'boot_id': boot_id, 'voice_control': True, 'timestamp': datetime.now().isoformat()})}\n\n"

                return Response(_vc_stream(), mimetype='text/event-stream')
        except Exception as vc_err:
            logger.debug(f"Voice control check skipped in api_chat_stream: {vc_err}")

        logger.info(f"[INFO] Streaming chat for user: {current_user}, session: {session_id}")
        
        def generate_stream():
            """Generate streaming response tokens"""
            try:
                # Resolve provider/model honoring request params & offline_mode
                norm_prov = LLMFactory.normalize_provider(req_prov_raw) if req_prov_raw else ''
                if req_offline and not is_local_provider(norm_prov):
                    cur_provider = 'gguf'
                else:
                    cur_provider = norm_prov or LLMFactory.normalize_provider(get_provider() or 'gguf') or 'gguf'
                raw_m = req_model_raw or (
                    get_model() if cur_provider == LLMFactory.normalize_provider(get_provider()) else None
                )
                cur_model = LLMFactory.sanitize_model_for_provider(cur_provider, raw_m)

                with chat_session_lock:
                    existing_chat = chat_sessions.get(session_id)
                    if (
                        existing_chat is None
                        or getattr(existing_chat, 'provider_name', None) != cur_provider
                        or getattr(existing_chat, 'model', None) != cur_model
                    ):
                        if LLM_PROVIDER_AVAILABLE:
                            chat_sessions[session_id] = UnifiedChatInterface(
                                provider=cur_provider,
                                model=cur_model,
                                use_fallback=(not is_local_provider(cur_provider)),
                            )
                        else:
                            # Fallback if LLM not available
                            store.record_message(
                                'ai',
                                'LLM provider not available',
                                source=source,
                                is_voice=False,
                                message_id=ai_msg_id,
                                provider=cur_provider,
                                model=cur_model,
                                success=False,
                                expected_session_id=active_sess_id,
                            )
                            yield f"data: {json.dumps({'error': 'LLM provider not available', 'session_id': active_sess_id, 'message_id': ai_msg_id, 'user_message_id': user_msg_id, 'boot_id': boot_id})}\n\n"
                            return
                    chat = chat_sessions[session_id]

                # Refresh persona system prompt + cross-session historical RAG context on EVERY turn
                rag_ctx = ""
                try:
                    from ai_assistant.ai.memory_retrieval import retrieve_unified_historical_context
                    rag_ctx = retrieve_unified_historical_context(
                        message,
                        current_session_id=active_sess_id,
                        only_when_triggered=True,
                    )
                except Exception as rag_err:
                    logger.debug(f"Historical RAG lookup skipped in stream: {rag_err}")

                try:
                    from ai_assistant.core.jarvis_persona import build_persona_system_prompt
                    sys_prompt = build_persona_system_prompt(
                        provider=cur_provider,
                        model=cur_model,
                        surface="chat",
                        extra_context=rag_ctx,
                    )
                except Exception:
                    sys_prompt = "You are Pulsar, an intelligent and helpful AI companion created by Diwakar."
                    if rag_ctx:
                        sys_prompt = f"{sys_prompt}\n{rag_ctx}"
                if hasattr(chat, 'set_system_message'):
                    chat.set_system_message(sys_prompt)

                start_time = time.time()
                tokens = 0
                full_response = ""
                
                logger.debug(f"Starting stream for message: {message[:50]}... (provider={cur_provider}, model={cur_model})")
                
                try:
                    # Get streaming response
                    for token in chat.chat(message, stream=True):
                        if store.get_current_session().get('id') != active_sess_id:
                            yield f"data: {json.dumps({'done': True, 'aborted': True, 'reason': 'new_session', 'session_id': active_sess_id})}\n\n"
                            return
                        if tokens == 0 and str(token).strip().startswith("Error:"):
                            err_tok = str(token)
                            store.record_message(
                                'ai',
                                err_tok,
                                source=source,
                                is_voice=False,
                                message_id=ai_msg_id,
                                provider=cur_provider,
                                model=cur_model,
                                success=False,
                                expected_session_id=active_sess_id,
                            )
                            error_data = json.dumps({
                                'error': err_tok,
                                'provider': cur_provider,
                                'model': cur_model,
                                'session_id': active_sess_id,
                                'message_id': ai_msg_id,
                                'user_message_id': user_msg_id,
                                'boot_id': boot_id,
                            })
                            yield f"data: {error_data}\n\n"
                            return
                        tokens += 1
                        full_response += token
                        
                        # Emit token with count
                        token_data = json.dumps({
                            'token': token,
                            'count': tokens,
                            'partial': full_response,
                            'provider': cur_provider,
                            'model': cur_model,
                            'stream_id': ai_msg_id,
                            'session_id': active_sess_id,
                        })
                        yield f"data: {token_data}\n\n"
                        
                        # Small delay to prevent overwhelming client
                        time.sleep(0.001)
                except Exception as stream_error:
                    logger.error(f"Streaming error: {stream_error}")
                    err_str = f'Streaming failed: {str(stream_error)}'
                    store.record_message(
                        'ai',
                        err_str,
                        source=source,
                        is_voice=False,
                        message_id=ai_msg_id,
                        provider=cur_provider,
                        model=cur_model,
                        success=False,
                        expected_session_id=active_sess_id,
                    )
                    error_data = json.dumps({
                        'error': err_str,
                        'provider': cur_provider,
                        'model': cur_model,
                        'session_id': active_sess_id,
                        'message_id': ai_msg_id,
                        'user_message_id': user_msg_id,
                        'boot_id': boot_id,
                    })
                    yield f"data: {error_data}\n\n"
                    return
                
                if store.get_current_session().get('id') != active_sess_id:
                    yield f"data: {json.dumps({'done': True, 'aborted': True, 'reason': 'new_session', 'session_id': active_sess_id})}\n\n"
                    return

                # Send completion stats
                if full_response.strip():
                    store.record_message(
                        'ai',
                        full_response,
                        source=source,
                        is_voice=False,
                        message_id=ai_msg_id,
                        provider=cur_provider,
                        model=cur_model,
                        success=True,
                        expected_session_id=active_sess_id,
                    )
                    try:
                        from ai_assistant.ai.memory_retrieval import persist_turn_to_conversation_ai
                        threading.Thread(
                            target=persist_turn_to_conversation_ai,
                            args=(message, full_response),
                            kwargs={'source': source, 'session_id': active_sess_id},
                            daemon=True,
                        ).start()
                    except Exception:
                        pass
                duration = time.time() - start_time
                completion_data = json.dumps({
                    'done': True,
                    'tokens': tokens,
                    'duration': round(duration, 2),
                    'tokens_per_second': round(tokens / duration, 2) if duration > 0 else 0,
                    'full_response': full_response,
                    'provider': cur_provider,
                    'model': cur_model,
                    'user': current_user,
                    'session_id': active_sess_id,
                    'message_id': ai_msg_id,
                    'user_message_id': user_msg_id,
                    'boot_id': boot_id,
                    'timestamp': datetime.now().isoformat()
                })
                yield f"data: {completion_data}\n\n"
                
                logger.info(f"[OK] Stream complete: {tokens} tokens in {duration:.2f}s ({tokens/duration:.1f} tok/s)")
                
            except Exception as e:
                logger.error(f"Stream generation error: {e}")
                store.record_message(
                    'ai',
                    str(e),
                    source=source,
                    is_voice=False,
                    message_id=ai_msg_id,
                    success=False,
                    expected_session_id=active_sess_id,
                )
                error_msg = json.dumps({
                    'error': str(e),
                    'session_id': active_sess_id,
                    'message_id': ai_msg_id,
                    'user_message_id': user_msg_id,
                    'boot_id': boot_id,
                })
                yield f"data: {error_msg}\n\n"
        
        return Response(generate_stream(), mimetype='text/event-stream')
    
    except Exception as e:
        logger.error(f"Chat stream endpoint error: {str(e)}")
        return jsonify({"error": f"Chat streaming failed: {str(e)}"}), 500

@chat_bp.route('/api/chat/sessions/<session_id>', methods=['GET'])
@jwt_required(optional=True)
def api_get_session(session_id):
    """Get information about a chat session"""
    try:
        if session_id not in chat_sessions:
            return jsonify({"error": "Session not found"}), 404
        
        chat = chat_sessions[session_id]
        stats = {
            "session_id": session_id,
            "messages": len(chat.conversation_history),
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/chat/sessions/<session_id>', methods=['DELETE'])
@jwt_required(optional=True)
def api_delete_session(session_id):
    """Delete a chat session"""
    try:
        with chat_session_lock:
            if session_id in chat_sessions:
                del chat_sessions[session_id]
                return jsonify({"success": True, "message": "Session deleted"})
        
        return jsonify({"error": "Session not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/chat/context', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("20 per minute")
def api_create_context():
    """Create new conversation context"""
    try:
        if not assistant.conversational_ai:
            return jsonify({"error": "Conversational AI not available"}), 503
        
        data = request.get_json()
        name = data.get('name', 'New Conversation')
        topic = data.get('topic', 'General Chat')
        initial_message = data.get('initial_message', '')
        
        context_id = assistant.conversational_ai.create_context(name, topic, initial_message)
        
        return jsonify({
            "context_id": context_id,
            "name": name,
            "topic": topic,
            "created_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Failed to create context: {str(e)}"}), 500

@chat_bp.route('/api/chat/suggestions', methods=['GET'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_get_suggestions():
    """Get AI-powered suggestions for next actions"""
    try:
        if not assistant.conversational_ai:
            return jsonify({"suggestions": []})
        
        suggestions = assistant.conversational_ai.suggest_next_actions()
        return jsonify({"suggestions": suggestions})
    except Exception as e:
        return jsonify({"error": f"Failed to get suggestions: {str(e)}"}), 500

@chat_bp.route('/api/multimodal/analyze', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("10 per minute")
def api_multimodal_analyze():
    """Analyze image with AI"""
    try:
        if not assistant.multimodal_ai:
            return jsonify({"error": "Multimodal AI not available"}), 503
        
        data = request.get_json()
        image_data = data.get('image')
        prompt = data.get('prompt', 'What do you see in this image?')
        
        if not image_data:
            return jsonify({"error": "No image provided"}), 400
        
        analysis = assistant.multimodal_ai.analyze_image_from_base64(image_data, prompt)
        
        return jsonify({
            "analysis": analysis,
            "prompt": prompt,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Image analysis failed: {str(e)}"}), 500

@chat_bp.route('/api/screen/analyze', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_analyze_screen():
    """Analyze current screen using multimodal AI"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', 'What is on the screen?')
        
        analysis = assistant.analyze_screen(prompt)
        
        return jsonify({
            "analysis": analysis,
            "prompt": prompt,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Screen analysis failed: {str(e)}"}), 500

@chat_bp.route('/api/automation/workflows', methods=['GET'])
@jwt_required(optional=True)
@limiter.limit("20 per minute")
def api_get_workflows():
    """Get available automation workflows"""
    try:
        if not AUTOMATION_AVAILABLE:
            return jsonify({"workflows": []})
        
        from ai_assistant.automation.automation_engine import SmartAutomationEngine
        automation_engine = SmartAutomationEngine()
        workflows = automation_engine.get_available_workflows()
        
        return jsonify({"workflows": workflows})
    except Exception as e:
        return jsonify({"error": f"Failed to get workflows: {str(e)}"}), 500

@chat_bp.route('/api/automation/execute', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("10 per minute")
def api_execute_workflow():
    """Execute automation workflow"""
    try:
        if not AUTOMATION_AVAILABLE:
            return jsonify({"error": "Automation not available"}), 503
        
        data = request.get_json()
        workflow_name = data.get('workflow_name')
        
        if not workflow_name:
            return jsonify({"error": "Workflow name required"}), 400
        
        from ai_assistant.automation.automation_engine import SmartAutomationEngine
        automation_engine = SmartAutomationEngine()
        result = automation_engine.execute_workflow_by_name(workflow_name)
        
        return jsonify({
            "result": result,
            "workflow_name": workflow_name,
            "executed_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Workflow execution failed: {str(e)}"}), 500

@chat_bp.route('/api/memory/save', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_save_memory():
    """Save information to memory system"""
    try:
        if not AUTOMATION_AVAILABLE:
            return jsonify({"error": "Memory system not available"}), 503
        
        data = request.get_json()
        category = data.get('category', 'user')
        content = data.get('content')
        
        if not content:
            return jsonify({"error": "Content required"}), 400
        
        result = save_to_memory(category, content)
        
        return jsonify({
            "result": result,
            "category": category,
            "saved_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Failed to save memory: {str(e)}"}), 500

@chat_bp.route('/api/memory/search', methods=['GET'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_search_memory():
    """Search memory system"""
    try:
        if not AUTOMATION_AVAILABLE:
            return jsonify({"results": []})
        
        query = request.args.get('query', '')
        if not query:
            return jsonify({"error": "Search query required"}), 400
        
        results = search_memory(query)
        
        return jsonify({
            "results": results,
            "query": query,
            "searched_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Memory search failed: {str(e)}"}), 500

@chat_bp.route('/api/visual/question', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def api_visual_question():
    """Answer visual questions about screen content - PROTECTED"""
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'question', 'command')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        question = data['question']
        
        answer = assistant.answer_visual_question(question)
        return jsonify({
            "question": question,
            "answer": answer,
            "user": current_user,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": "Failed to answer visual question"}), 500
