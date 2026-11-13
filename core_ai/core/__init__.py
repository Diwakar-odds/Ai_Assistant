"""
Core system modules for the AI Assistant.

This package contains the core functionality, system utilities,
tool execution, security, and performance optimization modules.
"""

__version__ = "1.0.0"

# from .core import *
# from .system import *

# Security modules
try:
    from .secrets_manager import (
        SecretsManager,
        get_secrets_manager,
        get_secret,
        generate_secret,
        SecretsValidationError,
    )
except ImportError:
    pass

try:
    from .encryption import SecureEncryption, EncryptionError
except ImportError:
    pass