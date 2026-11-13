"""
Voice Settings Manager

Handles persistence and validation of voice settings (TTS/STT).
"""

import copy
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
        "engine": "edge_tts",
        "voice_id": "hi-IN-SwaraNeural",
        "voice_name": "Swara (Hindi Online)",
        "speed": 1.0,
        "pitch": 1.0,
        "volume": 0.9
    },
    "stt": {
        "enabled": True,
        "engine": "whisper",  # whisper, google
        "language": "hi-IN",
        "noise_reduction": True,
        "vad_enabled": True
    },
    "wake_word": {
        "enabled": True,
        "phrase": "hey pulsar",
        "sensitivity": 0.6
    },
    "persona": {
        "style": "jarvis",
        "assistantName": "Pulsar",
        "userTitle": "Boss",
        "languageMode": "auto",
        "wakeAckEnabled": True,
        "preTaskReports": True,
        "postTaskReports": True,
        "dynamicGeneration": True,
        "recentMemorySize": 18
    },
    "general": {
        "always_listening": True,
        "continuous_mode": False,
        "timeout_seconds": 5
    }
}

# Valid voice IDs (Online EdgeTTS + Offline KittenTTS mini-0.8)
VALID_VOICE_IDS = [
    "en-US-AriaNeural", "en-US-JennyNeural", "en-US-GuyNeural",
    "en-US-DavisNeural", "en-GB-SoniaNeural", "en-GB-RyanNeural",
    "en-IN-NeerjaNeural", "en-IN-PrabhatNeural", "en-US-AnaNeural",
    "en-US-ChristopherNeural", "en-GB-LibbyNeural", "en-US-EricNeural",
    "hi-IN-SwaraNeural", "hi-IN-MadhurNeural",
    "kittentts",
    "kitten:Bella", "kitten:Jasper", "kitten:Luna", "kitten:Bruno",
    "kitten:Rosie", "kitten:Hugo", "kitten:Kiki", "kitten:Leo",
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
        """Load settings from file and synchronize with unified settings_manager."""
        base = copy.deepcopy(DEFAULT_SETTINGS)
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                logger.info("Loaded voice settings from file")
                base = self._merge_with_defaults(settings)
            except Exception as e:
                logger.error(f"Error loading settings: {e}. Using defaults.")

        # Overlay canonical unified voice settings so /api/voice/settings matches /api/settings/all
        try:
            from settings_manager import get_voice_config
            unified = get_voice_config()
            if isinstance(unified, dict):
                if isinstance(unified.get("tts"), dict):
                    base["tts"].update(unified["tts"])
                if isinstance(unified.get("stt"), dict):
                    for k in ("enabled", "engine", "language", "noise_reduction"):
                        if k in unified["stt"]:
                            base["stt"][k] = unified["stt"][k]
                if isinstance(unified.get("wakeWord"), dict):
                    ww = unified["wakeWord"]
                    if "enabled" in ww:
                        base["wake_word"]["enabled"] = bool(ww["enabled"])
                    if isinstance(ww.get("phrases"), list) and ww["phrases"]:
                        base["wake_word"]["phrase"] = str(ww["phrases"][0])
                    if "sensitivity" in ww:
                        base["wake_word"]["sensitivity"] = float(ww["sensitivity"])
                if isinstance(unified.get("persona"), dict):
                    base.setdefault("persona", {}).update(unified["persona"])
        except Exception:
            pass
        return base

    def save_settings(self, settings: Optional[Dict[str, Any]] = None, sync_unified: bool = True) -> bool:
        """Save settings to file and sync bidirectionally with unified settings_manager."""
        if settings is not None:
            merged_in = self.load_settings()
            for cat in ("tts", "stt", "wake_word", "persona", "general"):
                if isinstance(settings.get(cat), dict):
                    merged_in.setdefault(cat, {})
                    if isinstance(merged_in[cat], dict):
                        merged_in[cat].update(settings[cat])
            self.settings = merged_in

        try:
            validated = self.validate_settings(self.settings)
            self.settings = validated

            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(validated, f, indent=2)

            if sync_unified:
                try:
                    from settings_manager import update_settings_and_sync
                    tts_v = validated.get("tts", {})
                    stt_v = validated.get("stt", {})
                    ww_v = validated.get("wake_word", {})
                    persona_v = validated.get("persona", {})
                    voice_payload = {
                        "tts": {
                            "enabled": bool(tts_v.get("enabled", True)),
                            "engine": tts_v.get("engine", "edge_tts"),
                            "voice_id": tts_v.get("voice_id", "hi-IN-SwaraNeural"),
                            "voice_name": tts_v.get("voice_name", "Swara (Hindi Online)"),
                            "speed": float(tts_v.get("speed", 1.0)),
                            "pitch": float(tts_v.get("pitch", 1.0)),
                            "volume": float(tts_v.get("volume", 0.9)),
                        },
                        "stt": {
                            "enabled": bool(stt_v.get("enabled", True)),
                            "engine": stt_v.get("engine", "whisper"),
                            "language": stt_v.get("language", "hi-IN"),
                            "noise_reduction": bool(stt_v.get("noise_reduction", True)),
                        },
                        "wakeWord": {
                            "enabled": bool(ww_v.get("enabled", True)),
                            "sensitivity": float(ww_v.get("sensitivity", 0.6)),
                        },
                        "persona": copy.deepcopy(persona_v),
                    }
                    update_settings_and_sync("voice", voice_payload)
                except Exception as sync_err:
                    logger.debug(f"Could not sync voice settings to unified store: {sync_err}")

            logger.info(f"Settings saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False

    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize settings"""
        validated = copy.deepcopy(DEFAULT_SETTINGS)

        # Validate TTS
        if "tts" in settings:
            tts = settings["tts"]
            vid = tts.get("voice_id")
            if vid in VALID_VOICE_IDS:
                validated["tts"]["voice_id"] = vid
            elif vid:
                validated["tts"]["voice_id"] = str(vid)
            eff_vid = validated["tts"]["voice_id"]
            if eff_vid == "kittentts" or str(eff_vid).lower().startswith("kitten:"):
                validated["tts"]["engine"] = "kittentts"
            elif "neural" in str(eff_vid).lower():
                validated["tts"]["engine"] = "edge_tts"
            elif tts.get("engine") in ("edge_tts", "kittentts", "pyttsx3"):
                validated["tts"]["engine"] = tts["engine"]
            else:
                validated["tts"]["engine"] = "edge_tts"
            if "voice_name" in tts:
                validated["tts"]["voice_name"] = tts["voice_name"]
            if "enabled" in tts:
                validated["tts"]["enabled"] = bool(tts["enabled"])

            # Validate numeric ranges
            for key in ["speed", "pitch"]:
                if key in tts:
                    value = float(tts[key])
                    validated["tts"][key] = max(0.5, min(2.0, value))
            if "volume" in tts:
                validated["tts"]["volume"] = max(0.0, min(1.5, float(tts["volume"])))

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

        # Validate persona
        if "persona" in settings and isinstance(settings["persona"], dict):
            p = settings["persona"]
            valid_styles = {"jarvis", "friendly", "concise", "bilingual_buddy"}
            valid_lang_modes = {"auto", "hinglish", "hindi", "english"}
            if p.get("style") in valid_styles:
                validated["persona"]["style"] = p["style"]
            if p.get("languageMode") in valid_lang_modes:
                validated["persona"]["languageMode"] = p["languageMode"]
            if isinstance(p.get("assistantName"), str) and p["assistantName"].strip():
                validated["persona"]["assistantName"] = p["assistantName"].strip()[:40]
            if isinstance(p.get("userTitle"), str) and p["userTitle"].strip():
                validated["persona"]["userTitle"] = p["userTitle"].strip()[:40]
            for bkey in ("wakeAckEnabled", "preTaskReports", "postTaskReports", "dynamicGeneration"):
                if bkey in p:
                    validated["persona"][bkey] = bool(p[bkey])
            if "recentMemorySize" in p:
                try:
                    validated["persona"]["recentMemorySize"] = max(5, min(50, int(p["recentMemorySize"])))
                except (TypeError, ValueError):
                    pass

        return validated

    def _merge_with_defaults(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Merge loaded settings with defaults to ensure all keys exist"""
        merged = copy.deepcopy(DEFAULT_SETTINGS)

        for category in ["tts", "stt", "wake_word", "persona", "general"]:
            if category in settings and isinstance(settings[category], dict):
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

