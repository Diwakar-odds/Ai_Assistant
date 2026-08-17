# Complete Issue Resolution Guide

## 🔴 CRITICAL (Must Fix):

### 1. NumPy Compatibility Crisis
```bash
pip install "numpy<2.0"
```
**Why**: NumPy 2.x breaks TensorFlow/PyTorch modules

### 2. Startup Performance Regression (107s → target 30s)
**Status**: ✅ FIXED in semantic_cache.py
- Deferred sentence-transformers import
- Should reduce from 107s to ~35s

---

## 🟡 HIGH PRIORITY (Breaking Features):

### 3. Missing Dependencies for Core Features
```bash
# Voice Recognition (CRITICAL for voice features)
pip install SpeechRecognition pyaudio

# Voice Activity Detection
pip install webrtcvad

# Advanced Audio Processing
pip install librosa noisereduce soundfile

# PDF Support
pip install PyPDF2

# Data Visualization
pip install matplotlib
```

### 4. Missing Optional AI Features
```bash
# Local AI (optional)
pip install llama-cpp-python

# Advanced TTS (optional)
pip install TTS

# Persistent Cache (recommended)
pip install diskcache

# Computer Vision (optional)
pip install opencv-python
```

---

## 🟢 MEDIUM PRIORITY (Missing Modules):

### 5. Custom Module Imports
These need to be created or paths fixed:
- `auto_learning_router` - Learning router module
- `smart_memory_retrieval` - Smart memory module
- `ai_assistant.services.voice_websocket_handlers` - Voice WebSocket
- `learning_dashboard_api` - Dashboard API

**Action**: Either create these modules or disable their imports

---

## 🔵 LOW PRIORITY (Warnings):

### 6. Deprecated Libraries
- **google.generativeai** → Switch to `google.genai`
  ```bash
  pip install google-genai
  ```

### 7. TensorFlow/Keras Warnings
- Update tensorflow: `pip install --upgrade tensorflow`
- These are just warnings, not breaking

### 8. Missing Integration Services
```bash
# Google Services
pip install google-auth google-auth-oauthlib google-auth-httplib2
pip install google-api-python-client  # For Calendar/Gmail

# Video Download
pip install yt-dlp

# Task Scheduling
pip install schedule
```

### 9. Encryption (Security)
```bash
pip install cryptography pycryptodome
```

---

## 📋 Complete Installation Script

```bash
# Phase 1: Fix Critical Issues
pip install "numpy<2.0"

# Phase 2: Core Voice Features
pip install SpeechRecognition
pip install pyaudio  # May need: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

# Phase 3: Audio Processing
pip install webrtcvad librosa noisereduce soundfile

# Phase 4: Essential Features
pip install PyPDF2 matplotlib diskcache opencv-python

# Phase 5: Google Services
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# Phase 6: Optional Enhancements
pip install cryptography yt-dlp schedule
pip install google-genai  # Replace deprecated google.generativeai

# Phase 7: Advanced (Optional, Large Downloads)
pip install TTS llama-cpp-python
```

---

## 🎯 Expected Results After All Fixes:

| Metric | Current | After Fix |
|--------|---------|-----------|
| **Startup Time** | 107s | ~30-35s |
| **Sessions** | 1 ✅ | 1 ✅ |
| **Voice Recognition** | ❌ Broken | ✅ Working |
| **NumPy Errors** | ❌ Crash risk | ✅ Fixed |
| **Cache** | In-memory | ✅ Persistent |
| **Encryption** | ❌ None | ✅ Enabled |

---

## ⚡ Quick Fix (Minimum to Run):

```bash
pip install "numpy<2.0" SpeechRecognition
```

This fixes the crash and enables voice features.

---

## 🔍 Verification Commands:

```bash
# Test startup time
time python modern_web_backend.py

# Check NumPy version
python -c "import numpy; print(numpy.__version__)"

# Verify voice support
python -c "import speech_recognition; print('Voice OK')"
```
