"""
Voice Activity Detection (VAD) Module

This module provides advanced voice activity detection capabilities using multiple
algorithms including WebRTC VAD, energy-based detection, and spectral analysis.

Features:
- WebRTC VAD integration for real-time detection
- Energy-based VAD with adaptive thresholds
- Spectral analysis for improved accuracy
- Multi-algorithm fusion for robust detection
- Configurable sensitivity and latency settings
"""

import numpy as np
try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False
import threading
import queue
import time
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

try:
    import librosa
    import scipy.signal
    ADVANCED_AUDIO_AVAILABLE = True
except ImportError:
    ADVANCED_AUDIO_AVAILABLE = False
    # logging.warning("Advanced audio processing libraries not available. Some VAD features disabled.")
    pass

class VADSensitivity(Enum):
    """Voice Activity Detection sensitivity levels"""
    VERY_LOW = 0      # Most aggressive, least sensitive
    LOW = 1           # Low sensitivity
    MEDIUM = 2        # Balanced detection
    HIGH = 3          # High sensitivity

class VADAlgorithm(Enum):
    """Available VAD algorithms"""
    WEBRTC = "webrtc"
    ENERGY = "energy"
    SPECTRAL = "spectral"
    FUSION = "fusion"

@dataclass
class VADConfig:
    """Voice Activity Detection configuration"""
    algorithm: VADAlgorithm = VADAlgorithm.FUSION
    sensitivity: VADSensitivity = VADSensitivity.MEDIUM
    sample_rate: int = 16000
    frame_duration_ms: int = 30  # WebRTC supports 10, 20, 30 ms
    energy_threshold: float = 0.01
    spectral_threshold: float = 0.5
    min_speech_duration_ms: int = 250  # Minimum speech duration to consider
    max_silence_duration_ms: int = 500  # Maximum silence before considering end of speech
    adaptive_threshold: bool = True
    noise_reduction: bool = True

@dataclass
class VADResult:
    """Voice Activity Detection result"""
    is_speech: bool
    confidence: float
    energy_level: float
    spectral_features: Optional[Dict[str, float]]
    timestamp: float
    algorithm_results: Dict[VADAlgorithm, bool]

class VoiceActivityDetector:
    """
    Advanced Voice Activity Detection system with multiple algorithms
    
    Features:
    - WebRTC VAD for real-time detection
    - Energy-based detection with adaptive thresholds  
    - Spectral analysis for improved accuracy
    - Algorithm fusion for robust detection
    - Background noise estimation and adaptation
    """
    
    def __init__(self, config: Optional[VADConfig] = None):
        self.config = config or VADConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self._init_webrtc_vad()
        self._init_energy_detector()
        self._init_spectral_detector()
        
        # State tracking
        self.background_noise_level = 0.0
        self.noise_samples = []
        self.max_noise_samples = 100
        self.speech_frames = 0
        self.silence_frames = 0
        self.is_calibrated = False
        
        # Threading
        self.processing_thread = None
        self.audio_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.is_running = False
        
        self.logger.info(f"VAD initialized with {self.config.algorithm.value} algorithm")
    
    def _init_webrtc_vad(self):
        """Initialize WebRTC VAD"""
        if not WEBRTCVAD_AVAILABLE:
            self.webrtc_vad = None
            self.webrtc_available = False
            self.logger.warning("WebRTC VAD not available due to missing library. Falling back to energy/spectral.")
            return

        try:
            self.webrtc_vad = webrtcvad.Vad(self.config.sensitivity.value)
            self.webrtc_available = True
            self.logger.info("WebRTC VAD initialized successfully")
        except Exception as e:
            self.webrtc_vad = None
            self.webrtc_available = False
            self.logger.warning(f"WebRTC VAD initialization failed: {e}")
    
    def _init_energy_detector(self):
        """Initialize energy-based detection"""
        self.energy_threshold = self.config.energy_threshold
        self.energy_history = []
        self.max_energy_history = 50
        self.adaptive_factor = 0.95  # For exponential moving average
        
    def _init_spectral_detector(self):
        """Initialize spectral analysis detector"""
        if not ADVANCED_AUDIO_AVAILABLE:
            self.spectral_available = False
            return
            
        self.spectral_available = True
        self.spectral_threshold = self.config.spectral_threshold
        
        # Spectral features for voice detection
        self.voice_freq_range = (85, 255)  # Human voice fundamental frequency range
        self.formant_ranges = [(300, 3400), (700, 2100)]  # Typical formant ranges
        
    def detect_voice_activity(self, audio_data: np.ndarray) -> VADResult:
        """
        Detect voice activity in audio data
        
        Args:
            audio_data: Audio samples (16-bit PCM, sample_rate defined in config)
            
        Returns:
            VADResult with detection results and confidence
        """
        timestamp = time.time()
        
        # Ensure audio data is in correct format
        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).astype(np.int16)
        
        # Calculate energy level
        energy_level = self._calculate_energy(audio_data)
        
        # Update background noise estimation
        self._update_noise_estimation(energy_level)
        
        # Run different VAD algorithms
        algorithm_results = {}
        
        # WebRTC VAD
        if self.webrtc_available and self.config.algorithm in [VADAlgorithm.WEBRTC, VADAlgorithm.FUSION]:
            algorithm_results[VADAlgorithm.WEBRTC] = self._webrtc_detect(audio_data)
        
        # Energy-based VAD
        if self.config.algorithm in [VADAlgorithm.ENERGY, VADAlgorithm.FUSION]:
            algorithm_results[VADAlgorithm.ENERGY] = self._energy_detect(energy_level)
        
        # Spectral VAD
        if self.spectral_available and self.config.algorithm in [VADAlgorithm.SPECTRAL, VADAlgorithm.FUSION]:
            spectral_result, spectral_features = self._spectral_detect(audio_data)
            algorithm_results[VADAlgorithm.SPECTRAL] = spectral_result
        else:
            spectral_features = None
        
        # Combine results based on algorithm choice
        is_speech, confidence = self._combine_results(algorithm_results)
        
        # Apply temporal filtering
        is_speech = self._temporal_filter(is_speech)
        
        return VADResult(
            is_speech=is_speech,
            confidence=confidence,
            energy_level=energy_level,
            spectral_features=spectral_features,
            timestamp=timestamp,
            algorithm_results=algorithm_results
        )
    
    def _calculate_energy(self, audio_data: np.ndarray) -> float:
        """Calculate RMS energy of audio frame"""
        if len(audio_data) == 0:
            return 0.0
        return np.sqrt(np.mean(audio_data.astype(float) ** 2))
    
    def _update_noise_estimation(self, energy_level: float):
        """Update background noise level estimation"""
        if not self.is_calibrated or len(self.noise_samples) < self.max_noise_samples // 2:
            # Still calibrating - assume early samples are noise
            self.noise_samples.append(energy_level)
            if len(self.noise_samples) > self.max_noise_samples:
                self.noise_samples.pop(0)
                
            self.background_noise_level = np.mean(self.noise_samples) if self.noise_samples else 0.0
            
            if len(self.noise_samples) >= self.max_noise_samples // 2:
                self.is_calibrated = True
                self.logger.info(f"VAD calibrated. Background noise level: {self.background_noise_level:.6f}")
        
        elif self.config.adaptive_threshold:
            # Adaptive update during operation
            if energy_level < self.background_noise_level * 2:  # Likely noise
                self.background_noise_level = (self.adaptive_factor * self.background_noise_level + 
                                              (1 - self.adaptive_factor) * energy_level)
    
    def _webrtc_detect(self, audio_data: np.ndarray) -> bool:
        """WebRTC VAD detection"""
        if not self.webrtc_available:
            return False
            
        try:
            # WebRTC VAD expects specific frame sizes
            frame_size = int(self.config.sample_rate * self.config.frame_duration_ms / 1000)
            
            if len(audio_data) < frame_size:
                # Pad with zeros if frame is too short
                padded_data = np.zeros(frame_size, dtype=np.int16)
                padded_data[:len(audio_data)] = audio_data
                audio_data = padded_data
            elif len(audio_data) > frame_size:
                # Truncate if frame is too long
                audio_data = audio_data[:frame_size]
            
            return self.webrtc_vad.is_speech(audio_data.tobytes(), self.config.sample_rate)
        except Exception as e:
            self.logger.warning(f"WebRTC VAD error: {e}")
            return False
    
    def _energy_detect(self, energy_level: float) -> bool:
        """Energy-based VAD detection"""
        if not self.is_calibrated:
            return False
            
        # Adaptive threshold based on background noise
        threshold = max(self.energy_threshold, 
                       self.background_noise_level * 3)  # At least 3x noise level
        
        return energy_level > threshold
    
    def _spectral_detect(self, audio_data: np.ndarray) -> Tuple[bool, Dict[str, float]]:
        """Spectral analysis-based VAD detection"""
        if not self.spectral_available:
            return False, {}
            
        try:
            # Convert to float for spectral analysis
            audio_float = audio_data.astype(float) / 32767.0
            
            # Compute spectral features
            spectral_features = self._extract_spectral_features(audio_float)
            
            # Voice detection based on spectral characteristics
            is_voice = (
                spectral_features['spectral_centroid'] > 500 and  # Voice-like spectral center
                spectral_features['spectral_rolloff'] > 2000 and  # Energy concentration
                spectral_features['zero_crossing_rate'] < 0.3 and  # Not too noisy
                spectral_features['mfcc_variance'] > 0.1  # Spectral variation
            )
            
            return is_voice, spectral_features
            
        except Exception as e:
            self.logger.warning(f"Spectral detection error: {e}")
            return False, {}
    
    def _extract_spectral_features(self, audio_data: np.ndarray) -> Dict[str, float]:
        """Extract spectral features for voice detection"""
        features = {}
        
        try:
            # Spectral centroid (brightness)
            spectral_centroid = librosa.feature.spectral_centroid(y=audio_data, sr=self.config.sample_rate)[0]
            features['spectral_centroid'] = np.mean(spectral_centroid) if len(spectral_centroid) > 0 else 0
            
            # Spectral rolloff
            spectral_rolloff = librosa.feature.spectral_rolloff(y=audio_data, sr=self.config.sample_rate)[0]
            features['spectral_rolloff'] = np.mean(spectral_rolloff) if len(spectral_rolloff) > 0 else 0
            
            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(audio_data)[0]
            features['zero_crossing_rate'] = np.mean(zcr) if len(zcr) > 0 else 0
            
            # MFCC variance (spectral shape variation)
            mfccs = librosa.feature.mfcc(y=audio_data, sr=self.config.sample_rate, n_mfcc=13)
            features['mfcc_variance'] = np.var(mfccs) if mfccs.size > 0 else 0
            
            # Spectral bandwidth
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=audio_data, sr=self.config.sample_rate)[0]
            features['spectral_bandwidth'] = np.mean(spectral_bandwidth) if len(spectral_bandwidth) > 0 else 0
            
        except Exception as e:
            self.logger.warning(f"Feature extraction error: {e}")
            # Return default values
            features = {
                'spectral_centroid': 0,
                'spectral_rolloff': 0,
                'zero_crossing_rate': 0,
                'mfcc_variance': 0,
                'spectral_bandwidth': 0
            }
        
        return features
    
    def _combine_results(self, algorithm_results: Dict[VADAlgorithm, bool]) -> Tuple[bool, float]:
        """Combine results from multiple VAD algorithms"""
        if not algorithm_results:
            return False, 0.0
        
        if self.config.algorithm == VADAlgorithm.FUSION:
            # Weighted voting
            weights = {
                VADAlgorithm.WEBRTC: 0.4,
                VADAlgorithm.ENERGY: 0.3,
                VADAlgorithm.SPECTRAL: 0.3
            }
            
            total_weight = 0
            weighted_sum = 0
            
            for algorithm, result in algorithm_results.items():
                weight = weights.get(algorithm, 0.33)
                weighted_sum += weight * (1 if result else 0)
                total_weight += weight
            
            confidence = weighted_sum / total_weight if total_weight > 0 else 0
            is_speech = confidence > 0.5
            
            return is_speech, confidence
        
        else:
            # Single algorithm result
            algorithm = self.config.algorithm
            result = algorithm_results.get(algorithm, False)
            confidence = 1.0 if result else 0.0
            
            return result, confidence
    
    def _temporal_filter(self, is_speech: bool) -> bool:
        """Apply temporal filtering to reduce false positives/negatives"""
        if is_speech:
            self.speech_frames += 1
            self.silence_frames = 0
        else:
            self.silence_frames += 1
            if self.silence_frames > 0:
                self.speech_frames = max(0, self.speech_frames - 1)
        
        # Require minimum consecutive speech frames
        min_speech_frames = (self.config.min_speech_duration_ms // 
                           self.config.frame_duration_ms)
        
        # Allow maximum silence frames before ending speech
        max_silence_frames = (self.config.max_silence_duration_ms // 
                            self.config.frame_duration_ms)
        
        # Return true if we have enough speech frames and not too much silence
        return (self.speech_frames >= min_speech_frames and 
                self.silence_frames <= max_silence_frames)
    
    def start_continuous_detection(self, audio_callback=None):
        """Start continuous VAD processing in background thread"""
        if self.is_running:
            self.logger.warning("VAD already running")
            return
        
        self.is_running = True
        self.processing_thread = threading.Thread(
            target=self._continuous_processing_loop,
            args=(audio_callback,),
            daemon=True
        )
        self.processing_thread.start()
        self.logger.info("Continuous VAD processing started")
    
    def stop_continuous_detection(self):
        """Stop continuous VAD processing"""
        self.is_running = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)
        self.logger.info("Continuous VAD processing stopped")
    
    def _continuous_processing_loop(self, audio_callback):
        """Continuous processing loop for real-time VAD"""
        while self.is_running:
            try:
                # Get audio data from queue
                audio_data = self.audio_queue.get(timeout=0.1)
                
                # Process VAD
                result = self.detect_voice_activity(audio_data)
                
                # Put result in result queue
                self.result_queue.put(result)
                
                # Call callback if provided
                if audio_callback:
                    audio_callback(result)
                    
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"VAD processing error: {e}")
    
    def add_audio_data(self, audio_data: np.ndarray):
        """Add audio data for continuous processing"""
        if self.is_running:
            try:
                self.audio_queue.put_nowait(audio_data)
            except queue.Full:
                self.logger.warning("VAD audio queue full, dropping frame")
    
    def get_latest_result(self) -> Optional[VADResult]:
        """Get latest VAD result from processing"""
        try:
            return self.result_queue.get_nowait()
        except queue.Empty:
            return None
    
    def calibrate(self, noise_audio: np.ndarray):
        """Manually calibrate with noise sample"""
        noise_energy = self._calculate_energy(noise_audio)
        self.background_noise_level = noise_energy
        self.is_calibrated = True
        self.logger.info(f"VAD manually calibrated. Noise level: {noise_energy:.6f}")
    
    def reset_calibration(self):
        """Reset calibration to start fresh"""
        self.background_noise_level = 0.0
        self.noise_samples = []
        self.is_calibrated = False
        self.speech_frames = 0
        self.silence_frames = 0
        self.logger.info("VAD calibration reset")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current VAD status and statistics"""
        return {
            'algorithm': self.config.algorithm.value,
            'sensitivity': self.config.sensitivity.value,
            'is_calibrated': self.is_calibrated,
            'background_noise_level': self.background_noise_level,
            'webrtc_available': self.webrtc_available,
            'spectral_available': self.spectral_available,
            'is_running': self.is_running,
            'speech_frames': self.speech_frames,
            'silence_frames': self.silence_frames
        }


class VADProcessor:
    """
    High-level VAD processor for easy integration
    
    Provides simplified interface for common VAD operations
    """
    
    def __init__(self, sensitivity: VADSensitivity = VADSensitivity.MEDIUM):
        self.config = VADConfig(
            algorithm=VADAlgorithm.FUSION,
            sensitivity=sensitivity,
            adaptive_threshold=True,
            noise_reduction=True
        )
        self.vad = VoiceActivityDetector(self.config)
        self.logger = logging.getLogger(__name__)
    
    def is_speech_detected(self, audio_data: np.ndarray) -> bool:
        """Simple speech detection interface"""
        result = self.vad.detect_voice_activity(audio_data)
        return result.is_speech
    
    def process_audio_stream(self, audio_stream, callback=None):
        """Process continuous audio stream with callback"""
        self.vad.start_continuous_detection(callback)
        
        for audio_chunk in audio_stream:
            self.vad.add_audio_data(audio_chunk)
            
            # Get and handle results
            result = self.vad.get_latest_result()
            if result and callback:
                callback(result)
    
    def calibrate_with_silence(self, duration_seconds: float = 2.0):
        """Auto-calibrate by recording silence"""
        self.logger.info(f"Calibrating VAD with {duration_seconds}s of silence...")
        
        # This would typically record audio from microphone
        # For now, we'll reset calibration to let it auto-calibrate
        self.vad.reset_calibration()
        
        self.logger.info("VAD calibration reset - will auto-calibrate during use")


# Convenience functions for easy integration
def create_vad_detector(sensitivity: VADSensitivity = VADSensitivity.MEDIUM, 
                       algorithm: VADAlgorithm = VADAlgorithm.FUSION) -> VoiceActivityDetector:
    """Create a VAD detector with specified settings"""
    config = VADConfig(algorithm=algorithm, sensitivity=sensitivity)
    return VoiceActivityDetector(config)

def detect_voice_activity(audio_data: np.ndarray, 
                         sensitivity: VADSensitivity = VADSensitivity.MEDIUM) -> bool:
    """Quick voice activity detection for audio data"""
    detector = create_vad_detector(sensitivity)
    result = detector.detect_voice_activity(audio_data)
    return result.is_speech