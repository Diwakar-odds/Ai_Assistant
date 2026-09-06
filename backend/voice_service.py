# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

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
from typing import Optional, Callable, Dict, Any
from pathlib import Path

# Record when this module was imported (used for warmup time guard)
_voice_service_import_time = _time_module.time()

# Import all voice modules
try:
    from ai_assistant.voice.wake_word_detector import get_wake_word_manager, WakeWordDetectionMode
    WAKE_WORD_AVAILABLE = True
except ImportError:
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
    
    def speak_greeting(self):
        """Speak a greeting after wake word"""
        greetings = [
            "Yes, I'm listening",
            "How can I help you?",
            "I'm ready",
            "At your service"
        ]
        
        import random
        greeting = random.choice(greetings)
        
        self.speak_text(greeting)
    
    def speak_text(self, text: str, language: str = 'en', gender: str = 'female'):
        """Speak text using neural TTS"""
        if not self.enable_neural_tts or not self.tts_engine:
            self.logger.warning("Neural TTS not available")
            return None
        
        try:
            # Map gender string to VoiceGender enum
            voice_gender = VoiceGender.FEMALE if gender == 'female' else VoiceGender.MALE
            
            # Synthesize speech
            audio_file = self.tts_engine.speak(
                text,
                language=language,
                gender=voice_gender,
                style=SpeakingStyle.FRIENDLY
            )
            
            self.logger.info(f" TTS: '{text}' † {audio_file}")
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

# Check if voice synthesis is available
try:
    import kittentts
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    logging.warning("KittenTTS not available. Voice preview will not work.")

# Available Voice Options for TTS
AVAILABLE_VOICES = [
    {"id": "kittentts", "name": "KittenTTS (AI Voice)", "gender": "female", "accent": "Neutral", "language": "en", "description": "Local KittenTTS AI Voice", "personality": "Warm and natural"},
    {"id": "en-US-AriaNeural", "name": "Aria", "gender": "female", "accent": "US", "language": "en-US", "description": "Warm and friendly", "personality": "Friendly and conversational"},
    {"id": "en-US-JennyNeural", "name": "Jenny", "gender": "female", "accent": "US", "language": "en-US", "description": "Professional and clear", "personality": "Professional and articulate"},
    {"id": "en-US-GuyNeural", "name": "Guy", "gender": "male", "accent": "US", "language": "en-US", "description": "Confident and professional", "personality": "Confident and authoritative"},
    {"id": "en-US-DavisNeural", "name": "Davis", "gender": "male", "accent": "US", "language": "en-US", "description": "Warm and conversational", "personality": "Warm and approachable"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia", "gender": "female", "accent": "UK", "language": "en-GB", "description": "British elegance", "personality": "Elegant and refined"},
    {"id": "en-GB-RyanNeural", "name": "Ryan", "gender": "male", "accent": "UK", "language": "en-GB", "description": "British sophistication", "personality": "Sophisticated and clear"},
    {"id": "en-IN-NeerjaNeural", "name": "Neerja", "gender": "female", "accent": "Indian", "language": "en-IN", "description": "Indian warmth", "personality": "Warm and expressive"},
    {"id": "en-IN-PrabhatNeural", "name": "Prabhat", "gender": "male", "accent": "Indian", "language": "en-IN", "description": "Indian clarity", "personality": "Clear and professional"},
    {"id": "en-US-AnaNeural", "name": "Ana", "gender": "female", "accent": "US", "language": "en-US", "description": "Energetic and cheerful", "personality": "Cheerful and enthusiastic"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher", "gender": "male", "accent": "US", "language": "en-US", "description": "Deep and reassuring", "personality": "Calm and reassuring"},
    {"id": "en-GB-LibbyNeural", "name": "Libby", "gender": "female", "accent": "UK", "language": "en-GB", "description": "Young and friendly British", "personality": "Youthful and energetic"},
    {"id": "en-US-EricNeural", "name": "Eric", "gender": "male", "accent": "US", "language": "en-US", "description": "Natural and friendly", "personality": "Casual and friendly"}
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

def generate_voice_preview(voice_id: str, text: str) -> dict:
    """Generate voice preview audio (internal function)"""
    import tempfile
    import asyncio
    import base64
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
    output_path = temp_file.name
    temp_file.close()
    
    # Generate audio asynchronously
    async def generate():
        from ai_assistant.voice.neural_voice_engine import get_neural_voice_engine
        engine = get_neural_voice_engine()
        result = engine.speak(text, force_engine='kittentts', output_file=output_path)
        if result and result != output_path:
            import shutil
            shutil.copy2(result, output_path)
    
    # Run async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(generate())
    
    # Read and encode as base64
    with open(output_path, 'rb') as f:
        audio_data = f.read()
    
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    # Clean up temp file
    try:
        os.unlink(output_path)
    except Exception as cleanup_error:
        logging.warning(f"Failed to clean up temp file: {cleanup_error}")
    
    return f"data:audio/mp3;base64,{audio_base64}"

# ============================================================================
# API ENDPOINTS
# ============================================================================

@voice_bp.route('/list', methods=['GET'])
def api_list_voices():
    """Get list of available AI voices"""
    try:
        return jsonify({
            "success": True,
            "voices": AVAILABLE_VOICES,
            "default": "en-US-AriaNeural",
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
            "error": "Voice synthesis not available. Edge-TTS is not installed."
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
        
        # Start services
        voice_manager.start()
        
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
# Echo Prevention: Server-side TTS-active flag
# ==============================================
# Uses a time-based approach: when TTS audio is generated, we set
# a cooldown window. Audio arriving within that window is rejected.
# The window auto-expires so even if no explicit reset comes, the
# system recovers automatically.
_tts_cooldown_until = 0

def set_tts_active(active: bool, cooldown_ms: int = 10000):
    """Mark TTS as active with a cooldown window to prevent echo/self-listening.
    
    When active=True, sets a cooldown for cooldown_ms (default 10s, enough for
    most TTS audio to finish + room echo to dissipate).
    When active=False, sets a shorter 1.5s cooldown for lingering echo.
    """
    global _tts_cooldown_until
    if active:
        # TTS is about to play — block audio for up to cooldown_ms
        _tts_cooldown_until = _time_module.time() + (cooldown_ms / 1000)
        logger.info(f"[ECHO] TTS active flag set — blocking audio for {cooldown_ms}ms")
    else:
        # Explicit reset with short tail cooldown
        _tts_cooldown_until = _time_module.time() + 1.5
        logger.info("[ECHO] TTS active flag reset with 1.5s tail cooldown")

def is_tts_active():
    """Check if TTS is active or still in cooldown period"""
    return _time_module.time() < _tts_cooldown_until

# SocketIO will be injected
_socketio = None

def set_socketio(sio):
    """Set SocketIO instance and register handlers"""
    global _socketio
    _socketio = sio
    
    # Register all handlers
    sio.on_event('connect', handle_connect)
    sio.on_event('disconnect', handle_disconnect)
    sio.on_event('command', handle_command)
    sio.on_event('voice_command', handle_voice_command)
    sio.on_event('voice_audio_data', handle_voice_audio)
    
    print("… Command handlers registered with socketio")

# ==============================================
# WebSocket Event Handlers (as regular functions)
# ==============================================

# Fast in-memory cache for AI Settings
_ai_settings_cache = {}
_ai_settings_mtime = 0

def get_cached_ai_settings():
    """Retrieve AI settings from file only if modified, else from memory cache."""
    global _ai_settings_cache, _ai_settings_mtime
    try:
        import os, json
        settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'user_preferences', 'settings.json')
        if os.path.exists(settings_path):
            current_mtime = os.path.getmtime(settings_path)
            if current_mtime > _ai_settings_mtime:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    _ai_settings_cache = settings.get('ai', {})
                    _ai_settings_mtime = current_mtime
    except Exception as e:
        print(f"š  Cache read error for app_settings.json: {e}")
    return _ai_settings_cache

def handle_connect():
    """Handle client connection"""
    print(f'… Client connected: {request.sid}')
    emit('connection_established', {
        'status': 'connected',
        'sid': request.sid,
        'timestamp': datetime.now().isoformat()
    })

def handle_disconnect():
    """Handle client disconnection"""
    print(f'Œ Client disconnected: {request.sid}')

def handle_command(data):
    """
    Handle command with intelligent routing:
    1. Local Tools First (AdvancedConversationalAI) - for system commands  
    2. External AI Fallback (UnifiedChatInterface) - for general queries
    """
    try:
        command_text = data.get('command') or data.get('message', '')
        source = data.get('source', 'chat')
        
        if not command_text:
            emit('command_response', {
                'success': False,
                'error': 'No command provided',
                'timestamp': datetime.now().isoformat()
            })
            return
        
        print(f'💬 Command received ({source}): {command_text}')
        
        # Define safe emit helper to catch Errno 22
        def safe_emit(event, payload):
            try:
                if event == 'command_response' and payload.get('success') and payload.get('response'):
                    try:
                        import sys
                        assistant = None
                        if hasattr(sys.modules.get('__main__'), 'assistant'):
                            assistant = sys.modules['__main__'].assistant
                        
                        if assistant:
                            b64 = assistant.speak_text(payload['response'])
                            if b64:
                                payload['audio_base64'] = b64
                                set_tts_active(True)  # Echo prevention: mark TTS as active
                    except Exception as e:
                        logger.error(f"Failed to generate TTS: {e}")
                
                if _socketio:
                    _socketio.emit(event, payload)
                else:
                    emit(event, payload)
            except OSError as e:
                # Errno 22 often happens with socketio emit on windows if payload is too large or socket closed
                logger.warning(f"⚠️ Socket emit error (ignored): {e}")
            except Exception as e:
                logger.warning(f"⚠️ General emit error: {e}")
        
        # NOTE: ai_models_ready check removed - models load in ~3 seconds
        # and the cross-module check was broken. Commands proceed directly.

        # ============================================
        # PRIORITY 1: Local Command Processing
        # ============================================
        # Try AdvancedConversationalAI first (has built-in intent detection & tool execution)
        response_text = None
        used_local_tools = False
        
        if CONVERSATIONAL_AI_AVAILABLE:
            try:
                from ai_assistant.ai.conversational_ai import AdvancedConversationalAI
                
                # Create instance with automation callback
                def automation_callback(action, param):
                    """Execute automation actions"""
                    try:
                        if action == 'open_application':
                            from ai_assistant.core.core import open_application
                            return open_application(param)
                        elif action == 'close_application':
                            from ai_assistant.core.core import close_application
                            return close_application(param)
                        elif action == 'get_running_apps':
                            from ai_assistant.core.core import get_running_processes
                            return get_running_processes()
                    except Exception as e:
                        return f"Action error: {str(e)}"
                    return None
                
                conv_ai = AdvancedConversationalAI(automation_callback=automation_callback)
                
                # Process through conversational AI (has intent detection built-in)
                response_text = conv_ai.process_message(command_text)
                
                # Check if it actually executed something or just returned generic response
                if response_text and not any(phrase in response_text.lower() for phrase in [
                    "i don't understand", 
                    "i'm not sure",
                    "could you rephrase",
                    "what would you like"
                ]):
                    used_local_tools = True
                    print(f'… [LOCAL TOOLS] {response_text[:100]}...')
                    
                    # Emit response
                    safe_emit('command_response', {
                        'success': True,
                        'response': response_text,
                        'command': command_text,
                        'source': 'local_tools',
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # Log learning
                    try:
                        from modern_web_backend import _get_learning_router_lazy
                        lr = _get_learning_router_lazy()
                        if lr:
                            lr.route_conversation(speaker='user', content=command_text, input_mode=source)
                            lr.route_conversation(speaker='assistant', content=response_text, input_mode=source)
                    except Exception as e:
                        print(f"š  Could not log learning: {e}")
                    
                    return  # Successfully handled
                    
            except ImportError:
                print('š  AdvancedConversationalAI import failed')
            except Exception as e:
                print(f'š  Local processing attempt failed: {e}')
                import traceback
                traceback.print_exc()
        
        # ============================================
        # PRIORITY 2: External AI Fallback (for general queries)
        # ============================================
        if LLM_PROVIDER_AVAILABLE and not used_local_tools:
            try:
                from ai_assistant.ai.llm_provider import UnifiedChatInterface
                
                # Extract provider/model preference from request
                preferred_provider = data.get('provider')
                preferred_model = data.get('model')
                
                # If provider or model is not sent by frontend, check cached app_settings
                if not preferred_provider or not preferred_model:
                    ai_settings = get_cached_ai_settings()
                    if not preferred_provider:
                        preferred_provider = ai_settings.get('defaultProvider', 'openai')
                    if not preferred_model:
                        preferred_model = ai_settings.get('defaultModel', 'gpt-3.5-turbo')
                
                # Sanitize invalid provider-model combinations (e.g. if frontend forgets to update model)
                if preferred_provider:
                    prov_lower = preferred_provider.lower()
                    mod_lower = preferred_model.lower() if preferred_model else ""
                    if "gemini" in prov_lower and "gpt" in mod_lower:
                        preferred_model = "gemini-2.5-flash"
                    elif "openai" in prov_lower and "gemini" in mod_lower:
                        preferred_model = "gpt-4o-mini"
                
                
                print(f" Initializing Chat with Provider: {preferred_provider}, Model: {preferred_model}")

                # Initialize Chat with user preference
                chat = UnifiedChatInterface(
                    provider=preferred_provider,
                    model=preferred_model,
                    use_fallback=True
                )
                
                # Set provider-specific system message
                provider_name = chat.provider_name.lower()
                model_name = chat.model
                
                print(f"„¹ Actual Provider: {provider_name}, Actual Model: {model_name}")

                if 'openai' in provider_name or 'gpt' in model_name:
                    system_msg = (
                        "You are an AI assistant powered by OpenAI. "
                        f"You are using the {model_name} model. "
                        "You can answer general knowledge questions, help with information, "
                        "and provide assistance."
                    )
                elif 'gemini' in provider_name or 'gemini' in model_name:
                    system_msg = (
                        "You are Pulsar Assistant, powered by Google Gemini. "
                        f"You are using the {model_name} model. "
                        "You can answer general knowledge questions, help with information, "
                        "and provide assistance."
                    )
                else:
                    system_msg = (
                        "You are Pulsar, a helpful AI assistant. "
                        "You can answer general knowledge questions, help with information, "
                        "and provide assistance."
                    )
                
                chat.add_system_message(system_msg)
                
                # Get response from external AI
                response_text = chat.chat(command_text)
                
                print(f'… [EXTERNAL AI - {provider_name.upper()}] {response_text[:100]}...')
                
                # Log learning
                try:
                    from modern_web_backend import _get_learning_router_lazy
                    lr = _get_learning_router_lazy()
                    if lr:
                        lr.route_conversation(speaker='user', content=command_text, input_mode=source)
                        lr.route_conversation(speaker='assistant', content=response_text, input_mode=source)
                except Exception as e:
                    print(f"š  Could not log learning: {e}")
                
                # Emit response (safe_emit will catch any socket errors)
                safe_emit('command_response', {
                    'success': True,
                    'response': response_text,
                    'command': command_text,
                    'source': f'external_ai_{provider_name}',
                    'provider': provider_name,
                    'model': model_name,
                    'timestamp': datetime.now().isoformat()
                })
                
                return  # Successfully handled
                
            except Exception as llm_error:
                print(f'Œ External AI error: {llm_error}')
                # Don't return here, let it fall through to fallback if needed, or emit error silently
                # But typically if AI fails we want to know, just not crash socket
        
        # ============================================
        # FALLBACK: Simple acknowledgment
        # ============================================
        if not response_text:
            response_text = f'I received your command: "{command_text}". Processing...'
            
        safe_emit('command_response', {
            'success': True,
            'response': response_text,
            'command': command_text,
            'source': source,
            'timestamp': datetime.now().isoformat()
        })
            
    except OSError as e:
         print(f"š  Critical Socket/OS Error caught in handle_command: {e}")
         # DO NOT EMIT TO USER, just log it. This prevents the "Error: [Errno 22]" chat message
    except Exception as e:
        print(f'Œ Command handling error: {e}')
        import traceback
        print(traceback.format_exc())
        
        # Only emit operational errors, not low-level system errors
        if "[Errno 22]" not in str(e):
            safe_emit('command_response', {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

def handle_voice_command(data):
    """Handle voice command specifically"""
    try:
        # FIX: Frontend sends 'text', not 'transcript'. Support both for compatibility.
        transcript = data.get('text') or data.get('transcript', '')
        confidence = data.get('confidence', 0.0)
        provider = data.get('provider')
        model = data.get('model')
        language = data.get('language', 'en-US')
        offline_mode = data.get('offline_mode', False)
        
        if not transcript:
            emit('voice_response', {
                'success': False,
                'error': 'No transcript provided'
            })
            return
        
        print(f'Ž¤ Voice command: {transcript} (confidence: {confidence}, lang: {language})')
        
        # Forward to command handler with all context
        handle_command({
            'command': transcript,
            'source': 'voice',
            'provider': provider,
            'model': model,
            'offline_mode': offline_mode
        })
        
    except Exception as e:
        print(f' Œ Voice command error: {e}')
        emit('voice_response', {
            'success': False,
            'error': str(e)
        })

def handle_voice_audio(data):
    """Handle raw audio data from Faster-Whisper frontend (Note: now generates KittenTTS audio_base64)"""
    # Echo prevention: ignore audio while TTS is playing or in cooldown
    if is_tts_active():
        logger.info("[VOICE] Ignoring voice_audio_data — TTS active or in cooldown (echo prevention)")
        return

    audio_data = data.get('audio_data', '')
    if not audio_data:
        return

    logger.info(f"[VOICE] Received voice_audio_data! Length: {len(audio_data)}")
    
    def process_and_emit():
        try:
            import sys
            assistant = None
            if hasattr(sys.modules.get('__main__'), 'assistant'):
                assistant = sys.modules['__main__'].assistant
                
            if not assistant:
                logger.debug("DEBUG: No assistant found!")
                return
                
            # Emit transcript as soon as Whisper finishes (before LLM processing)
            def on_transcript(text):
                logger.info(f"[VOICE] Whisper finished transcribing: {text}")
                if _socketio:
                    _socketio.emit('voice_transcript', {
                        'text': text,
                        'confidence': 0.9
                    })

            # Run in a thread to prevent blocking the socketio loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(assistant.process_voice_audio, audio_data, on_transcript)
                result = future.result()
            
            if result.get('success') and result.get('transcript'):
                logger.info(f"[VOICE] Processed audio. Transcript: {result.get('transcript')}")
                logger.info(f"[VOICE] AI Response: {result.get('response', '<no response>')}")
                
                # Generate TTS for offline mode
                audio_base64 = None
                if result.get('response') and assistant:
                    audio_base64 = assistant.speak_text(result['response'])
                
                # Emit the response directly since process_voice_audio already generated it
                if result.get('response') and _socketio:
                    payload = {
                        'success': True,
                        'response': result['response'],
                        'provider': 'gguf',  # Fallback provider name if needed
                        'timestamp': __import__('datetime').datetime.now().isoformat()
                    }
                    if audio_base64:
                        payload['audio_base64'] = audio_base64
                        set_tts_active(True)  # Echo prevention: mark TTS as active

                    _socketio.emit('voice_response', payload)
            else:
                if _socketio:
                    _socketio.emit('voice_audio_response', result)
        except Exception as e:
            import traceback
            logger.error(f"Error in background voice processing: {e}")
            traceback.print_exc()
            if _socketio:
                _socketio.emit('voice_audio_response', {'success': False, 'error': str(e)})

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



