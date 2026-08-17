"""
AI Assistant App Security Module

This module provides secure app integration capabilities while protecting
sensitive information from being exposed in public repositories.
"""

import os
import json
import hashlib
import secrets
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class SecureAppManager:
    """Manages secure app integrations with encryption and access controls."""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self.secure_dir = self.config_dir / "secure"
        self.secure_dir.mkdir(exist_ok=True)
        
        # Create .gitignore for secure directory if it doesn't exist
        gitignore_path = self.secure_dir / ".gitignore"
        if not gitignore_path.exists():
            with open(gitignore_path, 'w') as f:
                f.write("# Secure configuration files - DO NOT COMMIT\n*\n!.gitignore\n")
        
        self.logger = logging.getLogger(__name__)
        self._cipher = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption for sensitive data."""
        try:
            # Try to load existing key
            key_file = self.secure_dir / ".key"
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    key = f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(key)
                # Secure the key file
                os.chmod(key_file, 0o600)  # Owner read/write only
            
            self._cipher = Fernet(key)
        except Exception as e:
            self.logger.error(f"Failed to initialize encryption: {e}")
            raise
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        if self._cipher is None:
            raise RuntimeError("Encryption not initialized")
        return base64.b64encode(self._cipher.encrypt(data.encode())).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        if self._cipher is None:
            raise RuntimeError("Encryption not initialized")
        return self._cipher.decrypt(base64.b64decode(encrypted_data.encode())).decode()
    
    def store_app_credentials(self, app_name: str, credentials: Dict[str, Any]):
        """Securely store app credentials."""
        try:
            # Encrypt sensitive fields
            encrypted_credentials = {}
            for key, value in credentials.items():
                if any(sensitive in key.lower() for sensitive in ['key', 'secret', 'token', 'password']):
                    encrypted_credentials[key] = self.encrypt_data(str(value))
                else:
                    encrypted_credentials[key] = value
            
            # Store in secure directory
            cred_file = self.secure_dir / f"{app_name}_credentials.json"
            with open(cred_file, 'w') as f:
                json.dump(encrypted_credentials, f, indent=2)
            
            os.chmod(cred_file, 0o600)  # Owner read/write only
            self.logger.info(f"Credentials stored securely for {app_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to store credentials for {app_name}: {e}")
            raise
    
    def load_app_credentials(self, app_name: str) -> Optional[Dict[str, Any]]:
        """Load and decrypt app credentials."""
        try:
            cred_file = self.secure_dir / f"{app_name}_credentials.json"
            if not cred_file.exists():
                return None
            
            with open(cred_file, 'r') as f:
                encrypted_credentials = json.load(f)
            
            # Decrypt sensitive fields
            credentials = {}
            for key, value in encrypted_credentials.items():
                if any(sensitive in key.lower() for sensitive in ['key', 'secret', 'token', 'password']):
                    credentials[key] = self.decrypt_data(value)
                else:
                    credentials[key] = value
            
            return credentials
            
        except Exception as e:
            self.logger.error(f"Failed to load credentials for {app_name}: {e}")
            return None
    
    def register_secure_app(self, app_config: Dict[str, Any]) -> bool:
        """Register an app with secure configuration."""
        try:
            app_name = app_config.get('name', '').lower()
            if not app_name:
                raise ValueError("App name is required")
            
            # Separate public and private config
            public_config = {
                'name': app_config.get('name'),
                'display_name': app_config.get('display_name'),
                'description': app_config.get('description'),
                'category': app_config.get('category'),
                'executable_path': app_config.get('executable_path'),
                'startup_args': app_config.get('startup_args', []),
                'permissions': app_config.get('permissions', []),
                'integration_type': app_config.get('integration_type', 'basic'),
                'registered_at': str(datetime.now())
            }
            
            # Extract credentials
            credentials = {}
            sensitive_fields = ['api_key', 'client_secret', 'access_token', 'refresh_token', 'password']
            for field in sensitive_fields:
                if field in app_config:
                    credentials[field] = app_config[field]
            
            # Store public config
            apps_file = self.config_dir / "registered_apps.json"
            apps_data = {}
            if apps_file.exists():
                with open(apps_file, 'r') as f:
                    apps_data = json.load(f)
            
            apps_data[app_name] = public_config
            with open(apps_file, 'w') as f:
                json.dump(apps_data, f, indent=2)
            
            # Store credentials securely if any
            if credentials:
                self.store_app_credentials(app_name, credentials)
            
            self.logger.info(f"App {app_name} registered successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register app: {e}")
            return False
    
    def get_app_access_token(self, app_name: str) -> Optional[str]:
        """Get access token for an app (if available)."""
        credentials = self.load_app_credentials(app_name)
        if credentials:
            return credentials.get('access_token') or credentials.get('api_key')
        return None
    
    def validate_app_permissions(self, app_name: str, required_permissions: List[str]) -> bool:
        """Validate if an app has required permissions."""
        try:
            apps_file = self.config_dir / "registered_apps.json"
            if not apps_file.exists():
                return False
            
            with open(apps_file, 'r') as f:
                apps_data = json.load(f)
            
            app_config = apps_data.get(app_name.lower())
            if not app_config:
                return False
            
            app_permissions = app_config.get('permissions', [])
            return all(perm in app_permissions for perm in required_permissions)
            
        except Exception as e:
            self.logger.error(f"Failed to validate permissions for {app_name}: {e}")
            return False
    
    def list_registered_apps(self) -> Dict[str, Dict[str, Any]]:
        """List all registered apps (without sensitive data)."""
        try:
            apps_file = self.config_dir / "registered_apps.json"
            if not apps_file.exists():
                return {}
            
            with open(apps_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"Failed to list registered apps: {e}")
            return {}
    
    def remove_app(self, app_name: str) -> bool:
        """Remove an app and its credentials."""
        try:
            app_name = app_name.lower()
            
            # Remove from registered apps
            apps_file = self.config_dir / "registered_apps.json"
            if apps_file.exists():
                with open(apps_file, 'r') as f:
                    apps_data = json.load(f)
                
                if app_name in apps_data:
                    del apps_data[app_name]
                    with open(apps_file, 'w') as f:
                        json.dump(apps_data, f, indent=2)
            
            # Remove credentials
            cred_file = self.secure_dir / f"{app_name}_credentials.json"
            if cred_file.exists():
                cred_file.unlink()
            
            self.logger.info(f"App {app_name} removed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove app {app_name}: {e}")
            return False

# Global instance
secure_app_manager = SecureAppManager()