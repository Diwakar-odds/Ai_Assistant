"""
Advanced Voice Features Module
Provides enhanced wake word detection, continuous listening, voice training, and speaker identification
"""

import threading
import time
import numpy as np
import speech_recognition as sr
from collections import deque, defaultdict
import pickle
import os
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
import logging

# Import utilities
try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class VoiceProfileManager:
    """Manages voice profiles and speaker identification"""
    
    def __init__(self, data_dir: str = "data/voice_profiles"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.profiles = {}
        self.current_speaker = None
        self.voice_features = defaultdict(list)
        
        self.load_profiles()
    
    def extract_voice_features(self, audio_data) -> List[float]:
        """Extract voice features from audio data"""
        try:
            # Basic spectral features (placeholder for more advanced feature extraction)
            if hasattr(audio_data, 'frame_data'):
                # Convert audio to numpy array for feature extraction
                audio_array = np.frombuffer(audio_data.frame_data, dtype=np.int16)
                
                # Extract basic features
                features = [
                    float(np.mean(audio_array)),      # Mean amplitude
                    float(np.std(audio_array)),       # Standard deviation
                    float(np.max(audio_array)),       # Maximum amplitude
                    float(np.min(audio_array)),       # Minimum amplitude
                    float(len(audio_array)),          # Length
                ]
                
                return features
            
            return [0.0, 0.0, 0.0, 0.0, 0.0]  # Default features
            
        except Exception as e:
            logger.warning(f"Feature extraction failed: {e}")
            return [0.0, 0.0, 0.0, 0.0, 0.0]
    
    def add_voice_sample(self, speaker_name: str, audio_data):
        """Add voice sample for speaker training"""
        features = self.extract_voice_features(audio_data)
        
        if speaker_name not in self.profiles:
            self.profiles[speaker_name] = {
                'created': datetime.now().isoformat(),
                'samples': [],
                'features': []
            }
        
        self.profiles[speaker_name]['samples'].append(len(self.profiles[speaker_name]['samples']))
        self.profiles[speaker_name]['features'].append(features)
        
        logger.info(f"Added voice sample for {speaker_name}")
        self.save_profiles()
    
    def identify_speaker(self, audio_data) -> Optional[str]:
        """Identify speaker from audio sample"""
        if not self.profiles:
            return None
        
        features = self.extract_voice_features(audio_data)
        
        best_match = None
        best_score = float('inf')
        
        for speaker_name, profile in self.profiles.items():
            if not profile['features']:
                continue
            
            # Calculate similarity to all samples
            scores = []
            for stored_features in profile['features']:
                # Simple Euclidean distance
                distance = np.sqrt(sum((a - b) ** 2 for a, b in zip(features, stored_features)))
                scores.append(distance)
            
            if scores:
                avg_score = sum(scores) / len(scores)
                if avg_score < best_score:
                    best_score = avg_score
                    best_match = speaker_name
        
        # Threshold for identification confidence
        if best_score < 1000:  # Adjustable threshold
            self.current_speaker = best_match
            return best_match
        
        return None
    
    def save_profiles(self):
        """Save voice profiles to disk"""
        try:
            profile_file = self.data_dir / "voice_profiles.pkl"
            with open(profile_file, 'wb') as f:
                pickle.dump(self.profiles, f)
        except Exception as e:
            logger.error(f"Failed to save voice profiles: {e}")
    
    def load_profiles(self):
        """Load voice profiles from disk"""
        try:
            profile_file = self.data_dir / "voice_profiles.pkl"
            if profile_file.exists():
                with open(profile_file, 'rb') as f:
                    self.profiles = pickle.load(f)
                logger.info(f"Loaded {len(self.profiles)} voice profiles")
        except Exception as e:
            logger.error(f"Failed to load voice profiles: {e}")

class AdvancedWakeWordDetector:
    """Enhanced wake word detection with fuzzy matching and learning"""
    
    def __init__(self, wake_words: List[str] = None):
        self.wake_words = wake_words or [
            "hey assistant", "your daddy", "daddy", "assistant",
            "help me", "listen", "computer", "ai assistant"
        ]
        
        # Fuzzy matching parameters
        self.similarity_threshold = 0.6
        self.confidence_threshold = 0.7
        
        # Learning parameters
        self.successful_detections = defaultdict(int)
        self.false_positives = defaultdict(int)
        
        # Load phonetic patterns
        self.phonetic_patterns = self._build_phonetic_patterns()
    
    def _build_phonetic_patterns(self) -> Dict[str, List[str]]:
        """Build phonetic patterns for wake words"""
        patterns = {}
        
        for word in self.wake_words:
            # Simple phonetic variations (could be enhanced with real phonetic algorithms)
            variations = [word.lower()]
            
            # Common mispronunciations
            variations.extend([
                word.replace('daddy', 'dady'),
                word.replace('assistant', 'asistant'),
                word.replace('hey', 'hay'),
                word.replace('computer', 'compyuter'),
            ])
            
            # Remove duplicates
            patterns[word] = list(set(variations))
        
        return patterns
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        text1, text2 = text1.lower().strip(), text2.lower().strip()
        
        if text1 == text2:
            return 1.0
        
        # Levenshtein distance based similarity
        def levenshtein_distance(s1, s2):
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            
            if len(s2) == 0:
                return len(s1)
            
            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            
            return previous_row[-1]
        
        max_len = max(len(text1), len(text2))
        if max_len == 0:
            return 1.0
        
        distance = levenshtein_distance(text1, text2)
        return 1.0 - (distance / max_len)
    
    def detect_wake_word(self, text: str) -> Tuple[bool, str, float]:
        """Detect wake word in text with confidence score"""
        text = text.lower().strip()
        
        best_match = None
        best_score = 0.0
        best_word = ""
        
        # Check each wake word and its variations
        for wake_word in self.wake_words:
            patterns = self.phonetic_patterns.get(wake_word, [wake_word])
            
            for pattern in patterns:
                # Check if pattern appears in text
                if pattern in text:
                    score = self.calculate_similarity(pattern, text)
                    if score > best_score:
                        best_score = score
                        best_word = wake_word
                        best_match = pattern
                
                # Check similarity for each word in text
                for word in text.split():
                    score = self.calculate_similarity(pattern, word)
                    if score > best_score:
                        best_score = score
                        best_word = wake_word
                        best_match = pattern
        
        # Determine if wake word was detected
        detected = best_score >= self.similarity_threshold
        
        if detected:
            self.successful_detections[best_word] += 1
            logger.debug(f"Wake word detected: '{best_word}' (score: {best_score:.3f})")
        
        return detected, best_word, best_score
    
    def report_false_positive(self, word: str):
        """Report a false positive to improve detection"""
        self.false_positives[word] += 1
        
        # Adjust threshold if too many false positives
        if self.false_positives[word] > 5:
            self.similarity_threshold = min(0.9, self.similarity_threshold + 0.05)
            logger.info(f"Increased similarity threshold to {self.similarity_threshold:.2f}")

class ContinuousListeningManager:
    """Manages continuous listening with smart activation/deactivation"""
    
    def __init__(self, voice_callback: Callable[[str], None] = None):
        self.voice_callback = voice_callback
        self.is_listening = False
        self.is_paused = False
        
        # Audio configuration
        self.recognizer = sr.Recognizer()
        self.microphone = None
        
        # Listening parameters
        self.energy_threshold = 4000
        self.pause_threshold = 0.8
        self.phrase_threshold = 0.3
        self.timeout = 1.0
        
        # Components
        self.wake_detector = AdvancedWakeWordDetector()
        self.voice_manager = VoiceProfileManager()
        
        # Thread management
        self.listen_thread = None
        self.stop_event = threading.Event()
        
        # Performance monitoring
        self.listen_start_time = None
        self.total_detections = 0
        self.successful_commands = 0
        
        self._initialize_audio()
    
    def _initialize_audio(self):
        """Initialize audio system"""
        try:
            self.microphone = sr.Microphone()
            
            # Adjust for ambient noise
            with self.microphone as source:
                logger.info("Calibrating microphone for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                self.energy_threshold = self.recognizer.energy_threshold
                logger.info(f"Energy threshold set to: {self.energy_threshold}")
                
        except Exception as e:
            logger.error(f"Failed to initialize audio: {e}")
            self.microphone = None
    
    def start_listening(self):
        """Start continuous listening"""
        if self.is_listening or not self.microphone:
            return False
        
        self.is_listening = True
        self.stop_event.clear()
        self.listen_start_time = time.time()
        
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        
        logger.info("🎤 Continuous listening started")
        return True
    
    def stop_listening(self):
        """Stop continuous listening"""
        if not self.is_listening:
            return
        
        self.is_listening = False
        self.stop_event.set()
        
        if self.listen_thread:
            self.listen_thread.join(timeout=2.0)
        
        logger.info("🔇 Continuous listening stopped")
    
    def pause_listening(self):
        """Pause listening temporarily"""
        self.is_paused = True
        logger.debug("Listening paused")
    
    def resume_listening(self):
        """Resume listening"""
        self.is_paused = False
        logger.debug("Listening resumed")
    
    def _listen_loop(self):
        """Main listening loop"""
        consecutive_errors = 0
        max_errors = 5
        
        while self.is_listening and not self.stop_event.is_set():
            try:
                if self.is_paused:
                    time.sleep(0.1)
                    continue
                
                # Listen for audio
                with self.microphone as source:
                    try:
                        # Listen for speech with timeout
                        audio = self.recognizer.listen(
                            source, 
                            timeout=self.timeout,
                            phrase_time_limit=10
                        )
                        
                        # Process audio in background
                        threading.Thread(
                            target=self._process_audio,
                            args=(audio,),
                            daemon=True
                        ).start()
                        
                        consecutive_errors = 0
                        
                    except sr.WaitTimeoutError:
                        # Normal timeout, continue listening
                        continue
                    
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Listening error: {e}")
                
                if consecutive_errors >= max_errors:
                    logger.error("Too many consecutive errors, stopping listening")
                    break
                
                time.sleep(1)  # Brief pause before retry
        
        logger.info("Listening loop ended")
    
    def _process_audio(self, audio):
        """Process captured audio"""
        try:
            # Try to recognize speech
            text = self._recognize_speech(audio)
            
            if not text:
                return
            
            self.total_detections += 1
            
            # Check for wake word
            detected, wake_word, confidence = self.wake_detector.detect_wake_word(text)
            
            if detected:
                logger.info(f"Wake word detected: '{wake_word}' (confidence: {confidence:.3f})")
                
                # Identify speaker if possible
                speaker = self.voice_manager.identify_speaker(audio)
                if speaker:
                    logger.info(f"Speaker identified: {speaker}")
                
                # Process command
                if self.voice_callback:
                    # Remove wake word from command text
                    command_text = self._extract_command(text, wake_word)
                    
                    if command_text:
                        self.successful_commands += 1
                        self.voice_callback(command_text)
                    else:
                        # Just wake word, wait for follow-up
                        self.voice_callback("I'm listening...")
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
    
    def _recognize_speech(self, audio) -> Optional[str]:
        """Recognize speech from audio"""
        try:
            # Try different recognition methods
            recognition_methods = [
                ("Google", lambda: self.recognizer.recognize_google(audio)),
                ("Sphinx", lambda: self.recognizer.recognize_sphinx(audio)),
            ]
            
            # Try Vosk if available
            try:
                import vosk
                recognition_methods.insert(0, ("Vosk", lambda: self._recognize_with_vosk(audio)))
            except ImportError:
                pass
            
            for method_name, recognize_func in recognition_methods:
                try:
                    result = recognize_func()
                    if result:
                        logger.debug(f"Recognized with {method_name}: '{result}'")
                        return result.lower()
                except Exception as e:
                    logger.debug(f"{method_name} recognition failed: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Speech recognition failed: {e}")
            return None
    
    def _recognize_with_vosk(self, audio) -> Optional[str]:
        """Recognize speech using Vosk (offline)"""
        try:
            import vosk
            import json
            
            # Load model if available
            model_path = Path("model/vosk-model-small-en-us-0.15")
            if not model_path.exists():
                return None
            
            model = vosk.Model(str(model_path))
            rec = vosk.KaldiRecognizer(model, 16000)
            
            # Convert audio data
            audio_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
            
            if rec.AcceptWaveform(audio_data):
                result = json.loads(rec.Result())
                return result.get('text', '')
            
            return None
            
        except Exception as e:
            logger.debug(f"Vosk recognition failed: {e}")
            return None
    
    def _extract_command(self, full_text: str, wake_word: str) -> str:
        """Extract command text after wake word"""
        full_text = full_text.lower()
        wake_word = wake_word.lower()
        
        # Find wake word position
        wake_index = full_text.find(wake_word)
        if wake_index == -1:
            return full_text
        
        # Extract text after wake word
        command_start = wake_index + len(wake_word)
        command_text = full_text[command_start:].strip()
        
        return command_text
    
    def get_statistics(self) -> Dict:
        """Get listening statistics"""
        uptime = time.time() - self.listen_start_time if self.listen_start_time else 0
        
        return {
            'uptime_seconds': uptime,
            'total_detections': self.total_detections,
            'successful_commands': self.successful_commands,
            'success_rate': self.successful_commands / max(1, self.total_detections),
            'voice_profiles': len(self.voice_manager.profiles),
            'current_speaker': self.voice_manager.current_speaker,
            'energy_threshold': self.energy_threshold,
        }

# Voice command registry
class VoiceCommandRegistry:
    """Registry for voice commands and their handlers"""
    
    def __init__(self):
        self.commands = {}
        self.aliases = {}
        self.context_handlers = []
        
        # Register default commands
        self._register_default_commands()
    
    def register_command(self, patterns: List[str], handler: Callable, description: str = ""):
        """Register a voice command"""
        for pattern in patterns:
            pattern = pattern.lower().strip()
            self.commands[pattern] = {
                'handler': handler,
                'description': description,
                'patterns': patterns
            }
            logger.debug(f"Registered command: '{pattern}'")
    
    def register_alias(self, alias: str, target_pattern: str):
        """Register an alias for an existing command"""
        self.aliases[alias.lower()] = target_pattern.lower()
    
    def register_context_handler(self, handler: Callable):
        """Register a context-aware handler"""
        self.context_handlers.append(handler)
    
    def find_command(self, text: str) -> Optional[Tuple[str, Dict]]:
        """Find matching command for text"""
        text = text.lower().strip()
        
        # Direct match
        if text in self.commands:
            return text, self.commands[text]
        
        # Alias match
        if text in self.aliases:
            target = self.aliases[text]
            if target in self.commands:
                return target, self.commands[target]
        
        # Fuzzy matching
        best_match = None
        best_score = 0.6  # Minimum similarity threshold
        
        for pattern in self.commands:
            # Check if pattern words are in text
            pattern_words = pattern.split()
            text_words = text.split()
            
            matches = sum(1 for word in pattern_words if word in text_words)
            score = matches / len(pattern_words)
            
            if score > best_score:
                best_score = score
                best_match = pattern
        
        if best_match:
            return best_match, self.commands[best_match]
        
        return None, None
    
    def _register_default_commands(self):
        """Register default voice commands"""
        # Basic commands
        self.register_command(
            ["what time is it", "current time", "tell me the time"],
            self._handle_time_command,
            "Get current time"
        )
        
        self.register_command(
            ["what date is it", "current date", "today's date"],
            self._handle_date_command,
            "Get current date"
        )
        
        self.register_command(
            ["stop listening", "pause listening", "be quiet"],
            self._handle_stop_listening,
            "Stop voice recognition"
        )
        
        self.register_command(
            ["help", "what can you do", "commands"],
            self._handle_help_command,
            "Show available commands"
        )
    
    def _handle_time_command(self, text: str) -> str:
        """Handle time request"""
        current_time = datetime.now().strftime("%I:%M %p")
        return f"The current time is {current_time}"
    
    def _handle_date_command(self, text: str) -> str:
        """Handle date request"""
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        return f"Today is {current_date}"
    
    def _handle_stop_listening(self, text: str) -> str:
        """Handle stop listening request"""
        return "STOP_LISTENING"  # Special command
    
    def _handle_help_command(self, text: str) -> str:
        """Handle help request"""
        commands = [f"• {cmd['description']}" for cmd in self.commands.values() if cmd['description']]
        return "I can help you with:\n" + "\n".join(commands[:10])

# Global instance for easy access
voice_command_registry = VoiceCommandRegistry()

def get_voice_features():
    """Get comprehensive voice feature set"""
    return {
        'wake_word_detector': AdvancedWakeWordDetector(),
        'voice_profile_manager': VoiceProfileManager(),
        'continuous_listening': ContinuousListeningManager(),
        'command_registry': voice_command_registry,
    }