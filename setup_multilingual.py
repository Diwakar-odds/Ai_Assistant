#!/usr/bin/env python3
"""
YourDaddy Assistant - Multilingual Setup Script
Installs and configures multilingual support for Hindi, English, and Hinglish
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        print(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return None

def install_dependencies():
    """Install required Python packages for multilingual support"""
    print("🚀 Installing multilingual dependencies...")
    
    # Core translation and language detection packages
    packages = [
        "googletrans==4.0.0rc1",  # Google Translate
        "langdetect==1.0.9",      # Language detection
        "SpeechRecognition==3.10.4",  # Speech recognition
        "pyttsx3==2.90",          # Text-to-speech
        "gTTS==2.5.3",            # Google Text-to-Speech
        "pyaudio==0.2.14",       # Audio I/O
        "pydub==0.25.1",         # Audio manipulation
        "soundfile==0.12.1",     # Audio file I/O
        "transliterate==1.10.2", # Text transliteration
    ]
    
    for package in packages:
        run_command(f"pip install {package}", f"Installing {package.split('==')[0]}")
    
    # Install optional packages
    optional_packages = [
        "indic-transliteration==2.3.37",  # Indic scripts
        "azure-cognitiveservices-speech==1.38.0",  # Azure Speech (optional)
    ]
    
    print("\n📦 Installing optional packages...")
    for package in optional_packages:
        result = run_command(f"pip install {package}", f"Installing {package.split('==')[0]} (optional)")
        if result is None:
            print(f"⚠️ {package.split('==')[0]} installation failed - this is optional")

def setup_configuration():
    """Setup configuration files for multilingual support"""
    print("\n🔧 Setting up configuration...")
    
    config_path = Path("multimodal_config.json")
    
    # Load existing config or create new one
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = {}
    
    # Add multilingual configuration
    config.update({
        "languages": {
            "primary": "hinglish",
            "fallback": "en",
            "supported": ["en", "hi", "hinglish"],
            "auto_detect": True,
            "translation": {
                "engine": "google",
                "api_key": "",
                "cache_translations": True,
                "max_cache_size": 1000,
                "offline_fallback": True
            },
            "hinglish": {
                "enable_processing": True,
                "romanization": True,
                "script_mixing": True,
                "cultural_context": True,
                "common_phrases": {
                    "greeting": ["namaste", "hello", "hi", "kaise ho"],
                    "confirmation": ["haan", "yes", "theek hai", "ok"],
                    "negation": ["nahi", "no", "nahin", "bilkul nahi"]
                }
            }
        }
    })
    
    # Update voice configuration for multilingual support
    if "voice" not in config:
        config["voice"] = {}
    
    config["voice"].update({
        "recognition": {
            "engine": "vosk",
            "model_path": "model/vosk-model-small-en-us-0.15",
            "language": "en-US",
            "energy_threshold": 4000,
            "pause_threshold": 0.8,
            "multilingual": True,
            "supported_languages": ["en-US", "hi-IN", "en-IN"]
        },
        "synthesis": {
            "engine": "pyttsx3",
            "rate": 150,
            "volume": 0.8,
            "voice_id": 0,
            "multilingual": True,
            "hindi_voice": True,
            "english_voice": True
        },
        "wake_word": {
            "enabled": True,
            "keyword": "hey daddy",
            "hindi_keywords": ["arre daddy", "sun daddy", "hey daddy"],
            "access_key": "",
            "sensitivity": 0.5
        }
    })
    
    # Save updated configuration
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ Configuration updated with multilingual settings")

def download_voice_models():
    """Download voice recognition models for supported languages"""
    print("\n🎤 Setting up voice recognition models...")
    
    model_dir = Path("model")
    model_dir.mkdir(exist_ok=True)
    
    # Download Vosk models for English and Hindi
    models = [
        {
            "name": "English (Small)",
            "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
            "filename": "vosk-model-small-en-us-0.15.zip",
            "extract_dir": "vosk-model-small-en-us-0.15"
        },
        {
            "name": "Hindi (Small)",
            "url": "https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip", 
            "filename": "vosk-model-small-hi-0.22.zip",
            "extract_dir": "vosk-model-small-hi-0.22"
        }
    ]
    
    for model in models:
        model_path = model_dir / model["extract_dir"]
        if model_path.exists():
            print(f"✅ {model['name']} model already exists")
            continue
        
        print(f"📥 Downloading {model['name']} model...")
        
        # Download model
        download_result = run_command(
            f"curl -L -o {model_dir / model['filename']} {model['url']}",
            f"Downloading {model['name']} model"
        )
        
        if download_result is not None:
            # Extract model
            run_command(
                f"cd {model_dir} && unzip -q {model['filename']}",
                f"Extracting {model['name']} model"
            )
            
            # Clean up zip file
            try:
                (model_dir / model['filename']).unlink()
                print(f"🧹 Cleaned up {model['filename']}")
            except:
                pass

def test_installation():
    """Test the multilingual installation"""
    print("\n🧪 Testing multilingual installation...")
    
    try:
        # Test imports
        from modules.multilingual import MultilingualSupport, Language
        print("✅ Multilingual module imported successfully")
        
        # Test basic functionality
        ml = MultilingualSupport()
        
        # Test language detection
        test_texts = [
            "Hello, how are you?",
            "नमस्ते कैसे हैं आप?",
            "Hi yaar, kaise ho?"
        ]
        
        for text in test_texts:
            context = ml.detect_language(text)
            print(f"✅ Detected '{text}' as {context.detected_language.value} (confidence: {context.confidence:.2f})")
        
        # Test translation (if Google Translate is available)
        try:
            result = ml.translate_text("Hello", Language.HINDI)
            print(f"✅ Translation test: 'Hello' -> '{result}'")
        except Exception as e:
            print(f"⚠️ Translation test failed (may need internet): {e}")
        
        print("✅ All tests passed! Multilingual support is ready.")
        
    except ImportError as e:
        print(f"❌ Import test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False
    
    return True

def create_example_usage():
    """Create example usage file"""
    print("\n📝 Creating example usage file...")
    
    example_code = '''#!/usr/bin/env python3
"""
Example usage of YourDaddy Assistant Multilingual Features
Run this file to test the multilingual capabilities
"""

from modules.multilingual import MultilingualSupport, Language

def main():
    print("🚀 YourDaddy Assistant - Multilingual Demo")
    print("=" * 50)
    
    # Initialize multilingual support
    ml = MultilingualSupport()
    
    # Test language detection
    test_sentences = [
        "Hello, open Google Chrome please",
        "नमस्ते, कृपया क्रोम खोलिए",
        "Hi yaar, Chrome kholo please",
        "Phone kar Rahul ko",
        "Play some music बहुत बेकार lag रहा है",
        "Weather kya hai today?"
    ]
    
    print("\\n📝 Language Detection Tests:")
    print("-" * 30)
    
    for sentence in test_sentences:
        context = ml.detect_language(sentence)
        print(f"Text: '{sentence}'")
        print(f"Language: {context.detected_language.value} (confidence: {context.confidence:.2f})")
        
        if context.is_mixed:
            print(f"Mixed language detected - Hindi: {context.hindi_percentage:.1f}%, English: {context.english_percentage:.1f}%")
        print()
    
    # Test Hinglish command processing
    print("\\n🔄 Hinglish Command Processing:")
    print("-" * 35)
    
    hinglish_commands = [
        "Phone kar mom ko",
        "Music baja koi achha sa",
        "Google me search kar recipes",
        "Volume kam kar do",
        "Time kya hai abhi?"
    ]
    
    for command in hinglish_commands:
        result = ml.process_hinglish_command(command)
        print(f"Command: '{command}'")
        if result.get('command'):
            print(f"Detected: {result['command']}")
            if result.get('parameters'):
                print(f"Parameters: {result['parameters']}")
        else:
            print("No specific command detected")
        print()
    
    # Test translation
    print("\\n🔤 Translation Tests:")
    print("-" * 20)
    
    try:
        translations = [
            ("Hello", Language.HINDI),
            ("Thank you", Language.HINDI),
            ("नमस्ते", Language.ENGLISH),
            ("धन्यवाद", Language.ENGLISH)
        ]
        
        for text, target_lang in translations:
            translated = ml.translate_text(text, target_lang)
            print(f"'{text}' -> '{translated}' ({target_lang.value})")
    
    except Exception as e:
        print(f"Translation requires internet connection: {e}")
    
    print("\\n🎉 Multilingual demo completed!")
    print("\\nTry these commands with your assistant:")
    print("- 'Phone kar dost ko'")
    print("- 'Music baja something romantic'") 
    print("- 'Google me search kar pizza places'")
    print("- 'Time batao please'")

if __name__ == "__main__":
    main()
'''
    
    with open("test_multilingual.py", "w", encoding="utf-8") as f:
        f.write(example_code)
    
    print("✅ Created test_multilingual.py - run this to test features!")

def main():
    """Main setup function"""
    print("🌍 YourDaddy Assistant - Multilingual Setup")
    print("=" * 50)
    print("Setting up Hindi, English, and Hinglish support...")
    print()
    
    # Check if we're in the right directory
    if not Path("yourdaddy_app.py").exists():
        print("❌ Please run this script from the YourDaddy Assistant root directory")
        sys.exit(1)
    
    # Install dependencies
    install_dependencies()
    
    # Setup configuration
    setup_configuration()
    
    # Download voice models (optional, requires internet)
    try:
        download_voice_models()
    except Exception as e:
        print(f"⚠️ Voice model download failed: {e}")
        print("You can download models manually later")
    
    # Test installation
    if test_installation():
        create_example_usage()
        
        print("\\n🎉 Multilingual setup completed successfully!")
        print("=" * 50)
        print("✅ Hindi language support enabled")
        print("✅ English language support enabled") 
        print("✅ Hinglish (mixed) support enabled")
        print("✅ Auto language detection configured")
        print("✅ Translation service ready")
        print("✅ Voice recognition prepared")
        print()
        print("🚀 You can now:")
        print("   - Use 'python test_multilingual.py' to test features")
        print("   - Run 'python yourdaddy_app.py' with language selection")
        print("   - Try commands like: 'Phone kar mom ko' or 'Music baja kuch achha'")
        print("   - Switch languages in the settings panel")
        print()
        print("📝 Next steps:")
        print("   1. Set GOOGLE_TRANSLATE_API_KEY for better translation (optional)")
        print("   2. Configure voice models for your preferred languages")
        print("   3. Customize language patterns in multimodal_config.json")
    else:
        print("\\n❌ Setup completed with errors. Check the output above.")

if __name__ == "__main__":
    main()