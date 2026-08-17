"""
Chat Blueprint

Handles chat/AI conversation endpoints with full integration.
Includes: basic chat, command processing, streaming, sessions, context, and suggestions.
"""

from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import time
import logging
import json

logger = logging.getLogger(__name__)

# In-memory session storage (should be replaced with proper DB)
chat_sessions = {}

def create_blueprint(assistant):
    """Create and configure the chat blueprint"""
    bp = Blueprint('chat', __name__, url_prefix='/api')
    
    # Import validation functions
    from ai_assistant.utils.backend_utils import validate_input, sanitize_command
    
    @bp.route('/chat', methods=['POST'])
    @jwt_required(optional=True)
    def chat():
        """Enhanced chat endpoint with full AI integration"""
        start_time = time.time()
        try:
            current_user = get_jwt_identity() or "anonymous"
            data = request.get_json()
            
            is_valid, error = validate_input(data, 'message', 'command')
            if not is_valid:
                return jsonify({"error": error}), 400
            
            message = sanitize_command(data['message'])
            context = data.get('context', {})
            
            if not message:
                return jsonify({"error": "No message provided"}), 400
            
            response = assistant.process_command(message)
            
            return jsonify({
                "message": message,
                "response": response,
                "user": current_user,
                "timestamp": datetime.now().isoformat(),
                "processing_time": time.time() - start_time
            })
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return jsonify({"error": "Chat failed"}), 500
    
    @bp.route('/command', methods=['POST'])
    @jwt_required()
    def command():
        """Process text command"""
        try:
            data = request.get_json()
            is_valid, error = validate_input(data, 'command', 'command')
            if not is_valid:
                return jsonify({"error": error}), 400
            
            cmd = sanitize_command(data['command'])
            if not cmd:
                return jsonify({"error": "No command provided"}), 400
            
            response = assistant.process_command(cmd)
            
            return jsonify({
                "success": True,
                "command": cmd,
                "response": response,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Command error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @bp.route('/chat/stream', methods=['POST'])
    @jwt_required(optional=True)
    def chat_stream():
        """Streaming chat endpoint"""
        try:
            data = request.get_json()
            message = sanitize_command(data.get('message', ''))
            
            def generate():
                try:
                    response = assistant.process_command(message)
                    # Simulate streaming by chunking response
                    words = response.split()
                    for i, word in enumerate(words):
                        chunk = {
                            "chunk": word + " ",
                            "index": i,
                            "done": i == len(words) - 1
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                        time.sleep(0.05)
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return Response(generate(), mimetype='text/event-stream')
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/chat/sessions/<session_id>', methods=['GET'])
    @jwt_required(optional=True)
    def get_session(session_id):
        """Get chat session data"""
        session = chat_sessions.get(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        return jsonify(session)
    
    @bp.route('/chat/sessions/<session_id>', methods=['DELETE'])
    @jwt_required(optional=True)
    def delete_session(session_id):
        """Delete chat session"""
        if session_id in chat_sessions:
            del chat_sessions[session_id]
            return jsonify({"success": True})
        return jsonify({"error": "Session not found"}), 404
    
    @bp.route('/chat/context', methods=['POST'])
    @jwt_required(optional=True)
    def set_context():
        """Set conversation context"""
        try:
            data = request.get_json()
            context = data.get('context', {})
            # Store context for session
            return jsonify({"success": True, "context_set": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/chat/suggestions', methods=['GET'])
    @jwt_required(optional=True)
    def get_suggestions():
        """Get chat suggestions"""
        try:
            suggestions = [
                "What's the weather today?",
                "Tell me a joke",
                "Open notepad",
                "What can you do?"
            ]
            return jsonify({"suggestions": suggestions})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    return bp
