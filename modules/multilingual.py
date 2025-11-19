# Language Support Module for YourDaddy Assistant
"""
Advanced multilingual support for Hindi, English, and Hinglish:
- Language detection and automatic switching
- Real-time translation between languages
- Voice recognition in multiple languages using Vosk (offline)
- Text-to-speech in Hindi and English
- Hinglish processing and understanding
- Cultural context awareness
- Smart language mixing (code-switching)
- Wake word detection
"""

import os
import json
import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum
from dataclasses import dataclass
import sqlite3
from datetime import datetime
from pathlib import Path
import threading
import queue

# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category='modules')

# Try to import translation libraries
try:
    from googletrans import Translator
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    import edge_tts
    import asyncio
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    print("⚠️ Edge-TTS not available. Install with: pip install edge-tts")

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import vosk
    import pyaudio
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    print("⚠️ Vosk not available. Install with: pip install vosk pyaudio")

class Language(Enum):
    """Supported languages."""
    ENGLISH = "en"
    HINDI = "hi"
    HINGLISH = "hinglish"
    AUTO_DETECT = "auto"

class TranslationEngine(Enum):
    """Available translation engines."""
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    LOCAL = "local"

@dataclass
class LanguageContext:
    """Context information for language processing."""
    detected_language: Language
    confidence: float
    is_mixed: bool  # True for Hinglish
    dominant_language: Optional[Language] = None
    hindi_percentage: float = 0.0
    english_percentage: float = 0.0

class MultilingualSupport:
    """Advanced multilingual support system."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize multilingual support."""
        self.config = config or self._default_config()
        self.translator = None
        self.speech_recognizer = None
        self.tts_engine = None
        self.edge_tts_available = False
        self.edge_voices = {}
        self.current_language = Language.AUTO_DETECT
        self.language_history = []
        
        # Initialize components
        self._setup_translation()
        self._setup_speech_recognition()
        self._setup_tts()
        self._setup_database()
        self._load_language_patterns()
        
        logger.info("✅ Multilingual support initialized")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for multilingual support."""
        return {
            "languages": {
                "primary": "hinglish",
                "fallback": "en",
                "supported": ["en", "hi", "hinglish"],
                "auto_detect": True
            },
            "translation": {
                "engine": "google",
                "api_key": "",
                "cache_translations": True,
                "max_cache_size": 1000
            },
            "speech": {
                "hindi_recognition": True,
                "english_recognition": True,
                "hinglish_processing": True,
                "confidence_threshold": 0.7
            },
            "tts": {
                "hindi_voice": True,
                "english_voice": True,
                "rate": 150,
                "volume": 0.8
            },
            "hinglish": {
                "enable_processing": True,
                "romanization": True,
                "script_mixing": True,
                "cultural_context": True
            }
        }
    
    def _setup_translation(self):
        """Setup translation services."""
        try:
            if GOOGLE_TRANSLATE_AVAILABLE:
                self.translator = Translator()
                logging.info("✅ Google Translate initialized")
            else:
                logging.warning("⚠️ Google Translate not available")
        except Exception as e:
            logging.error(f"❌ Translation setup failed: {e}")
    
    def _setup_speech_recognition(self):
        """Setup speech recognition for multiple languages."""
        try:
            if SPEECH_RECOGNITION_AVAILABLE:
                self.speech_recognizer = sr.Recognizer()
                self.speech_recognizer.energy_threshold = 4000
                self.speech_recognizer.pause_threshold = 0.8
                logging.info("✅ Multilingual speech recognition initialized")
            
            # Initialize Vosk for offline recognition
            if VOSK_AVAILABLE:
                self.vosk_models = {}
                self.vosk_recognizers = {}
                self._load_vosk_models()
            else:
                logging.warning("⚠️ Vosk not available for offline recognition")
                
        except Exception as e:
            logging.error(f"❌ Speech recognition setup failed: {e}")
    
    def _load_vosk_models(self):
        """Load Vosk models for offline speech recognition."""
        try:
            model_dir = Path("model")
            
            # Load English model
            english_model_path = model_dir / "vosk-model-small-en-us-0.15"
            if english_model_path.exists():
                try:
                    self.vosk_models['en'] = vosk.Model(str(english_model_path))
                    self.vosk_recognizers['en'] = vosk.KaldiRecognizer(
                        self.vosk_models['en'], 16000
                    )
                    logging.info("✅ Vosk English model loaded")
                except Exception as e:
                    logging.error(f"Failed to load English model: {e}")
            else:
                logging.warning(f"⚠️ English Vosk model not found at {english_model_path}")
            
            # Load Hindi model
            hindi_model_path = model_dir / "vosk-model-small-hi-0.22"
            if hindi_model_path.exists():
                try:
                    self.vosk_models['hi'] = vosk.Model(str(hindi_model_path))
                    self.vosk_recognizers['hi'] = vosk.KaldiRecognizer(
                        self.vosk_models['hi'], 16000
                    )
                    logging.info("✅ Vosk Hindi model loaded")
                except Exception as e:
                    logging.error(f"Failed to load Hindi model: {e}")
            else:
                logging.warning(f"⚠️ Hindi Vosk model not found at {hindi_model_path}")
            
            if not self.vosk_models:
                logging.error("❌ No Vosk models loaded")
                
        except Exception as e:
            logging.error(f"❌ Error loading Vosk models: {e}")
    
    def _setup_tts(self):
        """Setup text-to-speech for multiple languages."""
        # Try to initialize Edge-TTS first (highest quality, no compilation needed)
        if EDGE_TTS_AVAILABLE:
            try:
                logging.info("🎯 Initializing Edge-TTS (Microsoft Neural Voices)...")
                
                # Set up voice mapping for different languages
                self.edge_voices = {
                    'en': 'en-US-AriaNeural',      # Natural female US English
                    'hi': 'hi-IN-SwaraNeural',      # Natural female Hindi
                    'en-gb': 'en-GB-SoniaNeural',   # British English
                    'en-au': 'en-AU-NatashaNeural'  # Australian English
                }
                
                self.edge_tts_available = True
                logging.info("✅ Edge-TTS initialized (400+ neural voices available)")
                    
            except Exception as e:
                logging.error(f"❌ Edge-TTS initialization failed: {e}")
                self.edge_tts_available = False
        
        # Fallback to pyttsx3
        try:
            if TTS_AVAILABLE:
                self.tts_engine = pyttsx3.init()
                voices = self.tts_engine.getProperty('voices')
                
                # Find Hindi and English voices
                self.hindi_voice = None
                self.english_voice = None
                
                for voice in voices:
                    if 'hindi' in voice.name.lower() or 'hi' in voice.id.lower():
                        self.hindi_voice = voice.id
                    elif 'english' in voice.name.lower() or 'en' in voice.id.lower():
                        self.english_voice = voice.id
                
                logging.info("✅ pyttsx3 TTS initialized as fallback")
        except Exception as e:
            logging.error(f"❌ TTS setup failed: {e}")
    
    def _setup_database(self):
        """Setup language database for caching and learning."""
        try:
            conn = sqlite3.connect('language_data.db')
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS language_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_text TEXT NOT NULL,
                    detected_language TEXT,
                    translated_text TEXT,
                    target_language TEXT,
                    confidence REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(original_text, target_language)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hinglish_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT NOT NULL,
                    language_mix TEXT,
                    frequency INTEGER DEFAULT 1,
                    last_used DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_language_preferences (
                    user_id TEXT PRIMARY KEY,
                    preferred_language TEXT,
                    tts_language TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logging.info("✅ Language database initialized")
        except Exception as e:
            logging.error(f"❌ Database setup failed: {e}")
    
    def _load_language_patterns(self):
        """Load language patterns for detection."""
        # Hindi words commonly used in Hinglish
        self.hindi_patterns = [
            r'\b(acha|theek|hai|nahi|kya|kaise|kyun|kahan|kab|kaun|kitna)\b',
            r'\b(haan|nahin|achha|bhai|yaar|boss|sir|madam)\b',
            r'\b(paisa|paise|rupees|lakh|crore|hazaar)\b',
            r'\b(ghar|office|market|station|hospital|school)\b',
            r'\b(khana|paani|chai|coffee|juice|milk)\b',
            r'\b(time|samay|din|raat|subah|sham)\b',
            r'\b(kaam|work|job|business|meeting|call)\b'
        ]
        
        # English words commonly mixed in Hindi
        self.english_patterns = [
            r'\b(ok|okay|yes|no|please|sorry|thanks|welcome)\b',
            r'\b(phone|mobile|computer|laptop|internet|wifi)\b',
            r'\b(car|bike|bus|train|flight|taxi|auto)\b',
            r'\b(facebook|whatsapp|instagram|youtube|google)\b',
            r'\b(shopping|mall|restaurant|hotel|bank|atm)\b'
        ]
        
        # Hinglish mixing patterns
        self.hinglish_patterns = [
            r'\b(kar|kar diya|kar do|kar raha|kar rahe)\b.*\b(work|job|call|meeting)\b',
            r'\b(phone|call|message)\b.*\b(kar|karo|kiya|kiye)\b',
            r'\b(theek hai|achha hai|nahi hai)\b.*\b(ok|fine|good|bad)\b'
        ]
    
    def detect_language(self, text: str) -> LanguageContext:
        """Detect language of input text with confidence score."""
        try:
            text_lower = text.lower()
            
            # Count Hindi patterns
            hindi_matches = 0
            for pattern in self.hindi_patterns:
                hindi_matches += len(re.findall(pattern, text_lower))
            
            # Count English patterns
            english_matches = 0
            for pattern in self.english_patterns:
                english_matches += len(re.findall(pattern, text_lower))
            
            # Count Hinglish patterns
            hinglish_matches = 0
            for pattern in self.hinglish_patterns:
                hinglish_matches += len(re.findall(pattern, text_lower))
            
            # Calculate percentages
            total_words = len(text.split())
            hindi_percentage = (hindi_matches / total_words * 100) if total_words > 0 else 0
            english_percentage = (english_matches / total_words * 100) if total_words > 0 else 0
            hinglish_score = hinglish_matches / total_words if total_words > 0 else 0
            
            # Determine language
            if hinglish_score > 0.1 or (hindi_percentage > 20 and english_percentage > 20):
                detected_lang = Language.HINGLISH
                confidence = min(0.9, hinglish_score + 0.5)
                is_mixed = True
            elif hindi_percentage > english_percentage and hindi_percentage > 30:
                detected_lang = Language.HINDI
                confidence = min(0.95, hindi_percentage / 100 + 0.3)
                is_mixed = False
            elif english_percentage > 50:
                detected_lang = Language.ENGLISH
                confidence = min(0.95, english_percentage / 100 + 0.3)
                is_mixed = False
            else:
                # Default to English for ambiguous cases
                detected_lang = Language.ENGLISH
                confidence = 0.5
                is_mixed = False
            
            return LanguageContext(
                detected_language=detected_lang,
                confidence=confidence,
                is_mixed=is_mixed,
                hindi_percentage=hindi_percentage,
                english_percentage=english_percentage
            )
            
        except Exception as e:
            logging.error(f"Language detection error: {e}")
            return LanguageContext(
                detected_language=Language.ENGLISH,
                confidence=0.3,
                is_mixed=False
            )
    
    def translate_text(self, text: str, target_language: Language, 
                      source_language: Optional[Language] = None) -> str:
        """Translate text between languages."""
        try:
            if not self.translator:
                return f"❌ Translation service not available"
            
            # Check cache first
            cached_translation = self._get_cached_translation(text, target_language)
            if cached_translation:
                return cached_translation
            
            # Auto-detect source language if not provided
            if source_language is None:
                context = self.detect_language(text)
                source_language = context.detected_language
            
            # Handle special cases
            if source_language == target_language:
                return text
            
            # Handle Hinglish translations
            if source_language == Language.HINGLISH:
                return self._translate_hinglish(text, target_language)
            
            # Standard translation
            source_code = source_language.value
            target_code = target_language.value
            
            if target_code == "hinglish":
                target_code = "hi"  # Translate to Hindi for Hinglish base
            
            result = self.translator.translate(text, src=source_code, dest=target_code)
            translated_text = result.text
            
            # Post-process for Hinglish output
            if target_language == Language.HINGLISH:
                translated_text = self._create_hinglish_output(translated_text, text)
            
            # Cache the translation
            self._cache_translation(text, source_language, translated_text, target_language, result.confidence)
            
            return translated_text
            
        except Exception as e:
            logging.error(f"Translation error: {e}")
            return f"❌ Translation failed: {str(e)}"
    
    def _translate_hinglish(self, text: str, target_language: Language) -> str:
        """Handle Hinglish to other language translation."""
        try:
            # Split into Hindi and English parts
            words = text.split()
            translated_parts = []
            
            for word in words:
                # Check if word is Hindi
                is_hindi = any(re.search(pattern, word.lower()) for pattern in self.hindi_patterns)
                
                if is_hindi and target_language == Language.ENGLISH:
                    # Translate Hindi word to English
                    result = self.translator.translate(word, src='hi', dest='en')
                    translated_parts.append(result.text)
                elif not is_hindi and target_language == Language.HINDI:
                    # Translate English word to Hindi
                    result = self.translator.translate(word, src='en', dest='hi')
                    translated_parts.append(result.text)
                else:
                    # Keep the word as is
                    translated_parts.append(word)
            
            return ' '.join(translated_parts)
            
        except Exception as e:
            logging.error(f"Hinglish translation error: {e}")
            return text
    
    def _create_hinglish_output(self, hindi_text: str, original_text: str) -> str:
        """Create natural Hinglish by mixing Hindi and English."""
        try:
            # Keep common English words in their original form
            common_english_words = [
                'phone', 'mobile', 'computer', 'internet', 'ok', 'please',
                'sorry', 'thanks', 'time', 'office', 'work', 'meeting'
            ]
            
            words = hindi_text.split()
            original_words = original_text.lower().split()
            
            result_words = []
            
            for i, word in enumerate(words):
                # Check if original word should remain in English
                if i < len(original_words) and original_words[i] in common_english_words:
                    result_words.append(original_words[i])
                else:
                    result_words.append(word)
            
            return ' '.join(result_words)
            
        except Exception as e:
            logging.error(f"Hinglish creation error: {e}")
            return hindi_text
    
    def _get_cached_translation(self, text: str, target_language: Language) -> Optional[str]:
        """Get cached translation if available."""
        try:
            conn = sqlite3.connect('language_data.db')
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT translated_text FROM language_cache WHERE original_text = ? AND target_language = ?",
                (text, target_language.value)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else None
            
        except Exception as e:
            logging.error(f"Cache lookup error: {e}")
            return None
    
    def _cache_translation(self, original: str, source_lang: Language, 
                          translated: str, target_lang: Language, confidence: float):
        """Cache translation for future use."""
        try:
            conn = sqlite3.connect('language_data.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO language_cache 
                (original_text, detected_language, translated_text, target_language, confidence)
                VALUES (?, ?, ?, ?, ?)
            ''', (original, source_lang.value, translated, target_lang.value, confidence))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Cache storage error: {e}")
    
    def recognize_speech_multilingual(self, audio_source, language: Language = Language.AUTO_DETECT) -> Tuple[str, Language]:
        """Recognize speech in multiple languages."""
        try:
            if not self.speech_recognizer:
                return "❌ Speech recognition not available", Language.ENGLISH
            
            # Listen for audio
            with audio_source as source:
                self.speech_recognizer.adjust_for_ambient_noise(source)
                audio = self.speech_recognizer.listen(source, timeout=5)
            
            # Try different languages based on setting
            if language == Language.AUTO_DETECT:
                languages_to_try = ['hi-IN', 'en-IN', 'en-US']
            elif language == Language.HINDI:
                languages_to_try = ['hi-IN']
            elif language == Language.ENGLISH:
                languages_to_try = ['en-IN', 'en-US']
            else:  # Hinglish
                languages_to_try = ['hi-IN', 'en-IN']
            
            best_result = ""
            best_language = Language.ENGLISH
            best_confidence = 0.0
            
            for lang_code in languages_to_try:
                try:
                    result = self.speech_recognizer.recognize_google(audio, language=lang_code)
                    if result:
                        # Detect actual language of result
                        context = self.detect_language(result)
                        if context.confidence > best_confidence:
                            best_result = result
                            best_language = context.detected_language
                            best_confidence = context.confidence
                            
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    logging.error(f"Speech recognition request error: {e}")
                    continue
            
            if best_result:
                return best_result, best_language
            else:
                return "❌ Could not understand audio", Language.ENGLISH
                
        except Exception as e:
            logging.error(f"Multilingual speech recognition error: {e}")
            return f"❌ Speech recognition failed: {str(e)}", Language.ENGLISH
    
    def speak_multilingual(self, text: str, language: Language = Language.AUTO_DETECT) -> str:
        """Speak text in the appropriate language using Edge-TTS, gTTS, or pyttsx3 fallback."""
        try:
            # Detect language if auto-detect is enabled
            if language == Language.AUTO_DETECT:
                context = self.detect_language(text)
                language = context.detected_language
            
            # Try Edge-TTS first (highest quality)
            if self.edge_tts_available:
                try:
                    # Determine which voice to use
                    voice = None
                    if language == Language.HINDI:
                        voice = self.edge_voices.get('hi')
                    elif language == Language.ENGLISH:
                        voice = self.edge_voices.get('en')
                    elif language == Language.HINGLISH:
                        # For Hinglish, use Hindi voice
                        voice = self.edge_voices.get('hi', self.edge_voices.get('en'))
                    else:
                        voice = self.edge_voices.get('en')
                    
                    if voice:
                        # Generate speech asynchronously
                        output_path = "temp_edge_tts_output.mp3"
                        
                        async def generate_speech():
                            communicate = edge_tts.Communicate(text, voice)
                            await communicate.save(output_path)
                        
                        # Run async function
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        loop.run_until_complete(generate_speech())
                        
                        # Play the audio file
                        try:
                            import pygame
                            pygame.mixer.init()
                            pygame.mixer.music.load(output_path)
                            pygame.mixer.music.play()
                            while pygame.mixer.music.get_busy():
                                pygame.time.Clock().tick(10)
                        except ImportError:
                            # Fallback to platform-specific player
                            try:
                                if os.name == 'nt':  # Windows
                                    os.system(f'start /min "" "{output_path}"')
                                else:
                                    os.system(f'play "{output_path}" 2>/dev/null &')
                            except:
                                logging.warning("⚠️ No audio player available, file saved")
                        
                        # Clean up temporary file
                        try:
                            import time
                            time.sleep(0.5)  # Wait for playback to start
                            os.remove(output_path)
                        except:
                            pass
                        
                        return f"✅ Spoken in {language.value} (Edge-TTS Neural)"
                except Exception as edge_error:
                    logging.warning(f"⚠️ Edge-TTS failed, trying gTTS: {edge_error}")
            
            # Try gTTS (Google TTS) as second option
            if GTTS_AVAILABLE:
                try:
                    lang_code = 'hi' if language == Language.HINDI else 'en'
                    tts = gTTS(text=text, lang=lang_code, slow=False)
                    output_path = "temp_gtts_output.mp3"
                    tts.save(output_path)
                    
                    # Play the audio
                    try:
                        import pygame
                        pygame.mixer.init()
                        pygame.mixer.music.load(output_path)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            pygame.time.Clock().tick(10)
                    except:
                        if os.name == 'nt':
                            os.system(f'start /min "" "{output_path}"')
                    
                    # Cleanup
                    try:
                        import time
                        time.sleep(0.5)
                        os.remove(output_path)
                    except:
                        pass
                    
                    return f"✅ Spoken in {language.value} (Google TTS)"
                except Exception as gtts_error:
                    logging.warning(f"⚠️ gTTS failed, falling back to pyttsx3: {gtts_error}")
            
            # Final fallback to pyttsx3
            if not self.tts_engine:
                return "❌ Text-to-speech not available"
            
            # Set appropriate voice
            if language == Language.HINDI and self.hindi_voice:
                self.tts_engine.setProperty('voice', self.hindi_voice)
            elif language == Language.ENGLISH and self.english_voice:
                self.tts_engine.setProperty('voice', self.english_voice)
            elif language == Language.HINGLISH:
                # For Hinglish, prefer Hindi voice if available, otherwise English
                if self.hindi_voice:
                    self.tts_engine.setProperty('voice', self.hindi_voice)
                elif self.english_voice:
                    self.tts_engine.setProperty('voice', self.english_voice)
            
            # Set speech rate and volume
            self.tts_engine.setProperty('rate', self.config['tts']['rate'])
            self.tts_engine.setProperty('volume', self.config['tts']['volume'])
            
            # Speak the text
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
            
            return f"✅ Spoken in {language.value} (pyttsx3)"
            
        except Exception as e:
            logging.error(f"Multilingual TTS error: {e}")
            return f"❌ Speech synthesis failed: {str(e)}"
    
    def process_hinglish_command(self, text: str) -> Dict[str, Any]:
        """Process Hinglish commands with cultural context."""
        try:
            # Detect language context
            context = self.detect_language(text)
            
            # Common Hinglish command patterns
            hinglish_commands = {
                r'(phone|call)\s+(kar|karo|kiya)': 'make_call',
                r'(message|msg)\s+(send|kar|bhej)': 'send_message',
                r'(music|song|gaana)\s+(play|chala|baja)': 'play_music',
                r'(time|samay|waqt)\s+(kya|kitna|tell)': 'tell_time',
                r'(weather|mausam)\s+(kya|kaisa|how)': 'check_weather',
                r'(google|search)\s+(kar|karo|me)': 'web_search',
                r'(volume|awaaz)\s+(up|down|kam|zyada)': 'adjust_volume',
                r'(light|batti)\s+(on|off|band|chalu)': 'control_light'
            }
            
            detected_command = None
            for pattern, command in hinglish_commands.items():
                if re.search(pattern, text.lower()):
                    detected_command = command
                    break
            
            # Extract parameters from the text
            parameters = self._extract_hinglish_parameters(text, detected_command)
            
            return {
                'command': detected_command,
                'parameters': parameters,
                'language_context': context,
                'original_text': text,
                'confidence': context.confidence
            }
            
        except Exception as e:
            logging.error(f"Hinglish command processing error: {e}")
            return {
                'command': None,
                'parameters': {},
                'error': str(e)
            }
    
    def _extract_hinglish_parameters(self, text: str, command: str) -> Dict[str, Any]:
        """Extract parameters from Hinglish text."""
        parameters = {}
        text_lower = text.lower()
        
        try:
            if command == 'make_call':
                # Extract phone numbers or contact names
                phone_pattern = r'\b\d{10}\b|\b\d{3}-\d{3}-\d{4}\b'
                phone_match = re.search(phone_pattern, text)
                if phone_match:
                    parameters['phone'] = phone_match.group()
                
                # Extract contact names (could be in Hindi or English)
                name_patterns = [
                    r'(ko|se)\s+(\w+)',  # Hindi patterns
                    r'call\s+(\w+)',     # English patterns
                ]
                for pattern in name_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        parameters['contact'] = match.group(2)
                        break
            
            elif command == 'play_music':
                # Extract song/artist names
                music_patterns = [
                    r'(gaana|song)\s+(.+?)\s+(play|baja|chala)',
                    r'play\s+(.+?)\s+(song|gaana)',
                    r'(baja|chala)\s+(.+)'
                ]
                for pattern in music_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        parameters['song'] = match.group(2) if len(match.groups()) > 1 else match.group(1)
                        break
            
            elif command == 'web_search':
                # Extract search query
                search_patterns = [
                    r'search\s+(.+)',
                    r'google\s+(me|kar|karo)\s+(.+)',
                    r'(.+)\s+(search|kar|google)\s+(kar|karo)'
                ]
                for pattern in search_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        # Take the longest group as the query
                        groups = [g for g in match.groups() if g and g not in ['me', 'kar', 'karo', 'search', 'google']]
                        if groups:
                            parameters['query'] = max(groups, key=len)
                        break
            
            elif command == 'adjust_volume':
                # Extract volume level or direction
                if any(word in text_lower for word in ['up', 'zyada', 'badha', 'increase']):
                    parameters['direction'] = 'up'
                elif any(word in text_lower for word in ['down', 'kam', 'kum', 'decrease']):
                    parameters['direction'] = 'down'
                
                # Extract specific volume levels
                volume_match = re.search(r'(\d+)(?:%|\s*percent)', text_lower)
                if volume_match:
                    parameters['level'] = int(volume_match.group(1))
            
        except Exception as e:
            logging.error(f"Parameter extraction error: {e}")
        
        return parameters
    
    def set_language_preference(self, user_id: str, language: Language, tts_language: Language = None):
        """Set user language preference."""
        try:
            conn = sqlite3.connect('language_data.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_language_preferences 
                (user_id, preferred_language, tts_language)
                VALUES (?, ?, ?)
            ''', (user_id, language.value, (tts_language or language).value))
            
            conn.commit()
            conn.close()
            
            self.current_language = language
            logging.info(f"Language preference set to {language.value} for user {user_id}")
            
        except Exception as e:
            logging.error(f"Error setting language preference: {e}")
    
    def get_language_preference(self, user_id: str) -> Tuple[Language, Language]:
        """Get user language preference."""
        try:
            conn = sqlite3.connect('language_data.db')
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT preferred_language, tts_language FROM user_language_preferences WHERE user_id = ?",
                (user_id,)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return Language(result[0]), Language(result[1])
            else:
                return Language.HINGLISH, Language.HINGLISH
                
        except Exception as e:
            logging.error(f"Error getting language preference: {e}")
            return Language.HINGLISH, Language.HINGLISH
    
    def get_language_stats(self) -> Dict[str, Any]:
        """Get language usage statistics."""
        try:
            stats = {
                'total_translations': 0,
                'language_breakdown': {},
                'most_translated_phrases': [],
                'hinglish_usage': 0
            }
            
            conn = sqlite3.connect('language_data.db')
            cursor = conn.cursor()
            
            # Total translations
            cursor.execute("SELECT COUNT(*) FROM language_cache")
            stats['total_translations'] = cursor.fetchone()[0]
            
            # Language breakdown
            cursor.execute("""
                SELECT detected_language, COUNT(*) as count 
                FROM language_cache 
                GROUP BY detected_language
            """)
            for lang, count in cursor.fetchall():
                stats['language_breakdown'][lang] = count
            
            # Most translated phrases
            cursor.execute("""
                SELECT original_text, COUNT(*) as frequency 
                FROM language_cache 
                GROUP BY original_text 
                ORDER BY frequency DESC 
                LIMIT 10
            """)
            stats['most_translated_phrases'] = cursor.fetchall()
            
            # Hinglish usage
            cursor.execute("""
                SELECT COUNT(*) FROM language_cache 
                WHERE detected_language = 'hinglish'
            """)
            stats['hinglish_usage'] = cursor.fetchone()[0]
            
            conn.close()
            return stats
            
        except Exception as e:
            logging.error(f"Error getting language stats: {e}")
            return {}

            return {}

def voice_listen_loop(callback_function=None, wake_words=['hey assistant', 'ok assistant', 'daddy'], 
                      use_vosk=True, language='auto', stop_event=None):
    """
    Main voice listening loop with wake word detection and multilingual support.
    
    :param callback_function: Function to call with recognized text
    :param wake_words: List of wake words to listen for
    :param use_vosk: Use Vosk for offline recognition (recommended)
    :param language: Language code ('en', 'hi', 'auto')
    :param stop_event: Threading event to stop the loop
    :return: None
    """
    ml = MultilingualSupport()
    
    if use_vosk and VOSK_AVAILABLE and ml.vosk_models:
        logging.info("🎙️ Starting voice loop with Vosk (offline)")
        return _voice_listen_loop_vosk(ml, callback_function, wake_words, language, stop_event)
    elif SPEECH_RECOGNITION_AVAILABLE:
        logging.info("🎙️ Starting voice loop with Google Speech Recognition (online)")
        return _voice_listen_loop_google(ml, callback_function, wake_words, language, stop_event)
    else:
        logging.error("❌ No speech recognition available")
        return "❌ Speech recognition not available"


def _voice_listen_loop_vosk(ml_support, callback, wake_words, language, stop_event):
    """Voice loop using Vosk for offline recognition."""
    try:
        # Determine which model to use
        if language == 'hi':
            model_key = 'hi'
        elif language == 'en':
            model_key = 'en'
        else:  # auto
            model_key = 'en'  # Default to English, will try Hindi if needed
        
        if model_key not in ml_support.vosk_recognizers:
            return f"❌ Vosk model for {model_key} not available"
        
        # Initialize PyAudio
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                       channels=1,
                       rate=16000,
                       input=True,
                       frames_per_buffer=8000)
        stream.start_stream()
        
        logging.info("✅ Voice listening started (Vosk). Say one of the wake words to activate.")
        print("🎙️ Listening... Say wake word:", wake_words)
        
        wake_word_detected = False
        current_recognizer = ml_support.vosk_recognizers[model_key]
        
        while True:
            if stop_event and stop_event.is_set():
                break
                
            try:
                data = stream.read(4000, exception_on_overflow=False)
                
                if current_recognizer.AcceptWaveform(data):
                    result = json.loads(current_recognizer.Result())
                    text = result.get('text', '').strip()
                    
                    if text:
                        logging.info(f"Recognized: {text}")
                        
                        # Check for wake word
                        if not wake_word_detected:
                            for wake_word in wake_words:
                                if wake_word.lower() in text.lower():
                                    wake_word_detected = True
                                    print(f"✅ Wake word detected: {wake_word}")
                                    logging.info(f"Wake word detected: {wake_word}")
                                    if callback:
                                        callback(f"[WAKE_WORD_DETECTED: {wake_word}]")
                                    break
                        else:
                            # Process command
                            print(f"🎯 Command: {text}")
                            
                            # Detect language
                            context = ml_support.detect_language(text)
                            
                            # If auto mode and text looks Hindi, try Hindi model
                            if language == 'auto' and context.detected_language == Language.HINDI and 'hi' in ml_support.vosk_recognizers:
                                current_recognizer = ml_support.vosk_recognizers['hi']
                            
                            # Call callback with recognized text
                            if callback:
                                callback(text)
                            
                            # Reset wake word detection after processing
                            wake_word_detected = False
                            print("🎙️ Listening for wake word...")
                else:
                    # Partial result
                    partial = json.loads(current_recognizer.PartialResult())
                    partial_text = partial.get('partial', '')
                    if partial_text and wake_word_detected:
                        print(f"... {partial_text}", end='\r')
                        
            except Exception as e:
                logging.error(f"Error in voice loop: {e}")
                continue
                
    except KeyboardInterrupt:
        logging.info("🛑 Voice loop stopped by user")
    except Exception as e:
        logging.error(f"❌ Voice loop error: {e}")
        return f"❌ Error: {e}"
    finally:
        if 'stream' in locals():
            stream.stop_stream()
            stream.close()
        if 'p' in locals():
            p.terminate()
        logging.info("Voice loop ended")


def _voice_listen_loop_google(ml_support, callback, wake_words, language, stop_event):
    """Voice loop using Google Speech Recognition (online, fallback)."""
    try:
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        
        # Adjust for ambient noise
        with mic as source:
            logging.info("📊 Adjusting for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
        
        logging.info("✅ Voice listening started (Google). Say one of the wake words to activate.")
        print("🎙️ Listening... Say wake word:", wake_words)
        
        wake_word_detected = False
        
        while True:
            if stop_event and stop_event.is_set():
                break
            
            try:
                with mic as source:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                
                # Determine language code for Google
                if language == 'hi':
                    lang_code = 'hi-IN'
                elif language == 'en':
                    lang_code = 'en-US'
                else:  # auto - try both
                    lang_code = 'en-IN'  # English with Indian accent
                
                text = recognizer.recognize_google(audio, language=lang_code)
                
                if text:
                    logging.info(f"Recognized: {text}")
                    
                    # Check for wake word
                    if not wake_word_detected:
                        for wake_word in wake_words:
                            if wake_word.lower() in text.lower():
                                wake_word_detected = True
                                print(f"✅ Wake word detected: {wake_word}")
                                logging.info(f"Wake word detected: {wake_word}")
                                if callback:
                                    callback(f"[WAKE_WORD_DETECTED: {wake_word}]")
                                break
                    else:
                        # Process command
                        print(f"🎯 Command: {text}")
                        
                        # Call callback with recognized text
                        if callback:
                            callback(text)
                        
                        # Reset wake word detection after processing
                        wake_word_detected = False
                        print("🎙️ Listening for wake word...")
                        
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                logging.error(f"Speech recognition service error: {e}")
                continue
            except Exception as e:
                logging.error(f"Error in voice loop: {e}")
                continue
                
    except KeyboardInterrupt:
        logging.info("🛑 Voice loop stopped by user")
    except Exception as e:
        logging.error(f"❌ Voice loop error: {e}")
        return f"❌ Error: {e}"
    finally:
        logging.info("Voice loop ended")


def test_voice_recognition(duration=10, language='auto'):
    """
    Test voice recognition for a specified duration.
    
    :param duration: Test duration in seconds
    :param language: Language to test ('en', 'hi', 'auto')
    """
    print(f"\n🎙️ Testing voice recognition for {duration} seconds...")
    print(f"📝 Language: {language}")
    print("🗣️ Speak now...\n")
    
    results = []
    
    def callback(text):
        results.append(text)
        print(f"✅ Recognized: {text}")
    
    # Create a stop event
    stop_event = threading.Event()
    
    # Start voice loop in a thread
    voice_thread = threading.Thread(
        target=voice_listen_loop,
        args=(callback, ['test'], True, language, stop_event),
        daemon=True
    )
    voice_thread.start()
    
    # Wait for duration
    import time
    time.sleep(duration)
    
    # Stop the loop
    stop_event.set()
    voice_thread.join(timeout=2)
    
    print(f"\n📊 Test complete. Recognized {len(results)} phrases:")
    for i, result in enumerate(results, 1):
        print(f"   {i}. {result}")
    
    return results


# Convenience functions for easy integration
def detect_text_language(text: str) -> str:
    """Quick function to detect language of text."""
    ml = MultilingualSupport()
    context = ml.detect_language(text)
    return context.detected_language.value

def translate_quick(text: str, target_lang: str) -> str:
    """Quick translation function."""
    ml = MultilingualSupport()
    target_language = Language(target_lang)
    return ml.translate_text(text, target_language)

def speak_in_language(text: str, language: str = "auto") -> str:
    """Quick TTS function with language support."""
    ml = MultilingualSupport()
    lang = Language(language) if language != "auto" else Language.AUTO_DETECT
    return ml.speak_multilingual(text, lang)

def process_hinglish_input(text: str) -> Dict[str, Any]:
    """Quick function to process Hinglish input."""
    ml = MultilingualSupport()
    return ml.process_hinglish_command(text)

# Export main components
__all__ = [
    'MultilingualSupport',
    'Language',
    'LanguageContext',
    'voice_listen_loop',
    'test_voice_recognition',
    'detect_text_language',
    'translate_quick',
    'speak_in_language',
    'process_hinglish_input',
    'VOSK_AVAILABLE',
    'SPEECH_RECOGNITION_AVAILABLE',
    'TTS_AVAILABLE'
]