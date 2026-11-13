"""
Core AI Settings and Configuration Management
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

from .paths import PROJECT_ROOT, DATA_DIR, LOGS_DIR

class CoreAISettings(BaseSettings):
    """Core AI runtime settings loaded from environment or defaults."""
    app_name: str = "AI Assistant"
    version: str = "4.0.0"
    app_env: str = Field(default="development", alias="ENV")
    
    # Storage and paths
    data_dir: str = str(DATA_DIR)
    logs_dir: str = str(LOGS_DIR)
    
    # Offline and inference settings
    offline_mode: bool = False
    default_llm_model: str = "pulsar-final-q4_k_m.gguf"
    embedding_model: str = "all-MiniLM-L6-v2"

    class Config:
        env_file = os.path.join(PROJECT_ROOT, ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

def get_settings() -> CoreAISettings:
    return CoreAISettings()

__all__ = ["CoreAISettings", "get_settings"]

