"""
Core AI Configuration Package
"""

from .paths import (
    PROJECT_ROOT,
    CORE_AI_DIR,
    CONFIG_DIR,
    DATA_DIR,
    MODELS_DIR,
    LOGS_DIR,
    BIN_DIR,
    ASSETS_DIR,
    DOCS_DIR,
    FRONTEND_DIR,
    BACKEND_DIR,
)
from .settings import CoreAISettings, get_settings

__all__ = [
    "PROJECT_ROOT",
    "CORE_AI_DIR",
    "CONFIG_DIR",
    "DATA_DIR",
    "MODELS_DIR",
    "LOGS_DIR",
    "BIN_DIR",
    "ASSETS_DIR",
    "DOCS_DIR",
    "FRONTEND_DIR",
    "BACKEND_DIR",
    "CoreAISettings",
    "get_settings",
]

