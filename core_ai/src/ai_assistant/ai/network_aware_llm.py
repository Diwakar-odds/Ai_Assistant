"""
Online LLM Configuration
Uses cloud-based LLM providers (OpenAI GPT and Google Gemini).
Optimized for always-online operation.
"""

import os
import json
import requests
import logging
from typing import Dict, Tuple, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class OnlineLLMConfig:
    """Configuration for online-only LLM providers."""
    
    def __init__(self):
        self.last_check = None
        self.network_status = True  # Assume online
        self.check_interval = timedelta(minutes=5)
        self.api_keys = self._load_api_keys()
        
        # Get keys from json or env (secure loading)
        openai_key = self.api_keys.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        gemini_key = self.api_keys.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        # Online providers only - ordered by preference
        # Using user's preferred OpenAI model first
        self.online_providers = [
            ("openai", openai_model, openai_key),
            ("openai", "gpt-4o", openai_key),
            ("openai", "gpt-4", openai_key),
            ("openai", "gpt-3.5-turbo", openai_key),
            ("gemini", "gemini-2.5-flash", gemini_key),
            ("gemini", "gemini-2.5-pro", gemini_key),
            ("gemini", "gemini-flash-latest", gemini_key),
            ("gemini", "gemini-pro-latest", gemini_key),
        ]

    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from secure locations."""
        keys = {}
        
        # Try loading from api_keys.json (should be gitignored)
        try:
            key_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "api_keys.json"
            )
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    keys = json.load(f)
                logger.debug("Loaded API keys from api_keys.json")
        except Exception as e:
            logger.debug(f"No api_keys.json found: {e}")
        
        return keys

    def reload_config(self):
        """Hot-reload API keys and provider list from environment and files."""
        self.api_keys = self._load_api_keys()
        
        # Get keys from json or env (secure loading)
        openai_key = self.api_keys.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        gemini_key = self.api_keys.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        # Rebuild providers list
        self.online_providers = [
            ("openai", openai_model, openai_key),
            ("openai", "gpt-4o", openai_key),
            ("openai", "gpt-4", openai_key),
            ("openai", "gpt-3.5-turbo", openai_key),
            ("gemini", "gemini-2.5-flash", gemini_key),
            ("gemini", "gemini-2.5-pro", gemini_key),
            ("gemini", "gemini-flash-latest", gemini_key),
            ("gemini", "gemini-pro-latest", gemini_key),
        ]
        logger.info("OnlineLLMConfig hot-reloaded successfully")

    def check_internet_connectivity(self) -> bool:
        """Check if internet connection is available."""
        # Cache the result to avoid excessive checks
        now = datetime.now()
        if (self.last_check and 
            self.network_status is not None and 
            now - self.last_check < self.check_interval):
            return self.network_status
        
        try:
            response = requests.get("https://google.com", timeout=3)
            self.network_status = response.status_code == 200
            self.last_check = now
            return self.network_status
        except Exception as e:
            logger.warning(f"Network check failed: {e}")
            self.network_status = False
            self.last_check = now
            return False
    
    def get_optimal_provider(self) -> Tuple[str, str]:
        """
        Get the optimal online provider based on availability.
        
        Returns:
            Tuple of (provider_name, model_name)
        """
        # Try online providers in order of preference
        for provider, model, api_key in self.online_providers:
            if api_key:
                try:
                    if self._test_provider(provider, api_key):
                        logger.info(f"Using online provider: {provider} ({model})")
                        return (provider, model)
                except Exception as e:
                    logger.warning(f"Provider {provider} test failed: {e}")
                    continue
        
        # No providers available
        logger.error("No online providers available - check API keys")
        return ("none", "none")
    
    def _test_provider(self, provider: str, api_key: str) -> bool:
        """Quick test of online provider availability."""
        try:
            if provider == "openai":
                base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
                # Remove trailing slash if present
                base_url = base_url.rstrip("/")
                response = requests.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=5
                )
                return response.status_code == 200
            
            elif provider == "gemini":
                response = requests.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
                    timeout=5
                )
                return response.status_code == 200
            
            return False
            
        except Exception:
            return False
    
    def get_provider_config(self) -> Dict:
        """Get complete provider configuration."""
        provider, model = self.get_optimal_provider()
        
        config = {
            "provider": provider,
            "model": model,
            "online_only": True,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "network_status": self.network_status
        }
        
        # Add provider-specific settings
        if provider == "openai":
            config.update({
                "temperature": 0.7,
                "max_tokens": 4000,
                "top_p": 0.95
            })
        elif provider == "gemini":
            config.update({
                "temperature": 0.7,
                "max_tokens": 4000,
                "safety_settings": "BLOCK_MEDIUM_AND_ABOVE"
            })
        
        return config


# Backward compatibility alias
NetworkAwareLLMConfig = OnlineLLMConfig

# Global instance
network_config = OnlineLLMConfig()

def get_optimal_llm_config():
    """Get the optimal LLM configuration."""
    return network_config.get_provider_config()

def force_online_mode():
    """Force refresh of online providers."""
    network_config.network_status = True
    return network_config.get_optimal_provider()

def reload_global_config():
    """Reload the global OnlineLLMConfig instance."""
    network_config.reload_config()