# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Flask Blueprints Package

Organized route handlers for the Pulsar Assistant backend.
Each blueprint handles a specific domain of functionality.
"""

from flask import Blueprint

__all__ = [
    'register_all_blueprints',
]

def register_all_blueprints(app, assistant_instance):
    """
    Register all blueprints with the Flask app.
    
    Args:
        app: Flask application instance
        assistant_instance: ModernAssistant instance for route handlers
    """
    # Import blueprints here to avoid circular imports
    try:
        from . import chat
        app.register_blueprint(chat.create_blueprint(assistant_instance))
        logger.info("✅ Chat blueprint registered")
    except Exception as e:
        logger.warning(f"⚠️ Chat blueprint registration failed: {e}")
    
    try:
        from . import voice
        app.register_blueprint(voice.create_blueprint(assistant_instance))
        logger.info("✅ Voice blueprint registered")
    except Exception as e:
        logger.warning(f"⚠️ Voice blueprint registration failed: {e}")
    
    try:
        from . import apps
        app.register_blueprint(apps.create_blueprint(assistant_instance))
        logger.info("✅ Apps blueprint registered")
    except Exception as e:
        logger.warning(f"⚠️ Apps blueprint registration failed: {e}")
   
    try:
        from . import system
        app.register_blueprint(system.create_blueprint(assistant_instance))
        logger.info("✅ System blueprint registered")
    except Exception as e:
        logger.warning(f"⚠️ System blueprint registration failed: {e}")
    
    try:
        from . import auth
        app.register_blueprint(auth.create_blueprint(assistant_instance))
        logger.info("✅ Auth blueprint registered")
    except Exception as e:
        logger.warning(f"⚠️ Auth blueprint registration failed: {e}")
    
    try:
        from . import web
        app.register_blueprint(web.create_blueprint(assistant_instance))
        logger.info("✅ Web scraping blueprint registered")
    except Exception as e:
        logger.warning(f"⚠️ Web scraping blueprint registration failed: {e}")
    
    try:
        from . import learning
        app.register_blueprint(learning.create_blueprint(assistant_instance))
        logger.info("✅ Learning blueprint registered")
    except Exception as e:
        logger.warning(f"⚠️ Learning blueprint registration failed: {e}")
    
    try:
        from . import multimodal
        app.register_blueprint(multimodal.create_blueprint(assistant_instance))
        logger.info("✅ Multimodal blueprint registered")
    except Exception as e:
        logger.warning(f"⚠️ Multimodal blueprint registration failed: {e}")
    
    try:
        from . import preferences
        app.register_blueprint(preferences.create_blueprint(assistant_instance))
        logger.info("✅ Preferences blueprint registered")
    except Exception as e:
        logger.warning(f"⚠️ Preferences blueprint registration failed: {e}")
    
    try:
        from . import memory
        app.register_blueprint(memory.create_blueprint(assistant_instance))
        logger.info("✅ Memory & Language blueprint registered")
    except Exception as e:
        logger.warning(f"⚠️ Memory blueprint registration failed: {e}")
    
    try:
        from . import utilities
        app.register_blueprint(utilities.create_blueprint(assistant_instance))
        logger.info("✅ Utilities blueprint registered")
    except Exception as e:
        logger.warning(f"⚠️ Utilities blueprint registration failed: {e}")
    
    print(f"📋 All blueprints registered successfully")
