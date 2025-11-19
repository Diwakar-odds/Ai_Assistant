# YourDaddy Assistant - Web UI README

## Overview

YourDaddy Assistant is a sophisticated AI-powered personal assistant that provides both traditional GUI and modern web interfaces for interacting with your computer through voice commands, natural language processing, and smart automation.

## Features

🎤 **Voice Recognition**
- Wake word detection ("Hey Daddy")
- Continuous speech recognition
- Text-to-speech responses

🤖 **AI Integration** 
- Multimodal AI with Google Gemini
- Natural language command processing
- Context-aware responses

🚀 **Application Management**
- Automatic application discovery
- Smart application launching
- Usage tracking and suggestions

🌐 **Modern Web Interface**
- Real-time WebSocket communication
- Responsive design
- Voice and text input
- System status monitoring

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Web Interface

**Windows:**
```cmd
start_web_ui.bat
```

**Linux/macOS:**
```bash
./start_web_ui.sh
```

**Manual:**
```bash
python modern_web_backend.py
```

### 3. Access Interface

Open your browser to: http://localhost:5000

## Web Interface Guide

### Voice Commands
1. Click the microphone button 🎤
2. Speak your command clearly
3. Wait for processing and response

### Text Commands
1. Type in the command input field
2. Press Enter or click Send ↗️
3. View response in the output area

### Quick Actions
Use the pre-defined action buttons for common tasks:
- **Discover Apps** - Find installed applications
- **System Status** - Check system performance
- **Weather** - Get weather information
- **News** - Latest headlines

## Available Commands

### Application Control
- `"open [application]"` - Launch applications
- `"close [application]"` - Close applications
- `"discover apps"` - Scan for installed apps

### Web & Search
- `"search [query]"` - Google search
- `"search youtube [query]"` - YouTube search
- `"weather"` - Weather information
- `"news"` - Latest news headlines

### System Control
- `"volume [0-100]"` - Set system volume
- `"system status"` - Performance metrics
- `"cleanup"` - Clean temporary files

### Notes & Memory
- `"note [text]"` - Save a note
- `"remember [information]"` - Save to memory
- `"recall [query]"` - Search memory

### Media Control
- `"play"` / `"pause"` - Media control
- `"next song"` / `"previous song"` - Track control
- `"play [song/artist]"` - Search and play

## Configuration

### Environment Variables
Create a `.env` file or set environment variables:

```env
GEMINI_API_KEY=your_gemini_api_key_here
PORCUPINE_ACCESS_KEY=your_porcupine_key_here
```

### Settings File
Modify `multimodal_config.json` for:
- Voice recognition settings
- AI model configuration  
- UI preferences
- Feature toggles

## Troubleshooting

### Voice Recognition Not Working
1. Check microphone permissions in browser
2. Ensure Vosk model is downloaded
3. Verify audio input device

### Backend Connection Issues
1. Check if Flask server is running
2. Verify port 5000 is available
3. Check firewall settings

### Application Discovery Problems
1. Run as administrator (Windows)
2. Check file permissions
3. Verify installed applications

## Architecture

### Frontend (React)
- `project/src/` - React components
- WebSocket client for real-time communication
- Voice recognition via Web Speech API
- Modern UI with glass-morphism design

### Backend (Flask)
- `modern_web_backend.py` - Main server
- Socket.IO for WebSocket communication
- API endpoints for all features
- Integration with automation tools

### Automation Layer
- `automation_tools_new.py` - Core automation functions
- `modules/` - Feature-specific modules
- Integration with system APIs

## Development

### Adding New Commands
1. Add command logic to `automation_tools_new.py`
2. Update command processing in `modern_web_backend.py`
3. Test via web interface

### Customizing UI
1. Modify React components in `project/src/`
2. Update styles in component files
3. Rebuild with `npm run build`

### API Extensions
1. Add new routes in `modern_web_backend.py`
2. Update Socket.IO handlers
3. Test with frontend integration

## Security Notes

- Run with appropriate permissions
- Secure API keys in environment variables
- Be cautious with system-level commands
- Review automation scripts before execution

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review log files (`yourdaddy.log`)
3. Test with simple commands first
4. Ensure all dependencies are installed

## Version Information

- **Current Version:** 3.0.0
- **Python:** 3.8+ required
- **Node.js:** 16+ required for development
- **Browser:** Chrome/Firefox recommended for voice features