"""
Voice Service Manager

Manages voice-related services including speech recognition, TTS, and wake word detection.
Extracted from ModernAssistant for better modularity.
"""

import logging

logger = logging.getLogger(__name__)

class VoiceServiceManager:
    """Manages voice services with lazy initialization"""
    
    def __init__(self):
        """Initialize voice service manager"""
        self._voice_recognizer = None
        self._tts_engine = None
        self._wake_word_detector = None
        self._initialized = {
            'recognizer': False,
            'tts': False,
            'wake_word': False
        }
        self.voice_listening = False
    
    @property
    def voice_recognizer(self):
        """Get voice recognizer (lazy loaded)"""
        if not self._initialized['recognizer']:
            try:
                from ai_assistant.modules.voice_recognition import VoiceRecognizer
                self._voice_recognizer = VoiceRecognizer()
                self._initialized['recognizer'] = True
                logger.info("Voice recognizer initialized")
            except Exception as e:
                logger.warning(f"Voice recognizer initialization failed: {e}")
        return self._voice_recognizer
    
    @property
    def tts_engine(self):
        """Get TTS engine (lazy loaded)"""
        if not self._initialized['tts']:
            try:
                from ai_assistant.modules.tts import TextToSpeech
                self._tts_engine = TextToSpeech()
                self._initialized['tts'] = True
                logger.info("TTS engine initialized")
            except Exception as e:
                logger.warning(f"TTS engine initialization failed: {e}")
        return self._tts_engine
    
    @property
    def wake_word_detector(self):
        """Get wake word detector (lazy loaded)"""
        if not self._initialized['wake_word']:
            try:
                from ai_assistant.modules.wake_word import WakeWordDetector
                self._wake_word_detector = WakeWordDetector()
                self._initialized['wake_word'] = True
                logger.info("Wake word  detector initialized")
            except Exception as e:
                logger.warning(f"Wake word detector initialization failed: {e}")
        return self._wake_word_detector
    
    def start_listening(self):
        """Start voice listening"""
        if self.voice_recognizer:
            self.voice_listening = True
            return {"success": True, "listening": True}
        return {"error": "Voice recognizer not available"}
    
    def stop_listening(self):
        """Stop voice listening"""
        self.voice_listening = False
        return {"success": True, "listening": False}
    
    def speak(self, text):
        """Speak text using TTS"""
        if self.tts_engine:
            return self.tts_engine.speak(text)
        return False
    
    def get_status(self):
        """Get initialization status of all voice services"""
        return {
            'recognizer': 'ready' if self._initialized['recognizer'] and self._voice_recognizer else 'not_started',
            'tts': 'ready' if self._initialized['tts'] and self._tts_engine else 'not_started',
            'wake_word': 'ready' if self._initialized['wake_word'] and self._wake_word_detector else 'not_started',
            'listening': self.voice_listening
        }
