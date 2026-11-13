"""
Standard project filesystem paths for core_ai and the overall application.
"""

from pathlib import Path
import os

CORE_AI_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = CORE_AI_DIR.parent

# Standard Directories
CONFIG_DIR = CORE_AI_DIR / "config"
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"
BIN_DIR = PROJECT_ROOT / "bin"
ASSETS_DIR = PROJECT_ROOT / "frontend" / "public"
DOCS_DIR = PROJECT_ROOT / "docs"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"

# Ensure runtime directories exist
for directory in (DATA_DIR, LOGS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

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
]

