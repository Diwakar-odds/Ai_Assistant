"""
YourDaddy AI Assistant - Flask Application Factory

This is the main Flask application initialization module.
It sets up the Flask app, SocketIO, CORS, JWT, and rate limiting.
"""

import os
import sys
import secrets
import logging
from pathlib import Path
from datetime import timedelta
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    sys.stderr.reconfigure(encoding='utf-8') if hasattr(sys.stderr, 'reconfigure') else None

# Load environment variables
load_dotenv()

# Setup logging
from utils.logging_config import get_logger
logger = get_logger('backend', log_category='backend')

# Add ai_assistant to path
current_dir = os.path.dirname(os.path.abspath(__file__))
ai_assistant_dir = os.path.dirname(current_dir)
if ai_assistant_dir not in sys.path:
    sys.path.append(ai_assistant_dir)


def create_app():
    """
    Create and configure the Flask application
    
    Returns:
        tuple: (app, socketio) - Flask app and SocketIO instance
    """
    logger.info("="*80)
    logger.info("YourDaddy AI Assistant - Backend Starting")
    logger.info("="*80)
    
    # Create Flask app
    app = Flask(__name__)
    
    # Security Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY') or secrets.token_hex(32)
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
    
    # Initialize JWT
    jwt = JWTManager(app)
    
    # Initialize Rate Limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour", "50 per minute"],
        storage_uri="memory://"
    )
    
    # Store limiter on app for use in routes
    app.limiter = limiter
    
    # CORS Configuration
    allowed_origins = os.getenv(
        'ALLOWED_ORIGINS',
        'http://localhost:3000,http://localhost:5000,http://127.0.0.1:3000,'
        'http://127.0.0.1:5000,http://localhost:5173,http://127.0.0.1:5173'
    ).split(',')
    
    CORS(app, resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"],
            "supports_credentials": True,
            "expose_headers": ["Content-Type", "Authorization"]
        },
        r"/socket.io/*": {
            "origins": allowed_origins,
            "supports_credentials": True
        }
    })
    
    # Initialize SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins=allowed_origins,
        async_mode='threading',
        logger=False,
        engineio_logger=False,
        ping_timeout=60,
        ping_interval=25
    )
    
    logger.info(f"✅ Flask app initialized")
    logger.info(f"✅ CORS configured for origins: {allowed_origins}")
    logger.info(f"✅ SocketIO initialized")
    
    # Store socketio on app for use in routes
    app.socketio = socketio
    
    return app, socketio


def initialize_components():
    """
    Initialize AI components and automation tools
    
    Returns:
        dict: Dictionary of initialized components
    """
    components = {
        'automation_available': False,
        'multimodal_available': False,
        'voice_available': False,
        'learning_router': None,
        'memory_retriever': None
    }
    
    # Import automation tools
    try:
        from automation_tools_new import (
            write_a_note, open_application, search_google, search_youtube,
            close_application, speak, set_system_volume, get_app_path_from_name,
            setup_memory, save_to_memory, get_memory, search_memory,
            discover_applications, smart_open_application, list_installed_apps
        )
        components['automation_available'] = True
        logger.info("✅ Automation tools loaded")
        
        # Initialize memory
        try:
            setup_memory()
            logger.info("✅ Memory system initialized")
        except Exception as e:
            logger.error(f"Memory initialization failed: {e}")
            
    except ImportError as e:
        logger.warning(f"Automation tools not available: {e}")
    
    # Import learning router
    try:
        from auto_learning_router import LearningDataRouter
        components['learning_router'] = LearningDataRouter()
        logger.info("✅ Learning router initialized")
    except Exception as e:
        logger.warning(f"Learning router not available: {e}")
    
    # Import smart memory retrieval
    try:
        from smart_memory_retrieval import SmartMemoryRetrieval
        components['memory_retriever'] = SmartMemoryRetrieval()
        logger.info("✅ Smart memory retrieval initialized")
    except Exception as e:
        logger.warning(f"Smart memory not available: {e}")
    
    # Import multimodal AI
    try:
        from ai_assistant.multimodal import MultiModalAI
        components['multimodal_available'] = True
        logger.info("✅ Multimodal AI available")
    except ImportError:
        logger.warning("Multimodal AI not available")
    
    # Import voice processing
    try:
        import vosk
        import pyaudio
        import speech_recognition as sr
        components['voice_available'] = True
        logger.info("✅ Voice processing available")
    except ImportError:
        logger.warning("Voice processing not available")
    
    return components


# Global app and socketio instances (created by create_app)
app = None
socketio = None


if __name__ == "__main__":
    # Create app and run
    app, socketio = create_app()
    components = initialize_components()
    
    # Import and register routes
    from . import routes
    routes.register_routes(app, components)
    
    # Import and register WebSocket handlers
    from . import websocket
    websocket.register_handlers(socketio, components)
    
    # Run the app
    port = int(os.getenv('BACKEND_PORT', 5000))
    logger.info(f"🚀 Starting server on port {port}")
    socketio.run(app, debug=True, host='0.0.0.0', port=port)
