"""
Universal Settings Manager — SINGLE SOURCE OF TRUTH
====================================================
Every file in the project imports settings from HERE.
No hardcoded provider names, model names, or config values anywhere else.

Usage:
    from settings_manager import get_provider, get_model, get_voice_config
    
    provider = get_provider()    # "gemini" / "gguf" / "openai" / "ollama"
    model = get_model()          # "gemini-2.5-flash" etc.
    voice = get_voice_config()   # Full voice settings dict
"""

import os
import json
import threading
import logging
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)

# ─── Resolve the single settings file path ────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent  # backend/ -> project root
_SETTINGS_FILE = _PROJECT_ROOT / 'data' / 'user_preferences' / 'settings.json'

# Ensure .env is loaded
try:
    from dotenv import load_dotenv
    _env_file = _PROJECT_ROOT / '.env'
    if _env_file.exists():
        load_dotenv(_env_file)
    else:
        load_dotenv()
except ImportError:
    pass

# ─── Thread-safe cache ────────────────────────────────────────────────────────
_cache_lock = threading.Lock()
_settings_cache: dict = {}
_settings_mtime: float = 0

# ─── DEFAULTS — The ONE place all defaults live ──────────────────────────────
DEFAULTS = {
    "general": {
        "animations": True,
        "enableHinglish": True,
        "language": "en-US",
        "secondaryLanguage": "hi-IN",
        "startOnBoot": True,
        "theme": "dark"
    },
    "security": {
        "apiKeys": {
            "googleGemini": "",
            "openAI": "",
            "anthropic": "",
            "elevenLabs": ""
        },
        "permissions": {
            "allowFileDeletion": False,
            "allowAppExecution": True,
            "allowWebBrowsing": True,
            "allowSystemControl": True
        },
        "encryption": {
            "encryptDatabase": True,
            "enablePinParams": False
        }
    },
    "ai": {
        "defaultProvider": "gemini",
        "defaultModel": "gemini-2.5-flash",
        "temperature": 0.7,
        "maxTokens": 2048,
        "contextWindow": 4096,
        "safetySettings": {
            "dangerousContent": "block_none",
            "harassment": "block_none",
            "hateSpeech": "block_none",
            "sexuallyExplicit": "block_none"
        },
        "localLlm": {
            "enabled": True,
            "modelPath": "models/pulsar-final-q4_k_m.gguf",
            "useGpu": False
        }
    },
    "voice": {
        "tts": {
            "enabled": True,
            "engine": "edge_tts",
            "voice_id": "en-US-AriaNeural",
            "voice_name": "Aria",
            "speed": 1.0,
            "pitch": 1,
            "volume": 0.9,
            "useCache": True
        },
        "stt": {
            "enabled": True,
            "engine": "whisper",
            "model": "whisper-small",
            "sensitivity": 0.5,
            "language": "hi-IN",
            "continuous": True,
            "noise_reduction": True
        },
        "wakeWord": {
            "enabled": False,
            "phrases": ["hey assistant", "hey daddy"],
            "sensitivity": 0.5
        }
    },
    "automation": {
        "autoUpdate": True,
        "autoBackup": "weekly",
        "maxHistorySize": 1000,
        "smartHome": {
            "enabled": False,
            "provider": "none"
        }
    },
    "system": {
        "logLevel": "INFO",
        "maxLogSizeMb": 10,
        "minimizeToTray": True,
        "notifications": {
            "desktop": True,
            "sound": True
        }
    }
}


# ─── Core: Read settings from disk (cached) ──────────────────────────────────

def _load_settings() -> dict:
    """Load settings from disk, using cache if file hasn't changed."""
    global _settings_cache, _settings_mtime
    
    with _cache_lock:
        try:
            if _SETTINGS_FILE.exists():
                current_mtime = os.path.getmtime(_SETTINGS_FILE)
                if current_mtime > _settings_mtime or not _settings_cache:
                    with open(_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                        _settings_cache = json.load(f)
                    _settings_mtime = current_mtime
                    logger.debug(f"Settings reloaded from {_SETTINGS_FILE}")
            else:
                if not _settings_cache:
                    _settings_cache = DEFAULTS.copy()
                    logger.info("Settings file not found, using defaults")
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            if not _settings_cache:
                _settings_cache = DEFAULTS.copy()
    
    return _settings_cache


def invalidate_cache():
    """Force reload on next access. Call this after saving settings."""
    global _settings_mtime
    with _cache_lock:
        _settings_mtime = 0
    logger.debug("Settings cache invalidated")


# ─── Getters: Full sections ──────────────────────────────────────────────────

def get_settings() -> dict:
    """Get the full settings dictionary (cached)."""
    return _load_settings()


def get_ai_settings() -> dict:
    """Get the AI section of settings."""
    settings = _load_settings()
    return settings.get('ai', DEFAULTS['ai'])


def get_voice_config() -> dict:
    """Get the full voice configuration section."""
    settings = _load_settings()
    return settings.get('voice', DEFAULTS['voice'])


def get_general_settings() -> dict:
    """Get the general section of settings."""
    settings = _load_settings()
    return settings.get('general', DEFAULTS['general'])


def get_security_settings() -> dict:
    """Get the security section of settings."""
    settings = _load_settings()
    return settings.get('security', DEFAULTS['security'])


# ─── Getters: AI Provider & Model ────────────────────────────────────────────

def get_provider() -> str:
    """Get the active AI provider. Returns 'gemini', 'gguf', 'openai', or 'ollama'."""
    ai = get_ai_settings()
    provider = ai.get('defaultProvider', DEFAULTS['ai']['defaultProvider'])
    
    # Normalize legacy identifiers
    if provider == 'google':
        provider = 'gemini'
    elif provider == 'local':
        provider = 'gguf'
    
    # Validate provider has required API key (safety net)
    if provider == 'gemini' and not get_api_key('gemini'):
        gguf_path = _PROJECT_ROOT / 'models' / 'pulsar-final-q4_k_m.gguf'
        if gguf_path.exists():
            logger.warning("Gemini API key not found, falling back to GGUF")
            return 'gguf'
    elif provider == 'openai' and not get_api_key('openai'):
        logger.warning("OpenAI API key not found, checking alternatives")
        if get_api_key('gemini'):
            return 'gemini'
    
    return provider


def get_model() -> str:
    """Get the active AI model name."""
    ai = get_ai_settings()
    model = ai.get('defaultModel', DEFAULTS['ai']['defaultModel'])
    
    # If provider is GGUF, always use the local model
    provider = get_provider()
    if provider == 'gguf':
        return 'pulsar-final-q4_k_m'
    
    return model


def get_temperature() -> float:
    """Get the user-configured temperature for general chat."""
    ai = get_ai_settings()
    return float(ai.get('temperature', DEFAULTS['ai']['temperature']))


def get_max_tokens() -> int:
    """Get the user-configured max tokens for general chat."""
    ai = get_ai_settings()
    return int(ai.get('maxTokens', DEFAULTS['ai']['maxTokens']))


def get_context_window() -> int:
    """Get the context window size."""
    ai = get_ai_settings()
    return int(ai.get('contextWindow', DEFAULTS['ai']['contextWindow']))


# ─── Getters: Voice Settings ─────────────────────────────────────────────────

def get_tts_config() -> dict:
    """Get TTS configuration."""
    voice = get_voice_config()
    return voice.get('tts', DEFAULTS['voice']['tts'])


def get_tts_voice_id() -> str:
    """Get the active TTS voice ID."""
    tts = get_tts_config()
    return tts.get('voice_id', DEFAULTS['voice']['tts']['voice_id'])


def get_stt_config() -> dict:
    """Get STT configuration."""
    voice = get_voice_config()
    return voice.get('stt', DEFAULTS['voice']['stt'])


def get_stt_language() -> str:
    """Get the STT language code (e.g., 'hi-IN', 'en-US')."""
    stt = get_stt_config()
    return stt.get('language', DEFAULTS['voice']['stt']['language'])


def get_stt_language_short() -> str:
    """Get short STT language code for Whisper (e.g., 'hi' from 'hi-IN')."""
    lang = get_stt_language()
    if '-' in lang:
        return lang.split('-')[0]
    return lang


def get_stt_engine() -> str:
    """Get the active STT engine ('whisper', 'google')."""
    stt = get_stt_config()
    return stt.get('engine', DEFAULTS['voice']['stt']['engine'])


def get_wake_words() -> list:
    """Get the list of wake word phrases."""
    voice = get_voice_config()
    wake = voice.get('wakeWord', DEFAULTS['voice']['wakeWord'])
    return wake.get('phrases', DEFAULTS['voice']['wakeWord']['phrases'])


def is_wake_word_enabled() -> bool:
    """Check if wake word detection is enabled."""
    voice = get_voice_config()
    wake = voice.get('wakeWord', DEFAULTS['voice']['wakeWord'])
    return wake.get('enabled', False)


# ─── Getters: API Keys ───────────────────────────────────────────────────────

def get_api_key(provider: str) -> Optional[str]:
    """
    Get API key for a provider. Checks:
    1. OS environment variables (highest priority)
    2. OS Keyring (secure storage)
    
    Args:
        provider: 'gemini', 'openai', 'anthropic', 'elevenlabs'
    """
    env_map = {
        'gemini': ['GEMINI_API_KEY', 'GOOGLE_GEMINI_API_KEY'],
        'openai': ['OPENAI_API_KEY'],
        'anthropic': ['ANTHROPIC_API_KEY'],
        'elevenlabs': ['ELEVEN_LABS_API_KEY', 'ELEVENLABS_API_KEY'],
    }
    
    env_names = env_map.get(provider.lower(), [])
    for env_name in env_names:
        key = os.getenv(env_name)
        if key and key.strip():
            return key.strip()
    
    # Try OS Keyring
    try:
        from ai_assistant.utils.secure_storage import get_secure_key
        keyring_map = {
            'gemini': 'googleGemini',
            'openai': 'openAI',
            'anthropic': 'anthropic',
            'elevenlabs': 'elevenLabs',
        }
        keyring_name = keyring_map.get(provider.lower())
        if keyring_name:
            key = get_secure_key(keyring_name)
            if key and key.strip() and key != '********':
                return key.strip()
    except Exception:
        pass
    
    return None


# ─── Feature Flags ────────────────────────────────────────────────────────────

def is_file_deletion_allowed() -> bool:
    """Check if file deletion is permitted."""
    sec = get_security_settings()
    perms = sec.get('permissions', {})
    return perms.get('allowFileDeletion', False)


def is_app_execution_allowed() -> bool:
    """Check if app execution is permitted."""
    sec = get_security_settings()
    perms = sec.get('permissions', {})
    return perms.get('allowAppExecution', True)


# ─── Available providers/models (for UI dropdowns) ───────────────────────────

AVAILABLE_PROVIDERS = [
    {"id": "gemini", "name": "Google Gemini", "icon": "\U0001f537", "type": "online"},
    {"id": "openai", "name": "OpenAI (GPT)", "icon": "\U0001f7e2", "type": "online"},
    {"id": "gguf", "name": "Pulsar (Local GGUF)", "icon": "\U0001f9e0", "type": "offline"},
    {"id": "ollama", "name": "Ollama (Local)", "icon": "\U0001f916", "type": "offline"},
]

AVAILABLE_MODELS = {
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro"],
    "openai": ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o"],
    "gguf": ["pulsar-final-q4_k_m"],
    "ollama": ["llama3.2", "qwen2.5-coder:3b", "mistral", "gemma2"],
}


def get_default_model_for_provider(provider: str) -> str:
    """Get the default model for a given provider."""
    models = AVAILABLE_MODELS.get(provider, [])
    if models:
        return models[0]
    return DEFAULTS['ai']['defaultModel']
