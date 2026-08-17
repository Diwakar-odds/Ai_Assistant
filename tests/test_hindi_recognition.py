#!/usr/bin/env python3
"""
Test script to verify Hindi and Hinglish speech recognition improvements.
This script allows you to test voice recognition with different languages.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import speech_recognition as sr
from ai_assistant.voice.advanced_speech_recognizer import AdvancedSpeechRecognizer
from ai_assistant.multilingual import MultilingualSupport, Language

def test_recognition():
    """Interactive test for speech recognition"""
    print("=" * 60)
    print("Hindi & Hinglish Speech Recognition Test")
    print("=" * 60)
    print()
    
    # Initialize components
    print("Initializing recognition systems...")
    recognizer = sr.Recognizer()
    advanced_recognizer = AdvancedSpeechRecognizer(
        require_consent=False  # Skip consent for testing
    )
    multilingual = MultilingualSupport()
    
    print("✅ Systems initialized!\n")
    
    while True:
        print("\n" + "=" * 60)
        print("Select test mode:")
        print("1. Test Hindi recognition (हिंदी)")
        print("2. Test English recognition")
        print("3. Test Hinglish recognition (code-switching)")
        print("4. Test Auto-detect")
        print("5. Test Advanced Recognizer (Whisper API if available)")
        print("6. Exit")
        print("=" * 60)
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '6':
            print("\n👋 Goodbye!")
            break
        
        if choice in ['1', '2', '3', '4', '5']:
            # Map choice to language
            language_map = {
                '1': ('hi-IN', Language.HINDI, 'Hindi'),
                '2': ('en-IN', Language.ENGLISH, 'English'),
                '3': ('hi-IN', Language.HINGLISH, 'Hinglish'),
                '4': ('auto', Language.AUTO_DETECT, 'Auto-detect'),
                '5': ('auto', Language.AUTO_DETECT, 'Advanced (Whisper)')
            }
            
            google_lang, ml_lang, lang_name = language_map[choice]
            
            print(f"\n🎤 {lang_name} Mode")
            print("Listening... Speak now!")
            print("(Speak clearly for 3-5 seconds)")
            
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    print("🔴 Recording...")
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
                    print("✅ Recording complete! Processing...\n")
                
                # Test based on choice
                if choice == '5':
                    # Test advanced recognizer with Whisper
                    print("Testing Advanced Recognizer (Whisper API)...")
                    
                    # Save audio to temp file for Whisper
                    import tempfile
                    import wave
                    
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                        temp_file = f.name
                        with wave.open(temp_file, 'wb') as wav_file:
                            wav_file.setnchannels(1)
                            wav_file.setsampwidth(2)
                            wav_file.setframerate(16000)
                            wav_file.writeframes(audio.get_wav_data())
                    
                    try:
                        text, confidence, model = advanced_recognizer.recognize(
                            temp_file,
                            language=google_lang,
                            context=None
                        )
                        
                        if text:
                            print(f"✅ Recognized ({model}): {text}")
                            print(f"   Confidence: {confidence:.2%}")
                        else:
                            print("❌ Could not understand audio")
                    finally:
                        os.unlink(temp_file)
                
                else:
                    # Test multilingual support
                    print(f"Testing Multilingual Recognition ({lang_name})...")
                    
                    # First, try Google Speech Recognition directly
                    print(f"\n1️⃣ Google Speech ({google_lang}):")
                    try:
                        result = recognizer.recognize_google(audio, language=google_lang)
                        print(f"   Recognized: {result}")
                        
                        # Detect language of result
                        context = multilingual.detect_language(result)
                        print(f"   Detected: {context.detected_language.value}")
                        print(f"   Confidence: {context.confidence:.2%}")
                        print(f"   Hindi: {context.hindi_percentage:.1f}%, English: {context.english_percentage:.1f}%")
                    except sr.UnknownValueError:
                        print("   ❌ Could not understand")
                    except sr.RequestError as e:
                        print(f"   ❌ API Error: {e}")
                    
                    # If Hinglish mode, show dual recognition
                    if choice == '3':
                        print(f"\n2️⃣ Dual Recognition (Hindi + English):")
                        print("   Testing both hi-IN and en-IN simultaneously...")
                        
                        try:
                            # Create a mock audio source that returns our recorded audio
                            class MockAudioSource:
                                def __enter__(self):
                                    return self
                                def __exit__(self, *args):
                                    pass
                            
                            # We can't easily re-use the audio, so provide instructions
                            print("   ℹ️  For full dual-recognition test, integration is needed")
                            print("   ℹ️  Current implementation will use this in live system")
                        except Exception as e:
                            print(f"   ⚠️  {e}")
                
                print("\n" + "-" * 60)
                
            except sr.WaitTimeoutError:
                print("❌ Timeout - no speech detected")
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("❌ Invalid choice. Please select 1-6.")

def print_test_phrases():
    """Print example test phrases"""
    print("\n" + "=" * 60)
    print("Example Test Phrases")
    print("=" * 60)
    print("\n📝 Hindi:")
    print("  - अभी क्या समय है? (What time is it?)")
    print("  - मौसम कैसा है? (How's the weather?)")
    print("  - संगीत बजाओ (Play music)")
    
    print("\n📝 English:")
    print("  - What is the time?")
    print("  - How is the weather?")
    print("  - Play some music")
    
    print("\n📝 Hinglish:")
    print("  - Music play karo")
    print("  - Volume down kar do")
    print("  - Google me weather dhundo")
    print("  - Time kya hua hai?")
    print("  - WhatsApp open karo")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    print_test_phrases()
    
    print("\n⚙️  Configuration:")
    print("  - Whisper API: Will use if OpenAI API key is configured")
    print("  - Google Speech: Free, always available")
    print("  - Dual Recognition: Enabled for Hinglish")
    print()
    
    try:
        test_recognition()
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
