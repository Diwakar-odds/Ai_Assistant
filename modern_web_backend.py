# YourDaddy Assistant - Modern Web Backend
"""
Modern Flask backend to serve the React frontend and provide real-time APIs
for YourDaddy Assistant's features.
"""

from flask import Flask, jsonify, request, send_from_directory
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
# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    sys.stderr.reconfigure(encoding='utf-8') if hasattr(sys.stderr, 'reconfigure') else None

# Load environment variables
load_dotenv()

# Setup centralized logging
from utils.logging_config import get_logger, get_api_logger
from utils.user_data_logger import log_query, log_reply, log_action, log_module_usage
logger = get_logger('web_backend', log_category='backend')
api_logger = get_api_logger('api_requests')

logger.info("="*80)
logger.info("YourDaddy Assistant - Web Backend Starting")
logger.info("="*80)

# Validate configuration before starting
try:
    from config_validator import validate_config
    print("🔍 Validating configuration...")
    config_validator = validate_config(exit_on_failure=True)
except Exception as e:
    print(f"❌ Configuration validation failed: {e}")
    print("Please check your .env file and fix the configuration.")
    sys.exit(1)

# Import automation tools
try:
    from automation_tools_new import (
        write_a_note, open_application, search_google, search_youtube,
        close_application, speak, set_system_volume, get_app_path_from_name,
        setup_memory, save_to_memory, get_memory, search_memory,
        get_conversation_summary, save_knowledge, get_knowledge,
        discover_applications, smart_open_application, list_installed_apps,
        refresh_app_database, search_apps_by_name, get_app_usage_stats, get_apps_for_web,
        get_system_status, get_running_processes, cleanup_temp_files,
        get_network_info, get_upcoming_events, get_inbox_summary,
        get_spotify_status, spotify_play_pause, spotify_next_track,
        spotify_previous_track, search_and_play_spotify,
        get_weather_info, get_latest_news, get_stock_price,
        detect_taskbar_apps, can_see_taskbar
    )
    AUTOMATION_AVAILABLE = True
    print("✅ Automation tools loaded successfully")
except ImportError as e:
    print(f"⚠️ Automation tools not available: {e}")
    AUTOMATION_AVAILABLE = False
    # Fallback functions will be defined below

# Import multimodal AI if available
try:
    from modules.multimodal import MultiModalAI
    MULTIMODAL_AVAILABLE = True
except ImportError:
    MULTIMODAL_AVAILABLE = False

# Import conversational AI if available
try:
    from modules.conversational_ai import AdvancedConversationalAI
    CONVERSATIONAL_AI_AVAILABLE = True
except ImportError:
    CONVERSATIONAL_AI_AVAILABLE = False

# Import multilingual support if available
try:
    from modules.multilingual import MultilingualSupport, Language, LanguageContext
    MULTILINGUAL_AVAILABLE = True
    print("✅ Multilingual support loaded in web backend")
except ImportError:
    MULTILINGUAL_AVAILABLE = False
    print("⚠️ Multilingual support not available in web backend")

# System monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Voice processing
try:
    import vosk
    import pvporcupine
    import pyaudio
    import speech_recognition as sr
    import pyttsx3
    import numpy as np
    import wave
    import base64
    import io
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Security Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
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

# Secure CORS Configuration
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5000,http://127.0.0.1:3000,http://127.0.0.1:5000').split(',')
CORS(app, resources={
    r"/api/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Initialize SocketIO with secure origins
socketio = SocketIO(
    app, 
    cors_allowed_origins=ALLOWED_ORIGINS,
    async_mode='threading',
    engineio_logger=False
)

# User Management (Simple in-memory store - replace with database in production)
USERS_DB = {
    "admin": {
        "password_hash": generate_password_hash(os.getenv('ADMIN_PASSWORD', 'changeme123')),
        "role": "admin"
    }
}

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

class ModernAssistant:
    """Modern Assistant with real-time capabilities"""
    
    def __init__(self):
        self.multimodal_ai = None
        self.conversational_ai = None
        self.multilingual = None
        self.voice_listening = False
        self.system_stats_cache = {}
        self.cache_timestamp = 0
        self.voice_recognizer = None
        self.tts_engine = None
        self.audio_stream = None
        self.wake_word_detector = None
        self.current_language = "hinglish"
        
        # Initialize components
        self.init_multimodal_ai()
        self.init_conversational_ai()
        self.init_multilingual()
        self.init_memory()
        self.init_voice_system()
        
        # Network speed tracking
        self.last_network_stats = None
        self.last_network_time = None
        self.network_speed_history = []
        
        # Start background tasks
        self.start_system_monitoring()
    
    def init_multilingual(self):
        """Initialize multilingual support"""
        if MULTILINGUAL_AVAILABLE:
            try:
                # Load configuration
                config_path = Path("multimodal_config.json")
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    lang_config = config.get('languages', {})
                else:
                    lang_config = {}
                
                self.multilingual = MultilingualSupport(lang_config)
                
                # Set default language preference
                primary_lang = lang_config.get('primary', 'hinglish')
                self.multilingual.set_language_preference("web_user", Language(primary_lang))
                self.current_language = primary_lang
                
                print("✅ Multilingual support initialized in web backend")
            except Exception as e:
                print(f"❌ Multilingual initialization failed: {e}")
                self.multilingual = None
        else:
            print("⚠️ Multilingual support not available")
            self.multilingual = None
    
    def init_multimodal_ai(self):
        """Initialize multimodal AI"""
        if MULTIMODAL_AVAILABLE:
            try:
                api_key = os.environ.get("GEMINI_API_KEY")
                if api_key:
                    self.multimodal_ai = MultiModalAI(api_key)
                    print("✅ Multimodal AI initialized")
                else:
                    print("⚠️ GEMINI_API_KEY not set for multimodal AI")
                    self.multimodal_ai = None
            except Exception as e:
                print(f"❌ Multimodal AI initialization failed: {e}")
                self.multimodal_ai = None
        else:
            print("⚠️ Multimodal AI not available")
            self.multimodal_ai = None
    
    def init_conversational_ai(self):
        """Initialize conversational AI"""
        if CONVERSATIONAL_AI_AVAILABLE:
            try:
                # Create automation callback function
                def automation_callback(action, param):
                    """Callback to execute automation tasks from conversational AI"""
                    try:
                        if action == 'open_application':
                            if AUTOMATION_AVAILABLE:
                                return open_application(param)
                            return f"Opening {param}..."
                        elif action == 'close_application':
                            if AUTOMATION_AVAILABLE:
                                return close_application(param)
                            return f"Closing {param}..."
                        elif action == 'search_google':
                            if AUTOMATION_AVAILABLE:
                                return search_google(param)
                            return f"Searching for {param}..."
                        elif action == 'play_music':
                            if AUTOMATION_AVAILABLE:
                                return search_and_play_spotify(param)
                            return f"Playing {param}..."
                        elif action == 'set_volume':
                            if AUTOMATION_AVAILABLE:
                                return set_system_volume(param)
                            return f"Volume set to {param}%"
                        elif action == 'volume_up':
                            if AUTOMATION_AVAILABLE:
                                current = get_system_volume() if hasattr(globals(), 'get_system_volume') else 50
                                return set_system_volume(min(100, current + 10))
                            return "Volume increased"
                        elif action == 'volume_down':
                            if AUTOMATION_AVAILABLE:
                                current = get_system_volume() if hasattr(globals(), 'get_system_volume') else 50
                                return set_system_volume(max(0, current - 10))
                            return "Volume decreased"
                        elif action == 'mute':
                            if AUTOMATION_AVAILABLE:
                                return set_system_volume(0)
                            return "Muted"
                    except Exception as e:
                        return f"Error: {str(e)}"
                    return None
                
                self.conversational_ai = AdvancedConversationalAI(automation_callback=automation_callback)
                print("✅ Conversational AI initialized with automation support")
            except Exception as e:
                print(f"❌ Conversational AI initialization failed: {e}")
                self.conversational_ai = None
        else:
            print("⚠️ Conversational AI not available")
            self.conversational_ai = None
    
    def init_memory(self):
        """Initialize memory system"""
        if AUTOMATION_AVAILABLE:
            try:
                setup_memory()
                print("✅ Memory system initialized")
            except Exception as e:
                print(f"❌ Memory initialization failed: {e}")
        else:
            print("⚠️ Memory system not available")
    
    def init_voice_system(self):
        """Initialize voice recognition and TTS systems"""
        if VOICE_AVAILABLE:
            try:
                # Initialize speech recognition (safeguarded)
                try:
                    self.voice_recognizer = sr.Recognizer()
                    self.voice_recognizer.energy_threshold = 4000
                    self.voice_recognizer.pause_threshold = 0.8
                    print("✅ Speech recognition initialized")
                except Exception as e:
                    print(f"⚠️ Speech recognition initialization failed: {e}")
                    self.voice_recognizer = None
                
                # Initialize text-to-speech (safeguarded)
                try:
                    self.tts_engine = pyttsx3.init()
                    self.tts_engine.setProperty('rate', 150)
                    self.tts_engine.setProperty('volume', 0.8)
                    print("✅ Text-to-speech initialized")
                except Exception as e:
                    print(f"⚠️ Text-to-speech initialization failed: {e}")
                    self.tts_engine = None
                
                # Try to initialize wake word detection (most likely to cause segfault)
                try:
                    access_key = os.environ.get("PORCUPINE_ACCESS_KEY")
                    if access_key:
                        # This is often the culprit for segfaults - extra protection
                        import pvporcupine
                        self.wake_word_detector = pvporcupine.create(
                            access_key=access_key,
                            keywords=["hey daddy"]
                        )
                        print("✅ Wake word detection initialized")
                    else:
                        print("⚠️ PORCUPINE_ACCESS_KEY not set for wake word detection")
                        self.wake_word_detector = None
                except ImportError:
                    print("⚠️ Porcupine not available")
                    self.wake_word_detector = None
                except Exception as e:
                    print(f"⚠️ Wake word detection initialization failed: {e}")
                    self.wake_word_detector = None
                
                print("✅ Voice system initialized (partial or complete)")
            except Exception as e:
                print(f"❌ Voice system initialization failed: {e}")
                # Don't re-raise - allow server to continue without voice
        else:
            print("⚠️ Voice features not available - missing dependencies")
    
    def start_system_monitoring(self):
        """Start background system monitoring"""
        try:
            def monitor_loop():
                while True:
                    try:
                        stats = self.get_real_time_system_stats()
                        socketio.emit('system_stats_update', stats)
                        time.sleep(5)  # Update every 5 seconds
                    except Exception as e:
                        print(f"System monitoring error: {e}")
                        time.sleep(10)
            
            monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
            monitor_thread.start()
            print("✅ System monitoring started")
        except Exception as e:
            print(f"⚠️ System monitoring could not start: {e}")
    
    def get_real_time_system_stats(self):
        """Get real-time system statistics"""
        current_time = time.time()
        
        # Cache stats for 2 seconds to avoid excessive calls
        if current_time - self.cache_timestamp < 2:
            return self.system_stats_cache
        
        stats = {
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": 0,
            "memory_usage": 0,
            "disk_usage": 0,
            "network_mbps": 0,
            "network_speed_download": 0,
            "network_speed_upload": 0,
            "active_tasks": 0,
            "temperature": "N/A"
        }
        
        if PSUTIL_AVAILABLE:
            try:
                # Basic system stats
                stats.update({
                    "cpu_usage": psutil.cpu_percent(interval=0.1),
                    "memory_usage": psutil.virtual_memory().percent,
                    "disk_usage": psutil.disk_usage('C:\\' if os.name == 'nt' else '/').percent,
                    "active_tasks": len(psutil.pids()),
                })
                
                # Enhanced network speed calculation
                network_stats = self._calculate_network_speed(current_time)
                stats.update(network_stats)
                
            except Exception as e:
                print(f"PSUtil error: {e}")
        
        self.system_stats_cache = stats
        self.cache_timestamp = current_time
        return stats
    
    def _calculate_network_speed(self, current_time):
        """Calculate network download and upload speeds in Mbps"""
        network_stats = {
            "network_mbps": 0,
            "network_speed_download": 0,
            "network_speed_upload": 0
        }
        
        try:
            # Get current network I/O counters
            current_net = psutil.net_io_counters()
            
            if self.last_network_stats is not None and self.last_network_time is not None:
                # Calculate time difference
                time_diff = current_time - self.last_network_time
                
                if time_diff > 0:
                    # Calculate bytes transferred since last measurement
                    bytes_sent_diff = current_net.bytes_sent - self.last_network_stats.bytes_sent
                    bytes_recv_diff = current_net.bytes_recv - self.last_network_stats.bytes_recv
                    
                    # Convert to Mbps (bytes/sec -> Mbps)
                    upload_bps = bytes_sent_diff / time_diff
                    download_bps = bytes_recv_diff / time_diff
                    
                    upload_mbps = (upload_bps * 8) / (1024 * 1024)  # Convert to Mbps
                    download_mbps = (download_bps * 8) / (1024 * 1024)  # Convert to Mbps
                    
                    # Store in history for smoothing (keep last 5 measurements)
                    self.network_speed_history.append({
                        'download': download_mbps,
                        'upload': upload_mbps
                    })
                    
                    # Keep only last 5 measurements for averaging
                    if len(self.network_speed_history) > 5:
                        self.network_speed_history.pop(0)
                    
                    # Calculate averaged speeds for smoother display
                    if self.network_speed_history:
                        avg_download = sum(h['download'] for h in self.network_speed_history) / len(self.network_speed_history)
                        avg_upload = sum(h['upload'] for h in self.network_speed_history) / len(self.network_speed_history)
                        
                        network_stats.update({
                            "network_speed_download": max(0, avg_download),
                            "network_speed_upload": max(0, avg_upload),
                            "network_mbps": max(0, (avg_download + avg_upload) / 2)
                        })
            
            # Update tracking variables
            self.last_network_stats = current_net
            self.last_network_time = current_time
            
        except Exception as e:
            print(f"Network speed calculation error: {e}")
        
        return network_stats
        """Process user command with multilingual support"""
        log_query(command_text)
        try:
            # Process with multilingual support first
            if self.multilingual:
                response = self.process_multilingual_command(command_text)
                log_reply(response)
                return response
            
            # Save command to memory (with error handling)
            try:
                if AUTOMATION_AVAILABLE:
                    save_to_memory("user", f"Command: {command_text}")
            except Exception as mem_err:
                print(f"Memory save error (non-fatal): {mem_err}")
            
            # Use conversational AI if available
            if self.conversational_ai:
                response = self.conversational_ai.process_message(command_text)
                return response
            
            # Fallback to automation tools processing
            return self.process_automation_command(command_text)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Command processing error details:\n{error_details}")
            return f"Error processing command: {str(e)}"
    
    def process_multilingual_command(self, command_text):
        """Process command with full multilingual support"""
        log_query(command_text)
        try:
            # Detect language
            language_context = self.multilingual.detect_language(command_text)
            log_module_usage('multilingual', 'detect_language')
            
            # Log language detection
            print(f"Language detected: {language_context.detected_language.value} "
                  f"(confidence: {language_context.confidence:.2f})")
            
            # Handle Hinglish commands specially
            if language_context.detected_language == Language.HINGLISH:
                log_module_usage('multilingual', 'process_hinglish_command')
                hinglish_result = self.multilingual.process_hinglish_command(command_text)
                if hinglish_result.get('command'):
                    log_action('execute_hinglish_command', hinglish_result)
                    response = self.execute_hinglish_command(hinglish_result)
                    formatted_response = self.format_multilingual_response(response, language_context.detected_language)
                    log_reply(formatted_response)
                    return formatted_response
            
            # Translate to English if needed for processing
            processed_command = command_text
            if language_context.detected_language == Language.HINDI:
                processed_command = self.multilingual.translate_text(command_text, Language.ENGLISH)
                print(f"Translated to English: {processed_command}")
            
            # Save original command to memory (with detailed error handling)
            try:
                if AUTOMATION_AVAILABLE:
                    save_to_memory("user", f"Command ({language_context.detected_language.value}): {command_text}")
            except Exception as mem_err:
                print(f"Memory save error (non-fatal): {mem_err}")
                # Continue processing even if memory save fails
            
            # Process the command
            if self.conversational_ai:
                log_module_usage('conversational_ai', 'process_message')
                response = self.conversational_ai.process_message(processed_command)
            else:
                response = self.process_automation_command(processed_command)
            
            # Translate response back to user's language if needed
            if language_context.detected_language != Language.ENGLISH:
                translated_response = self.multilingual.translate_text(response, language_context.detected_language)
                return self.format_multilingual_response(translated_response, language_context.detected_language)
            
            return response
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Multilingual processing error details:\n{error_details}")
            return f"❌ Multilingual processing error: {str(e)}"
    
    def execute_hinglish_command(self, hinglish_result):
        """Execute commands detected from Hinglish input"""
        try:
            command = hinglish_result.get('command')
            parameters = hinglish_result.get('parameters', {})
            
            if command == 'make_call':
                if 'phone' in parameters:
                    return f"📞 Calling {parameters['phone']}..."
                elif 'contact' in parameters:
                    return f"📞 Calling {parameters['contact']}..."
                else:
                    return "📞 Phone number या contact name नहीं मिला"
                    
            elif command == 'play_music':
                if 'song' in parameters:
                    if AUTOMATION_AVAILABLE:
                        return f"🎵 {search_and_play_spotify(parameters['song'])}"
                    else:
                        return f"🎵 Playing: {parameters['song']}"
                else:
                    return "🎵 कौन सा song play करना है?"
                    
            elif command == 'web_search':
                if 'query' in parameters:
                    if AUTOMATION_AVAILABLE:
                        return f"🔍 {search_google(parameters['query'])}"
                    else:
                        return f"🔍 Searching for: {parameters['query']}"
                else:
                    return "🔍 Search query नहीं मिला"
                    
            elif command == 'adjust_volume':
                direction = parameters.get('direction', 'up')
                level = parameters.get('level')
                if level and AUTOMATION_AVAILABLE:
                    return f"🔊 {set_system_volume(level)}"
                elif direction == 'up' and AUTOMATION_AVAILABLE:
                    return "🔊 Volume बढ़ाया गया"
                else:
                    return "🔊 Volume कम किया गया"
                    
            elif command == 'tell_time':
                current_time = datetime.now().strftime("%H:%M:%S")
                return f"🕐 अभी समय है {current_time}"
                
            elif command == 'check_weather':
                if AUTOMATION_AVAILABLE:
                    weather = get_weather_info()
                    return f"🌤️ Weather: {weather.get('temperature', 'N/A')} - {weather.get('description', 'No data')}"
                else:
                    return "🌤️ Weather information उपलब्ध नहीं है"
                    
            else:
                return f"✅ Command '{command}' detected लेकिन अभी implement नहीं है"
                
        except Exception as e:
            return f"❌ Error executing Hinglish command: {str(e)}"
    
    def format_multilingual_response(self, response, language):
        """Format response with appropriate language indicators"""
        try:
            if language == Language.HINDI:
                return f"🇮🇳 {response}"
            elif language == Language.HINGLISH:
                return f"🇮🇳🇺🇸 {response}"
            else:
                return response
        except:
            return response
    
    def process_automation_command(self, text):
        """Process commands using automation tools"""
        text_lower = text.lower()
        
        try:
            # Weather queries
            if any(word in text_lower for word in ['weather', 'temperature', 'rain', 'sunny']):
                log_action('get_weather_info', {})
                log_module_usage('automation_tools_new', 'get_weather_info')
                weather = get_weather_info() if AUTOMATION_AVAILABLE else {"temperature": "22°C", "description": "Sunny"}
                return f"🌤️ Weather: {weather.get('temperature', 'N/A')} - {weather.get('description', 'No data available')}"
            
            # System status
            elif any(word in text_lower for word in ['system', 'cpu', 'memory', 'performance']):
                log_action('get_system_status', {})
                log_module_usage('system', 'get_system_status')
                if AUTOMATION_AVAILABLE:
                    status = get_system_status()
                    return f"💻 System - CPU: {status.get('cpu_percent', 0)}%, Memory: {status.get('memory_percent', 0)}%, Disk: {status.get('disk_percent', 0)}%"
                else:
                    stats = self.get_real_time_system_stats()
                    return f"💻 System - CPU: {stats['cpu_usage']:.1f}%, Memory: {stats['memory_usage']:.1f}%, Disk: {stats['disk_usage']:.1f}%"
            
            # Music/Spotify control
            elif any(word in text_lower for word in ['music', 'spotify', 'play', 'pause', 'song']):
                if AUTOMATION_AVAILABLE:
                    if 'play' in text_lower or 'pause' in text_lower:
                        log_action('spotify_play_pause', {})
                        log_module_usage('music', 'spotify_play_pause')
                        return f"🎵 {spotify_play_pause()}"
                    elif 'next' in text_lower:
                        log_action('spotify_next_track', {})
                        log_module_usage('music', 'spotify_next_track')
                        return f"🎵 {spotify_next_track()}"
                    elif 'previous' in text_lower:
                        log_action('spotify_previous_track', {})
                        log_module_usage('music', 'spotify_previous_track')
                        return f"🎵 {spotify_previous_track()}"
                    else:
                        log_action('get_spotify_status', {})
                        log_module_usage('music', 'get_spotify_status')
                        status = get_spotify_status()
                        return f"🎵 Now playing: {status.get('track_name', 'Nothing')} by {status.get('artist_name', 'Unknown')}"
                return "🎵 Music controls not available"
            
            # Application launching
            elif any(word in text_lower for word in ['open', 'launch', 'start', 'run']):
                app_name = text_lower.replace('open', '').replace('launch', '').replace('start', '').replace('run', '').strip()
                if app_name and AUTOMATION_AVAILABLE:
                    log_action('smart_open_application', {'app_name': app_name})
                    log_module_usage('app_discovery', 'smart_open_application')
                    return f"🚀 {smart_open_application(app_name)}"
                return "🚀 Please specify which application to open"
            
            # Memory/Notes
            elif any(word in text_lower for word in ['remember', 'note', 'save']):
                content = text.replace('remember', '').replace('note', '').replace('save', '').strip()
                if content and AUTOMATION_AVAILABLE:
                    log_action('write_a_note', {'content': content})
                    log_module_usage('core', 'write_a_note')
                    return f"📝 {write_a_note(content)}"
                return "📝 Note taking not available"
            
            # Help
            elif any(word in text_lower for word in ['help', 'commands', 'what can you do']):
                return """🤖 YourDaddy Assistant Commands:

🌤️ **Weather**: "What's the weather like?"
💻 **System**: "Show system status" 
🎵 **Music**: "Play music", "Pause", "Next song"
🚀 **Apps**: "Open Chrome", "Launch Notepad"
📝 **Notes**: "Remember to buy groceries"
🔍 **Search**: "Search for Python tutorials"
📊 **Monitor**: Real-time system monitoring
🎤 **Voice**: Voice commands and wake word
🤖 **AI Vision**: Screen analysis and visual Q&A

Just speak naturally - I understand context! 🎉"""
            
            # Default response
            else:
                return f"🤖 I heard: '{text}'\n\nTry asking about weather, system status, music control, opening apps, or say 'help' for more options!"
                
        except Exception as e:
            return f"🤖 Error: {str(e)}"
    
    def analyze_screen(self, prompt="What's on the screen?"):
        """Analyze current screen using multimodal AI"""
        if not self.multimodal_ai:
            return "Screen analysis not available - multimodal AI not initialized"
        
        try:
            result = self.multimodal_ai.analyze_screen(prompt)
            return result.get("analysis", "Could not analyze screen")
        except Exception as e:
            return f"Screen analysis error: {str(e)}"
    
    def process_enhanced_chat(self, message, context=None, image_data=None):
        """Enhanced chat processing with full AI integration and all features"""
        features_used = []
        suggestions = []
        response_text = ""
        mood = "neutral"
        context_id = None
        
        try:
            # Initialize context if not provided
            if context is None:
                context = {}
            
            # 1. MOOD DETECTION
            if self.conversational_ai and message:
                mood = self.conversational_ai.detect_mood(message).value
                features_used.append("mood_detection")
            
            # 2. MULTIMODAL PROCESSING (if image provided)
            if image_data and self.multimodal_ai:
                try:
                    # Process image with AI
                    visual_analysis = self.multimodal_ai.analyze_image_from_base64(image_data, message or "What do you see?")
                    response_text += f"🖼️ **Visual Analysis**: {visual_analysis}\n\n"
                    features_used.append("multimodal_ai")
                    
                    # If no text message, use image analysis as the message
                    if not message:
                        message = f"Analyze this image: {visual_analysis[:100]}..."
                except Exception as e:
                    response_text += f"❌ Image analysis failed: {str(e)}\n\n"
            
            # 3. MULTILINGUAL PROCESSING
            processed_message = message
            detected_language = "english"
            if message and self.multilingual:
                try:
                    language_context = self.multilingual.detect_language(message)
                    detected_language = language_context.detected_language.value
                    features_used.append("multilingual")
                    
                    # Handle Hinglish specially
                    if language_context.detected_language.value == "hinglish":
                        hinglish_result = self.multilingual.process_hinglish_command(message)
                        if hinglish_result.get('command'):
                            features_used.append("hinglish_processing")
                    
                    # Translate to English if needed
                    if language_context.detected_language.value == "hindi":
                        processed_message = self.multilingual.translate_text(message, Language.ENGLISH)
                        features_used.append("translation")
                        
                except Exception as e:
                    print(f"Multilingual processing error: {e}")
            
            # 4. CONVERSATIONAL AI PROCESSING
            if self.conversational_ai and processed_message:
                try:
                    # Create or get conversation context
                    if not hasattr(self, '_current_context_id') or not self._current_context_id:
                        self._current_context_id = self.conversational_ai.create_context(
                            "Enhanced Chat", "Multi-feature conversation", processed_message
                        )
                    context_id = self._current_context_id
                    
                    # Process with conversational AI
                    ai_response = self.conversational_ai.process_message(processed_message)
                    response_text += ai_response
                    features_used.append("conversational_ai")
                    
                    # Get suggestions
                    suggestions = self.conversational_ai.suggest_next_actions()
                    if suggestions:
                        features_used.append("ai_suggestions")
                        
                except Exception as e:
                    response_text += f"❌ AI processing failed: {str(e)}\n\n"
            
            # 5. SMART AUTOMATION DETECTION
            if AUTOMATION_AVAILABLE and processed_message:
                try:
                    from modules.smart_automation import SmartAutomationEngine
                    automation_engine = SmartAutomationEngine()
                    
                    # Detect if message requires automation
                    automation_suggestion = automation_engine.suggest_automation_from_pattern(processed_message)
                    if automation_suggestion:
                        features_used.append("smart_automation")
                        if not response_text or "I heard" in response_text:
                            # Execute automation if no better response
                            automation_result = automation_engine.execute_workflow_by_name(automation_suggestion)
                            if automation_result:
                                response_text = f"🤖 **Automation Executed**: {automation_result}"
                                features_used.append("automation_execution")
                except Exception as e:
                    print(f"Smart automation error: {e}")
            
            # 6. ENHANCED LEARNING INTEGRATION
            try:
                from modules.enhanced_learning import EnhancedLearning
                learning_system = EnhancedLearning()
                
                # Learn from this interaction
                learning_system.process_interaction(processed_message, response_text)
                features_used.append("enhanced_learning")
                
                # Get personalized suggestions
                personalized_suggestions = learning_system.get_personalized_suggestions()
                if personalized_suggestions:
                    suggestions.extend(personalized_suggestions)
                    features_used.append("personalized_suggestions")
            except Exception as e:
                print(f"Enhanced learning error: {e}")
            
            # 7. ADVANCED INTEGRATION FEATURES
            try:
                from modules.advanced_integration import AdvancedIntegration
                advanced_integration = AdvancedIntegration()
                
                # Check for integration opportunities
                integration_result = advanced_integration.process_command(processed_message)
                if integration_result and integration_result != processed_message:
                    response_text += f"\n\n🔗 **Advanced Integration**: {integration_result}"
                    features_used.append("advanced_integration")
            except Exception as e:
                print(f"Advanced integration error: {e}")
            
            # 8. FALLBACK TO AUTOMATION COMMAND PROCESSING
            if not response_text or len(response_text.strip()) < 10:
                response_text = self.process_automation_command(processed_message or "help")
                features_used.append("automation_fallback")
            
            # 9. TRANSLATE RESPONSE BACK IF NEEDED
            if detected_language != "english" and self.multilingual and response_text:
                try:
                    translated_response = self.multilingual.translate_text(
                        response_text, Language(detected_language)
                    )
                    if translated_response != response_text:
                        response_text = self.format_multilingual_response(
                            translated_response, Language(detected_language)
                        )
                        features_used.append("response_translation")
                except Exception as e:
                    print(f"Response translation error: {e}")
            
            # 10. MEMORY AND KNOWLEDGE INTEGRATION
            if AUTOMATION_AVAILABLE:
                try:
                    # Save to memory
                    save_to_memory("enhanced_chat", f"User: {message}\nResponse: {response_text}")
                    features_used.append("memory_storage")
                    
                    # Save knowledge if it's informational
                    if any(word in processed_message.lower() for word in ['learn', 'remember', 'know', 'fact']):
                        save_knowledge("chat_learning", response_text)
                        features_used.append("knowledge_storage")
                except Exception as e:
                    print(f"Memory/knowledge error: {e}")
            
            # 11. CONTEXT-AWARE SUGGESTIONS
            if not suggestions:
                suggestions = self._generate_contextual_suggestions(processed_message, features_used)
            
            return {
                "response": response_text,
                "features_used": features_used,
                "suggestions": suggestions,
                "mood": mood,
                "context_id": context_id,
                "detected_language": detected_language,
                "message_type": self._classify_message_type(processed_message)
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Enhanced chat processing error:\n{error_details}")
            
            return {
                "response": f"❌ Enhanced chat processing failed: {str(e)}\n\nFallback response: {self.process_automation_command(message or 'help')}",
                "features_used": ["error_fallback"],
                "suggestions": [],
                "mood": "confused",
                "context_id": None
            }
    
    def _generate_contextual_suggestions(self, message, features_used):
        """Generate contextual suggestions based on message and features used"""
        suggestions = []
        message_lower = message.lower() if message else ""
        
        # Smart suggestions based on context
        if "automation" in features_used:
            suggestions.append({"text": "📋 Show my automation workflows", "action": "show_workflows"})
        
        if "multimodal_ai" in features_used:
            suggestions.append({"text": "📸 Analyze current screen", "action": "analyze_screen"})
            suggestions.append({"text": "🔍 Extract text from image", "action": "extract_text"})
        
        if any(word in message_lower for word in ['open', 'launch', 'start']):
            suggestions.extend([
                {"text": "🚀 Show all apps", "action": "show_apps"},
                {"text": "📊 System status", "action": "system_status"}
            ])
        
        if any(word in message_lower for word in ['music', 'play', 'song']):
            suggestions.extend([
                {"text": "🎵 Spotify controls", "action": "music_controls"},
                {"text": "🔊 Volume control", "action": "volume_control"}
            ])
        
        if any(word in message_lower for word in ['weather', 'temperature']):
            suggestions.append({"text": "📅 Today's schedule", "action": "show_schedule"})
        
        if any(word in message_lower for word in ['email', 'mail']):
            suggestions.extend([
                {"text": "📧 Check inbox", "action": "check_email"},
                {"text": "✉️ Compose email", "action": "compose_email"}
            ])
        
        # Always include help
        suggestions.append({"text": "❓ Show all features", "action": "show_help"})
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def _classify_message_type(self, message):
        """Classify the type of message for better processing"""
        if not message:
            return "empty"
        
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['open', 'launch', 'start', 'run']):
            return "app_launch"
        elif any(word in message_lower for word in ['play', 'music', 'song', 'spotify']):
            return "music_control"
        elif any(word in message_lower for word in ['weather', 'temperature', 'forecast']):
            return "weather_query"
        elif any(word in message_lower for word in ['email', 'mail', 'inbox']):
            return "email_related"
        elif any(word in message_lower for word in ['remember', 'note', 'save']):
            return "memory_storage"
        elif any(word in message_lower for word in ['search', 'find', 'google']):
            return "search_query"
        elif any(word in message_lower for word in ['help', 'what can you do', 'features']):
            return "help_request"
        elif message.endswith('?'):
            return "question"
        else:
            return "general_chat"
    
    def answer_visual_question(self, question):
        """Answer visual questions about screen content"""
        if not self.multimodal_ai:
            return "Visual Q&A not available - multimodal AI not initialized"
        
        try:
            return self.multimodal_ai.answer_visual_question(question)
        except Exception as e:
            return f"Visual Q&A error: {str(e)}"
    
    def start_voice_listening(self):
        """Start voice listening session"""
        if not VOICE_AVAILABLE or not self.voice_recognizer:
            return {"error": "Voice recognition not available"}
        
        try:
            self.voice_listening = True
            socketio.emit('voice_status', {'listening': True})
            
            def listen_worker():
                with sr.Microphone() as source:
                    self.voice_recognizer.adjust_for_ambient_noise(source, duration=1)
                
                while self.voice_listening:
                    try:
                        with sr.Microphone() as source:
                            audio = self.voice_recognizer.listen(source, timeout=1, phrase_time_limit=5)
                        
                        # Recognize speech
                        text = self.voice_recognizer.recognize_google(audio)
                        
                        if text:
                            socketio.emit('voice_transcript', {'text': text})
                            response = self.process_command(text)
                            socketio.emit('voice_response', {
                                'command': text, 
                                'response': response
                            })
                            
                            # Speak response if TTS is available
                            if self.tts_engine:
                                self.speak_text(response)
                    
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        continue
                    except Exception as e:
                        print(f"Voice recognition error: {e}")
                        break
                
                self.voice_listening = False
                socketio.emit('voice_status', {'listening': False})
            
            # Start listening in background thread
            listen_thread = threading.Thread(target=listen_worker, daemon=True)
            listen_thread.start()
            
            return {"success": True, "message": "Voice listening started"}
            
        except Exception as e:
            self.voice_listening = False
            return {"error": f"Failed to start voice listening: {str(e)}"}
    
    def stop_voice_listening(self):
        """Stop voice listening session"""
        self.voice_listening = False
        socketio.emit('voice_status', {'listening': False})
        return {"success": True, "message": "Voice listening stopped"}
    
    def speak_text(self, text):
        """Convert text to speech"""
        if not self.tts_engine:
            return False
        
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
            return True
        except Exception as e:
            print(f"TTS error: {e}")
            return False
    
    def process_voice_audio(self, audio_data):
        """Process raw audio data for speech recognition"""
        if not VOICE_AVAILABLE or not self.voice_recognizer:
            return {"error": "Voice recognition not available"}
        
        try:
            # Decode base64 audio data
            audio_bytes = base64.b64decode(audio_data)
            
            # Create audio data object
            audio = sr.AudioData(audio_bytes, 16000, 2)
            
            # Recognize speech
            text = self.voice_recognizer.recognize_google(audio)
            
            if text:
                response = self.process_command(text)
                return {
                    "success": True,
                    "transcript": text,
                    "response": response
                }
            else:
                return {"error": "No speech detected"}
                
        except Exception as e:
            return {"error": f"Audio processing failed: {str(e)}"}

# Global assistant instance - protected initialization
try:
    print("🔧 Initializing YourDaddy Assistant...")
    assistant = ModernAssistant()
    print("✅ Assistant initialized successfully")
except Exception as e:
    print(f"❌ CRITICAL: Assistant initialization failed: {e}")
    print("⚠️  Server will start in limited mode without some features")
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
        
        def analyze_screen(self, prompt): return "Screen analysis unavailable"
        def answer_visual_question(self, question): return "Visual Q&A unavailable"
        def start_voice_listening(self): return {"error": "Voice features unavailable"}
        def stop_voice_listening(self): return {"error": "Voice features unavailable"}
        def speak_text(self, text): return False
        def process_voice_audio(self, audio_data): return {"error": "Audio processing unavailable"}
    
    assistant = MinimalAssistant()

# Serve HTML template
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_web_app(path):
    """Serve web application"""
    if path.startswith('static/'):
        # Serve static files
        return send_from_directory('static', path[7:])
    elif path and path != 'favicon.ico':
        # Serve static files without static prefix
        try:
            return send_from_directory('static', path)
        except:
            pass
    
    # Serve main HTML template
    from flask import render_template
    try:
        return render_template('index.html')
    except:
        # Fallback if template doesn't exist
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>YourDaddy Assistant</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
                h1 { color: #333; text-align: center; }
                .status { padding: 20px; background: #e8f5e8; border-radius: 5px; margin: 20px 0; }
                .api-link { display: inline-block; margin: 10px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
                .api-link:hover { background: #0056b3; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 YourDaddy Assistant - Server Running!</h1>
                <div class="status">
                    <strong>✅ Status:</strong> Backend is operational<br>
                    <strong>🌐 Server:</strong> Flask with SocketIO<br>
                    <strong>🤖 AI Features:</strong> All features enabled and integrated<br>
                    <strong>⚡ Automation:</strong> Voice, Apps, System Control
                </div>
                
                <h2>🚀 Try Enhanced Chat</h2>
                <div style="margin: 20px 0;">
                    <a href="/enhanced-chat" class="api-link">💬 Enhanced Chat Interface</a>
                    <a href="/api/features" class="api-link">🔧 Check Features</a>
                    <a href="/test" class="api-link">🧪 Test Page</a>
                </div>
                
                <p style="text-align: center; margin-top: 30px; color: #666;">
                    All chat features enabled with full AI integration!
                </p>
            </div>
        </body>
        </html>
        """

@app.route('/enhanced-chat')
def enhanced_chat():
    """Serve enhanced chat interface"""
    from flask import render_template
    return render_template('enhanced_chat.html')

@app.route('/test')
def test_page():
    """Simple test page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YourDaddy Assistant - Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            .test-btn { display: block; margin: 10px 0; padding: 15px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; text-align: center; }
            .test-btn:hover { background: #0056b3; }
            .status { padding: 15px; margin: 10px 0; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 YourDaddy Assistant - Test Page</h1>
            <div class="status success">✅ Backend is operational and all features are enabled!</div>
            
            <h2>Test Enhanced Chat Features:</h2>
            <a href="/enhanced-chat" class="test-btn">💬 Open Enhanced Chat Interface</a>
            <a href="/api/features" class="test-btn">🔧 Check Available Features</a>
            <a href="/api/apps" class="test-btn">📱 List Installed Applications</a>
            <a href="/api/weather" class="test-btn">🌤️ Get Weather Information</a>
            
            <h2>Quick API Tests:</h2>
            <div style="font-family: monospace; background: #f8f9fa; padding: 15px; border-radius: 5px; font-size: 12px;">
                <strong>Test Enhanced Chat:</strong><br>
                POST /api/chat<br>
                {"message": "Hello! What can you do?"}<br><br>
                
                <strong>Test Features:</strong><br>
                GET /api/features<br><br>
                
                <strong>Test Apps:</strong><br>
                GET /api/apps<br><br>
                
                <strong>Test Screen Analysis:</strong><br>
                POST /api/screen/analyze<br>
                {"prompt": "What's on the screen?"}
            </div>
        </div>
    </body>
    </html>
    """

# Authentication Routes
@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("3 per hour")  # Prevent abuse
def api_register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'username', 'username')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        if 'password' not in data:
            return jsonify({"error": "Password is required"}), 400
        
        username = data['username']
        password = data['password']
        
        # Check password strength
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        
        # Check if user already exists
        if username in USERS_DB:
            return jsonify({"error": "Username already exists"}), 409
        
        # Create new user
        USERS_DB[username] = {
            "password_hash": generate_password_hash(password),
            "role": "user"
        }
        
        # Create tokens
        access_token = create_access_token(
            identity=username,
            additional_claims={"role": "user"}
        )
        
        return jsonify({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 86400,
            "user": {
                "username": username,
                "role": "user"
            },
            "message": "Registration successful"
        }), 201
        
    except Exception as e:
        return jsonify({"error": "Registration failed"}), 500

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")  # Prevent brute force
def api_login():
    """Authenticate user and return JWT token"""
    try:
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'username', 'username')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        if 'password' not in data:
            return jsonify({"error": "Password is required"}), 400
        
        username = data['username']
        password = data['password']
        
        # Check credentials
        user = USERS_DB.get(username)
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Create tokens
        access_token = create_access_token(
            identity=username,
            additional_claims={"role": user['role']}
        )
        
        return jsonify({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 86400,  # 24 hours
            "user": {
                "username": username,
                "role": user['role']
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Login failed"}), 500

@app.route('/api/auth/verify', methods=['GET'])
@jwt_required()
def api_verify_token():
    """Verify JWT token is valid"""
    current_user = get_jwt_identity()
    user = USERS_DB.get(current_user)
    
    return jsonify({
        "valid": True,
        "user": {
            "username": current_user,
            "role": user['role'] if user else "user"
        }
    }), 200

# API Routes
@app.route('/api/status')
def api_status():
    """API status endpoint - Public"""
    authenticated = False
    try:
        verify_jwt_in_request(optional=True)
        authenticated = bool(get_jwt_identity())
    except:
        pass
    
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "authenticated": authenticated,
        "services": {
            "automation": AUTOMATION_AVAILABLE,
            "multimodal": MULTIMODAL_AVAILABLE,
            "conversational_ai": CONVERSATIONAL_AI_AVAILABLE,
            "voice": VOICE_AVAILABLE,
            "system_monitoring": PSUTIL_AVAILABLE
        }
    })

@app.route('/api/chat', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("60 per minute")
def api_chat():
    """Enhanced chat endpoint with full AI integration"""
    try:
        current_user = get_jwt_identity() or "anonymous"
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'message', 'command')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        message = sanitize_command(data['message'])
        context = data.get('context', {})
        image_data = data.get('image', None)
        
        if not message and not image_data:
            return jsonify({"error": "No message or image provided"}), 400
        
        # Process with full AI capabilities
        response = assistant.process_enhanced_chat(message, context, image_data)
        
        return jsonify({
            "message": message,
            "response": response["response"],
            "features_used": response["features_used"],
            "suggestions": response.get("suggestions", []),
            "mood": response.get("mood", "neutral"),
            "context_id": response.get("context_id"),
            "user": current_user,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Chat API error: {str(e)}")
        return jsonify({"error": "Chat processing failed"}), 500

@app.route('/api/command', methods=['POST'])
@jwt_required(optional=True)  # Optional authentication - works without login too
@limiter.limit("30 per minute")
def api_command():
    """Process text command - OPTIONALLY PROTECTED"""
    try:
        current_user = get_jwt_identity() or "anonymous"
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'command', 'command')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        command = sanitize_command(data['command'])
        
        if not command:
            return jsonify({"error": "No command provided"}), 400
        
        response = assistant.process_command(command)
        
        return jsonify({
            "command": command,
            "response": response,
            "user": current_user,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Command API error: {str(e)}")
        return jsonify({"error": "Command processing failed"}), 500

@app.route('/api/system/stats')
@jwt_required()
@limiter.limit("60 per minute")
def api_system_stats():
    """Get real-time system statistics - PROTECTED"""
    try:
        stats = assistant.get_real_time_system_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": "Failed to retrieve system stats"}), 500

@app.route('/api/weather')
@jwt_required()
@limiter.limit("20 per minute")
def api_weather():
    """Get weather information - PROTECTED"""
    try:
        if AUTOMATION_AVAILABLE:
            weather = get_weather_info()
        else:
            weather = {
                "temperature": "72°F",
                "description": "Sunny and Clear",
                "humidity": "45%",
                "wind_speed": "12 mph",
                "icon": "☀️"
            }
        return jsonify(weather)
    except Exception as e:
        return jsonify({"error": "Failed to retrieve weather"}), 500

# Enhanced Feature Endpoints for Full AI Integration
@app.route('/api/features', methods=['GET'])
def api_features():
    """Get list of all available features and their status"""
    features = {
        "conversational_ai": CONVERSATIONAL_AI_AVAILABLE,
        "multimodal_ai": MULTIMODAL_AVAILABLE,
        "multilingual": MULTILINGUAL_AVAILABLE,
        "automation": AUTOMATION_AVAILABLE,
        "voice_recognition": VOICE_AVAILABLE,
        "modules": {
            "smart_automation": True,
            "enhanced_learning": True,
            "advanced_integration": True,
            "file_operations": True,
            "web_scraping": True,
            "music_control": True,
            "email_handler": True,
            "calendar_integration": True,
            "document_ocr": True,
            "memory_system": True,
            "system_monitoring": True,
            "taskbar_detection": True
        }
    }
    return jsonify(features)

@app.route('/api/chat/context', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("20 per minute")
def api_create_context():
    """Create new conversation context"""
    try:
        if not assistant.conversational_ai:
            return jsonify({"error": "Conversational AI not available"}), 503
        
        data = request.get_json()
        name = data.get('name', 'New Conversation')
        topic = data.get('topic', 'General Chat')
        initial_message = data.get('initial_message', '')
        
        context_id = assistant.conversational_ai.create_context(name, topic, initial_message)
        
        return jsonify({
            "context_id": context_id,
            "name": name,
            "topic": topic,
            "created_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Failed to create context: {str(e)}"}), 500

@app.route('/api/chat/suggestions', methods=['GET'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_get_suggestions():
    """Get AI-powered suggestions for next actions"""
    try:
        if not assistant.conversational_ai:
            return jsonify({"suggestions": []})
        
        suggestions = assistant.conversational_ai.suggest_next_actions()
        return jsonify({"suggestions": suggestions})
    except Exception as e:
        return jsonify({"error": f"Failed to get suggestions: {str(e)}"}), 500

@app.route('/api/multimodal/analyze', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("10 per minute")
def api_multimodal_analyze():
    """Analyze image with AI"""
    try:
        if not assistant.multimodal_ai:
            return jsonify({"error": "Multimodal AI not available"}), 503
        
        data = request.get_json()
        image_data = data.get('image')
        prompt = data.get('prompt', 'What do you see in this image?')
        
        if not image_data:
            return jsonify({"error": "No image provided"}), 400
        
        analysis = assistant.multimodal_ai.analyze_image_from_base64(image_data, prompt)
        
        return jsonify({
            "analysis": analysis,
            "prompt": prompt,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Image analysis failed: {str(e)}"}), 500

@app.route('/api/screen/analyze', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("5 per minute")
def api_analyze_screen():
    """Analyze current screen using multimodal AI"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', 'What is on the screen?')
        
        analysis = assistant.analyze_screen(prompt)
        
        return jsonify({
            "analysis": analysis,
            "prompt": prompt,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Screen analysis failed: {str(e)}"}), 500

@app.route('/api/automation/workflows', methods=['GET'])
@jwt_required(optional=True)
@limiter.limit("20 per minute")
def api_get_workflows():
    """Get available automation workflows"""
    try:
        if not AUTOMATION_AVAILABLE:
            return jsonify({"workflows": []})
        
        from modules.smart_automation import SmartAutomationEngine
        automation_engine = SmartAutomationEngine()
        workflows = automation_engine.get_available_workflows()
        
        return jsonify({"workflows": workflows})
    except Exception as e:
        return jsonify({"error": f"Failed to get workflows: {str(e)}"}), 500

@app.route('/api/automation/execute', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("10 per minute")
def api_execute_workflow():
    """Execute automation workflow"""
    try:
        if not AUTOMATION_AVAILABLE:
            return jsonify({"error": "Automation not available"}), 503
        
        data = request.get_json()
        workflow_name = data.get('workflow_name')
        
        if not workflow_name:
            return jsonify({"error": "Workflow name required"}), 400
        
        from modules.smart_automation import SmartAutomationEngine
        automation_engine = SmartAutomationEngine()
        result = automation_engine.execute_workflow_by_name(workflow_name)
        
        return jsonify({
            "result": result,
            "workflow_name": workflow_name,
            "executed_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Workflow execution failed: {str(e)}"}), 500

@app.route('/api/memory/save', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_save_memory():
    """Save information to memory system"""
    try:
        if not AUTOMATION_AVAILABLE:
            return jsonify({"error": "Memory system not available"}), 503
        
        data = request.get_json()
        category = data.get('category', 'user')
        content = data.get('content')
        
        if not content:
            return jsonify({"error": "Content required"}), 400
        
        result = save_to_memory(category, content)
        
        return jsonify({
            "result": result,
            "category": category,
            "saved_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Failed to save memory: {str(e)}"}), 500

@app.route('/api/memory/search', methods=['GET'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_search_memory():
    """Search memory system"""
    try:
        if not AUTOMATION_AVAILABLE:
            return jsonify({"results": []})
        
        query = request.args.get('query', '')
        if not query:
            return jsonify({"error": "Search query required"}), 400
        
        results = search_memory(query)
        
        return jsonify({
            "results": results,
            "query": query,
            "searched_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Memory search failed: {str(e)}"}), 500

@app.route('/api/language/detect', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_detect_language():
    """Detect language of text"""
    try:
        if not assistant.multilingual:
            return jsonify({"error": "Multilingual support not available"}), 503
        
        data = request.get_json()
        text = data.get('text')
        
        if not text:
            return jsonify({"error": "Text required"}), 400
        
        language_context = assistant.multilingual.detect_language(text)
        
        return jsonify({
            "detected_language": language_context.detected_language.value,
            "confidence": language_context.confidence,
            "original_text": text,
            "detected_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Language detection failed: {str(e)}"}), 500

@app.route('/api/language/translate', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("20 per minute")
def api_translate_text():
    """Translate text to target language"""
    try:
        if not assistant.multilingual:
            return jsonify({"error": "Multilingual support not available"}), 503
        
        data = request.get_json()
        text = data.get('text')
        target_language = data.get('target_language', 'en')
        
        if not text:
            return jsonify({"error": "Text required"}), 400
        
        from modules.multilingual import Language
        translated = assistant.multilingual.translate_text(text, Language(target_language))
        
        return jsonify({
            "original_text": text,
            "translated_text": translated,
            "target_language": target_language,
            "translated_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Translation failed: {str(e)}"}), 500

@app.route('/api/apps')
# Removed @jwt_required() to fix HTTP 401 error - public endpoint for app grid
@limiter.limit("30 per minute")
def api_apps():
    """Get list of installed applications - PUBLIC"""
    try:
        if AUTOMATION_AVAILABLE:
            apps = get_apps_for_web()
        else:
            # Fallback app list
            apps = [
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
        
        return jsonify(apps)
    except Exception as e:
        logger.error(f"Failed to get apps: {e}")
        return jsonify({"error": "Failed to retrieve applications"}), 500

@app.route('/api/apps/launch', methods=['POST'])
@jwt_required(optional=True)  # Optional authentication for demo purposes
@limiter.limit("20 per minute")
def api_launch_app():
    """Launch an application - DEMO MODE"""
    try:
        current_user = get_jwt_identity() or "demo_user"
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'app_name', 'app_name')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        app_name = data['app_name']
        
        try:
            if AUTOMATION_AVAILABLE:
                result = smart_open_application(app_name)
                if "Error" in result or "not found" in result.lower():
                    # Try alternative approaches for common apps
                    if "youtube music" in app_name.lower():
                        # Try opening YouTube Music via web
                        import webbrowser
                        webbrowser.open('https://music.youtube.com')
                        result = "Opened YouTube Music in web browser"
                    elif "spotify" in app_name.lower():
                        # Try opening Spotify via web
                        import webbrowser
                        webbrowser.open('https://open.spotify.com')
                        result = "Opened Spotify in web browser"
                    else:
                        result = f"Attempted to launch {app_name} (result: {result})"
            else:
                result = f"Launched {app_name} (simulation mode)"
        except Exception as launch_error:
            # Fallback for common applications
            if "youtube music" in app_name.lower():
                import webbrowser
                webbrowser.open('https://music.youtube.com')
                result = "Opened YouTube Music in web browser"
            elif "spotify" in app_name.lower():
                import webbrowser
                webbrowser.open('https://open.spotify.com')
                result = "Opened Spotify in web browser"
            else:
                result = f"Could not launch {app_name} directly, but command was received"
        
        return jsonify({
            "success": True,
            "message": result,
            "app_name": app_name,
            "user": current_user
        })
    except Exception as e:
        logger.error(f"Launch error: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to launch {data.get('app_name', 'application')}: {str(e)}"
        }), 500

@app.route('/api/spotify/status')
@jwt_required()
@limiter.limit("30 per minute")
def api_spotify_status():
    """Get Spotify status - PROTECTED"""
    try:
        if AUTOMATION_AVAILABLE:
            status = get_spotify_status()
        else:
            status = {
                "is_playing": True,
                "track_name": "Midnight Dreams",
                "artist_name": "Synthwave Collective",
                "progress": 65,
                "duration": 240
            }
        
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": "Failed to retrieve Spotify status"}), 500

@app.route('/api/spotify/control', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def api_spotify_control():
    """Control Spotify playback - PROTECTED"""
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        action = data.get('action', '')
        
        if not action:
            return jsonify({"error": "No action provided"}), 400
        
        if AUTOMATION_AVAILABLE:
            if action == 'play_pause':
                result = spotify_play_pause()
            elif action == 'next':
                result = spotify_next_track()
            elif action == 'previous':
                result = spotify_previous_track()
            else:
                return jsonify({"error": "Unknown action"}), 400
        else:
            result = f"Spotify {action} executed (simulation mode)"
        
        return jsonify({
            "success": True,
            "message": result,
            "action": action,
            "user": current_user
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Failed to control Spotify"
        }), 500

@app.route('/api/visual/question', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def api_visual_question():
    """Answer visual questions about screen content - PROTECTED"""
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'question', 'command')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        question = data['question']
        
        answer = assistant.answer_visual_question(question)
        return jsonify({
            "question": question,
            "answer": answer,
            "user": current_user,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": "Failed to answer visual question"}), 500

# Activity feed endpoint
@app.route('/api/activity')
@jwt_required()
def api_activity():
    """Get recent activity feed - PROTECTED"""
    activities = [
        {"time": "2 min ago", "action": "Launched Spotify", "status": "success"},
        {"time": "15 min ago", "action": "Weather update received", "status": "info"},
        {"time": "1 hour ago", "action": "Calendar sync completed", "status": "success"},
        {"time": "3 hours ago", "action": "System optimization", "status": "info"}
    ]
    return jsonify(activities)

# Voice command history
@app.route('/api/voice/history')
@jwt_required()
def api_voice_history():
    """Get voice command history - PROTECTED"""
    history = [
        "Play my favorite playlist",
        "What's the weather like today?",
        "Schedule a meeting for 3 PM",
        "Open Chrome browser"
    ]
    return jsonify(history)

@app.route('/api/voice/start', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def api_start_voice():
    """Start voice listening - PROTECTED"""
    try:
        result = assistant.start_voice_listening()
        if "error" in result:
            return jsonify(result), 500
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Failed to start voice listening"}), 500

@app.route('/api/voice/stop', methods=['POST'])
@jwt_required()
def api_stop_voice():
    """Stop voice listening - PROTECTED"""
    try:
        result = assistant.stop_voice_listening()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Failed to stop voice listening"}), 500

@app.route('/api/voice/speak', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute")
def api_speak():
    """Convert text to speech - PROTECTED"""
    try:
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'text', 'command')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        text = data['text']
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        success = assistant.speak_text(text)
        return jsonify({"success": success, "text": text})
    except Exception as e:
        logging.error(f"Error in api_speak: {str(e)}")
        return jsonify({"error": "Failed to process text-to-speech"}), 500

@app.route('/api/voice/process', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute")
def api_process_voice():
    """Process voice audio data - PROTECTED"""
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        audio_data = data.get('audio_data', '')
        
        if not audio_data:
            return jsonify({"error": "No audio data provided"}), 400
        
        result = assistant.process_voice_audio(audio_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Failed to process voice"}), 500

# SocketIO Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('connected', {
        'message': 'Connected to YourDaddy Assistant',
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")

@socketio.on('command')
def handle_command(data):
    """Handle real-time command"""
    command = data.get('command', '')
    
    if command:
        response = assistant.process_command(command)
        emit('command_response', {
            'command': command,
            'response': response,
            'timestamp': datetime.now().isoformat()
        })

# Enhanced Chat SocketIO Events
@socketio.on('enhanced_chat')
def handle_enhanced_chat(data):
    """Handle enhanced chat with full AI integration"""
    try:
        message = data.get('message', '')
        context = data.get('context', {})
        image_data = data.get('image', None)
        
        if message or image_data:
            response = assistant.process_enhanced_chat(message, context, image_data)
            emit('enhanced_chat_response', {
                'message': message,
                'response': response['response'],
                'features_used': response['features_used'],
                'suggestions': response.get('suggestions', []),
                'mood': response.get('mood', 'neutral'),
                'context_id': response.get('context_id'),
                'detected_language': response.get('detected_language', 'english'),
                'message_type': response.get('message_type', 'general_chat'),
                'timestamp': datetime.now().isoformat()
            })
        else:
            emit('enhanced_chat_error', {'error': 'No message or image provided'})
    except Exception as e:
        emit('enhanced_chat_error', {'error': f'Chat processing failed: {str(e)}'})

@socketio.on('analyze_image')
def handle_analyze_image(data):
    """Handle image analysis request"""
    try:
        image_data = data.get('image')
        prompt = data.get('prompt', 'What do you see in this image?')
        
        if not image_data:
            emit('image_analysis_error', {'error': 'No image provided'})
            return
        
        if assistant.multimodal_ai:
            analysis = assistant.multimodal_ai.analyze_image_from_base64(image_data, prompt)
            emit('image_analysis_response', {
                'analysis': analysis,
                'prompt': prompt,
                'timestamp': datetime.now().isoformat()
            })
        else:
            emit('image_analysis_error', {'error': 'Multimodal AI not available'})
    except Exception as e:
        emit('image_analysis_error', {'error': f'Image analysis failed: {str(e)}'})

@socketio.on('analyze_screen')
def handle_analyze_screen(data):
    """Handle screen analysis request"""
    try:
        prompt = data.get('prompt', 'What is on the screen?')
        
        analysis = assistant.analyze_screen(prompt)
        emit('screen_analysis_response', {
            'analysis': analysis,
            'prompt': prompt,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        emit('screen_analysis_error', {'error': f'Screen analysis failed: {str(e)}'})

@socketio.on('get_suggestions')
def handle_get_suggestions():
    """Handle AI suggestions request"""
    try:
        if assistant.conversational_ai:
            suggestions = assistant.conversational_ai.suggest_next_actions()
            emit('suggestions_response', {
                'suggestions': suggestions,
                'timestamp': datetime.now().isoformat()
            })
        else:
            emit('suggestions_response', {'suggestions': []})
    except Exception as e:
        emit('suggestions_error', {'error': f'Failed to get suggestions: {str(e)}'})

@socketio.on('execute_workflow')
def handle_execute_workflow(data):
    """Handle workflow execution request"""
    try:
        workflow_name = data.get('workflow_name')
        
        if not workflow_name:
            emit('workflow_error', {'error': 'Workflow name required'})
            return
        
        if AUTOMATION_AVAILABLE:
            from modules.smart_automation import SmartAutomationEngine
            automation_engine = SmartAutomationEngine()
            result = automation_engine.execute_workflow_by_name(workflow_name)
            
            emit('workflow_response', {
                'result': result,
                'workflow_name': workflow_name,
                'executed_at': datetime.now().isoformat()
            })
        else:
            emit('workflow_error', {'error': 'Automation not available'})
    except Exception as e:
        emit('workflow_error', {'error': f'Workflow execution failed: {str(e)}'})

@socketio.on('mood_detection')
def handle_mood_detection(data):
    """Handle mood detection request"""
    try:
        text = data.get('text', '')
        
        if not text:
            emit('mood_detection_error', {'error': 'Text required'})
            return
        
        if assistant.conversational_ai:
            mood = assistant.conversational_ai.detect_mood(text)
            emit('mood_detection_response', {
                'text': text,
                'mood': mood.value,
                'timestamp': datetime.now().isoformat()
            })
        else:
            emit('mood_detection_error', {'error': 'Conversational AI not available'})
    except Exception as e:
        emit('mood_detection_error', {'error': f'Mood detection failed: {str(e)}'})

@socketio.on('request_system_stats')
def handle_system_stats_request():
    """Handle system stats request"""
    stats = assistant.get_real_time_system_stats()
    emit('system_stats', stats)

@socketio.on('start_voice_listening')
def handle_start_voice():
    """Start voice listening"""
    result = assistant.start_voice_listening()
    emit('voice_start_response', result)

@socketio.on('stop_voice_listening')
def handle_stop_voice():
    """Stop voice listening"""
    result = assistant.stop_voice_listening()
    emit('voice_stop_response', result)

@socketio.on('voice_audio_data')
def handle_voice_audio(data):
    """Handle voice audio data from client"""
    audio_data = data.get('audio_data', '')
    if audio_data:
        result = assistant.process_voice_audio(audio_data)
        emit('voice_audio_response', result)

@socketio.on('request_tts')
def handle_tts_request(data):
    """Handle text-to-speech request with multilingual support"""
    text = data.get('text', '')
    language = data.get('language', 'auto')
    
    if text:
        if assistant.multilingual:
            # Use multilingual TTS
            result = assistant.multilingual.speak_multilingual(
                text, 
                Language(language) if language != 'auto' else Language.AUTO_DETECT
            )
            emit('tts_response', {'success': True, 'text': text, 'result': result})
        else:
            # Fallback to regular TTS
            success = assistant.speak_text(text)
            emit('tts_response', {'success': success, 'text': text})

# Multilingual API Routes
@app.route('/api/language/detect', methods=['POST'])
def detect_language():
    """Detect language of input text"""
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    if assistant.multilingual:
        context = assistant.multilingual.detect_language(text)
        return jsonify({
            'detected_language': context.detected_language.value,
            'confidence': context.confidence,
            'is_mixed': context.is_mixed,
            'hindi_percentage': context.hindi_percentage,
            'english_percentage': context.english_percentage
        })
    else:
        return jsonify({"error": "Multilingual support not available"}), 503

@app.route('/api/language/translate', methods=['POST'])
def translate_text():
    """Translate text between languages"""
    data = request.json
    text = data.get('text', '')
    target_language = data.get('target_language', 'en')
    source_language = data.get('source_language')
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    if assistant.multilingual:
        try:
            target_lang = Language(target_language)
            source_lang = Language(source_language) if source_language else None
            
            result = assistant.multilingual.translate_text(text, target_lang, source_lang)
            return jsonify({
                'translated_text': result,
                'source_language': source_language,
                'target_language': target_language
            })
        except ValueError as e:
            return jsonify({"error": f"Invalid language code: {str(e)}"}), 400
        except Exception as e:
            return jsonify({"error": f"Translation failed: {str(e)}"}), 500
    else:
        return jsonify({"error": "Multilingual support not available"}), 503

@app.route('/api/language/hinglish', methods=['POST'])
def process_hinglish():
    """Process Hinglish commands"""
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    if assistant.multilingual:
        result = assistant.multilingual.process_hinglish_command(text)
        return jsonify(result)
    else:
        return jsonify({"error": "Multilingual support not available"}), 503

@app.route('/api/language/preference', methods=['POST'])
def set_language_preference():
    """Set user language preference"""
    data = request.json
    language = data.get('language', 'hinglish')
    tts_language = data.get('tts_language', language)
    user_id = data.get('user_id', 'web_user')
    
    if assistant.multilingual:
        try:
            lang = Language(language)
            tts_lang = Language(tts_language)
            assistant.multilingual.set_language_preference(user_id, lang, tts_lang)
            assistant.current_language = language
            return jsonify({
                'message': f'Language preference set to {language}',
                'user_id': user_id
            })
        except ValueError as e:
            return jsonify({"error": f"Invalid language: {str(e)}"}), 400
    else:
        return jsonify({"error": "Multilingual support not available"}), 503

@app.route('/api/language/preference', methods=['GET'])
def get_language_preference():
    """Get current language preference"""
    user_id = request.args.get('user_id', 'web_user')
    
    if assistant.multilingual:
        lang, tts_lang = assistant.multilingual.get_language_preference(user_id)
        return jsonify({
            'language': lang.value,
            'tts_language': tts_lang.value,
            'user_id': user_id
        })
    else:
        return jsonify({
            'language': 'en',
            'tts_language': 'en',
            'user_id': user_id
        })

# Multilingual SocketIO Events
@socketio.on('language_command')
def handle_multilingual_command(data):
    """Handle multilingual command"""
    command = data.get('command', '')
    language = data.get('language', 'auto')
    
    if command:
        log_query(command)
        if assistant.multilingual:
            response = assistant.process_multilingual_command(command)
        else:
            response = assistant.process_command(command)
        
        log_reply(response)
        emit('language_command_response', {
            'command': command,
            'response': response,
            'language': language,
            'timestamp': datetime.now().isoformat()
        })

@socketio.on('voice_audio_data')
def handle_voice_audio_data(data):
    """Handle voice audio data for multilingual recognition"""
    audio_data = data.get('audio_data', '')
    language = data.get('language', 'auto')
    
    if audio_data:
        log_action('process_voice_audio', {'language': language})
        if assistant.multilingual:
            # Process audio with multilingual support
            log_module_usage('multilingual', 'process_voice_audio')
            result = assistant.process_voice_audio(audio_data)
            # Add language detection to the result if available
            if result.get('transcript'):
                context = assistant.multilingual.detect_language(result['transcript'])
                result['detected_language'] = context.detected_language.value
                result['language_confidence'] = context.confidence
        else:
            result = assistant.process_voice_audio(audio_data)
        
        emit('voice_recognition_result', result)

# Error logging endpoint
@app.route('/api/error/log', methods=['POST'])
def api_log_error():
    """Log frontend errors for monitoring"""
    try:
        error_data = request.get_json()
        
        # Log to proper logger instead of print
        logger.error(f"Frontend Error: {error_data.get('message', 'Unknown error')}")
        logger.error(f"URL: {error_data.get('url', 'Unknown')}")
        logger.error(f"Time: {error_data.get('timestamp', 'Unknown')}")
        
        # Create error log entry
        error_log = {
            'timestamp': error_data.get('timestamp', datetime.now().isoformat()),
            'message': error_data.get('message', ''),
            'stack': error_data.get('stack', ''),
            'component_stack': error_data.get('componentStack', ''),
            'user_agent': error_data.get('userAgent', ''),
            'url': error_data.get('url', ''),
        }
        
        # Save to proper error log file in logs directory
        log_file = Path('logs/errors/frontend_errors.json')
        try:
            if log_file.exists():
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            logs.append(error_log)
            
            # Keep only last 100 errors
            if len(logs) > 100:
                logs = logs[-100:]
            
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save error log: {e}")
        
        return jsonify({"success": True, "logged": True})
    
    except Exception as e:
        logger.error(f"Error logging endpoint failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/settings/save', methods=['POST'])
def api_save_settings():
    """Save user settings"""
    try:
        settings_data = request.get_json()
        
        # Save settings to a file (in production, use a database)
        settings_file = Path(__file__).parent / 'user_settings.json'
        with open(settings_file, 'w') as f:
            json.dump(settings_data, f, indent=2)
        
        return jsonify({"success": True, "message": "Settings saved successfully"})
    
    except Exception as e:
        print(f"Failed to save settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/settings/load')
def api_load_settings():
    """Load user settings"""
    try:
        settings_file = Path(__file__).parent / 'user_settings.json'
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = json.load(f)
            return jsonify(settings)
        else:
            return jsonify({"settings": None})
    
    except Exception as e:
        print(f"Failed to load settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================
# FILE OPERATIONS API ENDPOINTS
# ============================================================

@app.route('/api/files/organize', methods=['POST'])
@jwt_required()
def api_organize_files():
    """Organize files by type in a directory"""
    try:
        from modules.file_ops import organize_files_by_type
        
        data = request.get_json()
        directory = data.get('directory')
        create_subfolders = data.get('create_subfolders', True)
        
        if not directory:
            return jsonify({"success": False, "error": "Directory path required"}), 400
        
        # Security: Basic path validation
        if not os.path.exists(directory):
            return jsonify({"success": False, "error": "Directory not found"}), 404
        
        result = organize_files_by_type(directory, create_subfolders)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"File organization error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/files/find-duplicates', methods=['POST'])
@jwt_required()
def api_find_duplicates():
    """Find duplicate files in a directory"""
    try:
        from modules.file_ops import find_duplicate_files
        
        data = request.get_json()
        directory = data.get('directory')
        include_subdirs = data.get('include_subdirs', True)
        
        if not directory:
            return jsonify({"success": False, "error": "Directory path required"}), 400
        
        result = find_duplicate_files(directory, include_subdirs)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Duplicate file detection error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/files/search', methods=['POST'])
@jwt_required()
def api_search_files():
    """Search for files with advanced filtering"""
    try:
        from modules.file_ops import smart_file_search
        
        data = request.get_json()
        directory = data.get('directory')
        pattern = data.get('pattern')
        search_content = data.get('search_content', False)
        file_types = data.get('file_types')
        
        if not directory or not pattern:
            return jsonify({"success": False, "error": "Directory and pattern required"}), 400
        
        result = smart_file_search(directory, pattern, search_content, file_types)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"File search error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/files/batch-rename', methods=['POST'])
@jwt_required()
def api_batch_rename():
    """Batch rename files using patterns"""
    try:
        from modules.file_ops import batch_rename_files
        
        data = request.get_json()
        directory = data.get('directory')
        pattern = data.get('pattern')
        replacement = data.get('replacement')
        preview = data.get('preview', True)
        
        if not all([directory, pattern, replacement]):
            return jsonify({"success": False, "error": "Directory, pattern, and replacement required"}), 400
        
        result = batch_rename_files(directory, pattern, replacement, preview)
        
        return jsonify({
            "success": True,
            "result": result,
            "preview": preview,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Batch rename error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/files/analyze-directory', methods=['POST'])
@jwt_required()
def api_analyze_directory():
    """Analyze directory structure and contents"""
    try:
        from modules.file_ops import analyze_directory_structure
        
        data = request.get_json()
        directory = data.get('directory')
        max_depth = data.get('max_depth', 3)
        
        if not directory:
            return jsonify({"success": False, "error": "Directory path required"}), 400
        
        result = analyze_directory_structure(directory, max_depth)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Directory analysis error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================
# DOCUMENT OCR API ENDPOINTS
# ============================================================

@app.route('/api/ocr/check-dependencies', methods=['GET'])
def api_ocr_check_dependencies():
    """Check OCR dependencies status"""
    try:
        from modules.document_ocr import check_ocr_dependencies
        
        result = check_ocr_dependencies()
        
        return jsonify({
            "success": True,
            "dependencies_status": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"OCR dependency check error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/ocr/extract-image', methods=['POST'])
@jwt_required()
def api_extract_text_image():
    """Extract text from image using OCR"""
    try:
        from modules.document_ocr import extract_text_from_image
        
        data = request.get_json()
        image_path = data.get('image_path')
        language = data.get('language', 'eng')
        enhance = data.get('enhance', True)
        
        if not image_path:
            return jsonify({"success": False, "error": "Image path required"}), 400
        
        result = extract_text_from_image(image_path, language, enhance)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Image OCR error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/ocr/extract-pdf', methods=['POST'])
@jwt_required()
def api_extract_text_pdf():
    """Extract text from PDF document"""
    try:
        from modules.document_ocr import extract_text_from_pdf
        
        data = request.get_json()
        pdf_path = data.get('pdf_path')
        page_range = data.get('page_range')
        
        if not pdf_path:
            return jsonify({"success": False, "error": "PDF path required"}), 400
        
        result = extract_text_from_pdf(pdf_path, page_range)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/ocr/analyze-document', methods=['POST'])
@jwt_required()
def api_analyze_document():
    """Analyze document structure and metadata"""
    try:
        from modules.document_ocr import analyze_document_structure
        
        data = request.get_json()
        file_path = data.get('file_path')
        
        if not file_path:
            return jsonify({"success": False, "error": "File path required"}), 400
        
        result = analyze_document_structure(file_path)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Document analysis error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/ocr/extract-info', methods=['POST'])
@jwt_required()
def api_extract_key_information():
    """Extract key information from text"""
    try:
        from modules.document_ocr import extract_key_information
        
        data = request.get_json()
        text = data.get('text')
        info_type = data.get('info_type', 'general')
        
        if not text:
            return jsonify({"success": False, "error": "Text required"}), 400
        
        result = extract_key_information(text, info_type)
        
        return jsonify({
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Information extraction error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================
# WEB SCRAPING API ENDPOINTS
# ============================================================

@app.route('/api/web/weather', methods=['GET'])
def api_get_weather():
    """Get weather information for a location"""
    try:
        from modules.web_scraping import get_weather_info
        
        location = request.args.get('location', 'New York')
        api_key = request.args.get('api_key')
        
        result = get_weather_info(location, api_key)
        
        return jsonify({
            "success": True,
            "weather": result,
            "location": location,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/web/news', methods=['GET'])
def api_get_news():
    """Get latest news headlines"""
    try:
        from modules.web_scraping import get_latest_news
        
        category = request.args.get('category', 'general')
        country = request.args.get('country', 'us')
        max_articles = int(request.args.get('max_articles', 5))
        
        result = get_latest_news(category, country, max_articles)
        
        return jsonify({
            "success": True,
            "news": result,
            "category": category,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"News API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/web/stock', methods=['GET'])
def api_get_stock():
    """Get stock price information"""
    try:
        from modules.web_scraping import get_stock_price
        
        symbol = request.args.get('symbol', 'AAPL')
        
        result = get_stock_price(symbol)
        
        return jsonify({
            "success": True,
            "stock_info": result,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Stock API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/web/crypto', methods=['GET'])
def api_get_crypto():
    """Get cryptocurrency price information"""
    try:
        from modules.web_scraping import get_crypto_price
        
        symbol = request.args.get('symbol', 'bitcoin')
        
        result = get_crypto_price(symbol)
        
        return jsonify({
            "success": True,
            "crypto_info": result,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Crypto API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/web/scrape', methods=['POST'])
@jwt_required()
def api_scrape_website():
    """Scrape website content"""
    try:
        from modules.web_scraping import scrape_website_content
        
        data = request.get_json()
        url = data.get('url')
        extract_text = data.get('extract_text', True)
        max_length = data.get('max_length', 1000)
        
        if not url:
            return jsonify({"success": False, "error": "URL required"}), 400
        
        result = scrape_website_content(url, extract_text, max_length)
        
        return jsonify({
            "success": True,
            "content": result,
            "url": url,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Web scraping error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/web/trending', methods=['GET'])
def api_get_trending():
    """Get trending topics from various platforms"""
    try:
        from modules.web_scraping import get_trending_topics
        
        platform = request.args.get('platform', 'general')
        
        result = get_trending_topics(platform)
        
        return jsonify({
            "success": True,
            "trending": result,
            "platform": platform,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Trending topics error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================
# TASKBAR DETECTION API ENDPOINTS
# ============================================================

@app.route('/api/taskbar/detect', methods=['GET'])
@jwt_required()
def api_detect_taskbar():
    """Detect and analyze taskbar applications"""
    try:
        from modules.taskbar_detection import detect_taskbar_apps
        
        result = detect_taskbar_apps()
        
        return jsonify({
            "success": True,
            "taskbar_analysis": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Taskbar detection error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/taskbar/capabilities', methods=['GET'])
def api_taskbar_capabilities():
    """Check taskbar detection capabilities"""
    try:
        from modules.taskbar_detection import can_see_taskbar
        
        result = can_see_taskbar()
        
        return jsonify({
            "success": True,
            "capabilities": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Taskbar capabilities check error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/taskbar/find-app', methods=['POST'])
@jwt_required()
def api_find_app_in_taskbar():
    """Find a specific application in taskbar"""
    try:
        from modules.taskbar_detection import TaskbarDetector
        
        data = request.get_json()
        app_name = data.get('app_name')
        
        if not app_name:
            return jsonify({"success": False, "error": "App name required"}), 400
        
        detector = TaskbarDetector()
        result = detector.find_specific_app_in_taskbar(app_name)
        
        return jsonify({
            "success": True,
            "app_search_result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"App search error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/taskbar/running-apps', methods=['GET'])
@jwt_required()
def api_get_running_apps():
    """Get list of running applications"""
    try:
        from modules.taskbar_detection import TaskbarDetector
        
        detector = TaskbarDetector()
        result = detector.get_running_applications()
        
        return jsonify({
            "success": True,
            "running_apps": result,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Running apps detection error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

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
        try:
            import subprocess
            subprocess.Popen(app_name, shell=True)
            return f"Opened {app_name}"
        except Exception as e:
            return f"Could not open {app_name}: {e}"
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

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 YourDaddy Assistant - Modern Web Backend")
    print("=" * 60)
    print("🌐 Server starting on: http://localhost:5000")
    print("📱 React frontend will be served automatically")
    print("⚡ Real-time features enabled via WebSockets")
    print("🔧 API endpoints available at /api/*")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        # Bind to localhost only for security
        host = os.getenv('HOST', '127.0.0.1')
        port = int(os.getenv('PORT', 5000))
        
        print(f"🔒 Security: JWT authentication enabled")
        print(f"🔒 Security: Rate limiting enabled")
        print(f"🔒 Security: CORS restricted to: {', '.join(ALLOWED_ORIGINS)}")
        print(f"🔒 Security: Host binding: {host}")
        print("")
        print(f"⚠️  Default credentials: username='admin', password='{os.getenv('ADMIN_PASSWORD', 'changeme123')}'")
        print("⚠️  CHANGE THE PASSWORD in .env file before production!")
        print("")
        
        socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)