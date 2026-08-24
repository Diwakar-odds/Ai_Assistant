"""
Advanced Speech Recognition Engine - Whisper Only
Uses OpenAI Whisper API or local Whisper for accuracy, with offline fallback options
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from enum import Enum
import time
import numpy as np

try:
    import openai
    WHISPER_API_AVAILABLE = True
except ImportError:
    WHISPER_API_AVAILABLE = False

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

# Import privacy consent manager
try:
    from ai_assistant.core.privacy_consent import get_consent_manager, ConsentType
    CONSENT_MANAGER_AVAILABLE = True
except ImportError:
    CONSENT_MANAGER_AVAILABLE = False
    logger.warning("Privacy consent manager not available. External APIs will be used without consent checks!")


class RecognitionModel(Enum):
    """Available recognition models"""
    WHISPER_API = "whisper_api"  # Best accuracy (online)
    OFFLINE_WHISPER = "offline_whisper"  # Whisper local


class AdvancedSpeechRecognizer:
    """
    Advanced speech recognition engine matching Google Assistant accuracy
    Multi-model approach with automatic fallback
    """
    
    def __init__(
        self,
        whisper_api_key: Optional[str] = None,
        google_cloud_key: Optional[str] = None, # Ignored, kept for backward compat
        prefer_online: bool = True,
        noise_reduction: bool = True,
        cache_dir: str = "data/recognition_cache",
        user_id: str = "default_user",
        require_consent: bool = True
    ):
        self.whisper_api_key = whisper_api_key
        self.prefer_online = prefer_online
        self.noise_reduction = noise_reduction
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.user_id = user_id
        self.require_consent = require_consent and CONSENT_MANAGER_AVAILABLE
        
        # Initialize consent manager
        if self.require_consent:
            self.consent_manager = get_consent_manager()
            logger.info("✅ Privacy consent manager enabled for speech recognition")
        else:
            self.consent_manager = None
            if require_consent:
                logger.warning("⚠️ Consent requested but not available!")
        
        # Performance tracking
        self.recognition_history = []
        
        # Initialize Advanced Noise Reduction
        self.noise_reducer = None
        if self.noise_reduction:
            try:
                from ai_assistant.voice.noise_reduction import NoiseReductionSystem, NoiseReductionConfig, NoiseReductionMethod
                self.noise_reducer = NoiseReductionSystem(
                    NoiseReductionConfig(
                        method=NoiseReductionMethod.HYBRID,
                        adaptive_parameters=True,
                        enable_vad_gating=True
                    )
                )
                logger.info("✅ Advanced Noise Reduction System initialized")
            except ImportError as e:
                logger.warning(f"⚠️ Advanced noise reduction not available: {e}. Using legacy noise gate.")
        
        self._initialize_recognizers()
    
    def _initialize_recognizers(self):
        """Initialize all available recognition engines"""
        # Whisper API
        if WHISPER_API_AVAILABLE and self.whisper_api_key:
            try:
                openai.api_key = self.whisper_api_key
                logger.info("✅ Whisper API configured")
            except Exception as e:
                logger.warning(f"⚠️ Whisper API setup failed: {e}")
    
    def reduce_noise(self, audio_data, sr: int = 16000) -> np.ndarray:
        """Apply noise reduction to audio data"""
        if not self.noise_reduction:
            return audio_data
            
        if self.noise_reducer:
            try:
                return self.noise_reducer.reduce_noise(audio_data)
            except Exception as e:
                logger.error(f"Advanced noise reduction failed: {e}. Falling back to simple gate.")
        
        try:
            # Fallback: Simple noise gate (remove very low amplitude)
            noise_threshold = np.mean(np.abs(audio_data)) * 0.1
            reduced = np.copy(audio_data)
            reduced[np.abs(reduced) < noise_threshold] = 0
            
            # Normalize after noise reduction
            max_val = np.max(np.abs(reduced))
            if max_val > 0:
                reduced = (reduced / max_val) * 32767
            
            return reduced
        except Exception as e:
            logger.warning(f"Noise reduction failed: {e}")
            return audio_data
    
    async def recognize_whisper_api(
        self,
        audio_file: str,
        language: str = "en",
        prompt: Optional[str] = None
    ) -> Tuple[Optional[str], float]:
        """Recognize speech using OpenAI Whisper API"""
        if self.require_consent and not self.consent_manager.has_consent(self.user_id, ConsentType.EXTERNAL_STT):
            logger.warning(f"🚫 Whisper API blocked - user {self.user_id} has not consented to external STT")
            return None, 0.0
        
        if not WHISPER_API_AVAILABLE or not self.whisper_api_key:
            return None, 0.0
        
        try:
            whisper_lang = None
            context_prompt = prompt
            
            if language in ["en", "en-US", "en-IN", "en-GB"]:
                whisper_lang = "en"
                if not context_prompt:
                    context_prompt = "English speech with possible Indian accent."
            elif language in ["hi", "hi-IN"]:
                whisper_lang = "hi"
                if not context_prompt:
                    context_prompt = "Hindi speech, may contain some English words."
            elif language in ["auto", "hinglish"]:
                whisper_lang = None
                if not context_prompt:
                    context_prompt = "Mixed Hindi and English speech (Hinglish). Contains both languages."
            
            logger.info(f"🎤 Whisper API: language={whisper_lang or 'auto-detect'}, prompt='{context_prompt}'")
            
            with open(audio_file, 'rb') as f:
                api_params = {
                    'model': 'whisper-1',
                    'file': f,
                }
                if whisper_lang:
                    api_params['language'] = whisper_lang
                if context_prompt:
                    api_params['prompt'] = context_prompt
                
                transcript = openai.Audio.transcribe(**api_params)
            
            text = transcript.get('text', '').strip()
            detected_lang = transcript.get('language', whisper_lang or 'unknown')
            
            logger.info(f"✅ Whisper recognized [{detected_lang}]: {text}")
            
            confidence = 0.95 if text else 0.0
            
            return text, confidence
            
        except Exception as e:
            logger.error(f"❌ Whisper API failed: {e}")
            return None, 0.0
    
    def recognize(
        self,
        audio_input,
        language: str = "en",
        context: Optional[str] = None
    ) -> Tuple[Optional[str], float, str]:
        """Recognize speech with automatic model selection and fallback"""
        normalized_lang = language.lower()
        
        if normalized_lang in ["en", "en-us", "en-in", "en-gb", "english", "auto"]:
            whisper_lang = "en"
        elif normalized_lang in ["hinglish"]:
            whisper_lang = "auto"
        elif normalized_lang in ["hi", "hi-in", "hindi"]:
            whisper_lang = "hi"
        else:
            whisper_lang = "en"
        
        models_to_try = []
        
        if self.whisper_api_key:
            models_to_try.append(("whisper_api", audio_input, whisper_lang))
            
        # You could also add logic for local whisper model here if required
        
        for model_info in models_to_try:
            model_name = model_info[0]
            audio = model_info[1]
            lang_code = model_info[2] if len(model_info) > 2 else language
            
            try:
                if model_name == "whisper_api":
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    text, conf = loop.run_until_complete(
                        self.recognize_whisper_api(audio, lang_code, context)
                    )
                else:
                    continue
                
                if text and conf > 0.5:
                    logger.info(f"✅ Recognition successful with {model_name}: {text} (conf: {conf:.2f})")
                    self.recognition_history.append({"text": text, "model": model_name, "confidence": conf})
                    return text, conf, model_name
                    
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}")
                continue
        
        logger.error("❌ Whisper recognition failed")
        return None, 0.0, "none"
    
    def get_recognition_stats(self) -> Dict:
        """Get recognition performance statistics"""
        if not self.recognition_history:
            return {}
        
        return {
            "total_recognitions": len(self.recognition_history),
            "average_confidence": np.mean([r["confidence"] for r in self.recognition_history]),
            "models_used": list(set([r["model"] for r in self.recognition_history])),
            "success_rate": len([r for r in self.recognition_history if r["confidence"] > 0.5]) / len(self.recognition_history)
        }


# Global instance
_recognizer_instance = None


def get_advanced_speech_recognizer(
    whisper_api_key: Optional[str] = None,
    google_cloud_key: Optional[str] = None
) -> AdvancedSpeechRecognizer:
    """Get or create the advanced speech recognizer instance"""
    global _recognizer_instance
    if _recognizer_instance is None:
        _recognizer_instance = AdvancedSpeechRecognizer(
            whisper_api_key=whisper_api_key
        )
    return _recognizer_instance


# Example usage
if __name__ == "__main__":
    recognizer = get_advanced_speech_recognizer()
    logger.info("✅ Advanced Speech Recognizer initialized")
