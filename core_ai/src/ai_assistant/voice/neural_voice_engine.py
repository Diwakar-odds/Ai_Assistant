"""
Neural Voice Engine for YourDaddy AI Assistant
Provides high-quality neural voice synthesis using KittenTTS (primary, offline) and Edge-TTS (fallback, online).
"""
import asyncio
import os
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from enum import Enum
import threading
import time



try:
    import kittentts
    KITTEN_AVAILABLE = True
except ImportError:
    KITTEN_AVAILABLE = False

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class VoiceGender(Enum):
    """Voice gender options"""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"

class SpeakingStyle(Enum):
    """Speaking style options for natural conversation"""
    NORMAL = "normal"
    EXCITED = "excited"
    CALM = "calm"
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CHEERFUL = "cheerful"


class NeuralVoiceEngine:
    """
    High-quality neural voice synthesis engine
    """
    
    def __init__(self, cache_dir: str = "data/voice_cache", gpu: bool = False):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.gpu = gpu
        
        # Initialize engines
        self.kitten_tts = None
        self.kitten_available = KITTEN_AVAILABLE
        
        self._initialize_engines()
        
    def _initialize_engines(self):
        """Initialize all available TTS engines"""
        if self.kitten_available:
             logger.info("✅ KittenTTS available (Primary Voice Engine)")
        else:
             logger.warning("⚠️ KittenTTS not available. Install: pip install kittentts")

    def synthesize_kitten_tts(
        self,
        text: str,
        voice: str = "Jasper",
        speed: float = 1.0,
        output_file: Optional[str] = None
    ) -> Optional[str]:
        """Synthesize speech using KittenTTS (offline, ultra-lightweight)"""
        if not self.kitten_available or not text:
            return None
            
        try:
            logger.info(f"⏳ Synthesizing with KittenTTS: {text[:50]}...")
            
            # Lazy load the model
            if self.kitten_tts is None:
                from kittentts import KittenTTS
                self.kitten_tts = KittenTTS("KittenML/kitten-tts-mini-0.8")
                
            if voice not in self.kitten_tts.available_voices:
                voice = "Jasper" # Default fallback
                
            # Cache key
            cache_key = f"kitten_{text[:30].replace(' ', '_')}_{voice}.wav"
            cache_file = self.cache_dir / cache_key
            
            output_file = output_file or str(cache_file)
            if Path(output_file).exists():
                return output_file
                
            # Generate audio
            self.kitten_tts.tts_to_file(text, output_file, voice=voice, speed=speed)
            logger.info(f"✅ KittenTTS Synthesized -> {output_file}")
            
            return output_file
            
        except Exception as e:
            logger.error(f"❌ KittenTTS synthesis failed: {e}")
            return None



    def speak(
        self, 
        text: str, 
        language: str = 'en',
        style: SpeakingStyle = SpeakingStyle.NORMAL,
        gender: VoiceGender = VoiceGender.FEMALE,
        output_file: Optional[str] = None,
        force_engine: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate audio using KittenTTS, falling back to Edge-TTS.
        Returns the path to the audio file.
        """
        if not text:
            return None
            
        logger.info(f"🎤 Synthesizing speech: {text[:50]}...")
        result_file = None
        
        # Primary Engine: KittenTTS
        if self.kitten_available:
            # Map gender to kitten voices roughly
            kitten_voice = "Jasper" if gender == VoiceGender.MALE else "Bella"
            result_file = self.synthesize_kitten_tts(text, voice=kitten_voice, output_file=output_file)
            
        if not result_file:
            logger.error("❌ All TTS engines failed or are unavailable.")
            
        return result_file

# Singleton instance
_engine_instance = None

def get_neural_voice_engine(cache_dir: str = "data/voice_cache", gpu: bool = False) -> NeuralVoiceEngine:
    """Get or create the neural voice engine singleton"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = NeuralVoiceEngine(cache_dir=cache_dir, gpu=gpu)
    return _engine_instance
