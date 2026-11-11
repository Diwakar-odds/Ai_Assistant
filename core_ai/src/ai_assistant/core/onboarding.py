import json
import logging
from pathlib import Path
import os
import sys
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


def _default_onboarding_settings_path() -> Path:
    try:
        from settings_manager import get_settings_file
        return get_settings_file()
    except Exception:
        pass
    override = os.environ.get('PULSAR_DATA_DIR')
    if override and override.strip():
        return Path(override.strip()).expanduser().resolve() / 'data' / 'user_preferences' / 'settings.json'
    if getattr(sys, 'frozen', False):
        appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~/.pulsar_ai'))
        return Path(appdata) / 'PulsarAI' / 'data' / 'user_preferences' / 'settings.json'
    return Path(__file__).resolve().parents[4] / 'data' / 'user_preferences' / 'settings.json'


class OnboardingManager:
    def __init__(self, settings_path: str = None):
        if settings_path is None:
            self.settings_path = _default_onboarding_settings_path()
        else:
            self.settings_path = Path(settings_path)

        self.settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        try:
            if self.settings_path.exists():
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading settings for onboarding: {e}")
        return {"onboarded": False, "settings": []}

    def _save_settings(self):
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving settings for onboarding: {e}")

    def is_onboarded(self) -> bool:
        return self.settings.get("onboarded", False)

    def set_onboarded(self, status: bool = True):
        self.settings["onboarded"] = status
        self._save_settings()

    def get_onboarding_system_prompt(self) -> str:
        return (
            "You are Pulsar, a highly intelligent and personalized AI assistant. "
            "You are currently in ONBOARDING MODE because this is your first interaction with the user. "
            "Your goal is to conduct a brief, friendly interactive interview to deeply learn about the user. "
            "Ask them these 4 quick questions one by one (do not ask them all at once): "
            "1. What is their primary profession and typical work schedule (e.g., 9-5, night owl)? "
            "2. Do they prefer short, concise answers or detailed, explanatory answers? "
            "3. What tone do they prefer (formal, casual, witty, JARVIS-like)? "
            "4. What are their core technical skills and main goals for using this assistant? "
            "Once you have gathered this information, output exactly the phrase '[ONBOARDING_COMPLETE]' "
            "at the end of your final response, summarizing their preferences."
        )

    def process_onboarding_response(self, response: str) -> Tuple[str, bool]:
        """
        Check if the onboarding is complete based on the LLM response.
        Returns (cleaned_response, is_complete)
        """
        if "[ONBOARDING_COMPLETE]" in response:
            cleaned = response.replace("[ONBOARDING_COMPLETE]", "").strip()
            self.set_onboarded(True)
            return cleaned, True
        return response, False