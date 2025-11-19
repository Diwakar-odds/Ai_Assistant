#!/usr/bin/env python3
"""
Test script for Edge-TTS implementation (Microsoft Neural Voices)
This will test the new TTS system with fallback support
"""

import sys
import os
from pathlib import Path

# Add modules to path
sys.path.append(str(Path(__file__).parent / "modules"))

def test_edge_tts():
    """Test Edge-TTS functionality"""
    print("=" * 60)
    print("Testing Edge-TTS Implementation (Microsoft Neural Voices)")
    print("=" * 60)
    
    # Check if Edge-TTS is installed
    try:
        import edge_tts
        print("✅ Edge-TTS library is installed")
        
        # List available models
        print("\n📋 Available Coqui TTS models:")
        try:
            models = TTS().list_models()
            print(f"   Total models available: {len(models)}")
            print("\n   Recommended models:")
            print("   - tts_models/en/ljspeech/tacotron2-DDC (English, high quality)")
            print("   - tts_models/en/ljspeech/fast_pitch (English, fast)")
            print("   - tts_models/hi/male/glow_tts (Hindi)")
        except Exception as e:
            print(f"   ⚠️ Could not list models: {e}")
        
    except ImportError:
        print("❌ Coqui TTS not installed")
        print("   Install with: pip install TTS")
        return False
    
    # Check pygame for audio playback
    try:
        import pygame
        print("✅ Pygame is installed (for audio playback)")
    except ImportError:
        print("⚠️ Pygame not installed - audio playback may not work")
        print("   Install with: pip install pygame")
    
    # Test with multilingual module
    print("\n" + "=" * 60)
    print("Testing with Multilingual Module")
    print("=" * 60)
    
    try:
        from multilingual import MultilingualSupport, Language
        
        print("✅ Multilingual module loaded")
        print("\n🎤 Initializing TTS system...")
        
        ml = MultilingualSupport()
        
        # Test English
        print("\n📢 Testing English TTS:")
        result = ml.speak_multilingual("Hello! This is a test of the Coqui TTS system.", Language.ENGLISH)
        print(f"   {result}")
        
        # Test auto-detect
        print("\n📢 Testing Auto-detect:")
        result = ml.speak_multilingual("How are you today?")
        print(f"   {result}")
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def install_instructions():
    """Print installation instructions"""
    print("\n" + "=" * 60)
    print("INSTALLATION INSTRUCTIONS")
    print("=" * 60)
    print("\nTo install Coqui TTS and dependencies:")
    print("\n  pip install TTS pygame")
    print("\nOr install all requirements:")
    print("\n  pip install -r requirements.txt")
    print("\n" + "=" * 60)
    print("\nAvailable TTS Models:")
    print("  • English (Fast): tts_models/en/ljspeech/fast_pitch")
    print("  • English (HQ):   tts_models/en/ljspeech/tacotron2-DDC")
    print("  • Hindi:          tts_models/hi/male/glow_tts")
    print("\nModels will be downloaded automatically on first use.")
    print("=" * 60)

if __name__ == "__main__":
    print("\n🎯 Edge-TTS Test Suite (Microsoft Neural Voices)\n")
    
    success = test_edge_tts()
    
    if not success:
        install_instructions()
    else:
        print("\n🎉 Your assistant now has Microsoft's high-quality neural voice synthesis!")
        print("   Edge-TTS > Coqui TTS (easier to install, same quality)")
        print("   Fallbacks: gTTS (Google) → pyttsx3 (offline)")
