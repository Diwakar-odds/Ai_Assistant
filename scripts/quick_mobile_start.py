#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick start script for mobile access
Automatically detects network and provides QR code
"""

import sys
import os

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

import qrcode
import socket
from pathlib import Path

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def generate_qr_code(url):
    """Generate QR code for easy mobile access"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    
    print("\n📱 Scan this QR code with your phone:\n")
    qr.print_ascii(invert=True)
    print()

def main():
    port = 5000
    local_ip = get_local_ip()
    url = f"http://{local_ip}:{port}"
    
    print("="*60)
    print("🚀 Pulsar AI - Mobile Quick Start")
    print("="*60)
    
    print(f"\n📡 Your Computer's IP: {local_ip}")
    print(f"🌐 Access URL: {url}\n")
    
    generate_qr_code(url)
    
    print("📋 Steps:")
    print("  1. Make sure your phone is on the same WiFi")
    print("  2. Scan the QR code above OR")
    print(f"  3. Open browser and go to: {url}")
    print("  4. Start chatting with your AI!\n")
    
    print("💡 Tip: Add to home screen for app-like experience")
    print("="*60)
    
    # Start server
    print("\n🎬 Starting server...\n")
    import subprocess
    
    # Try simple server first, fall back to full backend
    try:
        subprocess.run([sys.executable, "simple_mobile_server.py"])
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"\n⚠️  Error: {e}")
        print("\nTrying full backend server...")
        try:
            subprocess.run([sys.executable, "modern_web_backend.py"])
        except Exception as e2:
            print(f"\n❌ Backend server also failed: {e2}")
            print("\nPlease check:")
            print("  1. All dependencies are installed")
            print("  2. Backend configuration is correct")
            print(f"  3. Port {port} is not already in use")

if __name__ == "__main__":
    main()
