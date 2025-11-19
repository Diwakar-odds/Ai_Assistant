# YourDaddy Assistant - Multilingual Support

🌍 **Full Hindi, English, and Hinglish Support for Your AI Assistant**

## Overview

YourDaddy Assistant now supports three languages seamlessly:
- **English**: Full English interface and commands
- **Hindi**: Pure Hindi interface with Devanagari script support  
- **Hinglish**: Natural mixing of Hindi and English (most popular!)

## Features

### 🗣️ Language Detection
- Automatic language detection from text and voice
- High-accuracy detection of mixed languages (Hinglish)
- Confidence scoring for language detection

### 🔄 Real-time Translation
- Google Translate integration
- Cached translations for better performance
- Bidirectional translation between all supported languages
- Smart handling of cultural context and common phrases

### 🎤 Voice Recognition
- Multi-language voice input
- Hindi voice commands with automatic transliteration
- English voice commands
- Hinglish voice commands (mixed Hindi-English)

### 🔊 Text-to-Speech
- Hindi TTS with proper pronunciation
- English TTS
- Language-aware voice selection
- Cultural context in speech output

### 🤖 Hinglish Command Processing
- Natural command understanding like "Phone kar mom ko"
- Mixed language patterns like "Music baja something nice"
- Cultural context awareness
- Smart parameter extraction from mixed languages

## Quick Setup

1. **Install dependencies:**
   ```bash
   python setup_multilingual.py
   ```

2. **Test the installation:**
   ```bash
   python test_multilingual.py
   ```

3. **Start the assistant:**
   ```bash
   python yourdaddy_app.py
   ```

## Supported Commands

### English Commands
- "Open Google Chrome"
- "Play some music"
- "Search for restaurants near me"
- "What's the weather like?"
- "Call John"

### Hindi Commands
- "गूगल क्रोम खोलिए"
- "कुछ संगीत बजाइए"
- "मेरे पास रेस्टोरेंट खोजिए"
- "मौसम कैसा है?"
- "जॉन को फोन करिए"

### Hinglish Commands (Most Natural!)
- "Phone kar mom ko"
- "Music baja kuch achha sa"
- "Google me search kar pizza places"
- "Volume kam kar do please"
- "Time kya hai abhi?"
- "Weather check kar do"
- "Chrome open kar do"

## Configuration

### Language Settings in `multimodal_config.json`:

```json
{
  "languages": {
    "primary": "hinglish",
    "fallback": "en",
    "supported": ["en", "hi", "hinglish"],
    "auto_detect": true,
    "translation": {
      "engine": "google",
      "cache_translations": true,
      "max_cache_size": 1000
    },
    "hinglish": {
      "enable_processing": true,
      "romanization": true,
      "script_mixing": true,
      "cultural_context": true
    }
  }
}
```

### Voice Configuration:

```json
{
  "voice": {
    "recognition": {
      "multilingual": true,
      "supported_languages": ["en-US", "hi-IN", "en-IN"]
    },
    "synthesis": {
      "multilingual": true,
      "hindi_voice": true,
      "english_voice": true
    }
  }
}
```

## Usage Examples

### 1. Language Detection
```python
from modules.multilingual import MultilingualSupport

ml = MultilingualSupport()
context = ml.detect_language("Phone kar mom ko")
print(f"Language: {context.detected_language}")  # Output: hinglish
```

### 2. Translation
```python
# English to Hindi
hindi_text = ml.translate_text("Hello", Language.HINDI)
print(hindi_text)  # Output: नमस्ते

# Hindi to English  
english_text = ml.translate_text("धन्यवाद", Language.ENGLISH)
print(english_text)  # Output: Thank you
```

### 3. Hinglish Command Processing
```python
result = ml.process_hinglish_command("Phone kar Rahul ko")
print(result)
# Output: {'command': 'make_call', 'parameters': {'contact': 'Rahul'}}
```

### 4. Voice Recognition
```python
import speech_recognition as sr

# Record audio
with sr.Microphone() as source:
    audio = sr.AudioData(...)

# Recognize in multiple languages
text, language = ml.recognize_speech_multilingual(audio, Language.AUTO_DETECT)
print(f"You said: '{text}' in {language}")
```

## GUI Integration

The desktop and web interfaces include:

### Language Selector
- Switch between English, Hindi, and Hinglish modes
- Real-time language preference saving
- Visual indicators for current language

### Translation Mode
- Toggle real-time translation
- Translate commands and responses on-the-fly
- Show original and translated text

### Voice Language Detection
- Automatic detection of spoken language
- Visual feedback for detected language
- Confidence indicators

## Web API Endpoints

### Language Detection
```http
POST /api/language/detect
Content-Type: application/json

{
  "text": "Phone kar mom ko"
}

Response:
{
  "detected_language": "hinglish",
  "confidence": 0.85,
  "is_mixed": true,
  "hindi_percentage": 60,
  "english_percentage": 40
}
```

### Translation
```http
POST /api/language/translate
Content-Type: application/json

{
  "text": "Phone kar mom ko",
  "target_language": "en"
}

Response:
{
  "translated_text": "Call mom",
  "source_language": "hinglish",
  "target_language": "en"
}
```

### Hinglish Processing
```http
POST /api/language/hinglish
Content-Type: application/json

{
  "text": "Phone kar mom ko"
}

Response:
{
  "command": "make_call",
  "parameters": {"contact": "mom"},
  "confidence": 0.9
}
```

## Common Hinglish Patterns

The assistant understands these natural patterns:

### Phone/Call Commands
- "Phone kar [name] ko"
- "Call kar do [name] ko"
- "[name] ko phone karna hai"

### Music Commands  
- "Music baja [song/artist]"
- "Gaana chala [name]"
- "Play kar do kuch [genre]"

### Search Commands
- "Google me search kar [query]"
- "[query] search kar do"
- "Find kar [item] ke bare me"

### System Commands
- "Volume kam/zyada kar do"
- "[app] open kar do"
- "Time kya hai?"
- "Weather check kar"

## Cultural Context

The multilingual system understands:

### Common Greetings
- "Namaste", "Hello", "Hi"
- "Kaise ho", "How are you"
- "Acha hai", "Theek hai", "All good"

### Polite Expressions
- "Please", "Kripaya"  
- "Thank you", "Dhanyawad"
- "Sorry", "Maaf karo"

### Time References
- "Abhi", "Right now"
- "Baad me", "Later"
- "Jaldi", "Quickly"

## Troubleshooting

### Translation Not Working
1. Check internet connection
2. Verify Google Translate API access
3. Check language codes in configuration

### Voice Recognition Issues
1. Ensure microphone permissions
2. Check audio quality
3. Verify language model installation

### Hinglish Commands Not Recognized
1. Use common patterns listed above
2. Check confidence threshold in settings
3. Review detected language in logs

## Performance Tips

1. **Enable Translation Cache**: Speeds up repeated translations
2. **Use Offline Models**: For voice recognition without internet
3. **Optimize Language Detection**: Adjust confidence thresholds
4. **Preload Common Phrases**: Configure in settings for faster recognition

## Contributing

To add support for more languages:

1. Add language patterns to `modules/multilingual.py`
2. Update configuration schema
3. Add UI labels and interface text
4. Test with native speakers

## Support

For issues with multilingual features:

1. Check logs in `yourdaddy.log`
2. Test with `python test_multilingual.py`
3. Verify configuration in `multimodal_config.json`
4. Check language model installation

---

**Happy Multilingual Assistant Usage! 🎉**

*Now you can talk to your assistant the way you naturally speak - mixing Hindi and English just like in real conversations!*