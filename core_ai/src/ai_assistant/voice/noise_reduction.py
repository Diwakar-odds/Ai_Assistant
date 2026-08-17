"""
Noise Reduction Preprocessing Module

This module provides advanced noise reduction and audio preprocessing capabilities
for improving speech recognition accuracy in noisy environments.

Features:
- Spectral subtraction for stationary noise removal
- Wiener filtering for speech enhancement
- Adaptive noise estimation and tracking
- Multi-band noise reduction
- Real-time processing capabilities
- Configurable noise reduction levels
- Quality assessment and validation
"""

import numpy as np
import threading
import queue
import time
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import logging

try:
    import scipy.signal
    import scipy.fftpack
    from scipy.ndimage import uniform_filter1d
    NOISE_REDUCTION_AVAILABLE = True
except ImportError:
    NOISE_REDUCTION_AVAILABLE = False
    logging.warning("Noise reduction requires scipy. Install scipy for full functionality.")

try:
    import librosa
    import noisereduce as nr
    ADVANCED_NOISE_REDUCTION_AVAILABLE = True
except ImportError:
    ADVANCED_NOISE_REDUCTION_AVAILABLE = False
    logging.warning("Advanced noise reduction features require librosa and noisereduce")

class NoiseReductionMethod(Enum):
    """Available noise reduction methods"""
    SPECTRAL_SUBTRACTION = "spectral_subtraction"
    WIENER_FILTER = "wiener_filter"
    ADAPTIVE_FILTER = "adaptive_filter"
    MULTI_BAND = "multi_band"
    HYBRID = "hybrid"

class NoiseLevel(Enum):
    """Noise reduction intensity levels"""
    LIGHT = 0.3      # Minimal processing, preserve audio quality
    MODERATE = 0.5   # Balanced noise reduction
    AGGRESSIVE = 0.7 # Strong noise reduction
    MAXIMUM = 0.9    # Maximum noise reduction

@dataclass
class NoiseReductionConfig:
    """Configuration for noise reduction system"""
    method: NoiseReductionMethod = NoiseReductionMethod.HYBRID
    noise_level: NoiseLevel = NoiseLevel.MODERATE
    sample_rate: int = 16000
    frame_size: int = 1024
    hop_length: int = 512
    noise_estimation_duration: float = 1.0  # Seconds for noise estimation
    alpha: float = 2.0                      # Over-subtraction factor
    beta: float = 0.01                      # Noise floor factor
    smoothing_factor: float = 0.98          # Spectral smoothing
    enable_vad_gating: bool = True          # Use VAD to gate noise reduction
    preserve_speech_bands: bool = True       # Protect speech frequency bands
    adaptive_parameters: bool = True        # Adapt parameters based on noise level
    max_processing_delay: float = 0.1       # Maximum processing delay in seconds

@dataclass
class NoiseProfile:
    """Noise characteristics profile"""
    noise_spectrum: np.ndarray
    noise_power: float
    dominant_frequencies: List[float]
    noise_type: str  # "stationary", "non-stationary", "impulsive"
    estimation_confidence: float
    update_time: float

@dataclass
class AudioQualityMetrics:
    """Audio quality assessment metrics"""
    snr_estimate: float
    spectral_distortion: float
    speech_preservation: float
    noise_reduction_amount: float
    processing_artifacts: float

class SpectralSubtractionProcessor:
    """
    Spectral subtraction noise reduction processor
    
    Implements classic spectral subtraction algorithm with improvements:
    - Over-subtraction for better noise removal
    - Spectral floor to prevent musical noise
    - Smoothing to reduce artifacts
    """
    
    def __init__(self, config: NoiseReductionConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize noise profile
        self.noise_profile: Optional[NoiseProfile] = None
        self.noise_estimation_frames = []
        self.is_noise_estimated = False
        
        # Spectral smoothing
        self.prev_magnitude = None
        
    def estimate_noise(self, audio_data: np.ndarray) -> bool:
        """Estimate noise profile from audio data"""
        try:
            # Convert to frequency domain
            stft = scipy.signal.stft(
                audio_data,
                nperseg=self.config.frame_size,
                noverlap=self.config.frame_size - self.config.hop_length
            )[2]
            
            magnitude = np.abs(stft)
            
            # Estimate noise as minimum statistics across time
            noise_spectrum = np.percentile(magnitude, 10, axis=1)  # 10th percentile
            noise_power = np.mean(noise_spectrum ** 2)
            
            # Find dominant noise frequencies
            freqs = np.fft.fftfreq(self.config.frame_size, 1/self.config.sample_rate)
            dominant_freq_indices = np.argsort(noise_spectrum)[-5:]
            dominant_frequencies = [abs(freqs[i]) for i in dominant_freq_indices]
            
            # Classify noise type (simplified)
            variance = np.var(magnitude, axis=1)
            avg_variance = np.mean(variance)
            
            if avg_variance < 0.1:
                noise_type = "stationary"
            elif avg_variance < 0.5:
                noise_type = "non-stationary"
            else:
                noise_type = "impulsive"
            
            self.noise_profile = NoiseProfile(
                noise_spectrum=noise_spectrum,
                noise_power=noise_power,
                dominant_frequencies=dominant_frequencies,
                noise_type=noise_type,
                estimation_confidence=0.8,  # Simplified confidence
                update_time=time.time()
            )
            
            self.is_noise_estimated = True
            self.logger.info(f"Noise profile estimated: {noise_type} noise, power: {noise_power:.6f}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Noise estimation failed: {e}")
            return False
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply spectral subtraction noise reduction"""
        if not self.is_noise_estimated:
            self.logger.warning("Noise not estimated, skipping noise reduction")
            return audio_data
        
        try:
            # Short-time Fourier transform
            f, t, stft = scipy.signal.stft(
                audio_data,
                nperseg=self.config.frame_size,
                noverlap=self.config.frame_size - self.config.hop_length
            )
            
            magnitude = np.abs(stft)
            phase = np.angle(stft)
            
            # Spectral subtraction
            noise_spectrum = self.noise_profile.noise_spectrum.reshape(-1, 1)
            
            # Calculate gain using over-subtraction
            gain = 1 - (self.config.alpha * noise_spectrum) / (magnitude + 1e-10)
            
            # Apply noise floor
            gain = np.maximum(gain, self.config.beta)
            
            # Spectral smoothing
            if self.prev_magnitude is not None:
                smooth_factor = self.config.smoothing_factor
                magnitude_smoothed = (smooth_factor * self.prev_magnitude + 
                                    (1 - smooth_factor) * magnitude)
            else:
                magnitude_smoothed = magnitude
            
            self.prev_magnitude = magnitude_smoothed
            
            # Apply gain
            enhanced_magnitude = gain * magnitude_smoothed
            
            # Reconstruct signal
            enhanced_stft = enhanced_magnitude * np.exp(1j * phase)
            
            # Inverse STFT
            _, enhanced_audio = scipy.signal.istft(
                enhanced_stft,
                nperseg=self.config.frame_size,
                noverlap=self.config.frame_size - self.config.hop_length
            )
            
            return enhanced_audio.astype(audio_data.dtype)
            
        except Exception as e:
            self.logger.error(f"Spectral subtraction failed: {e}")
            return audio_data

class WienerFilterProcessor:
    """
    Wiener filter noise reduction processor
    
    Implements Wiener filtering for speech enhancement based on
    signal-to-noise ratio estimation
    """
    
    def __init__(self, config: NoiseReductionConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.noise_psd = None
        self.speech_psd = None
        self.is_initialized = False
        
    def initialize(self, noise_sample: np.ndarray, speech_sample: Optional[np.ndarray] = None):
        """Initialize Wiener filter with noise and optional speech samples"""
        try:
            # Estimate noise power spectral density
            f, noise_psd = scipy.signal.welch(
                noise_sample,
                fs=self.config.sample_rate,
                nperseg=self.config.frame_size
            )
            self.noise_psd = noise_psd
            
            # Estimate speech PSD if available, otherwise use generic model
            if speech_sample is not None:
                f, speech_psd = scipy.signal.welch(
                    speech_sample,
                    fs=self.config.sample_rate,
                    nperseg=self.config.frame_size
                )
                self.speech_psd = speech_psd
            else:
                # Generic speech model (emphasis on voice frequencies)
                freqs = f
                speech_model = np.ones_like(freqs)
                
                # Emphasize speech frequencies (85 Hz - 4 kHz)
                speech_freqs = (freqs >= 85) & (freqs <= 4000)
                speech_model[speech_freqs] *= 3.0
                
                # Fundamental frequency range (85-255 Hz)
                fundamental_freqs = (freqs >= 85) & (freqs <= 255)
                speech_model[fundamental_freqs] *= 2.0
                
                self.speech_psd = speech_model * np.mean(noise_psd) * 10
            
            self.is_initialized = True
            self.logger.info("Wiener filter initialized")
            
        except Exception as e:
            self.logger.error(f"Wiener filter initialization failed: {e}")
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply Wiener filtering"""
        if not self.is_initialized:
            self.logger.warning("Wiener filter not initialized, skipping")
            return audio_data
        
        try:
            # Compute noisy signal PSD
            f, noisy_psd = scipy.signal.welch(
                audio_data,
                fs=self.config.sample_rate,
                nperseg=self.config.frame_size
            )
            
            # Calculate Wiener gain
            snr = self.speech_psd / (self.noise_psd + 1e-10)
            wiener_gain = snr / (1 + snr)
            
            # Apply noise level adjustment
            reduction_factor = self.config.noise_level.value
            wiener_gain = wiener_gain ** reduction_factor
            
            # Convert to time-domain filter
            # For simplicity, apply frequency-domain multiplication
            # In practice, would use overlap-add for real-time processing
            
            # FFT of input signal
            fft_input = np.fft.fft(audio_data, n=len(audio_data))
            
            # Interpolate gain to match FFT size
            freqs_fft = np.fft.fftfreq(len(audio_data), 1/self.config.sample_rate)
            gain_interp = np.interp(np.abs(freqs_fft), f, wiener_gain)
            
            # Apply symmetric gain for negative frequencies
            gain_full = np.concatenate([gain_interp[:len(audio_data)//2], 
                                      gain_interp[len(audio_data)//2-1::-1]])
            
            # Apply gain and inverse FFT
            enhanced_fft = fft_input * gain_full
            enhanced_audio = np.real(np.fft.ifft(enhanced_fft))
            
            return enhanced_audio.astype(audio_data.dtype)
            
        except Exception as e:
            self.logger.error(f"Wiener filtering failed: {e}")
            return audio_data

class AdaptiveNoiseReducer:
    """
    Adaptive noise reduction that adjusts parameters based on 
    current noise conditions and signal characteristics
    """
    
    def __init__(self, config: NoiseReductionConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize processors
        self.spectral_processor = SpectralSubtractionProcessor(config)
        self.wiener_processor = WienerFilterProcessor(config)
        
        # Adaptive parameters
        self.current_snr = 10.0  # Initial SNR estimate
        self.adaptation_rate = 0.1
        
    def process(self, audio_data: np.ndarray, 
               noise_sample: Optional[np.ndarray] = None) -> np.ndarray:
        """Process audio with adaptive noise reduction"""
        try:
            # Estimate current SNR
            current_snr = self._estimate_snr(audio_data)
            
            # Update SNR estimate with smoothing
            self.current_snr = (1 - self.adaptation_rate) * self.current_snr + \
                              self.adaptation_rate * current_snr
            
            # Adapt noise reduction parameters based on SNR
            if self.current_snr > 15:  # Clean signal
                reduction_method = NoiseReductionMethod.WIENER_FILTER
                intensity = 0.3
            elif self.current_snr > 5:  # Moderate noise
                reduction_method = NoiseReductionMethod.SPECTRAL_SUBTRACTION
                intensity = 0.5
            else:  # Heavy noise
                reduction_method = NoiseReductionMethod.HYBRID
                intensity = 0.8
            
            # Apply appropriate noise reduction
            if reduction_method == NoiseReductionMethod.SPECTRAL_SUBTRACTION:
                if not self.spectral_processor.is_noise_estimated and noise_sample is not None:
                    self.spectral_processor.estimate_noise(noise_sample)
                return self.spectral_processor.process(audio_data)
            
            elif reduction_method == NoiseReductionMethod.WIENER_FILTER:
                if not self.wiener_processor.is_initialized and noise_sample is not None:
                    self.wiener_processor.initialize(noise_sample)
                return self.wiener_processor.process(audio_data)
            
            elif reduction_method == NoiseReductionMethod.HYBRID:
                # Apply both methods sequentially
                if noise_sample is not None:
                    if not self.spectral_processor.is_noise_estimated:
                        self.spectral_processor.estimate_noise(noise_sample)
                    if not self.wiener_processor.is_initialized:
                        self.wiener_processor.initialize(noise_sample)
                
                # First pass: spectral subtraction
                enhanced = self.spectral_processor.process(audio_data)
                # Second pass: Wiener filtering (lighter)
                final = self.wiener_processor.process(enhanced)
                return final
            
            else:
                return audio_data
                
        except Exception as e:
            self.logger.error(f"Adaptive noise reduction failed: {e}")
            return audio_data
    
    def _estimate_snr(self, audio_data: np.ndarray) -> float:
        """Estimate signal-to-noise ratio"""
        try:
            # Simple SNR estimation based on signal statistics
            signal_power = np.mean(audio_data ** 2)
            
            # Estimate noise as minimum energy in short segments
            segment_length = len(audio_data) // 10
            segments = np.array_split(audio_data, 10)
            segment_powers = [np.mean(seg ** 2) for seg in segments]
            noise_power = np.min(segment_powers)
            
            if noise_power > 0:
                snr_linear = signal_power / noise_power
                snr_db = 10 * np.log10(snr_linear)
                return max(0, min(30, snr_db))  # Clip to reasonable range
            else:
                return 20.0  # Default high SNR
                
        except Exception:
            return 10.0  # Default moderate SNR

class NoiseReductionSystem:
    """
    Complete noise reduction system with multiple algorithms
    and real-time processing capabilities
    """
    
    def __init__(self, config: Optional[NoiseReductionConfig] = None):
        self.config = config or NoiseReductionConfig()
        self.logger = logging.getLogger(__name__)
        
        if not NOISE_REDUCTION_AVAILABLE:
            raise ImportError("Noise reduction requires scipy")
        
        # Initialize processors based on method
        self.processors = {}
        self._initialize_processors()
        
        # Quality assessment
        self.quality_metrics = AudioQualityMetrics(0, 0, 0, 0, 0)
        
        # Real-time processing
        self.audio_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.is_processing = False
        self.processing_thread = None
        
        self.logger.info(f"Noise reduction system initialized with {self.config.method.value}")
    
    def _initialize_processors(self):
        """Initialize noise reduction processors"""
        try:
            if self.config.method in [NoiseReductionMethod.SPECTRAL_SUBTRACTION, 
                                    NoiseReductionMethod.HYBRID]:
                self.processors['spectral'] = SpectralSubtractionProcessor(self.config)
            
            if self.config.method in [NoiseReductionMethod.WIENER_FILTER,
                                    NoiseReductionMethod.HYBRID]:
                self.processors['wiener'] = WienerFilterProcessor(self.config)
            
            if self.config.method == NoiseReductionMethod.ADAPTIVE_FILTER:
                self.processors['adaptive'] = AdaptiveNoiseReducer(self.config)
            
        except Exception as e:
            self.logger.error(f"Processor initialization failed: {e}")
    
    def reduce_noise(self, audio_data: np.ndarray, 
                    noise_sample: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Apply noise reduction to audio data
        
        Args:
            audio_data: Input audio signal
            noise_sample: Optional noise sample for adaptation
            
        Returns:
            Enhanced audio signal
        """
        try:
            start_time = time.time()
            
            # Validate input
            if len(audio_data) == 0:
                return audio_data
            
            # Ensure float32 format
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
                if np.max(np.abs(audio_data)) > 1.0:
                    audio_data = audio_data / 32767.0
            
            # Apply noise reduction based on method
            if self.config.method == NoiseReductionMethod.SPECTRAL_SUBTRACTION:
                enhanced = self._apply_spectral_subtraction(audio_data, noise_sample)
            
            elif self.config.method == NoiseReductionMethod.WIENER_FILTER:
                enhanced = self._apply_wiener_filter(audio_data, noise_sample)
            
            elif self.config.method == NoiseReductionMethod.ADAPTIVE_FILTER:
                enhanced = self._apply_adaptive_filter(audio_data, noise_sample)
            
            elif self.config.method == NoiseReductionMethod.HYBRID:
                enhanced = self._apply_hybrid_method(audio_data, noise_sample)
            
            else:
                enhanced = audio_data
            
            # Calculate quality metrics
            processing_time = time.time() - start_time
            self.quality_metrics = self._calculate_quality_metrics(
                audio_data, enhanced, processing_time)
            
            self.logger.debug(f"Noise reduction completed in {processing_time:.3f}s")
            
            return enhanced
            
        except Exception as e:
            self.logger.error(f"Noise reduction failed: {e}")
            return audio_data
    
    def _apply_spectral_subtraction(self, audio_data: np.ndarray, 
                                  noise_sample: Optional[np.ndarray]) -> np.ndarray:
        """Apply spectral subtraction"""
        processor = self.processors.get('spectral')
        if not processor:
            return audio_data
        
        if noise_sample is not None and not processor.is_noise_estimated:
            processor.estimate_noise(noise_sample)
        
        return processor.process(audio_data)
    
    def _apply_wiener_filter(self, audio_data: np.ndarray,
                           noise_sample: Optional[np.ndarray]) -> np.ndarray:
        """Apply Wiener filter"""
        processor = self.processors.get('wiener')
        if not processor:
            return audio_data
        
        if noise_sample is not None and not processor.is_initialized:
            processor.initialize(noise_sample)
        
        return processor.process(audio_data)
    
    def _apply_adaptive_filter(self, audio_data: np.ndarray,
                             noise_sample: Optional[np.ndarray]) -> np.ndarray:
        """Apply adaptive filter"""
        processor = self.processors.get('adaptive')
        if not processor:
            return audio_data
        
        return processor.process(audio_data, noise_sample)
    
    def _apply_hybrid_method(self, audio_data: np.ndarray,
                           noise_sample: Optional[np.ndarray]) -> np.ndarray:
        """Apply hybrid noise reduction method"""
        # Apply multiple methods in sequence
        enhanced = audio_data
        
        # First: Spectral subtraction for stationary noise
        spectral_processor = self.processors.get('spectral')
        if spectral_processor:
            if noise_sample is not None and not spectral_processor.is_noise_estimated:
                spectral_processor.estimate_noise(noise_sample)
            enhanced = spectral_processor.process(enhanced)
        
        # Second: Light Wiener filtering for refinement
        wiener_processor = self.processors.get('wiener')
        if wiener_processor:
            if noise_sample is not None and not wiener_processor.is_initialized:
                wiener_processor.initialize(noise_sample)
            enhanced = wiener_processor.process(enhanced)
        
        return enhanced
    
    def _calculate_quality_metrics(self, original: np.ndarray, 
                                 enhanced: np.ndarray, 
                                 processing_time: float) -> AudioQualityMetrics:
        """Calculate audio quality metrics"""
        try:
            # SNR improvement estimation
            original_power = np.mean(original ** 2)
            enhanced_power = np.mean(enhanced ** 2)
            
            # Estimate noise reduction (simplified)
            noise_reduction = max(0, 1 - enhanced_power / (original_power + 1e-10))
            
            # Spectral distortion (simplified)
            orig_fft = np.abs(np.fft.fft(original))
            enh_fft = np.abs(np.fft.fft(enhanced))
            spectral_dist = np.mean((orig_fft - enh_fft) ** 2) / np.mean(orig_fft ** 2)
            
            # Speech preservation (energy in speech bands)
            sr = self.config.sample_rate
            freqs = np.fft.fftfreq(len(original), 1/sr)
            speech_mask = (np.abs(freqs) >= 85) & (np.abs(freqs) <= 4000)
            
            speech_orig = np.mean(orig_fft[speech_mask])
            speech_enh = np.mean(enh_fft[speech_mask])
            speech_preservation = speech_enh / (speech_orig + 1e-10)
            
            return AudioQualityMetrics(
                snr_estimate=10 * np.log10(enhanced_power / (original_power - enhanced_power + 1e-10)),
                spectral_distortion=spectral_dist,
                speech_preservation=min(1.0, speech_preservation),
                noise_reduction_amount=noise_reduction,
                processing_artifacts=max(0, spectral_dist - 0.1)  # Simplified metric
            )
            
        except Exception:
            return AudioQualityMetrics(0, 0, 0, 0, 0)
    
    def start_realtime_processing(self):
        """Start real-time noise reduction processing"""
        if self.is_processing:
            self.logger.warning("Real-time processing already running")
            return
        
        self.is_processing = True
        self.processing_thread = threading.Thread(
            target=self._realtime_processing_loop,
            daemon=True
        )
        self.processing_thread.start()
        self.logger.info("Real-time noise reduction started")
    
    def stop_realtime_processing(self):
        """Stop real-time processing"""
        self.is_processing = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)
        self.logger.info("Real-time noise reduction stopped")
    
    def _realtime_processing_loop(self):
        """Real-time processing loop"""
        while self.is_processing:
            try:
                # Get audio data from queue
                audio_data, noise_sample = self.audio_queue.get(timeout=0.1)
                
                # Process audio
                enhanced = self.reduce_noise(audio_data, noise_sample)
                
                # Put result in output queue
                self.result_queue.put(enhanced)
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Real-time processing error: {e}")
    
    def add_audio_for_processing(self, audio_data: np.ndarray, 
                               noise_sample: Optional[np.ndarray] = None):
        """Add audio data for real-time processing"""
        if self.is_processing:
            try:
                self.audio_queue.put_nowait((audio_data, noise_sample))
            except queue.Full:
                self.logger.warning("Audio queue full, dropping frame")
    
    def get_processed_audio(self) -> Optional[np.ndarray]:
        """Get processed audio from real-time processing"""
        try:
            return self.result_queue.get_nowait()
        except queue.Empty:
            return None
    
    def estimate_noise_profile(self, audio_data: np.ndarray) -> Optional[NoiseProfile]:
        """Estimate noise profile from audio sample"""
        spectral_processor = self.processors.get('spectral')
        if spectral_processor:
            success = spectral_processor.estimate_noise(audio_data)
            if success:
                return spectral_processor.noise_profile
        return None
    
    def get_quality_metrics(self) -> AudioQualityMetrics:
        """Get latest quality metrics"""
        return self.quality_metrics
    
    def update_config(self, new_config: NoiseReductionConfig):
        """Update noise reduction configuration"""
        self.config = new_config
        self._initialize_processors()
        self.logger.info(f"Configuration updated to {new_config.method.value}")


# Convenience functions
def create_noise_reducer(method: NoiseReductionMethod = NoiseReductionMethod.HYBRID,
                        noise_level: NoiseLevel = NoiseLevel.MODERATE) -> NoiseReductionSystem:
    """Create noise reduction system with specified method and level"""
    config = NoiseReductionConfig(method=method, noise_level=noise_level)
    return NoiseReductionSystem(config)

def reduce_audio_noise(audio_data: np.ndarray, 
                      noise_sample: Optional[np.ndarray] = None,
                      noise_level: NoiseLevel = NoiseLevel.MODERATE) -> np.ndarray:
    """Quick noise reduction function"""
    reducer = create_noise_reducer(NoiseReductionMethod.HYBRID, noise_level)
    return reducer.reduce_noise(audio_data, noise_sample)