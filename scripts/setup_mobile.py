#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
All-in-one mobile setup script
Handles installation, icon generation, and server startup
"""

import os
import sys
import subprocess

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    # Set console code page to UTF-8
    os.system('chcp 65001 > nul 2>&1')

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"▶️  {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Done!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed!")
        print(f"   Error: {e.stderr}")
        return False

def main():
    print_header("📱 YourDaddy AI - Mobile Setup Wizard")
    
    print("This script will:")
    print("  1. Install mobile dependencies")
    print("  2. Generate PWA icons")
    print("  3. Configure mobile server")
    print("  4. Start the server with QR code")
    print()
    
    response = input("Continue? (y/n): ").lower()
    if response != 'y':
        print("Setup cancelled.")
        return
    
    # Step 1: Install dependencies
    print_header("Step 1/4: Installing Dependencies")
    
    if os.path.exists("requirements_mobile.txt"):
        run_command(
            f"{sys.executable} -m pip install -r requirements_mobile.txt",
            "Installing mobile requirements"
        )
    else:
        print("⚠️  requirements_mobile.txt not found, skipping...")
    
    # Step 2: Generate icons
    print_header("Step 2/4: Generating PWA Icons")
    
    if os.path.exists("generate_pwa_icons.py"):
        run_command(
            f"{sys.executable} generate_pwa_icons.py",
            "Generating icons"
        )
    else:
        print("⚠️  generate_pwa_icons.py not found, skipping...")
    
    # Step 3: Check configuration
    print_header("Step 3/4: Checking Configuration")
    
    checks = [
        ("modern_web_backend.py", "Backend server"),
        ("static/manifest.json", "PWA manifest"),
        ("static/service-worker.js", "Service worker"),
        ("templates/mobile_chat.html", "Mobile chat interface"),
    ]
    
    all_good = True
    for file, name in checks:
        if os.path.exists(file):
            print(f"✅ {name} - Found")
        else:
            print(f"❌ {name} - Missing")
            all_good = False
    
    if not all_good:
        print("\n⚠️  Some files are missing. Setup may not work correctly.")
        response = input("Continue anyway? (y/n): ").lower()
        if response != 'y':
            print("Setup cancelled.")
            return
    
    # Step 4: Start server
    print_header("Step 4/4: Starting Mobile Server")
    
    print("Choose server mode:")
    print("  1. Local WiFi only (fastest, most secure)")
    print("  2. Local WiFi with HTTPS (required for voice)")
    print("  3. Internet access via Ngrok (access from anywhere)")
    print()
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == '1':
        print("\n🚀 Starting local server...")
        run_command(
            f"{sys.executable} quick_mobile_start.py",
            "Starting server"
        )
    elif choice == '2':
        print("\n🚀 Starting HTTPS server...")
        run_command(
            f"{sys.executable} mobile_server.py --https",
            "Starting server"
        )
    elif choice == '3':
        # Check if ngrok is installed
        try:
            subprocess.run(["ngrok", "version"], capture_output=True, check=True)
            print("\n🚀 Starting server with Ngrok...")
            run_command(
                f"{sys.executable} mobile_server.py --ngrok",
                "Starting server"
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("\n❌ Ngrok not installed!")
            print("\nTo use internet access:")
            print("  1. Download ngrok: https://ngrok.com/download")
            print("  2. Extract and add to PATH")
            print("  3. Run this script again")
            print("\nStarting local server instead...")
            run_command(
                f"{sys.executable} quick_mobile_start.py",
                "Starting server"
            )
    else:
        print("\n⚠️  Invalid choice. Starting local server...")
        run_command(
            f"{sys.executable} quick_mobile_start.py",
            "Starting server"
        )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("\nPlease report this issue with the error message above.")
