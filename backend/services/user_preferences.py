"""
User Preferences Management for Pulsar AI Assistant
Handles saving and loading user customization settings
"""

import json
import os
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Default user preferences
DEFAULT_PREFERENCES = {
    "startup": {
        "enabled": False,  # Don't show on every login by default
        "speed": 1.0,
        "showOnEveryLogin": False,
        "voiceEnabled": True,
        "fastMode": False
    },
    "voice": {
        "enabled": True,
        "rate": 1.0,
        "pitch": 1.0,
        "volume": 0.8
    },
    "dashboard": {
        "showProactiveInsights": True,
        "refreshInterval": 300000  # 5 minutes in ms
    },
    "theme": "dark",
    "language": "hinglish"
}

class UserPreferencesManager:
    """Manages user preferences with file-based storage"""
    
    def __init__(self, storage_dir="user_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
    def _get_user_file(self, user_id):
        """Get the preferences file path for a user"""
        return self.storage_dir / f"preferences_{user_id}.json"
    
    def get_preferences(self, user_id="default"):
        """
        Get user preferences, returns defaults if not found
        """
        try:
            user_file = self._get_user_file(user_id)
            
            if user_file.exists():
                with open(user_file, 'r') as f:
                    preferences = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return self._merge_with_defaults(preferences)
            else:
                logger.info(f"No preferences found for user {user_id}, using defaults")
                return DEFAULT_PREFERENCES.copy()
                
        except Exception as e:
            logger.error(f"Error loading preferences for user {user_id}: {e}")
            return DEFAULT_PREFERENCES.copy()
    
    def save_preferences(self, user_id, preferences):
        """
        Save user preferences to file
        """
        try:
            user_file = self._get_user_file(user_id)
            
            # Merge with existing to preserve any fields not included
            existing = self.get_preferences(user_id)
            merged = self._deep_merge(existing, preferences)
            
            # Add metadata
            merged['_metadata'] = {
                'last_updated': datetime.now().isoformat(),
                'user_id': user_id
            }
            
            with open(user_file, 'w') as f:
                json.dump(merged, f, indent=2)
            
            logger.info(f"Saved preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving preferences for user {user_id}: {e}")
            return False
    
    def _merge_with_defaults(self, preferences):
        """Merge user preferences with defaults to ensure all keys exist"""
        merged = DEFAULT_PREFERENCES.copy()
        return self._deep_merge(merged, preferences)
    
    def _deep_merge(self, base, updates):
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def reset_preferences(self, user_id):
        """Reset user preferences to defaults"""
        return self.save_preferences(user_id, DEFAULT_PREFERENCES)


# Singleton instance
_preferences_manager = None

def get_preferences_manager():
    """Get or create preferences manager instance"""
    global _preferences_manager
    if _preferences_manager is None:
        _preferences_manager = UserPreferencesManager()
    return _preferences_manager
