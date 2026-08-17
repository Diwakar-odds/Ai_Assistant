"""
Backend Utility Functions
=========================

Shared utility functions for the web backend.
Extracted to prevent circular imports between blueprints and main backend module.
"""

import re
from typing import Dict, Any, Optional, Tuple

# Input Validation Patterns
VALIDATION_PATTERNS = {
    'command': re.compile(r'^[\w\s\-.,!?@#$%()+=:;"\']+$'),
    'app_name': re.compile(r'^[\w\s\-.]+$'),
    'username': re.compile(r'^[a-zA-Z0-9_]{3,20}$'),
}

def validate_input(data: Dict[str, Any], field: str, pattern_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate input data against pattern
    
    Args:
        data: Dictionary containing the field to validate
        field: Field name to validate
        pattern_name: Name of the validation pattern to use
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not data or field not in data:
        return False, f"Missing required field: {field}"
    
    value = data[field]
    if not isinstance(value, str):
        return False, f"Field {field} must be a string"
    
    if len(value) > 1000:
        return False, f"Field {field} exceeds maximum length of 1000 characters"
    
    pattern = VALIDATION_PATTERNS.get(pattern_name)
    if pattern and not pattern.match(value):
        return False, f"Field {field} contains invalid characters"
    
    return True, None

def sanitize_command(command: str) -> str:
    """
    Sanitize command input to prevent injection
    
    Args:
        command: Command string to sanitize
        
    Returns:
        Sanitized command string
    """
    # Remove potentially dangerous characters
    dangerous_chars = ['|', '&', ';', '`', '$', '(', ')', '<', '>', '\n', '\r']
    for char in dangerous_chars:
        command = command.replace(char, '')
    return command.strip()[:500]  # Limit length
