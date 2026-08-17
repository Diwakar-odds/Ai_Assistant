# 🎙️ Voice Feature Complete Setup Guide

## Overview

This guide will help you set up the complete voice system for YourDaddy AI Assistant from scratch. The voice system includes:

- **Text-to-Speech (TTS)**: Multiple engines (Edge-TTS, pyttsx3, gTTS)
- **Speech-to-Text (STT)**: Google Speech, Whisper API, Vosk offline
- **Wake Word Detection**: "Hey Daddy", "OK Daddy" activation
- **Voice Activity Detection (VAD)**: Smart speech detection
- **Neural Voice Engine**: High-quality natural voices
- **Voice API**: RESTful endpoints for all voice features

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Integration](#integration)
5. [Testing](#testing)
6. [Usage Examples](#usage-examples)
7. [Troubleshooting](#troubleshooting)
8. [API Reference](#api-reference)

---

## Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Windows 10/11 (Linux/Mac supported with modifications)
- **Microphone**: For speech recognition
- **Speakers**: For text-to-speech output
- **Internet**: Required for cloud-based engines (optional for offline mode)

### API Keys (Optional but Recommended)
- **OpenAI API Key**: For Whisper speech recognition
- **Google Cloud API Key**: For Google Speech-to-Text (optional)

---

## Installation

### Step 1: Install Core Voice Packages

```bash
# Navigate to project directory
cd f:\bn\assitant

# Install all voice dependencies
pip install edge-tts==6.1.12 SpeechRecognition==3.14.3 pyttsx3==2.99 gTTS==2.5.3 pygame soundfile librosa vosk pydub pyaudio
```

### Step 2: Install Optional Components

```bash
# For advanced features (optional)
pip install webrtcvad
pip install pvporcupine  # Wake word detection (requires license)
pip install openai  # For Whisper API
```

### Step 3: Download Offline Models (Optional)

For offline speech recognition using Vosk:

```bash
# Create models directory
mkdir -p model

# Download English model
# Visit: https://alphacephei.com/vosk/models
# Download: vosk-model-en-us-0.22.zip
# Extract to: model/vosk-model-en-us-0.22

# Download Hindi model (optional)
# Download: vosk-model-small-hi-0.22.zip
# Extract to: model/vosk-model-small-hi-0.22
```

---

## Configuration

### Voice Configuration File

The voice system is configured via `config/voice_config.json`:

```json
{
  "tts": {
    "default_engine": "edge_tts",
    "default_voice": "en-US-AriaNeural",
    "default_language": "en-US",
    "speed": 1.0,
    "volume": 0.9
  },
  "stt": {
    "default_engine": "whisper_api",
    "language": "en-US",
    "continuous": true,
    "noise_reduction": true
  },
  "wake_word": {
    "enabled": true,
    "phrases": ["hey daddy", "ok daddy"],
    "sensitivity": 0.5
  }
}
```

### Key Configuration Options

#### TTS Engines
- **edge_tts**: High-quality neural voices (recommended)
- **pyttsx3**: Offline system voices (fast, robotic)
- **gtts**: Google TTS (requires internet)

#### STT Engines
- **whisper_api**: OpenAI Whisper (most accurate, requires API key)
- **google_speech**: Google Cloud Speech (good accuracy)
- **vosk**: Offline recognition (good for privacy)

#### Available Voices

**English:**
- `en-US-AriaNeural` - Female (US)
- `en-US-GuyNeural` - Male (US)
- `en-GB-SoniaNeural` - Female (UK)

**Hindi:**
- `hi-IN-SwaraNeural` - Female
- `hi-IN-MadhurNeural` - Male

See full list: [Microsoft Edge TTS Voices](https://speech.microsoft.com/portal/voicegallery)

---

## Integration

### Step 1: Register Voice API Blueprint

Edit `ai_assistant/services/modern_web_backend.py`:

```python
# Import voice API
from ai_assistant.api.voice_api import voice_api

# Register blueprint (add after other blueprints)
app.register_blueprint(voice_api)

print("✅ Voice API registered at /api/voice/*")
```

### Step 2: Initialize Voice Service in Backend

Add to `modern_web_backend.py` initialization:

```python
# Initialize voice service
try:
    from ai_assistant.services.voice_service import get_voice_service
    voice_service = get_voice_service()
    print("✅ Voice service initialized")
except Exception as e:
    print(f"⚠️ Voice service initialization failed: {e}")
    voice_service = None
```

### Step 3: Add Voice WebSocket Events

Add these handlers to `modern_web_backend.py`:

```python
@socketio.on('voice_command')
def handle_voice_command(data):
    """Handle voice command from client"""
    try:
        text = data.get('text', '')
        if text:
            response = assistant.process_command(text)
            emit('voice_response', {
                'command': text,
                'response': response,
                'timestamp': datetime.now().isoformat()
            })
    except Exception as e:
        emit('voice_error', {'error': str(e)})

@socketio.on('start_listening')
def handle_start_listening():
    """Start voice listening"""
    try:
        if voice_service:
            voice_service.is_listening = True
            emit('listening_started', {'success': True})
    except Exception as e:
        emit('voice_error', {'error': str(e)})

@socketio.on('stop_listening')
def handle_stop_listening():
    """Stop voice listening"""
    try:
        if voice_service:
            voice_service.is_listening = False
            emit('listening_stopped', {'success': True})
    except Exception as e:
        emit('voice_error', {'error': str(e)})
```

---

## Testing

### Run Automated Tests

```bash
# Run complete voice test suite
python tests/test_voice_integration.py
```

Expected output:
```
🎙️  VOICE SYSTEM COMPREHENSIVE TEST SUITE
======================================================================

🧪 Test 1: Service Initialization
✅ Voice service initialized successfully

🧪 Test 2: Get Voice Status
📊 Status:
  - TTS Available: True
  - STT Available: True
  - Wake Word Available: True
✅ Status retrieved successfully

🧪 Test 3: Get Available Voices
📋 Available Voices (5):
  - Aria (US Female) (en-US-AriaNeural) - en-US
  - Guy (US Male) (en-US-GuyNeural) - en-US
✅ Found 5 voices

======================================================================
TEST SUMMARY
======================================================================
Tests run: 7
Successes: 7
Failures: 0
Errors: 0

✅ ALL TESTS PASSED!
```

### Manual Testing

#### Test TTS
```python
from ai_assistant.services.voice_service import get_voice_service

service = get_voice_service()
service.speak("Hello! The voice system is working perfectly.")
```

#### Test STT
```python
from ai_assistant.services.voice_service import get_voice_service

service = get_voice_service()
print("Listening... Please speak:")
text = service.listen(timeout=5)
print(f"You said: {text}")
```

#### Test API Endpoints

```bash
# Start the backend
python modern_web_backend.py

# In another terminal, test endpoints:

# Get voice status
curl http://localhost:5000/api/voice/status

# Get available voices
curl http://localhost:5000/api/voice/voices

# Get voice health
curl http://localhost:5000/api/voice/health
```

---

## Usage Examples

### Example 1: Simple Text-to-Speech

```python
from ai_assistant.services.voice_service import get_voice_service

# Get service
service = get_voice_service()

# Speak with default voice
service.speak("Hello, how can I help you today?")

# Speak with specific voice
service.speak("This is a male voice", voice="en-US-GuyNeural")
```

### Example 2: Speech Recognition

```python
from ai_assistant.services.voice_service import get_voice_service

service = get_voice_service()

# Listen for speech
print("Listening...")
text = service.listen(timeout=10)

if text:
    print(f"Recognized: {text}")
    # Process the command
    service.speak(f"You said: {text}")
```

### Example 3: Wake Word Detection

```python
from ai_assistant.services.voice_service import get_voice_service

service = get_voice_service()

def on_wake_word():
    print("Wake word detected!")
    service.speak("Yes, I'm listening")
    text = service.listen()
    if text:
        print(f"Command: {text}")

# Start detection
service.start_wake_word_detection(on_wake_word)

# Keep running
input("Press Enter to stop...")
service.stop_wake_word_detection()
```

### Example 4: Using the API

```javascript
// Frontend - Speak text
async function speakText(text) {
  const response = await fetch('/api/voice/speak', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ text })
  });
  const data = await response.json();
  console.log('Speech result:', data);
}

// Get available voices
async function getVoices() {
  const response = await fetch('/api/voice/voices');
  const data = await response.json();
  console.log('Available voices:', data.voices);
}

// Listen for speech
async function listenForSpeech() {
  const response = await fetch('/api/voice/listen', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ timeout: 10 })
  });
  const data = await response.json();
  console.log('Recognized:', data.text);
}
```

---

## Troubleshooting

### Common Issues

#### 1. "No module named 'pyaudio'"

**Solution:**
```bash
# Windows
pip install pipwin
pipwin install pyaudio

# Or download wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
pip install PyAudio‑0.2.14‑cp311‑cp311‑win_amd64.whl
```

#### 2. "Edge-TTS not working"

**Solution:**
```bash
# Reinstall edge-tts
pip uninstall edge-tts
pip install edge-tts==6.1.12

# Test
python -c "import edge_tts; print('OK')"
```

#### 3. "Microphone not detected"

**Solution:**
- Check microphone is connected and enabled in Windows settings
- Test with: `python -m speech_recognition`
- Grant microphone permissions to Python

#### 4. "Wake word not detecting"

**Solution:**
- Speak clearly and closer to microphone
- Adjust sensitivity in config (0.0-1.0)
- Check energy threshold setting
- Ensure background noise is minimal

#### 5. "Voice service not available"

**Solution:**
```bash
# Check if service initializes
python -c "from ai_assistant.services.voice_service import get_voice_service; print(get_voice_service().get_status())"

# Check logs
tail -f logs/voice/*.log
```

---

## API Reference

### REST Endpoints

#### GET `/api/voice/status`
Get voice system status

**Response:**
```json
{
  "success": true,
  "tts_available": true,
  "stt_available": true,
  "wake_word_available": true,
  "is_listening": false,
  "is_speaking": false
}
```

#### GET `/api/voice/voices`
Get available TTS voices

**Response:**
```json
{
  "success": true,
  "voices": [
    {
      "id": "en-US-AriaNeural",
      "name": "Aria (US Female)",
      "language": "en-US",
      "gender": "female"
    }
  ]
}
```

#### POST `/api/voice/speak`
Convert text to speech

**Request:**
```json
{
  "text": "Hello, world!",
  "voice": "en-US-AriaNeural",
  "speed": 1.0,
  "volume": 0.9
}
```

**Response:**
```json
{
  "success": true,
  "message": "Speech generated successfully"
}
```

#### POST `/api/voice/listen`
Listen for speech

**Request:**
```json
{
  "timeout": 10,
  "phrase_time_limit": 15
}
```

**Response:**
```json
{
  "success": true,
  "text": "recognized speech text",
  "timestamp": "2025-01-02T10:30:00"
}
```

#### GET `/api/voice/history`
Get voice command history

**Response:**
```json
{
  "success": true,
  "history": [
    {
      "text": "open chrome",
      "timestamp": "2025-01-02T10:30:00",
      "type": "recognized"
    }
  ]
}
```

### WebSocket Events

#### `voice_command`
Send voice command to server

**Emit:**
```javascript
socket.emit('voice_command', { text: 'open chrome' });
```

**Listen:**
```javascript
socket.on('voice_response', (data) => {
  console.log(data.response);
});
```

#### `start_listening`
Start voice listening

**Emit:**
```javascript
socket.emit('start_listening');
```

**Listen:**
```javascript
socket.on('listening_started', (data) => {
  console.log('Listening started');
});
```

---

## Advanced Configuration

### Custom Voice Settings

```json
{
  "tts": {
    "engines": {
      "edge_tts": {
        "enabled": true,
        "priority": 1,
        "voices": {
          "en-US": {
            "female": "en-US-AriaNeural",
            "male": "en-US-GuyNeural"
          }
        }
      }
    }
  }
}
```

### Noise Reduction Settings

```json
{
  "stt": {
    "noise_reduction": true,
    "energy_threshold": 4000,
    "dynamic_energy": true,
    "pause_threshold": 0.8
  }
}
```

### Wake Word Customization

```json
{
  "wake_word": {
    "enabled": true,
    "phrases": ["hey daddy", "ok daddy", "hey assistant"],
    "sensitivity": 0.5,
    "timeout": 5,
    "confirmation_beep": true
  }
}
```

---

## Performance Optimization

1. **Enable Caching**: Reduces TTS generation time
2. **Use Edge-TTS**: Fastest and highest quality
3. **Offline Mode**: Use Vosk for no internet dependency
4. **Adjust Thresholds**: Tune energy and pause thresholds
5. **GPU Acceleration**: Enable if available for faster processing

---

## Next Steps

1. ✅ Install all dependencies
2. ✅ Configure voice settings
3. ✅ Test TTS and STT
4. ✅ Integrate with web backend
5. ✅ Test API endpoints
6. 🔄 Customize for your use case
7. 🔄 Add custom wake words
8. 🔄 Train voice profiles

---

## Support

For issues or questions:
- Check logs in `logs/voice/`
- Review configuration in `config/voice_config.json`
- Run test suite: `python tests/test_voice_integration.py`
- Check documentation: `docs/`

---

**Setup Complete! 🎉**

Your voice system is now fully configured and ready to use!
