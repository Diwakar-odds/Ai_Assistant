#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test mobile setup - verify all components work
"""

import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.system('chcp 65001 > nul 2>&1')

def test_encoding():
    """Test if emoji output works"""
    try:
        print("Testing emoji output: 🚀 ✅ 📱 🎨 ❌")
        return True
    except Exception as e:
        print(f"Encoding test failed: {e}")
        return False

def check_file(filepath, name):
    """Check if a file exists"""
    if os.path.exists(filepath):
        print(f"✅ {name} - Found")
        return True
    else:
        print(f"❌ {name} - Missing")
        return False

def main():
    print("="*60)
    print("  Mobile Setup Test")
    print("="*60)
    print()
    
    # Test encoding
    print("1. Testing console encoding...")
    if test_encoding():
        print("   ✅ Encoding works!")
    else:
        print("   ⚠️  Encoding issues detected")
    print()
    
    # Check required files
    print("2. Checking required files...")
    files = {
        "setup_mobile.py": "Setup script",
        "quick_mobile_start.py": "Quick start script",
        "mobile_server.py": "Mobile server",
        "generate_pwa_icons.py": "Icon generator",
        "static/manifest.json": "PWA manifest",
        "static/service-worker.js": "Service worker",
        "templates/mobile_chat.html": "Mobile chat interface",
        "requirements_mobile.txt": "Mobile requirements",
    }
    
    all_found = True
    for filepath, name in files.items():
        if not check_file(filepath, name):
            all_found = False
    print()
    
    # Check dependencies
    print("3. Checking Python dependencies...")
    try:
        import flask
        print("   ✅ Flask installed")
    except ImportError:
        print("   ❌ Flask not installed")
        all_found = False
    
    try:
        from PIL import Image
        print("   ✅ Pillow installed")
    except ImportError:
        print("   ❌ Pillow not installed")
        all_found = False
    
    try:
        import qrcode
        print("   ✅ QRCode installed")
    except ImportError:
        print("   ⚠️  QRCode not installed (optional)")
    print()
    
    # Final status
    print("="*60)
    if all_found:
        print("✅ All checks passed! Mobile setup is ready.")
        print()
        print("Next steps:")
        print("  1. Run: python quick_mobile_start.py")
        print("  2. Scan QR code with your phone")
        print("  3. Add to home screen")
    else:
        print("⚠️  Some components are missing.")
        print()
        print("To fix:")
        print("  pip install -r requirements_mobile.txt")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()
