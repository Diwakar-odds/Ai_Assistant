"""
PIN Authentication System for Pulsar AI Assistant

This module handles PIN-based authentication for the AI Assistant,
replacing traditional login pages with a simple PIN prompt at startup.

Now includes comprehensive audit logging for security events.
"""

import os
import sys
import hashlib
import secrets
import getpass
from pathlib import Path
from typing import Optional, Tuple
import json

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Import audit logging
try:
    from core.audit_logger import audit_auth_success, audit_auth_failure, audit_security_event, SeverityLevel
    AUDIT_AVAILABLE = True
except ImportError:
    AUDIT_AVAILABLE = False
    logger.warning("Audit logging not available for PIN authentication")


class PINAuth:
    """PIN-based authentication system"""
    
    def __init__(self):
        """Initialize PIN authentication"""
        self.config_file = Path(__file__).parent.parent / 'config' / 'app_integration.env'
        self.user_settings_file = Path(__file__).parent.parent / 'config' / 'user_settings.json'
        self.pin_hash = None
        self.salt = None
        
        # Load PIN hash and salt from config file
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract PIN hash and salt from env file
            for line in content.split('\n'):
                if line.startswith('PIN_HASH='):
                    self.pin_hash = line.split('=', 1)[1].strip()
                elif line.startswith('PIN_SALT='):
                    self.salt = line.split('=', 1)[1].strip()
        
        # Fallback to user settings file if not found in env
        if not self.pin_hash and self.user_settings_file.exists():
            try:
                with open(self.user_settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # Look for PIN in security settings
                for setting_group in settings.get('settings', []):
                    if setting_group.get('title') == 'Security & Privacy':
                        for setting in setting_group.get('settings', []):
                            if setting.get('name') == 'PIN Authentication':
                                self.pin_hash = setting.get('pin_hash')
                                self.salt = setting.get('pin_salt')
                                break
            except Exception as e:
                logger.warning(f"Could not load PIN from user settings: {e}")
    
    def _hash_pin(self, pin: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash a PIN using PBKDF2
        
        Args:
            pin: The PIN to hash
            salt: Optional salt (generates new one if not provided)
        
        Returns:
            Tuple of (hashed_pin, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Use PBKDF2 for secure hashing
        pin_bytes = pin.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        
        # 100,000 iterations for security
        hash_obj = hashlib.pbkdf2_hmac('sha256', pin_bytes, salt_bytes, 100000)
        hashed_pin = hash_obj.hex()
        
        return hashed_pin, salt
    
    def is_pin_configured(self) -> bool:
        """Check if a PIN is already configured"""
        return self.pin_hash is not None and self.salt is not None
    
    def verify_pin(self, pin: str) -> bool:
        """
        Verify a PIN against the stored hash
        
        Args:
            pin: The PIN to verify
        
        Returns:
            True if PIN is correct, False otherwise
        """
        if not self.is_pin_configured():
            logger.warning("No PIN configured for verification")
            return False
        
        try:
            hashed_pin, _ = self._hash_pin(pin, self.salt)
            return hashed_pin == self.pin_hash
        except Exception as e:
            logger.error(f"Error verifying PIN: {e}")
            return False
    
    def prompt_for_pin(self, max_attempts: int = 3) -> bool:
        """
        Prompt user for PIN and verify
        
        Args:
            max_attempts: Maximum number of attempts allowed
        
        Returns:
            True if authentication successful, False otherwise
        """
        if not self.is_pin_configured():
            logger.warning("⚠️  PIN authentication not configured")
            print("Run 'python main.py --setup-pin' to configure PIN")
            return False
            
        for attempt in range(max_attempts):
            try:
                pin = getpass.getpass("🔐 Enter PIN: ")
                
                if self.verify_pin(pin):
                    logger.info("PIN authentication successful")
                    if AUDIT_AVAILABLE:
                        audit_auth_success("PIN authentication")
                    return True
                else:
                    remaining = max_attempts - attempt - 1
                    if remaining > 0:
                        logger.error(f"❌ Invalid PIN. {remaining} attempts remaining.")
                    else:
                        logger.error("❌ Invalid PIN. Access denied.")
                    
                    if AUDIT_AVAILABLE:
                        audit_auth_failure("PIN authentication", "Invalid PIN")
                    
            except KeyboardInterrupt:
                print("\n❌ PIN authentication cancelled")
                return False
            except Exception as e:
                logger.error(f"Error during PIN prompt: {e}")
                logger.error(f"❌ Error: {e}")
                return False
        
        return False
    
    def setup_pin(self, pin: str) -> bool:
        """
        Set up a new PIN for the assistant
        
        Args:
            pin: The PIN to configure
        
        Returns:
            True if PIN was successfully configured, False otherwise
        """
        try:
            # Validate PIN
            if len(pin) < 4:
                logger.error("❌ PIN must be at least 4 digits long")
                if AUDIT_AVAILABLE:
                    audit_auth_failure("setup", "PIN too short during setup")
                return False
            
            if not pin.isdigit():
                logger.error("❌ PIN must contain only numbers")
                if AUDIT_AVAILABLE:
                    audit_auth_failure("setup", "Invalid PIN format during setup")
                return False
            
            # Hash the PIN
            hashed_pin, salt = self._hash_pin(pin)
            
            # Save to environment file
            self._save_pin_to_env(hashed_pin, salt)
            
            # Update instance variables
            self.pin_hash = hashed_pin
            self.salt = salt
            
            logger.info("PIN configured successfully")
            logger.info("✅ PIN configured successfully!")
            
            # Audit successful PIN setup
            if AUDIT_AVAILABLE:
                audit_security_event(
                    "PIN authentication configured successfully",
                    SeverityLevel.INFO
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up PIN: {e}")
            logger.error(f"❌ Error setting up PIN: {e}")
            
            if AUDIT_AVAILABLE:
                audit_security_event(
                    f"PIN setup failed: {str(e)}",
                    SeverityLevel.HIGH
                )
            
            return False
    
    def _save_pin_to_env(self, hashed_pin: str, salt: str) -> None:
        """Save PIN hash and salt to environment file"""
        try:
            # Create config directory if it doesn't exist
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing content
            existing_content = ""
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
            
            # Remove existing PIN entries
            lines = []
            for line in existing_content.split('\n'):
                if not (line.startswith('PIN_HASH=') or line.startswith('PIN_SALT=')):
                    lines.append(line)
            
            # Add PIN section if not present
            if not any('PIN AUTHENTICATION' in line for line in lines):
                lines.extend([
                    "",
                    "# =============================================================================",
                    "# PIN AUTHENTICATION",
                    "# =============================================================================",
                    ""
                ])
            
            # Add new PIN entries
            lines.append(f"PIN_HASH={hashed_pin}")
            lines.append(f"PIN_SALT={salt}")
            
            # Write back to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            logger.info(f"PIN saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Error saving PIN to env file: {e}")
            raise
    
    def _setup_new_pin(self) -> bool:
        """Set up a new PIN interactively"""
        print("-" * 20)
        print("PIN Requirements:")
        print("• At least 4 digits")
        print("• Numbers only")
        print("• Easy to remember but not obvious")
        print()
        
        while True:
            try:
                pin1 = getpass.getpass("Enter new PIN: ")
                
                if len(pin1) < 4:
                    logger.error("❌ PIN must be at least 4 digits long")
                    continue
                
                if not pin1.isdigit():
                    logger.error("❌ PIN must contain only numbers")
                    continue
                
                pin2 = getpass.getpass("Confirm PIN: ")
                
                if pin1 != pin2:
                    logger.error("❌ PINs do not match. Please try again.")
                    continue
                
                # Set up the PIN
                if self.setup_pin(pin1):
                    print("\n✅ PIN setup complete! Please restart the assistant.")
                    return True
                else:
                    logger.error("❌ Failed to setup PIN. Please try again.")
                    
            except KeyboardInterrupt:
                print("\n❌ PIN setup cancelled")
                return False
            except Exception as e:
                logger.error(f"Error during PIN setup: {e}")
                logger.error(f"❌ PIN setup error: {e}")
                return False
    
    def change_pin(self) -> bool:
        """Change the current PIN"""
        print("\n🔄 Change PIN")
        print("-" * 20)
        
        # Verify current PIN
        if self.is_pin_configured():
            current_pin = getpass.getpass("Enter current PIN: ")
            if not self.verify_pin(current_pin):
                logger.error("❌ Current PIN is incorrect")
                if AUDIT_AVAILABLE:
                    audit_auth_failure("change_pin", "Invalid current PIN")
                return False
        
        # Set up new PIN
        return self._setup_new_pin()


def authenticate() -> bool:
    """
    Main authentication function to be called at startup
    
    Returns:
        True if authentication successful, False otherwise
    """
    auth = PINAuth()
    return auth.prompt_for_pin()


def require_pin_auth(skip_auth_arg='--skip-auth'):
    """
    Decorator/helper function to add PIN authentication to any script
    
    Usage:
    if __name__ == "__main__":
        require_pin_auth()
        main()
    """
    import argparse
    
    # Check for skip auth argument
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(skip_auth_arg, action='store_true', help='Skip PIN authentication')
    args, unknown = parser.parse_known_args()
    
    if not getattr(args, skip_auth_arg.lstrip('--').replace('-', '_')):
        print("🔐 PIN Authentication Required")
        print("-" * 30)
        if not authenticate():
            logger.error("❌ Authentication failed. Exiting...")
            sys.exit(1)
        logger.info("✅ Authentication successful!\n")


def setup_pin_cli():
    """CLI utility for PIN setup"""
    print("🔐 Pulsar Assistant - PIN Setup Utility")
    print("=" * 50)
    
    auth = PINAuth()
    
    if auth.is_pin_configured():
        logger.info("✅ PIN is already configured")
        choice = input("Do you want to change it? (y/N): ").lower()
        if choice == 'y':
            auth.change_pin()
    else:
        logger.warning("⚠️  No PIN configured. Setting up new PIN...")
        auth._setup_new_pin()


if __name__ == "__main__":
    # CLI entry point for PIN setup
    setup_pin_cli()
