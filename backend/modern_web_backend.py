import sys; sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8');
# YourDaddy Assistant - Modern Web Backend
"""
Modern Flask backend to serve the React frontend and provide real-time APIs
for YourDaddy Assistant's features.
"""
# print("Server Started ");
import warnings
warnings.simplefilter("ignore", category=FutureWarning)

import sys
import os
from pathlib import Path

# Force UTF-8 encoding for stdout/stderr to fix emoji display on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Fix python paths for new modular monorepo
backend_dir = Path(__file__).parent.absolute()
project_root = backend_dir.parent.absolute()
core_ai_src = project_root / 'core_ai' / 'src'
shared_dir = project_root / 'shared'

if str(core_ai_src) not in sys.path:
    sys.path.insert(0, str(core_ai_src))
if str(shared_dir) not in sys.path:
    sys.path.insert(0, str(shared_dir))


# Initialize new session (must be first import)
import utils.session_init
from utils.session_activity_logger import (
    log_api_request,
    log_system_command,
    log_user_interaction,
    session_activity_logger
)

from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, 
    get_jwt_identity, verify_jwt_in_request
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import sys
import time
import threading
import json
from datetime import datetime, timedelta
from pathlib import Path
import re
import secrets
import logging

# Import secure secrets manager
try:
    from ai_assistant.core.secrets_manager import get_secrets_manager, SecretsValidationError
    SECRETS_MANAGER_AVAILABLE = True
except ImportError:
    SECRETS_MANAGER_AVAILABLE = False
# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    sys.stderr.reconfigure(encoding='utf-8') if hasattr(sys.stderr, 'reconfigure') else None

# Load environment variables from absolute path
_env_path = Path(__file__).parent.parent.parent.parent / '.env'
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()

# Setup centralized logging
from utils.logging_config import get_logger, get_api_logger
from utils.user_data_logger import log_query, log_reply, log_action, log_module_usage
logger = get_logger('web_backend', log_category='backend')
api_logger = get_api_logger('api_requests')

logger.info("="*80)
logger.info("YourDaddy Assistant - Web Backend Starting")
logger.info("="*80)

# Add ai_assistant directory to sys.path to allow importing automation_tools_new and modules
current_dir = os.path.dirname(os.path.abspath(__file__))
ai_assistant_dir = os.path.dirname(current_dir)
if ai_assistant_dir not in sys.path:
    sys.path.append(ai_assistant_dir)

# Import Multi-Agent System
try:
    from ai_assistant.core.chain_of_actions_manager import get_chain_manager, ChainOfActionsManager
    from ai_assistant.core.progress_tracker import get_progress_tracker
    MULTI_AGENT_AVAILABLE = True
except ImportError as e:
    MULTI_AGENT_AVAILABLE = False
    logger.warning(f"Multi-Agent System not available: {e}")

# Import automation tools
try:
    # Try importing from ai_assistant package first
    from ai_assistant.automation import automation_tools_new as automation_tools
    # Import app discovery scheduler functions
    from ai_assistant.automation.app_discovery import (
        start_auto_refresh_after_startup, start_periodic_refresh
    )
    AUTOMATION_AVAILABLE = True
    print("✅ Automation tools loaded successfully")
except ImportError as e:
    print(f"⚠️Â Automation tools import failed: {e}")
    # Try fallback import from modules directly
    try:
        from ai_assistant.automation.app_discovery import (
            get_apps_for_web, refresh_app_database, 
            start_auto_refresh_after_startup, start_periodic_refresh
        )
        AUTOMATION_AVAILABLE = True
        print("✅ App discovery loaded from modules")
    except ImportError as e2:
        print(f"❌ App discovery also failed: {e2}")
        AUTOMATION_AVAILABLE = False

# Import Learning Router for automatic AI training
learning_router = None
LEARNING_ROUTER_AVAILABLE = True # Assume true, fallback to false later

def _get_learning_router_lazy():
    global learning_router, LEARNING_ROUTER_AVAILABLE
    if learning_router is None and LEARNING_ROUTER_AVAILABLE:
        try:
            from ai_assistant.ai.auto_learning_router import LearningDataRouter
            learning_router = LearningDataRouter()
            logger.info("✅ Learning router initialized - AI will learn from all interactions")
        except Exception as e:
            logger.warning(f"⚠️Â Learning router not available: {e}")
            LEARNING_ROUTER_AVAILABLE = False
            learning_router = None
    return learning_router

# Import Smart Memory Retrieval for answering from past conversations
memory_retriever = None
SMART_MEMORY_AVAILABLE = True

def _get_memory_retriever_lazy():
    global memory_retriever, SMART_MEMORY_AVAILABLE
    if memory_retriever is None and SMART_MEMORY_AVAILABLE:
        try:
            from ai_assistant.ai.smart_memory_retrieval import SmartMemoryRetrieval
            memory_retriever = SmartMemoryRetrieval()
            logger.info("✅ Smart memory retrieval initialized - AI can answer from past conversations")
        except Exception as e:
            logger.warning(f"⚠️Â Smart memory retrieval not available: {e}")
            SMART_MEMORY_AVAILABLE = False
            memory_retriever = None
    return memory_retriever

# Global AI Loading State
ai_models_ready = False
ai_models_status = "Not Started"

# We are using pure lazy loading for all heavy ML modules.
# They will be imported locally inside the functions that need them.
MULTIMODAL_AVAILABLE = True
CONVERSATIONAL_AI_AVAILABLE = True
MULTILINGUAL_AVAILABLE = True
ADVANCED_CHAT_AVAILABLE = True
LLM_PROVIDER_AVAILABLE = True
LOCAL_AI_AVAILABLE = True
ENHANCED_AI_AVAILABLE = True
USAGE_ANALYZER_AVAILABLE = True

try:
    from google_speech_websocket_handler import register_google_speech_handlers
    GOOGLE_SPEECH_WS_AVAILABLE = True
except ImportError:
    GOOGLE_SPEECH_WS_AVAILABLE = False
    def register_google_speech_handlers(*args, **kwargs):
        pass

# Lazy loaded instances
enhanced_ai = None
usage_analyzer = None

def _get_enhanced_ai_lazy():
    """Lazy load enhanced AI on first use"""
    global enhanced_ai
    if enhanced_ai is None and ENHANCED_AI_AVAILABLE:
        try:
            from ai_assistant.core.enhanced_integration import get_enhanced_ai
            enhanced_ai = get_enhanced_ai()
            logger.info("✅ Enhanced AI initialized (semantic cache, routing, streaming, emotion, verification)")
        except Exception as e:
            logger.warning(f"⚠️Â Enhanced AI not available: {e}")
    return enhanced_ai

def _get_usage_analyzer_lazy():
    """Lazy load usage analyzer on first use"""
    global usage_analyzer
    if usage_analyzer is None and USAGE_ANALYZER_AVAILABLE:
        try:
            from ai_assistant.ai.usage_pattern_analyzer import UsagePatternAnalyzer
            usage_analyzer = UsagePatternAnalyzer()
            logger.info("✅ Usage pattern analyzer initialized")
        except Exception as e:
            logger.warning(f"⚠️Â Usage analyzer not available: {e}")
    return usage_analyzer

# System monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Voice processing (lazy loaded)
VOICE_AVAILABLE = True

def _load_voice_modules():
    global VOICE_AVAILABLE
    try:
        import pvporcupine
        import sounddevice as sd
        import speech_recognition as sr
        import numpy as np
        import wave
        import base64
        import io
        return True
    except ImportError:
        VOICE_AVAILABLE = False
        return False

# Background Initialization Thread for AI Models
def initialize_heavy_ai_models():
    """Run in a background thread to pre-warm the AI models without blocking the UI"""
    global ai_models_ready, ai_models_status
    
    logger.info("🚀 Background AI Initialization started...")
    
    try:
        # 1. Start loading the Learning Router
        ai_models_status = "Loading Learning Matrix..."
        _get_learning_router_lazy()
        
        # 2. Load Smart Memory
        ai_models_status = "Loading Memory Matrix..."
        _get_memory_retriever_lazy()
        
        # 3. Load Enhanced AI (semantic cache, routers)
        ai_models_status = "Loading Semantic Engines..."
        _get_enhanced_ai_lazy()
        
        # 4. Load Usage Analyzer
        ai_models_status = "Loading Pattern Analyzer..."
        _get_usage_analyzer_lazy()
        
        # 5. Load Voice Engines
        ai_models_status = "Loading Voice Engines..."
        global vad_detector, noise_reducer
        try:
            from ai_assistant.voice.voice_activity_detection import VoiceActivityDetector
            vad_detector = VoiceActivityDetector()
            logger.info("✅ Voice Activity Detector initialized in background")
        except Exception as e:
            logger.warning(f"⚠️ VAD module not available: {e}")
            
        try:
            from ai_assistant.voice.noise_reduction import NoiseReductionSystem
            noise_reducer = NoiseReductionSystem()
            logger.info("✅ Noise Reduction initialized in background")
        except Exception as e:
            logger.warning(f"⚠️ Noise Reduction module not available: {e}")
            
        logger.info("✅ Background AI Initialization COMPLETE!")
    except Exception as e:
        logger.error(f"❌ Background AI Initialization failed: {e}")
    finally:
        ai_models_ready = True
        ai_models_status = "Ready"

def start_ai_background_thread():
    """Starts the AI loading thread. Called by desktop app or main."""
    import threading
    t = threading.Thread(target=initialize_heavy_ai_models, daemon=True)
    t.start()

# Load environment variables again if needed
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()

# Create Flask app
# Point to new web assets location
if getattr(sys, 'frozen', False):
    # If we are running in a PyInstaller bundle
    bundle_dir = sys._MEIPASS
    web_assets_dir = os.path.join(bundle_dir, 'web_assets')
else:
    # If we are running in normal Python environment
    web_assets_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'web-app', 'dist'))

template_dir = web_assets_dir
static_dir = web_assets_dir

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir, static_url_path='/')

# Security Configuration - Use secrets manager for secure key handling
# Helper to dynamically ensure secret keys are persisted in .env
def get_or_create_env_secret(name: str) -> str:
    env_val = os.getenv(name)
    if env_val:
        return env_val
        
    # Generate new stable random key
    new_key = secrets.token_hex(32)
    env_path = Path(__file__).parent.parent.parent.parent / '.env'
    
    try:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        content = ""
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
        # Append if not already present
        if name not in content:
            separator = "\n" if content and not content.endswith("\n") else ""
            with open(env_path, 'a', encoding='utf-8') as f:
                f.write(f"{separator}{name}={new_key}\n")
            logger.info(f"💾 Generated and saved stable {name} to .env")
        
        # Update os.environ immediately so it's loaded
        os.environ[name] = new_key
        return new_key
    except Exception as e:
        logger.warning(f"⚠️Â Could not write secret {name} to .env: {e}. Session will not persist across restarts.")
        return new_key

if SECRETS_MANAGER_AVAILABLE:
    try:
        secrets_mgr = get_secrets_manager()
        app.config['SECRET_KEY'] = secrets_mgr.get_or_generate('SECRET_KEY', 32)
        app.config['JWT_SECRET_KEY'] = secrets_mgr.get_or_generate('JWT_SECRET_KEY', 32)
    except Exception as e:
        logger.warning(f"Secrets manager error: {e}. Falling back to stable .env keys.")
        app.config['SECRET_KEY'] = get_or_create_env_secret('SECRET_KEY')
        app.config['JWT_SECRET_KEY'] = get_or_create_env_secret('JWT_SECRET_KEY')
else:
    app.config['SECRET_KEY'] = get_or_create_env_secret('SECRET_KEY')
    app.config['JWT_SECRET_KEY'] = get_or_create_env_secret('JWT_SECRET_KEY')

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

@limiter.request_filter
def exempt_localhost():
    """Exempt the local desktop app from all rate limits so health checks don't ban it."""
    return request.remote_addr in ('127.0.0.1', 'localhost', '::1')

# Secure CORS Configuration
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5000,http://127.0.0.1:3000,http://127.0.0.1:5000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:15000,http://127.0.0.1:15000').split(',')
CORS(app, resources={
    r"/api/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "supports_credentials": True,
        "expose_headers": ["Content-Type", "Authorization"]
    },
    r"/socket.io/*": {
        "origins": ALLOWED_ORIGINS,
        "supports_credentials": True
    }
})

# Initialize SocketIO for WebSocket support (single init with secure origins)
socketio = SocketIO(
    app,
    cors_allowed_origins=ALLOWED_ORIGINS,
    async_mode='threading',
    logger=False,  # Disable verbose logging
    engineio_logger=False,  # Disable engine.io logging
    ping_timeout=60,
    ping_interval=25
)

# Configure logging levels for production - silence socketio spam
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('socketio.server').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)
logging.getLogger('engineio.server').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

logger.info("✅ SocketIO initialized with CORS origins: %s", ALLOWED_ORIGINS)

# (Duplicate AVAILABLE_VOICES removed - single copy at line ~498)
# Import voice API blueprint
try:
    from voice_service import voice_bp, AVAILABLE_VOICES as VOICE_API_VOICES
    VOICE_API_AVAILABLE = True
    # Update AVAILABLE_VOICES if not already defined
    if 'AVAILABLE_VOICES' not in globals() or not AVAILABLE_VOICES:
        AVAILABLE_VOICES = VOICE_API_VOICES
except ImportError as e:
    logger.warning(f"Voice API blueprint not available: {e}")
    VOICE_API_AVAILABLE = False

# Import advanced voice processing modules
# We defer imports to avoid blocking the main thread
VAD_AVAILABLE = True
NOISE_REDUCTION_AVAILABLE = True
ASYNC_RECOGNIZER_AVAILABLE = True
VOICE_WEBSOCKET_AVAILABLE = True
GOOGLE_SPEECH_WS_AVAILABLE = True


# =============================================================================
# STARTUP OPTIMIZATION - Feature Toggle Configuration
# =============================================================================
# These environment variables control which features are enabled at startup
# to optimize loading time. Set to 'false' to disable optional features.

ENABLE_VOICE = os.getenv('ENABLE_VOICE', 'true').lower() == 'true'
ENABLE_MULTIMODAL = os.getenv('ENABLE_MULTIMODAL', 'true').lower() == 'true'
ENABLE_CONVERSATIONAL_AI = os.getenv('ENABLE_CONVERSATIONAL_AI', 'true').lower() == 'true'
ENABLE_SYSTEM_MONITORING = os.getenv('ENABLE_SYSTEM_MONITORING', 'true').lower() == 'true'
LAZY_INIT = os.getenv('LAZY_INIT', 'true').lower() == 'true'  # Lazy load components on first use
BACKGROUND_INIT = os.getenv('BACKGROUND_INIT', 'true').lower() == 'true'  # Initialize in background

logger.info("Ã°Å¸â€Â§ Startup Configuration:")
logger.info(f"  - Lazy Initialization: {LAZY_INIT}")
logger.info(f"  - Background Initialization: {BACKGROUND_INIT}")
logger.info(f"  - Voice Features: {ENABLE_VOICE}")
logger.info(f"  - Multimodal AI: {ENABLE_MULTIMODAL}")
logger.info(f"  - Conversational AI: {ENABLE_CONVERSATIONAL_AI}")
logger.info(f"  - System Monitoring: {ENABLE_SYSTEM_MONITORING}")

# =============================================================================
# GLOBAL: Local AI Manager
# =============================================================================

local_ai_manager = None
local_ai_initialized = False

def initialize_local_ai():
    """Initialize local AI model in background"""
    global local_ai_manager, local_ai_initialized
    
    if not LOCAL_AI_AVAILABLE:
        logger.warning("Local AI not available")
        return
    
    try:
        logger.info("Initializing Local AI Manager (Ollama)...")
        local_ai_manager = LocalAIManager()
        
        # Check if Ollama is running
        if not local_ai_manager.is_ollama_running():
            logger.warning("Ollama service is not running. Start it with 'ollama serve'")
            return
        
        # Check for available models using auto-detection
        model_name = local_ai_manager.find_best_available_model()
        
        if model_name:
            logger.info(f"Loading Ollama model: {model_name}")
            if local_ai_manager.load_model(model_name):
                local_ai_initialized = True
                logger.info("Local AI ready!")
            else:
                logger.error(f"Failed to load model: {model_name}")
        else:
            logger.warning("No Ollama models found. Download with:")
            logger.warning("  ollama pull llama3.2")
    
    except Exception as e:
        logger.error(f"Local AI initialization failed: {e}")


# ⚡ OPTIMIZATION: Lazy load Ollama - only initialize when user selects it
# This saves 30-60 seconds on startup!
# Ollama will be initialized on-demand when provider == 'ollama'
# 
# if BACKGROUND_INIT and LOCAL_AI_AVAILABLE:
#     threading.Thread(target=initialize_local_ai, daemon=True).start()

logger.info("⚡ Ollama will load on-demand (lazy loading enabled)")

# =============================================================================

# Available Voice Options for TTS - Unified from voice_service to prevent duplicates
from voice_service import AVAILABLE_VOICES









# Initialization Status Endpoint


# NOTE: SocketIO is already initialized at module level above (line ~363).
# A duplicate init here was causing CORS origin rejection errors.
# Removed to prevent overwriting the existing socketio instance.

# ============================================================
# PROFESSIONAL VOICE SYSTEM INITIALIZATION
# ============================================================
try:
    from voice_service import voice_bp, init_professional_voice_services
    
    # Register voice API blueprint
    app.register_blueprint(voice_bp, url_prefix='/api/voice')
    logger.info("✅ Voice API blueprint registered at /api/voice")
    
    # Initialize professional voice services with WebSocket support
    voice_initialized = init_professional_voice_services(socketio)
    
    if voice_initialized:
        logger.info("=" * 60)
        logger.info("🎙️ PROFESSIONAL VOICE SYSTEM ACTIVATED")
        logger.info("=" * 60)
        logger.info("✅ SmartWakeWordDetector - PocketSphinx (Offline)")
        logger.info("✅ NeuralVoiceEngine - Edge-TTS + Coqui")
        logger.info("✅ VoiceActivityDetector - WebRTC VAD")
        logger.info("✅ Speaker Recognition - Enabled")
        logger.info("✅ Advanced STT - Whisper + Google + Vosk")
        logger.info("✅ Noise Reduction - Active")
        logger.info("=" * 60)
    else:
        logger.warning("⚠️Â  Voice system running in limited mode")
        
except ImportError as e:
    logger.warning(f"⚠️Â  Professional voice system not available: {e}")
    logger.info("💡 Basic voice features still available via assistant")
except Exception as e:
    logger.error(f"❌ Voice system initialization failed: {e}")
    logger.info("💡 Server will continue without professional voice features")


# User Management (Simple in-memory store - replace with database in production)
# WARNING: Admin password MUST be set via environment variable for security
_admin_password = os.getenv('ADMIN_PASSWORD')
if not _admin_password:
    logger.warning(
        "⚠️  ADMIN_PASSWORD not set! Using temporary generated password. "
        "Set ADMIN_PASSWORD in your environment for production use."
    )
    _admin_password = secrets.token_urlsafe(16)
    # SECURITY: Never log passwords — print redacted notice only
    logger.warning("🔑 A temporary admin password has been generated. Set ADMIN_PASSWORD in .env to use a persistent one.")

USERS_DB = {
    "admin": {
        "password_hash": generate_password_hash(_admin_password),
        "role": "admin"
    }
}

# Clear the password from memory
del _admin_password

# Input Validation Patterns
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
    # Remove potentially dangerous characters
    dangerous_chars = ['|', '&', ';', '`', '$', '(', ')', '<', '>', '\n', '\r']
    for char in dangerous_chars:
        command = command.replace(char, '')
    return command.strip()[:500]  # Limit length

# =============================================================================
# IMPORT MODERN ASSISTANT CLASS (Extracted for Modularity)
# =============================================================================
# ModernAssistant has been extracted to ai_assistant/core/assistant.py
# This reduces this file from 4946 lines to ~3700 lines while maintaining
# all functionality. The class can now be reused by other modules.

from ai_assistant.core.assistant import ModernAssistant, set_socketio

# Inject SocketIO instance into the assistant module for system monitoring
set_socketio(socketio)


# Global assistant instance - protected initialization
try:
    print("[INFO] Initializing YourDaddy Assistant...")
    assistant = ModernAssistant()
    print("[OK] Assistant initialized successfully")
except Exception as e:
    print(f"[ERROR] CRITICAL: Assistant initialization failed: {e}")
    print("[OK]  Server will start in limited mode without some features")
    # Create a minimal assistant instance
    class MinimalAssistant:
        def __init__(self):
            self.multimodal_ai = None
            self.conversational_ai = None
            self.multilingual = None
            self.voice_listening = False
        
        def process_command(self, command):
            return f"I understand you said: '{command}'. However, some features are currently unavailable due to initialization errors. Please check the server logs."
        
        def get_real_time_system_stats(self):
            return {"timestamp": datetime.now().isoformat(), "cpu_usage": 0, "memory_usage": 0, "disk_usage": 0, "network_mbps": 0, "active_tasks": 0, "temperature": "N/A"}
        
        def get_init_status(self):
            return {
                'multimodal_ai': 'failed',
                'conversational_ai': 'failed',
                'multilingual': 'failed',
                'llm_chat': 'failed',
                'voice_system': 'failed',
                'memory': 'failed',
                'system_monitoring': 'failed'
            }
        
        def analyze_screen(self, prompt): return "Screen analysis unavailable"
        def answer_visual_question(self, question): return "Visual Q&A unavailable"
        def start_voice_listening(self): return {"error": "Voice features unavailable"}
        def stop_voice_listening(self): return {"error": "Voice features unavailable"}
        def speak_text(self, text): return False
        def process_voice_audio(self, audio_data): return {"error": "Audio processing unavailable"}
    
    assistant = MinimalAssistant()

# =============================================================================
# REGISTER BLUEPRINTS - Modular Route Organization
# =============================================================================
print("📋 Registering blueprints...")
try:
    from backend.routes import register_all_routes
    register_all_routes(
        app=app,
        assistant_instance=assistant,
        socketio_instance=socketio,
        learning_router_instance=learning_router if 'learning_router' in globals() else None,
        limiter_instance=limiter
    )
    print("✅ All blueprints registered")
except Exception as e:
    print(f"⚠️ Blueprint registration failed: {e}")
    import traceback
    traceback.print_exc()


# ============================================================
# LEGACY ROUTES (keep for old template compatibility)
# ============================================================







# Authentication Routes




# API Routes



# ==================== LEARNING SYSTEMS ENDPOINTS ====================
# Comprehensive API for all 27 learning systems

# Import Learning Dashboard API
try:
    from learning_dashboard_api import LearningDashboardAPI
    dashboard_api = LearningDashboardAPI()
    DASHBOARD_API_AVAILABLE = True
except ImportError as e:
    print(f"⚠️Â Dashboard API not available: {e}")
    dashboard_api = None
    DASHBOARD_API_AVAILABLE = False




















# ============================================================================
# JARVIS-Style Startup Sequence API Endpoints
# ============================================================================




# ============================================================================
# End of Startup Sequence API Endpoints
# ============================================================================

# ============================================================================
# ADVANCED FEATURES API ENDPOINTS
# ============================================================================







# ============================================================================
# End of Advanced Features API Endpoints
# ============================================================================


# Chat Streaming Session Management
chat_sessions = {}
chat_session_lock = threading.Lock()






# Enhanced Feature Endpoints for Full AI Integration











@app.route('/api/apps')
# Removed @jwt_required() to fix HTTP 401 error - public endpoint for app grid






# Activity feed endpoint

# Voice command history








# (Duplicate connect/disconnect/command handlers removed - using voice_service.py)
# Enhanced Chat SocketIO Events













# (Duplicate language/detect and language/translate routes removed - kept secured versions above)




# Multilingual SocketIO Events

# Duplicate handler removed - see handle_voice_audio above

# Error logging endpoint









# ============================================================
# MODEL SELECTION & PREFERENCES API ENDPOINTS
# ============================================================







# ============================================================
# LOCAL AI API ENDPOINTS
# ============================================================













# ============================================================
# FILE OPERATIONS API ENDPOINTS
# ============================================================






# ============================================================
# DOCUMENT OCR API ENDPOINTS
# ============================================================






# ============================================================
# WEB SCRAPING API ENDPOINTS
# ============================================================







# ============================================================
# TASKBAR DETECTION API ENDPOINTS
# ============================================================





# Enhanced Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        "error": "Not found",
        "message": "The requested resource was not found",
        "timestamp": datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred on the server",
        "timestamp": datetime.now().isoformat()
    }), 500

@app.errorhandler(400)
def bad_request_error(error):
    return jsonify({
        "error": "Bad request",
        "message": "The request was invalid or malformed",
        "timestamp": datetime.now().isoformat()
    }), 400

@app.errorhandler(503)
def service_unavailable_error(error):
    return jsonify({
        "error": "Service unavailable",
        "message": "The service is temporarily unavailable",
        "timestamp": datetime.now().isoformat()
    }), 503

# Define fallback functions for when automation tools are not available
if not AUTOMATION_AVAILABLE:
    def write_a_note(*args, **kwargs): return "Note taking not available"
    def open_application(app_name, *args, **kwargs): 
        # SECURITY: Whitelist of safe application executables to prevent RCE
        SAFE_APPS = {
            'notepad': 'notepad.exe',
            'calculator': 'calc.exe',
            'calc': 'calc.exe',
            'paint': 'mspaint.exe',
            'mspaint': 'mspaint.exe',
            'chrome': 'chrome.exe',
            'firefox': 'firefox.exe',
            'edge': 'msedge.exe',
            'cmd': 'cmd.exe',
            'terminal': 'wt.exe',
            'explorer': 'explorer.exe',
            'taskmgr': 'taskmgr.exe',
            'task manager': 'taskmgr.exe',
            'control': 'control.exe',
            'control panel': 'control.exe',
            'code': 'code.exe',
            'vscode': 'code.exe',
            'vlc': 'vlc.exe',
            'spotify': 'spotify.exe',
            'whatsapp': 'whatsapp.exe',
            'discord': 'discord.exe',
            'slack': 'slack.exe',
            'teams': 'teams.exe',
            'word': 'winword.exe',
            'excel': 'excel.exe',
            'powerpoint': 'powerpnt.exe',
        }
        
        try:
            # Try to use Intent Recognizer for app name normalization
            try:
                import sys
                import os
                # Add ai_assistant to path if not already there
                ai_assistant_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if ai_assistant_dir not in sys.path:
                    sys.path.insert(0, ai_assistant_dir)
                
                from ai_assistant.ai.intent_recognizer import IntentRecognizer
                recognizer = IntentRecognizer()
                
                # Normalize the app name to handle variations like "whats app" -> "whatsapp"
                normalized_app = recognizer.normalize_app_name(app_name)
                print(f"[Intent Recognizer] Normalized '{app_name}' -> '{normalized_app}'")
                app_name = normalized_app
            except Exception as intent_error:
                # If intent recognizer fails, continue with original app name
                print(f"[Intent Recognizer] Not available: {intent_error}")
            
            # SECURITY: Look up the app in the whitelist — never pass raw user input to shell
            safe_executable = SAFE_APPS.get(app_name.lower().strip())
            if safe_executable:
                import shutil
                exe_path = shutil.which(safe_executable)
                if exe_path:
                    subprocess.Popen([exe_path], shell=False)
                else:
                    subprocess.Popen([safe_executable], shell=False)
                return f"Opened {app_name}"
            else:
                # App not in whitelist — use Start menu search as safe alternative
                try:
                    import pyautogui
                    import time
                    # Validate app_name contains only safe characters
                    import re
                    if not re.match(r'^[\w\s\-.]+$', app_name):
                        return f"Invalid application name: '{app_name}'"
                    pyautogui.hotkey('win', 'd')
                    time.sleep(0.5)
                    pyautogui.press('win')
                    time.sleep(0.5)
                    pyautogui.write(app_name, interval=0.05)
                    time.sleep(1)
                    pyautogui.press('enter')
                    return f"Tried to open '{app_name}' via Start menu."
                except Exception as e2:
                    return f"Could not find '{app_name}' on your system. Try saying the full application name or check if it's installed."
        except Exception as e:
            return f"Could not find '{app_name}' on your system. Try saying the full application name or check if it's installed."
    def search_google(*args, **kwargs): return "Google search not available"
    def search_youtube(*args, **kwargs): return "YouTube search not available"
    def close_application(*args, **kwargs): return "App closing not available"
    def speak(*args, **kwargs): return "Text-to-speech not available"
    def set_system_volume(*args, **kwargs): return "Volume control not available"
    def get_app_path_from_name(*args, **kwargs): return None
    def setup_memory(*args, **kwargs): return True
    def save_to_memory(*args, **kwargs): return True
    def get_memory(*args, **kwargs): return "Memory not available"
    def search_memory(*args, **kwargs): return "Memory search not available"
    def get_conversation_summary(*args, **kwargs): return "Conversation history not available"
    def save_knowledge(*args, **kwargs): return "Knowledge saving not available"
    def get_knowledge(*args, **kwargs): return "Knowledge retrieval not available"
    def discover_applications(*args, **kwargs): return "App discovery completed (fallback)"
    def smart_open_application(app_name, *args, **kwargs): return open_application(app_name)
    def list_installed_apps(*args, **kwargs): 
        return [
            {"name": "Notepad", "path": "notepad.exe"},
            {"name": "Calculator", "path": "calc.exe"},
            {"name": "Paint", "path": "mspaint.exe"}
        ]
    
    def get_apps_for_web(*args, **kwargs):
        return [
            {"name": "Chrome", "path": "chrome.exe", "category": "Browser", "usage": 89, "description": "Google Chrome web browser"},
            {"name": "Mail", "path": "mail.exe", "category": "Communication", "usage": 76, "description": "Email application"},
            {"name": "Documents", "path": "word.exe", "category": "Productivity", "usage": 65, "description": "Document editor"},
            {"name": "Photos", "path": "photos.exe", "category": "Media", "usage": 52, "description": "Photo viewer"},
            {"name": "Videos", "path": "vlc.exe", "category": "Media", "usage": 43, "description": "Video player"},
            {"name": "Code", "path": "code.exe", "category": "Development", "usage": 92, "description": "Code editor"},
            {"name": "Database", "path": "pgadmin.exe", "category": "Development", "usage": 67, "description": "Database administration"},
            {"name": "Terminal", "path": "cmd.exe", "category": "System Tools", "usage": 78, "description": "Command line interface"},
            {"name": "Calculator", "path": "calc.exe", "category": "System Tools", "usage": 45, "description": "Windows calculator"},
            {"name": "Notepad", "path": "notepad.exe", "category": "System Tools", "usage": 30, "description": "Simple text editor"},
            {"name": "Paint", "path": "mspaint.exe", "category": "System Tools", "usage": 25, "description": "Image editor"},
            {"name": "Control Panel", "path": "control.exe", "category": "System Tools", "usage": 20, "description": "System settings"},
            {"name": "Task Manager", "path": "taskmgr.exe", "category": "System Tools", "usage": 35, "description": "Process manager"}
        ]
    def get_system_status(*args, **kwargs): 
        if PSUTIL_AVAILABLE:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('C:\\' if os.name == 'nt' else '/').percent
            }
        return {"cpu_percent": 0, "memory_percent": 0, "disk_percent": 0}
    def get_running_processes(*args, **kwargs): return []
    def cleanup_temp_files(*args, **kwargs): return "Cleanup not available"
    def get_network_info(*args, **kwargs): return {"status": "unavailable"}
    def get_upcoming_events(*args, **kwargs): return []
    def get_inbox_summary(*args, **kwargs): return {"count": 0}
    def get_spotify_status(*args, **kwargs): return {"is_playing": False, "track_name": "Spotify not available", "artist_name": "N/A"}
    def spotify_play_pause(*args, **kwargs): return "Spotify control not available"
    def spotify_next_track(*args, **kwargs): return "Spotify control not available"
    def spotify_previous_track(*args, **kwargs): return "Spotify control not available"
    def search_and_play_spotify(*args, **kwargs): return "Spotify search not available"
    def get_weather_info(*args, **kwargs): return {"temperature": "22°C", "description": "Weather service not configured"}
    def get_latest_news(*args, **kwargs): return []
    def get_stock_price(*args, **kwargs): return "N/A"
    def detect_taskbar_apps(*args, **kwargs): return []
    def can_see_taskbar(*args, **kwargs): return False

# Voice models are initialized in background thread (initialize_heavy_ai_models)
vad_detector = None
noise_reducer = None

# Register voice API blueprint if available (skip if already registered above)
if VOICE_API_AVAILABLE and 'voice_bp' in globals():
    try:
        # Check if already registered to avoid duplicate error
        if not any(bp.name == 'voice' for bp in app.blueprints.values()):
            app.register_blueprint(voice_bp, url_prefix='/api/voice')
            logger.info("✅ Voice API blueprint registered at /api/voice")
            logger.info(f"   - GET /api/voice/list (12 voices available)")
            logger.info(f"   - POST /api/voice/preview (voice preview generation)")
            logger.info(f"   - GET /api/voice/cache/stats (cache monitoring)")
        else:
            logger.info("✅ Voice API blueprint already registered (skipping duplicate)")
    except Exception as e:
        logger.error(f"Failed to register voice API blueprint: {e}")
else:
    if not VOICE_API_AVAILABLE:
        logger.warning("⚠️  Voice API blueprint not available")

# (Redundant voice WebSocket handler registration removed during consolidation)

# ============================================================
# CHAT & VOICE INTEGRATION (handlers registered via voice_service.py)
# ============================================================
try:
    # System stats broadcaster with caching
    _stats_cache = {'data': None, 'timestamp': 0}
    STATS_CACHE_DURATION = 2  # Cache for 2 seconds
    BROADCAST_INTERVAL = 3  # Broadcast every 3 seconds
    
    def get_cached_stats():
        """Get system stats with caching to reduce CPU usage"""
        current_time = time.time()
        if _stats_cache['data'] and (current_time - _stats_cache['timestamp']) < STATS_CACHE_DURATION:
            return _stats_cache['data']
        
        try:
            if PSUTIL_AVAILABLE:
                stats = assistant.get_real_time_system_stats()
                _stats_cache['data'] = stats
                _stats_cache['timestamp'] = current_time
                return stats
        except Exception as e:
            logger.error(f'Stats collection error: {e}', exc_info=True)
        return None
    
    def broadcast_system_stats():
        """Broadcast system statistics every 3 seconds with caching"""
        while True:
            try:
                stats = get_cached_stats()
                if stats:
                    # Only broadcast essential stats to reduce bandwidth
                    broadcast_stats = {
                        'cpu_usage': stats.get('cpu_usage', 0),
                        'memory_usage': stats.get('memory_usage', 0),
                        'disk_usage': stats.get('disk_usage', 0),
                        'network_speed': stats.get('network_mbps', 0)
                    }
                    socketio.emit('system_stats_update', broadcast_stats)
            except Exception as e:
                logger.error(f'Stats broadcast error: {e}')
            time.sleep(BROADCAST_INTERVAL)

    # Start stats broadcaster
    stats_thread = threading.Thread(target=broadcast_system_stats, daemon=True)
    stats_thread.start()
    
    
    logger.info("✅ Chat & Voice Socket.IO handlers registered")
    
except Exception as e:
    logger.error(f"Failed to register chat/voice handlers: {e}")


# ============================================================
# MULTI-AGENT ACTION CHAIN ROUTES
# ============================================================








# WebSocket Broadcaster for Chain Progress
def _broadcast_chain_progress(progress):
    """Broadcast chain progress via WebSocket"""
    try:
        socketio.emit(
            'chain_progress',
            progress.to_dict(),
            namespace='/'
        )
    except Exception as e:
        logger.error(f"WebSocket broadcast error: {e}")




# ============================================================
# UNIFIED DASHBOARD ROUTES
# ============================================================




# SocketIO Handlers
try:
    import websockets
except Exception as e:
    logger.debug(f'Websockets module note: {e}')

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 YourDaddy Assistant - Modern Web Backend")
    print("=" * 60)
    print("Ã°Å¸Å’Â Server starting on: http://localhost:5000")
    print("Ã¢Å¡â€ºÃ¯Â¸Â  Bolt.ai React UI (Monochrome Steel Design)")
    print("⚡ Real-time features enabled via WebSockets")
    print("Ã°Å¸â€Â§ API endpoints available at /api/*")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        # Bind to localhost only for security
        host = os.getenv('HOST', '127.0.0.1')
        port = int(os.getenv('PORT', 5000))
        
        print(f"[OK] Security: JWT authentication enabled")
        print(f"[OK] Security: Rate limiting enabled")
        print(f"[OK] Security: CORS restricted to: {', '.join(ALLOWED_ORIGINS)}")
        print(f"[OK] Security: Host binding: {host}")
        print("")
        print("[OK]  Security: Admin credentials configured")
        print("[OK]  SECURITY: Ensure ADMIN_PASSWORD is set in .env file for production!")
        print("")
        
        # Initialize secure keys from OS Credential Store into environment
        try:
            from ai_assistant.utils.secure_storage import get_secure_key
            env_map = {
                "googleGemini": "GOOGLE_GEMINI_API_KEY",
                "openAI": "OPENAI_API_KEY",
                "elevenLabs": "ELEVEN_LABS_API_KEY"
            }
            for key_name, env_name in env_map.items():
                val = get_secure_key(key_name)
                if val:
                    os.environ[env_name] = val
                    logger.info(f"Ã°Å¸â€â€˜ Stored Key '{key_name}' loaded into environment at startup.")
        except Exception as e:
            logger.warning(f"⚠️Â Failed to load secure keys at startup: {e}")
            
        # Start app discovery schedulers (non-blocking)
        if AUTOMATION_AVAILABLE:
            # Start delayed refresh 5 minutes after server starts (to not slow down startup)
            start_auto_refresh_after_startup(delay_seconds=300)  # 5 minutes
            # Start weekly periodic refresh
            start_periodic_refresh(interval_hours=168)  # 168 hours = 1 week
        
        # Start robust system monitoring
        try:
            from backend.system_monitor import start_system_monitor
            start_system_monitor(socketio)
            print("✅ System monitoring started")
        except ImportError as e:
            print(f"⚠️Â Could not start system monitoring: {e}")
        
        # Register Google Speech Recognition WebSocket handlers
        if GOOGLE_SPEECH_WS_AVAILABLE:
            try:
                register_google_speech_handlers(socketio)
                print("✅ Google Speech Recognition WebSocket handlers registered")
            except Exception as e:
                print(f"⚠️Â Could not register Google Speech handlers: {e}")
        
        # Register improved command handlers with proper routing
        try:
            print(f"Ã°Å¸â€Â DEBUG: socketio type = {type(socketio)}, value = {socketio}")
            import voice_service as chat_handlers
            chat_handlers.set_socketio(socketio)
            chat_handlers.set_learning_router(learning_router if 'learning_router' in globals() else None)
            print("✅ Command handlers registered with local-first routing")
        except Exception as e:
            print(f"⚠️Â Could not register command handlers: {e}")
            import traceback
            traceback.print_exc()

        # Start AI models background initialization
        try:
            start_ai_background_thread()
            print("✅ AI background thread started")
        except Exception as e:
            print(f"⚠️ Could not start AI background thread: {e}")

        socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"[ERROR] Server failed to start: {e}")
        sys.exit(1)







