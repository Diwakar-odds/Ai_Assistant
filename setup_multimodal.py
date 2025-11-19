# Setup Multi-Modal AI Dependencies
"""
Setup script to install additional dependencies for multi-modal AI features.
Run this before using the new multi-modal capabilities.
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a Python package using pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def check_package(package):
    """Check if a package is already installed."""
    try:
        __import__(package)
        return True
    except ImportError:
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up Multi-Modal AI Dependencies")
    print("=" * 50)
    
    # Core multi-modal packages
    packages = [
        ("opencv-python", "cv2"),
        ("numpy", "numpy"),
        ("tensorflow", "tensorflow"),
        ("torch", "torch"),
        ("torchvision", "torchvision"),
        ("transformers", "transformers"),
        ("sentence-transformers", "sentence_transformers")
    ]
    
    print("📦 Checking current packages...")
    
    installed = []
    to_install = []
    
    for pip_name, import_name in packages:
        if check_package(import_name):
            print(f"✅ {pip_name} - Already installed")
            installed.append(pip_name)
        else:
            print(f"❌ {pip_name} - Not found")
            to_install.append(pip_name)
    
    if not to_install:
        print("\n🎉 All packages already installed!")
        return True
    
    print(f"\n📥 Installing {len(to_install)} packages...")
    print("-" * 30)
    
    success_count = 0
    for package in to_install:
        print(f"⬇️ Installing {package}...")
        if install_package(package):
            print(f"✅ {package} installed successfully")
            success_count += 1
        else:
            print(f"❌ Failed to install {package}")
    
    print("-" * 30)
    print(f"📊 Installation complete: {success_count}/{len(to_install)} packages installed")
    
    if success_count == len(to_install):
        print("\n🎉 All multi-modal dependencies installed successfully!")
        print("✨ You can now run: python test_multimodal.py")
        return True
    else:
        print("\n⚠️ Some packages failed to install.")
        print("💡 Try running as administrator or check your internet connection.")
        return False

def check_environment():
    """Check environment setup."""
    print("\n🔧 Checking environment...")
    
    # Check Python version
    py_version = sys.version_info
    print(f"🐍 Python version: {py_version.major}.{py_version.minor}.{py_version.micro}")
    
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 8):
        print("⚠️ Warning: Python 3.8+ recommended for best compatibility")
    
    # Check GEMINI_API_KEY
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        print("✅ GEMINI_API_KEY found")
    else:
        print("⚠️ GEMINI_API_KEY not set")
        print("💡 Set it with: set GEMINI_API_KEY=your_api_key_here")
    
    # Check if in virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment detected")
    else:
        print("⚠️ Not in virtual environment (recommended but not required)")

def create_test_config():
    """Create a test configuration file."""
    config = {
        "multimodal_ai": {
            "enabled": True,
            "model": "gemini-1.5-pro",
            "screenshot_quality": "high",
            "analysis_detail_level": "medium",
            "cache_screenshots": True,
            "max_history": 50
        },
        "features": {
            "screen_monitoring": True,
            "visual_qa": True,
            "text_extraction": True,
            "ui_analysis": True,
            "image_generation": False
        }
    }
    
    try:
        import json
        with open("multimodal_config.json", "w") as f:
            json.dump(config, f, indent=2)
        print("✅ Configuration file created: multimodal_config.json")
    except Exception as e:
        print(f"⚠️ Could not create config file: {e}")

if __name__ == "__main__":
    print("🤖 YourDaddy Assistant - Multi-Modal AI Setup")
    print("Version 4.0 - Advanced Computer Vision Integration")
    print()
    
    # Check environment
    check_environment()
    
    # Install packages
    success = main()
    
    if success:
        # Create config
        create_test_config()
        
        print("\n" + "=" * 50)
        print("🎯 Next Steps:")
        print("1. Run: python test_multimodal.py")
        print("2. If tests pass, run: python yourdaddy_app.py")
        print("3. Try the new multi-modal features!")
        print("\n✨ New Features Available:")
        print("   • 🔍 Real-time screen analysis")
        print("   • 💬 Visual question answering")
        print("   • 📝 Smart text extraction")
        print("   • 👁️ Screen monitoring")
        print("   • 📷 AI-powered screenshots")
    
    input("\nPress Enter to exit...")