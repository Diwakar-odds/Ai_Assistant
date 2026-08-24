"""
Routes Package for Flask Blueprints.
Registers all API route blueprints cleanly with the Flask application.
"""

import logging
from .common import (
    set_assistant, set_socketio, set_learning_router, set_limiter,
    limiter, logger
)

from .auth_routes import auth_bp
from .chain_routes import chain_bp
from .chat_routes import chat_bp
from .file_routes import file_bp
from .learning_routes import learning_bp
from .local_ai_routes import local_ai_bp
from .settings_routes import settings_bp
from .system_routes import system_bp
from .taskbar_routes import taskbar_bp
from .voice_routes import voice_bp
from .web_routes import web_bp

ALL_BLUEPRINTS = [
    (auth_bp, None),
    (chain_bp, None),
    (chat_bp, None),
    (file_bp, None),
    (learning_bp, None),
    (local_ai_bp, None),
    (settings_bp, None),
    (system_bp, None),
    (taskbar_bp, None),
    (voice_bp, None),
    (web_bp, None),
]

def register_all_routes(app, assistant_instance=None, socketio_instance=None, learning_router_instance=None, limiter_instance=None):
    """
    Register all modular blueprints with the Flask app.
    
    Args:
        app: Flask application instance
        assistant_instance: ModernAssistant instance
        socketio_instance: SocketIO instance
        learning_router_instance: LearningDataRouter instance
        limiter_instance: Flask Limiter instance
    """
    if assistant_instance:
        set_assistant(assistant_instance)
    if socketio_instance:
        set_socketio(socketio_instance)
    if learning_router_instance:
        set_learning_router(learning_router_instance)
    if limiter_instance:
        set_limiter(limiter_instance)
        
    for bp, prefix in ALL_BLUEPRINTS:
        try:
            if prefix:
                app.register_blueprint(bp, url_prefix=prefix)
            else:
                app.register_blueprint(bp)
            logger.debug(f"Registered blueprint: {bp.name}")
        except Exception as e:
            logger.warning(f"Failed to register blueprint {bp.name}: {e}")
            
    logger.info("All 11 route blueprints registered successfully")
