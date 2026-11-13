"""
Universal Settings Manager — SINGLE SOURCE OF TRUTH
====================================================
Every file in the project imports settings from HERE.
No hardcoded provider names, model names, or config values anywhere else.

Usage:
    from settings_manager import get_provider, get_model, get_voice_config
    
    provider = get_provider()    # "gemini" / "gguf" / "openai"
    model = get_model()          # "gemini-2.5-flash" etc.
    voice = get_voice_config()   # Full voice settings dict
"""

import os
import sys
import copy
import json
import threading
import logging
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Unify settings_manager / backend.settings_manager imports to one module object
_this_sm = sys.modules.get(__name__)
if _this_sm is not None:
    sys.modules.setdefault('settings_manager', _this_sm)
    sys.modules.setdefault('backend.settings_manager', _this_sm)


def is_frozen() -> bool:
    """Return True when running inside a packaged PyInstaller executable."""
    return bool(getattr(sys, 'frozen', False))


def get_bundle_root() -> Path:
    """Return the read-only root directory where bundled code/assets live."""
    if is_frozen():
        return Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)).resolve()
    return Path(__file__).resolve().parent.parent


def get_writable_root() -> Path:
    """Return writable per-user data root (%LOCALAPPDATA%\\PulsarAI when packaged)."""
    override = os.environ.get('PULSAR_DATA_DIR')
    if override and override.strip():
        root = Path(override.strip()).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root
    if is_frozen():
        appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~/.pulsar_ai'))
        root = Path(appdata) / 'PulsarAI'
        root.mkdir(parents=True, exist_ok=True)
        return root
    return Path(__file__).resolve().parent.parent


def get_settings_file() -> Path:
    """Single canonical writable path for settings.json."""
    return get_writable_root() / 'data' / 'user_preferences' / 'settings.json'


def get_env_file() -> Path:
    """Single canonical writable path for .env secrets."""
    writable_env = get_writable_root() / '.env'
    if writable_env.exists() or is_frozen() or bool(os.environ.get('PULSAR_DATA_DIR', '').strip()):
        return writable_env
    return get_bundle_root() / '.env'


def get_logs_root() -> Path:
    """Single canonical writable directory for application logs."""
    logs_dir = get_writable_root() / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def discover_gguf_models() -> list:
    """Discover local .gguf model stems across writable, exe, and bundle models/ dirs."""
    search_dirs = [
        get_writable_root() / 'models',
        (Path(sys.executable).parent / 'models') if is_frozen() else None,
        get_bundle_root() / 'models',
        Path(__file__).resolve().parent.parent / 'models',
    ]
    stems: list = []
    seen = set()
    for d in search_dirs:
        if d is None or not d.exists() or not d.is_dir():
            continue
        for gfile in sorted(d.glob('*.gguf')):
            stem = gfile.stem
            if stem.lower() not in seen:
                seen.add(stem.lower())
                stems.append(stem)

    if not stems:
        return ['pulsar-final-q4_k_m']

    # Put pulsar-final-q4_k_m first as canonical default when present
    for idx, s in enumerate(stems):
        if s.lower() == 'pulsar-final-q4_k_m':
            if idx != 0:
                stems.insert(0, stems.pop(idx))
            break
    return stems


def resolve_local_model_path(relative_or_abs: str) -> Path:
    """Locate a local GGUF/model file across writable AppData, exe dir, and bundle root."""
    p = Path(relative_or_abs)
    if p.is_absolute() and p.exists():
        return p
    candidates = [
        get_writable_root() / relative_or_abs,
        Path(sys.executable).parent / relative_or_abs if is_frozen() else None,
        get_bundle_root() / relative_or_abs,
    ]
    for cand in candidates:
        if cand is not None and cand.exists():
            return cand
    return get_writable_root() / relative_or_abs


# ─── Resolve the single settings file path ────────────────────────────────────
_PROJECT_ROOT = get_bundle_root()
_SETTINGS_FILE = get_settings_file()

# Ensure .env is loaded
try:
    from dotenv import load_dotenv
    _env_file = get_env_file()
    if _env_file.exists():
        load_dotenv(_env_file, override=False)
    else:
        _bundled_env = get_bundle_root() / '.env'
        if _bundled_env.exists():
            load_dotenv(_bundled_env, override=False)
        else:
            load_dotenv(override=False)
except ImportError:
    pass

# ─── Thread-safe cache ────────────────────────────────────────────────────────
_cache_lock = threading.Lock()
_settings_cache: dict = {}
_settings_mtime: float = 0

# ─── DEFAULTS — The ONE place all defaults live ──────────────────────────────
DEFAULTS = {
    "onboarded": False,
    "general": {
        "animations": True,
        "enableHinglish": True,
        "language": "en-US",
        "secondaryLanguage": "hi-IN",
        "startOnBoot": True,
        "theme": "dark",
        "hotkey": "Alt+Space",
        "hotkeyEnabled": True
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
            "voice_id": "hi-IN-SwaraNeural",
            "voice_name": "Swara (Hindi Online)",
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
            "enabled": True,
            "phrases": ["hey pulsar", "pulsar", "hey assistant", "ok pulsar"],
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
            "recentMemorySize": 18,
            "customInstructions": ""
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
        "desktopOverlay": True,
        "screenShareStealth": True,
        "companion": {
            "alwaysOnTop": True,
            "size": "medium",
            "opacity": 90,
            "autoHide": True
        },
        "notifications": {
            "desktop": True,
            "sound": True
        }
    }
}


# ─── Core: Read settings from disk (cached) ──────────────────────────────────

def _load_settings() -> dict:
    """Load settings from disk, deep-merged with DEFAULTS, using cache if unchanged."""
    global _settings_cache, _settings_mtime

    settings_file = get_settings_file()
    with _cache_lock:
        try:
            if settings_file.exists():
                current_mtime = os.path.getmtime(settings_file)
                if current_mtime > _settings_mtime or not _settings_cache:
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        loaded = json.load(f)
                    merged = copy.deepcopy(DEFAULTS)
                    if isinstance(loaded, dict):
                        deep_merge_settings(merged, loaded)
                    _settings_cache = merged
                    _settings_mtime = current_mtime
                    logger.debug(f"Settings reloaded from {settings_file}")
            else:
                if not _settings_cache:
                    _settings_cache = copy.deepcopy(DEFAULTS)
                    logger.info("Settings file not found, using defaults")
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            if not _settings_cache:
                _settings_cache = copy.deepcopy(DEFAULTS)

    return _settings_cache


def invalidate_cache():
    """Force reload on next access. Call this after saving settings."""
    global _settings_mtime
    import sys
    with _cache_lock:
        _settings_mtime = 0
    for alias in ("settings_manager", "backend.settings_manager"):
        mod = sys.modules.get(alias)
        if mod is not None and getattr(mod, "_cache_lock", None) is not None and mod is not sys.modules.get(__name__):
            try:
                with mod._cache_lock:
                    mod._settings_mtime = 0
            except Exception:
                pass
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
    """Get the active AI provider. Returns 'gemini', 'gguf', or 'openai'."""
    ai = get_ai_settings()
    provider = str(ai.get('defaultProvider', DEFAULTS['ai']['defaultProvider']) or '').strip().lower()
    
    # Normalize legacy/unknown identifiers cleanly to supported providers
    if provider == 'google':
        provider = 'gemini'
    elif provider not in ('gemini', 'openai', 'gguf'):
        provider = 'gguf'
    
    # Validate provider has required API key (do NOT override explicit user 'gguf' choice)
    if provider == 'gemini' and not get_api_key('gemini'):
        model_rel = ai.get('localLlm', {}).get('modelPath', 'models/pulsar-final-q4_k_m.gguf')
        gguf_path = resolve_local_model_path(model_rel)
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
    model = str(ai.get('defaultModel', DEFAULTS['ai']['defaultModel']) or '').strip()

    provider = get_provider()
    if provider == 'gguf':
        discovered = discover_gguf_models()
        model_stem = Path(model).stem if model.lower().endswith('.gguf') else model
        for d in discovered:
            if d.lower() == model_stem.lower():
                return d
        # Fall back to configured localLlm.modelPath if defaultModel held a cloud model
        local_path = str((ai.get('localLlm') or {}).get('modelPath') or '').strip()
        if local_path:
            lp_stem = Path(local_path).stem
            for d in discovered:
                if d.lower() == lp_stem.lower():
                    return d
        return discovered[0]

    ml = model.lower()
    if (
        not model
        or 'pulsar' in ml
        or (provider == 'gemini' and 'gemini' not in ml)
        or (provider == 'openai' and 'gpt' not in ml and not ml.startswith('o1') and not ml.startswith('o3'))
    ):
        return get_default_model_for_provider(provider)

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


def get_tts_engine() -> str:
    """Get the active TTS engine (canonical unified setting)."""
    tts = get_tts_config()
    eng = str(tts.get('engine', '') or '').strip().lower()
    if eng:
        return eng
    vid = str(tts.get('voice_id', '') or '').strip().lower()
    if vid == 'kittentts' or vid.startswith('kitten:'):
        return 'kittentts'
    if 'neural' in vid:
        return 'edge_tts'
    return DEFAULTS['voice']['tts']['engine']


def get_stt_config() -> dict:
    """Get STT configuration."""
    voice = get_voice_config()
    return voice.get('stt', DEFAULTS['voice']['stt'])


def get_stt_model() -> str:
    """Get configured Whisper STT model size (e.g., 'small' from 'whisper-small')."""
    stt = get_stt_config()
    raw = str(stt.get('model', DEFAULTS['voice']['stt']['model']) or 'whisper-small').strip().lower()
    if raw.startswith('whisper-'):
        raw = raw[len('whisper-'):]
    return raw or 'small'


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


def get_wake_word() -> str:
    """Get the primary wake word phrase."""
    words = get_wake_words()
    return words[0] if words else "hey pulsar"


def is_wake_word_enabled() -> bool:
    """Check if wake word detection is enabled."""
    voice = get_voice_config()
    wake = voice.get('wakeWord', DEFAULTS['voice']['wakeWord'])
    return bool(wake.get('enabled', True))


def get_persona_config() -> dict:
    """Get unified assistant persona configuration (JARVIS style, language mode, pre/post reports)."""
    voice = get_voice_config()
    base = copy.deepcopy(DEFAULTS['voice']['persona'])
    persona = voice.get('persona')
    if isinstance(persona, dict):
        base.update(persona)
    return base


def get_system_settings() -> dict:
    """Get the system section of settings."""
    settings = _load_settings()
    return settings.get('system', DEFAULTS['system'])


def is_desktop_overlay_enabled() -> bool:
    """Check if minimized transparent desktop orb overlay is enabled."""
    sys_cfg = get_system_settings()
    return bool(sys_cfg.get('desktopOverlay', True))


def is_screen_share_stealth_enabled() -> bool:
    """Check if desktop orb is hidden from screen capture/sharing (WDA_EXCLUDEFROMCAPTURE)."""
    sys_cfg = get_system_settings()
    return bool(sys_cfg.get('screenShareStealth', True))


def get_companion_settings() -> dict:
    """Get desktop companion mascot configuration."""
    sys_cfg = get_system_settings()
    base = copy.deepcopy(DEFAULTS['system']['companion'])
    comp = sys_cfg.get('companion')
    if isinstance(comp, dict):
        base.update(comp)
    return base


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


# ─── Feature Flags & OS Sync ──────────────────────────────────────────────────

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


def is_system_control_allowed() -> bool:
    """Check if system-level control commands are permitted."""
    sec = get_security_settings()
    perms = sec.get('permissions', {})
    return perms.get('allowSystemControl', True)


def is_web_browsing_allowed() -> bool:
    """Check if web browsing / online research is permitted."""
    sec = get_security_settings()
    perms = sec.get('permissions', {})
    return perms.get('allowWebBrowsing', True)


def is_onboarded() -> bool:
    """Return True if first-run onboarding has been completed."""
    return bool(_load_settings().get('onboarded', False))


def sync_windows_startup(enabled: bool) -> bool:
    """Sync general.startOnBoot with Windows HKCU Run startup registry key."""
    if sys.platform != 'win32':
        return False
    try:
        import winreg
        run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        value_name = "PulsarAIAssistant"

        if enabled:
            exe_cmd = None
            if is_frozen():
                exe_cmd = f'"{sys.executable}"'
            else:
                local_app_data = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')))
                installed_candidates = [
                    local_app_data / 'Programs' / 'PulsarAI' / 'Pulsar_AI_Assistant.exe',
                    local_app_data / 'Pulsar_Assistant' / 'Pulsar_AI_Assistant.exe',
                ]
                for cand in installed_candidates:
                    if cand.exists():
                        exe_cmd = f'"{cand}"'
                        break
            if not exe_cmd:
                logger.info("Dev environment without packaged exe: skipping HKCU Run registry write")
                return True
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, run_key_path) as key:
                winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, exe_cmd)
            logger.info(f"Windows startup enabled: {exe_cmd}")
            return True
        else:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key_path, 0, winreg.KEY_SET_VALUE) as key:
                try:
                    winreg.DeleteValue(key, value_name)
                    logger.info("Windows startup entry removed")
                except FileNotFoundError:
                    pass
            return True
    except Exception as e:
        logger.warning(f"Failed to sync Windows startup registry: {e}")
        return False


# ─── Available providers/models (for UI dropdowns) ───────────────────────────

AVAILABLE_PROVIDERS = [
    {"id": "gemini", "name": "Google Gemini", "icon": "\U0001f537", "type": "online"},
    {"id": "openai", "name": "OpenAI (GPT)", "icon": "\U0001f7e2", "type": "online"},
    {"id": "gguf", "name": "Pulsar (Local GGUF)", "icon": "\U0001f9e0", "type": "offline"},
]

AVAILABLE_MODELS = {
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro"],
    "openai": ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o"],
    "gguf": discover_gguf_models(),
}


def get_available_models() -> dict:
    """Return available models dict with live GGUF discovery."""
    models = {k: list(v) for k, v in AVAILABLE_MODELS.items()}
    models["gguf"] = discover_gguf_models()
    return models


def get_default_model_for_provider(provider: str) -> str:
    """Get the default model for a given provider."""
    prov = str(provider or "").strip().lower()
    if prov == 'google':
        prov = 'gemini'
    elif prov not in ('gemini', 'openai', 'gguf'):
        prov = 'gguf'
    if prov == 'gguf':
        discovered = discover_gguf_models()
        if discovered:
            return discovered[0]
    models = AVAILABLE_MODELS.get(prov, [])
    if models:
        return models[0]
    return DEFAULTS['ai']['defaultModel']


# ─── Unified Settings Mutation & Live Sync (Single Source of Truth) ──────────
_settings_write_lock = threading.Lock()


def deep_merge_settings(base: dict, override: dict) -> dict:
    """Recursively merge `override` into `base` without dropping nested default keys."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            deep_merge_settings(base[k], v)
        else:
            base[k] = v
    return base


def build_merged_settings(saved_settings: Optional[dict], available_voices: Optional[list] = None) -> dict:
    """Return DEFAULTS deep-merged with `saved_settings` plus dynamic voice list."""
    import copy
    merged = copy.deepcopy(DEFAULTS)
    if isinstance(saved_settings, dict):
        deep_merge_settings(merged, saved_settings)
    if available_voices is None:
        try:
            try:
                from voice_service import AVAILABLE_VOICES
            except ImportError:
                from backend.voice_service import AVAILABLE_VOICES
            available_voices = AVAILABLE_VOICES
        except Exception:
            available_voices = []
    if "voice" in merged and "tts" in merged["voice"]:
        merged["voice"]["tts"]["available_voices"] = available_voices
    return merged


def _get_active_socketio():
    """Locate active SocketIO instance across loaded modules cleanly."""
    import sys
    for mod_path in ("routes.common", "backend.routes.common"):
        mod = sys.modules.get(mod_path)
        if mod is not None:
            try:
                sio = mod.get_socketio()
                if sio:
                    return sio
            except Exception:
                pass
    for mod_path in ("voice_service", "backend.voice_service"):
        mod = sys.modules.get(mod_path)
        if mod is not None:
            try:
                sio = getattr(mod, "_socketio", None)
                if sio:
                    return sio
            except Exception:
                pass
    return None


def reset_all_llm_sessions():
    """Reset cached chat/assistant LLM instances across loaded backend modules so updated settings take effect immediately."""
    import sys

    for mod_path in ("voice_service", "backend.voice_service"):
        mod = sys.modules.get(mod_path)
        if mod is not None:
            try:
                if hasattr(mod, "reset_llm_sessions"):
                    mod.reset_llm_sessions()
                if hasattr(mod, "get_active_assistant"):
                    inst = mod.get_active_assistant()
                    if inst and hasattr(inst, "reset_llm_session"):
                        inst.reset_llm_session()
            except Exception:
                pass

    for mod_path in ("routes.chat_routes", "backend.routes.chat_routes"):
        mod = sys.modules.get(mod_path)
        if mod is not None:
            try:
                if hasattr(mod, "clear_chat_sessions"):
                    mod.clear_chat_sessions()
            except Exception:
                pass

    for mod_path in ("routes.common", "backend.routes.common"):
        mod = sys.modules.get(mod_path)
        if mod is not None:
            try:
                if hasattr(mod, "get_assistant"):
                    inst = mod.get_assistant()
                    if inst and hasattr(inst, "reset_llm_session"):
                        inst.reset_llm_session()
            except Exception:
                pass


def update_settings_and_sync(
    category: str,
    settings_data: dict,
    broadcast_fn=None,
) -> dict:
    """
    Single centralized entry point for mutating settings.json, updating keyring/env keys,
    invalidating caches, resetting cached LLM sessions, and broadcasting SocketIO events.
    """
    import copy
    from datetime import datetime

    if not category or not isinstance(settings_data, dict) or not settings_data:
        return {"success": False, "error": "Category and non-empty settings dict required"}

    payload_copy = copy.deepcopy(settings_data)

    settings_file = get_settings_file()

    with _settings_write_lock:
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                all_settings = json.load(f)
        else:
            all_settings = {}

        # Secure storage intercept for API keys
        if category == 'security' and 'apiKeys' in payload_copy and isinstance(payload_copy['apiKeys'], dict):
            from ai_assistant.utils.secure_storage import save_secure_key, delete_secure_key, get_secure_key
            api_keys = payload_copy['apiKeys']
            env_map = {
                "googleGemini": ["GEMINI_API_KEY", "GOOGLE_GEMINI_API_KEY"],
                "openAI": ["OPENAI_API_KEY"],
                "anthropic": ["ANTHROPIC_API_KEY"],
                "elevenLabs": ["ELEVEN_LABS_API_KEY", "ELEVENLABS_API_KEY"],
            }
            for key_name, key_val in list(api_keys.items()):
                env_vars = env_map.get(key_name, [])
                if key_val == "********":
                    actual_val = get_secure_key(key_name)
                    if actual_val:
                        for ev in env_vars:
                            os.environ[ev] = actual_val
                elif key_val == "":
                    delete_secure_key(key_name)
                    for ev in env_vars:
                        os.environ.pop(ev, None)
                else:
                    save_secure_key(key_name, key_val)
                    for ev in env_vars:
                        os.environ[ev] = key_val
                    logger.info(f"Secure Key '{key_name}' updated & loaded at runtime")

            cleaned_keys = {}
            for key_name in api_keys.keys():
                cleaned_keys[key_name] = "********" if get_secure_key(key_name) else ""
            payload_copy['apiKeys'] = cleaned_keys

        # Normalize AI provider/model updates so settings.json stays consistent
        if category == 'ai':
            existing_ai = all_settings.get('ai', {}) if isinstance(all_settings.get('ai'), dict) else {}
            if 'defaultProvider' in payload_copy:
                prov = str(payload_copy['defaultProvider']).strip().lower()
                if prov == 'google':
                    prov = 'gemini'
                elif prov not in ('gemini', 'openai', 'gguf'):
                    prov = 'gguf'
                payload_copy['defaultProvider'] = prov
            else:
                prov = str(existing_ai.get('defaultProvider') or get_provider() or 'gemini').strip().lower()
                if prov == 'google':
                    prov = 'gemini'
                elif prov not in ('gemini', 'openai', 'gguf'):
                    prov = 'gguf'

            raw_model = str(payload_copy.get('defaultModel') or existing_ai.get('defaultModel') or '').strip()
            rm_low = raw_model.lower()
            model_mismatch = (
                not raw_model
                or (prov == 'gguf' and any(t in rm_low for t in ('gemini', 'gpt-', 'claude', 'llama3.', 'qwen2.5-coder')))
                or (prov == 'gemini' and 'gemini' not in rm_low)
                or (prov == 'openai' and ('gpt' not in rm_low and not rm_low.startswith(('o1', 'o3'))))
            )
            if 'defaultProvider' in payload_copy and 'defaultModel' not in payload_copy:
                payload_copy['defaultModel'] = get_default_model_for_provider(prov)
            elif model_mismatch and ('defaultProvider' in payload_copy or 'defaultModel' in payload_copy):
                payload_copy['defaultModel'] = get_default_model_for_provider(prov)

            if prov == 'gguf':
                chosen_model = str(payload_copy.get('defaultModel') or raw_model or get_default_model_for_provider('gguf')).strip()
                stem = Path(chosen_model).stem if chosen_model.lower().endswith('.gguf') else chosen_model
                cand_rel = f"models/{stem}.gguf"
                if resolve_local_model_path(cand_rel).exists():
                    local_llm_patch = payload_copy.get('localLlm') if isinstance(payload_copy.get('localLlm'), dict) else {}
                    local_llm_patch['modelPath'] = cand_rel
                    local_llm_patch.setdefault('enabled', True)
                    payload_copy['localLlm'] = local_llm_patch

        # Keep voice.tts.engine synchronized with selected voice_id
        if category == 'voice' and isinstance(payload_copy.get('tts'), dict):
            tts_patch = payload_copy['tts']
            vid = tts_patch.get('voice_id')
            if vid:
                vid_str = str(vid).strip()
                vid_low = vid_str.lower()
                if vid_low == 'kittentts' or vid_low.startswith('kitten:'):
                    tts_patch['engine'] = 'kittentts'
                elif 'neural' in vid_low:
                    tts_patch['engine'] = 'edge_tts'
                elif vid_low in ('pyttsx3', 'sapi5') or vid_low.startswith('sapi'):
                    tts_patch['engine'] = 'pyttsx3'
            elif isinstance(tts_patch.get('engine'), str):
                eng_low = tts_patch['engine'].strip().lower()
                if eng_low in ('kittentts', 'edge_tts', 'pyttsx3'):
                    tts_patch['engine'] = eng_low

        # Normalize voice.persona updates cleanly
        if category == 'voice' and isinstance(payload_copy.get('persona'), dict):
            p_patch = payload_copy['persona']
            if 'style' in p_patch and isinstance(p_patch['style'], str):
                s_val = p_patch['style'].strip().lower()
                p_patch['style'] = s_val if s_val in ('jarvis', 'friendly', 'concise', 'bilingual_buddy') else 'jarvis'
            if 'languageMode' in p_patch and isinstance(p_patch['languageMode'], str):
                l_val = p_patch['languageMode'].strip().lower()
                p_patch['languageMode'] = l_val if l_val in ('auto', 'hinglish', 'hindi', 'english') else 'auto'
            if 'assistantName' in p_patch and isinstance(p_patch['assistantName'], str):
                cleaned = p_patch['assistantName'].strip()[:40]
                if cleaned:
                    p_patch['assistantName'] = cleaned
                else:
                    p_patch.pop('assistantName', None)
            if 'userTitle' in p_patch and isinstance(p_patch['userTitle'], str):
                cleaned_title = p_patch['userTitle'].strip()[:40]
                if cleaned_title:
                    p_patch['userTitle'] = cleaned_title
                else:
                    p_patch.pop('userTitle', None)
            if 'recentMemorySize' in p_patch:
                try:
                    p_patch['recentMemorySize'] = max(5, min(50, int(p_patch['recentMemorySize'])))
                except (TypeError, ValueError):
                    p_patch.pop('recentMemorySize', None)

        existing_cat = all_settings.get(category)
        if isinstance(existing_cat, dict) and isinstance(payload_copy, dict):
            deep_merge_settings(existing_cat, payload_copy)
            all_settings[category] = existing_cat
        else:
            all_settings[category] = payload_copy

        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(all_settings, f, indent=2)

    invalidate_cache()

    if category == 'general' and 'startOnBoot' in payload_copy:
        sync_windows_startup(bool(payload_copy['startOnBoot']))

    if category == 'ai':
        provider = payload_copy.get('defaultProvider') or get_provider()
        model = payload_copy.get('defaultModel') or get_model()
        logger.info(f"AI provider updated: {provider}, model: {model}")
        if provider == 'openai' and model:
            os.environ["OPENAI_MODEL"] = model

    if category in ('ai', 'security'):
        try:
            from ai_assistant.ai.network_aware_llm import reload_global_config
            reload_global_config()
            logger.info("Global LLM config hot-reloaded due to settings change")
        except Exception as e:
            logger.warning(f"Could not hot-reload global LLM config: {e}")
        reset_all_llm_sessions()

    if category == 'voice':
        for tts_mod_path in ("ai_assistant.voice.tts_output_service", "core_ai.src.ai_assistant.voice.tts_output_service"):
            tts_mod = sys.modules.get(tts_mod_path)
            if tts_mod is not None and hasattr(tts_mod, "get_tts_service"):
                try:
                    tts_mod.get_tts_service().reset_edge_circuit_breaker()
                except Exception:
                    pass
                break

    merged_settings = build_merged_settings(all_settings)
    category_payload = merged_settings.get(category, payload_copy)

    if category == 'system' and 'desktopOverlay' in category_payload:
        for mod_path in ("voice_service", "backend.voice_service"):
            try:
                mod = __import__(mod_path, fromlist=["update_overlay_state"])
                if hasattr(mod, "update_overlay_state"):
                    mod.update_overlay_state(source='settings_update')
                break
            except Exception:
                pass

    ts = datetime.now().isoformat()
    settings_event = {
        'category': category,
        'settings': category_payload,
        'all_settings': merged_settings,
        'timestamp': ts,
    }
    overlay_event = None
    if category == 'system' and 'desktopOverlay' in category_payload:
        overlay_event = {
            'enabled': bool(category_payload.get('desktopOverlay', True)),
            'timestamp': ts,
        }

    if broadcast_fn:
        try:
            broadcast_fn('settings_updated', settings_event)
            if overlay_event is not None:
                broadcast_fn('overlay_config_updated', overlay_event)
        except Exception as e:
            logger.warning(f"Custom broadcast failed for settings_updated: {e}")
    else:
        try:
            sio = _get_active_socketio()
            if sio:
                sio.emit('settings_updated', settings_event)
                if overlay_event is not None:
                    sio.emit('overlay_config_updated', overlay_event)
        except Exception as e:
            logger.warning(f"Could not broadcast settings_updated: {e}")

    return {
        "success": True,
        "message": f"{category.capitalize()} settings updated",
        "settings": merged_settings,
        "category_settings": category_payload,
    }


def complete_onboarding_settings(payload: Optional[dict] = None, broadcast_fn=None) -> dict:
    """
    Complete first-run onboarding: mark onboarded=True and apply any optional
    theme, AI provider, API key, or voice/mic preferences atomically.
    """
    from datetime import datetime
    data = payload if isinstance(payload, dict) else {}

    # Apply optional sub-category updates via standard pipeline first
    general_patch = {}
    if isinstance(data.get("theme"), str) and data["theme"].strip():
        general_patch["theme"] = data["theme"].strip().lower()
    if isinstance(data.get("enableHinglish"), bool):
        general_patch["enableHinglish"] = data["enableHinglish"]
    if isinstance(data.get("startOnBoot"), bool):
        general_patch["startOnBoot"] = data["startOnBoot"]
    if general_patch:
        update_settings_and_sync("general", general_patch, broadcast_fn=broadcast_fn)

    api_keys = data.get("apiKeys")
    if isinstance(api_keys, dict) and any(str(v).strip() for v in api_keys.values()):
        non_empty_keys = {k: str(v).strip() for k, v in api_keys.items() if str(v).strip()}
        update_settings_and_sync("security", {"apiKeys": non_empty_keys}, broadcast_fn=broadcast_fn)

    ai_patch = {}
    if isinstance(data.get("defaultProvider"), str) and data["defaultProvider"].strip():
        ai_patch["defaultProvider"] = data["defaultProvider"].strip().lower()
    if isinstance(data.get("defaultModel"), str) and data["defaultModel"].strip():
        ai_patch["defaultModel"] = data["defaultModel"].strip()
    if ai_patch:
        update_settings_and_sync("ai", ai_patch, broadcast_fn=broadcast_fn)

    if isinstance(data.get("micGranted"), bool):
        update_settings_and_sync(
            "voice",
            {"stt": {"enabled": bool(data["micGranted"])}},
            broadcast_fn=broadcast_fn,
        )

    settings_file = get_settings_file()
    with _settings_write_lock:
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                all_settings = json.load(f)
        else:
            all_settings = {}
        all_settings["onboarded"] = True
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(all_settings, f, indent=2)

    invalidate_cache()
    merged_settings = build_merged_settings(all_settings)
    event = {
        "category": "onboarded",
        "settings": True,
        "all_settings": merged_settings,
        "timestamp": datetime.now().isoformat(),
    }
    if broadcast_fn:
        try:
            broadcast_fn("settings_updated", event)
        except Exception:
            pass
    else:
        try:
            sio = _get_active_socketio()
            if sio:
                sio.emit("settings_updated", event)
        except Exception:
            pass

    return {
        "success": True,
        "onboarded": True,
        "message": "Onboarding completed successfully",
        "settings": merged_settings,
    }
