"""
Smart Wake Word Detection Engine
Implements low-latency, always-on wake word detection like Google Assistant
Uses PocketSphinx for local, instant detection without API calls
"""

import logging
import threading
import queue
import numpy as np
from pathlib import Path
from typing import Optional, Callable, List, Tuple
from enum import Enum
import time

try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    import json
    SetLogLevel(-1) # Hide verbose C++ logs that confuse the user
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class WakeWordDetectionMode(Enum):
    """Wake word detection modes"""
    ALWAYS_ON = "always_on"  # Continuous listening
    HOTWORD_ONLY = "hotword_only"  # Only detect wake word
    HYBRID = "hybrid"  # Listen then detect


class SmartWakeWordDetector:
    """
    Always-on wake word detection like Google Assistant
    Low latency, works completely offline using PocketSphinx
    """
    
    def __init__(
        self,
        wake_words: Optional[List[str]] = None,
        threshold: float = 0.5,
        mode: WakeWordDetectionMode = WakeWordDetectionMode.ALWAYS_ON,
        audio_device: Optional[int] = None,
        sample_rate: int = 16000,
        chunk_size: int = 512
    ):
        """
        Initialize wake word detector
        
        Args:
            wake_words: List of wake words (e.g., ["hey assistant", "ok assistant"])
            threshold: Detection confidence threshold (0.0-1.0)
            mode: Detection mode
            audio_device: Audio device index (None = default)
            sample_rate: Audio sample rate
            chunk_size: Audio chunk size
        """
        self.wake_words = wake_words or ["hey assistant", "ok assistant", "assistant"]
        self.threshold = threshold
        self.mode = mode
        self.audio_device = audio_device
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        
        # State
        self.is_listening = False
        self.is_processing = False
        self.detection_thread = None
        self.audio_queue = queue.Queue(maxsize=50)
        
        # Callbacks
        self.on_wake_word_detected = None
        self.on_speech_detected = None
        
        # Statistics
        self.detection_count = 0
        self.false_positive_count = 0
        self.average_latency = 0
        self.detection_history = []
        
        # Initialize decoder
        self.decoder = None
        self._initialize_decoder()
    
    def _initialize_decoder(self):
        """Initialize Vosk decoder for wake word detection"""
        if not VOSK_AVAILABLE:
            logger.warning("⚠️ Vosk not available. Install: pip install vosk")
            return
        
        try:
            model_path = str(Path(__file__).parent.parent / 'models' / 'vosk-model')
            if not Path(model_path).exists():
                logger.warning(f"⚠️ Vosk model not found at {model_path}")
                return
                
            # Create decoder
            self.model = Model(model_path)
            self.decoder = KaldiRecognizer(self.model, self.sample_rate)
            
            logger.info("✅ Vosk decoder initialized")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize decoder: {e}")
            logger.info("Wake word detection will use fallback methods")
    
    def start_listening(self):
        """Start continuous listening for wake words"""
        if self.is_listening:
            logger.warning("Already listening")
            return
        
        if not PYAUDIO_AVAILABLE:
            logger.error("❌ PyAudio not available. Install: pip install pyaudio")
            return
        
        self.is_listening = True
        self.detection_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.detection_thread.start()
        logger.info("🎤 Wake word detection started")
    
    def stop_listening(self):
        """Stop listening for wake words"""
        self.is_listening = False
        if self.detection_thread:
            self.detection_thread.join(timeout=2)
        logger.info("⏸️ Wake word detection stopped")
    
    def _listen_loop(self):
        """Main listening loop"""
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        try:
            import pyaudio
            
            p = pyaudio.PyAudio()
            
            # Open audio stream
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.audio_device,
                frames_per_buffer=self.chunk_size,
                stream_callback=None
            )
            
            stream.start_stream()
            logger.info("Audio stream started")
            
            while self.is_listening:
                try:
                    # Check if stream is still active
                    if not stream.is_active():
                        logger.warning("Audio stream became inactive, stopping listener")
                        break
                    
                    # Read audio chunk
                    audio_chunk = stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    # Reset error counter on successful read
                    consecutive_errors = 0
                    
                    # Put in queue for processing
                    if not self.audio_queue.full():
                        self.audio_queue.put(audio_chunk)
                    
                    # Process detection
                    self._process_audio_chunk(audio_chunk)
                    
                except IOError as e:
                    # Stream closed error
                    if e.errno == -9988:
                        logger.error("Audio stream closed unexpectedly. Stopping listener.")
                        break
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping listener")
                        break
                    elif consecutive_errors == 1:  # Only log first error
                        logger.warning(f"Audio read error: {e}")
                    time.sleep(0.1)
                    
                except Exception as e:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping listener")
                        break
                    elif consecutive_errors == 1:  # Only log first error
                        logger.warning(f"Audio read error: {e}")
                    time.sleep(0.1)
            
            # Cleanup
            try:
                stream.stop_stream()
                stream.close()
            except:
                pass
            p.terminate()
            
        except Exception as e:
            logger.error(f"❌ Listening loop failed: {e}")
        finally:
            self.is_listening = False
    
    def _process_audio_chunk(self, audio_chunk):
        """Process audio chunk for wake word detection"""
        if not audio_chunk or self.is_processing:
            return
        
        self.is_processing = True
        start_time = time.time()
        
        try:
            # Use decoder if available
            if self.decoder:
                if self.decoder.AcceptWaveform(audio_chunk):
                    res = json.loads(self.decoder.Result())
                    text = res.get("text", "").lower()
                else:
                    res = json.loads(self.decoder.PartialResult())
                    text = res.get("partial", "").lower()
                
                if text:
                    # Check for wake words
                    for wake_word in self.wake_words:
                        if wake_word.lower() in text:
                            self._on_detection(wake_word, 1.0)
                            # Reset recognizer state to prevent multiple triggers from same speech
                            self.decoder = KaldiRecognizer(self.model, self.sample_rate)
                            break
            else:
                # Fallback: simple energy-based detection
                audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
                energy = np.sum(audio_array ** 2) / len(audio_array)
                
                # If speech detected (high energy)
                if energy > 1e6:
                    if self.on_speech_detected:
                        self.on_speech_detected()
        
        finally:
            latency = (time.time() - start_time) * 1000
            self.average_latency = (self.average_latency * 0.9) + (latency * 0.1)
            self.is_processing = False
    
    def _on_detection(self, wake_word: str, confidence: float):
        """Handle wake word detection"""
        self.detection_count += 1
        detection_time = time.time()
        
        logger.info(f"🎯 Wake word detected: '{wake_word}' (confidence: {confidence:.2f})")
        
        # Store in history
        self.detection_history.append({
            'wake_word': wake_word,
            'confidence': confidence,
            'timestamp': detection_time
        })
        
        # Trigger callback
        if self.on_wake_word_detected:
            try:
                self.on_wake_word_detected(wake_word, confidence)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def add_custom_wake_word(self, wake_word: str):
        """Add custom wake word at runtime"""
        if wake_word.lower() not in [w.lower() for w in self.wake_words]:
            self.wake_words.append(wake_word)
            logger.info(f"Added custom wake word: {wake_word}")
    
    def remove_wake_word(self, wake_word: str):
        """Remove wake word"""
        self.wake_words = [w for w in self.wake_words if w.lower() != wake_word.lower()]
        logger.info(f"Removed wake word: {wake_word}")
    
    def get_detection_stats(self) -> dict:
        """Get detection statistics"""
        return {
            "detection_count": self.detection_count,
            "false_positives": self.false_positive_count,
            "average_latency_ms": self.average_latency,
            "recent_detections": self.detection_history[-10:],
            "active_wake_words": self.wake_words,
            "is_listening": self.is_listening
        }
    
    def simulate_wake_word(self, wake_word: str):
        """Simulate wake word for testing"""
        logger.info(f"🧪 Simulating wake word: {wake_word}")
        self._on_detection(wake_word, 0.95)


class WakeWordManager:
    """
    Manages wake word detection and integration with main assistant
    Handles custom wake words, profiles, and learning
    """
    
    def __init__(self, detection_mode: WakeWordDetectionMode = WakeWordDetectionMode.ALWAYS_ON):
        """Initialize wake word manager"""
        self.detector = SmartWakeWordDetector(mode=detection_mode)
        self.recognition_callback = None
        self.listening_mode = True
        self.stats_log = []
        
        # Set callbacks
        self.detector.on_wake_word_detected = self._on_wake_word
    
    def _on_wake_word(self, wake_word: str, confidence: float):
        """Handle wake word detection"""
        logger.info(f"🎙️ Ready to listen! (Wake word: {wake_word})")
        
        # Switch to recognition mode
        if self.recognition_callback:
            try:
                self.recognition_callback(wake_word, confidence)
            except Exception as e:
                logger.error(f"Recognition callback failed: {e}")
    
    def start(self):
        """Start wake word detection"""
        self.detector.start_listening()
    
    def stop(self):
        """Stop wake word detection"""
        self.detector.stop_listening()
    
    def get_stats(self) -> dict:
        """Get manager statistics"""
        return self.detector.get_detection_stats()
    
    def set_custom_wake_words(self, wake_words: List[str]):
        """Set custom wake words"""
        self.detector.wake_words = wake_words
        logger.info(f"Set wake words: {wake_words}")


# Global instance
_wake_word_manager = None


def get_wake_word_manager(
    detection_mode: WakeWordDetectionMode = WakeWordDetectionMode.ALWAYS_ON
) -> WakeWordManager:
    """Get or create wake word manager instance"""
    global _wake_word_manager
    if _wake_word_manager is None:
        _wake_word_manager = WakeWordManager(detection_mode=detection_mode)
    return _wake_word_manager


# Example usage
if __name__ == "__main__":
    manager = get_wake_word_manager()
    
    def on_wake_word(wake_word, confidence):
        print(f"🎤 Assistant is ready! Detected: {wake_word}")
    
    manager.detector.on_wake_word_detected = on_wake_word
    
    print("Starting wake word detection... (say 'hey assistant')")
    manager.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        manager.stop()
        print("Stopped")
