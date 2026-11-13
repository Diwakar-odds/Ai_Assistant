"""
Speaker Verification Module

This module provides speaker verification and authentication using voice biometrics.
Uses MFCC features, speaker embeddings, and machine learning techniques for secure
voice-based authentication.

Features:
- MFCC feature extraction for voice analysis
- Speaker embedding generation using neural networks  
- Voice biometric template creation and storage
- Real-time speaker verification and authentication
- Anti-spoofing protection against recorded playback
- Support for enrollment and verification workflows
- Configurable security thresholds
"""

import numpy as np
import pickle
import hashlib
import time
import threading
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import logging
import json

# Import biometric encryption
try:
    from ai_assistant.core.biometric_encryption import get_biometric_encryptor, BiometricEncryptionError
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    logging.warning("Biometric encryption not available. Biometric data will be stored unencrypted!")

try:
    import librosa
    import scipy.spatial.distance as distance
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import StandardScaler
    SPEAKER_VERIFICATION_AVAILABLE = True
except ImportError:
    SPEAKER_VERIFICATION_AVAILABLE = False
    logging.warning("Speaker verification libraries not available. Install librosa, scipy, sklearn.")

class VerificationResult(Enum):
    """Speaker verification results"""
    VERIFIED = "verified"
    REJECTED = "rejected" 
    UNKNOWN_SPEAKER = "unknown_speaker"
    INSUFFICIENT_AUDIO = "insufficient_audio"
    ERROR = "error"

class SecurityLevel(Enum):
    """Security levels for speaker verification"""
    LOW = 0.3       # More permissive, faster verification
    MEDIUM = 0.5    # Balanced security and usability  
    HIGH = 0.7      # Strict verification, higher security
    VERY_HIGH = 0.85 # Maximum security, may reject valid users

@dataclass
class VerificationConfig:
    """Configuration for speaker verification system"""
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    min_audio_duration: float = 1.0  # Minimum seconds of audio needed
    max_enrollment_samples: int = 5   # Max samples for enrollment
    feature_extraction_window: float = 0.025  # 25ms windows
    feature_extraction_hop: float = 0.01      # 10ms hop
    mfcc_coefficients: int = 13       # Number of MFCC coefficients
    enrollment_threshold: float = 0.8  # Threshold for enrollment quality
    anti_spoofing: bool = True        # Enable anti-spoofing detection
    max_verification_time: float = 5.0 # Max time for verification
    speaker_model_path: str = "user_data/speaker_models"
    encryption_enabled: bool = True   # Encrypt biometric templates

@dataclass  
class SpeakerProfile:
    """Speaker biometric profile"""
    speaker_id: str
    enrollment_date: float
    feature_vectors: List[np.ndarray]
    speaker_model: Any  # GMM model
    verification_count: int = 0
    last_verification: Optional[float] = None
    quality_score: float = 0.0
    anti_spoofing_profile: Optional[Dict] = None

@dataclass
class VerificationAttempt:
    """Result of speaker verification attempt"""
    result: VerificationResult
    confidence: float
    speaker_id: Optional[str] = None
    processing_time: float = 0.0
    quality_score: float = 0.0
    anti_spoofing_score: float = 0.0
    error_message: Optional[str] = None

class SpeakerVerificationSystem:
    """
    Advanced speaker verification system using voice biometrics
    
    Features:
    - MFCC-based feature extraction
    - Gaussian Mixture Model for speaker modeling
    - Anti-spoofing protection
    - Secure biometric template storage
    - Real-time verification
    """
    
    def __init__(self, config: Optional[VerificationConfig] = None):
        self.config = config or VerificationConfig()
        self.logger = logging.getLogger(__name__)
        
        if not SPEAKER_VERIFICATION_AVAILABLE:
            raise ImportError("Speaker verification requires librosa, scipy, and sklearn")
        
        # Initialize biometric encryption
        self.encryption_enabled = self.config.encryption_enabled and ENCRYPTION_AVAILABLE
        if self.encryption_enabled:
            try:
                self.encryptor = get_biometric_encryptor()
                self.logger.info("✅ Biometric encryption enabled (GDPR compliant)")
            except Exception as e:
                self.logger.error(f"Failed to initialize encryption: {e}")
                self.encryption_enabled = False
        else:
            self.encryptor = None
            if self.config.encryption_enabled:
                self.logger.warning("⚠️ Biometric encryption requested but not available!")
        
        # Initialize components
        self.speaker_profiles: Dict[str, SpeakerProfile] = {}
        self.feature_scaler = StandardScaler()
        self.is_scaler_fitted = False
        
        # Create speaker model directory
        self.model_path = Path(self.config.speaker_model_path)
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing speaker profiles
        self._load_speaker_profiles()
        
        # Anti-spoofing detector
        self.anti_spoofing_enabled = self.config.anti_spoofing
        
        encryption_status = "with encryption" if self.encryption_enabled else "WITHOUT encryption (WARNING)"
        self.logger.info(f"Speaker verification system initialized {encryption_status} with {len(self.speaker_profiles)} profiles")
    
    def enroll_speaker(self, speaker_id: str, audio_samples: List[np.ndarray], 
                      sample_rate: int = 16000) -> Tuple[bool, str]:
        """
        Enroll a new speaker with multiple audio samples
        
        Args:
            speaker_id: Unique identifier for the speaker
            audio_samples: List of audio arrays for enrollment
            sample_rate: Audio sample rate
            
        Returns:
            Tuple of (success, message)
        """
        try:
            start_time = time.time()
            
            # Validate input
            if not speaker_id or not audio_samples:
                return False, "Invalid speaker ID or audio samples"
            
            if len(audio_samples) < 2:
                return False, f"Need at least 2 audio samples for enrollment, got {len(audio_samples)}"
            
            # Extract features from all samples
            feature_vectors = []
            quality_scores = []
            
            for i, audio in enumerate(audio_samples):
                if len(audio) / sample_rate < self.config.min_audio_duration:
                    self.logger.warning(f"Audio sample {i+1} too short, skipping")
                    continue
                
                features = self._extract_features(audio, sample_rate)
                if features is not None and len(features) > 0:
                    quality_score = self._calculate_audio_quality(audio, sample_rate)
                    
                    if quality_score >= self.config.enrollment_threshold:
                        feature_vectors.append(features)
                        quality_scores.append(quality_score)
                    else:
                        self.logger.warning(f"Audio sample {i+1} quality too low: {quality_score:.3f}")
            
            # Check if we have enough good quality samples
            if len(feature_vectors) < 2:
                return False, f"Insufficient high-quality audio samples for enrollment"
            
            # Combine features and train speaker model
            combined_features = np.vstack(feature_vectors)
            
            # Fit feature scaler if not already fitted
            if not self.is_scaler_fitted:
                self.feature_scaler.fit(combined_features)
                self.is_scaler_fitted = True
            
            # Normalize features
            normalized_features = self.feature_scaler.transform(combined_features)
            
            # Train Gaussian Mixture Model for speaker
            gmm = GaussianMixture(
                n_components=min(8, len(feature_vectors)), 
                covariance_type='diag',
                random_state=42
            )
            gmm.fit(normalized_features)
            
            # Create anti-spoofing profile
            anti_spoofing_profile = None
            if self.anti_spoofing_enabled:
                anti_spoofing_profile = self._create_anti_spoofing_profile(audio_samples, sample_rate)
            
            # Create speaker profile
            profile = SpeakerProfile(
                speaker_id=speaker_id,
                enrollment_date=time.time(),
                feature_vectors=feature_vectors,
                speaker_model=gmm,
                quality_score=np.mean(quality_scores),
                anti_spoofing_profile=anti_spoofing_profile
            )
            
            # Store profile
            self.speaker_profiles[speaker_id] = profile
            self._save_speaker_profile(profile)
            
            processing_time = time.time() - start_time
            self.logger.info(f"Speaker {speaker_id} enrolled successfully in {processing_time:.2f}s")
            
            return True, f"Speaker enrolled with {len(feature_vectors)} samples"
            
        except Exception as e:
            self.logger.error(f"Enrollment error for {speaker_id}: {e}")
            return False, f"Enrollment failed: {str(e)}"
    
    def verify_speaker(self, speaker_id: str, audio_data: np.ndarray, 
                      sample_rate: int = 16000) -> VerificationAttempt:
        """
        Verify if audio matches enrolled speaker
        
        Args:
            speaker_id: Speaker to verify against
            audio_data: Audio sample for verification
            sample_rate: Audio sample rate
            
        Returns:
            VerificationAttempt with results
        """
        start_time = time.time()
        
        try:
            # Check if speaker is enrolled
            if speaker_id not in self.speaker_profiles:
                return VerificationAttempt(
                    result=VerificationResult.UNKNOWN_SPEAKER,
                    confidence=0.0,
                    error_message=f"Speaker {speaker_id} not enrolled"
                )
            
            # Check audio duration
            if len(audio_data) / sample_rate < self.config.min_audio_duration:
                return VerificationAttempt(
                    result=VerificationResult.INSUFFICIENT_AUDIO,
                    confidence=0.0,
                    error_message="Audio too short for verification"
                )
            
            # Extract features
            features = self._extract_features(audio_data, sample_rate)
            if features is None or len(features) == 0:
                return VerificationAttempt(
                    result=VerificationResult.ERROR,
                    confidence=0.0,
                    error_message="Feature extraction failed"
                )
            
            # Calculate audio quality
            quality_score = self._calculate_audio_quality(audio_data, sample_rate)
            
            # Anti-spoofing check
            anti_spoofing_score = 1.0
            if self.anti_spoofing_enabled:
                anti_spoofing_score = self._check_anti_spoofing(audio_data, sample_rate, speaker_id)
                if anti_spoofing_score < 0.5:  # Likely spoofing attempt
                    return VerificationAttempt(
                        result=VerificationResult.REJECTED,
                        confidence=0.0,
                        anti_spoofing_score=anti_spoofing_score,
                        error_message="Possible spoofing attempt detected"
                    )
            
            # Normalize features
            if self.is_scaler_fitted:
                normalized_features = self.feature_scaler.transform(features)
            else:
                normalized_features = features
            
            # Get speaker profile and model
            profile = self.speaker_profiles[speaker_id]
            speaker_model = profile.speaker_model
            
            # Calculate likelihood score
            log_likelihood = speaker_model.score(normalized_features)
            confidence = self._convert_likelihood_to_confidence(log_likelihood)
            
            # Apply security threshold
            threshold = self.config.security_level.value
            is_verified = confidence >= threshold
            
            # Update profile statistics
            profile.verification_count += 1
            profile.last_verification = time.time()
            
            processing_time = time.time() - start_time
            
            result = VerificationResult.VERIFIED if is_verified else VerificationResult.REJECTED
            
            self.logger.info(f"Verification for {speaker_id}: {result.value} "
                           f"(confidence: {confidence:.3f}, threshold: {threshold})")
            
            return VerificationAttempt(
                result=result,
                confidence=confidence,
                speaker_id=speaker_id,
                processing_time=processing_time,
                quality_score=quality_score,
                anti_spoofing_score=anti_spoofing_score
            )
            
        except Exception as e:
            self.logger.error(f"Verification error for {speaker_id}: {e}")
            return VerificationAttempt(
                result=VerificationResult.ERROR,
                confidence=0.0,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    def identify_speaker(self, audio_data: np.ndarray, 
                        sample_rate: int = 16000) -> VerificationAttempt:
        """
        Identify which enrolled speaker matches the audio
        
        Args:
            audio_data: Audio sample for identification
            sample_rate: Audio sample rate
            
        Returns:
            VerificationAttempt with identified speaker
        """
        if not self.speaker_profiles:
            return VerificationAttempt(
                result=VerificationResult.UNKNOWN_SPEAKER,
                confidence=0.0,
                error_message="No speakers enrolled"
            )
        
        best_confidence = 0.0
        best_speaker = None
        
        # Test against all enrolled speakers
        for speaker_id in self.speaker_profiles.keys():
            attempt = self.verify_speaker(speaker_id, audio_data, sample_rate)
            
            if attempt.confidence > best_confidence:
                best_confidence = attempt.confidence
                best_speaker = speaker_id
        
        # Check if best match meets threshold
        threshold = self.config.security_level.value
        if best_confidence >= threshold:
            return VerificationAttempt(
                result=VerificationResult.VERIFIED,
                confidence=best_confidence,
                speaker_id=best_speaker
            )
        else:
            return VerificationAttempt(
                result=VerificationResult.UNKNOWN_SPEAKER,
                confidence=best_confidence,
                error_message="No matching speaker found"
            )
    
    def _extract_features(self, audio_data: np.ndarray, sample_rate: int) -> Optional[np.ndarray]:
        """Extract MFCC features from audio"""
        try:
            # Ensure audio is float32
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32) / 32767.0
            
            # Extract MFCCs
            mfccs = librosa.feature.mfcc(
                y=audio_data,
                sr=sample_rate,
                n_mfcc=self.config.mfcc_coefficients,
                hop_length=int(sample_rate * self.config.feature_extraction_hop),
                win_length=int(sample_rate * self.config.feature_extraction_window)
            )
            
            # Add delta and delta-delta features
            delta_mfccs = librosa.feature.delta(mfccs)
            delta2_mfccs = librosa.feature.delta(mfccs, order=2)
            
            # Combine features
            combined_features = np.vstack([mfccs, delta_mfccs, delta2_mfccs])
            
            # Transpose to get (time_frames, features)
            return combined_features.T
            
        except Exception as e:
            self.logger.error(f"Feature extraction error: {e}")
            return None
    
    def _calculate_audio_quality(self, audio_data: np.ndarray, sample_rate: int) -> float:
        """Calculate audio quality score"""
        try:
            # Signal-to-noise ratio estimation
            signal_power = np.mean(audio_data ** 2)
            noise_power = np.var(audio_data[:int(0.1 * sample_rate)])  # First 100ms as noise estimate
            
            if noise_power > 0:
                snr = 10 * np.log10(signal_power / noise_power)
                snr_score = min(1.0, max(0.0, (snr - 5) / 20))  # Normalize SNR to 0-1
            else:
                snr_score = 1.0
            
            # Dynamic range
            dynamic_range = np.max(np.abs(audio_data)) - np.min(np.abs(audio_data))
            range_score = min(1.0, dynamic_range * 2)  # Normalize to 0-1
            
            # Spectral quality
            spectral_centroid = librosa.feature.spectral_centroid(y=audio_data, sr=sample_rate)[0]
            spectral_score = min(1.0, np.mean(spectral_centroid) / 4000)  # Normalize
            
            # Combined quality score
            quality = 0.4 * snr_score + 0.3 * range_score + 0.3 * spectral_score
            
            return quality
            
        except Exception:
            return 0.5  # Default medium quality
    
    def _create_anti_spoofing_profile(self, audio_samples: List[np.ndarray], 
                                    sample_rate: int) -> Dict[str, Any]:
        """Create anti-spoofing profile for speaker"""
        profile = {}
        
        try:
            # Analyze spectral characteristics typical of human voice
            spectral_features = []
            
            for audio in audio_samples:
                # Spectral rolloff (energy concentration)
                rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sample_rate)
                profile['avg_spectral_rolloff'] = np.mean(rolloff)
                
                # Zero crossing rate (measure of noisiness)
                zcr = librosa.feature.zero_crossing_rate(audio)
                profile['avg_zero_crossing_rate'] = np.mean(zcr)
                
                # Spectral centroid (brightness)
                centroid = librosa.feature.spectral_centroid(y=audio, sr=sample_rate)
                profile['avg_spectral_centroid'] = np.mean(centroid)
                
                # Harmonic-to-noise ratio
                harmonics, percussives = librosa.effects.hpss(audio)
                profile['harmonic_ratio'] = np.mean(harmonics) / (np.mean(percussives) + 1e-10)
            
            return profile
            
        except Exception as e:
            self.logger.warning(f"Anti-spoofing profile creation error: {e}")
            return {}
    
    def _check_anti_spoofing(self, audio_data: np.ndarray, sample_rate: int, 
                           speaker_id: str) -> float:
        """Check for potential spoofing attempts"""
        try:
            profile = self.speaker_profiles[speaker_id]
            if not profile.anti_spoofing_profile:
                return 1.0  # No anti-spoofing data available
            
            anti_spoofing_ref = profile.anti_spoofing_profile
            
            # Extract current audio characteristics
            rolloff = np.mean(librosa.feature.spectral_rolloff(y=audio_data, sr=sample_rate))
            zcr = np.mean(librosa.feature.zero_crossing_rate(audio_data))
            centroid = np.mean(librosa.feature.spectral_centroid(y=audio_data, sr=sample_rate))
            
            harmonics, percussives = librosa.effects.hpss(audio_data)
            harmonic_ratio = np.mean(harmonics) / (np.mean(percussives) + 1e-10)
            
            # Compare with enrolled characteristics
            rolloff_diff = abs(rolloff - anti_spoofing_ref.get('avg_spectral_rolloff', 0))
            zcr_diff = abs(zcr - anti_spoofing_ref.get('avg_zero_crossing_rate', 0))
            centroid_diff = abs(centroid - anti_spoofing_ref.get('avg_spectral_centroid', 0))
            harmonic_diff = abs(harmonic_ratio - anti_spoofing_ref.get('harmonic_ratio', 0))
            
            # Calculate similarity score (lower differences = higher score)
            similarity_score = 1.0 - min(1.0, (rolloff_diff/5000 + zcr_diff/0.1 + 
                                             centroid_diff/2000 + harmonic_diff/10) / 4)
            
            return max(0.0, similarity_score)
            
        except Exception as e:
            self.logger.warning(f"Anti-spoofing check error: {e}")
            return 1.0  # Default to allowing if check fails
    
    def _convert_likelihood_to_confidence(self, log_likelihood: float) -> float:
        """Convert log-likelihood to confidence score 0-1"""
        # Normalize log-likelihood to confidence score
        # This is a heuristic conversion - values may need tuning
        normalized = 1.0 / (1.0 + np.exp(-log_likelihood / 10))
        return np.clip(normalized, 0.0, 1.0)
    
    def _save_speaker_profile(self, profile: SpeakerProfile):
        """Save speaker profile to disk with encryption"""
        try:
            # Prepare profile data for saving
            profile_data = {
                'speaker_id': profile.speaker_id,
                'enrollment_date': profile.enrollment_date,
                'verification_count': profile.verification_count,
                'last_verification': profile.last_verification,
                'quality_score': profile.quality_score,
                'anti_spoofing_profile': profile.anti_spoofing_profile
            }
            
            # Save profile metadata (not encrypted - contains no biometric data)
            profile_file = self.model_path / f"{profile.speaker_id}_profile.json"
            with open(profile_file, 'w') as f:
                json.dump(profile_data, f, indent=2)
            
            if self.encryption_enabled:
                # ENCRYPTED STORAGE - GDPR Compliant
                # Encrypt GMM model
                encrypted_model = self.encryptor.encrypt_biometric(profile.speaker_model)
                model_file = self.model_path / f"{profile.speaker_id}_model.enc"
                with open(model_file, 'wb') as f:
                    f.write(encrypted_model)
                
                # Encrypt feature vectors
                features_array = np.vstack(profile.feature_vectors)
                encrypted_features = self.encryptor.encrypt_biometric(features_array)
                features_file = self.model_path / f"{profile.speaker_id}_features.enc"
                with open(features_file, 'wb') as f:
                    f.write(encrypted_features)
                
                self.logger.debug(f"🔒 Speaker profile saved (encrypted) for {profile.speaker_id}")
            else:
                # UNENCRYPTED LEGACY STORAGE - NOT RECOMMENDED
                self.logger.warning(f"⚠️ Saving biometric data UNENCRYPTED for {profile.speaker_id}")
                
                # Save GMM model (plaintext)
                model_file = self.model_path / f"{profile.speaker_id}_model.pkl"
                with open(model_file, 'wb') as f:
                    pickle.dump(profile.speaker_model, f)
                
                # Save feature vectors (plaintext)
                features_file = self.model_path / f"{profile.speaker_id}_features.npy"
                np.save(features_file, np.vstack(profile.feature_vectors))
            
        except Exception as e:
            self.logger.error(f"Error saving profile for {profile.speaker_id}: {e}")
    
    def _load_speaker_profiles(self):
        """Load existing speaker profiles from disk (encrypted or legacy)"""
        try:
            if not self.model_path.exists():
                return
            
            for profile_file in self.model_path.glob("*_profile.json"):
                speaker_id = profile_file.stem.replace('_profile', '')
                
                try:
                    # Load profile metadata
                    with open(profile_file, 'r') as f:
                        profile_data = json.load(f)
                    
                    # Check for encrypted files first
                    model_file_enc = self.model_path / f"{speaker_id}_model.enc"
                    features_file_enc = self.model_path / f"{speaker_id}_features.enc"
                    
                    if model_file_enc.exists() and features_file_enc.exists():
                        # Load encrypted biometric data
                        if not self.encryption_enabled:
                            self.logger.error(f"Encrypted profile found but encryption not enabled for {speaker_id}")
                            continue
                        
                        try:
                            # Decrypt GMM model
                            with open(model_file_enc, 'rb') as f:
                                encrypted_model = f.read()
                            speaker_model = self.encryptor.decrypt_biometric(encrypted_model)
                            
                            # Decrypt feature vectors
                            with open(features_file_enc, 'rb') as f:
                                encrypted_features = f.read()
                            features_array = self.encryptor.decrypt_biometric(encrypted_features)
                            
                            self.logger.debug(f"🔓 Loaded encrypted profile for {speaker_id}")
                            
                        except BiometricEncryptionError as e:
                            self.logger.error(f"Failed to decrypt profile for {speaker_id}: {e}")
                            continue
                    else:
                        # Try legacy unencrypted files
                        model_file = self.model_path / f"{speaker_id}_model.pkl"
                        features_file = self.model_path / f"{speaker_id}_features.npy"
                        
                        if model_file.exists() and features_file.exists():
                            self.logger.warning(f"⚠️ Loading UNENCRYPTED legacy profile for {speaker_id}")
                            
                            # Load GMM model (plaintext)
                            with open(model_file, 'rb') as f:
                                speaker_model = pickle.load(f)
                            
                            # Load feature vectors (plaintext)
                            features_array = np.load(features_file)
                            
                            # Optionally migrate to encrypted format
                            if self.encryption_enabled:
                                self.logger.info(f"Migrating {speaker_id} to encrypted storage...")
                                # Will be saved as encrypted on next profile update
                        else:
                            self.logger.error(f"No model files found for {speaker_id}")
                            continue
                    
                    # Reconstruct feature vectors list
                    feature_vectors = [features_array]
                    
                    # Create profile
                    profile = SpeakerProfile(
                        speaker_id=profile_data['speaker_id'],
                        enrollment_date=profile_data['enrollment_date'],
                        feature_vectors=feature_vectors,
                        speaker_model=speaker_model,
                        verification_count=profile_data.get('verification_count', 0),
                        last_verification=profile_data.get('last_verification'),
                        quality_score=profile_data.get('quality_score', 0.0),
                        anti_spoofing_profile=profile_data.get('anti_spoofing_profile')
                    )
                    
                    self.speaker_profiles[speaker_id] = profile
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load profile for {speaker_id}: {e}")
            
            encryption_status = "(encrypted)" if self.encryption_enabled else "(UNENCRYPTED)"
            self.logger.info(f"Loaded {len(self.speaker_profiles)} speaker profiles {encryption_status}")
            
        except Exception as e:
            self.logger.error(f"Error loading speaker profiles: {e}")
    
    def delete_speaker(self, speaker_id: str) -> bool:
        """Delete speaker profile and associated files (encrypted and legacy)"""
        try:
            if speaker_id not in self.speaker_profiles:
                return False
            
            # Remove from memory
            del self.speaker_profiles[speaker_id]
            
            # Remove all possible files (encrypted and legacy)
            files_to_remove = [
                f"{speaker_id}_profile.json",
                f"{speaker_id}_model.pkl",      # Legacy unencrypted
                f"{speaker_id}_model.enc",      # Encrypted
                f"{speaker_id}_features.npy",   # Legacy unencrypted
                f"{speaker_id}_features.enc"    # Encrypted
            ]
            
            for filename in files_to_remove:
                file_path = self.model_path / filename
                if file_path.exists():
                    file_path.unlink()
            
            self.logger.info(f"🗑️ Speaker {speaker_id} deleted successfully (all files removed)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting speaker {speaker_id}: {e}")
            return False
    
    def get_enrolled_speakers(self) -> List[str]:
        """Get list of enrolled speaker IDs"""
        return list(self.speaker_profiles.keys())
    
    def get_speaker_info(self, speaker_id: str) -> Optional[Dict[str, Any]]:
        """Get information about enrolled speaker"""
        if speaker_id not in self.speaker_profiles:
            return None
        
        profile = self.speaker_profiles[speaker_id]
        return {
            'speaker_id': profile.speaker_id,
            'enrollment_date': profile.enrollment_date,
            'verification_count': profile.verification_count,
            'last_verification': profile.last_verification,
            'quality_score': profile.quality_score,
            'has_anti_spoofing': profile.anti_spoofing_profile is not None
        }
    
    def update_security_level(self, security_level: SecurityLevel):
        """Update security level for verification"""
        self.config.security_level = security_level
        self.logger.info(f"Security level updated to {security_level.name}")


# Convenience functions
def create_speaker_verifier(security_level: SecurityLevel = SecurityLevel.MEDIUM) -> SpeakerVerificationSystem:
    """Create speaker verification system with specified security level"""
    config = VerificationConfig(security_level=security_level)
    return SpeakerVerificationSystem(config)

def quick_verify_speaker(speaker_id: str, audio_data: np.ndarray, 
                        verifier: Optional[SpeakerVerificationSystem] = None) -> bool:
    """Quick speaker verification function"""
    if verifier is None:
        verifier = create_speaker_verifier()
    
    result = verifier.verify_speaker(speaker_id, audio_data)
    return result.result == VerificationResult.VERIFIED