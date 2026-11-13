# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="tests")

#!/usr/bin/env python3
"""
Quick test script for voice recognition functionality.
Tests both Vosk (offline) and Google Speech Recognition (online).
"""

import sys
from pathlib import Path

# Add modules to path
sys.path.append(str(Path(__file__).parent / "modules"))

from multilingual import voice_listen_loop, MultilingualSupport, Language
import threading

def test_voice_callback(text):
    """Callback function for voice recognition"""
    if text.startswith('[WAKE_WORD_DETECTED'):
        print(f"\n{'='*50}")
        logger.info(f"✅ {text}")
        print(f"{'='*50}")
        print("Now speak your command...")
    else:
        print(f"\n🎯 You said: '{text}'")
        print(f"{'='*50}\n")

def test_vosk_models():
    """Test if Vosk models are available"""
    print("\n🔍 Checking Vosk models...")
    ml = MultilingualSupport()
    
    if hasattr(ml, 'vosk_models') and ml.vosk_models:
        logger.info(f"✅ Vosk models loaded: {list(ml.vosk_models.keys())}")
        return True
    else:
        logger.error("❌ No Vosk models found")
        return False

def main():
    print("="*60)
    print("🎤 Voice Recognition Test")
    print("="*60)
    
    # Test Vosk models
    vosk_available = test_vosk_models()
    
    print("\nOptions:")
    print("1. Test with Vosk (offline) - Recommended")
    print("2. Test with Google Speech Recognition (online)")
    print("3. Auto mode (tries Vosk first, falls back to Google)")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == '4':
        print("Goodbye!")
        return
    
    use_vosk = choice == '1' or (choice == '3' and vosk_available)
    
    # Wake words
    wake_words = ['hey daddy', 'ok daddy', 'arre daddy']
    
    print("\n" + "="*60)
    print(f"🎙️ Starting voice recognition...")
    print(f"   Engine: {'Vosk (offline)' if use_vosk else 'Google (online)'}")
    print(f"   Wake words: {', '.join(wake_words)}")
    print(f"   Language: Auto-detect (English/Hindi/Hinglish)")
    print("="*60)
    print("\n⏳ Initializing... Please wait...")
    print("\n📢 Say one of the wake words to start!")
    print("   Press Ctrl+C to stop\n")
    
    # Create stop event
    stop_event = threading.Event()
    
    try:
        # Start voice listening
        voice_listen_loop(
            callback_function=test_voice_callback,
            wake_words=wake_words,
            use_vosk=use_vosk,
            language='auto',
            stop_event=stop_event
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping voice recognition...")
        stop_event.set()
        logger.info("✅ Voice recognition stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
