"""
YourDaddy AI Assistant - API Routes

All REST API endpoints for the backend.
Organized by feature domain.
"""

import logging
from flask import jsonify, request
from .error_handler import error_handler, ValidationError
from .middleware import validate_json, sanitize_input
from .utils import validate_required_fields

logger = logging.getLogger(__name__)


def register_routes(app, components):
    """
    Register all API routes
    
    Args:
        app: Flask application instance
        components: Dictionary of initialized components
    """
    
    limiter = app.limiter
    
    # =========================================================================
    # HEALTH & STATUS
    # =========================================================================
    
    @app.route('/api/ping', methods=['GET'])
    def ping():
        """Health check endpoint"""
        return jsonify({"status": "ok", "message": "Backend is running"})
    
    @app.route('/api/status', methods=['GET'])
    @limiter.limit("30 per minute")
    def get_status():
        """Get system status"""
        try:
            status = {
                "success": True,
                "backend": "modular",
                "version": "2.0.0",
                "automation_available": components.get('automation_available', False),
                "multimodal_available": components.get('multimodal_available', False),
                "voice_available": components.get('voice_available', False)
            }
            return jsonify(status)
        except Exception as e:
            logger.error(f"Status error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    # =========================================================================
    # AUTHENTICATION (PIN-based)
    # =========================================================================
    
    @app.route('/api/auth/is-configured', methods=['GET'])
    def is_pin_configured():
        """Check if PIN is configured"""
        try:
            from ai_assistant.auth.pin_auth import PINAuth
            
            auth = PINAuth()
            configured = auth.is_pin_configured()
            
            return jsonify({"success": True, "configured": configured})
            
        except Exception as e:
            logger.error(f"PIN check error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/auth/verify-pin', methods=['POST'])
    @limiter.limit("10 per minute")
    @validate_json
    @error_handler("PIN verification")
    def verify_pin():
        """Verify PIN"""
        from ai_assistant.auth.pin_auth import PINAuth
        
        data = request.get_json()
        is_valid, error = validate_required_fields(data, ['pin'])
        if not is_valid:
            raise ValidationError(error)
        
        pin = data.get('pin', '')
        
        auth = PINAuth()
        if auth.verify_pin(pin):
            return jsonify({"success": True, "message": "PIN verified"})
        else:
            return jsonify({"success": False, "error": "Invalid PIN"}), 401
    
    @app.route('/api/auth/setup-pin', methods=['POST'])
    @limiter.limit("5 per hour")
    @validate_json
    @error_handler("PIN setup")
    def setup_pin():
        """Setup PIN"""
        from ai_assistant.auth.pin_auth import PINAuth
        
        data = request.get_json()
        is_valid, error = validate_required_fields(data, ['pin'])
        if not is_valid:
            raise ValidationError(error)
        
        pin = data.get('pin', '')
        
        if len(pin) < 4:
            raise ValidationError("PIN must be at least 4 characters")
        
        auth = PINAuth()
        if auth.setup_pin(pin):
            return jsonify({"success": True, "message": "PIN setup successful"})
        else:
            return jsonify({"success": False, "error": "PIN setup failed"}), 500
    
    @app.route('/api/auth/change-pin', methods=['POST'])
    @limiter.limit("5 per hour")
    @validate_json
    @error_handler("PIN change")
    def change_pin():
        """Change PIN"""
        from ai_assistant.auth.pin_auth import PINAuth
        
        data = request.get_json()
        is_valid, error = validate_required_fields(data, ['current_pin', 'new_pin'])
        if not is_valid:
            raise ValidationError(error)
        
        current_pin = data.get('current_pin', '')
        new_pin = data.get('new_pin', '')
        
        if len(new_pin) < 4:
            raise ValidationError("New PIN must be at least 4 characters")
        
        auth = PINAuth()
        
        # Verify current PIN
        if not auth.verify_pin(current_pin):
            return jsonify({"success": False, "error": "Current PIN is incorrect"}), 401
        
        # Set new PIN
        if auth.setup_pin(new_pin):
            return jsonify({"success": True, "message": "PIN changed successfully"})
        else:
            return jsonify({"success": False, "error": "Failed to change PIN"}), 500
    
    # =========================================================================
    # CHAT & CONVERSATION
    # =========================================================================
    
    @app.route('/api/chat', methods=['POST'])
    @limiter.limit("30 per minute")
    @validate_json
    @error_handler("Chat")
    def chat():
        """Process chat message"""
        data = request.get_json()
        is_valid, error = validate_required_fields(data, ['message'])
        if not is_valid:
            raise ValidationError(error)
        
        message = data.get('message', '')
        context = data.get('context', {})
        
        # TODO: Integrate actual AI processing
        # Placeholder response
        response = f"Echo: {message}"
        
        return jsonify({
            "success": True,
            "response": response,
            "context": context
        })
    
    @app.route('/api/conversation/history', methods=['GET'])
    @limiter.limit("20 per minute")
    def get_conversation_history():
        """Get conversation history"""
        try:
            limit = request.args.get('limit', 50, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            # TODO: Fetch from database
            history = []
            
            return jsonify({
                "success": True,
                "history": history,
                "limit": limit,
                "offset": offset
            })
            
        except Exception as e:
            logger.error(f"Conversation history error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    # =========================================================================
    # APPLICATION CONTROL
    # =========================================================================
    
    @app.route('/api/apps/list', methods=['GET'])
    @limiter.limit("20 per minute")
    @error_handler("List apps")
    def list_apps():
        """List installed applications"""
        if not components.get('automation_available'):
            return jsonify({"success": False, "error": "Automation not available"}), 503
        
        from automation_tools_new import list_installed_apps
        apps = list_installed_apps()
        
        return jsonify({"success": True, "apps": apps})
    
    @app.route('/api/apps/launch', methods=['POST'])
    @limiter.limit("10 per minute")
    @validate_json
    @error_handler("Launch app")
    def launch_app():
        """Launch an application"""
        if not components.get('automation_available'):
            return jsonify({"success": False, "error": "Automation not available"}), 503
        
        data = request.get_json()
        is_valid, error = validate_required_fields(data, ['name'])
        if not is_valid:
            raise ValidationError(error)
        
        app_name = data.get('name', '')
        
        from automation_tools_new import smart_open_application
        result = smart_open_application(app_name)
        
        return jsonify({"success": True, "message": result})
    
    @app.route('/api/apps/close', methods=['POST'])
    @limiter.limit("10 per minute")
    @validate_json
    @error_handler("Close app")
    def close_app():
        """Close an application"""
        if not components.get('automation_available'):
            return jsonify({"success": False, "error": "Automation not available"}), 503
        
        data = request.get_json()
        is_valid, error = validate_required_fields(data, ['name'])
        if not is_valid:
            raise ValidationError(error)
        
        app_name = data.get('name', '')
        
        from automation_tools_new import close_application
        result = close_application(app_name)
        
        return jsonify({"success": True, "message": result})
    
    # =========================================================================
    # VOICE
    # =========================================================================
    
    @app.route('/api/voice/available', methods=['GET'])
    def voice_available():
        """Check if voice is available"""
        available = components.get('voice_available', False)
        return jsonify({"success": True, "available": available})
    
    @app.route('/api/voice/voices', methods=['GET'])
    def get_available_voices():
        """Get list of available TTS voices"""
        try:
            # Import voice constants if available
            voices = []
            try:
                from voice_service import AVAILABLE_VOICES
                voices = AVAILABLE_VOICES
            except ImportError:
                pass
            
            return jsonify({"success": True, "voices": voices})
            
        except Exception as e:
            logger.error(f"Get voices error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    # =========================================================================
    # SYSTEM
    # =========================================================================
    
    @app.route('/api/system/volume', methods=['GET', 'POST'])
    @limiter.limit("20 per minute")
    def system_volume():
        """Get or set system volume"""
        try:
            if not components.get('automation_available'):
                return jsonify({"success": False, "error": "Automation not available"}), 503
            
            if request.method == 'POST':
                data = request.get_json()
                volume = data.get('volume', 50)
                
                from automation_tools_new import set_system_volume
                result = set_system_volume(volume)
                
                return jsonify({"success": True, "volume": volume, "message": result})
            else:
                # GET current volume
                # TODO: Implement get_system_volume if available
                return jsonify({"success": True, "volume": 50})
                
        except Exception as e:
            logger.error(f"System volume error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/system/info', methods=['GET'])
    @limiter.limit("10 per minute")
    def system_info():
        """Get system information"""
        try:
            if not components.get('automation_available'):
                return jsonify({"success": False, "error": "Automation not available"}), 503
            
            from automation_tools_new import get_system_status
            info = get_system_status()
            
            return jsonify({"success": True, "info": info})
            
        except Exception as e:
            logger.error(f"System info error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    # =========================================================================
    # MEMORY
    # =========================================================================
    
    @app.route('/api/memory/save', methods=['POST'])
    @limiter.limit("20 per minute")
    @validate_json
    @error_handler("Save memory")
    def save_memory():
        """Save to memory"""
        if not components.get('automation_available'):
            return jsonify({"success": False, "error": "Automation not available"}), 503
        
        data = request.get_json()
        is_valid, error = validate_required_fields(data, ['key', 'value'])
        if not is_valid:
            raise ValidationError(error)
        
        key = data.get('key')
        value = data.get('value')
        
        from automation_tools_new import save_to_memory
        result = save_to_memory(key, value)
        
        return jsonify({"success": True, "message": result})
    
    @app.route('/api/memory/get', methods=['GET'])
    @limiter.limit("30 per minute")
    def get_memory():
        """Get from memory"""
        try:
            if not components.get('automation_available'):
                return jsonify({"success": False, "error": "Automation not available"}), 503
            
            key = request.args.get('key', '')
            if not key:
                raise ValidationError("Key is required")
            
            from automation_tools_new import get_memory
            value = get_memory(key)
            
            return jsonify({"success": True, "key": key, "value": value})
            
        except Exception as e:
            logger.error(f"Get memory error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    # =========================================================================
    # ERROR HANDLERS
    # =========================================================================
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"success": False, "error": "Method not allowed"}), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({"success": False, "error": "Internal server error"}), 500
    
    logger.info("âœ… API routes registered")
    
    return app




