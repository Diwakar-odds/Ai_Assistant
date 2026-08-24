#!/usr/bin/env python3
"""
PIN Setup Utility for Pulsar AI Assistant

Standalone utility to setup, change, or manage PIN authentication.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Main function for PIN setup utility"""
    print("\n🔐 Pulsar AI Assistant - PIN Management Utility")
    print("=" * 60)
    
    try:
        from ai_assistant.auth import PINAuth
    except ImportError as e:
        print(f"❌ Error importing PIN authentication module: {e}")
        print("Please ensure the assistant is properly installed.")
        sys.exit(1)
    
    auth = PINAuth()
    
    # Check current PIN status
    if auth.is_pin_configured():
        print("✅ PIN is currently configured")
        print("\nOptions:")
        print("1. Change PIN")
        print("2. Test current PIN")
        print("3. Exit")
        
        while True:
            try:
                choice = input("\nSelect option (1-3): ").strip()
                
                if choice == "1":
                    print("\n🔄 Changing PIN...")
                    if auth.change_pin():
                        print("✅ PIN changed successfully!")
                    else:
                        print("❌ Failed to change PIN")
                    break
                    
                elif choice == "2":
                    print("\n🔍 Testing current PIN...")
                    if auth.prompt_for_pin(max_attempts=1):
                        print("✅ PIN verification successful!")
                    else:
                        print("❌ PIN verification failed")
                    break
                    
                elif choice == "3":
                    print("👋 Goodbye!")
                    break
                    
                else:
                    print("❌ Invalid choice. Please select 1-3.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                break
                
    else:
        print("⚠️  No PIN is configured")
        print("\nThe AI Assistant requires a PIN for secure access.")
        print("Would you like to set up a PIN now?")
        
        try:
            choice = input("Set up PIN? (y/N): ").strip().lower()
            
            if choice == 'y':
                print("\n📝 Setting up new PIN...")
                if auth._setup_new_pin():
                    print("✅ PIN setup completed successfully!")
                    print("\nYou can now start the AI Assistant normally.")
                else:
                    print("❌ PIN setup failed")
            else:
                print("⚠️  Assistant will require PIN setup before first use.")
                
        except KeyboardInterrupt:
            print("\n👋 Setup cancelled")
        except Exception as e:
            print(f"❌ Error during setup: {e}")


def show_help():
    """Show help information"""
    print("""
PIN Management Utility for Pulsar AI Assistant

This utility helps you manage PIN authentication for the AI Assistant.

Usage:
    python setup_pin.py              # Interactive PIN management
    python main.py --setup-pin       # Setup PIN through main application

Features:
• Set up new PIN for first-time use
• Change existing PIN
• Test PIN verification
• Secure PIN storage with PBKDF2 hashing

PIN Requirements:
• At least 4 digits
• Numbers only
• Should be memorable but not obvious

The PIN is securely hashed and stored in config/app_integration.env
""")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        show_help()
    else:
        main()
