"""
Secure Secrets Manager for YourDaddy AI Assistant

Centralized management for all sensitive credentials and secrets.
Features:
- Environment variable validation
- Secure secret generation
- Runtime secret access with caching
- Secret rotation support
"""

import os
import secrets
import hashlib
import warnings
from typing import Optional, Dict, Any
from pathlib import Path
from functools import lru_cache

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class SecretsValidationError(Exception):
    """Raised when required secrets are missing or invalid."""
    pass


class SecretsManager:
    """
    Centralized secrets management with validation and secure defaults.
    
    Usage:
        secrets_mgr = SecretsManager()
        admin_password = secrets_mgr.get_required('ADMIN_PASSWORD')
        api_key = secrets_mgr.get_optional('OPENAI_API_KEY')
    """
    
    # Secrets that MUST be set (no defaults allowed)
    REQUIRED_SECRETS = {
        'ADMIN_PASSWORD': 'Admin password for app management',
        'APP_SECRET_KEY': 'Secret key for session signing',
    }
    
    # Secrets with secure auto-generation if missing
    AUTO_GENERATE_SECRETS = {
        'JWT_SECRET_KEY': 64,  # bytes
        'ENCRYPTION_MASTER_KEY': 32,
    }
    
    # Patterns that indicate insecure default values
    INSECURE_PATTERNS = [
        'password', 'secret', 'admin', 'test', 'demo', 'example',
        '123456', 'qwerty', 'changeme', 'default'
    ]
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize secrets manager.
        
        Args:
            env_file: Path to .env file. If None, searches standard locations.
        """
        self._cache: Dict[str, str] = {}
        self._generated: Dict[str, str] = {}
        self._load_environment(env_file)
    
    def _load_environment(self, env_file: Optional[str] = None):
        """Load environment variables from .env file."""
        if not DOTENV_AVAILABLE:
            logger.warning("python-dotenv not installed. Using system environment only.")
            return
        
        # Search for env files in priority order
        search_paths = [
            env_file,
            'config/app_integration.env',
            'config/backend.env',
            '.env',
        ]
        
        for path in search_paths:
            if path and Path(path).exists():
                load_dotenv(path, override=False)
                logger.debug(f"Loaded environment from: {path}")
    
    def get_required(self, key: str) -> str:
        """
        Get a required secret. Raises error if not set or insecure.
        
        Args:
            key: Environment variable name
            
        Returns:
            Secret value
            
        Raises:
            SecretsValidationError: If secret is missing or insecure
        """
        value = os.getenv(key)
        
        if not value:
            raise SecretsValidationError(
                f"Required secret '{key}' is not set. "
                f"Description: {self.REQUIRED_SECRETS.get(key, 'No description')}"
            )
        
        if self._is_insecure_value(value):
            raise SecretsValidationError(
                f"Secret '{key}' appears to be an insecure default value. "
                f"Please generate a secure random value."
            )
        
        return value
    
    def get_optional(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get an optional secret with fallback to default.
        
        Args:
            key: Environment variable name
            default: Default value if not set
            
        Returns:
            Secret value or default
        """
        return os.getenv(key, default)
    
    def get_or_generate(self, key: str, length: int = 32) -> str:
        """
        Get a secret or generate a secure one if not set.
        
        Args:
            key: Environment variable name
            length: Length of generated secret in bytes
            
        Returns:
            Secret value (existing or generated)
        """
        value = os.getenv(key)
        
        if value:
            return value
        
        # Check if already generated this session
        if key in self._generated:
            return self._generated[key]
        
        # Generate new secure value
        generated = secrets.token_urlsafe(length)
        self._generated[key] = generated
        
        logger.warning(
            f"Secret '{key}' not set. Generated temporary value. "
            f"Set this in your environment for persistence."
        )
        
        return generated
    
    def _is_insecure_value(self, value: str) -> bool:
        """Check if a value appears to be an insecure default."""
        value_lower = value.lower()
        
        # Check for common insecure patterns
        for pattern in self.INSECURE_PATTERNS:
            if pattern in value_lower:
                return True
        
        # Check minimum length
        if len(value) < 16:
            return True
        
        return False
    
    def validate_all_required(self) -> Dict[str, bool]:
        """
        Validate all required secrets are properly set.
        
        Returns:
            Dict mapping secret names to validation status
        """
        results = {}
        
        for key in self.REQUIRED_SECRETS:
            try:
                self.get_required(key)
                results[key] = True
            except SecretsValidationError:
                results[key] = False
        
        return results
    
    def generate_secure_value(self, length: int = 32) -> str:
        """Generate a cryptographically secure random value."""
        return secrets.token_urlsafe(length)
    
    def hash_value(self, value: str, salt: Optional[str] = None) -> tuple:
        """
        Hash a value securely using PBKDF2.
        
        Args:
            value: Value to hash
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (hash, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)
        
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            value.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        
        return hash_obj.hex(), salt
    
    @staticmethod
    def print_setup_instructions():
        """Print instructions for setting up secrets."""
        print("""
╔══════════════════════════════════════════════════════════════════════╗
║                    SECRETS SETUP INSTRUCTIONS                        ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  1. Copy the example config file:                                    ║
║     cp config/app_integration.env.example config/app_integration.env ║
║                                                                      ║
║  2. Generate secure values for required secrets:                     ║
║     python -c "import secrets; print(secrets.token_urlsafe(32))"     ║
║                                                                      ║
║  3. Edit config/app_integration.env and set:                         ║
║     - ADMIN_PASSWORD=<your_generated_value>                          ║
║     - APP_SECRET_KEY=<your_generated_value>                          ║
║                                                                      ║
║  4. Never commit app_integration.env to version control!             ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
        """)


# Global instance for convenience
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def get_secret(key: str, required: bool = False, default: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to get a secret.
    
    Args:
        key: Secret name
        required: If True, raises error when missing
        default: Default value for optional secrets
        
    Returns:
        Secret value
    """
    mgr = get_secrets_manager()
    
    if required:
        return mgr.get_required(key)
    return mgr.get_optional(key, default)


def generate_secret(length: int = 32) -> str:
    """Generate a secure random secret."""
    return secrets.token_urlsafe(length)


# CLI for generating secrets
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'generate':
        length = int(sys.argv[2]) if len(sys.argv) > 2 else 32
        print(f"Generated secret: {generate_secret(length)}")
    elif len(sys.argv) > 1 and sys.argv[1] == 'validate':
        mgr = SecretsManager()
        results = mgr.validate_all_required()
        for key, valid in results.items():
            status = "✅" if valid else "❌"
            print(f"{status} {key}")
    else:
        SecretsManager.print_setup_instructions()
