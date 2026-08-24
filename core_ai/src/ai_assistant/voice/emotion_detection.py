# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Speech Emotion Detection
Detects emotions in user's voice to adapt assistant behavior

Features:
- Real-time emotion detection from audio
- Emotion-based response adaptation
- Mood tracking over time
- Sentiment analysis integration
"""

import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import librosa
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    logger.warning("librosa not available - audio emotion detection disabled")


class Emotion(Enum):
    """Detected emotions"""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    NEUTRAL = "neutral"
    EXCITED = "excited"
    FRUSTRATED = "frustrated"
    CALM = "calm"


@dataclass
class EmotionResult:
    """Emotion detection result"""
    primary_emotion: Emotion
    confidence: float
    emotions_breakdown: Dict[str, float]
    audio_features: Dict[str, float]
    timestamp: str


class SpeechEmotionDetector:
    """Detects emotions from speech audio"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize emotion detector
        
        Args:
            model_path: Path to custom emotion model (optional)
        """
        self.model_path = model_path
        self.emotion_history = []
        
        # Feature extraction parameters
        self.sample_rate = 16000
        self.n_mfcc = 13
        
        # Emotion thresholds (based on audio features)
        self.thresholds = {
            'energy_threshold': 0.02,  # For calm vs excited
            'pitch_variance_threshold': 50,  # For angry vs neutral
            'speech_rate_threshold': 3.0  # syllables per second
        }
        
        logger.info("🎤 Speech Emotion Detector initialized")
    
    def analyze_audio(self, audio_path: str) -> EmotionResult:
        """
        Analyze emotion from audio file
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            EmotionResult with detected emotion
        """
        if not AUDIO_AVAILABLE:
            logger.warning("Audio libraries not available")
            return self._get_neutral_result()
        
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # Extract features
            features = self._extract_features(audio, sr)
            
            # Classify emotion
            emotion_scores = self._classify_emotion(features)
            
            # Get primary emotion
            primary = max(emotion_scores.items(), key=lambda x: x[1])
            
            result = EmotionResult(
                primary_emotion=Emotion(primary[0]),
                confidence=primary[1],
                emotions_breakdown=emotion_scores,
                audio_features=features,
                timestamp=datetime.now().isoformat()
            )
            
            # Store in history
            self.emotion_history.append(result)
            
            logger.info(f"🎭 Detected emotion: {result.primary_emotion.value} "
                       f"(confidence: {result.confidence:.2f})")
            
            return result
        
        except Exception as e:
            logger.error(f"Emotion detection failed: {e}")
            return self._get_neutral_result()
    
    def analyze_realtime(self, audio_buffer: bytes) -> EmotionResult:
        """
        Analyze emotion from real-time audio buffer
        
        Args:
            audio_buffer: Raw audio bytes
            
        Returns:
            EmotionResult
        """
        # Save buffer to temp file and analyze
        # In production, process buffer directly
        temp_path = Path("data/voice_cache/temp_emotion.wav")
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_path, 'wb') as f:
            f.write(audio_buffer)
        
        return self.analyze_audio(str(temp_path))
    
    def _extract_features(self, audio: np.ndarray, sr: int) -> Dict[str, float]:
        """Extract audio features for emotion detection"""
        features = {}
        
        # MFCC (mel-frequency cepstral coefficients)
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=self.n_mfcc)
        features['mfcc_mean'] = float(np.mean(mfccs))
        features['mfcc_std'] = float(np.std(mfccs))
        
        # Energy/Amplitude
        energy = librosa.feature.rms(y=audio)
        features['energy_mean'] = float(np.mean(energy))
        features['energy_std'] = float(np.std(energy))
        
        # Pitch (fundamental frequency)
        pitches, magnitudes = librosa.piptrack(y=audio, sr=sr)
        pitch_values = pitches[pitches > 0]
        if len(pitch_values) > 0:
            features['pitch_mean'] = float(np.mean(pitch_values))
            features['pitch_std'] = float(np.std(pitch_values))
        else:
            features['pitch_mean'] = 0.0
            features['pitch_std'] = 0.0
        
        # Speech rate (zero crossing rate as proxy)
        zcr = librosa.feature.zero_crossing_rate(audio)
        features['speech_rate'] = float(np.mean(zcr))
        
        # Spectral features
        spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)
        features['spectral_centroid'] = float(np.mean(spectral_centroid))
        
        return features
    
    def _classify_emotion(self, features: Dict[str, float]) -> Dict[str, float]:
        """
        Classify emotion based on features
        
        Uses rule-based classification (can be replaced with ML model)
        """
        scores = {emotion.value: 0.0 for emotion in Emotion}
        
        # Rule-based classification
        energy = features['energy_mean']
        pitch_var = features['pitch_std']
        speech_rate = features['speech_rate']
        
        # Excited: High energy, high pitch variance, fast speech
        if energy > 0.03 and pitch_var > 50:
            scores['excited'] = 0.7
            scores['happy'] = 0.2
        
        # Happy: Moderate-high energy, varied pitch
        elif energy > 0.02 and pitch_var > 30:
            scores['happy'] = 0.8
            scores['excited'] = 0.1
        
        # Angry: High energy, high pitch variance, erratic
        elif energy > 0.025 and pitch_var > 60:
            scores['angry'] = 0.7
            scores['frustrated'] = 0.2
        
        # Frustrated: Moderate energy, varied
        elif pitch_var > 40:
            scores['frustrated'] = 0.6
            scores['angry'] = 0.2
        
        # Sad: Low energy, low pitch variance
        elif energy < 0.015 and pitch_var < 20:
            scores['sad'] = 0.7
            scores['calm'] = 0.2
        
        # Calm: Low-moderate energy, stable pitch
        elif energy < 0.025 and pitch_var < 30:
            scores['calm'] = 0.8
            scores['neutral'] = 0.1
        
        # Neutral: Everything else
        else:
            scores['neutral'] = 0.6
            scores['calm'] = 0.3
        
        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}
        
        return scores
    
    def _get_neutral_result(self) -> EmotionResult:
        """Get default neutral result"""
        return EmotionResult(
            primary_emotion=Emotion.NEUTRAL,
            confidence=1.0,
            emotions_breakdown={e.value: 0.0 for e in Emotion},
            audio_features={},
            timestamp=datetime.now().isoformat()
        )
    
    def get_mood_trend(self, window_minutes: int = 30) -> Dict[str, any]:
        """
        Analyze mood trend over recent history
        
        Args:
            window_minutes: Time window to analyze
            
        Returns:
            Mood trend analysis
        """
        if not self.emotion_history:
            return {'trend': 'neutral', 'stability': 'stable'}
        
        # Get recent emotions
        cutoff = datetime.now().timestamp() - (window_minutes * 60)
        recent = [
            e for e in self.emotion_history
            if datetime.fromisoformat(e.timestamp).timestamp() > cutoff
        ]
        
        if not recent:
            return {'trend': 'neutral', 'stability': 'stable'}
        
        # Calculate average valence (positive/negative)
        positive_emotions = {Emotion.HAPPY, Emotion.EXCITED, Emotion.CALM}
        negative_emotions = {Emotion.SAD, Emotion.ANGRY, Emotion.FRUSTRATED}
        
        positive_count = sum(1 for e in recent if e.primary_emotion in positive_emotions)
        negative_count = sum(1 for e in recent if e.primary_emotion in negative_emotions)
        
        if positive_count > negative_count * 1.5:
            trend = 'positive'
        elif negative_count > positive_count * 1.5:
            trend = 'negative'
        else:
            trend = 'neutral'
        
        # Calculate stability (variance in emotions)
        unique_emotions = len(set(e.primary_emotion for e in recent))
        if unique_emotions <= 2:
            stability = 'stable'
        elif unique_emotions <= 4:
            stability = 'moderate'
        else:
            stability = 'volatile'
        
        return {
            'trend': trend,
            'stability': stability,
            'positive_ratio': positive_count / len(recent),
            'negative_ratio': negative_count / len(recent),
            'sample_size': len(recent)
        }
    
    def adapt_response_style(self, emotion: Emotion) -> Dict[str, str]:
        """
        Get response adaptation recommendations based on emotion
        
        Args:
            emotion: Detected emotion
            
        Returns:
            Response style recommendations
        """
        adaptations = {
            Emotion.HAPPY: {
                'tone': 'enthusiastic',
                'formality': 'casual',
                'verbosity': 'moderate',
                'empathy': 'match_energy',
                'suggestion': 'Keep responses upbeat and engaging'
            },
            Emotion.SAD: {
                'tone': 'gentle',
                'formality': 'moderate',
                'verbosity': 'concise',
                'empathy': 'high',
                'suggestion': 'Be supportive and understanding, offer help'
            },
            Emotion.ANGRY: {
                'tone': 'calm',
                'formality': 'professional',
                'verbosity': 'brief',
                'empathy': 'validation',
                'suggestion': 'Stay neutral, de-escalate, focus on solutions'
            },
            Emotion.FRUSTRATED: {
                'tone': 'patient',
                'formality': 'moderate',
                'verbosity': 'clear',
                'empathy': 'high',
                'suggestion': 'Acknowledge frustration, provide clear steps'
            },
            Emotion.EXCITED: {
                'tone': 'enthusiastic',
                'formality': 'casual',
                'verbosity': 'moderate',
                'empathy': 'match_energy',
                'suggestion': 'Match their excitement, be encouraging'
            },
            Emotion.CALM: {
                'tone': 'balanced',
                'formality': 'moderate',
                'verbosity': 'moderate',
                'empathy': 'moderate',
                'suggestion': 'Maintain calm, professional tone'
            },
            Emotion.NEUTRAL: {
                'tone': 'balanced',
                'formality': 'moderate',
                'verbosity': 'moderate',
                'empathy': 'moderate',
                'suggestion': 'Standard response style'
            }
        }
        
        return adaptations.get(emotion, adaptations[Emotion.NEUTRAL])


# Global detector instance
_emotion_detector = None

def get_emotion_detector() -> SpeechEmotionDetector:
    """Get global emotion detector"""
    global _emotion_detector
    if _emotion_detector is None:
        _emotion_detector = SpeechEmotionDetector()
    return _emotion_detector


if __name__ == "__main__":
    # Demo
    print("🎭 Speech Emotion Detection Demo\n")
    
    detector = SpeechEmotionDetector()
    
    # Simulate emotion detection
    print("Example emotions and response adaptations:\n")
    
    for emotion in [Emotion.HAPPY, Emotion.SAD, Emotion.ANGRY, Emotion.FRUSTRATED]:
        print(f"Emotion: {emotion.value.upper()}")
        adaptation = detector.adapt_response_style(emotion)
        print(f"  Tone: {adaptation['tone']}")
        print(f"  Suggestion: {adaptation['suggestion']}")
        print()
