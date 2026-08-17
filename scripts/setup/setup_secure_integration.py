#!/usr/bin/env python3
"""
AI Assistant Secure App Integration - Quick Setup

This script helps you quickly set up secure app integration for your AI assistant.
It will guide you through the initial configuration and security setup.
"""

import os
import sys
import secrets
import subprocess
from pathlib import Path

def print_header():
    print("🤖 AI Assistant - Secure App Integration Setup")
    print("=" * 50)
    print("This setup will help you securely connect apps to your assistant.")
    print("Your personal information and credentials will be encrypted and protected.")
    print()

def check_dependencies():
    """Check if required packages are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = ['cryptography', 'flask', 'flask_cors']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Installing required packages...")
        
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("✅ Dependencies installed successfully!")
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies. Please install manually:")
            print(f"pip install {' '.join(missing_packages)}")
            return False
    else:
        print("✅ All dependencies are installed!")
    
    return True

def setup_security_config():
    """Set up secure configuration."""
    print("\n🔐 Setting up security configuration...")
    
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    # Check if config already exists
    config_file = config_dir / "app_integration.env"
    if config_file.exists():
        print("⚠️  Configuration file already exists.")
        overwrite = input("Do you want to overwrite it? (y/n): ").lower().strip()
        if overwrite != 'y':
            print("Keeping existing configuration.")
            return True
    
    # Copy example file if it exists
    example_file = config_dir / "app_integration.env.example"
    if example_file.exists():
        with open(example_file, 'r') as f:
            config_content = f.read()
    else:
        # Create basic config if example doesn't exist
        config_content = """# AI Assistant App Integration Configuration

# Security Settings
ENABLE_APP_INTEGRATIONS=true
INTEGRATION_API_PORT=5001

# Admin Credentials (CHANGE THESE!)
ADMIN_PASSWORD=changeme123
APP_SECRET_KEY=change-this-secret-key

# Feature Flags
ENABLE_CREDENTIAL_ENCRYPTION=true
ENABLE_PERMISSION_VALIDATION=true
ENABLE_APP_INTEGRATION_LOGGING=true

# Security Levels
APP_SECURITY_LEVEL=high
MAX_CONCURRENT_APPS=10
"""
    
    # Generate secure credentials
    print("\n🔑 Generating secure credentials...")
    admin_password = secrets.token_urlsafe(24)
    secret_key = secrets.token_hex(32)
    
    print(f"Generated admin password: {admin_password}")
    print(f"Generated secret key: {secret_key[:16]}...")
    print("\n⚠️  IMPORTANT: Save these credentials securely!")
    
    # Update config with generated credentials
    config_content = config_content.replace("changeme123", admin_password)
    config_content = config_content.replace("change-this-secret-key", secret_key)
    
    # Write config file
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    # Set secure file permissions (Unix-like systems)
    try:
        os.chmod(config_file, 0o600)  # Owner read/write only
    except OSError:
        pass  # Windows doesn't support these permissions
    
    print(f"✅ Configuration saved to: {config_file}")
    return True

def setup_secure_directory():
    """Set up secure directory for encrypted credentials."""
    print("\n🔒 Setting up secure directory...")
    
    secure_dir = Path("config/secure")
    secure_dir.mkdir(exist_ok=True)
    
    # Create .gitignore for secure directory
    gitignore_path = secure_dir / ".gitignore"
    with open(gitignore_path, 'w') as f:
        f.write("# Secure configuration files - DO NOT COMMIT TO GIT\n")
        f.write("*\n")
        f.write("!.gitignore\n")
    
    print("✅ Secure directory created with git protection")

def create_startup_scripts():
    """Create startup scripts for easy launching."""
    print("\n📜 Creating startup scripts...")
    
    scripts_dir = Path("scripts")
    scripts_dir.mkdir(exist_ok=True)
    
    # Windows batch script
    batch_script = scripts_dir / "start_integration.bat"
    batch_content = """@echo off
echo Starting AI Assistant App Integration...
python -m ai_assistant.services.app_integration_api
pause
"""
    
    with open(batch_script, 'w') as f:
        f.write(batch_content)
    
    # Unix shell script
    shell_script = scripts_dir / "start_integration.sh"
    shell_content = """#!/bin/bash
echo "Starting AI Assistant App Integration..."
python -m ai_assistant.services.app_integration_api
"""
    
    with open(shell_script, 'w') as f:
        f.write(shell_content)
    
    # Make shell script executable
    try:
        os.chmod(shell_script, 0o755)
    except OSError:
        pass
    
    print("✅ Startup scripts created")

def verify_setup():
    """Verify the setup is working correctly."""
    print("\n🧪 Verifying setup...")
    
    try:
        # Test imports
        from ai_assistant.core.app_security import secure_app_manager
        from ai_assistant.core.app_integrator import secure_app_integrator
        print("✅ Core modules imported successfully")
        
        # Test configuration
        config_file = Path("config/app_integration.env")
        if config_file.exists():
            print("✅ Configuration file exists")
        else:
            print("❌ Configuration file missing")
            return False
        
        # Test secure directory
        secure_dir = Path("config/secure")
        if secure_dir.exists():
            print("✅ Secure directory exists")
        else:
            print("❌ Secure directory missing")
            return False
        
        print("✅ Setup verification completed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all dependencies are installed")
        return False

def show_next_steps():
    """Show next steps to the user."""
    print("\n🎉 Setup Complete!")
    print("=" * 30)
    print("\nNext steps:")
    print("1. 🚀 Start the integration server:")
    print("   Windows: scripts\\start_integration.bat")
    print("   Linux/Mac: ./scripts/start_integration.sh")
    print("   Manual: python -m ai_assistant.services.app_integration_api")
    print("\n2. 📱 Access the web interface:")
    print("   URL: http://localhost:5001")
    print("   Login with the generated admin password")
    print("\n3. 🔧 Or use the command-line tool:")
    print("   python -m ai_assistant.cli.app_manager register")
    print("\n4. 📖 Read the documentation:")
    print("   docs/SETUP_SECURE_APP_INTEGRATION.md")
    print("   docs/APP_INTEGRATION_SECURITY.md")
    print("\n🔒 Security reminders:")
    print("- Your credentials are encrypted and stay local")
    print("- Sensitive files are automatically excluded from git")
    print("- Change the admin password if needed")
    print("- Review app permissions before granting access")

def main():
    """Main setup function."""
    print_header()
    
    # Check if we're in the right directory
    if not Path("ai_assistant").exists():
        print("❌ Please run this script from the AI Assistant root directory")
        return
    
    try:
        # Step 1: Check dependencies
        if not check_dependencies():
            print("❌ Setup failed: Missing dependencies")
            return
        
        # Step 2: Set up security configuration
        if not setup_security_config():
            print("❌ Setup failed: Security configuration")
            return
        
        # Step 3: Set up secure directory
        setup_secure_directory()
        
        # Step 4: Create startup scripts
        create_startup_scripts()
        
        # Step 5: Verify setup
        if not verify_setup():
            print("❌ Setup verification failed")
            return
        
        # Step 6: Show next steps
        show_next_steps()
        
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled by user")
    except Exception as e:
        print(f"❌ Setup failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()