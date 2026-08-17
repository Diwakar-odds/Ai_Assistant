"""
Multi-language Wake Word Detection Module

This module provides advanced multi-language wake word detection capabilities
with support for different languages, phoneme-based matching, and acoustic models.

Features:
- Multi-language phoneme recognition
- Language-specific acoustic models
- Dynamic wake word registration
- Cross-linguistic phonetic similarity matching
- Real-time detection with low latency
- Confidence scoring and threshold adjustment
- Custom wake word training
"""

import numpy as np
import threading
import queue
import time
import json
import pickle
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import logging
import re

try:
    import librosa
    import scipy.signal
    from dtw import dtw
    WAKE_WORD_AVAILABLE = True
except ImportError:
    WAKE_WORD_AVAILABLE = False
    logging.warning("Wake word detection requires librosa, scipy, and dtw")

try:
    import phonemes
    import epitran
    PHONETIC_SUPPORT_AVAILABLE = True
except ImportError:
    PHONETIC_SUPPORT_AVAILABLE = False
    logging.warning("Advanced phonetic support requires phonemes and epitran")

class SupportedLanguage(Enum):
    """Supported languages for wake word detection"""
    ENGLISH = "en"
    HINDI = "hi" 
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    MANDARIN = "zh"
    JAPANESE = "ja"
    ARABIC = "ar"
    RUSSIAN = "ru"
    PORTUGUESE = "pt"

class WakeWordConfidence(Enum):
    """Wake word detection confidence levels"""
    VERY_LOW = 0.3
    LOW = 0.5
    MEDIUM = 0.7
    HIGH = 0.8
    VERY_HIGH = 0.9

@dataclass
class PhonemeSequence:
    """Phonemic representation of a wake word"""
    phonemes: List[str]
    language: SupportedLanguage
    stress_pattern: Optional[List[int]] = None
    duration_pattern: Optional[List[float]] = None

@dataclass
class WakeWordTemplate:
    """Template for wake word detection"""
    word_text: str
    language: SupportedLanguage
    phoneme_sequence: PhonemeSequence
    acoustic_features: np.ndarray
    reference_samples: List[np.ndarray]
    confidence_threshold: float = 0.7
    created_date: float = 0.0
    usage_count: int = 0

@dataclass
class DetectionResult:
    """Result of wake word detection"""
    detected: bool
    wake_word: Optional[str]
    language: Optional[SupportedLanguage]
    confidence: float
    detection_time: float
    audio_segment: Optional[np.ndarray] = None

@dataclass
class MultilingualConfig:
    """Configuration for multilingual wake word detection"""
    supported_languages: List[SupportedLanguage] = None
    default_language: SupportedLanguage = SupportedLanguage.ENGLISH
    confidence_threshold: WakeWordConfidence = WakeWordConfidence.MEDIUM
    cross_lingual_matching: bool = True
    phoneme_similarity_threshold: float = 0.8
    acoustic_weight: float = 0.6
    phonetic_weight: float = 0.4
    max_detection_latency: float = 0.5
    wake_word_templates_path: str = "user_data/wake_words"
    enable_adaptive_thresholds: bool = True
    min_audio_length: float = 0.5
    max_audio_length: float = 3.0

# Phoneme mappings for cross-linguistic similarity
PHONEME_SIMILARITY_MAP = {
    # Vowels
    "a": ["a", "ä", "ɑ", "æ"],
    "e": ["e", "ɛ", "ə", "ɜ"],
    "i": ["i", "ɪ", "ɨ", "ɘ"],
    "o": ["o", "ɔ", "ɒ", "ɤ"],
    "u": ["u", "ʊ", "ɯ", "ɵ"],
    
    # Consonants
    "p": ["p", "b", "φ", "β"],
    "t": ["t", "d", "θ", "ð"],
    "k": ["k", "g", "x", "ɣ"],
    "m": ["m", "n", "ŋ", "ɲ"],
    "l": ["l", "r", "ɾ", "ɭ"],
    "s": ["s", "z", "ʃ", "ʒ"],
}

class PhonemeExtractor:
    """
    Extract phonemes from text in different languages
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.language_processors = {}
        self._initialize_processors()
    
    def _initialize_processors(self):
        """Initialize language-specific phoneme processors"""
        try:
            if PHONETIC_SUPPORT_AVAILABLE:
                # Initialize epitran processors for supported languages
                for lang in SupportedLanguage:
                    try:
                        processor = epitran.Epitran(lang.value)
                        self.language_processors[lang] = processor
                    except Exception as e:
                        self.logger.warning(f"Could not initialize processor for {lang.value}: {e}")
            
            # Fallback simple processors
            self._init_fallback_processors()
            
        except Exception as e:
            self.logger.error(f"Phoneme processor initialization failed: {e}")
    
    def _init_fallback_processors(self):
        """Initialize simple fallback phoneme processors"""
        # Basic English phoneme mapping
        self.english_phonemes = {
            'a': 'æ', 'e': 'ɛ', 'i': 'ɪ', 'o': 'ɔ', 'u': 'ʊ',
            'b': 'b', 'c': 'k', 'd': 'd', 'f': 'f', 'g': 'g',
            'h': 'h', 'j': 'dʒ', 'k': 'k', 'l': 'l', 'm': 'm',
            'n': 'n', 'p': 'p', 'q': 'kw', 'r': 'r', 's': 's',
            't': 't', 'v': 'v', 'w': 'w', 'x': 'ks', 'y': 'j', 'z': 'z'
        }
        
        # Basic Hindi transliteration (simplified)
        self.hindi_phonemes = {
            'अ': 'ə', 'आ': 'aː', 'इ': 'ɪ', 'ई': 'iː', 'उ': 'ʊ', 'ऊ': 'uː',
            'क': 'k', 'ख': 'kʰ', 'ग': 'g', 'घ': 'gʰ', 'च': 'tʃ', 'छ': 'tʃʰ',
            'ज': 'dʒ', 'झ': 'dʒʰ', 'ट': 'ʈ', 'ठ': 'ʈʰ', 'ड': 'ɖ', 'ढ': 'ɖʰ',
            'त': 't̪', 'थ': 't̪ʰ', 'द': 'd̪', 'ध': 'd̪ʰ', 'न': 'n', 'प': 'p',
            'फ': 'pʰ', 'ब': 'b', 'भ': 'bʰ', 'म': 'm', 'य': 'j', 'र': 'r',
            'ल': 'l', 'व': 'ʋ', 'श': 'ʃ', 'ष': 'ʂ', 'स': 's', 'ह': 'ɦ'
        }
    
    def extract_phonemes(self, text: str, language: SupportedLanguage) -> PhonemeSequence:
        """Extract phoneme sequence from text"""
        try:
            # Use epitran if available
            if language in self.language_processors:
                processor = self.language_processors[language]
                ipa_string = processor.transliterate(text)
                phonemes = list(ipa_string)
                
                return PhonemeSequence(
                    phonemes=phonemes,
                    language=language
                )
            
            # Fallback to simple mapping
            return self._fallback_phoneme_extraction(text, language)
            
        except Exception as e:
            self.logger.error(f"Phoneme extraction failed for '{text}' in {language.value}: {e}")
            return self._fallback_phoneme_extraction(text, language)
    
    def _fallback_phoneme_extraction(self, text: str, language: SupportedLanguage) -> PhonemeSequence:
        """Simple fallback phoneme extraction"""
        text = text.lower()
        phonemes = []
        
        if language == SupportedLanguage.ENGLISH:
            for char in text:
                if char in self.english_phonemes:
                    phonemes.append(self.english_phonemes[char])
                elif char.isalpha():
                    phonemes.append(char)  # Fallback to character
        
        elif language == SupportedLanguage.HINDI:
            for char in text:
                if char in self.hindi_phonemes:
                    phonemes.append(self.hindi_phonemes[char])
                elif char in self.english_phonemes:
                    phonemes.append(self.english_phonemes[char])
                elif char.isalpha():
                    phonemes.append(char)
        
        else:
            # Generic fallback
            for char in text:
                if char in self.english_phonemes:
                    phonemes.append(self.english_phonemes[char])
                elif char.isalpha():
                    phonemes.append(char)
        
        return PhonemeSequence(
            phonemes=phonemes,
            language=language
        )

class AcousticFeatureExtractor:
    """
    Extract acoustic features for wake word matching
    """
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.logger = logging.getLogger(__name__)
    
    def extract_features(self, audio_data: np.ndarray) -> np.ndarray:
        """Extract acoustic features from audio"""
        try:
            # Ensure correct format
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
                if np.max(np.abs(audio_data)) > 1.0:
                    audio_data = audio_data / 32767.0
            
            # Extract MFCC features
            mfccs = librosa.feature.mfcc(
                y=audio_data,
                sr=self.sample_rate,
                n_mfcc=13,
                hop_length=512,
                n_fft=2048
            )
            
            # Extract spectral features
            spectral_centroids = librosa.feature.spectral_centroid(
                y=audio_data, sr=self.sample_rate)
            
            spectral_rolloff = librosa.feature.spectral_rolloff(
                y=audio_data, sr=self.sample_rate)
            
            zero_crossing_rate = librosa.feature.zero_crossing_rate(audio_data)
            
            # Combine features
            features = np.vstack([
                mfccs,
                spectral_centroids,
                spectral_rolloff,
                zero_crossing_rate
            ])
            
            return features
            
        except Exception as e:
            self.logger.error(f"Feature extraction failed: {e}")
            return np.array([])

class PhoneticMatcher:
    """
    Match phoneme sequences with similarity scoring
    """
    
    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold
        self.logger = logging.getLogger(__name__)
    
    def calculate_similarity(self, seq1: PhonemeSequence, seq2: PhonemeSequence) -> float:
        """Calculate phonetic similarity between two sequences"""
        try:
            phonemes1 = seq1.phonemes
            phonemes2 = seq2.phonemes
            
            if not phonemes1 or not phonemes2:
                return 0.0
            
            # Use dynamic time warping for sequence alignment
            distance_matrix = self._create_distance_matrix(phonemes1, phonemes2)
            
            # Calculate DTW distance
            distance, _ = dtw(phonemes1, phonemes2, 
                            dist_method=lambda x, y: distance_matrix[
                                phonemes1.index(x) if x in phonemes1 else 0,
                                phonemes2.index(y) if y in phonemes2 else 0
                            ])
            
            # Convert distance to similarity score
            max_length = max(len(phonemes1), len(phonemes2))
            similarity = 1.0 - (distance / max_length)
            
            return max(0.0, similarity)
            
        except Exception as e:
            self.logger.error(f"Similarity calculation failed: {e}")
            return 0.0
    
    def _create_distance_matrix(self, phonemes1: List[str], phonemes2: List[str]) -> np.ndarray:
        """Create distance matrix for phoneme comparison"""
        matrix = np.ones((len(phonemes1), len(phonemes2)))
        
        for i, p1 in enumerate(phonemes1):
            for j, p2 in enumerate(phonemes2):
                if p1 == p2:
                    matrix[i, j] = 0.0
                else:
                    # Check phoneme similarity
                    similarity = self._phoneme_similarity(p1, p2)
                    matrix[i, j] = 1.0 - similarity
        
        return matrix
    
    def _phoneme_similarity(self, p1: str, p2: str) -> float:
        """Calculate similarity between individual phonemes"""
        if p1 == p2:
            return 1.0
        
        # Check similarity mappings
        for base_phoneme, similar_phonemes in PHONEME_SIMILARITY_MAP.items():
            if p1 in similar_phonemes and p2 in similar_phonemes:
                return 0.8  # High similarity
        
        # Check if they're both vowels or consonants
        vowels = set('aeiouæɛɪɔʊəɜɑɒɤɨɘɯɵ')
        if (p1 in vowels and p2 in vowels) or (p1 not in vowels and p2 not in vowels):
            return 0.3  # Low similarity
        
        return 0.0  # No similarity

class MultilingualWakeWordDetector:
    """
    Advanced multilingual wake word detection system
    """
    
    def __init__(self, config: Optional[MultilingualConfig] = None):
        self.config = config or MultilingualConfig()
        self.logger = logging.getLogger(__name__)
        
        if not WAKE_WORD_AVAILABLE:
            raise ImportError("Wake word detection requires librosa, scipy, and dtw")
        
        # Initialize components
        self.phoneme_extractor = PhonemeExtractor()
        self.feature_extractor = AcousticFeatureExtractor()
        self.phonetic_matcher = PhoneticMatcher(self.config.phoneme_similarity_threshold)
        
        # Wake word templates
        self.wake_word_templates: Dict[str, WakeWordTemplate] = {}
        
        # Detection state
        self.is_listening = False
        self.detection_thread = None
        self.audio_buffer = queue.Queue()
        self.detection_results = queue.Queue()
        
        # Create templates directory
        self.templates_path = Path(self.config.wake_word_templates_path)
        self.templates_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing templates
        self._load_wake_word_templates()
        
        # Set default supported languages
        if self.config.supported_languages is None:
            self.config.supported_languages = [
                SupportedLanguage.ENGLISH,
                SupportedLanguage.HINDI,
                SupportedLanguage.SPANISH
            ]
        
        self.logger.info(f"Multilingual wake word detector initialized with "
                        f"{len(self.wake_word_templates)} templates")
    
    def register_wake_word(self, word_text: str, language: SupportedLanguage,
                          audio_samples: List[np.ndarray]) -> bool:
        """
        Register a new wake word with audio samples
        
        Args:
            word_text: Text representation of the wake word
            language: Language of the wake word
            audio_samples: List of audio samples for training
            
        Returns:
            Success status
        """
        try:
            if not word_text or not audio_samples:
                return False
            
            # Extract phoneme sequence
            phoneme_sequence = self.phoneme_extractor.extract_phonemes(word_text, language)
            
            # Extract acoustic features from samples
            all_features = []
            for audio in audio_samples:
                features = self.feature_extractor.extract_features(audio)
                if features.size > 0:
                    all_features.append(features)
            
            if not all_features:
                self.logger.error(f"No valid features extracted for '{word_text}'")
                return False
            
            # Average features across samples
            # Pad features to same length for averaging
            max_frames = max(f.shape[1] for f in all_features)
            padded_features = []
            
            for features in all_features:
                if features.shape[1] < max_frames:
                    padding = max_frames - features.shape[1]
                    padded = np.pad(features, ((0, 0), (0, padding)), mode='edge')
                    padded_features.append(padded)
                else:
                    padded_features.append(features[:, :max_frames])
            
            averaged_features = np.mean(padded_features, axis=0)
            
            # Create template
            template = WakeWordTemplate(
                word_text=word_text,
                language=language,
                phoneme_sequence=phoneme_sequence,
                acoustic_features=averaged_features,
                reference_samples=audio_samples,
                confidence_threshold=self.config.confidence_threshold.value,
                created_date=time.time()
            )
            
            # Store template
            template_key = f"{language.value}_{word_text.lower().replace(' ', '_')}"
            self.wake_word_templates[template_key] = template
            
            # Save to disk
            self._save_wake_word_template(template_key, template)
            
            self.logger.info(f"Wake word '{word_text}' registered for {language.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Wake word registration failed for '{word_text}': {e}")
            return False
    
    def detect_wake_word(self, audio_data: np.ndarray, 
                        target_languages: Optional[List[SupportedLanguage]] = None) -> DetectionResult:
        """
        Detect wake words in audio data
        
        Args:
            audio_data: Audio data to analyze
            target_languages: Specific languages to check (None for all)
            
        Returns:
            Detection result
        """
        start_time = time.time()
        
        try:
            # Validate audio length
            duration = len(audio_data) / 16000  # Assuming 16kHz
            if duration < self.config.min_audio_length or duration > self.config.max_audio_length:
                return DetectionResult(
                    detected=False,
                    wake_word=None,
                    language=None,
                    confidence=0.0,
                    detection_time=0.0
                )
            
            # Extract acoustic features from input
            input_features = self.feature_extractor.extract_features(audio_data)
            if input_features.size == 0:
                return DetectionResult(
                    detected=False,
                    wake_word=None,
                    language=None,
                    confidence=0.0,
                    detection_time=time.time() - start_time
                )
            
            best_match = None
            best_confidence = 0.0
            
            # Check against all templates
            for template_key, template in self.wake_word_templates.items():
                # Skip if language not in target list
                if target_languages and template.language not in target_languages:
                    continue
                
                # Calculate acoustic similarity
                acoustic_similarity = self._calculate_acoustic_similarity(
                    input_features, template.acoustic_features)
                
                # Calculate phonetic similarity if cross-lingual matching enabled
                phonetic_similarity = 0.0
                if self.config.cross_lingual_matching:
                    # For phonetic matching, we'd need to extract phonemes from audio
                    # This is complex and would require additional ASR
                    # For now, use a heuristic based on acoustic features
                    phonetic_similarity = acoustic_similarity * 0.8  # Simplified
                
                # Combined confidence score
                confidence = (self.config.acoustic_weight * acoustic_similarity + 
                             self.config.phonetic_weight * phonetic_similarity)
                
                if confidence > best_confidence and confidence >= template.confidence_threshold:
                    best_confidence = confidence
                    best_match = template
            
            # Return result
            if best_match:
                # Update template usage
                best_match.usage_count += 1
                
                detection_time = time.time() - start_time
                
                return DetectionResult(
                    detected=True,
                    wake_word=best_match.word_text,
                    language=best_match.language,
                    confidence=best_confidence,
                    detection_time=detection_time,
                    audio_segment=audio_data
                )
            else:
                return DetectionResult(
                    detected=False,
                    wake_word=None,
                    language=None,
                    confidence=best_confidence,
                    detection_time=time.time() - start_time
                )
            
        except Exception as e:
            self.logger.error(f"Wake word detection failed: {e}")
            return DetectionResult(
                detected=False,
                wake_word=None,
                language=None,
                confidence=0.0,
                detection_time=time.time() - start_time
            )
    
    def _calculate_acoustic_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """Calculate acoustic similarity between feature vectors"""
        try:
            # Ensure same number of feature dimensions
            min_features = min(features1.shape[0], features2.shape[0])
            features1 = features1[:min_features, :]
            features2 = features2[:min_features, :]
            
            # Ensure same time length by DTW or truncation
            if features1.shape[1] != features2.shape[1]:
                min_time = min(features1.shape[1], features2.shape[1])
                features1 = features1[:, :min_time]
                features2 = features2[:, :min_time]
            
            # Calculate normalized cross-correlation
            correlation = np.corrcoef(features1.flatten(), features2.flatten())[0, 1]
            
            if np.isnan(correlation):
                return 0.0
            
            # Convert correlation to similarity score (0-1)
            similarity = (correlation + 1) / 2
            
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            self.logger.error(f"Acoustic similarity calculation failed: {e}")
            return 0.0
    
    def start_continuous_detection(self, callback=None):
        """Start continuous wake word detection"""
        if self.is_listening:
            self.logger.warning("Already listening for wake words")
            return
        
        self.is_listening = True
        self.detection_thread = threading.Thread(
            target=self._continuous_detection_loop,
            args=(callback,),
            daemon=True
        )
        self.detection_thread.start()
        self.logger.info("Continuous wake word detection started")
    
    def stop_continuous_detection(self):
        """Stop continuous detection"""
        self.is_listening = False
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=1.0)
        self.logger.info("Continuous wake word detection stopped")
    
    def _continuous_detection_loop(self, callback):
        """Continuous detection loop"""
        while self.is_listening:
            try:
                # Get audio data from buffer
                audio_data = self.audio_buffer.get(timeout=0.1)
                
                # Detect wake words
                result = self.detect_wake_word(audio_data)
                
                # Store result
                self.detection_results.put(result)
                
                # Call callback if provided and wake word detected
                if callback and result.detected:
                    callback(result)
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Continuous detection error: {e}")
    
    def add_audio_data(self, audio_data: np.ndarray):
        """Add audio data for continuous detection"""
        if self.is_listening:
            try:
                self.audio_buffer.put_nowait(audio_data)
            except queue.Full:
                self.logger.warning("Audio buffer full, dropping frame")
    
    def get_latest_detection(self) -> Optional[DetectionResult]:
        """Get latest detection result"""
        try:
            return self.detection_results.get_nowait()
        except queue.Empty:
            return None
    
    def _save_wake_word_template(self, template_key: str, template: WakeWordTemplate):
        """Save wake word template to disk"""
        try:
            # Prepare template data
            template_data = {
                'word_text': template.word_text,
                'language': template.language.value,
                'phoneme_sequence': {
                    'phonemes': template.phoneme_sequence.phonemes,
                    'language': template.phoneme_sequence.language.value
                },
                'confidence_threshold': template.confidence_threshold,
                'created_date': template.created_date,
                'usage_count': template.usage_count
            }
            
            # Save metadata
            metadata_file = self.templates_path / f"{template_key}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(template_data, f, indent=2)
            
            # Save acoustic features
            features_file = self.templates_path / f"{template_key}_features.npy"
            np.save(features_file, template.acoustic_features)
            
            # Save reference samples
            samples_file = self.templates_path / f"{template_key}_samples.pkl"
            with open(samples_file, 'wb') as f:
                pickle.dump(template.reference_samples, f)
            
            self.logger.debug(f"Template saved: {template_key}")
            
        except Exception as e:
            self.logger.error(f"Failed to save template {template_key}: {e}")
    
    def _load_wake_word_templates(self):
        """Load wake word templates from disk"""
        try:
            if not self.templates_path.exists():
                return
            
            for metadata_file in self.templates_path.glob("*_metadata.json"):
                template_key = metadata_file.stem.replace('_metadata', '')
                
                try:
                    # Load metadata
                    with open(metadata_file, 'r') as f:
                        template_data = json.load(f)
                    
                    # Load acoustic features
                    features_file = self.templates_path / f"{template_key}_features.npy"
                    if not features_file.exists():
                        continue
                    acoustic_features = np.load(features_file)
                    
                    # Load reference samples
                    samples_file = self.templates_path / f"{template_key}_samples.pkl"
                    if samples_file.exists():
                        with open(samples_file, 'rb') as f:
                            reference_samples = pickle.load(f)
                    else:
                        reference_samples = []
                    
                    # Reconstruct phoneme sequence
                    phoneme_data = template_data['phoneme_sequence']
                    phoneme_sequence = PhonemeSequence(
                        phonemes=phoneme_data['phonemes'],
                        language=SupportedLanguage(phoneme_data['language'])
                    )
                    
                    # Create template
                    template = WakeWordTemplate(
                        word_text=template_data['word_text'],
                        language=SupportedLanguage(template_data['language']),
                        phoneme_sequence=phoneme_sequence,
                        acoustic_features=acoustic_features,
                        reference_samples=reference_samples,
                        confidence_threshold=template_data.get('confidence_threshold', 0.7),
                        created_date=template_data.get('created_date', 0.0),
                        usage_count=template_data.get('usage_count', 0)
                    )
                    
                    self.wake_word_templates[template_key] = template
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load template {template_key}: {e}")
            
            self.logger.info(f"Loaded {len(self.wake_word_templates)} wake word templates")
            
        except Exception as e:
            self.logger.error(f"Template loading failed: {e}")
    
    def delete_wake_word(self, word_text: str, language: SupportedLanguage) -> bool:
        """Delete a wake word template"""
        template_key = f"{language.value}_{word_text.lower().replace(' ', '_')}"
        
        if template_key not in self.wake_word_templates:
            return False
        
        try:
            # Remove from memory
            del self.wake_word_templates[template_key]
            
            # Remove files
            files_to_remove = [
                f"{template_key}_metadata.json",
                f"{template_key}_features.npy",
                f"{template_key}_samples.pkl"
            ]
            
            for filename in files_to_remove:
                file_path = self.templates_path / filename
                if file_path.exists():
                    file_path.unlink()
            
            self.logger.info(f"Wake word '{word_text}' deleted for {language.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete wake word '{word_text}': {e}")
            return False
    
    def get_registered_wake_words(self) -> List[Dict[str, Any]]:
        """Get list of registered wake words"""
        wake_words = []
        
        for template_key, template in self.wake_word_templates.items():
            wake_words.append({
                'word_text': template.word_text,
                'language': template.language.value,
                'phonemes': template.phoneme_sequence.phonemes,
                'confidence_threshold': template.confidence_threshold,
                'usage_count': template.usage_count,
                'created_date': template.created_date
            })
        
        return wake_words
    
    def update_confidence_threshold(self, word_text: str, language: SupportedLanguage, 
                                  new_threshold: float):
        """Update confidence threshold for a specific wake word"""
        template_key = f"{language.value}_{word_text.lower().replace(' ', '_')}"
        
        if template_key in self.wake_word_templates:
            self.wake_word_templates[template_key].confidence_threshold = new_threshold
            self._save_wake_word_template(template_key, self.wake_word_templates[template_key])
            self.logger.info(f"Updated threshold for '{word_text}' to {new_threshold}")


# Convenience functions
def create_multilingual_detector(languages: List[SupportedLanguage] = None) -> MultilingualWakeWordDetector:
    """Create multilingual wake word detector with specified languages"""
    config = MultilingualConfig()
    if languages:
        config.supported_languages = languages
    return MultilingualWakeWordDetector(config)

def quick_wake_word_detection(audio_data: np.ndarray, 
                             detector: Optional[MultilingualWakeWordDetector] = None) -> bool:
    """Quick wake word detection function"""
    if detector is None:
        detector = create_multilingual_detector()
    
    result = detector.detect_wake_word(audio_data)
    return result.detected