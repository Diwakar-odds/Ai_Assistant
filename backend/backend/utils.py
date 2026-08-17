"""
YourDaddy AI Assistant - Utility Functions

Common utility functions for the backend.
"""

import logging
import hashlib
import secrets
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def generate_session_id() -> str:
    """Generate secure session ID"""
    return secrets.token_urlsafe(32)


def generate_api_token() -> str:
    """Generate API token"""
    return secrets.token_urlsafe(48)


def hash_string(value: str, salt: Optional[str] = None) -> tuple:
    """
    Hash a string with salt
    
    Returns:
        tuple: (hashed_value, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        value.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    
    return hashed.hex(), salt


def format_timestamp(timestamp: Optional[float] = None) -> str:
    """Format timestamp for API responses"""
    if timestamp is None:
        timestamp = datetime.now().timestamp()
    
    dt = datetime.fromtimestamp(timestamp)
    return dt.isoformat()


def safe_dict_get(data: Dict, key: str, default: Any = None) -> Any:
    """Safely get value from dict"""
    try:
        return data.get(key, default)
    except (AttributeError, TypeError):
        return default


def truncate_string(text: str, max_length: int = 100) -> str:
    """Truncate string to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def validate_required_fields(data: Dict, required_fields: list) -> tuple:
    """
    Validate that required fields are present
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Invalid data format"
    
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, None
