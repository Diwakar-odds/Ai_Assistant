"""
Voice Backend Integration Code
Add this to modern_web_backend.py to integrate the voice system
"""

# ============================================
# VOICE SYSTEM INTEGRATION
# ============================================

# 1. Import voice modules (add to imports section)
try:
    from ai_assistant.services.voice_service import get_voice_service
    from ai_assistant.api.voice_api import voice_api
    VOICE_INTEGRATION_AVAILABLE = True
    print("✅ Voice integration modules loaded")
except ImportError as e:
    VOICE_INTEGRATION_AVAILABLE = False
    print(f"⚠️ Voice integration not available: {e}")

# 2. Initialize voice service (add after app initialization)
voice_service = None
if VOICE_INTEGRATION_AVAILABLE:
    try:
        voice_service = get_voice_service()
        print("✅ Voice service initialized successfully")
        print(f"   - TTS Available: {voice_service.get_status()['tts_available']}")
        print(f"   - STT Available: {voice_service.get_status()['stt_available']}")
    except Exception as e:
        print(f"⚠️ Voice service initialization failed: {e}")
        voice_service = None

# 3. Register voice API blueprint (add after other blueprint registrations)
if VOICE_INTEGRATION_AVAILABLE:
    try:
        app.register_blueprint(voice_api)
        print("✅ Voice API blueprint registered at /api/voice/*")
    except Exception as e:
        print(f"⚠️ Failed to register voice API blueprint: {e}")

# 4. Add WebSocket event handlers (add to socketio events section)

@socketio.on('voice_command')
def handle_voice_command(data):
    """
    Handle voice command from client
    Receives transcribed text and processes it as a command
    """
    try:
        text = data.get('text', '').strip()
        source = data.get('source', 'voice')
        
        if not text:
            emit('voice_error', {'error': 'No text provided'})
            return
        
        logger.info(f"Voice command received: {text}")
        
        # Process command using assistant
        response = assistant.process_command(text)
        
        # Send response back
        emit('voice_response', {
            'command': text,
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'source': source
        })
        
        # Update history
        if voice_service:
            voice_service._add_to_history(text)
        
        logger.info(f"Voice response sent: {response[:100]}...")
        
    except Exception as e:
        logger.error(f"Error processing voice command: {e}")
        emit('voice_error', {'error': str(e)})

@socketio.on('start_voice_listening')
def handle_start_voice_listening():
    """Start voice listening mode"""
    try:
        if not voice_service:
            emit('voice_error', {'error': 'Voice service not available'})
            return
        
        voice_service.is_listening = True
        
        emit('voice_listening_started', {
            'success': True,
            'message': 'Voice listening started',
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info("Voice listening started")
        
    except Exception as e:
        logger.error(f"Error starting voice listening: {e}")
        emit('voice_error', {'error': str(e)})

@socketio.on('stop_voice_listening')
def handle_stop_voice_listening():
    """Stop voice listening mode"""
    try:
        if not voice_service:
            emit('voice_error', {'error': 'Voice service not available'})
            return
        
        voice_service.is_listening = False
        
        emit('voice_listening_stopped', {
            'success': True,
            'message': 'Voice listening stopped',
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info("Voice listening stopped")
        
    except Exception as e:
        logger.error(f"Error stopping voice listening: {e}")
        emit('voice_error', {'error': str(e)})

@socketio.on('speak_text')
def handle_speak_text(data):
    """Speak text using TTS"""
    try:
        if not voice_service:
            emit('voice_error', {'error': 'Voice service not available'})
            return
        
        text = data.get('text', '').strip()
        voice = data.get('voice')
        
        if not text:
            emit('voice_error', {'error': 'No text provided'})
            return
        
        # Speak the text
        success = voice_service.speak(text, voice=voice)
        
        if success:
            emit('text_spoken', {
                'success': True,
                'text': text,
                'timestamp': datetime.now().isoformat()
            })
        else:
            emit('voice_error', {'error': 'Failed to speak text'})
        
        logger.info(f"Text spoken: {text[:50]}...")
        
    except Exception as e:
        logger.error(f"Error speaking text: {e}")
        emit('voice_error', {'error': str(e)})

@socketio.on('request_voice_status')
def handle_request_voice_status():
    """Send voice system status to client"""
    try:
        if not voice_service:
            emit('voice_status', {
                'available': False,
                'error': 'Voice service not initialized'
            })
            return
        
        status = voice_service.get_status()
        
        emit('voice_status', {
            'available': True,
            **status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting voice status: {e}")
        emit('voice_error', {'error': str(e)})

# 5. Add voice status to initial connection (modify handle_connect)
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    
    emit('connected', {
        'message': 'Connected to Pulsar Assistant',
        'timestamp': datetime.now().isoformat()
    })
    
    # Send voice system status
    if voice_service:
        try:
            status = voice_service.get_status()
            emit('voice_status', {
                'available': True,
                **status
            })
        except Exception as e:
            emit('voice_status', {
                'available': False,
                'error': str(e)
            })
    else:
        emit('voice_status', {
            'available': False,
            'error': 'Voice service not initialized'
        })

# ============================================
# END VOICE SYSTEM INTEGRATION
# ============================================

# USAGE NOTES:
# 
# 1. Make sure to install dependencies first:
#    pip install edge-tts SpeechRecognition pyttsx3 gTTS pygame
#
# 2. Configuration file should exist at:
#    config/voice_config.json
#
# 3. Test the integration:
#    python voice_quick_start.py
#
# 4. API endpoints will be available at:
#    - GET  /api/voice/status
#    - GET  /api/voice/voices
#    - POST /api/voice/speak
#    - POST /api/voice/listen
#    - GET  /api/voice/history
#
# 5. WebSocket events:
#    - Client -> Server: voice_command, start_voice_listening, stop_voice_listening, speak_text
#    - Server -> Client: voice_response, voice_status, voice_error, voice_listening_started
#
# 6. Frontend integration example:
#    socket.emit('voice_command', { text: 'open chrome' });
#    socket.on('voice_response', (data) => {
#        console.log('Response:', data.response);
#    });
