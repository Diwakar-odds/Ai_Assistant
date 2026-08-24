from flask import request
from flask_socketio import emit
import json, logging, traceback
try:
    from backend.modern_web_backend import logger, socketio
except ImportError:
    pass

# We can import modern_web_backend to get other globals if needed inside functions
from backend.modern_web_backend import *

def register_socket_events(socketio_app):
    # This wrapper isn't strictly necessary if we just import socketio, 
    # but the decorators currently use `@socketio.on`.
    pass
    
@socketio.on('enhanced_chat')
def handle_enhanced_chat(data):
    """Handle enhanced chat with full AI integration"""
    try:
        message = data.get('message', '')
        context = data.get('context', {})
        image_data = data.get('image', None)
        model = data.get('model')  # Get model preference
        provider = data.get('provider')  # Get provider preference
        
        if message or image_data:
            response = assistant.process_enhanced_chat(
                message, context, image_data, 
                model_preference=model, 
                provider_preference=provider
            )
            emit('enhanced_chat_response', {
                'message': message,
                'response': response['response'],
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

@socketio.on('chat_stream')
def handle_chat_stream(data):
    """
    Handle real-time streaming chat via WebSocket.
    Streams response tokens as they are generated.
    """
    try:
        message = data.get('message', '')
        session_id = data.get('session_id', request.sid)
        
        if not message:
            emit('chat_stream_error', {'error': 'No message provided'})
            return
        
        logger.info(f"ÃƒÂ°Ã…Â¸Ã¢â‚¬Å“Ã‚Â¡ WebSocket chat stream started: {session_id}")
        
        # Get or create chat session
        with chat_session_lock:
            if session_id not in chat_sessions:
                if LLM_PROVIDER_AVAILABLE:
                    chat_sessions[session_id] = UnifiedChatInterface()
                    chat_sessions[session_id].add_system_message(
                        "You are a helpful AI assistant. Respond concisely and accurately."
                    )
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
                tokens += 1
                full_response += token
                
                # Emit token to client
                emit('chat_token', {
                    'token': token,
                    'count': tokens,
                    'partial': full_response
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
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"[OK] WebSocket stream complete: {tokens} tokens in {duration:.2f}s")
        
    except Exception as e:
        logger.error(f"WebSocket chat stream error: {e}")
        emit('chat_stream_error', {'error': f'Chat stream failed: {str(e)}'})

@socketio.on('analyze_image')
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

@socketio.on('analyze_screen')
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

@socketio.on('get_suggestions')
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

@socketio.on('execute_workflow')
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

@socketio.on('mood_detection')
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

@socketio.on('request_system_stats')
def handle_system_stats_request():
    """Handle system stats request"""
    stats = assistant.get_real_time_system_stats()
    emit('system_stats', stats)

@socketio.on('start_voice_listening')
def handle_start_voice():
    """Start voice listening"""
    result = assistant.start_voice_listening()
    emit('voice_start_response', result)

@socketio.on('stop_voice_listening')
def handle_stop_voice():
    """Stop voice listening"""
    result = assistant.stop_voice_listening()
    emit('voice_stop_response', result)

@socketio.on('request_tts')
def handle_tts_request(data):
    """Handle text-to-speech request with multilingual support"""
    text = data.get('text', '')
    language = data.get('language', 'auto')
    
    if text:
        if assistant.multilingual:
            # Use multilingual TTS
            result = assistant.multilingual.speak_multilingual(
                text, 
                Language(language) if language != 'auto' else Language.AUTO_DETECT
            )
            emit('tts_response', {'success': True, 'text': text, 'result': result})
        else:
            # Fallback to regular TTS
            success = assistant.speak_text(text)
            emit('tts_response', {'success': success, 'text': text})

@socketio.on('language_command')
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

@socketio.on('subscribe_chain')
def handle_chain_subscribe(data):
    """Subscribe to chain updates"""
    chain_id = data.get('chain_id')
    if chain_id:
        join_room(f"chain_{chain_id}")
        emit('chain.subscribed', {'chain_id': chain_id})
        logger.info(f"Client subscribed to progress for chain {chain_id}")

@socketio.on('unsubscribe_chain')
def handle_chain_unsubscribe(data):
    """Unsubscribe from chain updates"""
    chain_id = data.get('chain_id')
    if chain_id:
        leave_room(f"chain_{chain_id}")
        emit('chain.unsubscribed', {'chain_id': chain_id})
        logger.info(f"Client unsubscribed from progress for chain {chain_id}")

def broadcast_chain_progress(chain_id: str, event_type: str, data: dict):
    """
    Broadcasts chain progress to clients subscribed to the chain.
    event_type can be: chain.started, chain.step_completed, chain.step_failed, chain.verification_completed, chain.completed
    """
    socketio.emit(event_type, data, room=f"chain_{chain_id}")