# 🤖 YourDaddy AI Assistant

<div align="center">

![Version](https://img.shields.io/badge/version-3.1-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-orange)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

**A sophisticated AI-powered personal assistant with voice recognition, smart automation, multilingual support, and modern interface capabilities.**

[Features](#-features) • [Installation](#-installation) • [Configuration](#-configuration) • [Usage](#-usage) • [Documentation](#-documentation)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Modules](#-modules)
- [API Integration](#-api-integration)
- [Documentation](#-documentation)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Overview

**YourDaddy AI Assistant** is a comprehensive, voice-activated AI assistant that combines the power of Google's Gemini AI, advanced speech recognition, and intelligent automation to create a seamless personal assistant experience. Built with Python, it offers multilingual support, multimodal capabilities (text, voice, vision), and extensive system integration.

### Key Highlights

- 🎤 **Voice Control**: Natural language processing with multilingual speech recognition
- 🧠 **AI-Powered**: Google Gemini 2.5 Pro integration for intelligent responses
- 🌍 **Multilingual**: Support for English, Hindi, and multiple Indian languages
- 👁️ **Vision Capabilities**: Image analysis, OCR, and visual understanding
- 🔄 **Smart Automation**: Task scheduling, file operations, and system control
- 🎵 **Media Integration**: Spotify and YouTube Music control
- 📧 **Communication**: Email management and calendar integration
- 🌐 **Web Interface**: Modern React-based UI with real-time updates
- 🔒 **Secure**: API key validation and secure credential management

---

## ✨ Features

### Core Capabilities

#### 🎙️ Voice & Speech
- **Multilingual Speech Recognition**: Vosk-based offline recognition for English and Hindi
- **Text-to-Speech**: Natural voice synthesis using pyttsx3 and gTTS
- **Voice Commands**: Wake word detection and continuous listening mode
- **Language Switching**: Dynamic language detection and switching

#### 🤖 AI & Intelligence
- **Conversational AI**: Context-aware conversations with memory
- **Learning System**: Pattern recognition and personalized responses
- **Knowledge Graphs**: Relationship mapping and intelligent associations
- **Enhanced Memory**: Long-term context retention and recall

#### 🖥️ System Integration
- **File Operations**: Create, move, copy, search files and folders
- **App Discovery**: Automatic detection and launching of installed applications
- **Taskbar Detection**: Real-time window and application monitoring
- **System Control**: Volume, brightness, power management

#### 📅 Productivity
- **Calendar Management**: Event creation, reminders, and scheduling
- **Email Automation**: Send, read, and manage emails
- **Task Scheduling**: APScheduler-based task automation
- **Document OCR**: Extract text from images and PDFs

#### 🎵 Media & Entertainment
- **Spotify Integration**: Control playback, playlists, and search
- **YouTube Music**: Search and play music videos
- **Web Scraping**: Extract data from websites intelligently

#### 🌐 Modern Interfaces
- **Web UI**: React + TypeScript + Vite frontend
- **REST API**: Flask-based backend with WebSocket support
- **Real-time Updates**: Live status and conversation streaming

#### 👁️ Multimodal Capabilities
- **Image Analysis**: Visual understanding using Gemini Vision
- **Video Processing**: Frame extraction and analysis
- **Screen Capture**: Screenshot analysis and OCR
- **Object Detection**: Identify objects and scenes in images

---

## 🏗️ Architecture

```
YourDaddy Assistant
├── Core Application (yourdaddy_app.py)
│   ├── Voice Recognition Engine
│   ├── AI Processing (Gemini)
│   └── Command Router
├── Modules (modules/)
│   ├── conversational_ai.py - AI chat and learning
│   ├── multilingual.py - Language support
│   ├── multimodal.py - Vision and media
│   ├── smart_automation.py - Task automation
│   ├── file_ops.py - File management
│   ├── system.py - System control
│   ├── music.py - Spotify/YouTube integration
│   ├── email.py - Email automation
│   ├── calendar.py - Calendar management
│   ├── document_ocr.py - OCR processing
│   └── [and more...]
├── Web Interface (modern_web_backend.py + project/)
│   ├── Backend API (Flask)
│   ├── Frontend (React + TypeScript)
│   └── WebSocket Communication
├── Configuration
│   ├── multimodal_config.json - Main config
│   ├── .env - API keys and secrets
│   └── config_validator.py - Config validation
└── Data Storage
    ├── SQLite Databases (memory, learning, etc.)
    └── Log Files
```

---

## 📦 Prerequisites

### System Requirements

- **Operating System**: Windows 10/11 (primary), Linux/macOS (experimental)
- **Python**: 3.8 or higher
- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: 2GB free space (for models and dependencies)
- **Microphone**: Required for voice input
- **Internet**: Required for AI API calls and some features

### Required Accounts & API Keys

1. **Google Gemini API** (Required)
   - Sign up at [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Get your API key for Gemini 2.5 Pro

2. **Spotify API** (Optional - for music features)
   - Create app at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Get Client ID and Client Secret

3. **Email Account** (Optional - for email features)
   - Gmail or other SMTP-compatible email
   - App-specific password recommended

---

## 🚀 Installation

### Step 1: Clone or Download

```bash
git clone <repository-url>
cd assitant
```

### Step 2: Create Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: If you encounter installation issues, see [Troubleshooting](#-troubleshooting).

### Step 4: Download Voice Models

```bash
# English model (required)
# Download from: https://alphacephei.com/vosk/models
# Extract to: model/vosk-model-small-en-us-0.15/

# Hindi model (optional)
# Extract to: model/vosk-model-small-hi-0.22/
```

### Step 5: Configure API Keys

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
# GEMINI_API_KEY=your_gemini_api_key_here
# SPOTIFY_CLIENT_ID=your_spotify_client_id
# SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```

### Step 6: Validate Configuration

```bash
python config_validator.py
```

---

## ⚙️ Configuration

### Main Configuration File: `multimodal_config.json`

```json
{
  "gemini": {
    "api_key": "",  // Leave empty, use .env instead
    "model": "gemini-2.5-pro",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "voice": {
    "recognition": {
      "engine": "vosk",
      "model_path": "model/vosk-model-small-en-us-0.15",
      "language": "en-US",
      "multilingual": true
    },
    "synthesis": {
      "engine": "pyttsx3",
      "rate": 175,
      "volume": 0.9,
      "voice_id": null
    }
  },
  "features": {
    "conversational_ai": true,
    "learning": true,
    "automation": true,
    "multimodal": true,
    "web_interface": true
  }
}
```

### Environment Variables: `.env`

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional - Spotify Integration
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

# Optional - Email Integration
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_specific_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Optional - Azure Speech (if using)
AZURE_SPEECH_KEY=your_azure_key
AZURE_SPEECH_REGION=your_region
```

---

## 🎯 Usage

### Running the Main Application

```bash
# Windows
start_app.bat

# Linux/Mac
./start_app.sh

# Or directly
python yourdaddy_app.py
```

### Running the Web Interface

```bash
# Windows
start_web_ui.bat

# Linux/Mac
./start_web_ui.sh

# Or directly
python modern_web_backend.py
```

Then open your browser to: `http://localhost:5000`

### Voice Commands Examples

```
"Hey assistant, what's the weather today?"
"Open Chrome"
"Play music on Spotify"
"Send an email to John"
"Create a file named test.txt"
"What's in this image?" [after providing image]
"Set a reminder for tomorrow at 3 PM"
"Search the web for Python tutorials"
"Switch to Hindi" / "हिंदी में बोलो"
```

### Using the Web Interface

1. **Chat Mode**: Type or speak commands in the chat interface
2. **Voice Mode**: Click the microphone button for voice input
3. **Image Analysis**: Upload images for AI analysis
4. **Settings**: Configure preferences and API keys
5. **Dashboard**: View system status and recent activities

---

## 🧩 Modules

### Core Modules

| Module | Description | Key Features |
|--------|-------------|--------------|
| `conversational_ai.py` | AI chat and learning | Context memory, pattern recognition, knowledge graphs |
| `multilingual.py` | Language support | Translation, transliteration, language detection |
| `multimodal.py` | Vision and media | Image analysis, OCR, video processing |
| `smart_automation.py` | Task automation | Scheduling, workflows, triggers |
| `file_ops.py` | File management | CRUD operations, search, organization |
| `system.py` | System control | Volume, brightness, power, processes |
| `music.py` | Media integration | Spotify, YouTube Music, local playback |
| `email.py` | Email automation | Send, receive, filter, attachments |
| `calendar.py` | Calendar management | Events, reminders, scheduling |
| `document_ocr.py` | OCR processing | Text extraction, PDF parsing |
| `web_scraping.py` | Web data extraction | Intelligent scraping, data parsing |
| `app_discovery.py` | Application detection | Auto-discover and launch apps |
| `taskbar_detection.py` | Window monitoring | Active app detection, window control |

### Integration Modules

- `easy_integrations.py` - Simple third-party integrations
- `advanced_integration.py` - Complex API integrations
- `universal_integration.py` - Universal app connector
- `modern_interfaces.py` - UI and display management
- `performance_optimization.py` - Speed and efficiency enhancements

---

## 🔌 API Integration

### REST API Endpoints

#### Authentication
```http
POST /api/validate-key
Content-Type: application/json

{
  "api_key": "your_gemini_key"
}
```

#### Chat
```http
POST /api/chat
Content-Type: application/json

{
  "message": "Hello assistant",
  "conversation_id": "optional_id"
}
```

#### Voice
```http
POST /api/voice/start
POST /api/voice/stop
GET /api/voice/status
```

#### Image Analysis
```http
POST /api/analyze-image
Content-Type: multipart/form-data

file: <image_file>
prompt: "What's in this image?"
```

### WebSocket Events

```javascript
// Connect
const ws = new WebSocket('ws://localhost:5000/socket.io');

// Listen for messages
ws.on('message', (data) => {
  console.log('Assistant:', data.message);
});

// Send message
ws.emit('chat_message', {
  message: 'Hello',
  conversation_id: 'abc123'
});
```

---

## 📚 Documentation

Additional documentation is available in the `docs/` folder:

- **[Quick Start Guide](QUICK_START_SECURED.md)** - Get started quickly
- **[Multilingual README](MULTILINGUAL_README.md)** - Language support details
- **[Web UI README](WEB_UI_README.md)** - Web interface guide
- **[Integration Methods](INTEGRATION_METHODS_GUIDE.md)** - API integration guide
- **[Spotify Integration](docs/SPOTIFY_INTEGRATION.md)** - Spotify setup
- **[YouTube Music Integration](docs/YOUTUBE_MUSIC_INTEGRATION.md)** - YouTube Music setup
- **[API Documentation](docs/API_DOCUMENTATION.md)** - Complete API reference
- **[Incomplete Modules Guide](docs/INCOMPLETE_MODULES_GUIDE.md)** - Work in progress

### Analysis Reports

Comprehensive analysis reports are available in `ANALYSIS_REPORTS/`:

- Executive Summary
- Critical Issues
- Security Analysis
- Performance Analysis
- Fix Roadmap
- And more...

---

## 🧪 Testing

### Run All Tests

```bash
# Run all unit tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_conversational_ai.py

# Run with coverage
python -m pytest --cov=modules tests/
```

### Available Tests

- `test_conversational_ai.py` - AI chat functionality
- `test_multilingual.py` - Language support
- `test_multimodal.py` - Vision capabilities
- `test_file_ops.py` - File operations
- `test_music.py` - Media integration
- `test_calendar.py` - Calendar features
- `test_document_ocr.py` - OCR processing
- And more in `tests/` folder

### Manual Testing

```bash
# Test multilingual support
python test_multilingual.py

# Test simple functionality
python simple_test.py

# Test model listing
python list_models.py

# Debug video processing
python debug_video.py
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. PyAudio Installation Fails

**Windows:**
```bash
pip install pipwin
pipwin install pyaudio
```

**Linux:**
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

#### 2. Vosk Model Not Found

- Download the model from [Vosk Models](https://alphacephei.com/vosk/models)
- Extract to `model/vosk-model-small-en-us-0.15/`
- Verify the path in `multimodal_config.json`

#### 3. API Key Invalid

```bash
# Validate your configuration
python config_validator.py

# Check .env file format (no quotes needed)
GEMINI_API_KEY=AIza...your_key_here
```

#### 4. Import Errors

```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Check Python version
python --version  # Should be 3.8+
```

#### 5. Web UI Won't Start

```bash
# Check if port 5000 is available
netstat -ano | findstr :5000

# Try a different port
python modern_web_backend.py --port 5001
```

#### 6. Microphone Not Working

- Check Windows privacy settings (Microphone access)
- Verify microphone in Windows Sound settings
- Test with: `python -m speech_recognition`

### Debug Mode

```bash
# Run with verbose logging
python yourdaddy_app.py --debug

# Check logs
cat logs/assistant.log
```

### Getting Help

1. Check the documentation in `docs/`
2. Review analysis reports in `ANALYSIS_REPORTS/`
3. Search existing issues
4. Create a new issue with:
   - Error message
   - Python version
   - OS version
   - Steps to reproduce

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Development Setup

```bash
# Fork and clone the repository
git clone <your-fork-url>
cd assitant

# Create a feature branch
git checkout -b feature/your-feature-name

# Make changes and test
python -m pytest tests/

# Commit and push
git add .
git commit -m "Add your feature"
git push origin feature/your-feature-name
```

### Code Style

- Follow PEP 8 guidelines
- Add docstrings to functions and classes
- Include type hints where appropriate
- Write unit tests for new features
- Update documentation

### Areas for Contribution

- 🐛 Bug fixes and improvements
- ✨ New features and integrations
- 📝 Documentation enhancements
- 🌍 Additional language support
- 🧪 More comprehensive tests
- 🎨 UI/UX improvements
- ⚡ Performance optimizations

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.

---

## 🙏 Acknowledgments

### Technologies & Libraries

- **Google Gemini AI** - Advanced AI capabilities
- **Vosk** - Offline speech recognition
- **Flask** - Web backend framework
- **React** - Frontend UI framework
- **Spotify API** - Music integration
- **pyttsx3** - Text-to-speech synthesis
- **scikit-learn** - Machine learning
- **And many more** - See `requirements.txt`

### Special Thanks

- Google AI team for Gemini API
- Vosk developers for offline speech recognition
- Open source community for amazing libraries

---

## 📊 Project Status

**Version**: 3.1  
**Status**: Active Development  
**Last Updated**: November 2025

### Recent Updates

- ✅ Enhanced multilingual support with Hindi
- ✅ Improved vision capabilities with Gemini 2.5 Pro
- ✅ Modern React-based web interface
- ✅ Better error handling and configuration validation
- ✅ Comprehensive testing suite
- ✅ Security improvements and API key management

### Roadmap

- 🔄 Mobile app support (Android/iOS)
- 🔄 Voice customization and cloning
- 🔄 More language support (Spanish, French, etc.)
- 🔄 Cloud synchronization
- 🔄 Plugin system for easy extensions
- 🔄 Docker containerization

---

## 📞 Contact & Support

For questions, suggestions, or support:

- 📧 Create an issue in the repository
- 📖 Check the documentation in `docs/`
- 🐛 Report bugs with detailed information
- 💡 Share feature requests and ideas

---

<div align="center">

**Made with ❤️ and Python**

⭐ Star this repository if you find it helpful!

[Back to Top](#-yourdaddy-ai-assistant)

</div>
