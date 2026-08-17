#!/usr/bin/env python3
"""
Voice Listening Diagnostic Script
Tests and diagnoses voice recognition issues in the AI Assistant.
Checks for both Basic (Online) and Advanced (Offline) capabilities.
"""

import sys
import os
import importlib
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

print("=" * 70)
print("🔍 VOICE SYSTEM DIAGNOSTICS")
print("=" * 70)
print()

def check_library(name, import_name=None, description=""):
    if import_name is None:
        import_name = name
    
    print(f"Checking {name} ({description})...", end=" ")
    try:
        importlib.import_module(import_name)
        print("✅ INSTALLED")
        return True
    except ImportError:
        print("❌ NOT INSTALLED")
        return False

# 1. Basic Dependencies
print("1️⃣ Checking CORE Dependencies (Required for Basic Voice)...")
has_sr = check_library("SpeechRecognition", "speech_recognition", "Microphone Access")
has_pyaudio = check_library("PyAudio", "pyaudio", "Audio I/O")
has_numpy = check_library("Numpy", "numpy", "Audio Processing")
print("-" * 70)

# 2. Advanced Dependencies
print("2️⃣ Checking ADVANCED Dependencies (Required for Offline/Wake Word)...")
has_vosk = check_library("Vosk", "vosk", "Offline Recognition")
has_pocketsphinx = check_library("PocketSphinx", "pocketsphinx", "Wake Word Detection")
has_webrtc = check_library("WebRTCVAD", "webrtcvad", "Voice Activity Detection")
has_edgetts = check_library("Edge-TTS", "edge_tts", "Neural Text-to-Speech")
print("-" * 70)

# 3. Microphone Check
print("3️⃣ Testing Microphone Access...")
if has_sr and has_pyaudio:
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        mics = sr.Microphone.list_microphone_names()
        if not mics:
            print("❌ No microphones found!")
        else:
            print(f"✅ Found {len(mics)} microphones:")
            for i, mic_name in enumerate(mics):
                print(f"   [{i}] {mic_name}")
            
            # Simple energy check
            print("\n   Quick energy check (1s)...")
            try:
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=1)
                    print(f"   ✅ Energy threshold: {r.energy_threshold}")
            except Exception as e:
                print(f"   ❌ Failed to access microphone: {e}")
    except Exception as e:
        print(f"❌ Microphone check failed: {e}")
else:
    print("⚠️ Skipping microphone check (missing dependencies)")
print("-" * 70)

# 4. Fallback Status
print("4️⃣ System Status Report")
if has_vosk and has_pocketsphinx and has_webrtc:
    print("✅ FULL CAPABILITY: Offline Voice, Wake Word, and VAD are fully supported.")
elif has_vosk:
    print("⚠️ PARTIAL CAPABILITY: Offline Voice is supported via Vosk.")
    if not has_pocketsphinx:
        print("   ❌ Wake Word ('Hey Assistant') will NOT work (missing pocketsphinx).")
    if not has_webrtc:
        print("   ❌ Advanced VAD is disabled (using energy-based fallback).")
else:
    print("⚠️ BASIC MODE: Only Online Voice (Google) is supported. No offline capabilities.")

if not has_edgetts:
    print("⚠️ Text-to-Speech will use robotic fallback (pyttsx3) instead of Neural Voices.")

print("=" * 70)
