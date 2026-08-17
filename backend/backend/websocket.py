"""
YourDaddy AI Assistant - WebSocket Handlers

Real-time communication handlers for voice, chat, and system events.
"""

import logging
from flask_socketio import emit, disconnect
from flask import request

logger = logging.getLogger(__name__)


def register_handlers(socketio, components):
    """
    Register all WebSocket event handlers
    
    Args:
        socketio: SocketIO instance
        components: Dictionary of initialized components
    """
    
    # Track connected clients
    connected_clients = {}
    
    @socketio.on('connect')
    def handle_connect():
        """Client connected"""
        client_id = request.sid
        connected_clients[client_id] = {
            'connected_at': __import__('time').time(),
            'address': request.remote_addr
        }
        
        logger.info(f"Client connected: {client_id} from {request.remote_addr}")
        emit('connected', {
            'status': 'ok',
            'client_id': client_id,
            'message': 'Connected to YourDaddy Assistant'
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Client disconnected"""
        client_id = request.sid
        
        if client_id in connected_clients:
            del connected_clients[client_id]
        
        logger.info(f"Client disconnected: {client_id}")
    
    @socketio.on('ping')
    def handle_ping():
        """Ping/pong for connection keepalive"""
        emit('pong', {'timestamp': __import__('time').time()})
    
    @socketio.on('chat_message')
    def handle_chat_message(data):
        """
        Handle chat message via WebSocket
        
        Expected data:
            {
                "message": "user message",
                "context": {...}  # optional
            }
        """
        try:
            message = data.get('message', '')
            context = data.get('context', {})
            
            if not message:
                emit('error', {'error': 'Message is required'})
                return
            
            logger.info(f"Chat message from {request.sid}: {message[:100]}")
            
            # TODO: Integrate actual AI processing
            # For now, echo response
            response = f"Received: {message}"
            
            emit('chat_response', {
                'response': response,
                'timestamp': __import__('time').time()
            })
            
        except Exception as e:
            logger.error(f"Chat message error: {e}")
            emit('error', {'error': str(e)})
    
    @socketio.on('voice_start')
    def handle_voice_start(data):
        """Start voice recognition session"""
        try:
            logger.info(f"Voice recognition started for {request.sid}")
            
            emit('voice_started', {
                'status': 'listening',
                'timestamp': __import__('time').time()
            })
            
        except Exception as e:
            logger.error(f"Voice start error: {e}")
            emit('error', {'error': str(e)})
    
    @socketio.on('voice_audio')
    def handle_voice_audio(data):
        """
        Process voice audio chunks
        
        Expected data:
            {
                "audio": "base64_encoded_audio",
                "format": "wav|webm",
                "sample_rate": 16000
            }
        """
        try:
            audio_data = data.get('audio')
            audio_format = data.get('format', 'wav')
            sample_rate = data.get('sample_rate', 16000)
            
            if not audio_data:
                emit('error', {'error': 'Audio data is required'})
                return
            
            # TODO: Process audio with speech recognition
            logger.debug(f"Received audio chunk: {len(audio_data)} bytes")
            
            # Placeholder response
            emit('voice_processing', {
                'status': 'processing',
                'timestamp': __import__('time').time()
            })
            
        except Exception as e:
            logger.error(f"Voice audio error: {e}")
            emit('error', {'error': str(e)})
    
    @socketio.on('voice_stop')
    def handle_voice_stop():
        """Stop voice recognition session"""
        try:
            logger.info(f"Voice recognition stopped for {request.sid}")
            
            emit('voice_stopped', {
                'status': 'stopped',
                'timestamp': __import__('time').time()
            })
            
        except Exception as e:
            logger.error(f"Voice stop error: {e}")
            emit('error', {'error': str(e)})
    
    @socketio.on('system_command')
    def handle_system_command(data):
        """
        Execute system command
        
        Expected data:
            {
                "command": "command_name",
                "params": {...}
            }
        """
        try:
            command = data.get('command')
            params = data.get('params', {})
            
            if not command:
                emit('error', {'error': 'Command is required'})
                return
            
            logger.info(f"System command from {request.sid}: {command}")
            
            # TODO: Route to appropriate handler
            emit('command_result', {
                'command': command,
                'status': 'received',
                'timestamp': __import__('time').time()
            })
            
        except Exception as e:
            logger.error(f"System command error: {e}")
            emit('error', {'error': str(e)})
    
    @socketio.on('get_status')
    def handle_get_status():
        """Get system status"""
        try:
            status = {
                'connected_clients': len(connected_clients),
                'automation_available': components.get('automation_available', False),
                'multimodal_available': components.get('multimodal_available', False),
                'voice_available': components.get('voice_available', False),
                'timestamp': __import__('time').time()
            }
            
            emit('status_update', status)
            
        except Exception as e:
            logger.error(f"Get status error: {e}")
            emit('error', {'error': str(e)})
    
    logger.info("✅ WebSocket handlers registered")
    
    return socketio
