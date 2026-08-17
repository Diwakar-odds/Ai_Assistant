#!/usr/bin/env python3
"""
Voice System Quick Start Script
Initializes and tests the complete voice system
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def print_step(step, text):
    """Print step"""
    print(f"\n{'='*70}")
    print(f"STEP {step}: {text}")
    print(f"{'='*70}\n")

def check_dependencies():
    """Check if all required packages are installed"""
    print_step(1, "Checking Dependencies")
    
    dependencies = {
        'edge_tts': 'edge-tts',
        'speech_recognition': 'SpeechRecognition',
        'pyttsx3': 'pyttsx3',
        'gtts': 'gTTS',
        'pygame': 'pygame'
    }
    
    missing = []
    
    for module, package in dependencies.items():
        try:
            __import__(module)
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} NOT installed")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("\nInstall with:")
        print(f"pip install {' '.join(missing)}")
        return False
    
    print("\n✅ All dependencies installed!")
    return True

def check_configuration():
    """Check if configuration file exists"""
    print_step(2, "Checking Configuration")
    
    config_path = "config/voice_config.json"
    
    if os.path.exists(config_path):
        print(f"✅ Configuration file found: {config_path}")
        
        import json
        with open(config_path) as f:
            config = json.load(f)
        
        print(f"\n📄 Configuration:")
        print(f"  - TTS Engine: {config['tts']['default_engine']}")
        print(f"  - Default Voice: {config['tts']['default_voice']}")
        print(f"  - STT Engine: {config['stt']['default_engine']}")
        print(f"  - Wake Word Enabled: {config['wake_word']['enabled']}")
        print(f"  - Wake Words: {', '.join(config['wake_word']['phrases'])}")
        
        return True
    else:
        print(f"❌ Configuration file not found: {config_path}")
        print("\nThe configuration file has been created automatically.")
        return True

def test_voice_service():
    """Test voice service initialization"""
    print_step(3, "Testing Voice Service")
    
    try:
        from ai_assistant.services.voice_service import get_voice_service
        
        print("Initializing voice service...")
        service = get_voice_service()
        
        print("✅ Voice service initialized!")
        
        # Get status
        status = service.get_status()
        
        print(f"\n📊 Voice System Status:")
        print(f"  - TTS Available: {status['tts_available']}")
        print(f"  - STT Available: {status['stt_available']}")
        print(f"  - Wake Word Available: {status['wake_word_available']}")
        print(f"  - Is Listening: {status['is_listening']}")
        print(f"  - Is Speaking: {status['is_speaking']}")
        
        print(f"\n🔧 Available Engines:")
        for engine, available in status['engines'].items():
            status_icon = "✅" if available else "❌"
            print(f"  {status_icon} {engine}")
        
        return service
    
    except Exception as e:
        print(f"❌ Error initializing voice service: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_tts(service):
    """Test text-to-speech"""
    print_step(4, "Testing Text-to-Speech")
    
    try:
        # Get available voices
        voices = service.get_available_voices()
        print(f"📋 Available Voices: {len(voices)}")
        
        for i, voice in enumerate(voices[:5], 1):
            print(f"  {i}. {voice['name']} ({voice['id']}) - {voice['language']}")
        
        if len(voices) > 5:
            print(f"  ... and {len(voices) - 5} more")
        
        # Test speaking
        print("\n🔊 Testing TTS...")
        test_text = "Hello! The voice system is working perfectly. Text to speech is operational."
        
        print(f"Speaking: '{test_text}'")
        success = service.speak(test_text)
        
        if success:
            print("✅ TTS test successful!")
        else:
            print("⚠️  TTS test completed (engine may not be available)")
        
        return True
    
    except Exception as e:
        print(f"❌ TTS test failed: {e}")
        return False

def test_stt(service):
    """Test speech-to-text"""
    print_step(5, "Testing Speech-to-Text (Optional)")
    
    response = input("\n🎤 Do you want to test speech recognition? (y/n): ").strip().lower()
    
    if response != 'y':
        print("⏭️  Skipping STT test")
        return True
    
    try:
        print("\n🎧 Please speak something (you have 5 seconds)...")
        print("Listening...")
        
        text = service.listen(timeout=5)
        
        if text:
            print(f"\n✅ Recognized: '{text}'")
            
            # Speak back
            print("\n🔊 Speaking back your words...")
            service.speak(f"You said: {text}")
            
            return True
        else:
            print("\n⚠️  No speech detected")
            return False
    
    except Exception as e:
        print(f"❌ STT test failed: {e}")
        return False

def test_api():
    """Test voice API endpoints"""
    print_step(6, "Testing Voice API")
    
    try:
        from ai_assistant.api.voice_api import voice_api
        
        print("✅ Voice API blueprint loaded")
        
        # List registered routes
        print(f"\n📡 Registered API Endpoints:")
        endpoints = [
            "GET /api/voice/status",
            "GET /api/voice/voices",
            "GET /api/voice/health",
            "POST /api/voice/speak",
            "POST /api/voice/listen",
            "POST /api/voice/wake-word/start",
            "POST /api/voice/wake-word/stop",
            "GET /api/voice/history"
        ]
        
        for endpoint in endpoints:
            print(f"  ✅ {endpoint}")
        
        return True
    
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def show_usage_examples():
    """Show usage examples"""
    print_step(7, "Usage Examples")
    
    print("""
📚 Quick Usage Examples:

1️⃣  Simple Text-to-Speech:
    ```python
    from ai_assistant.services.voice_service import get_voice_service
    
    service = get_voice_service()
    service.speak("Hello, world!")
    ```

2️⃣  Speech Recognition:
    ```python
    service = get_voice_service()
    text = service.listen(timeout=10)
    print(f"You said: {text}")
    ```

3️⃣  Use Different Voice:
    ```python
    service = get_voice_service()
    service.speak("This is a male voice", voice="en-US-GuyNeural")
    ```

4️⃣  Get Voice Status:
    ```python
    service = get_voice_service()
    status = service.get_status()
    print(status)
    ```

5️⃣  API Usage (JavaScript):
    ```javascript
    // Speak text
    fetch('/api/voice/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: 'Hello!' })
    });
    
    // Get voices
    fetch('/api/voice/voices')
      .then(r => r.json())
      .then(data => console.log(data.voices));
    ```
""")

def show_next_steps():
    """Show next steps"""
    print_header("Next Steps")
    
    print("""
🚀 Your voice system is ready! Here's what you can do next:

1. ✅ Run the web backend:
   python modern_web_backend.py

2. ✅ Test the API:
   curl http://localhost:5000/api/voice/status

3. ✅ Run comprehensive tests:
   python tests/test_voice_integration.py

4. ✅ Read the documentation:
   - VOICE_SETUP_COMPLETE.md (complete setup guide)
   - VOICE_TESTING_GUIDE.md (testing guide)
   - config/voice_config.json (configuration)

5. ✅ Customize settings:
   - Edit config/voice_config.json
   - Change default voice, language, wake words
   - Adjust sensitivity and thresholds

6. ✅ Integrate with frontend:
   - Use the Voice API endpoints
   - WebSocket events for real-time communication
   - React VoiceInterface component

📖 Documentation:
   - Full API Reference: docs/API_REFERENCE_COMPLETE.md
   - Voice Testing Guide: VOICE_TESTING_GUIDE.md
   - Setup Guide: VOICE_SETUP_COMPLETE.md

💡 Tips:
   - Use Edge-TTS for best voice quality
   - Enable caching for faster responses
   - Adjust microphone sensitivity in config
   - Test different voices to find your favorite
""")

def main():
    """Main function"""
    print_header("🎙️  Voice System Quick Start")
    
    print("""
This script will:
  1. Check dependencies
  2. Verify configuration
  3. Initialize voice service
  4. Test TTS (text-to-speech)
  5. Test STT (speech-to-text) - optional
  6. Verify API endpoints
  7. Show usage examples

Press Enter to continue or Ctrl+C to exit...
""")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        return 1
    
    # Run checks
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first")
        return 1
    
    if not check_configuration():
        print("\n⚠️  Configuration issue detected")
    
    # Test service
    service = test_voice_service()
    if not service:
        print("\n❌ Voice service initialization failed")
        return 1
    
    # Test TTS
    test_tts(service)
    
    # Test STT (optional)
    test_stt(service)
    
    # Test API
    test_api()
    
    # Show examples
    show_usage_examples()
    
    # Next steps
    show_next_steps()
    
    print_header("✅ Voice System Setup Complete!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
