import logging
import base64
import math
import sqlite3
import time
from typing import Dict, Any, List
from ai_assistant.core.database_config import get_db_path_str

logger = logging.getLogger(__name__)

class EmotionalIntelligence:
    """NLP-based sentiment and emotion classification with historical tracking."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or get_db_path_str('memory')
        self._setup_db()
        
    def _setup_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS emotion_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emotion TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def _record_emotion(self, emotion: str, sentiment: str, confidence: float):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('INSERT INTO emotion_history (emotion, sentiment, confidence) VALUES (?, ?, ?)',
                      (emotion, sentiment, confidence))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to record emotion: {e}")

    def analyze_sentiment(self, text: str) -> dict:
        """
        Mock implementation of sentiment analysis.
        In production, this would use a localized NLP model or an API.
        """
        lower_text = text.lower()
        result = {"sentiment": "neutral", "emotion": "neutral", "confidence": 0.5}
        
        if any(word in lower_text for word in ["angry", "mad", "stupid", "hate", "frustrated", "annoyed"]):
            result = {"sentiment": "negative", "emotion": "frustrated", "confidence": 0.8}
        elif any(word in lower_text for word in ["happy", "glad", "awesome", "love", "great", "thanks"]):
            result = {"sentiment": "positive", "emotion": "happy", "confidence": 0.8}
        elif any(word in lower_text for word in ["sad", "depressed", "lonely", "help", "tired"]):
            result = {"sentiment": "negative", "emotion": "sad", "confidence": 0.7}
            
        self._record_emotion(result["emotion"], result["sentiment"], result["confidence"])
        return result

    def detect_emotion_from_voice(self, audio_data_base64: str) -> dict:
        """
        Analyzes audio properties to estimate emotion.
        Uses a heuristic based on RMS volume.
        """
        try:
            # Decode the base64 audio
            if audio_data_base64.startswith("data:audio"):
                audio_data_base64 = audio_data_base64.split(",")[1]
            audio_bytes = base64.b64decode(audio_data_base64)
            
            energy = sum(b for b in audio_bytes[:1000]) / 1000 if len(audio_bytes) > 0 else 0
            
            result = {"sentiment": "neutral", "emotion": "neutral", "confidence": 0.5}
            if energy > 150:
                result = {"sentiment": "negative", "emotion": "frustrated", "confidence": 0.6}
            elif energy < 50 and len(audio_bytes) > 50000: # Long and quiet
                result = {"sentiment": "negative", "emotion": "sad", "confidence": 0.6}
            elif energy > 100:
                result = {"sentiment": "positive", "emotion": "happy", "confidence": 0.6}
                
            self._record_emotion(result["emotion"], result["sentiment"], result["confidence"])
            return result
        except Exception as e:
            logger.error(f"Failed to detect emotion from voice: {e}")
            return {"sentiment": "neutral", "emotion": "neutral", "confidence": 0.1}

    def get_prompt_modifier(self, emotion_profile: dict) -> str:
        """Returns a system prompt modifier based on detected emotion."""
        emotion = emotion_profile.get("emotion", "neutral")
        if emotion == "frustrated":
            return "The user seems frustrated. Be extremely concise, direct, and helpful. Do not use pleasantries."
        if emotion == "sad":
            return "The user seems down. Be warm, empathetic, and gently supportive."
        if emotion == "happy":
            return "The user is in a good mood. Match their energy and be cheerful!"
        return ""
        
    def get_mood_trend(self, days: int = 7) -> str:
        """Returns a string describing the user's mood trend over the past N days."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT emotion FROM emotion_history WHERE timestamp >= datetime('now', ?)", (f"-{days} days",))
            rows = c.fetchall()
            conn.close()
            
            if not rows:
                return "Stable (neutral)"
                
            counts = {}
            for row in rows:
                counts[row[0]] = counts.get(row[0], 0) + 1
                
            top_emotion = max(counts, key=counts.get)
            if top_emotion == "happy":
                return "Generally positive and upbeat"
            elif top_emotion == "frustrated":
                return "Often frustrated or stressed"
            elif top_emotion == "sad":
                return "Leaning towards sad or tired"
            else:
                return "Stable and neutral"
        except Exception as e:
            logger.error(f"Failed to get mood trend: {e}")
            return "Stable"
