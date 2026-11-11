import os
import sys as _sys_alias
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Unify voice_service / backend.voice_service imports to a single module object
_this_voice_mod = _sys_alias.modules.get(__name__)
if _this_voice_mod is not None:
    _sys_alias.modules.setdefault('voice_service', _this_voice_mod)
    _sys_alias.modules.setdefault('backend.voice_service', _this_voice_mod)

# Setup centralized logging
from utils.logging_config import get_logger
from settings_manager import (
    get_provider, get_model, get_wake_words,
    get_stt_language_short, is_desktop_overlay_enabled,
    get_tts_config, get_tts_voice_id, is_wake_word_enabled, resolve_local_model_path,
)
logger = get_logger(__name__, log_category="app")

try:
    from ai_assistant.voice.tts_output_service import (
        ensure_espeak_environment,
        get_tts_service,
        load_kitten_mini_model,
        resolve_kitten_voice,
        resolve_edge_voice,
        decode_audio_bytes_to_pcm24k,
        pcm_to_wav_bytes,
        split_speakable_chunks,
    )
    ensure_espeak_environment()
    TTS_SERVICE_AVAILABLE = True
except Exception as _tts_svc_err:
    TTS_SERVICE_AVAILABLE = False
    logger.warning(f"Unified TTSOutputService import warning: {_tts_svc_err}")

# =============================================================================
# Unified Voice Service
# Consolidated from: voice_service_manager.py, voice_api.py, chat_voice_handlers_new.py
# =============================================================================

"""
Comprehensive Voice Service Manager
Integrates all professional voice features: wake word detection, neural TTS,
VAD, speaker recognition, and continuous listening
"""

import logging
import asyncio
import threading
import queue
import time as _time_module
from typing import Optional, Callable, Dict, Any, Tuple
from pathlib import Path

# Record when this module was imported (used for warmup time guard)
_voice_service_import_time = _time_module.time()

# Import all voice modules
try:
    from ai_assistant.voice.wake_word_detector import get_wake_word_manager, WakeWordDetectionMode
    WAKE_WORD_AVAILABLE = True
except (ImportError, OSError):
    WAKE_WORD_AVAILABLE = False
    logging.warning("Wake word detector not available")

try:
    from ai_assistant.voice.neural_voice_engine import get_neural_voice_engine, VoiceGender, SpeakingStyle
    NEURAL_TTS_AVAILABLE = True
except ImportError:
    NEURAL_TTS_AVAILABLE = False
    logging.warning("Neural TTS not available")

try:
    from ai_assistant.voice.voice_activity_detection import create_vad_detector, VADSensitivity
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    logging.warning("VAD not available")

try:
    from ai_assistant.voice.advanced_voice import (
        VoiceProfileManager,
        ContinuousListeningManager,
        voice_command_registry
    )
    ADVANCED_VOICE_AVAILABLE = True
except ImportError:
    ADVANCED_VOICE_AVAILABLE = False
    logging.warning("Advanced voice features not available")

try:
    from ai_assistant.voice.advanced_speech_recognizer import AdvancedSpeechRecognizer
    ADVANCED_STT_AVAILABLE = True
except ImportError:
    ADVANCED_STT_AVAILABLE = False
    logging.warning("Advanced STT not available")

try:
    from ai_assistant.voice.echo_guard import get_echo_guard, reset_echo_guard, band_energies
    ECHO_GUARD_AVAILABLE = True
except ImportError:
    ECHO_GUARD_AVAILABLE = False
    logging.warning("EchoGuard not available — falling back to timer-based echo prevention")


def get_active_assistant():
    """Robust helper to get the running assistant instance across main module or globals."""
    import sys
    if hasattr(sys, '_pulsar_assistant_instance') and sys._pulsar_assistant_instance:
        return sys._pulsar_assistant_instance
    main_mod = sys.modules.get('__main__')
    if main_mod and hasattr(main_mod, 'assistant') and main_mod.assistant:
        return main_mod.assistant
    b_mod = sys.modules.get('modern_web_backend') or sys.modules.get('backend.modern_web_backend')
    if b_mod and hasattr(b_mod, 'assistant') and b_mod.assistant:
        return b_mod.assistant
    return None


class VoiceServiceManager:
    """
    Comprehensive voice service manager
    Coordinates all voice features: wake word, TTS, VAD, speaker recognition
    """
    
    def __init__(self, 
                 enable_wake_word: bool = True,
                 enable_neural_tts: bool = True,
                 enable_vad: bool = True,
                 enable_speaker_recognition: bool = True):
        
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        
        # Configuration
        self.enable_wake_word = enable_wake_word and WAKE_WORD_AVAILABLE
        self.enable_neural_tts = enable_neural_tts and NEURAL_TTS_AVAILABLE
        self.enable_vad = enable_vad and VAD_AVAILABLE
        self.enable_speaker_recognition = enable_speaker_recognition and ADVANCED_VOICE_AVAILABLE
        
        # Components
        self.wake_word_manager = None
        self.tts_engine = None
        self.vad_detector = None
        self.voice_profile_manager = None
        self.speech_recognizer = None
        self.continuous_listener = None
        
        # Callbacks
        self.on_wake_word_detected: Optional[Callable] = None
        self.on_command_recognized: Optional[Callable] = None
        self.on_speaker_identified: Optional[Callable] = None
        
        # State
        self.current_speaker: Optional[str] = None
        self.is_listening_for_command = False
        
        # Initialize components
        self._initialize_components()
        
        self.logger.info(f"… Voice Service Manager initialized")
        self.logger.info(f"   Wake Word: {self.enable_wake_word}")
        self.logger.info(f"   Neural TTS: {self.enable_neural_tts}")
        self.logger.info(f"   VAD: {self.enable_vad}")
        self.logger.info(f"   Speaker Recognition: {self.enable_speaker_recognition}")
    
    def _initialize_components(self):
        """Initialize all voice components"""
        
        # 1. Wake Word Detector (PocketSphinx)
        if self.enable_wake_word:
            try:
                self.wake_word_manager = get_wake_word_manager(
                    detection_mode=WakeWordDetectionMode.ALWAYS_ON
                )
                self.wake_word_manager.detector.on_wake_word_detected = self._handle_wake_word
                self.logger.info("… Wake word detector initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize wake word detector: {e}")
                self.enable_wake_word = False
        
        # 2. Neural TTS Engine (Edge-TTS + Coqui)
        if self.enable_neural_tts:
            try:
                self.tts_engine = get_neural_voice_engine()
                self.logger.info("… Neural TTS engine initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize TTS engine: {e}")
                self.enable_neural_tts = False
        
        # 3. Voice Activity Detector
        if self.enable_vad:
            try:
                self.vad_detector = create_vad_detector(
                    sensitivity=VADSensitivity.MEDIUM
                )
                self.logger.info("… VAD initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize VAD: {e}")
                self.enable_vad = False
        
        # 4. Speaker Recognition
        if self.enable_speaker_recognition:
            try:
                self.voice_profile_manager = VoiceProfileManager()
                self.logger.info("… Voice profile manager initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize voice profiles: {e}")
                self.enable_speaker_recognition = False
        
        # 5. Advanced Speech Recognizer
        if ADVANCED_STT_AVAILABLE:
            try:
                self.speech_recognizer = AdvancedSpeechRecognizer(
                    prefer_online=True,
                    noise_reduction=True
                )
                self.logger.info("… Advanced speech recognizer initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize speech recognizer: {e}")
    
    def start(self):
        """Start all voice services"""
        if self.is_running:
            self.logger.warning("Voice services already running")
            return
        
        self.is_running = True
        
        # Start wake word detection
        if self.enable_wake_word and self.wake_word_manager:
            try:
                self.wake_word_manager.start()
                self.logger.info("Ž¤ Wake word detection started")
            except Exception as e:
                self.logger.error(f"Failed to start wake word detection: {e}")
        
        # Start continuous listening if available
        if ADVANCED_VOICE_AVAILABLE and self.continuous_listener:
            try:
                self.continuous_listener.start_listening()
                self.logger.info("‘‚ Continuous listening started")
            except Exception as e:
                self.logger.error(f"Failed to start continuous listening: {e}")
        
        self.logger.info("… All voice services started")
    
    def stop(self):
        """Stop all voice services"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop wake word detection
        if self.wake_word_manager:
            try:
                self.wake_word_manager.stop()
                self.logger.info("Wake word detection stopped")
            except Exception as e:
                self.logger.error(f"Error stopping wake word: {e}")
        
        # Stop continuous listening
        if self.continuous_listener:
            try:
                self.continuous_listener.stop_listening()
                self.logger.info("Continuous listening stopped")
            except Exception as e:
                self.logger.error(f"Error stopping listener: {e}")
        
        self.logger.info("Voice services stopped")
    
    def _handle_wake_word(self, wake_word: str, confidence: float):
        """Handle wake word detection"""
        self.logger.info(f"Ž Wake word detected: '{wake_word}' (confidence: {confidence:.2f})")
        
        self.is_listening_for_command = True
        
        # Callback to frontend
        if self.on_wake_word_detected:
            self.on_wake_word_detected(wake_word, confidence)
        
        # Speak greeting
        self.speak_greeting()
    
    def speak_greeting(self, wake_word: str = "hey pulsar"):
        """Speak a natural, non-repetitive greeting after wake word."""
        try:
            from ai_assistant.core.jarvis_persona import generate_wake_acknowledgment
            greeting = generate_wake_acknowledgment(wake_word=wake_word)
        except Exception:
            greeting = ""
        if greeting:
            self.speak_text(greeting)
    
    def speak_text(self, text: str, language: str = 'en', gender: str = 'female'):
        """Speak text via unified desktop TTS output service (with neural engine fallback)."""
        if TTS_SERVICE_AVAILABLE:
            try:
                if get_tts_service().speak(text, source='voice_service_manager'):
                    return "unified_tts_stream"
            except Exception as e:
                self.logger.debug(f"Unified TTS fallback in VoiceServiceManager: {e}")

        if not self.enable_neural_tts or not self.tts_engine:
            self.logger.warning("Neural TTS not available")
            return None

        try:
            voice_gender = VoiceGender.FEMALE if gender == 'female' else VoiceGender.MALE
            audio_file = self.tts_engine.speak(
                text,
                language=language,
                gender=voice_gender,
                style=SpeakingStyle.FRIENDLY
            )
            self.logger.info(f"🔊 TTS: '{text}' -> {audio_file}")
            return audio_file

        except Exception as e:
            self.logger.error(f"TTS failed: {e}")
            return None
    
    async def speak_text_async(self, text: str, language: str = 'en', gender: str = 'female'):
        """Async version of speak_text"""
        if not self.enable_neural_tts or not self.tts_engine:
            return None
        
        try:
            voice_gender = VoiceGender.FEMALE if gender == 'female' else VoiceGender.MALE
            
            # Use KittenTTS
            audio_file = self.tts_engine.speak(
                text,
                language=language,
                gender=voice_gender
            )
            
            return audio_file
        except Exception as e:
            self.logger.error(f"Async TTS failed: {e}")
            return None
    
    def identify_speaker(self, audio_data) -> Optional[str]:
        """Identify speaker from audio"""
        if not self.enable_speaker_recognition or not self.voice_profile_manager:
            return None
        
        try:
            speaker = self.voice_profile_manager.identify_speaker(audio_data)
            
            if speaker:
                self.current_speaker = speaker
                self.logger.info(f"‘¤ Speaker identified: {speaker}")
                
                if self.on_speaker_identified:
                    self.on_speaker_identified(speaker)
            
            return speaker
            
        except Exception as e:
            self.logger.error(f"Speaker identification failed: {e}")
            return None
    
    def train_speaker(self, speaker_name: str, audio_data):
        """Train voice profile for a speaker"""
        if not self.enable_speaker_recognition or not self.voice_profile_manager:
            return False
        
        try:
            self.voice_profile_manager.add_voice_sample(speaker_name, audio_data)
            self.logger.info(f"… Added voice sample for {speaker_name}")
            return True
        except Exception as e:
            self.logger.error(f"Speaker training failed: {e}")
            return False
    
    def detect_voice_activity(self, audio_data) -> bool:
        """Detect if audio contains speech"""
        if not self.enable_vad or not self.vad_detector:
            return True  # Assume speech if VAD not available
        
        try:
            result = self.vad_detector.detect_voice_activity(audio_data)
            return result.is_speech
        except Exception as e:
            self.logger.error(f"VAD failed: {e}")
            return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all voice services"""
        return {
            'running': self.is_running,
            'wake_word': {
                'enabled': self.enable_wake_word,
                'active': self.wake_word_manager is not None,
                'stats': self.wake_word_manager.get_stats() if self.wake_word_manager else {}
            },
            'tts': {
                'enabled': self.enable_neural_tts,
                'active': self.tts_engine is not None
            },
            'vad': {
                'enabled': self.enable_vad,
                'active': self.vad_detector is not None,
                'status': self.vad_detector.get_status() if self.vad_detector else {}
            },
            'speaker_recognition': {
                'enabled': self.enable_speaker_recognition,
                'active': self.voice_profile_manager is not None,
                'current_speaker': self.current_speaker,
                'profiles': len(self.voice_profile_manager.profiles) if self.voice_profile_manager else 0
            },
            'listening_for_command': self.is_listening_for_command
        }
    
    def get_available_voices(self) -> list:
        """Get list of available TTS voices"""
        if not self.enable_neural_tts or not self.tts_engine:
            return []
        
        # Return available voices from neural engine
        return [
            {'language': 'en', 'gender': 'female', 'name': 'Aria (US English Female)'},
            {'language': 'en', 'gender': 'male', 'name': 'Guy (US English Male)'},
            {'language': 'en-IN', 'gender': 'female', 'name': 'Neerja (Indian English Female)'},
            {'language': 'en-IN', 'gender': 'male', 'name': 'Prabhat (Indian English Male)'},
            {'language': 'hi', 'gender': 'female', 'name': 'Swara (Hindi Female)'},
            {'language': 'hi', 'gender': 'male', 'name': 'Madhur (Hindi Male)'},
        ]


# Global instance
_voice_service_manager: Optional[VoiceServiceManager] = None


def get_voice_service_manager(
    enable_wake_word: bool = True,
    enable_neural_tts: bool = True,
    enable_vad: bool = True,
    enable_speaker_recognition: bool = True
) -> VoiceServiceManager:
    """Get or create voice service manager instance"""
    global _voice_service_manager
    
    if _voice_service_manager is None:
        _voice_service_manager = VoiceServiceManager(
            enable_wake_word=enable_wake_word,
            enable_neural_tts=enable_neural_tts,
            enable_vad=enable_vad,
            enable_speaker_recognition=enable_speaker_recognition
        )
    
    return _voice_service_manager


# Example usage
if __name__ == "__main__":
    # Initialize voice services
    voice_manager = get_voice_service_manager()
    
    # Set up callbacks
    def on_wake_word(word, confidence):
        print(f"Ž Wake word: {word} ({confidence:.2f})")
    
    def on_speaker(speaker):
        print(f"‘¤ Speaker: {speaker}")
    
    voice_manager.on_wake_word_detected = on_wake_word
    voice_manager.on_speaker_identified = on_speaker
    
    # Start services
    voice_manager.start()
    
    print("Voice services running. Press Ctrl+C to stop...")
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        voice_manager.stop()
        print("Stopped")


# =============================================================================
# Section 2: HTTP API Routes (from voice_api.py)
# =============================================================================

# Voice endpoints added by AI assistant
# Location: f:\bn\assitant\ai_assistant\services\voice_api.py

from flask import Blueprint, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import os
import hashlib
import time
from functools import lru_cache
from typing import Dict, Optional

voice_bp = Blueprint('voice', __name__)

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"]
)

# Check if any TTS synthesis engine is available (EdgeTTS / KittenTTS / pyttsx3)
def _check_tts_available() -> bool:
    for mod in ("edge_tts", "kittentts", "pyttsx3"):
        try:
            __import__(mod)
            return True
        except ImportError:
            continue
    return False


VOICE_AVAILABLE = _check_tts_available()
if not VOICE_AVAILABLE:
    logging.warning("No TTS synthesis engine available. Voice preview will not work.")

# Available Voice Options (Online Natural Hindi/Hinglish EdgeTTS Default First + Offline KittenTTS mini-0.8)
AVAILABLE_VOICES = [
    {"id": "hi-IN-SwaraNeural", "name": "Swara (Hindi Online)", "gender": "female", "accent": "Hindi", "language": "hi-IN", "engine": "edge_tts", "description": "Default Natural Hindi & Hinglish (Online EdgeTTS)", "personality": "Warm and clear Hindi"},
    {"id": "hi-IN-MadhurNeural", "name": "Madhur (Hindi Online)", "gender": "male", "accent": "Hindi", "language": "hi-IN", "engine": "edge_tts", "description": "Expressive Hindi male (Online EdgeTTS)", "personality": "Confident Hindi male"},
    {"id": "kitten:Bella", "name": "Bella (Offline KittenTTS)", "gender": "female", "accent": "Offline Local", "language": "en", "engine": "kittentts", "description": "Offline Local ~80MB (Warm female)", "personality": "Warm and natural"},
    {"id": "kitten:Luna", "name": "Luna (Offline KittenTTS)", "gender": "female", "accent": "Offline Local", "language": "en", "engine": "kittentts", "description": "Offline Local ~80MB (Soft female)", "personality": "Gentle and calm"},
    {"id": "kitten:Rosie", "name": "Rosie (Offline KittenTTS)", "gender": "female", "accent": "Offline Local", "language": "en", "engine": "kittentts", "description": "Offline Local ~80MB (Bright female)", "personality": "Bright and friendly"},
    {"id": "kitten:Kiki", "name": "Kiki (Offline KittenTTS)", "gender": "female", "accent": "Offline Local", "language": "en", "engine": "kittentts", "description": "Offline Local ~80MB (Youthful female)", "personality": "Lively and expressive"},
    {"id": "kitten:Jasper", "name": "Jasper (Offline KittenTTS)", "gender": "male", "accent": "Offline Local", "language": "en", "engine": "kittentts", "description": "Offline Local ~80MB (Balanced male)", "personality": "Clear and natural"},
    {"id": "kitten:Bruno", "name": "Bruno (Offline KittenTTS)", "gender": "male", "accent": "Offline Local", "language": "en", "engine": "kittentts", "description": "Offline Local ~80MB (Deep male)", "personality": "Deep and grounded"},
    {"id": "kitten:Hugo", "name": "Hugo (Offline KittenTTS)", "gender": "male", "accent": "Offline Local", "language": "en", "engine": "kittentts", "description": "Offline Local ~80MB (Crisp male)", "personality": "Crisp and clear"},
    {"id": "kitten:Leo", "name": "Leo (Offline KittenTTS)", "gender": "male", "accent": "Offline Local", "language": "en", "engine": "kittentts", "description": "Offline Local ~80MB (Warm male)", "personality": "Warm and steady"},
    {"id": "kittentts", "name": "KittenTTS Bella (Offline Auto)", "gender": "female", "accent": "Offline Local", "language": "en", "engine": "kittentts", "description": "Offline Local KittenTTS mini-0.8 (~80MB)", "personality": "Fast offline neural voice"},
    {"id": "en-US-AriaNeural", "name": "Aria (Online)", "gender": "female", "accent": "US", "language": "en-US", "engine": "edge_tts", "description": "Warm and friendly (Online EdgeTTS)", "personality": "Friendly and conversational"},
    {"id": "en-IN-NeerjaNeural", "name": "Neerja (Online)", "gender": "female", "accent": "Indian", "language": "en-IN", "engine": "edge_tts", "description": "Indian English warmth (Online EdgeTTS)", "personality": "Warm and expressive"},
    {"id": "en-IN-PrabhatNeural", "name": "Prabhat (Online)", "gender": "male", "accent": "Indian", "language": "en-IN", "engine": "edge_tts", "description": "Indian clarity (Online EdgeTTS)", "personality": "Clear and professional"},
    {"id": "en-US-JennyNeural", "name": "Jenny (Online)", "gender": "female", "accent": "US", "language": "en-US", "engine": "edge_tts", "description": "Professional and clear (Online EdgeTTS)", "personality": "Professional and articulate"},
    {"id": "en-US-GuyNeural", "name": "Guy (Online)", "gender": "male", "accent": "US", "language": "en-US", "engine": "edge_tts", "description": "Confident and professional (Online EdgeTTS)", "personality": "Confident and authoritative"},
    {"id": "en-US-DavisNeural", "name": "Davis (Online)", "gender": "male", "accent": "US", "language": "en-US", "engine": "edge_tts", "description": "Warm and conversational (Online EdgeTTS)", "personality": "Warm and approachable"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia (Online)", "gender": "female", "accent": "UK", "language": "en-GB", "engine": "edge_tts", "description": "British elegance (Online EdgeTTS)", "personality": "Elegant and refined"},
    {"id": "en-GB-RyanNeural", "name": "Ryan (Online)", "gender": "male", "accent": "UK", "language": "en-GB", "engine": "edge_tts", "description": "British sophistication (Online EdgeTTS)", "personality": "Sophisticated and clear"},
    {"id": "en-US-AnaNeural", "name": "Ana (Online)", "gender": "female", "accent": "US", "language": "en-US", "engine": "edge_tts", "description": "Energetic and cheerful (Online EdgeTTS)", "personality": "Cheerful and enthusiastic"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher (Online)", "gender": "male", "accent": "US", "language": "en-US", "engine": "edge_tts", "description": "Deep and reassuring (Online EdgeTTS)", "personality": "Calm and reassuring"},
    {"id": "en-GB-LibbyNeural", "name": "Libby (Online)", "gender": "female", "accent": "UK", "language": "en-GB", "engine": "edge_tts", "description": "Young and friendly British (Online EdgeTTS)", "personality": "Youthful and energetic"},
    {"id": "en-US-EricNeural", "name": "Eric (Online)", "gender": "male", "accent": "US", "language": "en-US", "engine": "edge_tts", "description": "Natural and friendly (Online EdgeTTS)", "personality": "Casual and friendly"},
]

# Default preview text
DEFAULT_PREVIEW_TEXT = "Hello! This is a sample of my voice. I'm here to assist you with anything you need."

# ============================================================================
# CACHING SYSTEM for Voice Previews
# ============================================================================

class VoicePreviewCache:
    """In-memory LRU cache for voice previews with expiration"""
    
    def __init__(self, max_size: int = 50, expiry_seconds: int = 3600):
        self.cache: Dict[str, dict] = {}
        self.max_size = max_size
        self.expiry_seconds = expiry_seconds
        self.hits = 0
        self.misses = 0
    
    def get_cache_key(self, voice_id: str, text: str) -> str:
        """Generate cache key from voice_id and text"""
        content = f"{voice_id}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[dict]:
        """Get cached preview if exists and not expired"""
        if key in self.cache:
            cached = self.cache[key]
            if time.time() - cached['timestamp'] < self.expiry_seconds:
                self.hits += 1
                return cached['data']
            else:
                # Expired, remove
                del self.cache[key]
        
        self.misses += 1
        return None
    
    def set(self, key: str, data: dict):
        """Cache preview data with LRU eviction"""
        # If cache is full, remove oldest entry
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
        
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%"
        }

# Global cache instance
preview_cache = VoicePreviewCache()

def generate_voice_preview(voice_id: str, text: str) -> str:
    """Generate voice preview audio data URI (in-memory, accurate WAV/MP3 MIME, offline fallback)."""
    import asyncio
    import base64
    from ai_assistant.voice.text_cleaner import clean_text_for_tts, prepare_text_for_kitten_tts

    clean_sample = clean_text_for_tts(text) or text
    vid_str = str(voice_id or "hi-IN-SwaraNeural").strip()
    is_kitten = vid_str.lower() == "kittentts" or vid_str.lower().startswith("kitten:")

    def _kitten_wav_uri() -> str:
        cleaned_k = prepare_text_for_kitten_tts(clean_sample) or clean_sample
        model = load_kitten_mini_model()
        k_voice = resolve_kitten_voice(vid_str)
        pcm = model.generate(cleaned_k, voice=k_voice, speed=1.0, clean_text=True)
        wav_bytes = pcm_to_wav_bytes(pcm, sample_rate=24000)
        b64 = base64.b64encode(wav_bytes).decode("utf-8")
        return f"data:audio/wav;base64,{b64}"

    if is_kitten:
        return _kitten_wav_uri()

    # EdgeTTS preview first; fall back seamlessly to local KittenTTS mini-0.8 if offline / 503
    try:
        import edge_tts

        resolved_voice = resolve_edge_voice(clean_sample, vid_str) if TTS_SERVICE_AVAILABLE else vid_str

        async def _fetch_edge() -> bytes:
            comm = edge_tts.Communicate(clean_sample, resolved_voice)
            buf = bytearray()
            async for chunk in comm.stream():
                if chunk.get("type") == "audio":
                    data = chunk.get("data")
                    if data:
                        buf.extend(data)
            return bytes(buf)

        async def _fetch_edge_timed() -> bytes:
            return await asyncio.wait_for(_fetch_edge(), timeout=10.0)

        try:
            asyncio.get_running_loop()
            has_running_loop = True
        except RuntimeError:
            has_running_loop = False

        if has_running_loop:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                audio_bytes = pool.submit(lambda: asyncio.run(_fetch_edge_timed())).result(timeout=12.0)
        else:
            audio_bytes = asyncio.run(_fetch_edge_timed())
        if not audio_bytes:
            raise RuntimeError("Empty EdgeTTS preview stream")
        b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return f"data:audio/mp3;base64,{b64}"
    except Exception as edge_err:
        logging.warning(f"EdgeTTS preview failed ({edge_err}), falling back to offline KittenTTS mini-0.8")
        if TTS_SERVICE_AVAILABLE:
            return _kitten_wav_uri()
        raise

# ============================================================================
# API ENDPOINTS
# ============================================================================

@voice_bp.route('/settings', methods=['GET'])
def api_get_voice_settings():
    from ai_assistant.voice.voice_settings_manager import get_settings_manager
    manager = get_settings_manager()
    return jsonify({
        'success': True,
        'settings': manager.load_settings()
    })

@voice_bp.route('/settings', methods=['POST'])
def api_save_voice_settings():
    from flask import request
    from ai_assistant.voice.voice_settings_manager import get_settings_manager
    data = request.json
    manager = get_settings_manager()
    manager.save_settings(data)
    return jsonify({'success': True, 'settings': manager.load_settings()})
@voice_bp.route('/list', methods=['GET'])
def api_list_voices():
    """Get list of available AI voices"""
    try:
        return jsonify({
            "success": True,
            "voices": AVAILABLE_VOICES,
            "default": get_tts_voice_id(),
            "total": len(AVAILABLE_VOICES)
        }), 200
    except Exception as e:
        logging.error(f"Error fetching voice list: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch voices"
        }), 500

@voice_bp.route('/preview', methods=['POST'])
@limiter.limit("10 per minute")  # Rate limiting
def api_preview_voice():
    """Generate preview audio for a voice (with caching)"""
    
    # Check if voice synthesis is available
    if not VOICE_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Voice synthesis not available. No TTS engine is installed."
        }), 503
    
    try:
        # Get and validate request data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        voice_id = data.get('voice_id')
        if not voice_id:
            return jsonify({
                "success": False,
                "error": "voice_id is required"
            }), 400
        
        # Validate voice_id exists
        voice_info = next((v for v in AVAILABLE_VOICES if v['id'] == voice_id), None)
        if not voice_info:
            return jsonify({
                "success": False,
                "error": f"Invalid voice_id: {voice_id}. Use /api/voice/list to get valid voices."
            }), 404
        
        # Get sample text (with length limit for safety)
        sample_text = data.get('text', DEFAULT_PREVIEW_TEXT)
        if len(sample_text) > 500:
            return jsonify({
                "success": False,
                "error": "Text too long. Maximum 500 characters allowed."
            }), 400
        
        # Check cache first
        cache_key = preview_cache.get_cache_key(voice_id, sample_text)
        cached_audio = preview_cache.get(cache_key)
        
        if cached_audio:
            # Return from cache (fast!)
            return jsonify({
                "success": True,
                "voice_id": voice_id,
                "voice_name": voice_info['name'],
                "audio_data": cached_audio,
                "text": sample_text,
                "cached": True
            }), 200
        
        # Generate audio using Edge-TTS
        try:
            audio_data_base64 = generate_voice_preview(voice_id, sample_text)
            
            # Cache the result
            preview_cache.set(cache_key, audio_data_base64)
            
            return jsonify({
                "success": True,
                "voice_id": voice_id,
                "voice_name": voice_info['name'],
                "audio_data": audio_data_base64,
                "text": sample_text,
                "cached": False
            }), 200
            
        except ImportError as ie:
            logging.error(f"Import error in preview generation: {ie}")
            return jsonify({
                "success": False,
                "error": "Required library not available"
            }), 503
        except asyncio.TimeoutError:
            logging.error("Edge-TTS timeout")
            return jsonify({
                "success": False,
                "error": "Voice generation timed out. Please try again."
            }), 504
        except Exception as e:
            logging.error(f"Edge-TTS preview failed: {str(e)}")
            return jsonify({
                "success": False,
                "error": f"Preview generation failed: {str(e)}"
            }), 500
            
    except Exception as e:
        logging.error(f"Voice preview error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to generate preview"
        }), 500

@voice_bp.route('/cache/stats', methods=['GET'])
def api_cache_stats():
    """Get cache statistics (for monitoring)"""
    try:
        stats = preview_cache.get_stats()
        return jsonify({
            "success": True,
            "cache_stats": stats
        }), 200
    except Exception as e:
        logging.error(f"Error getting cache stats: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to get cache stats"
        }), 500


@voice_bp.route('/status', methods=['GET'])
def api_tts_status():
    """Get live single-speaker TTS & EchoGuard & overlay status."""
    tts_status = get_tts_service().get_status() if TTS_SERVICE_AVAILABLE else {"speaking": False}
    echo_status = get_echo_guard().get_status() if ECHO_GUARD_AVAILABLE else {}
    return jsonify({
        "success": True,
        "tts": tts_status,
        "echo_guard": echo_status,
        "overlay": get_overlay_state(),
    }), 200


@voice_bp.route('/speak', methods=['POST'])
def api_tts_speak():
    """Speak text through the single unified desktop speaker pipeline."""
    if not TTS_SERVICE_AVAILABLE:
        return jsonify({"success": False, "error": "TTS output service unavailable"}), 503

    data = request.get_json(force=True, silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify({"success": False, "error": "text is required"}), 400

    interrupt = bool(data.get("interrupt", True))
    wait = bool(data.get("wait", False))
    source = str(data.get("source", "api"))
    voice_id = data.get("voice_id")
    engine = data.get("engine")

    queued = get_tts_service().speak(
        text,
        interrupt=interrupt,
        wait=wait,
        source=source,
        voice=voice_id,
        engine=engine,
    )
    return jsonify({
        "success": bool(queued),
        "queued": bool(queued),
        "status": get_tts_service().get_status(),
    }), 200


@voice_bp.route('/stop', methods=['POST'])
def api_tts_stop():
    """Immediately stop ongoing TTS playback and flush pending queue (barge-in)."""
    data = request.get_json(force=True, silent=True) or {}
    reason = str(data.get("reason", "api_stop"))
    try:
        from ai_assistant.core.jarvis_persona import get_lifecycle_coordinator
        get_lifecycle_coordinator().cancel_all(reason=reason)
    except Exception:
        pass
    if TTS_SERVICE_AVAILABLE:
        get_tts_service().stop(reason=reason)
    else:
        set_tts_active(False)
    return jsonify({"success": True, "stopped": True}), 200


def _get_chat_store():
    try:
        from utils.chat_session_store import get_session_store
    except ImportError:
        from backend.utils.chat_session_store import get_session_store
    return get_session_store()


_WAKE_ACK_DEDUP_LOCK = threading.Lock()
_RECENT_WAKE_ACKS: Dict[str, Tuple[float, Dict[str, Any]]] = {}


@voice_bp.route('/wake-ack', methods=['POST', 'OPTIONS'])
def api_wake_ack():
    """Generate and optionally speak a dynamic wake, startup, or new-session greeting."""
    if request.method == 'OPTIONS':
        return ('', 204)
    data = request.get_json(force=True, silent=True) or {}
    wake_word = str(data.get("wake_word", "") or "")
    raw_transcript = str(data.get("raw_transcript", "") or "")
    kind = str(data.get("kind", "wake") or "wake").strip().lower()
    lang_hint = data.get("language_hint")
    speak_flag = bool(data.get("speak", False))
    wait_flag = bool(data.get("wait", False))
    source = str(data.get("source", "wake_ack") or "wake_ack")

    dedup_key = f"{kind}:{source}:{wake_word.strip().lower()}"
    if kind in ("startup", "new_session", "wake"):
        now_m = time.monotonic()
        with _WAKE_ACK_DEDUP_LOCK:
            recent = _RECENT_WAKE_ACKS.get(dedup_key)
            window_s = 2.0 if kind in ("startup", "new_session") else 0.85
            if recent and (now_m - recent[0]) < window_s:
                cached_resp = dict(recent[1])
                cached_resp["deduplicated"] = True
                return jsonify(cached_resp), 200

    message = ""
    detected_lang = "hinglish"
    try:
        from ai_assistant.core.jarvis_persona import (
            detect_language_hint,
            generate_session_greeting,
            generate_wake_acknowledgment,
        )
        detected_lang = str(lang_hint or detect_language_hint(raw_transcript or wake_word))
        if kind in ("startup", "new_session"):
            message = generate_session_greeting(kind=kind, language_hint=detected_lang)
        else:
            message = generate_wake_acknowledgment(
                wake_word=wake_word,
                raw_transcript=raw_transcript,
                language_hint=detected_lang,
            )
    except Exception as exc:
        logger.debug(f"Wake ack generator fallback: {exc}")

    store = None
    sess_id = None
    boot_id = None
    msg_id = None
    created_startup = True
    try:
        store = _get_chat_store()
        boot_id = store.get_boot_id()
        sess = store.get_current_session()
        sess_id = sess.get("id")
        if kind == "startup":
            recorded_msg, created_startup = store.ensure_startup_greeting(
                greeting_text=message,
                source=source,
                emit_event=True,
            )
            if recorded_msg:
                msg_id = recorded_msg.get("message_id")
                if not created_startup and recorded_msg.get("text"):
                    message = str(recorded_msg["text"])
        elif kind == "new_session":
            if message:
                msg_id = f"greeting_{sess_id}"
                if not sess.get("messages"):
                    store.record_message(
                        "ai",
                        message,
                        source=source,
                        is_voice=False,
                        message_id=msg_id,
                    )
        else:
            store.record_activity(
                "wake",
                "Wake word acknowledged",
                f"{wake_word or raw_transcript or 'wake'} -> {message}".strip(),
                source=source,
                status="info",
            )
    except Exception as store_exc:
        logger.debug(f"Wake ack session store note: {store_exc}")

    queued = False
    finished = False
    if speak_flag and message and _is_tts_enabled() and TTS_SERVICE_AVAILABLE and (kind != "startup" or created_startup):
        try:
            tts_svc = get_tts_service()
            queued = bool(
                tts_svc.speak(
                    message,
                    interrupt=True,
                    wait=False,
                    source=source,
                )
            )
            if queued and wait_flag:
                finished = bool(tts_svc.wait_until_idle(timeout=15.0))
        except Exception as exc:
            logger.debug(f"Wake ack speech failed: {exc}")

    resp_payload = {
        "success": True,
        "text": message,
        "message": message,
        "message_id": msg_id,
        "session_id": sess_id,
        "boot_id": boot_id,
        "created": created_startup if kind == "startup" else True,
        "language_hint": detected_lang,
        "queued": queued,
        "finished": finished if wait_flag else False,
        "spoken": queued,
        "kind": kind,
    }
    with _WAKE_ACK_DEDUP_LOCK:
        _RECENT_WAKE_ACKS[dedup_key] = (time.monotonic(), dict(resp_payload))
        if len(_RECENT_WAKE_ACKS) > 24:
            oldest = min(_RECENT_WAKE_ACKS.items(), key=lambda kv: kv[1][0])[0]
            _RECENT_WAKE_ACKS.pop(oldest, None)

    return jsonify(resp_payload), 200

# ============================================================================
# CACHE PRE-WARMING (Optional - can be called at startup)
# ============================================================================

def prewarm_voice_cache():
    """Pre-generate previews for all voices with default text"""
    if not VOICE_AVAILABLE:
        logging.warning("Cannot prewarm cache: Edge-TTS not available")
        return
    
    logging.info("„ Pre-warming voice preview cache...")
    success_count = 0
    
    for voice in AVAILABLE_VOICES:
        try:
            voice_id = voice['id']
            audio_data = generate_voice_preview(voice_id, DEFAULT_PREVIEW_TEXT)
            cache_key = preview_cache.get_cache_key(voice_id, DEFAULT_PREVIEW_TEXT)
            preview_cache.set(cache_key, audio_data)
            success_count += 1
            logging.info(f"   … Cached preview for {voice['name']}")
        except Exception as e:
            logging.warning(f"   š  Failed to cache {voice['name']}: {e}")
    
    logging.info(f"… Cache pre-warming complete: {success_count}/{len(AVAILABLE_VOICES)} voices cached")


# ============================================================================
# PROFESSIONAL VOICE SERVICE INTEGRATION
# ============================================================================

# Import voice service manager
voice_manager = None

VOICE_SERVICE_AVAILABLE = True
logging.info("Voice Service Manager available (consolidated)")


def init_professional_voice_services(socketio=None):
    """Initialize professional voice system (call from backend startup)"""
    global voice_manager
    
    if not VOICE_SERVICE_AVAILABLE:
        return False
    
    try:
        logging.info("Ž¤ Initializing Professional Voice System...")
        
        voice_manager = get_voice_service_manager(
            enable_wake_word=True,
            enable_neural_tts=True,
            enable_vad=True,
            enable_speaker_recognition=True
        )
        
        # Set up WebSocket callbacks if provided
        if socketio:
            def on_wake_word(word, confidence):
                socketio.emit('wake_word_detected', {
                    'wake_word': word,
                    'confidence': confidence,
                    'timestamp': time.time()
                })
            
            def on_speaker(speaker):
                socketio.emit('speaker_identified', {
                    'speaker': speaker,
                    'timestamp': time.time()
                })
            
            voice_manager.on_wake_word_detected = on_wake_word
            voice_manager.on_speaker_identified = on_speaker
        
        # Start services (only open PyAudio wake loop here if Vosk decoder is actually loaded;
        # otherwise companion_voice handles lightweight Whisper/VAD wake detection without mic contention)
        has_vosk_decoder = bool(
            voice_manager.wake_word_manager
            and getattr(voice_manager.wake_word_manager.detector, 'decoder', None) is not None
        )
        if has_vosk_decoder:
            voice_manager.start()
        else:
            voice_manager.is_running = True
            logging.info("Wake word Vosk decoder not present; delegating wake-word audio loop to companion voice listener")
        
        logging.info("… Professional Voice System activated!")
        return True
        
    except Exception as e:
        logging.error(f"Failed to initialize professional voice: {e}")
        return False


# Professional Voice API Endpoints

@voice_bp.route('/professional/status', methods=['GET'])
def get_professional_voice_status():
    """Get status of professional voice services"""
    if not voice_manager:
        return jsonify({
            'available': False,
            'error': 'Professional voice services not initialized'
        }), 503
    
    try:
        status = voice_manager.get_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@voice_bp.route('/professional/wake-word/start', methods=['POST'])
def start_professional_wake_word():
    """Start professional wake word detection"""
    if not voice_manager:
        return jsonify({'error': 'Voice services not available'}), 503
    
    try:
        voice_manager.start()
        return jsonify({
            'success': True,
            'message': 'Wake word detection started'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@voice_bp.route('/professional/wake-word/stop', methods=['POST'])
def stop_professional_wake_word():
    """Stop professional wake word detection"""
    if not voice_manager:
        return jsonify({'error': 'Voice services not available'}), 503
    
    try:
        voice_manager.stop()
        return jsonify({
            'success': True,
            'message': 'Wake word detection stopped'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@voice_bp.route('/professional/tts/speak', methods=['POST'])
def professional_tts_speak():
    """Synthesize speech using neural TTS engine"""
    if not voice_manager:
        return jsonify({'error': 'TTS not available'}), 503
    
    data = request.json
    text = data.get('text', '')
    language = data.get('language', 'en')
    gender = data.get('gender', 'female')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        from flask import send_file
        audio_file = voice_manager.speak_text(text, language, gender)
        
        if audio_file and os.path.exists(audio_file):
            return send_file(
                audio_file,
                mimetype='audio/wav',
                as_attachment=False,
                download_name='speech.wav'
            )
        else:
            return jsonify({'error': 'TTS synthesis failed'}), 500
            
    except Exception as e:
        logging.error(f"Professional TTS error: {e}")
        return jsonify({'error': str(e)}), 500


@voice_bp.route('/professional/tts/voices', methods=['GET'])
def get_professional_voices():
    """Get list of available neural TTS voices"""
    if not voice_manager:
        return jsonify({'error': 'TTS not available'}), 503
    
    try:
        voices = voice_manager.get_available_voices()
        return jsonify(voices), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Export initialization function
__all__ = ['voice_bp', 'init_professional_voice_services', 'prewarm_voice_cache']


# =============================================================================
# Section 3: Chat & Voice WebSocket Handlers (from chat_voice_handlers_new.py)
# =============================================================================

# ==============================================
# Fixed Chat & Voice Integration - Socket.IO Events
# ==============================================
"""
Unified command handler with proper routing:
1. Local Tools First (AdvancedConversationalAI) - for system commands
2. External AI Fallback (UnifiedChatInterface) - for general queries
"""

from datetime import datetime
from flask_socketio import emit
from flask import request
from flask_jwt_extended import decode_token
import time
import threading

# Import required modules
# Lazy loading for AI modules
LLM_PROVIDER_AVAILABLE = True
CONVERSATIONAL_AI_AVAILABLE = True

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Learning router (set by modern_web_backend.py)
learning_router = None

def set_learning_router(router):
    """Set learning router for this module"""
    global learning_router
    learning_router = router

# ==============================================
# Persistent Conversational AI Singleton
# ==============================================
_conv_ai_instance = None
_conv_ai_lock = threading.Lock()

def _default_automation_callback(action, param):
    """Execute automation actions"""
    try:
        if action == 'open_application':
            from ai_assistant.core.core import open_application
            return open_application(param)
        elif action == 'close_application':
            from ai_assistant.core.core import close_application
            return close_application(param)
        elif action == 'get_running_apps':
            from ai_assistant.core.system import get_running_processes
            return get_running_processes()
    except Exception as e:
        return f"Action error: {str(e)}"
    return None

def get_conv_ai(automation_callback=None):
    """Get or create the singleton AdvancedConversationalAI instance."""
    global _conv_ai_instance
    if _conv_ai_instance is None:
        with _conv_ai_lock:
            if _conv_ai_instance is None:
                from ai_assistant.ai.conversational_ai import AdvancedConversationalAI
                cb = automation_callback or _default_automation_callback
                _conv_ai_instance = AdvancedConversationalAI(automation_callback=cb)
    if automation_callback and _conv_ai_instance:
        _conv_ai_instance.automation_callback = automation_callback
    return _conv_ai_instance

# ==============================================
# Echo Prevention: Content-Based Acoustic Echo Cancellation
# ==============================================
# Replaced the old timer/cooldown approach with EchoGuard:
# Instead of blanket-muting the mic for N seconds, the system now
# compares what the speakers played vs what the mic hears using
# FFT band-energy subtraction. This allows user interruption during
# TTS playback and auto-calibrates to the room.
#
# The set_tts_active / is_tts_active functions are kept for backward
# compatibility but now delegate to EchoGuard. Legacy timer fallback
# is used only if EchoGuard import failed.
_tts_cooldown_until = 0   # Legacy fallback only

def _note_tts_output_to_echo_guard(audio_b64: str) -> None:
    """Decode base64 TTS audio (WAV or MP3) and feed it to EchoGuard for echo tracking."""
    if not ECHO_GUARD_AVAILABLE or not audio_b64:
        return
    try:
        import base64
        import io
        import wave
        import numpy as np

        raw_bytes = base64.b64decode(audio_b64.split(",", 1)[-1])
        if raw_bytes[:4] == b"RIFF":
            with wave.open(io.BytesIO(raw_bytes), 'rb') as wf:
                sr = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
                pcm = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        elif TTS_SERVICE_AVAILABLE:
            sr = 24000
            pcm = decode_audio_bytes_to_pcm24k(raw_bytes)
        else:
            return

        if pcm.size > 0:
            guard = get_echo_guard()
            level = float(np.sqrt(np.mean(pcm ** 2)))
            guard.note_output(pcm, sr, level=level)
    except Exception as e:
        logger.debug(f"[EchoGuard] note_output failed (non-fatal): {e}")


def set_tts_active(active: bool, cooldown_ms: int = 10000):
    """Mark TTS as active — backward-compatible wrapper with EchoGuard sync + 0.85s tail."""
    global _tts_cooldown_until
    if ECHO_GUARD_AVAILABLE:
        if active:
            _tts_cooldown_until = _time_module.time() + (cooldown_ms / 1000)
            logger.debug("[ECHO] EchoGuard active — legacy timer set as fallback")
        else:
            _tts_cooldown_until = _time_module.time() + 0.85  # Room reverb tail protection
            get_echo_guard().reset()
            logger.debug("[ECHO] TTS done — EchoGuard reset, 0.85s tail cooldown")
    else:
        if active:
            _tts_cooldown_until = _time_module.time() + (cooldown_ms / 1000)
            logger.info(f"[ECHO] TTS active flag set — blocking audio for {cooldown_ms}ms")
        else:
            _tts_cooldown_until = _time_module.time() + 1.5
            logger.info("[ECHO] TTS active flag reset with 1.5s tail cooldown")


def is_tts_active():
    """Check if TTS is active or still in cooldown period.

    With EchoGuard: returns True only as a fallback indicator.  The real
    echo decision happens inside is_echo_not_user().
    Without EchoGuard: behaves like the original timer-based check.
    """
    return _time_module.time() < _tts_cooldown_until


def is_echo_not_user(pcm_bytes: bytes, sample_rate: int = 16000) -> bool:
    """Content-based echo check: returns True if the audio is OUR echo (reject it).

    This replaces the old ``is_tts_active()`` blanket-mute.  If EchoGuard is
    available, it uses band-energy subtraction.  Otherwise, falls back to the
    legacy timer.

    Parameters
    ----------
    pcm_bytes : bytes
        Raw 16-bit PCM audio from the microphone.
    sample_rate : int
        Sample rate (default 16000).

    Returns
    -------
    bool
        True → this is echo, ignore it.
        False → this is a real user voice, process it.
    """
    if not ECHO_GUARD_AVAILABLE:
        return is_tts_active()  # Legacy fallback

    try:
        import numpy as np
        guard = get_echo_guard()

        if not guard.is_playing and not is_tts_active():
            return False  # Nothing playing, mic is free

        pcm = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        level = float(np.sqrt(np.mean(pcm ** 2))) if pcm.size > 0 else 0.0

        user_speaking = guard.is_user_speech(pcm, sample_rate, level=level)
        return not user_speaking  # True = echo (reject), False = real voice (accept)
    except Exception as e:
        logger.debug(f"[EchoGuard] is_echo_not_user error, falling back to timer: {e}")
        return is_tts_active()

# SocketIO will be injected
_socketio = None

# ==============================================
# Live 4D Orb & Minimized Desktop Overlay State
# ==============================================
_overlay_lock = threading.Lock()
_overlay_idle_timer: Optional[threading.Timer] = None
_client_visibility: Dict[str, bool] = {}
_OVERLAY_STATE: Dict[str, Any] = {
    'state': 'idle',           # 'idle' | 'listening' | 'speaking' | 'processing' | 'error'
    'audio_level': 0.0,        # 0..100
    'tts_speaking': False,     # True strictly while backend TTSOutputService is actively outputting audio
    'app_minimized': True,     # Default True until an un-minimized WebUI/desktop client is active
    'webui_mic_active': False, # True while WebUI owns active mic capture
    'overlay_enabled': True,
    'transcript': '',
    'error_message': '',
    'source': 'system',
    'updated_at': 0.0,
}


def get_overlay_state() -> Dict[str, Any]:
    """Thread-safe snapshot of current orb & desktop overlay visibility state."""
    with _overlay_lock:
        snap = dict(_OVERLAY_STATE)
    try:
        snap['overlay_enabled'] = is_desktop_overlay_enabled()
    except Exception:
        snap['overlay_enabled'] = True
    return snap


def _cancel_idle_timer():
    global _overlay_idle_timer
    if _overlay_idle_timer is not None:
        try:
            _overlay_idle_timer.cancel()
        except Exception:
            pass
        _overlay_idle_timer = None


def _schedule_overlay_idle(delay_sec: float, expected_updated_at: float):
    """Safety transition back to idle if no newer state update superseded it."""
    global _overlay_idle_timer

    def _reset():
        with _overlay_lock:
            if abs(_OVERLAY_STATE['updated_at'] - expected_updated_at) > 1e-6:
                return
            if TTS_SERVICE_AVAILABLE and get_tts_service().is_speaking():
                return
            _OVERLAY_STATE['state'] = 'idle'
            _OVERLAY_STATE['audio_level'] = 0.0
            _OVERLAY_STATE['tts_speaking'] = False
            _OVERLAY_STATE['error_message'] = ''
            _OVERLAY_STATE['updated_at'] = time.time()
            snap = dict(_OVERLAY_STATE)
        if _socketio:
            try:
                _socketio.emit('orb_state_sync', snap)
            except Exception:
                pass

    with _overlay_lock:
        _cancel_idle_timer()
        _overlay_idle_timer = threading.Timer(max(0.5, delay_sec), _reset)
        _overlay_idle_timer.daemon = True
        _overlay_idle_timer.start()


def update_overlay_state(
    state: Optional[str] = None,
    audio_level: Optional[float] = None,
    app_minimized: Optional[bool] = None,
    transcript: Optional[str] = None,
    error_message: Optional[str] = None,
    source: Optional[str] = None,
    webui_mic_active: Optional[bool] = None,
    tts_speaking: Optional[bool] = None,
    broadcast: bool = True,
) -> Dict[str, Any]:
    """Update orb overlay state and broadcast to all connected SocketIO clients."""
    with _overlay_lock:
        if state is not None and state in ('idle', 'listening', 'speaking', 'processing', 'error'):
            if state != _OVERLAY_STATE['state'] or state == 'speaking':
                _cancel_idle_timer()
            _OVERLAY_STATE['state'] = state
            if state == 'idle':
                _OVERLAY_STATE['audio_level'] = 0.0
                _OVERLAY_STATE['error_message'] = ''
            elif state != 'error' and error_message is None:
                _OVERLAY_STATE['error_message'] = ''
        if tts_speaking is not None:
            _OVERLAY_STATE['tts_speaking'] = bool(tts_speaking)
        if audio_level is not None:
            try:
                _OVERLAY_STATE['audio_level'] = max(0.0, min(100.0, float(audio_level)))
            except (TypeError, ValueError):
                pass
        if app_minimized is not None:
            new_min = bool(app_minimized)
            _OVERLAY_STATE['app_minimized'] = new_min
            if new_min and source in ('webui_unload', 'windows_app', 'companion_autodetect'):
                for k in list(_client_visibility.keys()):
                    _client_visibility[k] = True
            elif (not new_min) and source in ('windows_app', 'companion_autodetect') and _client_visibility:
                first_k = next(iter(_client_visibility))
                _client_visibility[first_k] = False
        if webui_mic_active is not None:
            _OVERLAY_STATE['webui_mic_active'] = bool(webui_mic_active)
        if transcript is not None:
            _OVERLAY_STATE['transcript'] = str(transcript)[:200]
        if error_message is not None:
            _OVERLAY_STATE['error_message'] = str(error_message)[:200]
        if source is not None:
            _OVERLAY_STATE['source'] = str(source)
        _OVERLAY_STATE['updated_at'] = time.time()
        try:
            _OVERLAY_STATE['overlay_enabled'] = is_desktop_overlay_enabled()
        except Exception:
            pass
        snap = dict(_OVERLAY_STATE)

    if broadcast and _socketio:
        try:
            _socketio.emit('orb_state_sync', snap)
        except Exception:
            pass
    return snap


def handle_orb_state_update(data):
    """Receive live orb state & mic amplitude from WebUI or companion."""
    if not isinstance(data, dict):
        return
    update_overlay_state(
        state=data.get('state'),
        audio_level=data.get('audio_level'),
        app_minimized=data.get('app_minimized'),
        transcript=data.get('transcript'),
        error_message=data.get('error_message'),
        source=data.get('source', 'webui'),
        webui_mic_active=data.get('webui_mic_active'),
        broadcast=True,
    )


def handle_app_visibility(data):
    """Track whether connected WebUI windows are visible or minimized/hidden."""
    payload = data if isinstance(data, dict) else {}
    minimized = bool(payload.get('minimized', False))
    source = str(payload.get('source', 'visibility'))
    unloading = bool(payload.get('unloading', False))
    force = bool(payload.get('force', False))
    try:
        sid = request.sid
    except Exception:
        sid = None

    with _overlay_lock:
        if source in ('companion_autodetect', 'windows_app'):
            if minimized:
                for k in list(_client_visibility.keys()):
                    _client_visibility[k] = True
                resolved_minimized = True
            else:
                if _client_visibility:
                    first_k = next(iter(_client_visibility))
                    _client_visibility[first_k] = False
                resolved_minimized = False
        elif unloading and sid:
            _client_visibility.pop(sid, None)
            any_visible = any(not is_min for is_min in _client_visibility.values()) if _client_visibility else False
            resolved_minimized = not any_visible
        else:
            if sid:
                _client_visibility[sid] = minimized
            if force and minimized:
                for k in list(_client_visibility.keys()):
                    _client_visibility[k] = True
                resolved_minimized = True
            else:
                any_visible = any(not is_min for is_min in _client_visibility.values()) if _client_visibility else False
                resolved_minimized = not any_visible

    update_overlay_state(app_minimized=resolved_minimized, source=source, broadcast=True)


def handle_companion_wake(data):
    """Relay background wake-word activation from companion to WebUI + overlay."""
    payload = data if isinstance(data, dict) else {'wake_word': 'hey pulsar'}
    wake_word = payload.get('wake_word', 'hey pulsar')
    update_overlay_state(state='listening', transcript='', source='companion_wake', broadcast=True)
    try:
        store = _get_chat_store()
        store.record_activity(
            'wake',
            'Glowing Orb wake detected',
            f"Wake phrase: {wake_word}",
            source='companion_wake',
            status='info',
        )
    except Exception:
        pass
    if _socketio:
        try:
            _socketio.emit('wake_word_detected', {
                'wake_word': wake_word,
                'confidence': payload.get('confidence', 0.95),
                'source': 'companion',
                'timestamp': time.time(),
            })
        except Exception:
            pass


# ==============================================
# ?? PHASE 2: LIVE STREAMING & VAD ENGINE
# (Designed for Zero-Latency Windows App)
# ==============================================
import math
import struct
import io
import time

class LiveVoiceStreamer:
    """Manages raw PCM audio streams and applies Energy-based VAD"""
    def __init__(self):
        self.sessions = {}
        
    def calculate_rms(self, pcm_bytes):
        """Calculate Root Mean Square (Volume/Energy) of raw PCM data"""
        if not pcm_bytes or len(pcm_bytes) < 2: return 0
        # Assuming 16-bit PCM mono
        count = len(pcm_bytes) // 2
        try:
            shorts = struct.unpack(f"<{count}h", pcm_bytes[:count*2])
            sum_squares = sum(s*s for s in shorts)
            return math.sqrt(sum_squares / count)
        except Exception:
            return 0
            
    def start_session(self, sid, config):
        self.sessions[sid] = {
            'buffer': bytearray(),
            'config': config,
            'last_speech_time': time.time(),
            'is_speaking': False,
            'silence_threshold': 500,  # VAD RMS threshold
            'max_silence_s': 0.7       # 700ms silence = stop
        }
        logger.info(f"[VAD] Stream session started for {sid}")
        
    def add_chunk(self, sid, pcm_chunk):
        if sid not in self.sessions:
            return None # No session
            
        session = self.sessions[sid]
        session['buffer'].extend(pcm_chunk)
        
        # VAD Logic
        rms = self.calculate_rms(pcm_chunk)
        if rms > session['silence_threshold']:
            session['is_speaking'] = True
            session['last_speech_time'] = time.time()
        else:
            # Check for silence timeout
            if session['is_speaking'] and (time.time() - session['last_speech_time']) > session['max_silence_s']:
                logger.info(f"[VAD] Silence detected for {sid}. Triggering transcription!")
                return self.end_session(sid)
        return None
        
    def end_session(self, sid):
        if sid in self.sessions:
            session = self.sessions.pop(sid)
            return session['buffer'], session['config']
        return None, None

live_streamer = LiveVoiceStreamer()

def handle_stream_start(data):
    """Called by Windows App / Client when mic opens"""
    from flask import request
    live_streamer.start_session(request.sid, data)
    
def handle_stream_chunk(data):
    """Receives live PCM audio chunks (e.g. 100ms each)"""
    from flask import request
    result = live_streamer.add_chunk(request.sid, data.get('audio_bytes', b''))
    
    # If VAD detected silence, result contains the full buffer
    if result and result[0]:
        pcm_buffer, config = result
        process_live_stream_buffer(pcm_buffer, config)
        
def handle_stream_end(data):
    """Manual stop (fallback if VAD doesn't trigger)"""
    from flask import request
    result = live_streamer.end_session(request.sid)
    if result and result[0]:
        pcm_buffer, config = result
        process_live_stream_buffer(pcm_buffer, config)

def process_live_stream_buffer(pcm_buffer, config):
    """Sends the raw PCM buffer directly to Whisper"""
    assistant = get_active_assistant()
    if not assistant:
        return
        
    # We would convert raw PCM to WAV in-memory for Whisper
    import wave
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(pcm_buffer)
        
    wav_io.seek(0)
    wav_io.name = "stream.wav"
    
    def on_transcript(text):
        if _socketio:
            _socketio.emit('voice_transcript', {'text': text, 'confidence': 1.0})
            
    # Process
    import concurrent.futures
    raw_stt_lang = (get_stt_language_short() or "").strip().lower()
    whisper_lang = None if not raw_stt_lang or raw_stt_lang == "auto" else raw_stt_lang
    stream_prompt = (
        "Hey Pulsar, OK Pulsar, नमस्ते! WhatsApp, YouTube Music, Chrome, VS Code खोलो, स्क्रीनशॉट लो, बताओ क्या करना है?"
        if whisper_lang != "en"
        else "Hey Pulsar, OK Pulsar. Open WhatsApp, Chrome, YouTube Music, VS Code, take a screenshot."
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        # Use Hindi/Hinglish by default for streaming too, with proper beam_size
        future = executor.submit(
            assistant.whisper_model.transcribe, wav_io,
            beam_size=5,
            language=whisper_lang,
            initial_prompt=stream_prompt
        )
        segments, _ = future.result()
        text = " ".join([s.text for s in segments]).strip()
        
    if text:
        logger.info(f"[STREAM-VAD] Transcribed: {text}")
        stream_msg_id = None
        stream_sess_id = None
        try:
            store = _get_chat_store()
            stream_msg_id = store.next_message_id('stream_user')
            stream_sess_id = store.get_current_session().get('id')
        except Exception:
            pass
        if _socketio:
            try:
                _socketio.emit('voice_transcript', {
                    'text': text,
                    'confidence': 1.0,
                    'source': 'voice',
                    'message_id': stream_msg_id,
                    'session_id': stream_sess_id,
                })
            except Exception:
                pass
        handle_command({
            'command': text,
            'source': 'voice',
            'client_message_id': stream_msg_id,
            'provider': config.get('provider'),
            'model': config.get('model'),
            'offline_mode': config.get('offline_mode', False)
        })

# ==============================================

def _tts_overlay_callback(speaking: bool, level: float, source: str) -> None:
    """Forward real-time TTSOutputService playback telemetry to overlay orb, WebUI, and Companion."""
    set_tts_active(speaking)
    next_state = 'speaking' if speaking else 'idle'
    if not speaking:
        try:
            from ai_assistant.core.jarvis_persona import get_lifecycle_coordinator
            if get_lifecycle_coordinator().has_executing_turn():
                # Keep orb active in processing state while task continues after pre-report speech
                next_state = 'processing'
        except Exception:
            pass
    update_overlay_state(
        state=next_state,
        audio_level=level if speaking else 0.0,
        tts_speaking=bool(speaking),
        source=source or 'backend_tts',
        broadcast=True,
    )


if TTS_SERVICE_AVAILABLE:
    try:
        get_tts_service().set_state_callback(_tts_overlay_callback)
    except Exception:
        pass


def handle_voice_stop(data=None):
    """Stop ongoing TTS playback and cancel active lifecycle turns on user barge-in or gesture stop."""
    reason = str((data or {}).get('reason', 'socket_stop')) if isinstance(data, dict) else 'socket_stop'
    try:
        from ai_assistant.core.jarvis_persona import get_lifecycle_coordinator
        get_lifecycle_coordinator().cancel_all(reason=reason)
    except Exception:
        pass
    if TTS_SERVICE_AVAILABLE:
        get_tts_service().stop(reason=reason)
    else:
        set_tts_active(False)


def set_socketio(sio):
    """Set SocketIO instance and register handlers"""
    global _socketio
    _socketio = sio

    if TTS_SERVICE_AVAILABLE:
        try:
            get_tts_service().set_state_callback(_tts_overlay_callback)
        except Exception:
            pass

    # Register all handlers
    sio.on_event('connect', handle_connect)
    sio.on_event('disconnect', handle_disconnect)
    sio.on_event('command', handle_command)
    sio.on_event('voice_command', handle_voice_command)
    sio.on_event('voice_audio_data', handle_voice_audio)
    sio.on_event('voice_stop', handle_voice_stop)
    sio.on_event('tts_stop', handle_voice_stop)

    # Phase 2: Live Streaming Endpoints
    sio.on_event('stream_start', handle_stream_start)
    sio.on_event('stream_chunk', handle_stream_chunk)
    sio.on_event('stream_end', handle_stream_end)

    # Orb & Minimized Overlay Synchronization
    sio.on_event('orb_state_update', handle_orb_state_update)
    sio.on_event('app_visibility', handle_app_visibility)
    sio.on_event('companion_wake', handle_companion_wake)
    
    # Command handlers registered

# ==============================================
# WebSocket Event Handlers (as regular functions)
# ==============================================

# Fast in-memory cache for AI Settings
_authenticated_socket_sids = set()
_socket_auth_lock = threading.Lock()

def _extract_socket_access_token(auth: Any) -> Optional[str]:
    """Read a JWT from the Socket.IO auth payload or handshake header."""
    if isinstance(auth, dict):
        token = auth.get('token') or auth.get('access_token')
        if isinstance(token, str) and token.strip():
            return token.strip()

    authorization = request.headers.get('Authorization', '')
    scheme, _, token = authorization.partition(' ')
    return token.strip() if scheme.lower() == 'bearer' and token.strip() else None


def handle_connect(auth=None):
    """Handle Socket.IO client connection with optional JWT authentication."""
    token = _extract_socket_access_token(auth)
    client_role = request.args.get('role', 'webui') if hasattr(request, 'args') else 'webui'
    user = None
    if token:
        try:
            decoded_token = decode_token(token)
            if decoded_token.get('type') == 'access' and decoded_token.get('sub'):
                user = decoded_token.get('sub')
        except Exception:
            logger.debug("Socket.IO client token invalid/expired, continuing as guest")

    with _socket_auth_lock:
        _authenticated_socket_sids.add(request.sid)
    if client_role != 'companion':
        min_arg = request.args.get('minimized', '0') if hasattr(request, 'args') else '0'
        initial_min = str(min_arg).lower() in ('1', 'true', 'yes')
        with _overlay_lock:
            _client_visibility[request.sid] = initial_min
            any_visible = any(not is_min for is_min in _client_visibility.values())
            resolved_min = not any_visible
        update_overlay_state(app_minimized=resolved_min, source='visibility', broadcast=True)

    boot_id = None
    active_session_id = None
    try:
        store = _get_chat_store()
        boot_id = store.get_boot_id()
        active_session_id = store.get_current_session().get('id')
    except Exception:
        pass

    logger.info(f"✅ Socket.IO client connected: {request.sid} (role={client_role}, user: {user or 'local_guest'})")
    emit('connection_established', {
        'status': 'connected',
        'sid': request.sid,
        'authenticated': user is not None,
        'boot_id': boot_id,
        'active_session_id': active_session_id,
        'timestamp': datetime.now().isoformat()
    })
    emit('orb_state_sync', get_overlay_state())

_persistent_chat_session = None
_persistent_chat_lock = threading.Lock()


def reset_llm_sessions():
    """Reset cached persistent voice chat session when AI settings change."""
    global _persistent_chat_session
    with _persistent_chat_lock:
        _persistent_chat_session = None


def _resolve_request_provider_model(data: dict) -> tuple[str, str]:
    """Normalize provider/model/offline_mode from a command payload or settings."""
    from ai_assistant.ai.llm_provider import LLMFactory, is_local_provider
    raw_prov = str((data or {}).get('provider') or '').strip().lower()
    offline_mode = bool((data or {}).get('offline_mode', False))
    prov = LLMFactory.normalize_provider(raw_prov) if raw_prov else ''
    if offline_mode and not is_local_provider(prov):
        prov = 'gguf'
    if not prov:
        prov = LLMFactory.normalize_provider(get_provider() or 'gguf') or 'gguf'

    raw_model = (data or {}).get('model') or get_model()
    model = LLMFactory.sanitize_model_for_provider(prov, raw_model)
    return prov, model


def get_persistent_chat_session(provider: str, model: str):
    global _persistent_chat_session
    from ai_assistant.ai.llm_provider import UnifiedChatInterface, LLMFactory, is_local_provider

    raw_prov = str(provider or '').strip().lower()
    norm_prov = (
        'offline' if raw_prov == 'offline' else LLMFactory.normalize_provider(raw_prov or get_provider())
    )
    sanitized_model = LLMFactory.sanitize_model_for_provider(norm_prov, model)

    with _persistent_chat_lock:
        if (
            _persistent_chat_session is None
            or getattr(_persistent_chat_session, 'provider_name', None) != norm_prov
            or getattr(_persistent_chat_session, 'model', None) != sanitized_model
        ):
            _persistent_chat_session = UnifiedChatInterface(
                provider=norm_prov,
                model=sanitized_model,
                use_fallback=(not is_local_provider(norm_prov)),
            )
        return _persistent_chat_session

def handle_disconnect():
    """Handle client disconnection"""
    with _socket_auth_lock:
        _authenticated_socket_sids.discard(request.sid)
    with _overlay_lock:
        removed = _client_visibility.pop(request.sid, None)
        if removed is not None:
            any_visible = any(not is_min for is_min in _client_visibility.values()) if _client_visibility else False
            _OVERLAY_STATE['app_minimized'] = not any_visible
    if removed is not None and _socketio:
        try:
            _socketio.emit('orb_state_sync', get_overlay_state())
        except Exception:
            pass
    print(f' Œ Client disconnected: {request.sid}')

def _is_tts_enabled() -> bool:
    try:
        return bool(get_tts_config().get('enabled', True))
    except Exception:
        return True


def safe_emit(event, payload):
    """Safely emit socket events; client-side browser TTS is always suppressed (skip_tts=True)."""
    try:
        if event == 'command_response' and isinstance(payload, dict):
            payload['skip_tts'] = True

        if _socketio:
            _socketio.emit(event, payload)
        else:
            emit(event, payload)
    except OSError as e:
        logger.warning(f"⚠️ Socket emit error (ignored): {e}")
    except Exception as e:
        logger.warning(f"⚠️ General emit error: {e}")


def handle_command(data):
    """
    Handle command with intelligent routing:
    1. Local Tools First (AdvancedConversationalAI / ExecutiveBrain) - for system commands
    2. External AI Fallback (UnifiedChatInterface) - for general queries
    3. Unified Single-Speaker Streaming TTS via TTSOutputService
    """
    try:
        command_text = data.get('command') or data.get('message', '')
        source = str(data.get('source', 'chat') or 'chat')

        store = None
        sess_id = None
        boot_id = None
        user_msg_id = None
        ai_msg_id = None
        stream_id = None
        try:
            store = _get_chat_store()
            sess_id = store.get_current_session().get('id')
            boot_id = store.get_boot_id()
            user_msg_id = str(data.get('client_message_id') or '').strip() or store.next_message_id('user')
            ai_msg_id = store.next_message_id('ai')
            stream_id = ai_msg_id
        except Exception:
            pass

        if not command_text:
            snap = update_overlay_state(state='error', error_message='No command provided', source=source)
            _schedule_overlay_idle(3.5, snap['updated_at'])
            safe_emit('command_response', {
                'success': False,
                'error': 'No command provided',
                'session_id': sess_id,
                'boot_id': boot_id,
                'skip_tts': True,
                'timestamp': datetime.now().isoformat()
            })
            return

        if store is not None:
            try:
                is_voice_src = any(t in source.lower() for t in ('voice', 'companion', 'whisper', 'google'))
                store.record_message(
                    'user',
                    command_text,
                    source=source,
                    is_voice=is_voice_src,
                    message_id=user_msg_id,
                    expected_session_id=sess_id,
                )
            except Exception:
                pass

        if TTS_SERVICE_AVAILABLE:
            get_tts_service().stop(reason='new_command')

        from ai_assistant.core.jarvis_persona import (
            get_lifecycle_coordinator,
            should_speak_for_request,
            generate_conversational_greeting,
            build_persona_system_prompt,
        )
        coordinator = get_lifecycle_coordinator()
        wants_speak = should_speak_for_request(data, default_for_chat=_is_tts_enabled())
        turn_id = coordinator.begin_turn(command_text, source=source, speak=wants_speak)
        tts_enabled = wants_speak

        print(f'💬 Command received ({source}): {command_text}')
        update_overlay_state(state='processing', transcript=command_text, error_message='', source=source)

        # ============================================
        # VOICE / MODE CONTROL (Zero LLM calls)
        # ============================================
        try:
            from ai_assistant.core.local_command_normalizer import (
                parse_voice_control_command,
                execute_voice_control_command,
            )
            vc_parsed = parse_voice_control_command(command_text)
            if vc_parsed:
                def _ws_broadcast(ev, pl):
                    if _socketio:
                        _socketio.emit(ev, pl)
                    else:
                        emit(ev, pl)

                vc_res = execute_voice_control_command(vc_parsed, broadcast_fn=_ws_broadcast)
                vc_ok = bool(vc_res.get('success', True))
                vc_msg = vc_res.get('response', '')
                wants_vc_speech = bool(vc_ok and vc_msg and vc_res.get('tts') and wants_speak)
                formatted_vc, was_active = coordinator.complete_turn(
                    turn_id,
                    command_text,
                    vc_msg,
                    success=vc_ok,
                    intent='voice_control',
                    source='voice_control',
                    speak=wants_vc_speech,
                    tts_text_override=vc_msg,
                )
                if was_active:
                    vc_prov = vc_res.get('provider', 'local_voice_control')
                    vc_model = vc_res.get('model', get_model())
                    if store is not None and formatted_vc:
                        try:
                            store.record_message(
                                'ai',
                                formatted_vc,
                                source='local_voice_control',
                                is_voice=False,
                                message_id=ai_msg_id,
                                provider=vc_prov,
                                model=vc_model,
                                intent='voice_control',
                                success=vc_ok,
                                expected_session_id=sess_id,
                            )
                        except Exception:
                            pass
                    safe_emit('command_response', {
                        'success': vc_ok,
                        'response': formatted_vc,
                        'command': command_text,
                        'source': 'local_voice_control',
                        'provider': vc_prov,
                        'model': vc_model,
                        'message_id': ai_msg_id,
                        'user_message_id': user_msg_id,
                        'session_id': sess_id,
                        'boot_id': boot_id,
                        'skip_tts': True,
                        'timestamp': datetime.now().isoformat(),
                    })
                return
        except Exception as vc_err:
            logger.debug(f"Voice control check skipped in handle_command: {vc_err}")

        req_provider, req_model = _resolve_request_provider_model(data)
        req_offline_flag = bool(
            data.get('offline_mode', False)
            or str(req_provider or '').strip().lower() in ('gguf', 'local', 'offline')
        )

        # ============================================
        # PRIORITY 0: Executive Brain (Central Routing)
        # ============================================
        try:
            from ai_assistant.core.command_brain import get_executive_brain
            brain = get_executive_brain()
            brain_response = brain.receive_command(
                command_text,
                source=source,
                turn_id=turn_id,
                speak=wants_speak,
                provider_preference=req_provider,
                offline_mode=req_offline_flag,
            )

            if brain_response.action_taken != 'chatting':
                logger.info(f"🧠 Brain handled chat command: {brain_response.action_taken}")
                running_async = brain_response.action_taken in ('executing', 'running', 'queued')
                if running_async:
                    if not brain_response.success:
                        snap = update_overlay_state(state='error', error_message=brain_response.message, source='brain')
                        _schedule_overlay_idle(3.5, snap['updated_at'])
                        if store is not None:
                            try:
                                store.record_message(
                                    'ai',
                                    brain_response.message or 'Command failed',
                                    source='brain',
                                    is_voice=False,
                                    message_id=ai_msg_id,
                                    intent='brain_async',
                                    success=False,
                                    expected_session_id=sess_id,
                                )
                            except Exception:
                                pass
                    elif brain_response.active_chains:
                        snap = update_overlay_state(state='processing', transcript=command_text, source='brain')
                        _schedule_overlay_idle(12.0, snap['updated_at'])
                    if brain_response.success and store is not None and brain_response.message:
                        try:
                            store.record_activity(
                                'pre_report',
                                'Task started',
                                brain_response.message,
                                source=source,
                                status='running',
                                intent='brain_async',
                                expected_session_id=sess_id,
                            )
                        except Exception:
                            pass
                    async_payload = {
                        'success': brain_response.success,
                        'response': brain_response.message,
                        'pre_report': brain_response.message,
                        'brain_action': brain_response.action_taken,
                        'chain_id': brain_response.chain_id,
                        'active_chains': brain_response.active_chains,
                        'user_message_id': user_msg_id,
                        'session_id': sess_id,
                        'boot_id': boot_id,
                        'skip_tts': True,
                        'timestamp': datetime.now().isoformat()
                    }
                    if not brain_response.success:
                        async_payload['message_id'] = ai_msg_id
                    safe_emit('command_response', async_payload)
                    return

                if brain_response.action_taken == 'cancelled':
                    if store is not None:
                        try:
                            store.record_activity(
                                'action',
                                'Task cancelled',
                                brain_response.message or command_text,
                                source=source,
                                status='info',
                                intent='cancel',
                                expected_session_id=sess_id,
                            )
                        except Exception:
                            pass
                    coordinator.cancel_all(reason='brain_cancelled')
                    return

                formatted_brain, was_active = coordinator.complete_turn(
                    turn_id,
                    command_text,
                    brain_response.message,
                    success=bool(brain_response.success),
                    intent='brain_sync',
                    source='brain',
                    speak=wants_speak,
                )
                if was_active:
                    if store is not None and formatted_brain:
                        try:
                            store.record_message(
                                'ai',
                                formatted_brain,
                                source='brain',
                                is_voice=False,
                                message_id=ai_msg_id,
                                intent='brain_sync',
                                success=bool(brain_response.success),
                                activity_kind=('action' if brain_response.success else 'error'),
                                expected_session_id=sess_id,
                            )
                        except Exception:
                            pass
                    safe_emit('command_response', {
                        'success': brain_response.success,
                        'response': formatted_brain,
                        'brain_action': brain_response.action_taken,
                        'chain_id': brain_response.chain_id,
                        'active_chains': brain_response.active_chains,
                        'message_id': ai_msg_id,
                        'user_message_id': user_msg_id,
                        'session_id': sess_id,
                        'boot_id': boot_id,
                        'skip_tts': True,
                        'timestamp': datetime.now().isoformat()
                    })
                return
        except ImportError:
            logger.debug("Executive Brain not available, using legacy handler")

        # Fast conversational greeting / pleasantry handler (dynamic human variation)
        cmd_clean = command_text.strip().lower()
        import re
        greeting_patterns = [
            r'^(?:hi|hello|hey|suno|namaste|pranam|helo|hii|hiii|yo)\b',
            r'^(?:kaise ho|kaisa hai|kya haal|kya haal hai|aur bhai|aur dost)\b',
            r'^(?:good morning|good evening|good afternoon|good night)\b',
            r'^(?:who are you|tum kaun ho|aap kaun ho)\b',
        ]
        if any(re.search(pat, cmd_clean) for pat in greeting_patterns) and len(cmd_clean.split()) <= 4:
            greeting_reply = generate_conversational_greeting(command_text)
            logger.info(f"💬 Conversational fast-greeting: {greeting_reply}")
            formatted_greet, was_active = coordinator.complete_turn(
                turn_id,
                command_text,
                greeting_reply,
                success=True,
                intent='wake_greeting',
                source='conversational_fast_path',
                speak=wants_speak,
                tts_text_override=greeting_reply,
            )
            if was_active:
                if store is not None and formatted_greet:
                    try:
                        store.record_message(
                            'ai',
                            formatted_greet,
                            source='conversational_fast_path',
                            is_voice=False,
                            message_id=ai_msg_id,
                            provider=req_provider,
                            model=req_model,
                            intent='wake_greeting',
                            success=True,
                            expected_session_id=sess_id,
                        )
                    except Exception:
                        pass
                safe_emit('command_response', {
                    'success': True,
                    'response': formatted_greet,
                    'source': 'conversational_fast_path',
                    'provider': req_provider,
                    'model': req_model,
                    'message_id': ai_msg_id,
                    'user_message_id': user_msg_id,
                    'session_id': sess_id,
                    'boot_id': boot_id,
                    'skip_tts': True,
                    'timestamp': datetime.now().isoformat()
                })
            return

        # ============================================
        # PRIORITY 2: External AI / Local LLM (for general queries)
        # ============================================
        used_local_tools = False
        response_text = ""
        if LLM_PROVIDER_AVAILABLE and not used_local_tools:
            try:
                from ai_assistant.ai.llm_provider import LLMFactory, is_local_provider
                preferred_provider, preferred_model = req_provider, req_model
                
                print(f" Initializing Chat with Provider: {preferred_provider}, Model: {preferred_model}")

                # Get or initialize persistent chat session with user preference
                chat = get_persistent_chat_session(preferred_provider, preferred_model)
                
                # Set provider-specific system message
                provider_name = LLMFactory.normalize_provider(getattr(chat, 'provider_name', preferred_provider))
                model_name = chat.model
                
                print(f"„¹  Actual Provider: {provider_name}, Actual Model: {model_name}")

                rag_ctx = ""
                try:
                    from ai_assistant.ai.memory_retrieval import retrieve_unified_historical_context
                    rag_ctx = retrieve_unified_historical_context(
                        command_text,
                        current_session_id=sess_id,
                        only_when_triggered=True,
                    )
                except Exception as rag_err:
                    logger.debug(f"Historical RAG lookup skipped: {rag_err}")

                system_msg = build_persona_system_prompt(
                    provider=provider_name,
                    model=model_name,
                    surface=source or 'voice',
                    extra_context=rag_ctx,
                )
                if hasattr(chat, 'set_system_message'):
                    chat.set_system_message(system_msg)
                else:
                    chat.add_system_message(system_msg)

                def _is_turn_still_live() -> bool:
                    if not coordinator.is_turn_active(turn_id):
                        return False
                    if store is not None and sess_id:
                        try:
                            return store.get_current_session().get('id') == sess_id
                        except Exception:
                            pass
                    return True

                # Get streaming response from AI with Pipeline Parallelism (Pre-report -> Streaming TTS + Live Text)
                response_text = ""
                sentence_buffer = ""
                any_tts_queued = False
                is_first_token = True
                stream_error_msg = None
                tts_gen = None
                tts_svc = None
                if wants_speak and TTS_SERVICE_AVAILABLE:
                    try:
                        tts_svc = get_tts_service()
                        tts_gen = tts_svc.begin_stream(interrupt=True, source=f'external_ai_{provider_name}')
                    except Exception:
                        tts_gen = None
                        tts_svc = None

                pre_report = coordinator.emit_pre_report(
                    turn_id,
                    command_text,
                    intent='general_think',
                    source=source,
                    speak=bool(wants_speak and tts_svc is not None and tts_gen is not None),
                    stream_tts_gen=tts_gen,
                )
                if pre_report and store is not None:
                    try:
                        store.record_activity(
                            'pre_report',
                            'Thinking...',
                            pre_report,
                            source=source,
                            status='running',
                            intent='general_think',
                            provider=provider_name,
                            model=model_name,
                            expected_session_id=sess_id,
                        )
                    except Exception:
                        pass
                if pre_report and wants_speak and tts_svc is not None and tts_gen is not None:
                    any_tts_queued = True

                def _iter_with_gguf_fallback():
                    nonlocal provider_name, model_name, stream_error_msg
                    local_mode = is_local_provider(provider_name)
                    stream_iter = iter(chat.chat(command_text, stream=True))
                    first_yield = True
                    for ch in stream_iter:
                        if not _is_turn_still_live():
                            return
                        ch_str = str(ch) if ch else ""
                        # Only allow GGUF fallback when a cloud provider fails — never mask explicit local provider errors
                        if ch and first_yield and ch_str.startswith("Error:") and not local_mode:
                            try:
                                gguf_path = resolve_local_model_path('models/pulsar-final-q4_k_m.gguf')
                                if gguf_path.exists():
                                    from ai_assistant.ai.llm_provider import UnifiedChatInterface
                                    logger.warning(f"[VOICE] Cloud provider {provider_name} failed ({ch_str[:80]}), switching stream to local GGUF")
                                    fb_chat = UnifiedChatInterface(provider='gguf', model='pulsar-final-q4_k_m', use_fallback=False)
                                    provider_name = 'gguf'
                                    model_name = 'pulsar-final-q4_k_m'
                                    fb_sys = build_persona_system_prompt(provider='gguf', model=model_name, surface=source or 'voice', extra_context=rag_ctx)
                                    if hasattr(fb_chat, 'set_system_message'):
                                        fb_chat.set_system_message(fb_sys)
                                    else:
                                        fb_chat.add_system_message(fb_sys)
                                    fb_first = True
                                    for fb_ch in fb_chat.chat(command_text, stream=True):
                                        if not _is_turn_still_live():
                                            return
                                        if fb_ch:
                                            if fb_first and str(fb_ch).startswith("Error:"):
                                                stream_error_msg = str(fb_ch)
                                                return
                                            fb_first = False
                                            yield fb_ch
                                    return
                            except Exception as fb_err:
                                logger.warning(f"[VOICE] Local GGUF stream fallback failed: {fb_err}")
                        if ch and first_yield and ch_str.startswith("Error:"):
                            stream_error_msg = ch_str
                            return
                        first_yield = False
                        yield ch

                try:
                    for chunk in _iter_with_gguf_fallback():
                        if not _is_turn_still_live():
                            break
                        if chunk:
                            response_text += chunk
                            sentence_buffer += chunk

                            # Emit live text token to frontend chat UI immediately!
                            try:
                                stream_payload = {
                                    'token': chunk,
                                    'is_start': is_first_token,
                                    'provider': provider_name,
                                    'model': model_name,
                                    'stream_id': stream_id,
                                    'session_id': sess_id,
                                }
                                if _socketio:
                                    _socketio.emit('chat_stream_chunk', stream_payload)
                                else:
                                    emit('chat_stream_chunk', stream_payload)
                            except Exception:
                                pass
                            is_first_token = False

                            if tts_svc is not None and tts_gen is not None:
                                speakable_list, sentence_buffer = split_speakable_chunks(sentence_buffer, final=False)
                                for piece in speakable_list:
                                    try:
                                        if tts_svc.enqueue_sentence(piece, gen=tts_gen, source=f'external_ai_{provider_name}'):
                                            any_tts_queued = True
                                    except Exception:
                                        pass
                finally:
                    if not is_first_token and not _is_turn_still_live():
                        try:
                            end_payload = {
                                'stream_id': stream_id,
                                'session_id': sess_id,
                                'aborted': True,
                                'reason': 'interrupted_or_new_session',
                            }
                            if _socketio:
                                _socketio.emit('chat_stream_end', end_payload)
                            else:
                                emit('chat_stream_end', end_payload)
                        except Exception:
                            pass
                    if tts_svc is not None and tts_gen is not None:
                        try:
                            if sentence_buffer.strip() and wants_speak and not stream_error_msg and _is_turn_still_live():
                                tail_list, tail_rem = split_speakable_chunks(sentence_buffer, final=True)
                                if tail_rem:
                                    tail_list.append(tail_rem)
                                for piece in tail_list:
                                    if tts_svc.enqueue_sentence(piece, gen=tts_gen, source=f'external_ai_{provider_name}'):
                                        any_tts_queued = True
                            tts_svc.finish_stream(gen=tts_gen, wait=False)
                        except Exception:
                            pass
                        sentence_buffer = ""

                skip_tts_flag = True

                
                print(f'… [EXTERNAL AI - {provider_name.upper()}] {response_text[:100]}...')
                
                # Log learning
                try:
                    lr = learning_router
                    if lr:
                        lr.route_conversation(speaker='user', content=command_text, input_mode=source)
                        lr.route_conversation(speaker='assistant', content=response_text, input_mode=source)
                except Exception as e:
                    print(f"š  Could not log learning: {e}")
                
                if stream_error_msg or not response_text.strip():
                    err_text = stream_error_msg or f"Provider ({provider_name}) returned an empty response."
                    if TTS_SERVICE_AVAILABLE:
                        try:
                            get_tts_service().stop(reason='llm_error')
                        except Exception:
                            pass
                    snap = update_overlay_state(state='error', error_message=err_text, source='llm_error')
                    _schedule_overlay_idle(3.5, snap['updated_at'])
                    _, was_active = coordinator.complete_turn(
                        turn_id,
                        command_text,
                        err_text,
                        success=False,
                        intent='general_chat',
                        source=f'external_ai_{provider_name}',
                        speak=False,
                    )
                    if was_active:
                        final_msg_id = stream_id or ai_msg_id
                        if store is not None:
                            try:
                                store.record_message(
                                    'ai',
                                    err_text,
                                    source=f'external_ai_{provider_name}',
                                    is_voice=False,
                                    message_id=final_msg_id,
                                    provider=provider_name,
                                    model=model_name,
                                    intent='general_chat',
                                    success=False,
                                    expected_session_id=sess_id,
                                )
                            except Exception:
                                pass
                        safe_emit('command_response', {
                            'success': False,
                            'error': err_text,
                            'response': err_text,
                            'command': command_text,
                            'source': f'external_ai_{provider_name}',
                            'provider': provider_name,
                            'model': model_name,
                            'message_id': final_msg_id,
                            'user_message_id': user_msg_id,
                            'session_id': sess_id,
                            'boot_id': boot_id,
                            'timestamp': datetime.now().isoformat(),
                            'skip_tts': True,
                        })
                    return

                # Complete streaming turn lifecycle & emit response if still active
                formatted_resp, was_active = coordinator.complete_turn(
                    turn_id,
                    command_text,
                    response_text,
                    success=True,
                    intent='general_chat',
                    source=f'external_ai_{provider_name}',
                    speak=False,
                    tts_already_queued=any_tts_queued,
                )
                if was_active and (store is None or not sess_id or store.get_current_session().get('id') == sess_id):
                    final_msg_id = stream_id or ai_msg_id
                    if store is not None and formatted_resp:
                        try:
                            store.record_message(
                                'ai',
                                formatted_resp,
                                source=f'external_ai_{provider_name}',
                                is_voice=False,
                                message_id=final_msg_id,
                                provider=provider_name,
                                model=model_name,
                                intent='general_chat',
                                success=True,
                                expected_session_id=sess_id,
                            )
                        except Exception:
                            pass
                    try:
                        from ai_assistant.ai.memory_retrieval import persist_turn_to_conversation_ai
                        threading.Thread(
                            target=persist_turn_to_conversation_ai,
                            args=(command_text, formatted_resp),
                            kwargs={'source': source or 'chat', 'session_id': sess_id},
                            daemon=True,
                        ).start()
                    except Exception:
                        pass
                    safe_emit('command_response', {
                        'success': True,
                        'response': formatted_resp,
                        'command': command_text,
                        'source': f'external_ai_{provider_name}',
                        'provider': provider_name,
                        'model': model_name,
                        'message_id': final_msg_id,
                        'user_message_id': user_msg_id,
                        'session_id': sess_id,
                        'boot_id': boot_id,
                        'timestamp': datetime.now().isoformat(),
                        'skip_tts': skip_tts_flag
                    })

                return  # Successfully handled
                
            except Exception as llm_error:
                print(f' Œ External AI error: {llm_error}')
                if TTS_SERVICE_AVAILABLE:
                    try:
                        get_tts_service().stop(reason='llm_error')
                    except Exception:
                        pass
                snap = update_overlay_state(state='error', error_message=str(llm_error), source='llm_error')
                _schedule_overlay_idle(3.5, snap['updated_at'])
                _, was_active = coordinator.complete_turn(
                    turn_id,
                    command_text,
                    f"Error: {llm_error}",
                    success=False,
                    source='llm_error',
                    speak=False,
                )
                if was_active:
                    final_msg_id = stream_id or ai_msg_id
                    if store is not None:
                        try:
                            store.record_message(
                                'ai',
                                f"Error: {llm_error}",
                                source='llm_error',
                                is_voice=False,
                                message_id=final_msg_id,
                                provider=req_provider,
                                model=req_model,
                                success=False,
                                expected_session_id=sess_id,
                            )
                        except Exception:
                            pass
                    safe_emit('command_response', {
                        'success': False,
                        'error': str(llm_error),
                        'response': f"Error: {llm_error}",
                        'command': command_text,
                        'provider': req_provider,
                        'model': req_model,
                        'source': 'llm_error',
                        'message_id': final_msg_id,
                        'user_message_id': user_msg_id,
                        'session_id': sess_id,
                        'boot_id': boot_id,
                        'skip_tts': True,
                        'timestamp': datetime.now().isoformat(),
                    })
                return
        
        # ============================================
        # FALLBACK: Simple acknowledgment
        # ============================================
        had_fallback_fail = not response_text
        if had_fallback_fail:
            raw_fail = f'Sorry, I could not generate a response for "{command_text}". Please check your AI model settings and API keys.'
            snap = update_overlay_state(state='error', error_message=raw_fail, source='fallback')
            _schedule_overlay_idle(3.5, snap['updated_at'])
            response_text, was_active = coordinator.complete_turn(
                turn_id,
                command_text,
                raw_fail,
                success=False,
                source='fallback',
                speak=False,
            )
            if not was_active:
                return
        else:
            response_text, was_active = coordinator.complete_turn(
                turn_id,
                command_text,
                response_text,
                success=True,
                source=source,
                speak=False,
            )
            if not was_active:
                return
            
        if store is not None and response_text:
            try:
                store.record_message(
                    'ai',
                    response_text,
                    source=('fallback' if had_fallback_fail else source),
                    is_voice=False,
                    message_id=ai_msg_id,
                    provider=req_provider,
                    model=req_model,
                    success=(not had_fallback_fail),
                    expected_session_id=sess_id,
                )
            except Exception:
                pass
        safe_emit('command_response', {
            'success': not had_fallback_fail,
            'error': response_text if had_fallback_fail else None,
            'response': response_text,
            'command': command_text,
            'provider': req_provider,
            'model': req_model,
            'source': source,
            'message_id': ai_msg_id,
            'user_message_id': user_msg_id,
            'session_id': sess_id,
            'boot_id': boot_id,
            'skip_tts': True,
            'timestamp': datetime.now().isoformat()
        })
            
    except OSError as e:
         print(f"š   Critical Socket/OS Error caught in handle_command: {e}")
         # DO NOT EMIT TO USER, just log it. This prevents the "Error: [Errno 22]" chat message
         snap = update_overlay_state(state='error', error_message=str(e), source='os_error')
         _schedule_overlay_idle(3.5, snap['updated_at'])
    except Exception as e:
        print(f'Œ Command handling error: {e}')
        import traceback
        print(traceback.format_exc())
        snap = update_overlay_state(state='error', error_message=str(e), source='command_error')
        _schedule_overlay_idle(3.5, snap['updated_at'])
        
        # Only emit operational errors, not low-level system errors
        if "[Errno 22]" not in str(e):
            if store is not None:
                try:
                    store.record_message(
                        'ai',
                        f"Error: {e}",
                        source='command_error',
                        is_voice=False,
                        message_id=ai_msg_id,
                        success=False,
                        expected_session_id=sess_id,
                    )
                except Exception:
                    pass
            safe_emit('command_response', {
                'success': False,
                'error': str(e),
                'response': f"Error: {e}",
                'message_id': ai_msg_id,
                'user_message_id': user_msg_id,
                'session_id': sess_id,
                'boot_id': boot_id,
                'timestamp': datetime.now().isoformat()
            })

def handle_voice_command(data):
    """Handle voice command specifically and route to unified command handler."""
    try:
        # FIX: Frontend sends 'text', not 'transcript'. Support both for compatibility.
        transcript = data.get('text') or data.get('transcript', '')
        confidence = data.get('confidence', 0.0)
        provider = data.get('provider')
        model = data.get('model')
        language = data.get('language', 'en-US')
        offline_mode = data.get('offline_mode', False)
        
        if not transcript:
            snap = update_overlay_state(state='error', error_message='No transcript provided', source='voice')
            _schedule_overlay_idle(3.5, snap['updated_at'])
            emit('voice_response', {
                'success': False,
                'error': 'No transcript provided'
            })
            return
        
        print(f'🎤 Voice command: {transcript} (confidence: {confidence}, lang: {language})')
        
        # Forward to unified command handler which guarantees 100% parity between Text and Voice.
        # It routes through ExecutiveBrain first, then falls back to Conversational AI.
        handle_command({
            'command': transcript,
            'source': data.get('source', 'voice'),
            'client_message_id': data.get('client_message_id'),
            'provider': provider,
            'model': model,
            'offline_mode': offline_mode
        })
        
    except Exception as e:
        print(f' ❌ Voice command error: {e}')
        snap = update_overlay_state(state='error', error_message=str(e), source='voice')
        _schedule_overlay_idle(3.5, snap['updated_at'])
        emit('voice_response', {
            'success': False,
            'error': str(e)
        })

def handle_voice_audio(data):
    """Handle raw audio data from Faster-Whisper frontend (Note: now generates KittenTTS audio_base64)"""
    audio_data = data.get('audio_data', '')
    language = data.get('language')
    if not audio_data:
        return

    # ── Content-based Echo Prevention (EchoGuard) ──
    # Instead of blanket-muting the mic, we check if this audio chunk is our
    # own TTS echo or a real user voice using band-energy subtraction.
    if ECHO_GUARD_AVAILABLE:
        try:
            import base64 as _b64
            clean_b64 = audio_data.split(",")[-1] if "," in audio_data else audio_data
            raw_pcm = _b64.b64decode(clean_b64)
            if is_echo_not_user(raw_pcm, sample_rate=16000):
                logger.debug("[VOICE] EchoGuard: audio is our echo — ignoring")
                return
        except Exception as e:
            logger.debug(f"[VOICE] EchoGuard check failed, using timer fallback: {e}")
            if is_tts_active():
                logger.info("[VOICE] Ignoring voice_audio_data — TTS active (timer fallback)")
                return
    else:
        # Legacy timer-based echo prevention
        if is_tts_active():
            logger.info("[VOICE] Ignoring voice_audio_data — TTS active or in cooldown (echo prevention)")
            return

    logger.info(f"[VOICE] Received voice_audio_data! Length: {len(audio_data)}, Language: {language}")
    print(f"[VOICE] Received voice audio data (length: {len(audio_data)}, lang: {language})")
    
    def process_and_emit():
        try:
            update_overlay_state(state='processing', source='voice')
            assistant = get_active_assistant()
            if not assistant:
                logger.error("[VOICE] No active assistant instance found!")
                print("[VOICE] Error: No active assistant instance found!")
                snap = update_overlay_state(state='error', error_message='Assistant initializing', source='voice')
                _schedule_overlay_idle(3.5, snap['updated_at'])
                if _socketio:
                    _socketio.emit('voice_response', {
                        'success': False,
                        'error': True,
                        'response': "Assistant is initializing. Please try again in a moment."
                    })
                return
                
            # Update live overlay transcript only after Whisper finishes; wait for wake-word check before emitting chat transcript
            def on_transcript(text):
                logger.info(f"[VOICE] Whisper finished transcribing: {text}")
                print(f"[VOICE] Faster-Whisper transcribed: '{text}'")
                update_overlay_state(transcript=text, source='whisper')

            # Run in a thread to prevent blocking the socketio loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(assistant.process_voice_audio, audio_data, on_transcript, language=language)
                result = future.result()
            
            if result.get('success') and result.get('transcript'):
                transcript = result.get('transcript', '').strip()
                logger.info(f"[VOICE] Processed audio. Transcript: '{transcript}'")

                store = None
                sess_id = None
                user_msg_id = str(data.get('client_message_id') or '').strip() or None
                try:
                    store = _get_chat_store()
                    sess_id = store.get_current_session().get('id')
                    if not user_msg_id:
                        user_msg_id = store.next_message_id('voice_user')
                except Exception:
                    pass
                
                require_wake_word = data.get('require_wake_word')
                if require_wake_word is None:
                    require_wake_word = is_wake_word_enabled()

                from ai_assistant.core.local_command_normalizer import match_and_strip_wake_phrase
                matched_wake, clean_command = match_and_strip_wake_phrase(transcript)

                if require_wake_word:
                    if not matched_wake:
                        logger.info(f"[WAKE-WORD] Speech ignored: '{transcript}' (Wake word required)")
                        next_state = 'listening' if get_overlay_state().get('webui_mic_active') else 'idle'
                        update_overlay_state(state=next_state, transcript='', source='wake_ignored')
                        if _socketio:
                            _socketio.emit('wake_word_status', {
                                'detected': False,
                                'transcript': transcript,
                                'message': 'Say "Hey Pulsar" or "Hey Assistant" to activate'
                            })
                        return

                    logger.info(f"[WAKE-WORD] Detected wake word '{matched_wake}' in '{transcript}'")
                    if _socketio:
                        _socketio.emit('wake_word_status', {'detected': True, 'wake_word': matched_wake})
                        _socketio.emit('wake_word_detected', {'wake_word': matched_wake, 'confidence': 0.95, 'source': 'voice', 'timestamp': time.time()})
                elif matched_wake and _socketio:
                    _socketio.emit('wake_word_status', {'detected': True, 'wake_word': matched_wake})
                    _socketio.emit('wake_word_detected', {'wake_word': matched_wake, 'confidence': 0.95, 'source': 'voice', 'timestamp': time.time()})

                if matched_wake and not clean_command:
                    # User only spoke the wake word — respond with a fresh dynamic acknowledgment
                    logger.info("[WAKE-WORD] User only called wake word with no query")
                    try:
                        from ai_assistant.core.jarvis_persona import generate_wake_acknowledgment
                        reply = generate_wake_acknowledgment(wake_word=matched_wake, raw_transcript=transcript)
                    except Exception:
                        reply = ""
                    if store is not None:
                        try:
                            store.record_activity(
                                'wake',
                                f"Wake word '{matched_wake}'",
                                reply or transcript,
                                source='webui_voice',
                                status='info',
                                expected_session_id=sess_id,
                            )
                        except Exception:
                            pass
                    tts_enabled = _is_tts_enabled()
                    spoke = False
                    if reply and tts_enabled and TTS_SERVICE_AVAILABLE:
                        spoke = get_tts_service().speak(reply, interrupt=True, source='wake_greeting')
                    if not spoke:
                        update_overlay_state(state='listening', transcript=matched_wake, source='wake_greeting')
                    safe_emit('command_response', {
                        'success': True,
                        'response': reply,
                        'is_wake_ack': True,
                        'session_id': sess_id,
                        'skip_tts': True
                    })
                    return

                if matched_wake and clean_command and store is not None:
                    try:
                        store.record_activity(
                            'wake',
                            f"Wake word '{matched_wake}'",
                            clean_command,
                            source='webui_voice',
                            status='info',
                            expected_session_id=sess_id,
                        )
                    except Exception:
                        pass

                if clean_command:
                    transcript = clean_command

                if _socketio and transcript:
                    try:
                        _socketio.emit('voice_transcript', {
                            'text': transcript,
                            'confidence': 0.9,
                            'source': 'webui_voice',
                            'message_id': user_msg_id,
                            'session_id': sess_id,
                        })
                    except Exception:
                        pass

                # Pass to unified command handler
                handle_command({
                    'command': transcript,
                    'source': 'webui_voice',
                    'client_message_id': user_msg_id,
                    'provider': data.get('provider'),
                    'model': data.get('model'),
                    'offline_mode': data.get('offline_mode', False)
                })
            else:
                error_msg = result.get('error', 'Unknown audio processing error')
                logger.warning(f"[VOICE] Audio processing failed: {error_msg}")
                if any(tok in str(error_msg).lower() for tok in ('no speech', 'empty', 'silent')):
                    update_overlay_state(state='idle', transcript='', source='voice_silence')
                else:
                    snap = update_overlay_state(state='error', error_message=str(error_msg), source='voice_error')
                    _schedule_overlay_idle(3.5, snap['updated_at'])
                if _socketio:
                    _socketio.emit('voice_response', {
                        'success': False,
                        'error': True,
                        'response': f"Audio processing failed: {error_msg}"
                    })
        except Exception as e:
            import traceback
            logger.error(f"Error in background voice processing: {e}")
            snap = update_overlay_state(state='error', error_message=str(e), source='voice_error')
            _schedule_overlay_idle(3.5, snap['updated_at'])
            if _socketio:
                _socketio.emit('voice_response', {'success': False, 'error': True, 'response': str(e)})

    if _socketio:
        _socketio.start_background_task(process_and_emit)


# System stats broadcaster
def broadcast_system_stats():
    """Broadcast system statistics periodically"""
    while True:
        try:
            if PSUTIL_AVAILABLE and _socketio:
                stats = {
                    'cpu_usage': psutil.cpu_percent(interval=1),
                    'memory_usage': psutil.virtual_memory().percent,
                    'network_speed': 0  # Placeholder
                }
                _socketio.emit('system_stats_update', stats)
        except Exception as e:
            print(f'Stats broadcast error: {e}')
        time.sleep(5)  # Update every 5 seconds

# Start stats broadcaster thread
stats_thread = threading.Thread(target=broadcast_system_stats, daemon=True)
stats_thread.start()




