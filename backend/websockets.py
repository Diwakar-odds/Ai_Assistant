from flask import request
from flask_socketio import emit
import json
import logging
import sys
import threading
import time
import traceback
from datetime import datetime
from settings_manager import get_provider, get_model

main_mod = sys.modules.get('__main__') or sys.modules.get('backend.modern_web_backend') or sys.modules.get('modern_web_backend')
logger = getattr(main_mod, 'logger', logging.getLogger('websockets'))
socketio = getattr(main_mod, 'socketio', None)
assistant = getattr(main_mod, 'assistant', None)

if socketio is None:
    try:
        from routes.common import get_socketio
        socketio = get_socketio()
    except Exception:
        try:
            from backend.routes.common import get_socketio
            socketio = get_socketio()
        except Exception:
            pass

if assistant is None:
    try:
        from routes.common import get_assistant
        assistant = get_assistant()
    except Exception:
        try:
            from backend.routes.common import get_assistant
            assistant = get_assistant()
        except Exception:
            pass

try:
    from routes.chat_routes import (
        chat_session_lock,
        chat_sessions,
        LLM_PROVIDER_AVAILABLE,
        UnifiedChatInterface,
        LLMFactory,
        is_local_provider,
    )
except Exception:
    try:
        from backend.routes.chat_routes import (
            chat_session_lock,
            chat_sessions,
            LLM_PROVIDER_AVAILABLE,
            UnifiedChatInterface,
            LLMFactory,
            is_local_provider,
        )
    except Exception:
        chat_session_lock = threading.Lock()
        chat_sessions = {}
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
    from ai_assistant.automation.automation_engine import SmartAutomationEngine  # noqa: F401
    AUTOMATION_AVAILABLE = True
except Exception:
    AUTOMATION_AVAILABLE = False

try:
    from ai_assistant.multilingual import Language
except Exception:
    Language = None

try:
    from utils.logging_config import log_query, log_reply
except Exception:
    def log_query(msg): logger.info(f"Query: {msg}")
    def log_reply(msg): logger.info(f"Reply: {msg}")

_SOCKET_HANDLERS = []
_REGISTERED_APPS = set()


def _on_socket(event_name):
    """Register a Socket.IO handler safely even before socketio is bound."""
    def decorator(func):
        _SOCKET_HANDLERS.append((event_name, func))
        if socketio is not None:
            socketio.on(event_name)(func)
            _REGISTERED_APPS.add(id(socketio))
        return func
    return decorator


def register_socket_events(socketio_app):
    """Bind all module Socket.IO handlers onto the provided SocketIO instance."""
    global socketio
    if socketio_app is None:
        return
    socketio = socketio_app
    app_id = id(socketio_app)
    if app_id in _REGISTERED_APPS:
        return
    _REGISTERED_APPS.add(app_id)
    existing_handlers = set()
    try:
        ns_handlers = getattr(getattr(socketio_app, 'server', None), 'handlers', {}) or {}
        if '/' in ns_handlers and isinstance(ns_handlers['/'], dict):
            existing_handlers = set(ns_handlers['/'].keys())
    except Exception:
        existing_handlers = set()

    for event_name, func in _SOCKET_HANDLERS:
        if event_name in existing_handlers:
            logger.debug(f"Skipping duplicate Socket.IO handler for '{event_name}'")
            continue
        socketio_app.on(event_name)(func)
    
@_on_socket('enhanced_chat')
def handle_enhanced_chat(data):
    """Handle enhanced chat with full AI integration"""
    try:
        message = data.get('message', '')
        context = data.get('context', {})
        image_data = data.get('image', None)
        model = data.get('model')  # Get model preference
        offline_mode = bool(data.get('offline_mode', False))
        raw_prov = str(data.get('provider') or '').strip().lower()
        if offline_mode and not is_local_provider(raw_prov):
            provider = 'gguf'
        elif raw_prov:
            provider = LLMFactory.normalize_provider(raw_prov)
        else:
            provider = None
        if provider:
            model = LLMFactory.sanitize_model_for_provider(provider, model)
        
        if message or image_data:
            response = assistant.process_enhanced_chat(
                message, context, image_data, 
                model_preference=model, 
                provider_preference=provider
            )
            resp_text = str(response.get('response', ''))
            if resp_text.strip().startswith('Error:'):
                emit('enhanced_chat_error', {'error': resp_text, 'provider': response.get('provider'), 'model': response.get('model')})
                return
            emit('enhanced_chat_response', {
                'message': message,
                'response': resp_text,
                'features_used': response['features_used'],
                'suggestions': response.get('suggestions', []),
                'mood': response.get('mood', 'neutral'),
                'context_id': response.get('context_id'),
                'detected_language': response.get('detected_language', 'english'),
                'message_type': response.get('message_type', 'general_chat'),
                'provider': response.get('provider'),
                'model': response.get('model'),
                'timestamp': datetime.now().isoformat()
            })
        else:
            emit('enhanced_chat_error', {'error': 'No message or image provided'})
    except Exception as e:
        emit('enhanced_chat_error', {'error': f'Chat processing failed: {str(e)}'})

@_on_socket('chat_stream')
def handle_chat_stream(data):
    """
    Handle real-time streaming chat via WebSocket.
    Streams response tokens as they are generated.
    """
    try:
        message = data.get('message', '')
        session_id = data.get('session_id', request.sid)
        offline_mode = bool(data.get('offline_mode', False))
        raw_prov = str(data.get('provider') or '').strip().lower()
        req_model = data.get('model')
        
        if not message:
            emit('chat_stream_error', {'error': 'No message provided'})
            return

        norm_prov = LLMFactory.normalize_provider(raw_prov) if raw_prov else ''
        if offline_mode and not is_local_provider(norm_prov):
            cur_provider = 'gguf'
        else:
            cur_provider = norm_prov or LLMFactory.normalize_provider(get_provider() or 'gguf') or 'gguf'
        raw_m = req_model or (
            get_model() if cur_provider == LLMFactory.normalize_provider(get_provider()) else None
        )
        cur_model = LLMFactory.sanitize_model_for_provider(cur_provider, raw_m)
        
        logger.info(f"ƒ…‚¬‚ WebSocket chat stream started: {session_id}")
        
        # Get or create chat session (and keep provider/model/persona synced)
        with chat_session_lock:
            existing_chat = chat_sessions.get(session_id)
            if (
                existing_chat is None
                or getattr(existing_chat, 'provider_name', None) != cur_provider
                or getattr(existing_chat, 'model', None) != cur_model
            ):
                if LLM_PROVIDER_AVAILABLE and UnifiedChatInterface is not None:
                    chat_sessions[session_id] = UnifiedChatInterface(
                        provider=cur_provider,
                        model=cur_model,
                        use_fallback=(not is_local_provider(cur_provider)),
                    )
                    try:
                        from ai_assistant.core.jarvis_persona import build_persona_system_prompt
                        sys_prompt = build_persona_system_prompt(provider=cur_provider, model=cur_model, surface="chat")
                    except Exception:
                        sys_prompt = "You are Pulsar, an intelligent and helpful AI companion created by Diwakar."
                    chat_sessions[session_id].set_system_message(sys_prompt)
                else:
                    emit('chat_stream_error', {'error': 'LLM provider not available'})
                    return

            chat = chat_sessions[session_id]
        
        # Stream the response
        start_time = time.time()
        tokens = 0
        full_response = ""
        
        try:
            # Stream tokens
            for token in chat.chat(message, stream=True):
                if tokens == 0 and str(token).strip().startswith('Error:'):
                    emit('chat_stream_error', {
                        'error': str(token),
                        'provider': cur_provider,
                        'model': cur_model,
                    })
                    return
                tokens += 1
                full_response += token
                
                # Emit token to client
                emit('chat_token', {
                    'token': token,
                    'count': tokens,
                    'partial': full_response,
                    'provider': cur_provider,
                    'model': cur_model,
                }, skip_sid=False)  # Send to current client
        
        except Exception as stream_error:
            logger.error(f"WebSocket streaming error: {stream_error}")
            emit('chat_stream_error', {'error': f'Streaming failed: {str(stream_error)}'})
            return
        
        # Send completion signal with stats
        duration = time.time() - start_time
        emit('chat_complete', {
            'tokens': tokens,
            'duration': round(duration, 2),
            'tokens_per_second': round(tokens / duration, 2) if duration > 0 else 0,
            'full_response': full_response,
            'provider': cur_provider,
            'model': cur_model,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"[OK] WebSocket stream complete: {tokens} tokens in {duration:.2f}s")
        
    except Exception as e:
        logger.error(f"WebSocket chat stream error: {e}")
        emit('chat_stream_error', {'error': f'Chat stream failed: {str(e)}'})

@_on_socket('analyze_image')
def handle_analyze_image(data):
    """Handle image analysis request"""
    try:
        image_data = data.get('image')
        prompt = data.get('prompt', 'What do you see in this image?')
        
        if not image_data:
            emit('image_analysis_error', {'error': 'No image provided'})
            return
        
        if assistant.multimodal_ai:
            analysis = assistant.multimodal_ai.analyze_image_from_base64(image_data, prompt)
            emit('image_analysis_response', {
                'analysis': analysis,
                'prompt': prompt,
                'timestamp': datetime.now().isoformat()
            })
        else:
            emit('image_analysis_error', {'error': 'Multimodal AI not available'})
    except Exception as e:
        emit('image_analysis_error', {'error': f'Image analysis failed: {str(e)}'})

@_on_socket('analyze_gesture')
def handle_analyze_gesture(data):
    """Handle high-frequency gesture analysis request"""
    try:
        image_data = data.get('image')
        if not image_data:
            return
            
        try:
            from ai_assistant.vision.gesture_recognition import gesture_recognition_sys
            gesture = gesture_recognition_sys.detect_gesture(image_data)
            
            if gesture:
                emit('gesture_detected', {
                    'gesture': gesture,
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Gesture recognition error: {e}")
            
    except Exception as e:
        logger.error(f"Analyze gesture failed: {e}")
        emit('image_analysis_error', {'error': f'Image analysis failed: {str(e)}'})

@_on_socket('analyze_presence')
def handle_analyze_presence(data):
    """Handle periodic presence/mood analysis request from camera"""
    try:
        image_data = data.get('image')
        
        if not image_data:
            return # Don't emit error for background tasks to avoid spam
            
        # 1. Local Face Identification
        person_name = None
        try:
            from ai_assistant.vision.facial_recognition import facial_recognition_sys
            person_name = facial_recognition_sys.identify_person(image_data)
        except Exception as e:
            logger.error(f"Local face recognition error: {e}")

        # 2. Mood & Presence Detection via Gemini
        prompt = "Analyze the person in this image. Answer with valid JSON only (no markdown, no backticks). Include keys: 'present' (boolean) and 'mood' (string, e.g., 'neutral', 'happy', 'focused', 'away'). Keep the explanation short in a third key 'description'."
        if person_name and person_name != "Unknown":
            prompt = f"Analyze {person_name} in this image. Answer with valid JSON only (no markdown, no backticks). Include keys: 'present' (boolean) and 'mood' (string, e.g., 'neutral', 'happy', 'focused', 'away'). Keep the explanation short in a third key 'description'."

        if assistant.multimodal_ai:
            raw_analysis = assistant.multimodal_ai.analyze_image_from_base64(image_data, prompt, use_cache=False)
            
            # Parse Gemini's JSON response
            import json
            parsed_data = {}
            try:
                # The text is in raw_analysis['analysis']
                text = raw_analysis.get('analysis', '{}').strip()
                if text.startswith('```json'):
                    text = text.replace('```json', '').replace('```', '')
                elif text.startswith('```'):
                    text = text.replace('```', '')
                parsed_data = json.loads(text)
            except Exception as parse_e:
                logger.error(f"Failed to parse presence JSON: {parse_e}")
            
            # Merge parsed data into raw_analysis for frontend
            raw_analysis.update(parsed_data)
            
            # Inject person name if found
            if person_name:
                raw_analysis['person_name'] = person_name
                if 'present' not in raw_analysis:
                    raw_analysis['present'] = True
                
                # Override mood to include name if not already there
                if 'mood' in raw_analysis and raw_analysis['mood'] and raw_analysis['mood'] != 'away':
                    raw_analysis['mood'] = f"{person_name} ({raw_analysis['mood']})"
                else:
                    raw_analysis['mood'] = person_name

            emit('presence_update', {
                'analysis': raw_analysis,
                'timestamp': datetime.now().isoformat()
            })
    except Exception as e:
        logger.error(f"Presence analysis failed: {e}")

@_on_socket('analyze_screen')
def handle_analyze_screen(data):
    """Handle screen analysis request"""
    try:
        prompt = data.get('prompt', 'What is on the screen?')
        
        analysis = assistant.analyze_screen(prompt)
        emit('screen_analysis_response', {
            'analysis': analysis,
            'prompt': prompt,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        emit('screen_analysis_error', {'error': f'Screen analysis failed: {str(e)}'})

@_on_socket('get_suggestions')
def handle_get_suggestions():
    """Handle AI suggestions request"""
    try:
        if assistant.conversational_ai:
            suggestions = assistant.conversational_ai.suggest_next_actions()
            emit('suggestions_response', {
                'suggestions': suggestions,
                'timestamp': datetime.now().isoformat()
            })
        else:
            emit('suggestions_response', {'suggestions': []})
    except Exception as e:
        emit('suggestions_error', {'error': f'Failed to get suggestions: {str(e)}'})

@_on_socket('execute_workflow')
def handle_execute_workflow(data):
    """Handle workflow execution request"""
    try:
        workflow_name = data.get('workflow_name')
        
        if not workflow_name:
            emit('workflow_error', {'error': 'Workflow name required'})
            return
        
        if AUTOMATION_AVAILABLE:
            from ai_assistant.automation.automation_engine import SmartAutomationEngine
            automation_engine = SmartAutomationEngine()
            result = automation_engine.execute_workflow_by_name(workflow_name)
            
            emit('workflow_response', {
                'result': result,
                'workflow_name': workflow_name,
                'executed_at': datetime.now().isoformat()
            })
        else:
            emit('workflow_error', {'error': 'Automation not available'})
    except Exception as e:
        emit('workflow_error', {'error': f'Workflow execution failed: {str(e)}'})

@_on_socket('mood_detection')
def handle_mood_detection(data):
    """Handle mood detection request (Note: duplicate voice listeners were removed from this file)"""
    try:
        text = data.get('text', '')
        
        if not text:
            emit('mood_detection_error', {'error': 'Text required'})
            return
        
        if assistant.conversational_ai:
            mood = assistant.conversational_ai.detect_mood(text)
            emit('mood_detection_response', {
                'text': text,
                'mood': mood.value,
                'timestamp': datetime.now().isoformat()
            })
        else:
            emit('mood_detection_error', {'error': 'Conversational AI not available'})
    except Exception as e:
        emit('mood_detection_error', {'error': f'Mood detection failed: {str(e)}'})

@_on_socket('request_system_stats')
def handle_system_stats_request():
    """Handle system stats request"""
    stats = assistant.get_real_time_system_stats()
    emit('system_stats', stats)

@_on_socket('start_voice_listening')
def handle_start_voice():
    """Start voice listening"""
    result = assistant.start_voice_listening()
    emit('voice_start_response', result)

@_on_socket('stop_voice_listening')
def handle_stop_voice():
    """Stop voice listening"""
    result = assistant.stop_voice_listening()
    emit('voice_stop_response', result)

@_on_socket('request_tts')
def handle_tts_request(data):
    """Handle text-to-speech request via the single unified desktop speaker pipeline."""
    text = (data or {}).get('text', '') if isinstance(data, dict) else ''
    if not text:
        return

    interrupt = bool(data.get('interrupt', True)) if isinstance(data, dict) else True
    try:
        from ai_assistant.voice.tts_output_service import get_tts_service
        success = get_tts_service().speak(text, interrupt=interrupt, source='websocket_tts')
        emit('tts_response', {'success': bool(success), 'text': text, 'unified': True})
        return
    except Exception as tts_err:
        logger.debug(f"Unified TTS fallback in websockets.py: {tts_err}")

    if assistant and assistant.multilingual:
        language = data.get('language', 'auto')
        result = assistant.multilingual.speak_multilingual(
            text,
            Language(language) if language != 'auto' else Language.AUTO_DETECT
        )
        emit('tts_response', {'success': True, 'text': text, 'result': result})
    elif assistant:
        success = assistant.speak_text(text)
        emit('tts_response', {'success': bool(success), 'text': text})

@_on_socket('language_command')
def handle_multilingual_command(data):
    """Handle multilingual command"""
    command = data.get('command', '')
    language = data.get('language', 'auto')
    
    if command:
        log_query(command)
        if assistant.multilingual:
            response = assistant.process_multilingual_command(command)
        else:
            response = assistant.process_command(command)
        
        log_reply(response)
        emit('language_command_response', {
            'command': command,
            'response': response,
            'language': language,
            'timestamp': datetime.now().isoformat()
        })

from flask_socketio import join_room, leave_room

@_on_socket('subscribe_chain')
def handle_chain_subscribe(data):
    """Subscribe to chain updates"""
    payload = data if isinstance(data, dict) else {}
    chain_id = payload.get('chain_id') or payload.get('id')
    if chain_id:
        join_room(f"chain_{chain_id}")
        emit('chain.subscribed', {'chain_id': chain_id})
        try:
            from routes.chain_routes import resolve_chain_snapshot
            snapshot = resolve_chain_snapshot(str(chain_id))
        except Exception:
            try:
                from backend.routes.chain_routes import resolve_chain_snapshot
                snapshot = resolve_chain_snapshot(str(chain_id))
            except Exception:
                snapshot = None
        if snapshot:
            emit('chain.state', snapshot)
        logger.info(f"Client subscribed to progress for chain {chain_id}")

@_on_socket('unsubscribe_chain')
def handle_chain_unsubscribe(data):
    """Unsubscribe from chain updates"""
    payload = data if isinstance(data, dict) else {}
    chain_id = payload.get('chain_id') or payload.get('id')
    if chain_id:
        leave_room(f"chain_{chain_id}")
        emit('chain.unsubscribed', {'chain_id': chain_id})
        logger.info(f"Client unsubscribed from progress for chain {chain_id}")

def _resolve_sio():
    sio = socketio
    if sio is None:
        try:
            from routes.common import get_socketio
            sio = get_socketio()
        except Exception:
            try:
                from backend.routes.common import get_socketio
                sio = get_socketio()
            except Exception:
                sio = None
    return sio

def broadcast_chain_progress(chain_id: str, event_type: str, data: dict):
    """
    Broadcasts chain progress to room subscribers AND global WebUI listeners.
    event_type can be: chain.started, chain.planned, chain.step_started,
    chain.step_completed, chain.step_failed, chain.verification_completed,
    chain.paused, chain.resumed, chain.cancelled, chain.completed
    """
    sio = _resolve_sio()
    if sio is None:
        return

    payload = dict(data) if isinstance(data, dict) else {'data': data}
    if chain_id and 'chain_id' not in payload:
        payload['chain_id'] = chain_id
    payload.setdefault('event', event_type)
    payload.setdefault('timestamp', datetime.now().isoformat())

    try:
        if chain_id:
            sio.emit(event_type, payload, room=f"chain_{chain_id}", namespace='/')
    except Exception as e:
        logger.debug(f"Room emit error for {event_type}: {e}")

    try:
        sio.emit('chain_progress', {**payload, 'event_type': event_type}, namespace='/')
    except Exception as e:
        logger.debug(f"Global chain_progress emit error: {e}")

@_on_socket('subscribe_agents')
def handle_agents_subscribe(data=None):
    """Subscribe client to live multi-agent status & task updates and emit snapshot."""
    join_room('agents')
    emit('agents.subscribed', {'subscribed': True})
    try:
        from routes.agent_routes import get_agents_snapshot_payload
        snap = get_agents_snapshot_payload()
    except Exception:
        try:
            from backend.routes.agent_routes import get_agents_snapshot_payload
            snap = get_agents_snapshot_payload()
        except Exception:
            snap = None
    if snap:
        emit('agents_snapshot', snap)

@_on_socket('unsubscribe_agents')
def handle_agents_unsubscribe(data=None):
    """Unsubscribe client from agents room."""
    leave_room('agents')
    emit('agents.unsubscribed', {'subscribed': False})

def broadcast_agent_event(event_type: str, data: dict):
    """Broadcast multi-agent status/task event (`agent.*` or `agents_snapshot`) on '/'."""
    sio = _resolve_sio()
    if sio is None:
        return
    payload = dict(data) if isinstance(data, dict) else {'data': data}
    payload.setdefault('event', event_type)
    payload.setdefault('timestamp', datetime.now().isoformat())
    try:
        sio.emit(event_type, payload, namespace='/')
    except Exception as e:
        logger.debug(f"Agent broadcast error for {event_type}: {e}")

@_on_socket('emergency_stop')
@_on_socket('executive_stop')
def handle_emergency_stop_socket(data=None):
    """Handle emergency stop WebSocket event"""
    try:
        from ai_assistant.core.emergency_stop import trigger_emergency_stop
        reason = (data or {}).get('reason', 'Triggered via WebSocket') if isinstance(data, dict) else 'Triggered via WebSocket'
        res = trigger_emergency_stop(reason=reason)
        emit('emergency_stop_confirmed', {'success': True, 'result': res})
    except Exception as e:
        logger.error(f"WebSocket emergency stop error: {e}")
        emit('emergency_stop_error', {'error': str(e)})
