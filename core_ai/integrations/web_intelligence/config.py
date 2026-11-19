"""
Configuration loader for Web Intelligence Subsystem.
Reads settings from config/app_settings.json with fallback to environment variables.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict


def load_web_intelligence_config() -> Dict[str, Any]:
    """Load web intelligence settings."""
    default_config = {
        "enabled": True,
        "preferred_engine": "duckduckgo",
        "timeout_seconds": 3.5,
        "cache_enabled": True,
        "max_results_chat": 4,
        "max_results_research": 6,
        "api_keys": {
            "tavily": os.getenv("TAVILY_API_KEY", ""),
            "serpapi": os.getenv("SERPAPI_API_KEY", ""),
            "google_cse": os.getenv("GOOGLE_CSE_KEY", ""),
            "google_cse_cx": os.getenv("GOOGLE_CSE_CX", ""),
        },
        "searxng_url": os.getenv("SEARXNG_URL", ""),
    }

    # Try to load from config/app_settings.json
    try:
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        settings_file = project_root / "config" / "app_settings.json"
        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "web_intelligence" in data:
                    wi = data["web_intelligence"]
                    default_config["enabled"] = wi.get("enabled", default_config["enabled"])
                    default_config["preferred_engine"] = wi.get("preferred_engine", default_config["preferred_engine"])
                    default_config["timeout_seconds"] = float(wi.get("timeout_seconds", default_config["timeout_seconds"]))
                    default_config["cache_enabled"] = wi.get("cache_enabled", default_config["cache_enabled"])
                    default_config["max_results_chat"] = int(wi.get("max_results_chat", default_config["max_results_chat"]))
                    default_config["max_results_research"] = int(wi.get("max_results_research", default_config["max_results_research"]))
                    
                    user_keys = wi.get("api_keys", {})
                    for k, v in user_keys.items():
                        if v:
                            default_config["api_keys"][k] = v
    except Exception:
        pass

    return default_config
