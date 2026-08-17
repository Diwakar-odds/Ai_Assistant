"""
Voice Settings Manager

Handles persistence and validation of voice settings (TTS/STT).
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default settings
DEFAULT_SETTINGS = {
    "tts": {
        "enabled": True,
        "voice_id": "en-US-AriaNeural",
        "voice_name": "Aria",
        "speed": 1.0,
        "pitch": 1.0,
        "volume": 1.0
    },
    "stt": {
        "enabled": True,
        "engine": "whisper",  # whisper, google
        "language": "en-US",
        "noise_reduction": True,
        "vad_enabled": True
    },
    "wake_word": {
        "enabled": False,
        "phrase": "hey daddy",
        "sensitivity": 0.5
    },
    "general": {
        "always_listening": False,
        "continuous_mode": False,
        "timeout_seconds": 5
    }
}

# Valid voice IDs (from voice_api.py)
VALID_VOICE_IDS = [
    "en-US-AriaNeural", "en-US-JennyNeural", "en-US-GuyNeural",
    "en-US-DavisNeural", "en-GB-SoniaNeural", "en-GB-RyanNeural",
    "en-IN-NeerjaNeural", "en-IN-PrabhatNeural", "en-US-AnaNeural",
    "en-US-ChristopherNeural", "en-GB-LibbyNeural", "en-US-EricNeural"
]

VALID_STT_ENGINES = ["whisper", "google"]

class VoiceSettingsManager:
    """Manages voice settings persistence and validation"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize settings manager"""
        if config_path is None:
            # Default to config directory
            base_dir = Path(__file__).parent.parent.parent
            config_dir = base_dir / "config"
            config_dir.mkdir(exist_ok=True)
            config_path = config_dir / "voice_settings.json"
        
        self.config_path = Path(config_path)
        self.settings = self.load_settings()
        logger.info(f"Voice settings manager initialized with config: {self.config_path}")
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file or return defaults"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    settings = json.load(f)
                logger.info("Loaded voice settings from file")
                # Merge with defaults to ensure all keys exist
                return self._merge_with_defaults(settings)
            except Exception as e:
                logger.error(f"Error loading settings: {e}. Using defaults.")
                return DEFAULT_SETTINGS.copy()
        else:
            logger.info("No settings file found. Using defaults.")
            return DEFAULT_SETTINGS.copy()
    
    def save_settings(self, settings: Optional[Dict[str, Any]] = None) -> bool:
        """Save settings to file"""
        if settings is not None:
            self.settings = settings
        
        try:
            # Validate before saving
            validated = self.validate_settings(self.settings)
            
            with open(self.config_path, 'w') as f:
                json.dump(validated, f, indent=2)
            
            logger.info(f"Settings saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize settings"""
        validated = DEFAULT_SETTINGS.copy()
        
        # Validate TTS
        if "tts" in settings:
            tts = settings["tts"]
            if tts.get("voice_id") in VALID_VOICE_IDS:
                validated["tts"]["voice_id"] = tts["voice_id"]
            if "voice_name" in tts:
                validated["tts"]["voice_name"] = tts["voice_name"]
            if "enabled" in tts:
                validated["tts"]["enabled"] = bool(tts["enabled"])
            
            # Validate numeric ranges
            for key in ["speed", "pitch", "volume"]:
                if key in tts:
                    value = float(tts[key])
                    validated["tts"][key] = max(0.5, min(2.0, value))
        
        # Validate STT
        if "stt" in settings:
            stt = settings["stt"]
            if stt.get("engine") in VALID_STT_ENGINES:
                validated["stt"]["engine"] = stt["engine"]
            if "language" in stt:
                validated["stt"]["language"] = stt["language"]
            for key in ["enabled", "noise_reduction", "vad_enabled"]:
                if key in stt:
                    validated["stt"][key] = bool(stt[key])
        
        # Validate wake word
        if "wake_word" in settings:
            ww = settings["wake_word"]
            if "enabled" in ww:
                validated["wake_word"]["enabled"] = bool(ww["enabled"])
            if "phrase" in ww:
                validated["wake_word"]["phrase"] = str(ww["phrase"])
            if "sensitivity" in ww:
                validated["wake_word"]["sensitivity"] = max(0.0, min(1.0, float(ww["sensitivity"])))
        
        # Validate general
        if "general" in settings:
            gen = settings["general"]
            for key in ["always_listening", "continuous_mode"]:
                if key in gen:
                    validated["general"][key] = bool(gen[key])
            if "timeout_seconds" in gen:
                validated["general"]["timeout_seconds"] = max(1, min(60, int(gen["timeout_seconds"])))
        
        return validated
    
    def _merge_with_defaults(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Merge loaded settings with defaults to ensure all keys exist"""
        merged = DEFAULT_SETTINGS.copy()
        
        for category in ["tts", "stt", "wake_word", "general"]:
            if category in settings:
                merged[category].update(settings[category])
        
        return merged
    
    def get_tts_settings(self) -> Dict[str, Any]:
        """Get TTS settings"""
        return self.settings.get("tts", DEFAULT_SETTINGS["tts"])
    
    def get_stt_settings(self) -> Dict[str, Any]:
        """Get STT settings"""
        return self.settings.get("stt", DEFAULT_SETTINGS["stt"])
    
    def update_tts_voice(self, voice_id: str, voice_name: str) -> bool:
        """Update TTS voice"""
        if voice_id in VALID_VOICE_IDS:
            self.settings["tts"]["voice_id"] = voice_id
            self.settings["tts"]["voice_name"] = voice_name
            return self.save_settings()
        return False
    
    def update_stt_engine(self, engine: str) -> bool:
        """Update STT engine"""
        if engine in VALID_STT_ENGINES:
            self.settings["stt"]["engine"] = engine
            return self.save_settings()
        return False
    
    def toggle_feature(self, feature: str, enabled: bool) -> bool:
        """Toggle a feature on/off"""
        valid_features = {
            "tts": ("tts", "enabled"),
            "stt": ("stt", "enabled"),
            "wake_word": ("wake_word", "enabled"),
            "always_listening": ("general", "always_listening"),
            "noise_reduction": ("stt", "noise_reduction")
        }
        
        if feature in valid_features:
            category, key = valid_features[feature]
            self.settings[category][key] = bool(enabled)
            return self.save_settings()
        return False


# Global instance
_settings_manager = None

def get_settings_manager() -> VoiceSettingsManager:
    """Get global settings manager instance"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = VoiceSettingsManager()
    return _settings_manager

