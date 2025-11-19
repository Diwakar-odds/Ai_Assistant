#!/usr/bin/env python3
"""
YourDaddy Assistant Launcher
Professional startup script with comprehensive error handling and system checks
"""

import sys
import os
import traceback
from pathlib import Path
import subprocess
import platform
import time

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "modules"))
sys.path.insert(0, str(project_root / "utils"))

# Import utilities
try:
    from utils.logging_config import get_logger, setup_logging
    setup_logging()
    logger = get_logger(__name__)
except ImportError:
    # Fallback logging if advanced logging fails
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class SystemChecker:
    """Comprehensive system compatibility checker"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.python_version = sys.version_info
        
    def check_python_version(self):
        """Check Python version compatibility"""
        if self.python_version < (3, 8):
            self.errors.append(f"Python 3.8+ required, found {sys.version}")
            return False
        elif self.python_version < (3, 9):
            self.warnings.append("Python 3.9+ recommended for best performance")
        return True
    
    def check_dependencies(self):
        """Check critical dependencies"""
        critical_deps = [
            ('tkinter', 'GUI framework'),
            ('speech_recognition', 'Voice recognition'),
            ('edge_tts', 'Text-to-speech'),
            ('pygame', 'Audio playback'),
            ('requests', 'HTTP requests'),
        ]
        
        optional_deps = [
            ('pyaudio', 'Microphone access'),
            ('vosk', 'Offline voice recognition'),
            ('google.generativeai', 'Google AI'),
            ('openai', 'OpenAI integration'),
        ]
        
        missing_critical = []
        missing_optional = []
        
        for module, description in critical_deps:
            try:
                __import__(module)
                logger.info(f"✅ {description} available")
            except ImportError:
                missing_critical.append((module, description))
                logger.error(f"❌ {description} missing")
        
        for module, description in optional_deps:
            try:
                __import__(module)
                logger.info(f"✅ {description} available")
            except ImportError:
                missing_optional.append((module, description))
                logger.warning(f"⚠️ {description} optional (missing)")
        
        if missing_critical:
            self.errors.append(f"Missing critical dependencies: {', '.join([m[0] for m in missing_critical])}")
        
        if missing_optional:
            self.warnings.append(f"Missing optional features: {', '.join([m[0] for m in missing_optional])}")
        
        return len(missing_critical) == 0
    
    def check_models(self):
        """Check if AI models are available"""
        model_dir = project_root / "model"
        
        if not model_dir.exists():
            self.warnings.append("Voice models directory not found - offline voice recognition disabled")
            return False
        
        english_model = model_dir / "vosk-model-small-en-us-0.15"
        hindi_model = model_dir / "vosk-model-small-hi-0.22"
        
        if english_model.exists():
            logger.info("✅ English voice model found")
        else:
            self.warnings.append("English voice model missing - online recognition will be used")
        
        if hindi_model.exists():
            logger.info("✅ Hindi voice model found")
        else:
            self.warnings.append("Hindi voice model missing - limited multilingual support")
        
        return True
    
    def check_audio_system(self):
        """Check audio system compatibility"""
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            device_count = p.get_device_count()
            p.terminate()
            
            if device_count > 0:
                logger.info(f"✅ Audio system ready ({device_count} devices)")
                return True
            else:
                self.warnings.append("No audio devices found")
                return False
        except Exception as e:
            self.warnings.append(f"Audio system check failed: {e}")
            return False
    
    def check_config_files(self):
        """Check configuration files"""
        config_files = [
            ('multimodal_config.json', 'Main configuration'),
            ('requirements.txt', 'Dependencies list'),
        ]
        
        for file_name, description in config_files:
            file_path = project_root / file_name
            if file_path.exists():
                logger.info(f"✅ {description} found")
            else:
                self.warnings.append(f"{description} missing ({file_name})")
        
        return True
    
    def run_full_check(self):
        """Run complete system check"""
        logger.info("🔍 Running system compatibility check...")
        
        checks = [
            ("Python version", self.check_python_version),
            ("Dependencies", self.check_dependencies),
            ("AI models", self.check_models),
            ("Audio system", self.check_audio_system),
            ("Configuration", self.check_config_files),
        ]
        
        passed = 0
        total = len(checks)
        
        for check_name, check_func in checks:
            try:
                if check_func():
                    passed += 1
            except Exception as e:
                self.errors.append(f"{check_name} check failed: {e}")
                logger.error(f"❌ {check_name} check error: {e}")
        
        # Print summary
        print("\n" + "="*60)
        print("🤖 YourDaddy Assistant - System Check Results")
        print("="*60)
        
        if self.errors:
            print("\n❌ ERRORS (must fix):")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print("\n⚠️ WARNINGS (recommended fixes):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All systems operational!")
        elif not self.errors:
            print(f"\n✅ Core systems operational ({passed}/{total} checks passed)")
            print("   Some optional features may be limited.")
        else:
            print(f"\n❌ System check failed ({passed}/{total} checks passed)")
            return False
        
        print("="*60)
        return len(self.errors) == 0

def install_missing_dependencies():
    """Install missing critical dependencies"""
    logger.info("📦 Installing missing dependencies...")
    
    try:
        # Check if we have pip
        subprocess.check_call([sys.executable, "-m", "pip", "--version"])
        
        # Install from requirements.txt
        requirements_file = project_root / "requirements.txt"
        if requirements_file.exists():
            logger.info("Installing from requirements.txt...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
            ])
            return True
        else:
            # Install critical packages individually
            critical_packages = [
                "edge-tts>=6.1.12",
                "speech-recognition>=3.14.3",
                "pygame>=2.5.2",
                "requests>=2.32.0",
                "pyaudio>=0.2.14",
            ]
            
            for package in critical_packages:
                logger.info(f"Installing {package}...")
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", package
                ])
            
            return True
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False
    except Exception as e:
        logger.error(f"Installation error: {e}")
        return False

def download_voice_models():
    """Download required voice models"""
    logger.info("📥 Downloading voice models...")
    
    models = [
        {
            "name": "English (US)",
            "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
            "dir": "vosk-model-small-en-us-0.15"
        },
        {
            "name": "Hindi",
            "url": "https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip", 
            "dir": "vosk-model-small-hi-0.22"
        }
    ]
    
    model_dir = project_root / "model"
    model_dir.mkdir(exist_ok=True)
    
    for model in models:
        model_path = model_dir / model["dir"]
        if model_path.exists():
            logger.info(f"✅ {model['name']} model already exists")
            continue
        
        try:
            import requests
            import zipfile
            from io import BytesIO
            
            logger.info(f"Downloading {model['name']} model...")
            response = requests.get(model["url"], stream=True)
            response.raise_for_status()
            
            # Extract zip file
            with zipfile.ZipFile(BytesIO(response.content)) as zip_ref:
                zip_ref.extractall(model_dir)
            
            logger.info(f"✅ {model['name']} model installed")
            
        except Exception as e:
            logger.error(f"Failed to download {model['name']} model: {e}")

def start_assistant():
    """Start the YourDaddy Assistant"""
    logger.info("🚀 Starting YourDaddy Assistant...")
    
    try:
        # Import and start the assistant
        from yourdaddy_app import YourDaddyAssistant
        
        assistant = YourDaddyAssistant()
        
        logger.info("✅ Assistant initialized successfully")
        logger.info("🎉 YourDaddy Assistant is ready!")
        
        # Start the assistant
        assistant.run()
        
    except KeyboardInterrupt:
        logger.info("👋 Assistant stopped by user")
    except Exception as e:
        logger.error(f"❌ Assistant failed to start: {e}")
        traceback.print_exc()
        return False
    
    return True

def main():
    """Main launcher function"""
    print("🤖 YourDaddy Assistant v3.1 - Professional AI Assistant")
    print("=" * 60)
    
    # System check
    checker = SystemChecker()
    if not checker.run_full_check():
        print("\n🔧 Attempting to fix issues...")
        
        # Try to install missing dependencies
        if "Missing critical dependencies" in str(checker.errors):
            if install_missing_dependencies():
                print("✅ Dependencies installed successfully")
                # Re-run check
                checker = SystemChecker()
                if not checker.run_full_check():
                    print("❌ Still have issues after installation")
                    return False
            else:
                print("❌ Failed to install dependencies")
                return False
    
    # Download models if needed
    if any("voice model" in str(w) for w in checker.warnings):
        try:
            download_voice_models()
        except Exception as e:
            logger.warning(f"Failed to download models: {e}")
    
    # Start the assistant
    print("\n🚀 Launching YourDaddy Assistant...")
    return start_assistant()

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Launcher failed: {e}")
        traceback.print_exc()
        sys.exit(1)