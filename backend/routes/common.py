"""
Shared utilities, helpers, and state for backend routes.
Eliminates wildcard imports, circular dependencies, and provides safe fallbacks.
"""

import os
import re
import logging
from flask import request
from werkzeug.security import generate_password_hash

# Logging setup
logger = logging.getLogger('web_backend')
api_logger = logging.getLogger('api_requests')

def get_current_context():
    """Returns empty or current request context"""
    return {}

# JWT authentication imports with fallback stubs
try:
    from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request
except ImportError:
    def jwt_required(optional=False, **kwargs):
        def decorator(f):
            return f
        return decorator

    def create_access_token(identity, additional_claims=None, **kwargs):
        return f"token_for_{identity}"

    def get_jwt_identity():
        return "default_user"

    def verify_jwt_in_request(optional=False, **kwargs):
        pass

# In-memory user database
_admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
USERS_DB = {
    "admin": {
        "password_hash": generate_password_hash(_admin_password),
        "role": "admin"
    }
}

# Feature toggles
ENABLE_VOICE = os.getenv('ENABLE_VOICE', 'true').lower() == 'true'
ENABLE_MULTIMODAL = os.getenv('ENABLE_MULTIMODAL', 'true').lower() == 'true'
ENABLE_CONVERSATIONAL_AI = os.getenv('ENABLE_CONVERSATIONAL_AI', 'true').lower() == 'true'
ENABLE_SYSTEM_MONITORING = os.getenv('ENABLE_SYSTEM_MONITORING', 'true').lower() == 'true'
LAZY_INIT = os.getenv('LAZY_INIT', 'true').lower() == 'true'
BACKGROUND_INIT = os.getenv('BACKGROUND_INIT', 'true').lower() == 'true'

# Input validation patterns
VALIDATION_PATTERNS = {
    'command': re.compile(r'^[\w\s\-.,!?@#$%()+=:;"\']+$'),
    'app_name': re.compile(r'^[\w\s\-.]+$'),
    'username': re.compile(r'^[a-zA-Z0-9_]{3,20}$'),
}

def validate_input(data, field, pattern_name):
    """Validate input data against pattern"""
    if not data or field not in data:
        return False, f"{field} is required"
    
    value = data[field]
    if not isinstance(value, str):
        return False, f"{field} must be a string"
    
    if len(value) > 1000:
        return False, f"{field} is too long (max 1000 characters)"
    
    pattern = VALIDATION_PATTERNS.get(pattern_name)
    if pattern and not pattern.match(value):
        return False, f"{field} contains invalid characters"
    
    return True, None

def sanitize_command(command):
    """Sanitize command input to prevent injection"""
    if not command:
        return ""
    dangerous_chars = ['|', '&', ';', '`', '$', '(', ')', '<', '>', '\n', '\r']
    for char in dangerous_chars:
        command = command.replace(char, '')
    return command.strip()[:500]

# Global singleton holders
_assistant = None
_socketio = None
_learning_router = None
_limiter = None

def set_assistant(assistant_instance):
    global _assistant
    _assistant = assistant_instance

def get_assistant():
    global _assistant
    return _assistant

def set_socketio(socketio_instance):
    global _socketio
    _socketio = socketio_instance

def get_socketio():
    global _socketio
    return _socketio

def set_learning_router(router_instance):
    global _learning_router
    _learning_router = router_instance

def get_learning_router():
    global _learning_router
    return _learning_router

def set_limiter(limiter_instance):
    global _limiter
    _limiter = limiter_instance

def get_limiter():
    global _limiter
    return _limiter

class _LimiterProxy:
    """Proxy object so decorators like @limiter.limit work even before limiter is bound."""
    def limit(self, limit_value, **kwargs):
        def decorator(f):
            def wrapped(*args, **kw):
                if _limiter is not None:
                    return _limiter.limit(limit_value, **kwargs)(f)(*args, **kw)
                return f(*args, **kw)
            return wrapped
        return decorator

class _AssistantProxy:
    def __getattr__(self, name):
        inst = get_assistant()
        if inst is not None:
            return getattr(inst, name)
        return None
    def __bool__(self):
        return get_assistant() is not None

class _SocketIOProxy:
    def __getattr__(self, name):
        inst = get_socketio()
        if inst is not None:
            return getattr(inst, name)
        return lambda *args, **kw: None
    def __bool__(self):
        return get_socketio() is not None

class _LearningRouterProxy:
    def __getattr__(self, name):
        inst = get_learning_router()
        if inst is not None:
            return getattr(inst, name)
        return None
    def __bool__(self):
        return get_learning_router() is not None

limiter = _LimiterProxy()
assistant = _AssistantProxy()
socketio = _SocketIOProxy()
learning_router = _LearningRouterProxy()
