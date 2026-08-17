"""
Encryption Utilities for YourDaddy AI Assistant

Provides comprehensive encryption/decryption for sensitive data including:
- API credentials and tokens
- Conversation history 
- User data and preferences
- Database content encryption

Uses AES-256-GCM for symmetric encryption with secure key derivation.
"""

import os
import base64
import secrets
import hashlib
import json
from pathlib import Path
from typing import Union, Dict, Any, Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Custom exception for encryption-related errors"""
    pass


class SecureEncryption:
    """
    Secure encryption/decryption utility for AI Assistant data.
    
    Features:
    - AES-256-GCM encryption with authenticated encryption
    - PBKDF2 key derivation from master password
    - Secure random salt and nonce generation
    - JSON serialization support
    - Database field encryption support
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption with master key.
        
        Args:
            master_key: Master password/key. If None, will use environment variable
        """
        self.master_key = master_key or self._get_master_key()
        self._key_cache = {}  # Cache derived keys for performance
        
    def _get_master_key(self) -> str:
        """Get master key from environment or generate new one"""
        # Check environment variable first
        master_key = os.getenv('ENCRYPTION_MASTER_KEY')
        if master_key:
            return master_key
        
        # Check config file
        config_path = Path("config/encryption.key")
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return f.read().strip()
            except Exception as e:
                logger.warning(f"Failed to read encryption key from file: {e}")
        
        # Generate new key if none exists
        logger.warning("No encryption master key found. Generating new key...")
        master_key = self._generate_master_key()
        self._save_master_key(master_key)
        return master_key
    
    def _generate_master_key(self) -> str:
        """Generate a new cryptographically secure master key"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
    
    def _save_master_key(self, key: str) -> None:
        """Save master key to secure location"""
        try:
            config_path = Path("config/encryption.key")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                f.write(key)
            
            # Set restrictive permissions on Unix systems
            if hasattr(os, 'chmod'):
                os.chmod(config_path, 0o600)
            
            logger.info("Master encryption key saved securely")
            
            # Also set as environment variable for current session
            os.environ['ENCRYPTION_MASTER_KEY'] = key
            
        except Exception as e:
            logger.error(f"Failed to save master key: {e}")
            raise EncryptionError(f"Could not save encryption key: {e}")
    
    def _derive_key(self, salt: bytes, context: str = "default") -> bytes:
        """
        Derive encryption key from master key using PBKDF2
        
        Args:
            salt: Cryptographic salt
            context: Context for key derivation (different contexts get different keys)
            
        Returns:
            32-byte derived key
        """
        # Create cache key
        cache_key = (salt, context)
        if cache_key in self._key_cache:
            return self._key_cache[cache_key]
        
        # Derive key using PBKDF2
        master_bytes = (self.master_key + context).encode('utf-8')
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # Same as PIN hashing for consistency
            backend=default_backend()
        )
        
        derived_key = kdf.derive(master_bytes)
        self._key_cache[cache_key] = derived_key
        return derived_key
    
    def encrypt(self, plaintext: Union[str, bytes, Dict[str, Any]], context: str = "default") -> str:
        """
        Encrypt data with AES-256-GCM
        
        Args:
            plaintext: Data to encrypt (string, bytes, or JSON-serializable object)
            context: Encryption context for key derivation
            
        Returns:
            Base64-encoded encrypted data with salt and nonce
        """
        try:
            # Convert to bytes if needed
            if isinstance(plaintext, dict) or isinstance(plaintext, list):
                data_bytes = json.dumps(plaintext).encode('utf-8')
            elif isinstance(plaintext, str):
                data_bytes = plaintext.encode('utf-8')
            else:
                data_bytes = plaintext
            
            # Generate random salt and nonce
            salt = secrets.token_bytes(16)
            nonce = secrets.token_bytes(12)  # GCM standard nonce size
            
            # Derive encryption key
            key = self._derive_key(salt, context)
            
            # Encrypt with AES-GCM
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, data_bytes, None)
            
            # Combine salt + nonce + ciphertext
            encrypted_data = salt + nonce + ciphertext
            
            # Return base64 encoded
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt data: {e}")
    
    def decrypt(self, encrypted_data: str, context: str = "default") -> Union[str, Dict[str, Any]]:
        """
        Decrypt AES-256-GCM encrypted data
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            context: Decryption context (must match encryption context)
            
        Returns:
            Decrypted data (string or JSON object)
        """
        try:
            # Decode from base64
            data = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Extract salt, nonce, and ciphertext
            salt = data[:16]
            nonce = data[16:28]
            ciphertext = data[28:]
            
            # Derive decryption key
            key = self._derive_key(salt, context)
            
            # Decrypt with AES-GCM
            aesgcm = AESGCM(key)
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            
            # Convert back to string
            plaintext = plaintext_bytes.decode('utf-8')
            
            # Try to parse as JSON
            try:
                return json.loads(plaintext)
            except json.JSONDecodeError:
                return plaintext
                
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt data: {e}")
    
    def encrypt_file(self, file_path: Union[str, Path], context: str = "files") -> str:
        """
        Encrypt entire file contents
        
        Args:
            file_path: Path to file to encrypt
            context: Encryption context
            
        Returns:
            Base64-encoded encrypted file contents
        """
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            return self.encrypt(file_data, context)
            
        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt file {file_path}: {e}")
    
    def decrypt_file(self, encrypted_data: str, output_path: Union[str, Path], context: str = "files") -> bool:
        """
        Decrypt and save file contents
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            output_path: Path to save decrypted file
            context: Decryption context
            
        Returns:
            True if successful
        """
        try:
            # Decrypt data
            data = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Extract components
            salt = data[:16]
            nonce = data[16:28]
            ciphertext = data[28:]
            
            # Derive key and decrypt
            key = self._derive_key(salt, context)
            aesgcm = AESGCM(key)
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            
            # Save to file
            with open(output_path, 'wb') as f:
                f.write(plaintext_bytes)
            
            return True
            
        except Exception as e:
            logger.error(f"File decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt file to {output_path}: {e}")


class DatabaseEncryption:
    """Encryption helper for database fields"""
    
    def __init__(self, encryption: SecureEncryption):
        self.encryption = encryption
    
    def encrypt_field(self, value: Any, table_name: str, field_name: str) -> str:
        """Encrypt a database field value"""
        context = f"db_{table_name}_{field_name}"
        return self.encryption.encrypt(value, context)
    
    def decrypt_field(self, encrypted_value: str, table_name: str, field_name: str) -> Any:
        """Decrypt a database field value"""
        context = f"db_{table_name}_{field_name}"
        return self.encryption.decrypt(encrypted_value, context)


class ConfigEncryption:
    """Encryption helper for configuration files"""
    
    def __init__(self, encryption: SecureEncryption):
        self.encryption = encryption
    
    def encrypt_config(self, config_dict: Dict[str, Any], config_name: str) -> str:
        """Encrypt entire configuration dictionary"""
        context = f"config_{config_name}"
        return self.encryption.encrypt(config_dict, context)
    
    def decrypt_config(self, encrypted_config: str, config_name: str) -> Dict[str, Any]:
        """Decrypt configuration dictionary"""
        context = f"config_{config_name}"
        result = self.encryption.decrypt(encrypted_config, context)
        return result if isinstance(result, dict) else {}
    
    def encrypt_api_keys(self, api_keys: Dict[str, str]) -> Dict[str, str]:
        """Encrypt API keys while preserving structure"""
        encrypted_keys = {}
        for key, value in api_keys.items():
            if value and not value.startswith('encrypted:'):
                encrypted_keys[key] = 'encrypted:' + self.encryption.encrypt(value, f"api_key_{key}")
            else:
                encrypted_keys[key] = value
        return encrypted_keys
    
    def decrypt_api_keys(self, encrypted_keys: Dict[str, str]) -> Dict[str, str]:
        """Decrypt API keys"""
        decrypted_keys = {}
        for key, value in encrypted_keys.items():
            if value and value.startswith('encrypted:'):
                try:
                    encrypted_value = value[10:]  # Remove 'encrypted:' prefix
                    decrypted_keys[key] = self.encryption.decrypt(encrypted_value, f"api_key_{key}")
                except Exception as e:
                    logger.warning(f"Failed to decrypt API key {key}: {e}")
                    decrypted_keys[key] = value
            else:
                decrypted_keys[key] = value
        return decrypted_keys


# Global encryption instance
_global_encryption = None

def get_encryption() -> SecureEncryption:
    """Get global encryption instance"""
    global _global_encryption
    if _global_encryption is None:
        _global_encryption = SecureEncryption()
    return _global_encryption


def get_db_encryption() -> DatabaseEncryption:
    """Get database encryption helper"""
    return DatabaseEncryption(get_encryption())


def get_config_encryption() -> ConfigEncryption:
    """Get configuration encryption helper"""
    return ConfigEncryption(get_encryption())


# Utility functions for easy use
def encrypt_sensitive_data(data: Union[str, Dict[str, Any]], context: str = "default") -> str:
    """Convenience function to encrypt sensitive data"""
    return get_encryption().encrypt(data, context)


def decrypt_sensitive_data(encrypted_data: str, context: str = "default") -> Union[str, Dict[str, Any]]:
    """Convenience function to decrypt sensitive data"""
    return get_encryption().decrypt(encrypted_data, context)


if __name__ == "__main__":
    # Test the encryption system
    print("Testing encryption system...")
    
    # Test basic encryption
    encryption = SecureEncryption()
    
    test_data = {
        "api_key": "sk-test-key-12345",
        "user_id": "user_123",
        "sensitive_info": "This is sensitive data"
    }
    
    # Encrypt
    encrypted = encryption.encrypt(test_data, "test")
    print(f"Encrypted: {encrypted[:50]}...")
    
    # Decrypt
    decrypted = encryption.decrypt(encrypted, "test")
    print(f"Decrypted: {decrypted}")
    
    # Test string encryption
    message = "Hello, this is a secret message!"
    encrypted_msg = encryption.encrypt(message, "message")
    decrypted_msg = encryption.decrypt(encrypted_msg, "message")
    
    print(f"Original message: {message}")
    print(f"Decrypted message: {decrypted_msg}")
    print("✅ Encryption test passed!")