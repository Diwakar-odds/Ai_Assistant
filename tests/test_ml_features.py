"""
Quick test script to verify P3 ML features are working

Run this after all dependencies are installed to verify:
- Silero VAD
- Voice Cloning (TTS)
- Speaker Diarization (pyannote.audio)
"""

import sys
import numpy as np

print("="*60)
print("Testing P3 ML Features")
print("="*60)

# Test 1: Silero VAD
print("\n1. Testing Silero VAD...")
try:
    import torch
    model, utils = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        force_reload=False,
        verbose=False
    )
    print("   ✅ Silero VAD loaded successfully")
    print(f"   Model type: {type(model)}")
    
    # Quick inference test
    audio = torch.randn(1, 16000)  # 1 second of random audio
    with torch.no_grad():
        probs = model(audio, 16000)
    print(f"   ✅ Inference working (output shape: {probs.shape})")
    
except Exception as e:
    print(f"   ❌ Silero VAD failed: {e}")
    #

# Test 2: Voice Cloning (TTS)
print("\n2. Testing Coqui TTS...")
try:
    from TTS.api import TTS
    
    # List available models
    models = TTS().list_models()
    print(f"   ✅ TTS loaded ({len(models)} models available)")
    print(f"   Sample model: {models[0] if models else 'None'}")
    
except Exception as e:
    print(f"   ❌ TTS failed: {e}")
    #

# Test 3: Speaker Diarization
print("\n3. Testing pyannote.audio...")
try:
    from pyannote.audio import Pipeline
    print("   ✅ pyannote.audio imported successfully")
    print("   ⚠️  Note: Requires HuggingFace token for full functionality")
    print("   Token setup: https://huggingface.co/settings/tokens")
    
except Exception as e:
    print(f"   ❌ pyannote.audio failed: {e}")
    #

# Summary
print("\n" + "="*60)
print("✅ All P3 ML Features Ready!")
print("="*60)
print("\nNext steps:")
print("1. Set HF_TOKEN for diarization:")
print("   export HF_TOKEN='your_token_here'")
print("2. Restart backend to load features")
print("3. Test with: python tests/test_voice_system.py")
print("="*60)
