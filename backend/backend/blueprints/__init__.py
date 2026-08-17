"""
Flask Blueprints Package

Organized route handlers for the YourDaddy Assistant backend.
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
        print("✅ Chat blueprint registered")
    except Exception as e:
        print(f"⚠️ Chat blueprint registration failed: {e}")
    
    try:
        from . import voice
        app.register_blueprint(voice.create_blueprint(assistant_instance))
        print("✅ Voice blueprint registered")
    except Exception as e:
        print(f"⚠️ Voice blueprint registration failed: {e}")
    
    try:
        from . import apps
        app.register_blueprint(apps.create_blueprint(assistant_instance))
        print("✅ Apps blueprint registered")
    except Exception as e:
        print(f"⚠️ Apps blueprint registration failed: {e}")
   
    try:
        from . import system
        app.register_blueprint(system.create_blueprint(assistant_instance))
        print("✅ System blueprint registered")
    except Exception as e:
        print(f"⚠️ System blueprint registration failed: {e}")
    
    try:
        from . import auth
        app.register_blueprint(auth.create_blueprint(assistant_instance))
        print("✅ Auth blueprint registered")
    except Exception as e:
        print(f"⚠️ Auth blueprint registration failed: {e}")
    
    try:
        from . import web
        app.register_blueprint(web.create_blueprint(assistant_instance))
        print("✅ Web scraping blueprint registered")
    except Exception as e:
        print(f"⚠️ Web scraping blueprint registration failed: {e}")
    
    try:
        from . import learning
        app.register_blueprint(learning.create_blueprint(assistant_instance))
        print("✅ Learning blueprint registered")
    except Exception as e:
        print(f"⚠️ Learning blueprint registration failed: {e}")
    
    try:
        from . import multimodal
        app.register_blueprint(multimodal.create_blueprint(assistant_instance))
        print("✅ Multimodal blueprint registered")
    except Exception as e:
        print(f"⚠️ Multimodal blueprint registration failed: {e}")
    
    try:
        from . import preferences
        app.register_blueprint(preferences.create_blueprint(assistant_instance))
        print("✅ Preferences blueprint registered")
    except Exception as e:
        print(f"⚠️ Preferences blueprint registration failed: {e}")
    
    try:
        from . import memory
        app.register_blueprint(memory.create_blueprint(assistant_instance))
        print("✅ Memory & Language blueprint registered")
    except Exception as e:
        print(f"⚠️ Memory blueprint registration failed: {e}")
    
    try:
        from . import utilities
        app.register_blueprint(utilities.create_blueprint(assistant_instance))
        print("✅ Utilities blueprint registered")
    except Exception as e:
        print(f"⚠️ Utilities blueprint registration failed: {e}")
    
    print(f"📋 All blueprints registered successfully")
