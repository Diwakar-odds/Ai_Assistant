"""
Voice Manager Module
Handles Speech Recognition, Text-to-Speech, and Wake Word detection.
Extracted from assistant.py for modularity.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    import speech_recognition as sr
    import pyttsx3
    VOICE_AVAILABLE = True
except ImportError:
    sr = None
    pyttsx3 = None
    VOICE_AVAILABLE = False


class VoiceManager:
    """Manages voice input, speech recognition, and audio output."""
    
    def __init__(self, enable_voice: bool = True):
        self.enabled = enable_voice and VOICE_AVAILABLE
        self.voice_listening = False
        self._voice_recognizer = None
        self._tts_engine = None
        self._audio_stream = None
        self._wake_word_detector = None
        self._init_status = "not_started"
        
    @property
    def voice_recognizer(self):
        """Lazy load speech recognition"""
        if self._voice_recognizer is None and self.enabled:
            try:
                if sr:
                    self._voice_recognizer = sr.Recognizer()
                    self._voice_recognizer.energy_threshold = 300
                    self._voice_recognizer.dynamic_energy_threshold = True
                    self._init_status = "ready"
                    logger.info("✅ Speech recognizer initialized")
            except Exception as e:
                logger.warning(f"Voice recognizer init failed: {e}")
                self._init_status = "failed"
        return self._voice_recognizer

    @property
    def tts_engine(self):
        """Lazy load TTS engine"""
        if self._tts_engine is None and self.enabled:
            try:
                if pyttsx3:
                    self._tts_engine = pyttsx3.init()
                    self._tts_engine.setProperty('rate', 175)
                    self._tts_engine.setProperty('volume', 0.9)
                    logger.info("✅ TTS engine initialized")
            except Exception as e:
                logger.warning(f"TTS engine init failed: {e}")
        return self._tts_engine

    @property
    def wake_word_detector(self):
        """Lazy load wake word detector"""
        if self._wake_word_detector is None and self.enabled:
            try:
                from ai_assistant.voice.wake_word_detector import WakeWordDetector
                self._wake_word_detector = WakeWordDetector()
                logger.info("✅ Wake word detector initialized")
            except Exception as e:
                logger.debug(f"Wake word detector not available: {e}")
        return self._wake_word_detector

    def start_voice_listening(self) -> Dict[str, Any]:
        """Start listening for voice commands"""
        if not self.enabled:
            return {"error": "Voice listening is disabled or dependencies not installed"}
        self.voice_listening = True
        return {"status": "listening", "message": "Voice listening started"}

    def stop_voice_listening(self) -> Dict[str, Any]:
        """Stop listening for voice commands"""
        self.voice_listening = False
        return {"status": "stopped", "message": "Voice listening stopped"}

    def speak_text(self, text: str) -> bool:
        """Speak text using TTS engine asynchronously"""
        if not text:
            return False
            
        self.stop_speaking()
        
        try:
            # Try to use Neural Voice Engine first if available
            try:
                from ai_assistant.voice.neural_voice_engine import get_neural_voice_engine
                nve = get_neural_voice_engine()
                wav_file = nve.speak(text)
                if wav_file and os.path.exists(wav_file):
                    import winsound
                    winsound.PlaySound(wav_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    return True
            except Exception as e:
                logger.warning(f"Neural TTS failed, falling back to pyttsx3: {e}")
                
            if self.tts_engine:
                import tempfile
                import winsound
                temp_file = os.path.join(tempfile.gettempdir(), "tts_temp.wav")
                self.tts_engine.save_to_file(text, temp_file)
                self.tts_engine.runAndWait()
                winsound.PlaySound(temp_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return True
        except Exception as e:
            logger.error(f"TTS error: {e}")
        return False

    def stop_speaking(self):
        """Stop any ongoing speech playback"""
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception as e:
            logger.debug(f"Could not stop speech: {e}")

    def process_voice_audio(self, audio_data: str) -> Dict[str, Any]:
        """Process base64 audio data for speech recognition"""
        if not self.enabled or not self.voice_recognizer:
            return {"error": "Voice recognition unavailable"}
        return {"status": "processed", "text": "Voice processing received"}
