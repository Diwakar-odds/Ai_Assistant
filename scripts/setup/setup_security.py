#!/usr/bin/env python3
"""
Security Setup Script for YourDaddy AI Assistant

This script helps you set up secure credentials for the assistant.
Run this script to:
1. Generate secure random secrets
2. Create/update your config/app_integration.env file
3. Validate your security configuration

Usage:
    python scripts/setup/setup_security.py
"""

import os
import sys
import secrets
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def generate_secure_key(length: int = 32) -> str:
    """Generate a cryptographically secure random key."""
    return secrets.token_urlsafe(length)


def setup_env_file():
    """Set up the app_integration.env file with secure values."""
    config_dir = project_root / 'config'
    env_file = config_dir / 'app_integration.env'
    example_file = config_dir / 'app_integration.env.example'
    
    print("\n" + "=" * 60)
    print("🔐 YourDaddy AI Assistant - Security Setup")
    print("=" * 60)
    
    # Check if env file already exists
    if env_file.exists():
        print(f"\n⚠️  Config file already exists: {env_file}")
        response = input("Do you want to regenerate secrets? (y/N): ").strip().lower()
        if response != 'y':
            print("Keeping existing configuration.")
            return validate_existing_config(env_file)
    
    # Read example file or create from scratch
    if example_file.exists():
        print(f"\n📄 Using template: {example_file}")
        with open(example_file, 'r') as f:
            content = f.read()
    else:
        print("\n📄 Creating new configuration from scratch...")
        content = create_default_config()
    
    # Generate secure values
    print("\n🔑 Generating secure credentials...")
    
    admin_password = generate_secure_key(32)
    app_secret_key = generate_secure_key(32)
    jwt_secret_key = generate_secure_key(64)
    encryption_key = generate_secure_key(32)
    
    # Replace placeholder values
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        if line.startswith('ADMIN_PASSWORD='):
            new_lines.append(f'ADMIN_PASSWORD={admin_password}')
        elif line.startswith('APP_SECRET_KEY='):
            new_lines.append(f'APP_SECRET_KEY={app_secret_key}')
        elif line.startswith('JWT_SECRET_KEY=') or (line.startswith('#') and 'JWT_SECRET_KEY' in line):
            new_lines.append(f'JWT_SECRET_KEY={jwt_secret_key}')
        elif line.startswith('ENCRYPTION_MASTER_KEY=') or (line.startswith('#') and 'ENCRYPTION_MASTER_KEY' in line):
            new_lines.append(f'ENCRYPTION_MASTER_KEY={encryption_key}')
        else:
            new_lines.append(line)
    
    # Ensure all required keys are present
    content_check = '\n'.join(new_lines)
    if 'JWT_SECRET_KEY=' not in content_check:
        new_lines.append(f'\n# JWT Secret Key (auto-generated)')
        new_lines.append(f'JWT_SECRET_KEY={jwt_secret_key}')
    if 'ENCRYPTION_MASTER_KEY=' not in content_check:
        new_lines.append(f'\n# Encryption Master Key (auto-generated)')
        new_lines.append(f'ENCRYPTION_MASTER_KEY={encryption_key}')
    
    # Write the new config
    config_dir.mkdir(parents=True, exist_ok=True)
    with open(env_file, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print(f"\n✅ Configuration saved to: {env_file}")
    print("\n" + "-" * 60)
    print("🔐 Generated Credentials (save these securely!):")
    print("-" * 60)
    print(f"ADMIN_PASSWORD: {admin_password}")
    print(f"APP_SECRET_KEY: {app_secret_key[:16]}...")
    print(f"JWT_SECRET_KEY: {jwt_secret_key[:16]}...")
    print("-" * 60)
    
    print("\n⚠️  IMPORTANT:")
    print("   • Never commit config/app_integration.env to version control")
    print("   • Store these credentials securely")
    print("   • The admin password is required to access admin features")
    
    return True


def validate_existing_config(env_file: Path) -> bool:
    """Validate an existing configuration file."""
    print("\n🔍 Validating configuration...")
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    issues = []
    
    # Check for required keys
    required_keys = ['ADMIN_PASSWORD', 'APP_SECRET_KEY']
    for key in required_keys:
        if f'{key}=' not in content:
            issues.append(f"Missing required key: {key}")
        else:
            # Check if value is set (not empty)
            for line in content.split('\n'):
                if line.startswith(f'{key}='):
                    value = line.split('=', 1)[1].strip()
                    if not value:
                        issues.append(f"{key} is empty")
                    elif len(value) < 16:
                        issues.append(f"{key} appears too short (should be at least 16 characters)")
    
    # Check for insecure default values
    insecure_patterns = ['changeme', 'password', 'secret', 'admin123', 'test']
    for pattern in insecure_patterns:
        if pattern in content.lower():
            issues.append(f"Found potentially insecure value containing '{pattern}'")
    
    if issues:
        print("\n❌ Configuration Issues Found:")
        for issue in issues:
            print(f"   • {issue}")
        print("\nRun this script with 'y' to regenerate secure values.")
        return False
    else:
        print("✅ Configuration looks secure!")
        return True


def create_default_config() -> str:
    """Create a default configuration template."""
    return """# Security Configuration for App Integrations
# Generated by setup_security.py
# WARNING: This file contains sensitive data. DO NOT commit to version control!

# =============================================================================
# APP INTEGRATION SECURITY
# =============================================================================

ENABLE_APP_INTEGRATIONS=true
INTEGRATION_API_PORT=5001

# Admin password for app management (auto-generated)
ADMIN_PASSWORD=

# Secret key for app integration sessions (auto-generated)
APP_SECRET_KEY=

# Maximum number of concurrent app launches
MAX_CONCURRENT_APPS=10

# App security settings
APP_SECURITY_LEVEL=high

# Auto-cleanup terminated processes (seconds)
CLEANUP_INTERVAL=300

# Enable app permission validation
ENABLE_PERMISSION_VALIDATION=true

# Allowed app categories (comma-separated)
ALLOWED_APP_CATEGORIES=productivity,media,development,communication,utility,entertainment,business

# Enable detailed logging for app integrations
ENABLE_APP_INTEGRATION_LOGGING=true

# =============================================================================
# ENCRYPTION SETTINGS
# =============================================================================

ENABLE_CREDENTIAL_ENCRYPTION=true
KEY_ROTATION_INTERVAL=90

# =============================================================================
# NETWORK SECURITY
# =============================================================================

ALLOWED_NETWORKS=127.0.0.1/32,192.168.1.0/24
ENABLE_INTEGRATION_RATE_LIMITING=true
INTEGRATION_RATE_LIMIT=100
"""


def setup_pin():
    """Set up PIN authentication."""
    print("\n" + "=" * 60)
    print("🔐 PIN Authentication Setup")
    print("=" * 60)
    
    try:
        from ai_assistant.auth import setup_pin_cli
        setup_pin_cli()
    except ImportError as e:
        print(f"\n❌ Could not import PIN authentication module: {e}")
        print("Run: python main.py --setup-pin")


def main():
    """Main setup function."""
    print("\n🚀 Starting Security Setup...\n")
    
    # Step 1: Set up environment file
    env_success = setup_env_file()
    
    # Step 2: Optionally set up PIN
    print("\n" + "=" * 60)
    response = input("\nWould you like to set up PIN authentication? (y/N): ").strip().lower()
    if response == 'y':
        setup_pin()
    
    # Final summary
    print("\n" + "=" * 60)
    print("📋 Setup Summary")
    print("=" * 60)
    
    if env_success:
        print("✅ Environment configuration: Complete")
    else:
        print("⚠️  Environment configuration: Needs attention")
    
    print("\n🎉 Security setup complete!")
    print("\nNext steps:")
    print("  1. Review config/app_integration.env")
    print("  2. Set up PIN with: python main.py --setup-pin")
    print("  3. Start the assistant: python main.py")


if __name__ == '__main__':
    main()
