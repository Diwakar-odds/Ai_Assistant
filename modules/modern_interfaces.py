"""
Modern Interface Options for YourDaddy Assistant

This module provides multiple interface options including:
- Web interface with REST API
- Mobile app backend
- Voice-only mode
- Modern UI alternatives
- Cross-device synchronization
- Remote access capabilities
"""

import os
import json
import time
import threading
import asyncio
import websockets
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import base64

# Web framework
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_socketio import SocketIO, emit, disconnect
from flask_cors import CORS

# Voice processing
import speech_recognition as sr
import pyttsx3

# QR code for mobile pairing
try:
    import qrcode
    from PIL import Image
    HAS_QR_SUPPORT = True
except ImportError:
    HAS_QR_SUPPORT = False

class InterfaceType(Enum):
    """Available interface types"""
    DESKTOP_GUI = "desktop_gui"
    WEB_INTERFACE = "web_interface"
    VOICE_ONLY = "voice_only"
    MOBILE_APP = "mobile_app"
    API_ONLY = "api_only"
    HEADLESS = "headless"

class VoiceMode(Enum):
    """Voice interaction modes"""
    ALWAYS_LISTENING = "always_listening"
    PUSH_TO_TALK = "push_to_talk"
    WAKE_WORD = "wake_word"
    VOICE_COMMANDS_ONLY = "voice_commands_only"

@dataclass
class InterfaceSession:
    """Represents an active interface session"""
    session_id: str
    interface_type: InterfaceType
    connected_at: datetime
    last_activity: datetime
    client_info: Dict[str, Any]
    is_active: bool = True

@dataclass
class VoiceSettings:
    """Voice interface settings"""
    mode: VoiceMode
    wake_word: str
    voice_speed: float
    voice_volume: float
    language: str
    auto_speak_responses: bool
    voice_feedback: bool

class WebInterface:
    """Web-based interface for YourDaddy Assistant"""
    
    def __init__(self, port: int = 5000, host: str = "0.0.0.0"):
        self.app = Flask(__name__)
        self.app.secret_key = os.urandom(24)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        CORS(self.app)
        
        self.port = port
        self.host = host
        self.is_running = False
        self.sessions = {}
        self.assistant_instance = None
        
        self.setup_routes()
        self.setup_socketio_events()
    
    def setup_routes(self):
        """Setup web routes"""
        
        @self.app.route('/')
        def index():
            return render_template_string(self.get_web_template())
        
        @self.app.route('/api/status')
        def api_status():
            return jsonify({
                "status": "active",
                "version": "4.0.0",
                "interface": "web",
                "timestamp": datetime.now().isoformat(),
                "sessions": len(self.sessions)
            })
        
        @self.app.route('/api/command', methods=['POST'])
        def api_command():
            data = request.get_json()
            command = data.get('command', '')
            session_id = data.get('session_id', 'web_api')
            
            if not command:
                return jsonify({"error": "No command provided"}), 400
            
            try:
                response = self.process_command(command, session_id)
                return jsonify({
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/history/<session_id>')
        def api_history(session_id):
            history = self.get_session_history(session_id)
            return jsonify({"history": history})
        
        @self.app.route('/api/system/status')
        def api_system_status():
            if self.assistant_instance and hasattr(self.assistant_instance, 'integration_manager'):
                status = self.assistant_instance.integration_manager.get_system_status()
                return jsonify(status)
            return jsonify({"error": "System integration not available"}), 503
        
        @self.app.route('/mobile')
        def mobile_interface():
            return render_template_string(self.get_mobile_template())
        
        @self.app.route('/voice')
        def voice_interface():
            return render_template_string(self.get_voice_template())
        
        @self.app.route('/api/pairing/qr')
        def get_pairing_qr():
            if not HAS_QR_SUPPORT:
                return jsonify({"error": "QR code support not available"}), 503
            
            pairing_data = {
                "server_url": f"http://{request.host}",
                "api_key": self.generate_api_key(),
                "timestamp": datetime.now().isoformat()
            }
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(json.dumps(pairing_data))
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            import io
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return jsonify({
                "qr_code": f"data:image/png;base64,{img_str}",
                "pairing_data": pairing_data
            })
    
    def setup_socketio_events(self):
        """Setup WebSocket events"""
        
        @self.socketio.on('connect')
        def handle_connect():
            session_id = request.sid
            self.sessions[session_id] = InterfaceSession(
                session_id=session_id,
                interface_type=InterfaceType.WEB_INTERFACE,
                connected_at=datetime.now(),
                last_activity=datetime.now(),
                client_info=request.headers.to_wsgi_list()
            )
            emit('connected', {"session_id": session_id, "status": "connected"})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            session_id = request.sid
            if session_id in self.sessions:
                self.sessions[session_id].is_active = False
        
        @self.socketio.on('command')
        def handle_command(data):
            session_id = request.sid
            command = data.get('message', '')
            
            if session_id in self.sessions:
                self.sessions[session_id].last_activity = datetime.now()
            
            try:
                response = self.process_command(command, session_id)
                emit('response', {
                    "message": response,
                    "timestamp": datetime.now().isoformat(),
                    "type": "assistant_response"
                })
            except Exception as e:
                emit('error', {"message": str(e)})
        
        @self.socketio.on('voice_data')
        def handle_voice_data(data):
            session_id = request.sid
            audio_data = data.get('audio_data', '')
            
            try:
                # Process voice data
                command = self.process_voice_data(audio_data)
                if command:
                    response = self.process_command(command, session_id)
                    emit('response', {
                        "message": response,
                        "command": command,
                        "timestamp": datetime.now().isoformat(),
                        "type": "voice_response"
                    })
            except Exception as e:
                emit('error', {"message": f"Voice processing error: {str(e)}"})
    
    def process_command(self, command: str, session_id: str) -> str:
        """Process a command and return response"""
        if self.assistant_instance:
            # Create a mock event object for the existing command processing
            class MockEvent:
                pass
            
            # Store the original input method and restore after processing
            original_input = self.assistant_instance.text_input.get() if hasattr(self.assistant_instance, 'text_input') else ""
            
            try:
                # Use the existing agent brain
                if hasattr(self.assistant_instance, 'agent_brain') and self.assistant_instance.agent_brain:
                    response = self.assistant_instance.agent_brain.run(command)
                    return response
                else:
                    return f"Processed command via web interface: {command}"
            except Exception as e:
                return f"Error processing command: {str(e)}"
        
        return f"Echo: {command} (Assistant not connected)"
    
    def process_voice_data(self, audio_data: str) -> str:
        """Process voice data and return recognized text"""
        try:
            # Decode base64 audio data
            audio_bytes = base64.b64decode(audio_data)
            
            # Use speech recognition
            recognizer = sr.Recognizer()
            
            # Convert audio data to AudioFile format
            import io
            import wave
            
            # This is a simplified version - in practice, you'd need proper audio format handling
            with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                audio = recognizer.record(source)
                command = recognizer.recognize_google(audio)
                return command
        except Exception as e:
            raise Exception(f"Voice recognition failed: {str(e)}")
    
    def generate_api_key(self) -> str:
        """Generate API key for mobile pairing"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def get_session_history(self, session_id: str) -> List[Dict]:
        """Get command history for a session"""
        # This would typically come from a database
        return [
            {
                "timestamp": datetime.now().isoformat(),
                "command": "example command",
                "response": "example response",
                "type": "command"
            }
        ]
    
    def get_web_template(self) -> str:
        """Get web interface HTML template"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YourDaddy Assistant - Web Interface</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a1a, #2d2d2d);
            color: #ffffff;
            height: 100vh;
            overflow: hidden;
        }
        .container { 
            display: flex; 
            height: 100vh; 
        }
        .sidebar {
            width: 300px;
            background: rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            background: linear-gradient(45deg, #00ff88, #00ccff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .chat-container {
            flex: 1;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            overflow-y: auto;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .message {
            margin-bottom: 15px;
            padding: 12px 16px;
            border-radius: 10px;
            max-width: 80%;
            word-wrap: break-word;
        }
        .user-message {
            background: linear-gradient(45deg, #007bff, #0056b3);
            margin-left: auto;
            text-align: right;
        }
        .assistant-message {
            background: rgba(0, 255, 136, 0.1);
            border: 1px solid rgba(0, 255, 136, 0.3);
        }
        .input-container {
            display: flex;
            gap: 10px;
        }
        #messageInput {
            flex: 1;
            padding: 15px;
            border: none;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            font-size: 16px;
            backdrop-filter: blur(10px);
        }
        #messageInput:focus {
            outline: none;
            box-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
        }
        .btn {
            padding: 15px 25px;
            border: none;
            border-radius: 10px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        .btn-send {
            background: linear-gradient(45deg, #00ff88, #00cc6a);
            color: #000;
        }
        .btn-voice {
            background: linear-gradient(45deg, #ff4757, #ff3742);
            color: #fff;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }
        .status-panel {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .status-item {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .features-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 20px;
        }
        .feature-btn {
            padding: 10px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            color: #fff;
            cursor: pointer;
            text-align: center;
            transition: all 0.3s ease;
        }
        .feature-btn:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        .voice-indicator {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #ff4757;
            display: inline-block;
            margin-left: 10px;
        }
        .voice-indicator.listening {
            background: #00ff88;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        @media (max-width: 768px) {
            .container { flex-direction: column; }
            .sidebar { width: 100%; height: auto; }
            .features-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <div class="status-panel">
                <h3>🔗 Connection Status</h3>
                <div class="status-item">
                    <span>Status:</span>
                    <span id="connectionStatus">Connecting...</span>
                </div>
                <div class="status-item">
                    <span>Session:</span>
                    <span id="sessionId">-</span>
                </div>
                <div class="status-item">
                    <span>Voice:</span>
                    <span>Ready <span class="voice-indicator" id="voiceIndicator"></span></span>
                </div>
            </div>
            
            <div class="status-panel">
                <h3>⚡ Quick Actions</h3>
                <div class="features-grid">
                    <div class="feature-btn" onclick="sendQuickCommand('What time is it?')">⏰ Time</div>
                    <div class="feature-btn" onclick="sendQuickCommand('Check system status')">💻 System</div>
                    <div class="feature-btn" onclick="sendQuickCommand('What is the weather?')">🌤️ Weather</div>
                    <div class="feature-btn" onclick="sendQuickCommand('Open notepad')">📝 Notepad</div>
                    <div class="feature-btn" onclick="sendQuickCommand('Show my skills')">🎯 Skills</div>
                    <div class="feature-btn" onclick="sendQuickCommand('System monitor')">📊 Monitor</div>
                </div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="header">
                <h1>🤖 YourDaddy Assistant</h1>
                <p>Web Interface v4.0 - Modern AI Assistant</p>
            </div>
            
            <div class="chat-container" id="chatContainer">
                <div class="message assistant-message">
                    <strong>🤖 Assistant:</strong> Hello! I'm your AI assistant. How can I help you today?
                </div>
            </div>
            
            <div class="input-container">
                <input type="text" id="messageInput" placeholder="Type your message or use voice..." 
                       onkeypress="handleKeyPress(event)">
                <button class="btn btn-send" onclick="sendMessage()">📤 Send</button>
                <button class="btn btn-voice" id="voiceBtn" onclick="toggleVoice()">🎤 Voice</button>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let isListening = false;
        let mediaRecorder;
        let audioChunks = [];

        // Socket event handlers
        socket.on('connected', (data) => {
            document.getElementById('connectionStatus').textContent = 'Connected';
            document.getElementById('sessionId').textContent = data.session_id.substring(0, 8) + '...';
        });

        socket.on('response', (data) => {
            addMessage('assistant', data.message);
            if (data.type === 'voice_response') {
                speakText(data.message);
            }
        });

        socket.on('error', (data) => {
            addMessage('assistant', '❌ Error: ' + data.message);
        });

        // Voice functions
        async function toggleVoice() {
            const voiceBtn = document.getElementById('voiceBtn');
            const voiceIndicator = document.getElementById('voiceIndicator');
            
            if (!isListening) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];

                    mediaRecorder.ondataavailable = (event) => {
                        audioChunks.push(event.data);
                    };

                    mediaRecorder.onstop = () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        const reader = new FileReader();
                        reader.onload = () => {
                            const audioData = reader.result.split(',')[1];
                            socket.emit('voice_data', { audio_data: audioData });
                        };
                        reader.readAsDataURL(audioBlob);
                    };

                    mediaRecorder.start();
                    isListening = true;
                    voiceBtn.textContent = '🛑 Stop';
                    voiceIndicator.classList.add('listening');
                } catch (err) {
                    alert('Microphone access denied or not available');
                }
            } else {
                mediaRecorder.stop();
                isListening = false;
                voiceBtn.textContent = '🎤 Voice';
                voiceIndicator.classList.remove('listening');
            }
        }

        function speakText(text) {
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = 0.9;
                utterance.pitch = 1;
                speechSynthesis.speak(utterance);
            }
        }

        // Message functions
        function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            if (message) {
                addMessage('user', message);
                socket.emit('command', { message: message });
                input.value = '';
            }
        }

        function sendQuickCommand(command) {
            addMessage('user', command);
            socket.emit('command', { message: command });
        }

        function addMessage(type, text) {
            const chatContainer = document.getElementById('chatContainer');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}-message`;
            
            const icon = type === 'user' ? '👤' : '🤖';
            const label = type === 'user' ? 'You' : 'Assistant';
            
            messageDiv.innerHTML = `<strong>${icon} ${label}:</strong> ${text}`;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }

        // Initialize
        document.getElementById('messageInput').focus();
    </script>
</body>
</html>
        """
    
    def get_mobile_template(self) -> str:
        """Get mobile interface HTML template"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YourDaddy Assistant - Mobile</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #ffffff;
            height: 100vh;
            overflow: hidden;
        }
        .mobile-container {
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .mobile-header {
            padding: 20px;
            text-align: center;
            background: rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(10px);
        }
        .mobile-header h1 {
            font-size: 1.5em;
            margin-bottom: 5px;
        }
        .mobile-chat {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            background: rgba(255, 255, 255, 0.1);
        }
        .mobile-message {
            margin-bottom: 10px;
            padding: 10px 15px;
            border-radius: 15px;
            max-width: 85%;
        }
        .mobile-user {
            background: #007bff;
            margin-left: auto;
            text-align: right;
        }
        .mobile-assistant {
            background: rgba(255, 255, 255, 0.2);
        }
        .mobile-input {
            padding: 15px;
            background: rgba(0, 0, 0, 0.3);
            display: flex;
            gap: 10px;
        }
        .mobile-input input {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 25px;
            background: rgba(255, 255, 255, 0.9);
            color: #000;
        }
        .mobile-btn {
            width: 50px;
            height: 50px;
            border: none;
            border-radius: 50%;
            background: #00ff88;
            color: #000;
            font-size: 20px;
            cursor: pointer;
        }
        .quick-actions {
            display: flex;
            justify-content: space-around;
            padding: 10px;
            background: rgba(0, 0, 0, 0.2);
        }
        .quick-btn {
            padding: 8px 12px;
            background: rgba(255, 255, 255, 0.2);
            border: none;
            border-radius: 15px;
            color: white;
            font-size: 12px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="mobile-container">
        <div class="mobile-header">
            <h1>🤖 YourDaddy AI</h1>
            <p>Mobile Assistant</p>
        </div>
        
        <div class="quick-actions">
            <button class="quick-btn" onclick="sendQuick('⏰ Time')">⏰</button>
            <button class="quick-btn" onclick="sendQuick('🌤️ Weather')">🌤️</button>
            <button class="quick-btn" onclick="sendQuick('💻 System')">💻</button>
            <button class="quick-btn" onclick="sendQuick('📝 Note')">📝</button>
        </div>
        
        <div class="mobile-chat" id="mobileChat">
            <div class="mobile-message mobile-assistant">
                🤖 Hi! I'm your mobile AI assistant. How can I help?
            </div>
        </div>
        
        <div class="mobile-input">
            <input type="text" id="mobileInput" placeholder="Type message..."
                   onkeypress="handleMobileKeyPress(event)">
            <button class="mobile-btn" onclick="sendMobileMessage()">📤</button>
            <button class="mobile-btn" id="mobileVoice" onclick="toggleMobileVoice()">🎤</button>
        </div>
    </div>

    <script>
        const mobileSocket = io();
        
        function sendMobileMessage() {
            const input = document.getElementById('mobileInput');
            const message = input.value.trim();
            if (message) {
                addMobileMessage('user', message);
                mobileSocket.emit('command', { message: message });
                input.value = '';
            }
        }
        
        function sendQuick(command) {
            addMobileMessage('user', command);
            mobileSocket.emit('command', { message: command });
        }
        
        function addMobileMessage(type, text) {
            const chat = document.getElementById('mobileChat');
            const div = document.createElement('div');
            div.className = `mobile-message mobile-${type}`;
            div.textContent = text;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }
        
        function handleMobileKeyPress(event) {
            if (event.key === 'Enter') {
                sendMobileMessage();
            }
        }
        
        function toggleMobileVoice() {
            // Mobile voice implementation
            const btn = document.getElementById('mobileVoice');
            btn.textContent = btn.textContent === '🎤' ? '🛑' : '🎤';
        }
        
        mobileSocket.on('response', (data) => {
            addMobileMessage('assistant', data.message);
        });
    </script>
</body>
</html>
        """
    
    def get_voice_template(self) -> str:
        """Get voice-only interface template"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YourDaddy Assistant - Voice Only</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: radial-gradient(circle, #2c3e50, #1a1a1a);
            color: #ffffff;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .voice-container {
            text-align: center;
            max-width: 600px;
            padding: 40px;
        }
        .voice-circle {
            width: 200px;
            height: 200px;
            border-radius: 50%;
            background: linear-gradient(45deg, #00ff88, #00ccff);
            margin: 0 auto 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 60px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .voice-circle:hover {
            transform: scale(1.05);
            box-shadow: 0 0 30px rgba(0, 255, 136, 0.5);
        }
        .voice-circle.listening {
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); box-shadow: 0 0 30px rgba(0, 255, 136, 0.5); }
            50% { transform: scale(1.1); box-shadow: 0 0 50px rgba(0, 255, 136, 0.8); }
            100% { transform: scale(1); box-shadow: 0 0 30px rgba(0, 255, 136, 0.5); }
        }
        .voice-status {
            font-size: 24px;
            margin-bottom: 20px;
            min-height: 60px;
        }
        .voice-instructions {
            font-size: 18px;
            opacity: 0.8;
            margin-bottom: 30px;
        }
        .voice-controls {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-top: 30px;
        }
        .voice-btn {
            padding: 12px 24px;
            border: none;
            border-radius: 25px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        .voice-btn:hover {
            background: rgba(255, 255, 255, 0.2);
        }
    </style>
</head>
<body>
    <div class="voice-container">
        <h1>🎤 Voice Assistant</h1>
        <div class="voice-status" id="voiceStatus">Click the microphone to start</div>
        
        <div class="voice-circle" id="voiceCircle" onclick="toggleVoiceOnly()">
            🎤
        </div>
        
        <div class="voice-instructions">
            Tap the microphone and speak naturally. Your assistant will respond with voice.
        </div>
        
        <div class="voice-controls">
            <button class="voice-btn" onclick="setVoiceMode('always')">Always Listen</button>
            <button class="voice-btn" onclick="setVoiceMode('push')">Push to Talk</button>
            <button class="voice-btn" onclick="setVoiceMode('wake')">Wake Word</button>
        </div>
    </div>

    <script>
        const voiceSocket = io();
        let voiceMode = 'push';
        let isVoiceListening = false;
        let voiceRecorder;
        let voiceChunks = [];

        function toggleVoiceOnly() {
            const circle = document.getElementById('voiceCircle');
            const status = document.getElementById('voiceStatus');
            
            if (!isVoiceListening) {
                startVoiceRecording();
                circle.classList.add('listening');
                circle.textContent = '🛑';
                status.textContent = 'Listening... Speak now';
                isVoiceListening = true;
            } else {
                stopVoiceRecording();
                circle.classList.remove('listening');
                circle.textContent = '🎤';
                status.textContent = 'Processing...';
                isVoiceListening = false;
            }
        }

        async function startVoiceRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                voiceRecorder = new MediaRecorder(stream);
                voiceChunks = [];

                voiceRecorder.ondataavailable = (event) => {
                    voiceChunks.push(event.data);
                };

                voiceRecorder.onstop = () => {
                    const audioBlob = new Blob(voiceChunks, { type: 'audio/wav' });
                    const reader = new FileReader();
                    reader.onload = () => {
                        const audioData = reader.result.split(',')[1];
                        voiceSocket.emit('voice_data', { audio_data: audioData });
                    };
                    reader.readAsDataURL(audioBlob);
                };

                voiceRecorder.start();
            } catch (err) {
                document.getElementById('voiceStatus').textContent = 'Microphone access denied';
            }
        }

        function stopVoiceRecording() {
            if (voiceRecorder) {
                voiceRecorder.stop();
            }
        }

        function setVoiceMode(mode) {
            voiceMode = mode;
            const status = document.getElementById('voiceStatus');
            
            switch(mode) {
                case 'always':
                    status.textContent = 'Always listening mode activated';
                    break;
                case 'push':
                    status.textContent = 'Push to talk mode activated';
                    break;
                case 'wake':
                    status.textContent = 'Wake word mode activated - say "Hey Daddy"';
                    break;
            }
        }

        function speakResponse(text) {
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = 0.9;
                utterance.pitch = 1;
                speechSynthesis.speak(utterance);
            }
        }

        voiceSocket.on('response', (data) => {
            document.getElementById('voiceStatus').textContent = data.message;
            speakResponse(data.message);
            
            setTimeout(() => {
                document.getElementById('voiceStatus').textContent = 'Ready for next command';
            }, 3000);
        });

        voiceSocket.on('error', (data) => {
            document.getElementById('voiceStatus').textContent = 'Error: ' + data.message;
        });
    </script>
</body>
</html>
        """
    
    def set_assistant_instance(self, assistant):
        """Connect to the main assistant instance"""
        self.assistant_instance = assistant
    
    def start_server(self):
        """Start the web server"""
        if not self.is_running:
            self.is_running = True
            print(f"🌐 Starting web interface on http://{self.host}:{self.port}")
            self.socketio.run(self.app, host=self.host, port=self.port, debug=False)
    
    def stop_server(self):
        """Stop the web server"""
        self.is_running = False

class VoiceOnlyInterface:
    """Voice-only interface mode"""
    
    def __init__(self, settings: VoiceSettings = None):
        self.settings = settings or VoiceSettings(
            mode=VoiceMode.WAKE_WORD,
            wake_word="hey daddy",
            voice_speed=0.9,
            voice_volume=0.8,
            language="en-US",
            auto_speak_responses=True,
            voice_feedback=True
        )
        
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.tts_engine = pyttsx3.init()
        self.is_listening = False
        self.assistant_instance = None
        
        self.setup_voice_engine()
    
    def setup_voice_engine(self):
        """Configure the voice engine"""
        self.tts_engine.setProperty('rate', int(self.settings.voice_speed * 200))
        self.tts_engine.setProperty('volume', self.settings.voice_volume)
        
        # Adjust for ambient noise
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
    
    def speak(self, text: str):
        """Speak text using TTS"""
        if self.settings.auto_speak_responses:
            print(f"🔊 Speaking: {text}")
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
    
    def listen_for_wake_word(self) -> bool:
        """Listen for wake word"""
        try:
            with self.microphone as source:
                print("👂 Listening for wake word...")
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
            
            command = self.recognizer.recognize_google(audio).lower()
            return self.settings.wake_word.lower() in command
        except (sr.WaitTimeoutError, sr.UnknownValueError, sr.RequestError):
            return False
    
    def listen_for_command(self) -> Optional[str]:
        """Listen for voice command"""
        try:
            with self.microphone as source:
                if self.settings.voice_feedback:
                    self.speak("I'm listening")
                
                print("🎤 Listening for command...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            command = self.recognizer.recognize_google(audio)
            print(f"👤 Heard: {command}")
            return command
        except sr.WaitTimeoutError:
            if self.settings.voice_feedback:
                self.speak("I didn't hear anything")
            return None
        except sr.UnknownValueError:
            if self.settings.voice_feedback:
                self.speak("I couldn't understand that")
            return None
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            return None
    
    def process_voice_command(self, command: str) -> str:
        """Process voice command and return response"""
        if self.assistant_instance:
            try:
                if hasattr(self.assistant_instance, 'agent_brain') and self.assistant_instance.agent_brain:
                    response = self.assistant_instance.agent_brain.run(command)
                    return response
                else:
                    return f"Voice command processed: {command}"
            except Exception as e:
                return f"Error processing command: {str(e)}"
        
        return "Voice assistant not connected"
    
    def start_voice_loop(self):
        """Start the voice-only interaction loop"""
        self.is_listening = True
        self.speak("Voice assistant activated")
        
        print("🎤 Voice-only mode started")
        print(f"Mode: {self.settings.mode.value}")
        print(f"Wake word: {self.settings.wake_word}")
        
        try:
            while self.is_listening:
                if self.settings.mode == VoiceMode.ALWAYS_LISTENING:
                    command = self.listen_for_command()
                    if command:
                        response = self.process_voice_command(command)
                        self.speak(response)
                
                elif self.settings.mode == VoiceMode.WAKE_WORD:
                    if self.listen_for_wake_word():
                        command = self.listen_for_command()
                        if command:
                            response = self.process_voice_command(command)
                            self.speak(response)
                
                elif self.settings.mode == VoiceMode.PUSH_TO_TALK:
                    print("Press Enter to talk, 'q' to quit...")
                    user_input = input()
                    if user_input.lower() == 'q':
                        break
                    
                    command = self.listen_for_command()
                    if command:
                        response = self.process_voice_command(command)
                        self.speak(response)
                
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        
        self.stop_voice_loop()
    
    def stop_voice_loop(self):
        """Stop the voice-only loop"""
        self.is_listening = False
        self.speak("Voice assistant deactivated")
        print("🎤 Voice-only mode stopped")
    
    def set_assistant_instance(self, assistant):
        """Connect to the main assistant instance"""
        self.assistant_instance = assistant

class MobileAppBackend:
    """Backend services for mobile app integration"""
    
    def __init__(self, port: int = 8080):
        self.app = Flask(__name__)
        self.app.secret_key = os.urandom(24)
        CORS(self.app)
        
        self.port = port
        self.registered_devices = {}
        self.push_tokens = {}
        self.assistant_instance = None
        
        self.setup_mobile_routes()
    
    def setup_mobile_routes(self):
        """Setup mobile-specific API routes"""
        
        @self.app.route('/mobile/api/register', methods=['POST'])
        def register_device():
            data = request.get_json()
            device_id = data.get('device_id')
            device_info = data.get('device_info', {})
            push_token = data.get('push_token')
            
            if not device_id:
                return jsonify({"error": "Device ID required"}), 400
            
            # Generate API key
            api_key = self.generate_mobile_api_key()
            
            self.registered_devices[device_id] = {
                "device_info": device_info,
                "api_key": api_key,
                "registered_at": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat()
            }
            
            if push_token:
                self.push_tokens[device_id] = push_token
            
            return jsonify({
                "status": "registered",
                "api_key": api_key,
                "device_id": device_id
            })
        
        @self.app.route('/mobile/api/command', methods=['POST'])
        def mobile_command():
            api_key = request.headers.get('Authorization')
            if not self.validate_mobile_api_key(api_key):
                return jsonify({"error": "Invalid API key"}), 401
            
            data = request.get_json()
            command = data.get('command', '')
            device_id = data.get('device_id')
            
            if device_id in self.registered_devices:
                self.registered_devices[device_id]["last_seen"] = datetime.now().isoformat()
            
            try:
                response = self.process_mobile_command(command, device_id)
                return jsonify({
                    "response": response,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/mobile/api/sync', methods=['POST'])
        def sync_data():
            api_key = request.headers.get('Authorization')
            if not self.validate_mobile_api_key(api_key):
                return jsonify({"error": "Invalid API key"}), 401
            
            # Sync assistant data with mobile device
            sync_data = {
                "skills": self.get_skills_data(),
                "recent_conversations": self.get_recent_conversations(),
                "system_status": self.get_system_status(),
                "quick_actions": self.get_quick_actions()
            }
            
            return jsonify(sync_data)
        
        @self.app.route('/mobile/api/push/send', methods=['POST'])
        def send_push_notification():
            data = request.get_json()
            device_id = data.get('device_id')
            message = data.get('message', '')
            title = data.get('title', 'YourDaddy Assistant')
            
            if device_id in self.push_tokens:
                # In a real implementation, this would send to FCM/APNS
                print(f"📱 Push to {device_id}: {title} - {message}")
                return jsonify({"status": "sent"})
            
            return jsonify({"error": "Device not found"}), 404
    
    def generate_mobile_api_key(self) -> str:
        """Generate API key for mobile device"""
        import secrets
        return f"mobile_{secrets.token_urlsafe(24)}"
    
    def validate_mobile_api_key(self, api_key: str) -> bool:
        """Validate mobile API key"""
        if not api_key:
            return False
        
        for device_id, device_data in self.registered_devices.items():
            if device_data.get("api_key") == api_key:
                return True
        
        return False
    
    def process_mobile_command(self, command: str, device_id: str) -> str:
        """Process command from mobile device"""
        if self.assistant_instance:
            try:
                if hasattr(self.assistant_instance, 'agent_brain') and self.assistant_instance.agent_brain:
                    # Add mobile context
                    mobile_context = f"\n[Mobile device: {device_id}]"
                    response = self.assistant_instance.agent_brain.run(command + mobile_context)
                    return response
                else:
                    return f"Mobile command processed: {command}"
            except Exception as e:
                return f"Error processing mobile command: {str(e)}"
        
        return "Assistant not connected"
    
    def get_skills_data(self) -> Dict:
        """Get skills data for mobile sync"""
        if (self.assistant_instance and 
            hasattr(self.assistant_instance, 'learning_system') and 
            self.assistant_instance.learning_system):
            skills = self.assistant_instance.learning_system.skill_manager.get_skills_by_category()
            return {
                "total_skills": len(skills),
                "skills": [
                    {
                        "name": skill.name,
                        "category": skill.category,
                        "proficiency": skill.proficiency,
                        "usage_count": skill.usage_count
                    } for skill in skills[:10]  # Top 10 skills
                ]
            }
        return {"total_skills": 0, "skills": []}
    
    def get_recent_conversations(self) -> List:
        """Get recent conversations for mobile sync"""
        # This would come from conversation history
        return [
            {
                "timestamp": datetime.now().isoformat(),
                "command": "example command",
                "response": "example response"
            }
        ]
    
    def get_system_status(self) -> Dict:
        """Get system status for mobile display"""
        if (self.assistant_instance and 
            hasattr(self.assistant_instance, 'integration_manager') and 
            self.assistant_instance.integration_manager):
            try:
                status = self.assistant_instance.integration_manager.get_system_status()
                return {
                    "platform": status.get("platform", "unknown"),
                    "cpu_usage": status.get("hardware", {}).get("cpu", {}).get("usage_percent", 0),
                    "memory_usage": status.get("hardware", {}).get("memory", {}).get("percentage", 0),
                    "active_processes": len(status.get("processes", []))
                }
            except Exception:
                pass
        
        return {"platform": "unknown", "cpu_usage": 0, "memory_usage": 0, "active_processes": 0}
    
    def get_quick_actions(self) -> List:
        """Get quick actions for mobile interface"""
        return [
            {"id": "time", "label": "Current Time", "icon": "⏰", "command": "What time is it?"},
            {"id": "weather", "label": "Weather", "icon": "🌤️", "command": "What's the weather like?"},
            {"id": "system", "label": "System Status", "icon": "💻", "command": "Check system status"},
            {"id": "notes", "label": "Take Note", "icon": "📝", "command": "Create a new note"},
            {"id": "music", "label": "Play Music", "icon": "🎵", "command": "Play some music"},
            {"id": "skills", "label": "My Skills", "icon": "🎯", "command": "Show my skills"}
        ]
    
    def set_assistant_instance(self, assistant):
        """Connect to the main assistant instance"""
        self.assistant_instance = assistant
    
    def start_mobile_server(self):
        """Start the mobile backend server"""
        print(f"📱 Starting mobile backend on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False)

class ModernInterfaceManager:
    """Main manager for all modern interface options"""
    
    def __init__(self, db_path: str = "modern_interfaces.db"):
        self.db_path = db_path
        self.active_interfaces = {}
        self.sessions = {}
        self.assistant_instance = None
        
        # Initialize interface components
        self.web_interface = WebInterface()
        self.voice_interface = VoiceOnlyInterface()
        self.mobile_backend = MobileAppBackend()
        
        self.init_database()
    
    def init_database(self):
        """Initialize interfaces database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interface_sessions (
                session_id TEXT PRIMARY KEY,
                interface_type TEXT NOT NULL,
                connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                client_info TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interface_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interface_type TEXT NOT NULL,
                session_duration INTEGER,
                commands_processed INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def set_assistant_instance(self, assistant):
        """Connect all interfaces to the main assistant instance"""
        self.assistant_instance = assistant
        self.web_interface.set_assistant_instance(assistant)
        self.voice_interface.set_assistant_instance(assistant)
        self.mobile_backend.set_assistant_instance(assistant)
    
    def start_interface(self, interface_type: InterfaceType, **kwargs):
        """Start a specific interface"""
        if interface_type == InterfaceType.WEB_INTERFACE:
            thread = threading.Thread(target=self.web_interface.start_server, daemon=True)
            thread.start()
            self.active_interfaces[interface_type] = thread
            
        elif interface_type == InterfaceType.VOICE_ONLY:
            thread = threading.Thread(target=self.voice_interface.start_voice_loop, daemon=True)
            thread.start()
            self.active_interfaces[interface_type] = thread
            
        elif interface_type == InterfaceType.MOBILE_APP:
            thread = threading.Thread(target=self.mobile_backend.start_mobile_server, daemon=True)
            thread.start()
            self.active_interfaces[interface_type] = thread
        
        print(f"✅ Started interface: {interface_type.value}")
    
    def stop_interface(self, interface_type: InterfaceType):
        """Stop a specific interface"""
        if interface_type in self.active_interfaces:
            if interface_type == InterfaceType.VOICE_ONLY:
                self.voice_interface.stop_voice_loop()
            elif interface_type == InterfaceType.WEB_INTERFACE:
                self.web_interface.stop_server()
            
            del self.active_interfaces[interface_type]
            print(f"🛑 Stopped interface: {interface_type.value}")
    
    def get_active_interfaces(self) -> List[InterfaceType]:
        """Get list of currently active interfaces"""
        return list(self.active_interfaces.keys())
    
    def get_interface_stats(self) -> Dict[str, Any]:
        """Get statistics about interface usage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT interface_type, COUNT(*) as session_count, 
                   AVG(session_duration) as avg_duration,
                   SUM(commands_processed) as total_commands
            FROM interface_usage 
            GROUP BY interface_type
        ''')
        
        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = {
                "session_count": row[1],
                "avg_duration": row[2] or 0,
                "total_commands": row[3] or 0
            }
        
        conn.close()
        
        # Add current active interfaces
        stats["active_interfaces"] = [iface.value for iface in self.active_interfaces.keys()]
        stats["total_active"] = len(self.active_interfaces)
        
        return stats
    
    def generate_qr_pairing_code(self) -> Optional[str]:
        """Generate QR code for mobile app pairing"""
        if HAS_QR_SUPPORT:
            pairing_data = {
                "server_url": "http://localhost:5000",
                "mobile_api_url": "http://localhost:8080",
                "pairing_code": f"pair_{int(time.time())}",
                "expires_at": (datetime.now() + timedelta(hours=1)).isoformat()
            }
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(json.dumps(pairing_data))
            qr.make(fit=True)
            
            # Save QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            qr_path = "mobile_pairing_qr.png"
            img.save(qr_path)
            
            print(f"📱 QR code saved to {qr_path}")
            return qr_path
        
        return None

def main():
    """Example usage of Modern Interface Options"""
    interface_manager = ModernInterfaceManager()
    
    print("🚀 Modern Interface Options Demo")
    
    # Start web interface
    print("Starting web interface...")
    interface_manager.start_interface(InterfaceType.WEB_INTERFACE)
    
    # Start mobile backend
    print("Starting mobile backend...")
    interface_manager.start_interface(InterfaceType.MOBILE_APP)
    
    print("Interfaces started. Check:")
    print("🌐 Web Interface: http://localhost:5000")
    print("🌐 Mobile Interface: http://localhost:5000/mobile")
    print("🎤 Voice Interface: http://localhost:5000/voice")
    print("📱 Mobile Backend: http://localhost:8080")
    
    # Generate QR code for mobile pairing
    qr_path = interface_manager.generate_qr_pairing_code()
    if qr_path:
        print(f"📱 Mobile pairing QR code: {qr_path}")
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping interfaces...")
        for interface_type in list(interface_manager.active_interfaces.keys()):
            interface_manager.stop_interface(interface_type)

if __name__ == "__main__":
    main()