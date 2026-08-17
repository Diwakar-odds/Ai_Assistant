# Python 3.11 Installation Guide

## ✅ Completed Steps:
1. ✅ Backed up old environment → `.venv_backup_20260114`
2. ✅ Created new virtual environment with Python 3.11.9
3. ✅ Updated `pyproject.toml` to require Python >=3.11
4. ✅ Resolved dependency conflicts

## 📦 Package Installation Strategy:

### Phase 1: Core Packages (INSTALLING NOW)
```bash
pip install -r requirements_core.txt
```

This includes:
- Flask web framework
- Google AI & Gemini
- OpenAI
- Autogen AI framework
- Basic ML (numpy, scikit-learn)
- Computer vision (opencv, pillow)
- Windows automation
- Voice & audio (except PyAudio)
- All essential dependencies

### Phase 2: Optional Heavy ML Packages
```bash
pip install -r requirements_optional.txt
```

This includes:
- TensorFlow 2.16+ (large download)
- PyTorch
- Transformers & sentence-transformers
- Vector databases (faiss, chromadb)
- Advanced voice processing

### Phase 3: Problem Packages (Install manually if needed)
```bash
# PyAudio (often fails - alternative: pip install sounddevice)
pip install PyAudio

# If PyAudio fails on Windows:
pip install pipwin
pipwin install pyaudio
```

## 🔧 Dependency Conflicts Resolved:

### Original Issues:
- ❌ TensorFlow 2.15.1 required protobuf <5.0.0
- ❌ Autogen required protobuf ~=5.29.3
- ❌ Conflict between packages

### Solutions Applied:
- ✅ Updated TensorFlow to 2.16+ (supports protobuf 5.x)
- ✅ Updated scikit-learn to 1.4+ (Python 3.11 compatible)
- ✅ Set protobuf to flexible range: >=5.26.1,<6.0
- ✅ Split requirements into core and optional

## 🚀 Testing Your Installation:

### Test Core Functionality:
```bash
python -c "import flask, google.generativeai, numpy, cv2, PIL; print('✅ Core packages OK')"
```

### Test Your Application:
```bash
python main.py
# or
python modern_web_backend.py
```

### Test Specific Features:
```bash
# Test Google AI
python -c "import google.generativeai as genai; print('✅ Gemini ready')"

# Test Voice
python -c "import speech_recognition, pyttsx3; print('✅ Voice ready')"

# Test Windows Automation
python -c "import pywinauto, pyautogui; print('✅ Automation ready')"
```

## 📊 Package Versions:

| Package | Old Version | New Version |
|---------|-------------|-------------|
| Python | 3.9.13 | 3.11.9 |
| TensorFlow | 2.15.1 | 2.16+ |
| scikit-learn | 1.3.0 | 1.4+ |
| protobuf | 5.29.5 (fixed) | 5.26.1-6.0 (flexible) |

## ⚠️ Known Issues & Workarounds:

### PyAudio Installation Fails:
```bash
# Use sounddevice as alternative:
pip install sounddevice

# Or on Windows:
pip install pipwin
pipwin install pyaudio
```

### TensorFlow Too Large:
TensorFlow is ~400MB. If you don't need ML features:
- Skip `requirements_optional.txt`
- Use Google Gemini API instead (already installed)

### Eventlet Compatibility:
Eventlet 0.33.3 may have issues with Python 3.11+. If you encounter problems:
```bash
pip install eventlet==0.35.0
```

## 🎯 Recommended Next Steps:

1. Wait for core installation to complete
2. Test your main application
3. Install optional packages only if needed
4. Remove backup if everything works: `rmdir /s /q .venv_backup_20260114`

## 🆘 If Something Goes Wrong:

### Restore Backup:
```bash
deactivate
rmdir /s /q .venv
move .venv_backup_20260114 .venv
.venv\Scripts\activate
```

### Start Fresh:
```bash
py -3.11 -m venv .venv_fresh
.venv_fresh\Scripts\activate
pip install -r requirements_core.txt
```
