"""
Configuration Loader for YourDaddy AI Assistant

Centralized configuration management using environment variables.
Replaces api_keys.json with secure .env file.

Usage:
    from ai_assistant.core.config_loader import get_config
    
    config = get_config()
    gemini_key = config['GOOGLE_GEMINI_API_KEY']
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Configuration related errors"""
    pass


class Config:
    """
    Configuration manager for AI Assistant
    
    Loads configuration from .env file and provides validation.
    """
    
    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize configuration loader
        
        Args:
            env_file: Path to .env file (default: project root/.env)
        """
        # Determine .env file location
        if env_file is None:
            # Try to find .env in project root
            current_dir = Path(__file__).parent.parent.parent
            env_file = current_dir / '.env'
        
        self.env_file = Path(env_file)
        self._config = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from .env file"""
        # Load .env file if it exists
        if self.env_file.exists():
            load_dotenv(self.env_file)
            logger.info(f"✅ Loaded configuration from {self.env_file}")
        else:
            logger.warning(f"⚠️ .env file not found at {self.env_file}")
            logger.info("Using system environment variables only")
        
        # Load all configuration values
        self._config = {
            # AI API Keys
            'GOOGLE_GEMINI_API_KEY': os.getenv('GOOGLE_GEMINI_API_KEY', ''),
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', ''),
            'GOOGLE_CLOUD_PROJECT_ID': os.getenv('GOOGLE_CLOUD_PROJECT_ID', ''),
            
            # Database
            'DATABASE_ENCRYPTION_KEY': os.getenv('DATABASE_ENCRYPTION_KEY', ''),
            
            # Security
            'SECRET_KEY': os.getenv('SECRET_KEY', ''),
            'JWT_SECRET_KEY': os.getenv('JWT_SECRET_KEY', ''),
            'PIN_ENCRYPTION_KEY': os.getenv('PIN_ENCRYPTION_KEY', ''),
            'SESSION_SECRET_KEY': os.getenv('SESSION_SECRET_KEY', ''),
            'ADMIN_PASSWORD': os.getenv('ADMIN_PASSWORD', ''),
            
            # Feature Flags
            'ENABLE_VOICE_EXTERNAL_APIS': os.getenv('ENABLE_VOICE_EXTERNAL_APIS', 'true').lower() == 'true',
            'ENABLE_FILE_DELETION': os.getenv('ENABLE_FILE_DELETION', 'true').lower() == 'true',
            'ENABLE_APP_EXECUTION': os.getenv('ENABLE_APP_EXECUTION', 'true').lower() == 'true',
            'ENABLE_MULTIMODAL': os.getenv('ENABLE_MULTIMODAL', 'true').lower() == 'true',
            'ENABLE_VOICE': os.getenv('ENABLE_VOICE', 'true').lower() == 'true',
            
            # API Rate Limits
            'API_RATE_LIMIT_PER_MINUTE': int(os.getenv('API_RATE_LIMIT_PER_MINUTE', '60')),
            'VOICE_API_RATE_LIMIT_PER_MINUTE': int(os.getenv('VOICE_API_RATE_LIMIT_PER_MINUTE', '10')),
            
            # Backend Configuration
            'BACKEND_PORT': int(os.getenv('BACKEND_PORT', '5000')),
            'ALLOWED_ORIGINS': os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5173'),
            
            # Paths
            'DATA_DIR': os.getenv('DATA_DIR', 'data'),
            'LOGS_DIR': os.getenv('LOGS_DIR', 'logs'),
            'DATABASES_DIR': os.getenv('DATABASES_DIR', 'databases'),
        }
        
        # Validate required keys
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration has required values"""
        # Check for at least one AI API key
        has_gemini = bool(self._config.get('GOOGLE_GEMINI_API_KEY'))
        has_openai = bool(self._config.get('OPENAI_API_KEY'))
        
        if not has_gemini and not has_openai:
            logger.warning(
                "⚠️ No AI API keys configured! Please set GOOGLE_GEMINI_API_KEY "
                "or OPENAI_API_KEY in your .env file"
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Get configuration value using dict syntax"""
        if key not in self._config:
            raise ConfigurationError(f"Configuration key '{key}' not found")
        return self._config[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if configuration key exists"""
        return key in self._config
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get all configuration as dictionary
        
        Note: Sensitive values are masked
        
        Returns:
            Dictionary of configuration (sensitive values masked)
        """
        safe_config = self._config.copy()
        
        # Mask sensitive values
        sensitive_keys = [
            'GOOGLE_GEMINI_API_KEY', 'OPENAI_API_KEY',
            'SECRET_KEY', 'JWT_SECRET_KEY', 'PIN_ENCRYPTION_KEY',
            'SESSION_SECRET_KEY', 'ADMIN_PASSWORD', 'DATABASE_ENCRYPTION_KEY'
        ]
        
        for key in sensitive_keys:
            if key in safe_config and safe_config[key]:
                safe_config[key] = '*' * 8  # Mask with asterisks
        
        return safe_config
    
    def reload(self):
        """Reload configuration from .env file"""
        self._load_config()
        logger.info("Configuration reloaded")


# Global configuration instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Get global configuration instance (singleton)
    
    Returns:
        Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def load_config(env_file: Optional[Path] = None) -> Config:
    """
    Load configuration from .env file
    
    Args:
        env_file: Path to .env file (optional)
        
    Returns:
        Config instance
    """
    global _config_instance
    _config_instance = Config(env_file)
    return _config_instance


if __name__ == "__main__":
    # Test configuration loading
    print("Testing Configuration Loader")
    print("=" * 80)
    
    config = get_config()
    
    print("\nLoaded Configuration:")
    print(f"  .env file: {config.env_file}")
    print(f"  Exists: {config.env_file.exists()}")
    
    print("\nConfiguration Values (masked):")
    for key, value in config.to_dict().items():
        print(f"  {key}: {value}")
    
    print("\nValidation:")
    print(f"  Has Gemini API Key: {bool(config.get('GOOGLE_GEMINI_API_KEY'))}")
    print(f"  Has OpenAI API Key: {bool(config.get('OPENAI_API_KEY'))}")
    print(f"  Backend Port: {config.get('BACKEND_PORT')}")
    
    print("\n✅ Configuration loading test complete!")
