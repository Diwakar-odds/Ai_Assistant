"""
Multi-Modal Learning Integration
Combines voice, text, and behavioral data for unified user understanding

Features:
- Cross-modal embeddings (voice + text)
- Unified user profiling across modalities
- Voice-to-behavior correlation learning
- Emotion-aware context switching
- Multi-modal preference learning
"""

import json
import sqlite3
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
from pathlib import Path
import hashlib


try:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@dataclass
class MultiModalProfile:
    """Unified user profile across modalities"""
    user_id: str
    voice_features: Dict[str, float]
    text_preferences: Dict[str, float]
    behavioral_patterns: Dict[str, float]
    emotion_history: List[str]
    interaction_times: List[str]
    cross_modal_correlations: Dict[str, float]
    last_updated: datetime


@dataclass
class ModalityInteraction:
    """Record of multi-modal interaction"""
    timestamp: datetime
    voice_data: Optional[Dict]
    text_data: Optional[Dict]
    emotion: str
    context: str
    response_quality: float


class CrossModalEmbedder:
    """
    Creates unified embeddings from multiple modalities
    """
    
    def __init__(self, embedding_dim: int = 128):
        self.embedding_dim = embedding_dim
        self.voice_weights = np.random.randn(50, embedding_dim) * 0.01  # Voice features to embedding
        self.text_weights = np.random.randn(384, embedding_dim) * 0.01   # Text embeddings (SBERT dim)
        self.behavior_weights = np.random.randn(20, embedding_dim) * 0.01
        
        if SKLEARN_AVAILABLE:
            self.scaler = StandardScaler()
            self.pca = PCA(n_components=embedding_dim)
        
    def embed_voice(self, voice_features: np.ndarray) -> np.ndarray:
        """Convert voice features to embedding"""
        if voice_features.shape[0] < 50:
            # Pad if needed
            padded = np.zeros(50)
            padded[:voice_features.shape[0]] = voice_features
            voice_features = padded
        elif voice_features.shape[0] > 50:
            voice_features = voice_features[:50]
        
        return voice_features @ self.voice_weights
    
    def embed_text(self, text_embedding: np.ndarray) -> np.ndarray:
        """Convert text embedding to unified space"""
        if text_embedding.shape[0] != 384:
            # Resize if needed
            resized = np.zeros(384)
            min_len = min(len(text_embedding), 384)
            resized[:min_len] = text_embedding[:min_len]
            text_embedding = resized
        
        return text_embedding @ self.text_weights
    
    def embed_behavior(self, behavior_features: np.ndarray) -> np.ndarray:
        """Convert behavioral features to embedding"""
        if behavior_features.shape[0] < 20:
            padded = np.zeros(20)
            padded[:behavior_features.shape[0]] = behavior_features
            behavior_features = padded
        elif behavior_features.shape[0] > 20:
            behavior_features = behavior_features[:20]
        
        return behavior_features @ self.behavior_weights
    
    def fuse_modalities(self, embeddings: Dict[str, np.ndarray]) -> np.ndarray:
        """Fuse multiple modal embeddings"""
        # Weighted fusion based on availability and quality
        fused = np.zeros(self.embedding_dim)
        total_weight = 0.0
        
        modality_weights = {
            'voice': 0.3,
            'text': 0.5,
            'behavior': 0.2
        }
        
        for modality, embedding in embeddings.items():
            if modality in modality_weights and embedding is not None:
                weight = modality_weights[modality]
                fused += weight * embedding
                total_weight += weight
        
        if total_weight > 0:
            fused /= total_weight
        
        return fused


class VoiceTextCorrelator:
    """
    Learns correlations between voice patterns and text preferences
    """
    
    def __init__(self):
        self.correlations = {}
        self.voice_to_emotion = defaultdict(list)
        self.emotion_to_preference = defaultdict(list)
    
    def learn_correlation(self, voice_features: Dict, text_preference: str, emotion: str):
        """Learn voice-text correlation"""
        # Extract voice characteristics
        voice_key = self._voice_fingerprint(voice_features)
        
        # Track emotion patterns
        self.voice_to_emotion[voice_key].append(emotion)
        self.emotion_to_preference[emotion].append(text_preference)
        
        # Build correlation
        if voice_key not in self.correlations:
            self.correlations[voice_key] = defaultdict(int)
        
        self.correlations[voice_key][text_preference] += 1
    
    def _voice_fingerprint(self, voice_features: Dict) -> str:
        """Create fingerprint from voice features"""
        # Simple fingerprint based on key features
        pitch = voice_features.get('pitch', 0)
        energy = voice_features.get('energy', 0)
        
        pitch_bucket = int(pitch / 50)
        energy_bucket = int(energy / 0.1)
        
        return f"p{pitch_bucket}_e{energy_bucket}"
    
    def predict_preference(self, voice_features: Dict) -> Optional[str]:
        """Predict text preference from voice"""
        voice_key = self._voice_fingerprint(voice_features)
        
        if voice_key not in self.correlations:
            return None
        
        # Get most common preference for this voice pattern
        preferences = self.correlations[voice_key]
        if not preferences:
            return None
        
        return max(preferences.items(), key=lambda x: x[1])[0]
    
    def detect_emotion_from_voice(self, voice_features: Dict) -> Optional[str]:
        """Detect likely emotion from voice pattern"""
        voice_key = self._voice_fingerprint(voice_features)
        
        if voice_key not in self.voice_to_emotion:
            return None
        
        emotions = self.voice_to_emotion[voice_key]
        if not emotions:
            return None
        
        # Most common emotion for this voice pattern
        emotion_counts = defaultdict(int)
        for e in emotions:
            emotion_counts[e] += 1
        
        return max(emotion_counts.items(), key=lambda x: x[1])[0]


class MultiModalLearningEngine:
    """
    Main engine for multi-modal learning
    """
    
    def __init__(self, db_path: str = "data/multimodal_learning.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.embedder = CrossModalEmbedder()
        self.correlator = VoiceTextCorrelator()
        self.user_profiles = {}
        
        self._init_database()
        self._load_profiles()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    voice_features TEXT NOT NULL,
                    text_preferences TEXT NOT NULL,
                    behavioral_patterns TEXT NOT NULL,
                    emotion_history TEXT NOT NULL,
                    interaction_times TEXT NOT NULL,
                    cross_modal_correlations TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS modal_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    voice_data TEXT,
                    text_data TEXT,
                    emotion TEXT NOT NULL,
                    context TEXT NOT NULL,
                    response_quality REAL DEFAULT 0.5
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_text_correlations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voice_pattern TEXT NOT NULL,
                    text_preference TEXT NOT NULL,
                    emotion TEXT NOT NULL,
                    count INTEGER DEFAULT 1,
                    confidence REAL DEFAULT 0.5,
                    last_seen TEXT NOT NULL
                )
            """)
    
    def _load_profiles(self):
        """Load user profiles"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM user_profiles")
            
            for row in cursor.fetchall():
                profile = MultiModalProfile(
                    user_id=row[0],
                    voice_features=json.loads(row[1]),
                    text_preferences=json.loads(row[2]),
                    behavioral_patterns=json.loads(row[3]),
                    emotion_history=json.loads(row[4]),
                    interaction_times=json.loads(row[5]),
                    cross_modal_correlations=json.loads(row[6]),
                    last_updated=datetime.fromisoformat(row[7])
                )
                self.user_profiles[profile.user_id] = profile
    
    def get_or_create_profile(self, user_id: str = "default") -> MultiModalProfile:
        """Get or create user profile"""
        if user_id not in self.user_profiles:
            profile = MultiModalProfile(
                user_id=user_id,
                voice_features={},
                text_preferences={},
                behavioral_patterns={},
                emotion_history=[],
                interaction_times=[],
                cross_modal_correlations={},
                last_updated=datetime.now()
            )
            self.user_profiles[user_id] = profile
            self.save_profile(profile)
        
        return self.user_profiles[user_id]
    
    def save_profile(self, profile: MultiModalProfile):
        """Save profile to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_profiles
                (user_id, voice_features, text_preferences, behavioral_patterns,
                 emotion_history, interaction_times, cross_modal_correlations, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.user_id,
                json.dumps(profile.voice_features),
                json.dumps(profile.text_preferences),
                json.dumps(profile.behavioral_patterns),
                json.dumps(profile.emotion_history),
                json.dumps(profile.interaction_times),
                json.dumps(profile.cross_modal_correlations),
                profile.last_updated.isoformat()
            ))
    
    def record_interaction(self, user_id: str, voice_data: Optional[Dict],
                          text_data: Optional[Dict], emotion: str,
                          context: str, quality: float = 0.5):
        """Record multi-modal interaction"""
        # Get or create profile
        profile = self.get_or_create_profile(user_id)
        
        # Update profile
        if voice_data:
            self._update_voice_features(profile, voice_data)
        
        if text_data:
            self._update_text_preferences(profile, text_data)
        
        # Track emotion
        profile.emotion_history.append(emotion)
        if len(profile.emotion_history) > 100:
            profile.emotion_history = profile.emotion_history[-100:]
        
        # Track interaction time
        profile.interaction_times.append(datetime.now().isoformat())
        if len(profile.interaction_times) > 200:
            profile.interaction_times = profile.interaction_times[-200:]
        
        profile.last_updated = datetime.now()
        
        # Learn correlations
        if voice_data and text_data:
            text_pref = text_data.get('preference', 'general')
            self.correlator.learn_correlation(voice_data, text_pref, emotion)
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO modal_interactions
                (user_id, timestamp, voice_data, text_data, emotion, context, response_quality)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                datetime.now().isoformat(),
                json.dumps(voice_data) if voice_data else None,
                json.dumps(text_data) if text_data else None,
                emotion,
                context,
                quality
            ))
        
        self.save_profile(profile)
    
    def _update_voice_features(self, profile: MultiModalProfile, voice_data: Dict):
        """Update voice feature averages"""
        for key, value in voice_data.items():
            if isinstance(value, (int, float)):
                if key not in profile.voice_features:
                    profile.voice_features[key] = value
                else:
                    # Exponential moving average
                    alpha = 0.1
                    profile.voice_features[key] = alpha * value + (1 - alpha) * profile.voice_features[key]
    
    def _update_text_preferences(self, profile: MultiModalProfile, text_data: Dict):
        """Update text preference scores"""
        for key, value in text_data.items():
            if isinstance(value, (int, float)):
                if key not in profile.text_preferences:
                    profile.text_preferences[key] = value
                else:
                    alpha = 0.1
                    profile.text_preferences[key] = alpha * value + (1 - alpha) * profile.text_preferences[key]
    
    def get_unified_embedding(self, user_id: str, current_voice: Optional[np.ndarray] = None,
                             current_text: Optional[np.ndarray] = None) -> np.ndarray:
        """Get unified multi-modal embedding for user"""
        profile = self.get_or_create_profile(user_id)
        
        embeddings = {}
        
        # Voice embedding
        if current_voice is not None:
            embeddings['voice'] = self.embedder.embed_voice(current_voice)
        elif profile.voice_features:
            # Use profile average
            voice_array = np.array([profile.voice_features.get(f'feature_{i}', 0) for i in range(50)])
            embeddings['voice'] = self.embedder.embed_voice(voice_array)
        
        # Text embedding
        if current_text is not None:
            embeddings['text'] = self.embedder.embed_text(current_text)
        
        # Behavioral embedding
        if profile.behavioral_patterns:
            behavior_array = np.array([profile.behavioral_patterns.get(f'pattern_{i}', 0) for i in range(20)])
            embeddings['behavior'] = self.embedder.embed_behavior(behavior_array)
        
        return self.embedder.fuse_modalities(embeddings)
    
    def predict_user_state(self, user_id: str, voice_features: Optional[Dict] = None) -> Dict:
        """Predict user state from available modalities"""
        profile = self.get_or_create_profile(user_id)
        
        state = {
            'emotion': 'neutral',
            'text_preference': 'general',
            'engagement_level': 0.5,
            'likely_intent': 'unknown'
        }
        
        # Predict emotion from voice
        if voice_features:
            predicted_emotion = self.correlator.detect_emotion_from_voice(voice_features)
            if predicted_emotion:
                state['emotion'] = predicted_emotion
            
            # Predict text preference
            predicted_pref = self.correlator.predict_preference(voice_features)
            if predicted_pref:
                state['text_preference'] = predicted_pref
        
        # Analyze recent emotion history
        if profile.emotion_history:
            recent = profile.emotion_history[-10:]
            positive_emotions = ['happy', 'excited', 'calm']
            positive_count = sum(1 for e in recent if e in positive_emotions)
            state['engagement_level'] = positive_count / len(recent)
        
        return state
    
    def get_contextual_insights(self, user_id: str) -> Dict:
        """Get insights from multi-modal data"""
        profile = self.get_or_create_profile(user_id)
        
        insights = {
            'primary_emotion': 'neutral',
            'voice_consistency': 0.0,
            'interaction_frequency': 0,
            'peak_hours': [],
            'modality_preferences': {}
        }
        
        # Primary emotion
        if profile.emotion_history:
            emotion_counts = defaultdict(int)
            for e in profile.emotion_history:
                emotion_counts[e] += 1
            insights['primary_emotion'] = max(emotion_counts.items(), key=lambda x: x[1])[0]
        
        # Interaction frequency (interactions per day)
        if profile.interaction_times:
            time_span = (datetime.now() - datetime.fromisoformat(profile.interaction_times[0])).days + 1
            insights['interaction_frequency'] = len(profile.interaction_times) / max(time_span, 1)
        
        # Peak hours
        if profile.interaction_times:
            hours = [datetime.fromisoformat(t).hour for t in profile.interaction_times]
            hour_counts = defaultdict(int)
            for h in hours:
                hour_counts[h] += 1
            
            sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
            insights['peak_hours'] = [h for h, _ in sorted_hours[:3]]
        
        return insights


def example_usage():
    """Demonstrate multi-modal learning"""
    engine = MultiModalLearningEngine()
    
    # Simulate interaction with voice and text
    voice_data = {
        'pitch': 150.0,
        'energy': 0.8,
        'tempo': 120.0
    }
    
    text_data = {
        'preference': 'detailed',
        'formality': 0.7
    }
    
    engine.record_interaction(
        user_id="user_001",
        voice_data=voice_data,
        text_data=text_data,
        emotion="happy",
        context="morning_greeting",
        quality=0.9
    )
    
    # Predict user state
    state = engine.predict_user_state("user_001", voice_data)
    print("Predicted user state:")
    print(json.dumps(state, indent=2))
    
    # Get insights
    insights = engine.get_contextual_insights("user_001")
    print("\nContextual insights:")
    print(json.dumps(insights, indent=2, default=str))


if __name__ == "__main__":
    example_usage()
