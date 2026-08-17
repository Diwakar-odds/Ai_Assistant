"""
Voice Fingerprinting and User Recognition Module

This module provides advanced voice fingerprinting capabilities for automatic
user recognition and authentication through vocal characteristics.

Features:
- Voice embedding extraction using deep learning models
- Speaker enrollment and verification
- Automatic user recognition from voice
- Anti-spoofing protection
- Continuous adaptation to voice changes
- Multi-session voice profile management
- Privacy-preserving voice templates
"""

import numpy as np
import threading
import queue
import time
import json
import hashlib
import pickle
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging
from datetime import datetime, timedelta

try:
    import librosa
    import scipy.spatial.distance
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    import torch
    import torchaudio
    FINGERPRINTING_AVAILABLE = True
except ImportError:
    FINGERPRINTING_AVAILABLE = False
    logging.warning("Voice fingerprinting requires librosa, scikit-learn, torch, and torchaudio")

try:
    import speechbrain as sb
    from speechbrain.pretrained import EncoderClassifier
    SPEECHBRAIN_AVAILABLE = True
except ImportError:
    SPEECHBRAIN_AVAILABLE = False
    logging.warning("Advanced embeddings require SpeechBrain")

class RecognitionConfidence(Enum):
    """Voice recognition confidence levels"""
    VERY_LOW = 0.3
    LOW = 0.5
    MEDIUM = 0.7
    HIGH = 0.8
    VERY_HIGH = 0.9

class VoiceQuality(Enum):
    """Voice sample quality assessment"""
    POOR = "poor"
    FAIR = "fair" 
    GOOD = "good"
    EXCELLENT = "excellent"

@dataclass
class VoiceEmbedding:
    """Voice embedding representation"""
    embedding: np.ndarray
    quality_score: float
    duration: float
    sample_rate: int
    extraction_model: str
    created_time: float = field(default_factory=time.time)

@dataclass
class UserVoiceProfile:
    """User voice profile with multiple embeddings"""
    user_id: str
    display_name: str
    embeddings: List[VoiceEmbedding] = field(default_factory=list)
    enrollment_samples: int = 0
    last_recognition: float = 0.0
    recognition_count: int = 0
    adaptation_enabled: bool = True
    confidence_threshold: float = 0.7
    created_date: float = field(default_factory=time.time)
    updated_date: float = field(default_factory=time.time)

@dataclass
class RecognitionResult:
    """Voice recognition result"""
    recognized: bool
    user_id: Optional[str]
    display_name: Optional[str] 
    confidence: float
    quality_score: float
    processing_time: float
    embedding: Optional[VoiceEmbedding] = None
    is_spoofing_detected: bool = False

@dataclass
class VoiceFingerprintConfig:
    """Configuration for voice fingerprinting"""
    # Model settings
    embedding_model: str = "speechbrain/spkrec-ecapa-voxceleb"
    fallback_model: str = "custom_mfcc"
    min_audio_duration: float = 2.0
    max_audio_duration: float = 10.0
    target_sample_rate: int = 16000
    
    # Recognition settings
    recognition_threshold: RecognitionConfidence = RecognitionConfidence.MEDIUM
    adaptation_threshold: float = 0.8
    max_embeddings_per_user: int = 20
    quality_threshold: float = 0.6
    
    # Anti-spoofing settings
    enable_anti_spoofing: bool = True
    spoofing_threshold: float = 0.5
    liveness_detection: bool = True
    
    # Privacy settings
    encrypt_profiles: bool = True
    profile_retention_days: int = 365
    auto_cleanup: bool = True
    
    # Storage paths
    profiles_path: str = "user_data/voice_profiles"
    models_cache_path: str = "model/voice_models"
    
    # Clustering settings
    clustering_enabled: bool = True
    min_cluster_samples: int = 3
    cluster_eps: float = 0.3

class VoiceEmbeddingExtractor:
    """
    Extract voice embeddings using various models
    """
    
    def __init__(self, config: VoiceFingerprintConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Model cache
        self.models = {}
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Initialize models
        self._initialize_models()
        
        # Quality assessor
        self.quality_assessor = VoiceQualityAssessor()
    
    def _initialize_models(self):
        """Initialize embedding models"""
        try:
            # Try to load SpeechBrain model
            if SPEECHBRAIN_AVAILABLE:
                try:
                    model = EncoderClassifier.from_hparams(
                        source=self.config.embedding_model,
                        savedir=self.config.models_cache_path,
                        run_opts={"device": self.device}
                    )
                    self.models['speechbrain'] = model
                    self.logger.info("SpeechBrain model loaded successfully")
                except Exception as e:
                    self.logger.warning(f"Failed to load SpeechBrain model: {e}")
            
            # Always have fallback model available
            self.models['mfcc'] = self._create_mfcc_extractor()
            
        except Exception as e:
            self.logger.error(f"Model initialization failed: {e}")
    
    def _create_mfcc_extractor(self):
        """Create MFCC-based fallback extractor"""
        return {
            'type': 'mfcc',
            'n_mfcc': 13,
            'n_fft': 2048,
            'hop_length': 512
        }
    
    def extract_embedding(self, audio_data: np.ndarray, model_name: str = None) -> Optional[VoiceEmbedding]:
        """
        Extract voice embedding from audio
        
        Args:
            audio_data: Audio data (mono, normalized)
            model_name: Specific model to use
            
        Returns:
            Voice embedding or None if extraction failed
        """
        try:
            # Validate audio
            if not self._validate_audio(audio_data):
                return None
            
            # Assess audio quality
            quality_score = self.quality_assessor.assess_quality(audio_data, self.config.target_sample_rate)
            
            if quality_score < self.config.quality_threshold:
                self.logger.warning(f"Audio quality too low: {quality_score}")
                return None
            
            # Choose model
            if model_name and model_name in self.models:
                model = self.models[model_name]
                model_type = model_name
            elif 'speechbrain' in self.models:
                model = self.models['speechbrain']
                model_type = 'speechbrain'
            else:
                model = self.models['mfcc']
                model_type = 'mfcc'
            
            # Extract embedding
            if model_type == 'speechbrain':
                embedding = self._extract_speechbrain_embedding(audio_data, model)
            else:
                embedding = self._extract_mfcc_embedding(audio_data, model)
            
            if embedding is None:
                return None
            
            return VoiceEmbedding(
                embedding=embedding,
                quality_score=quality_score,
                duration=len(audio_data) / self.config.target_sample_rate,
                sample_rate=self.config.target_sample_rate,
                extraction_model=model_type
            )
            
        except Exception as e:
            self.logger.error(f"Embedding extraction failed: {e}")
            return None
    
    def _validate_audio(self, audio_data: np.ndarray) -> bool:
        """Validate audio data"""
        if audio_data is None or len(audio_data) == 0:
            return False
        
        duration = len(audio_data) / self.config.target_sample_rate
        if duration < self.config.min_audio_duration or duration > self.config.max_audio_duration:
            return False
        
        # Check for silence
        energy = np.mean(audio_data ** 2)
        if energy < 1e-6:  # Very low energy
            return False
        
        return True
    
    def _extract_speechbrain_embedding(self, audio_data: np.ndarray, model) -> Optional[np.ndarray]:
        """Extract embedding using SpeechBrain model"""
        try:
            # Convert to tensor
            audio_tensor = torch.tensor(audio_data).unsqueeze(0).float()
            
            # Extract embeddings
            with torch.no_grad():
                embeddings = model.encode_batch(audio_tensor)
                embedding = embeddings.squeeze().cpu().numpy()
            
            # Normalize
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"SpeechBrain embedding extraction failed: {e}")
            return None
    
    def _extract_mfcc_embedding(self, audio_data: np.ndarray, model_config: dict) -> Optional[np.ndarray]:
        """Extract MFCC-based embedding"""
        try:
            # Extract MFCC features
            mfccs = librosa.feature.mfcc(
                y=audio_data,
                sr=self.config.target_sample_rate,
                n_mfcc=model_config['n_mfcc'],
                n_fft=model_config['n_fft'],
                hop_length=model_config['hop_length']
            )
            
            # Additional features
            spectral_centroids = librosa.feature.spectral_centroid(
                y=audio_data, sr=self.config.target_sample_rate)
            
            spectral_rolloff = librosa.feature.spectral_rolloff(
                y=audio_data, sr=self.config.target_sample_rate)
            
            zero_crossing_rate = librosa.feature.zero_crossing_rate(audio_data)
            
            # Combine features
            features = np.vstack([
                mfccs,
                spectral_centroids,
                spectral_rolloff,
                zero_crossing_rate
            ])
            
            # Create embedding from statistical measures
            embedding = np.concatenate([
                np.mean(features, axis=1),
                np.std(features, axis=1),
                np.median(features, axis=1),
                np.min(features, axis=1),
                np.max(features, axis=1)
            ])
            
            # Normalize
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"MFCC embedding extraction failed: {e}")
            return None

class VoiceQualityAssessor:
    """
    Assess voice sample quality for fingerprinting
    """
    
    def assess_quality(self, audio_data: np.ndarray, sample_rate: int) -> float:
        """Assess overall quality score (0-1)"""
        try:
            quality_factors = []
            
            # Signal-to-noise ratio
            snr_score = self._assess_snr(audio_data)
            quality_factors.append(snr_score)
            
            # Spectral clarity
            spectral_score = self._assess_spectral_clarity(audio_data, sample_rate)
            quality_factors.append(spectral_score)
            
            # Speech activity
            activity_score = self._assess_speech_activity(audio_data)
            quality_factors.append(activity_score)
            
            # Clipping detection
            clipping_score = self._assess_clipping(audio_data)
            quality_factors.append(clipping_score)
            
            # Overall quality
            overall_quality = np.mean(quality_factors)
            
            return max(0.0, min(1.0, overall_quality))
            
        except Exception:
            return 0.0
    
    def _assess_snr(self, audio_data: np.ndarray) -> float:
        """Assess signal-to-noise ratio"""
        try:
            # Simple energy-based SNR estimation
            energy = np.mean(audio_data ** 2)
            
            # Estimate noise from quietest 10% of frames
            frame_size = 1024
            frame_energies = []
            
            for i in range(0, len(audio_data) - frame_size, frame_size):
                frame = audio_data[i:i + frame_size]
                frame_energies.append(np.mean(frame ** 2))
            
            if not frame_energies:
                return 0.5
            
            frame_energies = np.array(frame_energies)
            noise_energy = np.percentile(frame_energies, 10)
            
            if noise_energy <= 0:
                return 1.0
            
            snr = 10 * np.log10(energy / noise_energy)
            
            # Convert to 0-1 scale (0dB SNR = 0.5, 20dB+ = 1.0)
            snr_score = min(1.0, max(0.0, (snr + 20) / 40))
            
            return snr_score
            
        except Exception:
            return 0.5
    
    def _assess_spectral_clarity(self, audio_data: np.ndarray, sample_rate: int) -> float:
        """Assess spectral clarity and definition"""
        try:
            # Compute spectral features
            spectral_centroid = librosa.feature.spectral_centroid(y=audio_data, sr=sample_rate)
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=audio_data, sr=sample_rate)
            spectral_contrast = librosa.feature.spectral_contrast(y=audio_data, sr=sample_rate)
            
            # Assess clarity based on spectral characteristics
            centroid_std = np.std(spectral_centroid)
            bandwidth_mean = np.mean(spectral_bandwidth)
            contrast_mean = np.mean(spectral_contrast)
            
            # Higher contrast and moderate centroid variation indicate clarity
            clarity_score = (contrast_mean + (1.0 / (1.0 + centroid_std/1000))) / 2
            
            return max(0.0, min(1.0, clarity_score))
            
        except Exception:
            return 0.5
    
    def _assess_speech_activity(self, audio_data: np.ndarray) -> float:
        """Assess speech activity level"""
        try:
            # Voice activity detection using zero crossing rate and energy
            frame_size = 1024
            hop_length = 512
            
            zcr = librosa.feature.zero_crossing_rate(audio_data, frame_length=frame_size, 
                                                   hop_length=hop_length)
            energy = librosa.feature.rms(y=audio_data, frame_length=frame_size, 
                                       hop_length=hop_length)
            
            # Thresholds for speech activity
            zcr_threshold = np.mean(zcr)
            energy_threshold = np.mean(energy) * 0.1
            
            # Count active frames
            active_frames = np.sum((zcr[0] > zcr_threshold) & (energy[0] > energy_threshold))
            total_frames = len(zcr[0])
            
            activity_ratio = active_frames / total_frames if total_frames > 0 else 0
            
            # Ideal activity ratio is around 0.6-0.8
            if activity_ratio < 0.3:
                return activity_ratio * 2  # Too little speech
            elif activity_ratio > 0.9:
                return 2 - activity_ratio  # Too much activity (noise)
            else:
                return 1.0  # Good activity level
            
        except Exception:
            return 0.5
    
    def _assess_clipping(self, audio_data: np.ndarray) -> float:
        """Assess audio clipping"""
        try:
            # Detect clipping (samples at maximum/minimum values)
            max_val = np.max(np.abs(audio_data))
            
            if max_val >= 0.99:  # Likely clipped
                clipped_samples = np.sum(np.abs(audio_data) >= 0.99)
                clipping_ratio = clipped_samples / len(audio_data)
                return 1.0 - min(1.0, clipping_ratio * 10)  # Penalize clipping
            
            return 1.0  # No clipping detected
            
        except Exception:
            return 1.0

class AntiSpoofingDetector:
    """
    Detect voice spoofing and liveness
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def detect_spoofing(self, audio_data: np.ndarray, sample_rate: int) -> Tuple[bool, float]:
        """
        Detect voice spoofing
        
        Returns:
            (is_spoofed, confidence)
        """
        try:
            spoofing_indicators = []
            
            # Spectral analysis for synthetic detection
            spectral_score = self._analyze_spectral_artifacts(audio_data, sample_rate)
            spoofing_indicators.append(spectral_score)
            
            # Temporal analysis for replay detection
            temporal_score = self._analyze_temporal_artifacts(audio_data)
            spoofing_indicators.append(temporal_score)
            
            # Harmonic analysis
            harmonic_score = self._analyze_harmonic_structure(audio_data, sample_rate)
            spoofing_indicators.append(harmonic_score)
            
            # Combined spoofing score
            overall_score = np.mean(spoofing_indicators)
            
            is_spoofed = overall_score > 0.5
            confidence = overall_score if is_spoofed else 1.0 - overall_score
            
            return is_spoofed, confidence
            
        except Exception as e:
            self.logger.error(f"Spoofing detection failed: {e}")
            return False, 0.0
    
    def _analyze_spectral_artifacts(self, audio_data: np.ndarray, sample_rate: int) -> float:
        """Analyze spectral artifacts common in synthetic speech"""
        try:
            # Compute spectrogram
            stft = librosa.stft(audio_data, hop_length=512)
            magnitude = np.abs(stft)
            
            # Look for artifacts in high frequencies
            high_freq_energy = np.mean(magnitude[magnitude.shape[0]//2:, :])
            total_energy = np.mean(magnitude)
            
            high_freq_ratio = high_freq_energy / total_energy if total_energy > 0 else 0
            
            # Synthetic speech often lacks high frequency content
            if high_freq_ratio < 0.1:
                return 0.7  # Suspicious
            
            # Check for regular patterns (vocoder artifacts)
            freq_var = np.var(np.mean(magnitude, axis=1))
            if freq_var < 0.001:  # Too regular
                return 0.8
            
            return 0.2  # Seems natural
            
        except Exception:
            return 0.0
    
    def _analyze_temporal_artifacts(self, audio_data: np.ndarray) -> float:
        """Analyze temporal artifacts for replay detection"""
        try:
            # Analyze amplitude envelope
            envelope = np.abs(librosa.util.frame(audio_data, frame_length=1024, hop_length=512))
            envelope_mean = np.mean(envelope, axis=0)
            
            # Check for unnatural amplitude patterns
            envelope_var = np.var(envelope_mean)
            
            # Too uniform amplitude (common in replayed audio)
            if envelope_var < 0.001:
                return 0.6
            
            # Check for compression artifacts
            dynamic_range = np.max(audio_data) - np.min(audio_data)
            if dynamic_range < 0.1:  # Heavily compressed
                return 0.5
            
            return 0.2
            
        except Exception:
            return 0.0
    
    def _analyze_harmonic_structure(self, audio_data: np.ndarray, sample_rate: int) -> float:
        """Analyze harmonic structure naturalness"""
        try:
            # Pitch detection
            pitches, magnitudes = librosa.piptrack(y=audio_data, sr=sample_rate)
            
            # Get fundamental frequency
            f0 = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    f0.append(pitch)
            
            if len(f0) < 10:
                return 0.3  # Insufficient pitch information
            
            f0 = np.array(f0)
            
            # Check pitch continuity (natural speech has gradual pitch changes)
            pitch_diff = np.abs(np.diff(f0))
            large_jumps = np.sum(pitch_diff > 50) / len(pitch_diff)
            
            if large_jumps > 0.3:  # Too many abrupt pitch changes
                return 0.6
            
            # Check pitch variance (monotonic pitch is suspicious)
            pitch_var = np.var(f0)
            if pitch_var < 100:  # Too little variation
                return 0.5
            
            return 0.1  # Natural harmonic structure
            
        except Exception:
            return 0.0

class VoiceFingerprintingSystem:
    """
    Complete voice fingerprinting and user recognition system
    """
    
    def __init__(self, config: Optional[VoiceFingerprintConfig] = None):
        self.config = config or VoiceFingerprintConfig()
        self.logger = logging.getLogger(__name__)
        
        if not FINGERPRINTING_AVAILABLE:
            raise ImportError("Voice fingerprinting requires librosa, scikit-learn, torch")
        
        # Initialize components
        self.embedding_extractor = VoiceEmbeddingExtractor(self.config)
        self.anti_spoofing = AntiSpoofingDetector() if self.config.enable_anti_spoofing else None
        
        # User profiles
        self.user_profiles: Dict[str, UserVoiceProfile] = {}
        
        # Clustering for profile management
        self.scaler = StandardScaler()
        self.clustering_model = DBSCAN(eps=self.config.cluster_eps, 
                                     min_samples=self.config.min_cluster_samples)
        
        # Recognition state
        self.is_recognizing = False
        self.recognition_thread = None
        self.audio_queue = queue.Queue()
        self.results_queue = queue.Queue()
        
        # Create directories
        self.profiles_path = Path(self.config.profiles_path)
        self.profiles_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing profiles
        self._load_user_profiles()
        
        self.logger.info(f"Voice fingerprinting system initialized with "
                        f"{len(self.user_profiles)} user profiles")
    
    def enroll_user(self, user_id: str, display_name: str, 
                   audio_samples: List[np.ndarray]) -> bool:
        """
        Enroll a new user with voice samples
        
        Args:
            user_id: Unique user identifier
            display_name: Display name for the user
            audio_samples: List of voice samples for enrollment
            
        Returns:
            Success status
        """
        try:
            if not audio_samples:
                self.logger.error("No audio samples provided for enrollment")
                return False
            
            embeddings = []
            
            # Extract embeddings from all samples
            for i, audio_data in enumerate(audio_samples):
                # Preprocess audio
                audio_data = self._preprocess_audio(audio_data)
                
                # Anti-spoofing check
                if self.anti_spoofing:
                    is_spoofed, confidence = self.anti_spoofing.detect_spoofing(
                        audio_data, self.config.target_sample_rate)
                    
                    if is_spoofed and confidence > self.config.spoofing_threshold:
                        self.logger.warning(f"Spoofing detected in sample {i}, skipping")
                        continue
                
                # Extract embedding
                embedding = self.embedding_extractor.extract_embedding(audio_data)
                
                if embedding and embedding.quality_score >= self.config.quality_threshold:
                    embeddings.append(embedding)
                else:
                    self.logger.warning(f"Poor quality sample {i}, skipping")
            
            if len(embeddings) < 2:
                self.logger.error("Insufficient quality embeddings for enrollment")
                return False
            
            # Create user profile
            profile = UserVoiceProfile(
                user_id=user_id,
                display_name=display_name,
                embeddings=embeddings,
                enrollment_samples=len(embeddings),
                confidence_threshold=self.config.recognition_threshold.value
            )
            
            # Store profile
            self.user_profiles[user_id] = profile
            
            # Save to disk
            self._save_user_profile(profile)
            
            self.logger.info(f"User '{display_name}' enrolled with {len(embeddings)} embeddings")
            return True
            
        except Exception as e:
            self.logger.error(f"User enrollment failed: {e}")
            return False
    
    def recognize_user(self, audio_data: np.ndarray) -> RecognitionResult:
        """
        Recognize user from voice sample
        
        Args:
            audio_data: Audio data for recognition
            
        Returns:
            Recognition result
        """
        start_time = time.time()
        
        try:
            # Preprocess audio
            audio_data = self._preprocess_audio(audio_data)
            
            # Anti-spoofing check
            if self.anti_spoofing:
                is_spoofed, spoofing_confidence = self.anti_spoofing.detect_spoofing(
                    audio_data, self.config.target_sample_rate)
                
                if is_spoofed and spoofing_confidence > self.config.spoofing_threshold:
                    return RecognitionResult(
                        recognized=False,
                        user_id=None,
                        display_name=None,
                        confidence=0.0,
                        quality_score=0.0,
                        processing_time=time.time() - start_time,
                        is_spoofing_detected=True
                    )
            
            # Extract embedding
            embedding = self.embedding_extractor.extract_embedding(audio_data)
            
            if not embedding:
                return RecognitionResult(
                    recognized=False,
                    user_id=None,
                    display_name=None,
                    confidence=0.0,
                    quality_score=0.0,
                    processing_time=time.time() - start_time
                )
            
            # Find best matching user
            best_user = None
            best_confidence = 0.0
            
            for user_id, profile in self.user_profiles.items():
                # Calculate similarity to user embeddings
                similarities = []
                
                for profile_embedding in profile.embeddings:
                    similarity = self._calculate_embedding_similarity(
                        embedding.embedding, profile_embedding.embedding)
                    similarities.append(similarity)
                
                if similarities:
                    # Use maximum similarity
                    max_similarity = max(similarities)
                    
                    # Weight by number of embeddings (more samples = more reliable)
                    weight = min(1.0, len(similarities) / 5)
                    confidence = max_similarity * weight
                    
                    if confidence > best_confidence and confidence >= profile.confidence_threshold:
                        best_confidence = confidence
                        best_user = profile
            
            # Return result
            if best_user:
                # Update profile
                best_user.last_recognition = time.time()
                best_user.recognition_count += 1
                
                # Adaptive learning
                if (best_confidence > self.config.adaptation_threshold and 
                    best_user.adaptation_enabled):
                    self._adapt_user_profile(best_user, embedding)
                
                return RecognitionResult(
                    recognized=True,
                    user_id=best_user.user_id,
                    display_name=best_user.display_name,
                    confidence=best_confidence,
                    quality_score=embedding.quality_score,
                    processing_time=time.time() - start_time,
                    embedding=embedding
                )
            else:
                return RecognitionResult(
                    recognized=False,
                    user_id=None,
                    display_name=None,
                    confidence=best_confidence,
                    quality_score=embedding.quality_score,
                    processing_time=time.time() - start_time,
                    embedding=embedding
                )
            
        except Exception as e:
            self.logger.error(f"User recognition failed: {e}")
            return RecognitionResult(
                recognized=False,
                user_id=None,
                display_name=None,
                confidence=0.0,
                quality_score=0.0,
                processing_time=time.time() - start_time
            )
    
    def _preprocess_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Preprocess audio for fingerprinting"""
        # Ensure float32 format
        if audio_data.dtype != np.float32:
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32767.0
            else:
                audio_data = audio_data.astype(np.float32)
        
        # Resample if needed
        if hasattr(self, 'current_sample_rate') and self.current_sample_rate != self.config.target_sample_rate:
            audio_data = librosa.resample(
                audio_data, 
                orig_sr=self.current_sample_rate, 
                target_sr=self.config.target_sample_rate
            )
        
        # Normalize amplitude
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            audio_data = audio_data / max_val * 0.9
        
        return audio_data
    
    def _calculate_embedding_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate similarity between embeddings"""
        try:
            # Ensure same dimension
            min_dim = min(len(emb1), len(emb2))
            emb1 = emb1[:min_dim]
            emb2 = emb2[:min_dim]
            
            # Cosine similarity
            cosine_sim = 1 - scipy.spatial.distance.cosine(emb1, emb2)
            
            if np.isnan(cosine_sim):
                return 0.0
            
            return max(0.0, min(1.0, cosine_sim))
            
        except Exception:
            return 0.0
    
    def _adapt_user_profile(self, profile: UserVoiceProfile, new_embedding: VoiceEmbedding):
        """Adaptively update user profile with new embedding"""
        try:
            # Add new embedding
            profile.embeddings.append(new_embedding)
            profile.updated_date = time.time()
            
            # Limit number of embeddings
            if len(profile.embeddings) > self.config.max_embeddings_per_user:
                # Remove oldest or lowest quality embeddings
                profile.embeddings.sort(key=lambda x: (x.quality_score, x.created_time))
                profile.embeddings = profile.embeddings[-self.config.max_embeddings_per_user:]
            
            # Clustering-based profile optimization
            if self.config.clustering_enabled and len(profile.embeddings) > self.config.min_cluster_samples:
                self._optimize_profile_embeddings(profile)
            
            # Save updated profile
            self._save_user_profile(profile)
            
        except Exception as e:
            self.logger.error(f"Profile adaptation failed: {e}")
    
    def _optimize_profile_embeddings(self, profile: UserVoiceProfile):
        """Optimize profile embeddings using clustering"""
        try:
            # Extract embedding vectors
            embeddings_matrix = np.array([emb.embedding for emb in profile.embeddings])
            
            # Standardize features
            embeddings_scaled = self.scaler.fit_transform(embeddings_matrix)
            
            # Cluster embeddings
            clusters = self.clustering_model.fit_predict(embeddings_scaled)
            
            # Keep representative embeddings from each cluster
            unique_clusters = set(clusters)
            if -1 in unique_clusters:  # Remove noise cluster
                unique_clusters.remove(-1)
            
            representative_embeddings = []
            
            for cluster_id in unique_clusters:
                cluster_indices = np.where(clusters == cluster_id)[0]
                cluster_embeddings = [profile.embeddings[i] for i in cluster_indices]
                
                # Choose highest quality embedding from cluster
                best_embedding = max(cluster_embeddings, key=lambda x: x.quality_score)
                representative_embeddings.append(best_embedding)
            
            # Update profile with representative embeddings
            if representative_embeddings:
                profile.embeddings = representative_embeddings
            
        except Exception as e:
            self.logger.error(f"Profile optimization failed: {e}")
    
    def start_continuous_recognition(self, callback=None):
        """Start continuous user recognition"""
        if self.is_recognizing:
            self.logger.warning("Already recognizing users")
            return
        
        self.is_recognizing = True
        self.recognition_thread = threading.Thread(
            target=self._continuous_recognition_loop,
            args=(callback,),
            daemon=True
        )
        self.recognition_thread.start()
        self.logger.info("Continuous user recognition started")
    
    def stop_continuous_recognition(self):
        """Stop continuous recognition"""
        self.is_recognizing = False
        if self.recognition_thread and self.recognition_thread.is_alive():
            self.recognition_thread.join(timeout=1.0)
        self.logger.info("Continuous user recognition stopped")
    
    def _continuous_recognition_loop(self, callback):
        """Continuous recognition loop"""
        while self.is_recognizing:
            try:
                # Get audio from queue
                audio_data = self.audio_queue.get(timeout=0.1)
                
                # Recognize user
                result = self.recognize_user(audio_data)
                
                # Store result
                self.results_queue.put(result)
                
                # Call callback if provided and user recognized
                if callback and result.recognized:
                    callback(result)
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Continuous recognition error: {e}")
    
    def add_recognition_audio(self, audio_data: np.ndarray):
        """Add audio for continuous recognition"""
        if self.is_recognizing:
            try:
                self.audio_queue.put_nowait(audio_data)
            except queue.Full:
                self.logger.warning("Recognition audio queue full")
    
    def get_latest_recognition(self) -> Optional[RecognitionResult]:
        """Get latest recognition result"""
        try:
            return self.results_queue.get_nowait()
        except queue.Empty:
            return None
    
    def delete_user_profile(self, user_id: str) -> bool:
        """Delete a user profile"""
        if user_id not in self.user_profiles:
            return False
        
        try:
            # Remove from memory
            del self.user_profiles[user_id]
            
            # Remove from disk
            profile_file = self.profiles_path / f"{user_id}_profile.json"
            embeddings_file = self.profiles_path / f"{user_id}_embeddings.pkl"
            
            if profile_file.exists():
                profile_file.unlink()
            
            if embeddings_file.exists():
                embeddings_file.unlink()
            
            self.logger.info(f"User profile {user_id} deleted")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete user profile {user_id}: {e}")
            return False
    
    def get_user_profiles(self) -> List[Dict[str, Any]]:
        """Get list of enrolled user profiles"""
        profiles = []
        
        for profile in self.user_profiles.values():
            profiles.append({
                'user_id': profile.user_id,
                'display_name': profile.display_name,
                'enrollment_samples': profile.enrollment_samples,
                'recognition_count': profile.recognition_count,
                'last_recognition': profile.last_recognition,
                'created_date': profile.created_date,
                'adaptation_enabled': profile.adaptation_enabled
            })
        
        return profiles
    
    def _save_user_profile(self, profile: UserVoiceProfile):
        """Save user profile to disk"""
        try:
            # Prepare profile data (without embeddings)
            profile_data = {
                'user_id': profile.user_id,
                'display_name': profile.display_name,
                'enrollment_samples': profile.enrollment_samples,
                'last_recognition': profile.last_recognition,
                'recognition_count': profile.recognition_count,
                'adaptation_enabled': profile.adaptation_enabled,
                'confidence_threshold': profile.confidence_threshold,
                'created_date': profile.created_date,
                'updated_date': profile.updated_date
            }
            
            # Save profile metadata
            profile_file = self.profiles_path / f"{profile.user_id}_profile.json"
            with open(profile_file, 'w') as f:
                json.dump(profile_data, f, indent=2)
            
            # Save embeddings separately
            embeddings_file = self.profiles_path / f"{profile.user_id}_embeddings.pkl"
            with open(embeddings_file, 'wb') as f:
                pickle.dump(profile.embeddings, f)
            
        except Exception as e:
            self.logger.error(f"Failed to save profile {profile.user_id}: {e}")
    
    def _load_user_profiles(self):
        """Load user profiles from disk"""
        try:
            if not self.profiles_path.exists():
                return
            
            for profile_file in self.profiles_path.glob("*_profile.json"):
                user_id = profile_file.stem.replace('_profile', '')
                
                try:
                    # Load profile metadata
                    with open(profile_file, 'r') as f:
                        profile_data = json.load(f)
                    
                    # Load embeddings
                    embeddings_file = self.profiles_path / f"{user_id}_embeddings.pkl"
                    if embeddings_file.exists():
                        with open(embeddings_file, 'rb') as f:
                            embeddings = pickle.load(f)
                    else:
                        embeddings = []
                    
                    # Create profile
                    profile = UserVoiceProfile(
                        user_id=profile_data['user_id'],
                        display_name=profile_data['display_name'],
                        embeddings=embeddings,
                        enrollment_samples=profile_data.get('enrollment_samples', len(embeddings)),
                        last_recognition=profile_data.get('last_recognition', 0.0),
                        recognition_count=profile_data.get('recognition_count', 0),
                        adaptation_enabled=profile_data.get('adaptation_enabled', True),
                        confidence_threshold=profile_data.get('confidence_threshold', 0.7),
                        created_date=profile_data.get('created_date', time.time()),
                        updated_date=profile_data.get('updated_date', time.time())
                    )
                    
                    self.user_profiles[user_id] = profile
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load profile {user_id}: {e}")
            
            self.logger.info(f"Loaded {len(self.user_profiles)} user profiles")
            
        except Exception as e:
            self.logger.error(f"Profile loading failed: {e}")


# Convenience functions
def create_voice_fingerprinting_system(config: VoiceFingerprintConfig = None) -> VoiceFingerprintingSystem:
    """Create voice fingerprinting system with configuration"""
    return VoiceFingerprintingSystem(config)

def quick_user_recognition(audio_data: np.ndarray, 
                          system: Optional[VoiceFingerprintingSystem] = None) -> RecognitionResult:
    """Quick user recognition function"""
    if system is None:
        system = create_voice_fingerprinting_system()
    
    return system.recognize_user(audio_data)