#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mobile-Optimized Server for Pulsar AI Assistant
Provides easy access for phones with automatic network detection
"""

import os
import sys
import socket
import argparse
import subprocess
from pathlib import Path

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

def get_local_ip():
    """Get local IP address"""
    try:
        # Create a socket connection to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def print_access_info(host, port, https=False):
    """Print mobile access information"""
    protocol = "https" if https else "http"
    local_ip = get_local_ip()
    
    print("\n" + "="*60)
    print("🚀 Pulsar AI Assistant - Mobile Server Started!")
    print("="*60)
    print(f"\n📱 Access from your phone:\n")
    print(f"   Local Network:  {protocol}://{local_ip}:{port}")
    print(f"   Localhost:      {protocol}://{host}:{port}")
    print(f"\n💡 Make sure your phone is on the same WiFi network!\n")
    print("="*60)
    print("\n🔧 To access from anywhere (internet):")
    print(f"   1. Install ngrok: https://ngrok.com/download")
    print(f"   2. Run: ngrok http {port}")
    print(f"   3. Use the ngrok URL on your phone\n")
    print("="*60)
    print("\n📲 To install as PWA (Progressive Web App):")
    print("   1. Open the URL in Chrome/Safari on your phone")
    print("   2. Tap menu → 'Add to Home Screen'")
    print("   3. Launch from home screen like a native app!\n")
    print("="*60 + "\n")

def check_firewall():
    """Check if firewall might be blocking access"""
    print("\n🔍 Checking firewall settings...")
    
    if sys.platform == "win32":
        print("   On Windows, you may need to allow Python through firewall.")
        print("   The system may prompt you when first running.")
    elif sys.platform == "darwin":
        print("   On macOS, check System Preferences → Security & Privacy → Firewall")
    else:
        print("   On Linux, check your firewall settings (ufw/iptables)")

def generate_ssl_cert():
    """Generate self-signed SSL certificate for HTTPS"""
    cert_file = Path("cert.pem")
    key_file = Path("key.pem")
    
    if cert_file.exists() and key_file.exists():
        print("✅ SSL certificate already exists")
        return str(cert_file), str(key_file)
    
    print("🔐 Generating self-signed SSL certificate...")
    try:
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:4096",
            "-nodes", "-out", "cert.pem", "-keyout", "key.pem",
            "-days", "365", "-subj", "/CN=localhost"
        ], check=True, capture_output=True)
        print("✅ SSL certificate generated successfully")
        return str(cert_file), str(key_file)
    except FileNotFoundError:
        print("❌ OpenSSL not found. Install it or use HTTP mode.")
        print("   Download: https://www.openssl.org/")
        return None, None
    except Exception as e:
        print(f"❌ Error generating certificate: {e}")
        return None, None

def start_ngrok(port):
    """Start ngrok tunnel (if installed)"""
    try:
        print("\n🌐 Attempting to start ngrok tunnel...")
        subprocess.Popen(["ngrok", "http", str(port)], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE)
        print("✅ Ngrok started! Check http://localhost:4040 for the public URL")
    except FileNotFoundError:
        print("ℹ️  Ngrok not found. Install from https://ngrok.com/download")
        print("   This is optional but allows internet access to your AI")

def main():
    parser = argparse.ArgumentParser(
        description="Mobile-optimized server for Pulsar AI Assistant"
    )
    parser.add_argument(
        "--host", 
        default="0.0.0.0", 
        help="Host to bind to (default: 0.0.0.0 for all interfaces)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=5000, 
        help="Port to run on (default: 5000)"
    )
    parser.add_argument(
        "--https", 
        action="store_true", 
        help="Enable HTTPS (required for PWA features)"
    )
    parser.add_argument(
        "--ngrok", 
        action="store_true", 
        help="Automatically start ngrok tunnel for internet access"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug mode"
    )
    
    args = parser.parse_args()
    
    # Print access information
    print_access_info(args.host, args.port, args.https)
    
    # Check firewall
    check_firewall()
    
    # Start ngrok if requested
    if args.ngrok:
        start_ngrok(args.port)
    
    # Prepare Flask run command
    # Assuming modern_web_backend.py is in the same directory as this script (src/launchers)
    launcher_dir = os.path.dirname(os.path.abspath(__file__))
    backend_script = os.path.join(launcher_dir, "modern_web_backend.py")
    
    os.environ["FLASK_APP"] = backend_script
    if args.debug:
        os.environ["FLASK_DEBUG"] = "1"
    
    # Build command
    cmd = [sys.executable, backend_script]
    
    # Set environment variables for mobile optimization
    os.environ["MOBILE_OPTIMIZED"] = "1"
    os.environ["PWA_ENABLED"] = "1"
    os.environ["SERVER_HOST"] = args.host
    os.environ["SERVER_PORT"] = str(args.port)
    
    # Handle HTTPS
    if args.https:
        cert_file, key_file = generate_ssl_cert()
        if cert_file and key_file:
            os.environ["SSL_CERT"] = cert_file
            os.environ["SSL_KEY"] = key_file
            print("\n🔐 HTTPS enabled - Your connection is encrypted!")
        else:
            print("\n⚠️  Falling back to HTTP mode")
            args.https = False
    
    # Additional mobile-friendly settings
    print("\n📱 Mobile Optimizations:")
    print("   ✅ CORS enabled for cross-origin requests")
    print("   ✅ Compression enabled for faster loading")
    print("   ✅ Service Worker for offline support")
    print("   ✅ PWA manifest for app installation")
    print("   ✅ WebSocket for real-time communication")
    
    # Final instructions
    print("\n🎯 Quick Start Guide:")
    print("   1. Make sure your backend is configured correctly")
    print("   2. Open the URL on your phone's browser")
    print("   3. Grant microphone permissions when prompted")
    print("   4. Start talking to your AI assistant!")
    print("\n   Need help? Check MOBILE_ACCESS_GUIDE.md\n")
    
    # Run the server
    try:
        print("Starting backend server...\n")
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("\nTroubleshooting:")
        print("   1. Make sure all dependencies are installed: pip install -r requirements.txt")
        print("   2. Check if port is already in use")
        print("   3. Verify backend configuration files")
        sys.exit(1)

if __name__ == "__main__":
    main()
