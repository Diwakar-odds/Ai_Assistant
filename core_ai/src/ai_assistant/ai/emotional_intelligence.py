import logging
import base64
import math
import wave
import io

logger = logging.getLogger(__name__)

class EmotionalIntelligence:
    """NLP-based sentiment and emotion classification."""
    
    def __init__(self):
        pass
        
    def analyze_sentiment(self, text: str) -> dict:
        """
        Mock implementation of sentiment analysis.
        In production, this would use a localized NLP model or an API.
        """
        lower_text = text.lower()
        if any(word in lower_text for word in ["angry", "mad", "stupid", "hate", "frustrated", "annoyed"]):
            return {"sentiment": "negative", "emotion": "frustrated", "confidence": 0.8}
        if any(word in lower_text for word in ["happy", "glad", "awesome", "love", "great", "thanks"]):
            return {"sentiment": "positive", "emotion": "happy", "confidence": 0.8}
        if any(word in lower_text for word in ["sad", "depressed", "lonely", "help", "tired"]):
            return {"sentiment": "negative", "emotion": "sad", "confidence": 0.7}
            
        return {"sentiment": "neutral", "emotion": "neutral", "confidence": 0.5}

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
            
            # Since the frontend might send mp3/webm or raw PCM, and doing full decoding is hard without ffmpeg,
            # we will use a naive proxy: the length of the string and the distribution of byte values.
            # In a real system, we'd use librosa or a proper acoustic model.
            
            # Simple heuristic:
            # If the audio is very short, it's likely a quick, urgent command.
            # We'll calculate a pseudo-energy score.
            energy = sum(b for b in audio_bytes[:1000]) / 1000 if len(audio_bytes) > 0 else 0
            
            if energy > 150:
                return {"sentiment": "negative", "emotion": "frustrated", "confidence": 0.6}
            elif energy < 50 and len(audio_bytes) > 50000: # Long and quiet
                return {"sentiment": "negative", "emotion": "sad", "confidence": 0.6}
            elif energy > 100:
                return {"sentiment": "positive", "emotion": "happy", "confidence": 0.6}
                
            return {"sentiment": "neutral", "emotion": "neutral", "confidence": 0.5}
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
