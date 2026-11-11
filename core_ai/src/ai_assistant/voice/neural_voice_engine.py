"""
Neural Voice Engine for Pulsar AI Assistant
Provides high-quality neural voice synthesis using KittenTTS (primary, offline) and Edge-TTS (fallback, online).
"""
import asyncio
import hashlib
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

from ai_assistant.voice.text_cleaner import clean_text_for_tts, prepare_text_for_kitten_tts
from ai_assistant.voice.tts_output_service import (
    ensure_espeak_environment,
    load_kitten_mini_model,
    resolve_edge_voice,
    resolve_kitten_voice,
)

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
    
    def __init__(self, cache_dir: Optional[str] = None, gpu: bool = False):
        if cache_dir is None or cache_dir == "data/voice_cache":
            try:
                from ai_assistant.core.database_config import get_data_root
                self.cache_dir = get_data_root() / "voice_cache"
            except Exception:
                self.cache_dir = Path("data/voice_cache")
        else:
            self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.gpu = gpu
        
        # Initialize engines
        self.kitten_tts = None
        self.kitten_available = KITTEN_AVAILABLE
        
        self._initialize_engines()
        
    def _initialize_engines(self):
        """Initialize all available TTS engines"""
        ensure_espeak_environment()
        if self.kitten_available:
             logger.info("✅ KittenTTS available (Offline Neural Voice Engine)")
        else:
             logger.warning("⚠️ KittenTTS not available. Install: pip install kittentts")

    def synthesize_kitten_tts(
        self,
        text: str,
        voice: str = "Bella",
        speed: float = 1.0,
        output_file: Optional[str] = None
    ) -> Optional[str]:
        """Synthesize speech using KittenTTS mini-0.8 (offline, ultra-lightweight)."""
        if not self.kitten_available or not text:
            return None

        try:
            cleaned = prepare_text_for_kitten_tts(text)
            if not cleaned:
                return None

            logger.info(f"⏳ Synthesizing with KittenTTS mini-0.8: {cleaned[:50]}...")

            if self.kitten_tts is None:
                self.kitten_tts = load_kitten_mini_model()

            resolved_voice = resolve_kitten_voice(voice)
            digest = hashlib.md5(f"{cleaned}|{resolved_voice}|{speed:.2f}".encode("utf-8")).hexdigest()[:16]
            cache_file = self.cache_dir / f"kitten_{resolved_voice}_{digest}.wav"

            target_file = output_file or str(cache_file)
            if Path(target_file).exists() and Path(target_file).stat().st_size > 44:
                return target_file

            Path(target_file).parent.mkdir(parents=True, exist_ok=True)
            self.kitten_tts.generate_to_file(
                cleaned,
                target_file,
                voice=resolved_voice,
                speed=speed,
                sample_rate=24000,
                clean_text=True,
            )
            if Path(target_file).exists() and Path(target_file).stat().st_size > 44:
                logger.info(f"✅ KittenTTS Synthesized -> {target_file}")
                return target_file
            return None

        except Exception as e:
            logger.error(f"❌ KittenTTS synthesis failed: {e}")
            return None

    def synthesize_edge_tts(
        self,
        text: str,
        voice: str = 'en-US-AriaNeural',
        output_file: Optional[str] = None
    ) -> Optional[str]:
        """Synthesize speech using Microsoft Edge Neural TTS."""
        if not text:
            return None
        try:
            import edge_tts
        except ImportError:
            logger.error('edge-tts not installed')
            return None

        cleaned = clean_text_for_tts(text)
        if not cleaned:
            return None

        resolved_voice = resolve_edge_voice(cleaned, voice)
        digest = hashlib.md5(f"{cleaned}|{resolved_voice}".encode("utf-8")).hexdigest()[:16]
        target_file = output_file or str(self.cache_dir / f'edge_{resolved_voice}_{digest}.mp3')
        if Path(target_file).exists() and Path(target_file).stat().st_size > 0:
            return target_file

        Path(target_file).parent.mkdir(parents=True, exist_ok=True)

        async def _run():
            comm = edge_tts.Communicate(cleaned, resolved_voice)
            await comm.save(target_file)

        try:
            try:
                asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(asyncio.run, _run()).result(timeout=12)
            except RuntimeError:
                asyncio.run(_run())
            if Path(target_file).exists() and Path(target_file).stat().st_size > 0:
                return target_file
            return None
        except Exception as e:
            logger.error(f'EdgeTTS synthesis failed: {e}')
            return None

    def speak(
        self,
        text: str,
        language: str = 'en',
        style: SpeakingStyle = SpeakingStyle.NORMAL,
        gender: VoiceGender = VoiceGender.FEMALE,
        output_file: Optional[str] = None,
        force_engine: Optional[str] = None,
        voice_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate audio using Edge-TTS (online) or KittenTTS mini-0.8 (offline/selected).
        Returns the path to the generated audio file.
        """
        if not text:
            return None

        logger.info(f"🎤 Synthesizing speech: {text[:50]}...")
        result_file = None

        target_engine = force_engine
        target_voice = voice_id
        try:
            from settings_manager import get_tts_config
            tts_cfg = get_tts_config()
            if not target_engine:
                target_engine = tts_cfg.get('engine', 'edge_tts')
            if not target_voice:
                target_voice = tts_cfg.get('voice_id', 'hi-IN-SwaraNeural')
        except Exception:
            target_engine = target_engine or 'edge_tts'
            target_voice = target_voice or 'hi-IN-SwaraNeural'

        target_voice_str = str(target_voice or '')
        use_kitten_only = (
            str(target_engine or '').lower() == 'kittentts'
            or target_voice_str.lower() == 'kittentts'
            or target_voice_str.lower().startswith('kitten:')
        )

        # 1. Preferred Online: Edge-TTS (skip if user selected a KittenTTS voice)
        if not use_kitten_only:
            result_file = self.synthesize_edge_tts(text, voice=target_voice_str, output_file=output_file)

        # 2. Offline KittenTTS mini-0.8 (primary if selected, or fallback when offline)
        if not result_file and (self.kitten_available or use_kitten_only):
            fallback_hint = target_voice_str or ('Jasper' if gender == VoiceGender.MALE else 'Bella')
            kitten_voice = resolve_kitten_voice(fallback_hint)
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
