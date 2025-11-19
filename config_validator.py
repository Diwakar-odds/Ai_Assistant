"""Configuration Validator for YourDaddy AI Assistant."""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv

from utils.logging_config import get_logger

# Configure logging with UTF-8 encoding for Windows console
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

logger = get_logger(__name__)


class ConfigValidator:
    """Validates application configuration and API keys"""
    
    # Define required and optional configuration keys
    REQUIRED_KEYS = {
        'GEMINI_API_KEY': 'Google Gemini API (https://makersuite.google.com/app/apikey)',
        'JWT_SECRET_KEY': 'JWT Secret Key for authentication (generate with: python -c "import secrets; print(secrets.token_hex(32))")',
        'ADMIN_PASSWORD': 'Admin password for web interface',
    }
    
    OPTIONAL_KEYS = {
        'PICOVOICE_ACCESS_KEY': 'Picovoice for wake word detection (https://console.picovoice.ai/)',
        'SPOTIFY_CLIENT_ID': 'Spotify API (https://developer.spotify.com/dashboard)',
        'SPOTIFY_CLIENT_SECRET': 'Spotify API (https://developer.spotify.com/dashboard)',
        'OPENAI_API_KEY': 'OpenAI API (https://platform.openai.com/api-keys)',
        'AZURE_SPEECH_KEY': 'Azure Speech Services',
        'OPENWEATHER_API_KEY': 'OpenWeather API (https://openweathermap.org/api)',
        'NEWS_API_KEY': 'News API (https://newsapi.org/)'
    }
    
    FEATURE_DEPENDENCIES = {
        'ENABLE_WAKE_WORD': ['PICOVOICE_ACCESS_KEY'],
        'ENABLE_MUSIC_CONTROLS': ['SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET'],
    }
    
    def __init__(self, env_path: str = '.env'):
        """
        Initialize configuration validator
        
        Args:
            env_path: Path to .env file
        """
        self.env_path = Path(env_path)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.config: Dict[str, str] = {}
        
    def load_environment(self) -> bool:
        """
        Load environment variables from .env file
        
        Returns:
            True if .env file exists and was loaded
        """
        if not self.env_path.exists():
            logger.warning(f"❌ .env file not found at {self.env_path.absolute()}")
            logger.info("📄 Please copy .env.example to .env and configure your API keys")
            return False
        
        load_dotenv(self.env_path)
        logger.info(f"✅ Loaded environment from {self.env_path}")
        return True
    
    def validate_required_keys(self) -> Tuple[bool, List[str]]:
        """
        Validate all required configuration keys
        
        Returns:
            Tuple of (is_valid, missing_keys)
        """
        missing_keys = []
        
        for key, description in self.REQUIRED_KEYS.items():
            value = os.getenv(key, '').strip()
            
            if not value or value.startswith('your_') or value == 'change_this_to_a_strong_password':
                missing_keys.append(f"{key}: {description}")
                self.errors.append(f"❌ Missing or invalid: {key}")
            else:
                self.config[key] = value
                logger.info(f"✅ {key} is configured")
        
        return len(missing_keys) == 0, missing_keys
    
    def validate_optional_keys(self) -> Dict[str, bool]:
        """
        Check which optional features are configured
        
        Returns:
            Dictionary of feature_name: is_configured
        """
        configured = {}
        
        for key, description in self.OPTIONAL_KEYS.items():
            value = os.getenv(key, '').strip()
            is_configured = bool(value and not value.startswith('your_'))
            configured[key] = is_configured
            
            if is_configured:
                self.config[key] = value
                logger.info(f"✅ Optional: {key} is configured")
            else:
                self.warnings.append(f"⚠️ Optional: {key} not configured - {description}")
        
        return configured
    
    def validate_feature_dependencies(self) -> List[str]:
        """
        Validate that enabled features have required configuration
        
        Returns:
            List of warnings about features that can't be enabled
        """
        disabled_features = []
        
        for feature, dependencies in self.FEATURE_DEPENDENCIES.items():
            is_enabled = os.getenv(feature, 'True').lower() == 'true'
            
            if is_enabled:
                missing_deps = [dep for dep in dependencies if dep not in self.config]
                
                if missing_deps:
                    warning = f"⚠️ {feature} is enabled but missing: {', '.join(missing_deps)}"
                    self.warnings.append(warning)
                    disabled_features.append(feature)
        
        return disabled_features
    
    def validate_file_paths(self) -> bool:
        """
        Validate required directories exist and create them if needed
        
        Returns:
            True if all paths are valid
        """
        required_dirs = ['data', 'logs', 'model']
        
        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"✅ Created directory: {dir_path}")
                except Exception as e:
                    self.errors.append(f"❌ Failed to create directory {dir_path}: {e}")
                    return False
        
        return True
    
    def validate_google_credentials(self) -> bool:
        """
        Check if Google credentials.json exists for Calendar/Gmail
        
        Returns:
            True if credentials file exists
        """
        credentials_path = Path('credentials.json')
        
        if not credentials_path.exists():
            self.warnings.append(
                "⚠️ credentials.json not found - Google Calendar and Gmail features will not work\n"
                "   Download from: https://console.cloud.google.com/"
            )
            return False
        
        logger.info("✅ Google credentials.json found")
        return True
    
    def validate(self) -> bool:
        """
        Run complete validation
        
        Returns:
            True if all required configuration is valid
        """
        logger.info("=" * 70)
        logger.info("🔍 YourDaddy AI Assistant - Configuration Validation")
        logger.info("=" * 70)
        
        # Load environment file
        if not self.load_environment():
            self.errors.append("❌ .env file not found. Please copy .env.example to .env")
            self._print_results()
            return False
        
        # Validate required keys
        is_valid, missing_keys = self.validate_required_keys()
        
        # Validate optional keys
        self.validate_optional_keys()
        
        # Validate feature dependencies
        self.validate_feature_dependencies()
        
        # Validate file paths
        self.validate_file_paths()
        
        # Validate Google credentials
        self.validate_google_credentials()
        
        # Print results
        self._print_results()
        
        if not is_valid:
            logger.error("\n" + "=" * 70)
            logger.error("❌ CONFIGURATION VALIDATION FAILED")
            logger.error("=" * 70)
            logger.error("\nMissing required configuration:")
            for key in missing_keys:
                logger.error(f"  • {key}")
            logger.error("\n📝 Steps to fix:")
            logger.error("  1. Copy .env.example to .env")
            logger.error("  2. Edit .env and add your API keys")
            logger.error("  3. Run the application again")
            logger.error("=" * 70)
            return False
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ CONFIGURATION VALIDATION PASSED")
        logger.info("=" * 70)
        return True
    
    def _print_results(self):
        """Print validation results"""
        if self.warnings:
            logger.warning("\n⚠️ Warnings:")
            for warning in self.warnings:
                logger.warning(f"  {warning}")
    
    def get_config(self, key: str, default: str = None) -> str:
        """
        Get configuration value
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, os.getenv(key, default))


def validate_config(env_path: str = '.env', exit_on_failure: bool = True) -> ConfigValidator:
    """
    Validate configuration and optionally exit on failure
    
    Args:
        env_path: Path to .env file
        exit_on_failure: If True, exit program on validation failure
        
    Returns:
        ConfigValidator instance
    """
    validator = ConfigValidator(env_path)
    is_valid = validator.validate()
    
    if not is_valid and exit_on_failure:
        sys.exit(1)
    
    return validator


# Quick validation function for imports
def quick_check() -> bool:
    """
    Quick validation check without detailed output
    
    Returns:
        True if configuration is valid
    """
    validator = ConfigValidator()
    if not validator.load_environment():
        return False
    is_valid, _ = validator.validate_required_keys()
    return is_valid


if __name__ == "__main__":
    # Run validation when script is executed directly
    validate_config()
