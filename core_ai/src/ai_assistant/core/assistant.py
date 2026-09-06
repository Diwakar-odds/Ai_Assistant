# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Pulsar AI Assistant - ModernAssistant Class

Core assistant class with AI initialization, command processing, and system monitoring.
Extracted from modern_web_backend.py for better modularity and reusability.

This class handles:
- AI component initialization (multimodal, conversational, multilingual, LLM)
- Voice system setup (recognition, TTS, wake word detection)
- System monitoring and statistics
- Command processing with multilingual support
- Automation and Hinglish command execution
"""

# Standard library imports
import os
import sys
import time
import threading
import json
from datetime import datetime
from pathlib import Path

# Third-party imports
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import speech_recognition as sr
    import pyttsx3
    VOICE_AVAILABLE = True
except ImportError:
    sr = None
    pyttsx3 = None
    VOICE_AVAILABLE = False

# Internal imports - AI and ML
try:
    from ai_assistant.multimodal import MultiModalAI
    MULTIMODAL_AVAILABLE = True
except ImportError:
    MultiModalAI = None
    MULTIMODAL_AVAILABLE = False

try:
    from ai_assistant.ai.conversational_ai import AdvancedConversationalAI
    CONVERSATIONAL_AI_AVAILABLE = True
except ImportError:
    AdvancedConversationalAI = None
    CONVERSATIONAL_AI_AVAILABLE = False

try:
    from ai_assistant.multilingual import MultilingualSupport, Language, LanguageContext
    MULTILINGUAL_AVAILABLE = True
except ImportError:
    MultilingualSupport = None
    Language = None
    LanguageContext = None
    MULTILINGUAL_AVAILABLE = False

# Internal imports - Automation tools
try:
    from ai_assistant.automation_tools_new import (
        setup_memory, save_to_memory, get_memory,
        open_application, close_application,
        search_google, search_and_play_spotify,
        set_system_volume, get_system_volume,
        get_weather_info, get_system_status,
        smart_open_application, write_a_note,
        spotify_play_pause, spotify_next_track, spotify_previous_track,
        get_spotify_status
    )
    AUTOMATION_AVAILABLE = True
except ImportError:
    AUTOMATION_AVAILABLE = False
    # Stub functions
    setup_memory = lambda: None
    save_to_memory = lambda *args: None

# Internal imports - Logging
try:
    from utils.user_data_logger import log_query, log_reply, log_action, log_module_usage
except ImportError:
    log_query = lambda x: None
    log_reply = lambda x: None
    log_action = lambda *args: None
    log_module_usage = lambda *args: None

# Internal imports - Learning router
try:
    from auto_learning_router import LearningDataRouter
    LEARNING_ROUTER_AVAILABLE = True
    learning_router = LearningDataRouter()
except ImportError:
    LEARNING_ROUTER_AVAILABLE = False
    learning_router = None

# Feature flags - can be overridden via environment or constructor
ENABLE_VOICE = os.getenv('ENABLE_VOICE', 'true').lower() == 'true'
ENABLE_MULTIMODAL = os.getenv('ENABLE_MULTIMODAL', 'true').lower() == 'true'
ENABLE_CONVERSATIONAL_AI = os.getenv('ENABLE_CONVERSATIONAL_AI', 'true').lower() == 'true'
ENABLE_SYSTEM_MONITORING = os.getenv('ENABLE_SYSTEM_MONITORING', 'true').lower() == 'true'
ENABLE_MULTILINGUAL = os.getenv('ENABLE_MULTILINGUAL', 'true').lower() == 'true'
LAZY_INIT = os.getenv('LAZY_INIT', 'true').lower() == 'true'
BACKGROUND_INIT = os.getenv('BACKGROUND_INIT', 'true').lower() == 'true'

# SocketIO instance - will be injected
socketio = None

def set_socketio(sio):
    """Set the SocketIO instance for system monitoring"""
    global socketio
    socketio = sio


class ModernAssistant:
    """Modern Assistant with real-time capabilities"""
    
    def __init__(self):
        """Initialize assistant with optimized startup - components load on-demand or in background"""
        # Core attributes - always initialized
        self.voice_listening = False
        self.system_stats_cache = {}
        self.cache_timestamp = 0
        self.current_language = "hinglish"
        import threading
        self._process_lock = threading.RLock()
        
        # Network speed tracking
        self.last_network_stats = None
        self.last_network_time = None
        self.network_speed_history = []
        
        # Private attributes for lazy loading (None until first access)
        self._multimodal_ai = None
        self._conversational_ai = None
        self._multilingual = None
        self._llm_chat = None
        self._voice_recognizer = None
        self._tts_engine = None
        self._audio_stream = None
        self._wake_word_detector = None
        
        # Initialization status tracking
        self._init_status = {
            'multimodal_ai': 'not_started',
            'conversational_ai': 'not_started',
            'multilingual': 'not_started',
            'llm_chat': 'not_started',
            'voice_system': 'not_started',
            'memory': 'not_started',
            'system_monitoring': 'not_started'
        }
        self._init_lock = threading.Lock()
        
        # Fast startup: Only initialize memory (quick operation)
        if AUTOMATION_AVAILABLE:
            try:
                setup_memory()
                self._init_status['memory'] = 'ready'
                print("… Memory system initialized")
            except Exception as e:
                print(f"š  Memory initialization failed: {e}")
                self._init_status['memory'] = 'failed'
        
        # Background or lazy initialization based on config
        if BACKGROUND_INIT and not LAZY_INIT:
            # Start background initialization thread
            self._bg_init_thread = threading.Thread(target=self._background_init, daemon=True)
            self._bg_init_thread.start()
            print("š Background initialization started - features will be ready shortly")
        elif not LAZY_INIT:
            # Eager initialization (old behavior, but respects feature flags)
            self._eager_init()
        else:
            print("š Lazy initialization enabled - features load on first use")
            
    def process_query(self, query: str) -> str:
        """Process user query and return response"""
        
        # Check custom commands first
        try:
            from ai_assistant.core.custom_commands import CustomCommandManager
            if not hasattr(self, '_custom_cmd_mgr'):
                self._custom_cmd_mgr = CustomCommandManager()
            resolved = self._custom_cmd_mgr.resolve_command(query)
            if len(resolved) > 1:
                return f"Executing macro: {', '.join(resolved)} (Multi-step macros are partially supported)"
        except Exception:
            pass
            
        """
        Process a natural language query using the best available AI method.
        Added for backward compatibility and centralized processing.
        """
        try:
            # Lazy import to avoid circular dependencies
            try:
                from ai_assistant.ai.llm_provider import UnifiedChatInterface
                from ai_assistant.core.onboarding import OnboardingManager
                from ai_assistant.core.context_optimizer import ContextOptimizer
                
                if self._llm_chat is None:
                    self._llm_chat = UnifiedChatInterface(use_fallback=True)
                    self._onboarding_mgr = OnboardingManager()
                    self._context_opt = ContextOptimizer()
                    
                    if not self._onboarding_mgr.is_onboarded():
                        self._llm_chat.add_system_message(self._onboarding_mgr.get_onboarding_system_prompt())
                    else:
                        base_prompt = "You are 'Pulsar', a smart and helpful AI assistant."
                        self._llm_chat.add_system_message(self._context_opt.inject_context_into_prompt(base_prompt))
                
                # --- JARVIS HOOK: Inject emotional context before sending to LLM ---
                emotion_context = {}
                self._current_turn_mood = "neutral"
                if hasattr(self, '_learning_loop') and self._learning_loop:
                    emotion_context = self._learning_loop.get_emotion_context(query)
                    self._current_turn_mood = emotion_context.get("mood", "neutral")
                    modifier = emotion_context.get("prompt_modifier", "")
                    if modifier:
                        # Temporarily inject the emotion-aware system instruction
                        self._llm_chat.add_system_message(modifier)
                
                # Fetch response
                response = self._llm_chat.chat(query)
                
                # Process onboarding if active
                if hasattr(self, '_onboarding_mgr') and not self._onboarding_mgr.is_onboarded():
                    response, is_complete = self._onboarding_mgr.process_onboarding_response(response)
                    if is_complete:
                        # Reset system message once onboarding completes
                        if not hasattr(self, '_context_opt'):
                            self._context_opt = ContextOptimizer()
                        base_prompt = "You are 'Pulsar', a smart and helpful AI assistant."
                        self._llm_chat.add_system_message(self._context_opt.inject_context_into_prompt(base_prompt))
                
                # --- JARVIS HOOK: Fire async learning loop after every interaction ---
                if hasattr(self, '_learning_loop') and self._learning_loop:
                    self._learning_loop.process_interaction(
                        prompt=query,
                        response=response,
                        context=emotion_context
                    )
                        
                return response
            except ImportError:
                # Fallback if module missing
                return f"I received: {query} (AI engine unavailable)"
                
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"I encountered an error replying to that: {str(e)}"
    
    def _background_init(self):
        """Initialize heavy components in background thread"""
        print("„ Background initialization in progress...")
        
        if ENABLE_MULTILINGUAL:
            self._init_multilingual_internal()
        
        if ENABLE_CONVERSATIONAL_AI:
            self._init_conversational_ai_internal()
        
        if ENABLE_MULTIMODAL:
            self._init_multimodal_ai_internal()
        
        # Always try to init LLM (lightweight)
        self._init_smart_llm_internal()
        
        if ENABLE_VOICE:
            self._init_voice_system_internal()
        
        if ENABLE_SYSTEM_MONITORING:
            self.start_system_monitoring()
            
        try:
            from ai_assistant.core.proactive_anticipator import ProactiveAnticipator
            self._proactive_anticipator = ProactiveAnticipator(chat_interface=self._llm_chat if hasattr(self, '_llm_chat') else None)
            self._proactive_anticipator.start()
        except Exception as e:
            logger.warning(f"⚠️ Proactive Anticipator could not start: {e}")
            
        try:
            from ai_assistant.core.self_healing_engine import SelfHealingEngine
            self._self_healing_engine = SelfHealingEngine()
            self._self_healing_engine.start()
            logger.info("✅ Self-Healing Engine started")
        except Exception as e:
            logger.warning(f"⚠️ Self-Healing Engine could not start: {e}")
        
        # Initialize the Learning Loop (connects DNA, EI, Relationship, Memory)
        try:
            from ai_assistant.core.learning_loop import LearningLoop
            self._learning_loop = LearningLoop()
            logger.info("✅ Learning Loop initialized (EI + DNA + Relationship + Memory)")
        except Exception as e:
            logger.warning(f"⚠️ Learning Loop could not initialize: {e}")
            self._learning_loop = None
        
        logger.info("✅ Background initialization complete")
    
    def _eager_init(self):
        """Eager initialization (respects feature flags)"""
        if ENABLE_MULTIMODAL:
            self._init_multimodal_ai_internal()
        
        if ENABLE_CONVERSATIONAL_AI:
            self._init_conversational_ai_internal()
        
        if ENABLE_MULTILINGUAL:
            self._init_multilingual_internal()
        
        self._init_smart_llm_internal()
        
        if ENABLE_VOICE:
            self._init_voice_system_internal()
        
        if ENABLE_SYSTEM_MONITORING:
            self.start_system_monitoring()
    
    def get_init_status(self):
        """Get initialization status of all components"""
        return self._init_status.copy()
    
    # Lazy loading properties
    @property
    def multimodal_ai(self):
        """Lazy-load multimodal AI on first access"""
        if self._multimodal_ai is None and ENABLE_MULTIMODAL and LAZY_INIT:
            self._init_multimodal_ai_internal()
        return self._multimodal_ai
    
    @property
    def conversational_ai(self):
        """Lazy-load conversational AI on first access"""
        if self._conversational_ai is None and ENABLE_CONVERSATIONAL_AI and LAZY_INIT:
            self._init_conversational_ai_internal()
        return self._conversational_ai
    
    @property
    def multilingual(self):
        """Lazy-load multilingual support on first access"""
        if self._multilingual is None and ENABLE_MULTILINGUAL and LAZY_INIT:
            self._init_multilingual_internal()
        return self._multilingual
    
    @property
    def llm_chat(self):
        """Lazy-load LLM chat on first access"""
        if self._llm_chat is None and LAZY_INIT:
            self._init_smart_llm_internal()
        return self._llm_chat
    
    @property
    def voice_recognizer(self):
        """Lazy-load voice recognizer on first access"""
        if self._voice_recognizer is None and ENABLE_VOICE and LAZY_INIT:
            self._init_voice_system_internal()
        return self._voice_recognizer
    
    @property
    def tts_engine(self):
        """Lazy-load TTS engine on first access"""
        if self._tts_engine is None and ENABLE_VOICE and LAZY_INIT:
            self._init_voice_system_internal()
        return self._tts_engine

    
    def _init_multilingual_internal(self):
        """Initialize multilingual support (internal)"""
        with self._init_lock:
            if self._init_status['multilingual'] in ['ready', 'initializing']:
                return
            self._init_status['multilingual'] = 'initializing'
        
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
                
                self._multilingual = MultilingualSupport(lang_config)
                
                # Set default language preference
                primary_lang = lang_config.get('primary', 'hinglish')
                self._multilingual.set_language_preference("web_user", Language(primary_lang))
                self.current_language = primary_lang
                
                self._init_status['multilingual'] = 'ready'
                print("… Multilingual support initialized in web backend")
            except Exception as e:
                print(f"Œ Multilingual initialization failed: {e}")
                self._multilingual = None
                self._init_status['multilingual'] = 'failed'
        else:
            print("š  Multilingual support not available")
            self._multilingual = None
            self._init_status['multilingual'] = 'disabled'
    
    def _init_smart_llm_internal(self):
        """Initialize smart network-aware LLM system (internal)"""
        with self._init_lock:
            if self._init_status['llm_chat'] in ['ready', 'initializing']:
                return
            self._init_status['llm_chat'] = 'initializing'
        
        try:
            from ai_assistant.ai.network_aware_llm import get_optimal_llm_config
            from ai_assistant.ai.llm_provider import UnifiedChatInterface
            
            # Get optimal configuration based on network status
            config = get_optimal_llm_config()
            provider = config["provider"]
            model = config["model"]
            
            print(f"  Initializing LLM: {provider} ({model})")
            print(f" Network status: {'Online' if config['network_status'] else 'Offline'}")
            
            # Initialize the chat interface with smart config
            self._llm_chat = UnifiedChatInterface(
                provider=provider,
                model=model,
                use_fallback=False  # Disable automatic fallback
            )
            
            # Store config for reference
            self.current_llm_config = config
            
            # REMOVED: Blocking test connection - trust the config
            self._init_status['llm_chat'] = 'ready'
            print(f"… Smart LLM initialized with {provider} ({model})")
                
        except Exception as e:
            print(f"Œ Smart LLM initialization failed: {e}")
            self._llm_chat = None
            self.current_llm_config = None
            self._init_status['llm_chat'] = 'failed'
    
    def _init_multimodal_ai_internal(self):
        """Initialize multimodal AI (internal)"""
        with self._init_lock:
            if self._init_status['multimodal_ai'] in ['ready', 'initializing']:
                return
            self._init_status['multimodal_ai'] = 'initializing'
        
        if MULTIMODAL_AVAILABLE:
            try:
                api_key = os.environ.get("GEMINI_API_KEY")
                if api_key:
                    self._multimodal_ai = MultiModalAI(api_key)
                    self._init_status['multimodal_ai'] = 'ready'
                    print("… Multimodal AI initialized")
                else:
                    print("š  GEMINI_API_KEY not set for multimodal AI")
                    self._multimodal_ai = None
                    self._init_status['multimodal_ai'] = 'disabled'
            except Exception as e:
                print(f"Œ Multimodal AI initialization failed: {e}")
                self._multimodal_ai = None
                self._init_status['multimodal_ai'] = 'failed'
        else:
            print("š  Multimodal AI not available")
            self._multimodal_ai = None
            self._init_status['multimodal_ai'] = 'disabled'
    
    def _init_conversational_ai_internal(self):
        """Initialize conversational AI (internal)"""
        with self._init_lock:
            if self._init_status['conversational_ai'] in ['ready', 'initializing']:
                return
            self._init_status['conversational_ai'] = 'initializing'
        
        if CONVERSATIONAL_AI_AVAILABLE:
            try:
                # Initialize file automator for folder creation
                from ai_assistant.automation.file_automation import FileAutomation
                file_automator = FileAutomation()
                
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
                        elif action == 'create_folder':
                            if AUTOMATION_AVAILABLE:
                                # Param should be something like "folder_name|destination"
                                parts = param.split('|') if '|' in param else [param, 'desktop']
                                folder = parts[0].strip()
                                dest = parts[1].strip() if len(parts) > 1 else 'desktop'
                                success = file_automator.create_folder(folder, dest)
                                return f"Created folder {folder} on {dest}" if success else f"Failed to create folder {folder}"
                            return f"Creating folder {param}..."
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
                
                self._conversational_ai = AdvancedConversationalAI(automation_callback=automation_callback)
                self._init_status['conversational_ai'] = 'ready'
                print("… Conversational AI initialized with automation support")
            except Exception as e:
                print(f"Œ Conversational AI initialization failed: {e}")
                self._conversational_ai = None
                self._init_status['conversational_ai'] = 'failed'
        else:
            print("š  Conversational AI not available")
            self._conversational_ai = None
            self._init_status['conversational_ai'] = 'disabled'
    
    def init_memory(self):
        """Initialize memory system"""
        if AUTOMATION_AVAILABLE:
            try:
                setup_memory()
                logger.info("✅ Memory system initialized")
            except Exception as e:
                logger.error(f"❌ Memory initialization failed: {e}")
        else:
            logger.warning("⚠️ Memory system not available")
    
    def _init_voice_system_internal(self):
        """Initialize voice recognition and TTS systems (internal)"""
        with self._init_lock:
            if self._init_status['voice_system'] in ['ready', 'initializing']:
                return
            self._init_status['voice_system'] = 'initializing'
        
        if VOICE_AVAILABLE:
            try:
                # Initialize speech recognition (Faster-Whisper local)
                try:
                    import os
                    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
                    os.environ['PHONEMIZER_ESPEAK_LIBRARY'] = r'C:\Program Files\eSpeak NG\libespeak-ng.dll'
                    # Ensure ffmpeg in bin/ is found
                    bin_dir = os.path.abspath('bin')
                    if bin_dir not in os.environ['PATH']:
                        os.environ['PATH'] = bin_dir + os.pathsep + os.environ['PATH']
                    from faster_whisper import WhisperModel
                    # Use small model (~400MB) with CPU int8 quantization for best compatibility/speed
                    self._voice_recognizer = WhisperModel("small", device="cpu", compute_type="int8")
                    print("[OK] Faster-Whisper STT initialized locally")
                except Exception as e:
                    print(f"[WARN] Faster-Whisper initialization failed: {e}")
                    self._voice_recognizer = None
                
                # Initialize text-to-speech (KittenTTS)
                try:
                    from kittentts import KittenTTS
                    self._tts_engine = KittenTTS()
                    print("[OK] KittenTTS initialized")
                except Exception as e:
                    print(f"[WARN] KittenTTS initialization failed: {e}")
                    self._tts_engine = None
                
                # Try to initialize wake word detection (most likely to cause segfault)
                try:
                    access_key = os.environ.get("PORCUPINE_ACCESS_KEY")
                    if access_key:
                        # This is often the culprit for segfaults - extra protection
                        import pvporcupine
                        self._wake_word_detector = pvporcupine.create(
                            access_key=access_key,
                            keywords=["hey daddy"]
                        )
                        print("[OK] Wake word detection initialized")
                    else:
                        print("[WARN] PORCUPINE_ACCESS_KEY not set for wake word detection")
                        self._wake_word_detector = None
                except ImportError:
                    print("[WARN] Porcupine not available")
                    self._wake_word_detector = None
                except Exception as e:
                    print(f"[WARN] Wake word detection initialization failed: {e}")
                    self._wake_word_detector = None
                
                self._init_status['voice_system'] = 'ready'
                print("[OK] Voice system initialized (partial or complete)")
            except Exception as e:
                print(f"[ERROR] Voice system initialization failed: {e}")
                self._init_status['voice_system'] = 'failed'
                # Don't re-raise - allow server to continue without voice
        else:
            print("[WARN] Voice features not available - missing dependencies")
            self._init_status['voice_system'] = 'disabled'
    
    def start_system_monitoring(self):
        """Start background system monitoring"""
        if not ENABLE_SYSTEM_MONITORING:
            self._init_status['system_monitoring'] = 'disabled'
            return
        
        try:
            self._init_status['system_monitoring'] = 'initializing'
            
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
            self._init_status['system_monitoring'] = 'ready'
            print("… System monitoring started")
        except Exception as e:
            print(f"š  System monitoring could not start: {e}")
            self._init_status['system_monitoring'] = 'failed'
    
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
                # Basic system stats - use non-blocking calls
                stats.update({
                    "cpu_usage": psutil.cpu_percent(interval=0),  # Non-blocking
                    "memory_usage": psutil.virtual_memory().percent,
                    "disk_usage": psutil.disk_usage('C:\\' if os.name == 'nt' else '/').percent,
                    "active_tasks": len(psutil.pids()),
                })
                
                # Enhanced network speed calculation
                network_stats = self._calculate_network_speed(current_time)
                stats.update(network_stats)
                
            except Exception as e:
                # Log but don't crash on stats collection errors
                import traceback
                print(f"PSUtil error: {e}")
                print(traceback.format_exc())
        
        # Append AI Intelligence Metrics
        if getattr(self, '_self_healing_engine', None):
            stats["self_healing"] = self._self_healing_engine.get_status()
            
        if getattr(self, '_learning_loop', None) and self._learning_loop and self._learning_loop.dna:
            stats["user_dna"] = self._learning_loop.dna.get_all_traits()

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
            
            # Initialize on first call
            if self.last_network_stats is None:
                self.last_network_stats = current_net
                self.last_network_time = current_time
                return network_stats
            
            if self.last_network_stats is not None and self.last_network_time is not None:
                # Calculate time difference
                time_diff = current_time - self.last_network_time
                
                if time_diff > 0.5:  # Only calculate if enough time passed (avoid division issues)
                    # Calculate bytes transferred since last measurement
                    bytes_sent_diff = max(0, current_net.bytes_sent - self.last_network_stats.bytes_sent)
                    bytes_recv_diff = max(0, current_net.bytes_recv - self.last_network_stats.bytes_recv)
                    
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
    
    def process_command(self, command_text, model_preference=None):
        """Process user command with multilingual support"""
        log_query(command_text)
        with self._process_lock:
            try:
                # Process with multilingual support first
                if self.multilingual:
                    response = self.process_multilingual_command(command_text, model_preference)
                    log_reply(response)
                    return response
                
                # Save command to memory (with error handling)
                try:
                    if AUTOMATION_AVAILABLE:
                        save_to_memory("user", f"Command: {command_text}")
                        
                    # Route to learning systems
                    if LEARNING_ROUTER_AVAILABLE and learning_router:
                        learning_router.route_conversation(
                            speaker="user",
                            content=command_text,
                            category="command",
                            importance=3,
                            success=True
                        )
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
    
    def process_multilingual_command(self, command_text, model_preference=None):
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
                    
                # Route to learning systems for both voice and chat
                if LEARNING_ROUTER_AVAILABLE and learning_router:
                    learning_router.route_conversation(
                        speaker="user",
                        content=command_text,
                        category="command",
                        importance=4,  # Higher importance for multilingual commands
                        success=True
                    )
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
            return f" Multilingual processing error: {str(e)}"
    
    def execute_hinglish_command(self, hinglish_result):
        """Execute commands detected from Hinglish input"""
        try:
            command = hinglish_result.get('command')
            parameters = hinglish_result.get('parameters', {})
            
            if command == 'make_call':
                if 'phone' in parameters:
                    return f"¾ Calling {parameters['phone']}..."
                elif 'contact' in parameters:
                    return f"¾ Calling {parameters['contact']}..."
                else:
                    return "¾ Phone number  ¤ ¤¾ contact name  ¤¨ ¤¹ ¥‚¬ ¤š  ¤® ¤ ¤² ¤¾"
                    
            elif command == 'play_music':
                if 'song' in parameters:
                    if AUTOMATION_AVAILABLE:
                        return f" {search_and_play_spotify(parameters['song'])}"
                    else:
                        return f" Playing: {parameters['song']}"
                else:
                    return "  ¤ ¥ ¤¨  ¤ ¤¾ song play  ¤ ¤ ¤¨ ¤¾  ¤¹ ¥Ë†?"
                    
            elif command == 'web_search':
                if 'query' in parameters:
                    if AUTOMATION_AVAILABLE:
                        return f" {search_google(parameters['query'])}"
                    else:
                        return f" Searching for: {parameters['query']}"
                else:
                    return " Search query  ¤¨ ¤¹ ¥‚¬ ¤š  ¤® ¤ ¤² ¤¾"
                    
            elif command == 'adjust_volume':
                direction = parameters.get('direction', 'up')
                level = parameters.get('level')
                if level and AUTOMATION_AVAILABLE:
                    return f"  {set_system_volume(level)}"
                elif direction == 'up' and AUTOMATION_AVAILABLE:
                    return "  Volume  ¤¬ ¤ ¤¼ ¤¾ ¤ ¤¾  ¤ ¤ ¤¾"
                else:
                    return "  Volume  ¤ ¤®  ¤ ¤ ¤ ¤¾  ¤ ¤ ¤¾"
                    
            elif command == 'tell_time':
                current_time = datetime.now().strftime("%H:%M:%S")
                return f"  ¤¦ ¤­ ¥‚¬  ¤ ¤® ¤  ¤¹ ¥Ë† {current_time}"
                
            elif command == 'check_weather':
                if AUTOMATION_AVAILABLE:
                    weather = get_weather_info()
                    return f"¤ Weather: {weather.get('temperature', 'N/A')} - {weather.get('description', 'No data')}"
                else:
                    return "¤ Weather information  ¤ ¤ª ¤² ¤¬ ¥ ¤  ¤¨ ¤¹ ¥‚¬ ¤š  ¤¹ ¥Ë†"
                    
            else:
                return f"¦ Command '{command}' detected  ¤² ¥ ¤ ¤ ¤¨  ¤¦ ¤­ ¥‚¬ implement  ¤¨ ¤¹ ¥‚¬ ¤š  ¤¹ ¥Ë†"
                
        except Exception as e:
            return f" Error executing Hinglish command: {str(e)}"
    
    def format_multilingual_response(self, response, language):
        """Format response with appropriate language indicators"""
        try:
            if language == Language.HINDI:
                return f"®³ {response}"
            elif language == Language.HINGLISH:
                return f"®³º {response}"
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
                weather = get_weather_info() if AUTOMATION_AVAILABLE else {"temperature": "22‚C", "description": "Sunny"}
                return f"¤ Weather: {weather.get('temperature', 'N/A')} - {weather.get('description', 'No data available')}"
            
            # System status
            elif any(word in text_lower for word in ['system', 'cpu', 'memory', 'performance']):
                log_action('get_system_status', {})
                log_module_usage('system', 'get_system_status')
                if AUTOMATION_AVAILABLE:
                    status = get_system_status()
                    return f"» System - CPU: {status.get('cpu_percent', 0)}%, Memory: {status.get('memory_percent', 0)}%, Disk: {status.get('disk_percent', 0)}%"
                else:
                    stats = self.get_real_time_system_stats()
                    return f"» System - CPU: {stats['cpu_usage']:.1f}%, Memory: {stats['memory_usage']:.1f}%, Disk: {stats['disk_usage']:.1f}%"
            
            # Music/Spotify control
            elif any(word in text_lower for word in ['music', 'spotify', 'play', 'pause', 'song']):
                if AUTOMATION_AVAILABLE:
                    if 'play' in text_lower or 'pause' in text_lower:
                        log_action('spotify_play_pause', {})
                        log_module_usage('music', 'spotify_play_pause')
                        return f" {spotify_play_pause()}"
                    elif 'next' in text_lower:
                        log_action('spotify_next_track', {})
                        log_module_usage('music', 'spotify_next_track')
                        return f" {spotify_next_track()}"
                    elif 'previous' in text_lower:
                        log_action('spotify_previous_track', {})
                        log_module_usage('music', 'spotify_previous_track')
                        return f" {spotify_previous_track()}"
                    else:
                        log_action('get_spotify_status', {})
                        log_module_usage('music', 'get_spotify_status')
                        status = get_spotify_status()
                        return f" Now playing: {status.get('track_name', 'Nothing')} by {status.get('artist_name', 'Unknown')}"
                return " Music controls not available"
            
            # Application launching
            elif any(word in text_lower for word in ['open', 'launch', 'start', 'run']):
                app_name = text_lower.replace('open', '').replace('launch', '').replace('start', '').replace('run', '').strip()
                if app_name and AUTOMATION_AVAILABLE:
                    log_action('smart_open_application', {'app_name': app_name})
                    log_module_usage('app_discovery', 'smart_open_application')
                    return f"‚¬ {smart_open_application(app_name)}"
                return "‚¬ Please specify which application to open"
            
            # Memory/Notes
            elif any(word in text_lower for word in ['remember', 'note', 'save']):
                content = text.replace('remember', '').replace('note', '').replace('save', '').strip()
                if content and AUTOMATION_AVAILABLE:
                    log_action('write_a_note', {'content': content})
                    log_module_usage('core', 'write_a_note')
                    return f" {write_a_note(content)}"
                return " Note taking not available"
            
            # Help
            elif any(word in text_lower for word in ['help', 'commands', 'what can you do']):
                return """¤ Pulsar Assistant Commands:

¤ **Weather**: "What's the weather like?"
» **System**: "Show system status" 
 **Music**: "Play music", "Pause", "Next song"
‚¬ **Apps**: "Open Chrome", "Launch Notepad"
 **Notes**: "Remember to buy groceries"
 **Search**: "Search for Python tutorials"
  **Monitor**: Real-time system monitoring
¤ **Voice**: Voice commands and wake word
¤ **AI Vision**: Screen analysis and visual Q&A

Just speak naturally - I understand context! """
            
            # Default response
            else:
                return f"¤ I heard: '{text}'\n\nTry asking about weather, system status, music control, opening apps, or say 'help' for more options!"
                
        except Exception as e:
            return f"¤ Error: {str(e)}"
    
    def analyze_screen(self, prompt="What's on the screen?"):
        """Analyze current screen using multimodal AI"""
        if not self.multimodal_ai:
            return "Screen analysis not available - multimodal AI not initialized"
        
        try:
            result = self.multimodal_ai.analyze_screen(prompt)
            return result.get("analysis", "Could not analyze screen")
        except Exception as e:
            return f"Screen analysis error: {str(e)}"
    
    def process_enhanced_chat(self, message, context=None, image_data=None, model_preference=None, provider_preference=None):
        """Enhanced chat processing with full AI integration and all features"""
        features_used = []
        suggestions = []
        response_text = ""
        mood = "neutral"
        context_id = None
        actual_provider = None
        actual_model = None
        
        try:
            # Initialize context if not provided
            if context is None:
                context = {}
            
            # 0. CHECK SMART MEMORY FIRST (for questions)
            if '?' in message and SMART_MEMORY_AVAILABLE and memory_retriever:
                try:
                    memory_answer = memory_retriever.answer_from_memory(message)
                    if memory_answer:
                        # Found answer in memory!
                        response_text = f"­ **From Memory**: {memory_answer}\n\n"
                        features_used.append("memory_retrieval")
                except Exception as e:
                    print(f"Memory retrieval error: {e}")
            
            # 1. MOOD DETECTION
            if self.conversational_ai and message:
                mood = self.conversational_ai.detect_mood(message).value
                features_used.append("mood_detection")
            
            # 2. MULTIMODAL PROCESSING (if image provided)
            if image_data and self.multimodal_ai:
                try:
                    # Process image with AI
                    visual_analysis = self.multimodal_ai.analyze_image_from_base64(image_data, message or "What do you see?")
                    response_text += f"¼ **Visual Analysis**: {visual_analysis}\n\n"
                    features_used.append("multimodal_ai")
                    
                    # If no text message, use image analysis as the message
                    if not message:
                        message = f"Analyze this image: {visual_analysis[:100]}..."
                except Exception as e:
                    response_text += f" Image analysis failed: {str(e)}\n\n"
            
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
            
            # 4. SMART LLM PROCESSING (Network-Aware)
            if processed_message:
                try:
                    # --- Inject Learning Loop Context ---
                    if hasattr(self, '_learning_loop') and self._learning_loop:
                        context_dict = self._learning_loop.get_emotion_context(processed_message)
                        if context_dict and context_dict.get("prompt_modifier"):
                            processed_message = f"{context_dict['prompt_modifier']}\n\nUser: {processed_message}"
                    
                    # Use smart LLM system that auto-selects best provider
                    if hasattr(self, 'llm_chat') and self.llm_chat:
                        chat_interface = self.llm_chat
                        
                        if provider_preference or model_preference:
                            try:
                                from ai_assistant.ai.llm_provider import UnifiedChatInterface
                                chat_interface = UnifiedChatInterface(
                                    provider=provider_preference,
                                    model=model_preference,
                                    use_fallback=True
                                )
                            except Exception as e:
                                logger.warning(f"Warning: Failed to use preferred provider {provider_preference}: {e}")
                        
                        # Get current provider info
                        provider_info = ""
                        actual_provider = getattr(chat_interface, 'provider_name', 'unknown')
                        actual_model = getattr(chat_interface, 'model', 'unknown')
                        
                        if hasattr(self, 'current_llm_config') and self.current_llm_config and chat_interface == self.llm_chat:
                            network_status = "Online" if self.current_llm_config.get('network_status') else "Offline"
                            provider_info = f" ({network_status} - {actual_provider}:{actual_model})"
                        else:
                            provider_info = f" (Custom - {actual_provider}:{actual_model})"
                        
                        # Generate response using smart LLM
                        ai_response = chat_interface.chat(processed_message, stream=False)
                        response_text += ai_response
                        features_used.append(f"smart_llm{provider_info}")
                        
                    # Fallback to conversational AI if smart LLM fails
                    elif self.conversational_ai:
                        # Create or get conversation context
                        if not hasattr(self, '_current_context_id') or not self._current_context_id:
                            self._current_context_id = self.conversational_ai.create_context(
                                "Enhanced Chat", "Multi-feature conversation", processed_message
                            )
                        context_id = self._current_context_id
                        
                        # Process with conversational AI
                        ai_response = self.conversational_ai.process_message(processed_message)
                        response_text += ai_response
                        features_used.append("conversational_ai_fallback")
                        
                        # Get suggestions
                        suggestions = self.conversational_ai.suggest_next_actions()
                        if suggestions:
                            features_used.append("ai_suggestions")
                    else:
                        response_text += "  No AI system available for processing"
                        
                except Exception as e:
                    response_text += f"  AI processing failed: {str(e)}\n\n"
            
            # 5. SMART AUTOMATION DETECTION
            if AUTOMATION_AVAILABLE and processed_message:
                try:
                    from ai_assistant.automation.automation_engine import SmartAutomationEngine
                    automation_engine = SmartAutomationEngine()
                    
                    # Detect if message requires automation
                    automation_suggestion = automation_engine.suggest_automation_from_pattern(processed_message)
                    if automation_suggestion:
                        features_used.append("smart_automation")
                        if not response_text or "I heard" in response_text:
                            # Execute automation if no better response
                            automation_result = automation_engine.execute_workflow_by_name(automation_suggestion)
                            if automation_result:
                                response_text = f"¤ **Automation Executed**: {automation_result}"
                                features_used.append("automation_execution")
                except Exception as e:
                    print(f"Smart automation error: {e}")
            
            # 6. ENHANCED LEARNING INTEGRATION
            try:
                from ai_assistant.ai.enhanced_learning import EnhancedLearning
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
                from ai_assistant.automation.automation_engine import AdvancedIntegration
                advanced_integration = AdvancedIntegration()
                
                # Check for integration opportunities
                integration_result = advanced_integration.process_command(processed_message)
                if integration_result and integration_result != processed_message:
                    response_text += f"\n\n  **Advanced Integration**: {integration_result}"
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
                    
                    # Route to learning systems - BOTH VOICE AND CHAT
                    if LEARNING_ROUTER_AVAILABLE and learning_router:
                        # Determine if it's a question
                        is_question = '?' in message
                        learning_router.route_conversation(
                            speaker="user",
                            content=message,
                            category="question" if is_question else "chat",
                            importance=4 if is_question else 3,
                            success=True
                        )
                        # Also route the response
                        learning_router.route_conversation(
                            speaker="assistant",
                            content=response_text,
                            category="response",
                            importance=3,
                            success=True
                        )
                        features_used.append("ai_learning")
                    
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
                "message_type": self._classify_message_type(processed_message),
                "provider": actual_provider,
                "model": actual_model
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Enhanced chat processing error:\n{error_details}")
            
            return {
                "response": f" Enhanced chat processing failed: {str(e)}\n\nFallback response: {self.process_automation_command(message or 'help')}",
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
            suggestions.append({"text": "¹ Show my automation workflows", "action": "show_workflows"})
        
        if "multimodal_ai" in features_used:
            suggestions.append({"text": " Analyze current screen", "action": "analyze_screen"})
            suggestions.append({"text": " Extract text from image", "action": "extract_text"})
        
        if any(word in message_lower for word in ['open', 'launch', 'start']):
            suggestions.extend([
                {"text": "‚¬ Show all apps", "action": "show_apps"},
                {"text": "  System status", "action": "system_status"}
            ])
        
        if any(word in message_lower for word in ['music', 'play', 'song']):
            suggestions.extend([
                {"text": " Spotify controls", "action": "music_controls"},
                {"text": "  Volume control", "action": "volume_control"}
            ])
        
        if any(word in message_lower for word in ['weather', 'temperature']):
            suggestions.append({"text": "¦ Today's schedule", "action": "show_schedule"})
        
        if any(word in message_lower for word in ['email', 'mail']):
            suggestions.extend([
                {"text": " Check inbox", "action": "check_email"},
                {"text": " Compose email", "action": "compose_email"}
            ])
        
        # Always include help
        suggestions.append({"text": " Show all features", "action": "show_help"})
        
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
    
    def speak_text(self, text, mood=None):
        """Convert text to speech and return base64 audio data"""
        if not self.tts_engine:
            return None
            
        # Dynamically retrieve mood if not provided
        if mood is None:
            # Prefer the mood from the current interaction turn
            mood = getattr(self, '_current_turn_mood', None)
            # Fallback to learning loop history if unavailable
            if mood is None and getattr(self, '_learning_loop', None) and self._learning_loop.dna:
                mood = self._learning_loop.dna.get_trait("recent_mood")
        
        # Default voice params
        voice = 'expr-voice-2-m'
        speed = 1.0
        
        # Adjust based on mood
        if mood:
            mood_lower = mood.lower()
            if mood_lower in ['happy', 'excited']:
                speed = 1.15
            elif mood_lower in ['sad']:
                speed = 0.85
            elif mood_lower in ['frustrated', 'angry']:
                speed = 1.1
                # Could change voice here if more voices are added
            elif mood_lower in ['neutral']:
                speed = 1.0
        
        try:
            # Generate audio using KittenTTS with mood-aware parameters
            audio_array = self.tts_engine.generate(text, voice=voice, speed=speed)
            
            import io
            import soundfile as sf
            import base64
            
            # Convert to WAV and Base64
            buffer = io.BytesIO()
            sf.write(buffer, audio_array, 24000, format='WAV')
            b64_audio = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return b64_audio
        except Exception as e:
            print(f"KittenTTS error: {e}")
            return None
    
    def process_voice_audio(self, audio_data, on_transcription_complete=None):
        """Process raw audio data for speech recognition using Faster-Whisper"""
        if not VOICE_AVAILABLE or not self.voice_recognizer:
            return {"error": "Voice recognition not available"}
        
        try:
            import base64
            import tempfile
            import os
            
            logger.debug(f"DEBUG: Received audio_data length: {len(audio_data)}")
            
            # Decode base64 audio data
            # Audio data from MediaRecorder is usually webm
            audio_bytes = base64.b64decode(audio_data.split(',')[-1] if ',' in audio_data else audio_data)
            logger.debug(f"DEBUG: Decoded audio_bytes length: {len(audio_bytes)}")
            
            # Write to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
                temp_audio.write(audio_bytes)
                temp_path = temp_audio.name
                
            logger.debug(f"DEBUG: Audio written to {temp_path}. Starting Whisper transcribe...")
                
            try:
                # Transcribe using Faster-Whisper
                segments, info = self.voice_recognizer.transcribe(temp_path, beam_size=5)
                logger.debug("DEBUG: Generator returned. Evaluating segments...")
                text = " ".join([segment.text for segment in segments]).strip()
                logger.debug(f"DEBUG: Segments evaluated. Text: {text}")
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
            if text:
                print(f"Whisper transcribed: {text}")
                if on_transcription_complete:
                    try:
                        on_transcription_complete(text)
                    except Exception as cb_err:
                        print(f"Transcription callback error: {cb_err}")
                
                # Voice Emotion Detection
                try:
                    from ai_assistant.ai.emotional_intelligence import EmotionalIntelligence
                    ei = EmotionalIntelligence()
                    voice_emotion = ei.detect_emotion_from_voice(audio_data)
                    print(f"Detected voice emotion: {voice_emotion}")
                    if voice_emotion and voice_emotion.get("emotion") != "neutral":
                        self._current_turn_mood = voice_emotion.get("emotion")
                except Exception as e:
                    print(f"Voice emotion detection error: {e}")
                    
                response = self.process_command(text)
                return {
                    "success": True,
                    "transcript": text,
                    "response": response
                }
            else:
                return {"error": "No speech detected"}
                
        except Exception as e:
            print(f"Faster-Whisper processing failed: {str(e)}")
            return {"error": f"Audio processing failed: {str(e)}"}




