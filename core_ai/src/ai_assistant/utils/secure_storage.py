import keyring
import logging

logger = logging.getLogger(__name__)

# The service name used in the OS credential manager
SERVICE_NAME = "Pulsar_Assistant"

def save_secure_key(key_name: str, key_value: str) -> bool:
    """Save a secure key (like an API key) to the OS keychain."""
    if not key_value or not key_name:
        return False
        
    try:
        # Ignore masking values
        if key_value == "********":
            return True
            
        keyring.set_password(SERVICE_NAME, key_name, key_value)
        return True
    except Exception as e:
        logger.error(f"Failed to save secure key '{key_name}': {e}")
        return False

def get_secure_key(key_name: str) -> str:
    """Retrieve a secure key from the OS keychain. Returns empty string if not found."""
    try:
        value = keyring.get_password(SERVICE_NAME, key_name)
        return value if value else ""
    except Exception as e:
        logger.error(f"Failed to retrieve secure key '{key_name}': {e}")
        return ""

def delete_secure_key(key_name: str) -> bool:
    """Delete a secure key from the OS keychain."""
    try:
        keyring.delete_password(SERVICE_NAME, key_name)
        return True
    except keyring.errors.PasswordDeleteError:
        # Password doesn't exist, which is fine
        return True
    except Exception as e:
        logger.error(f"Failed to delete secure key '{key_name}': {e}")
        return False
