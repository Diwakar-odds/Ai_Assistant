"""
Pulsar AI Assistant - Production-Grade Filesystem & Storage Architecture.
========================================================================
Zero-Hardcoding, Cross-Platform System Path & Storage Manager.

Supports:
  1. Development Mode (runs from git repo, stores data/logs/config in project root)
  2. Production / Standalone Mode (packaged installer/binary or PULSAR_ENV=production):
       - Windows: %LOCALAPPDATA%\\Pulsar\\data, %APPDATA%\\Pulsar\\config, %LOCALAPPDATA%\\Pulsar\\logs
       - macOS:   ~/Library/Application Support/Pulsar
       - Linux:   ~/.local/share/pulsar, ~/.config/pulsar
  3. Explicit Environment Variable Overrides:
       - PULSAR_DATA_DIR, PULSAR_CONFIG_DIR, PULSAR_LOGS_DIR, PULSAR_MODELS_DIR, PULSAR_ENV
"""

import os
import sys
import shutil
import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

APP_NAME = "Pulsar"
APP_DIR_NAME = "PulsarAI"

# 1. Execution Mode Detection
IS_FROZEN = bool(getattr(sys, "frozen", False))
PULSAR_ENV = os.environ.get("PULSAR_ENV", "").strip().lower()
IS_PRODUCTION = IS_FROZEN or (PULSAR_ENV in ("production", "prod", "release"))

# 2. Application Code / Bundle Root (Read-Only in Production)
CORE_AI_DIR = Path(__file__).resolve().parent.parent  # .../core_ai
if IS_FROZEN:
    PROJECT_ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)).resolve()
else:
    PROJECT_ROOT = CORE_AI_DIR.parent.resolve()

CORE_AI_CONFIG_DIR = CORE_AI_DIR / "config"
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BIN_DIR = PROJECT_ROOT / "bin"
ASSETS_DIR = PROJECT_ROOT / "frontend" / "public"
DOCS_DIR = PROJECT_ROOT / "docs"

# 3. OS-Standard System Directories
def _get_os_system_data_dir() -> Path:
    """Resolve OS-standard user data directory."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / APP_DIR_NAME
        app_data = os.environ.get("APPDATA")
        if app_data:
            return Path(app_data) / APP_DIR_NAME
        return Path.home() / f".{APP_NAME.lower()}"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        # Linux / XDG
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            return Path(xdg_data) / APP_NAME.lower()
        return Path.home() / ".local" / "share" / APP_NAME.lower()


def _get_os_system_config_dir() -> Path:
    """Resolve OS-standard user config directory."""
    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if app_data:
            return Path(app_data) / APP_DIR_NAME / "config"
        return Path.home() / f".{APP_NAME.lower()}" / "config"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME / "config"
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / APP_NAME.lower()
        return Path.home() / ".config" / APP_NAME.lower()


def _get_os_system_logs_dir() -> Path:
    """Resolve OS-standard logs directory."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / APP_DIR_NAME / "logs"
        return Path.home() / f".{APP_NAME.lower()}" / "logs"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / APP_NAME
    else:
        xdg_state = os.environ.get("XDG_STATE_HOME")
        if xdg_state:
            return Path(xdg_state) / APP_NAME.lower() / "logs"
        return Path.home() / ".local" / "state" / APP_NAME.lower() / "logs"


# 4. Canonical Runtime Paths with Environment Overrides
_env_data_dir = os.environ.get("PULSAR_DATA_DIR")
if _env_data_dir and _env_data_dir.strip():
    DATA_DIR = Path(_env_data_dir.strip()).expanduser().resolve()
elif IS_PRODUCTION:
    DATA_DIR = _get_os_system_data_dir() / "data"
else:
    DATA_DIR = (PROJECT_ROOT / "data").resolve()

_env_config_dir = os.environ.get("PULSAR_CONFIG_DIR")
if _env_config_dir and _env_config_dir.strip():
    CONFIG_DIR = Path(_env_config_dir.strip()).expanduser().resolve()
elif IS_PRODUCTION:
    CONFIG_DIR = _get_os_system_config_dir()
else:
    CONFIG_DIR = (PROJECT_ROOT / "config").resolve()

_env_logs_dir = os.environ.get("PULSAR_LOGS_DIR")
if _env_logs_dir and _env_logs_dir.strip():
    LOGS_DIR = Path(_env_logs_dir.strip()).expanduser().resolve()
elif IS_PRODUCTION:
    LOGS_DIR = _get_os_system_logs_dir()
else:
    LOGS_DIR = (PROJECT_ROOT / "logs").resolve()

_env_models_dir = os.environ.get("PULSAR_MODELS_DIR")
if _env_models_dir and _env_models_dir.strip():
    MODELS_DIR = Path(_env_models_dir.strip()).expanduser().resolve()
elif IS_FROZEN and (Path(sys.executable).resolve().parent / "models").exists():
    MODELS_DIR = (Path(sys.executable).resolve().parent / "models").resolve()
else:
    MODELS_DIR = (PROJECT_ROOT / "models").resolve()


def get_candidate_model_dirs() -> List[Path]:
    """Return ordered list of directories to look for models (user overrides, exe dir, repo, bundle)."""
    candidates = []
    if _env_models_dir:
        candidates.append(Path(_env_models_dir).resolve())
    candidates.append(MODELS_DIR)
    if IS_FROZEN:
        candidates.append(Path(sys.executable).resolve().parent / "models")
    if IS_PRODUCTION:
        candidates.append(_get_os_system_data_dir() / "models")
    candidates.append(PROJECT_ROOT / "models")
    # De-duplicate while preserving order
    seen = set()
    unique = []
    for c in candidates:
        if c and str(c) not in seen:
            seen.add(str(c))
            unique.append(c)
    return unique


# 5. Initialization & Template Seeding for Fresh Installations
def ensure_directories():
    """
    Ensure all necessary runtime directories exist on the current system.
    If running in production mode and user config files do not exist yet,
    seed them safely from the bundled default configuration templates.
    """
    for d in (
        DATA_DIR,
        DATA_DIR / "core",
        DATA_DIR / "analytics",
        DATA_DIR / "automation",
        DATA_DIR / "caches",
        DATA_DIR / "user_preferences",
        LOGS_DIR,
        CONFIG_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)

    # In production, seed initial configs if not present in the user directory
    if IS_PRODUCTION and CONFIG_DIR != (PROJECT_ROOT / "config"):
        bundled_config_dir = PROJECT_ROOT / "config"
        if bundled_config_dir.exists():
            for src_file in bundled_config_dir.glob("*.json*"):
                dest_file = CONFIG_DIR / src_file.name
                if not dest_file.exists():
                    try:
                        shutil.copy2(str(src_file), str(dest_file))
                    except Exception as e:
                        logger.debug(f"Failed to seed config {src_file.name}: {e}")


# Initialize essential directories
ensure_directories()

__all__ = [
    "APP_NAME",
    "APP_DIR_NAME",
    "IS_FROZEN",
    "IS_PRODUCTION",
    "PULSAR_ENV",
    "PROJECT_ROOT",
    "CORE_AI_DIR",
    "CORE_AI_CONFIG_DIR",
    "BACKEND_DIR",
    "FRONTEND_DIR",
    "BIN_DIR",
    "ASSETS_DIR",
    "DOCS_DIR",
    "CONFIG_DIR",
    "DATA_DIR",
    "LOGS_DIR",
    "MODELS_DIR",
    "get_candidate_model_dirs",
    "ensure_directories",
]
