// YourDaddy Assistant - Web Interface JavaScript

class YourDaddyWebInterface {
    constructor() {
        this.socket = null;
        this.isListening = false;
        this.recognition = null;
        this.authToken = null;
        
        this.initializeElements();
        this.initializeAuth();
        this.initializeSocket();
        this.initializeVoice();
        this.bindEvents();
        this.loadRecentApps();
        
        console.log('YourDaddy Web Interface initialized');
    }
    
    initializeAuth() {
        // Auto-login for demo purposes
        this.authToken = localStorage.getItem('auth_token');
        if (!this.authToken) {
            this.performAutoLogin();
        }
    }
    
    async performAutoLogin() {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: 'admin',
                    password: 'changeme123'
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.authToken = data.access_token;
                localStorage.setItem('auth_token', this.authToken);
                console.log('Auto-login successful');
            } else {
                console.warn('Auto-login failed, continuing without auth');
                this.authToken = null;
            }
        } catch (error) {
            console.warn('Auto-login error, continuing without auth:', error);
            this.authToken = null;
        }
    }
    
    getAuthHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        if (this.authToken) {
            headers['Authorization'] = `Bearer ${this.authToken}`;
        }
        return headers;
    }
    
    initializeElements() {
        this.elements = {
            voiceBtn: document.getElementById('voice-btn'),
            voiceText: document.getElementById('voice-text'),
            commandInput: document.getElementById('command-input'),
            sendBtn: document.getElementById('send-btn'),
            output: document.getElementById('output'),
            clearBtn: document.getElementById('clear-btn'),
            statusText: document.getElementById('status-text'),
            recentApps: document.getElementById('recent-apps'),
            modal: document.getElementById('modal'),
            modalBody: document.getElementById('modal-body'),
            modalClose: document.getElementById('modal-close')
        };
    }
    
    initializeSocket() {
        try {
            this.socket = io();
            
            this.socket.on('connect', () => {
                this.updateStatus('Connected', 'success');
                this.addMessage('Connected to YourDaddy Assistant', 'system');
            });
            
            this.socket.on('disconnect', () => {
                this.updateStatus('Disconnected', 'error');
            });
            
            this.socket.on('response', (data) => {
                this.addMessage(data.message, 'assistant');
            });
            
            this.socket.on('voice_result', (data) => {
                this.elements.voiceText.textContent = data.text;
                this.addMessage(`Voice: ${data.text}`, 'user');
                this.processCommand(data.text);
            });
            
        } catch (error) {
            console.warn('Socket.IO not available, using fallback mode');
            this.updateStatus('Offline Mode', 'warning');
        }
    }
    
    initializeVoice() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'en-US';
            
            this.recognition.onstart = () => {
                this.isListening = true;
                this.elements.voiceBtn.classList.add('listening');
                this.elements.voiceText.textContent = 'Listening...';
            };
            
            this.recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                this.elements.voiceText.textContent = transcript;
                this.addMessage(`Voice: ${transcript}`, 'user');
                this.processCommand(transcript);
            };
            
            this.recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                this.elements.voiceText.textContent = 'Voice recognition error';
            };
            
            this.recognition.onend = () => {
                this.isListening = false;
                this.elements.voiceBtn.classList.remove('listening');
                if (this.elements.voiceText.textContent === 'Listening...') {
                    this.elements.voiceText.textContent = 'Click microphone to start voice commands';
                }
            };
        } else {
            console.warn('Speech recognition not supported');
            this.elements.voiceBtn.disabled = true;
            this.elements.voiceText.textContent = 'Voice recognition not supported in this browser';
        }
    }
    
    bindEvents() {
        // Voice button
        this.elements.voiceBtn.addEventListener('click', () => {
            this.toggleVoiceRecognition();
        });
        
        // Send button
        this.elements.sendBtn.addEventListener('click', () => {
            this.sendCommand();
        });
        
        // Enter key in command input
        this.elements.commandInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendCommand();
            }
        });
        
        // Clear button
        this.elements.clearBtn.addEventListener('click', () => {
            this.clearOutput();
        });
        
        // Action buttons
        document.querySelectorAll('.action-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const command = btn.getAttribute('data-command');
                this.processCommand(command);
            });
        });
        
        // Modal close
        this.elements.modalClose.addEventListener('click', () => {
            this.closeModal();
        });
        
        window.addEventListener('click', (e) => {
            if (e.target === this.elements.modal) {
                this.closeModal();
            }
        });
    }
    
    toggleVoiceRecognition() {
        if (!this.recognition) {
            this.addMessage('Voice recognition not available', 'error');
            return;
        }
        
        if (this.isListening) {
            this.recognition.stop();
        } else {
            try {
                this.recognition.start();
            } catch (error) {
                console.error('Failed to start voice recognition:', error);
                this.addMessage('Failed to start voice recognition', 'error');
            }
        }
    }
    
    sendCommand() {
        const command = this.elements.commandInput.value.trim();
        if (!command) return;
        
        this.addMessage(command, 'user');
        this.elements.commandInput.value = '';
        this.processCommand(command);
    }
    
    async processCommand(command) {
        // Show processing indicator
        this.addMessage('Processing...', 'system');
        
        if (this.socket && this.socket.connected) {
            // Send to backend via Socket.IO
            this.socket.emit('command', { text: command });
        } else {
            // Try API call first, fallback to local processing
            try {
                await this.processCommandViaAPI(command);
            } catch (error) {
                console.warn('API call failed, falling back to local processing:', error);
                this.processCommandLocally(command);
            }
        }
    }
    
    async processCommandViaAPI(command) {
        try {
            const response = await fetch('/api/command', {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify({ command: command })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.addMessage(data.response || data.message || 'Command processed', 'assistant');
            } else {
                throw new Error(`API error: ${response.status}`);
            }
        } catch (error) {
            // Check if it's an app launch command
            if (command.toLowerCase().includes('open') || command.toLowerCase().includes('launch')) {
                const appName = command.replace(/open|launch|start|run/gi, '').trim();
                await this.launchApp(appName);
            } else {
                throw error; // Re-throw for fallback handling
            }
        }
    }
    
    async launchApp(appName) {
        try {
            const response = await fetch('/api/apps/launch', {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify({ app_name: appName })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.addMessage(data.message, 'success');
            } else {
                this.addMessage(`Failed to launch ${appName}: ${data.error}`, 'error');
            }
        } catch (error) {
            this.addMessage(`Error launching ${appName}: ${error.message}`, 'error');
        }
    }
    
    processCommandLocally(command) {
        const cmd = command.toLowerCase();
        let response = '';
        
        if (cmd.includes('hello') || cmd.includes('hi')) {
            response = 'Hello! How can I assist you today?';
        } else if (cmd.includes('time')) {
            response = `Current time: ${new Date().toLocaleTimeString()}`;
        } else if (cmd.includes('date')) {
            response = `Current date: ${new Date().toLocaleDateString()}`;
        } else if (cmd.includes('weather')) {
            response = 'Weather feature requires backend connection.';
        } else if (cmd.includes('open')) {
            const app = cmd.replace('open', '').trim();
            response = `Attempting to open ${app}...`;
        } else if (cmd.includes('search')) {
            const query = cmd.replace('search', '').trim();
            response = `Searching for: ${query}`;
            // Open search in new tab
            setTimeout(() => {
                window.open(`https://www.google.com/search?q=${encodeURIComponent(query)}`, '_blank');
            }, 1000);
        } else {
            response = `Command received: ${command}. Backend connection required for full functionality.`;
        }
        
        // Simulate processing delay
        setTimeout(() => {
            this.addMessage(response, 'assistant');
        }, 500);
    }
    
    addMessage(message, type) {
        const messageElement = document.createElement('div');
        messageElement.className = `message message-${type}`;
        
        const timestamp = new Date().toLocaleTimeString();
        const icon = this.getMessageIcon(type);
        
        messageElement.innerHTML = `
            <div class="message-header">
                <span class="message-icon">${icon}</span>
                <span class="message-type">${type.toUpperCase()}</span>
                <span class="message-time">${timestamp}</span>
            </div>
            <div class="message-content">${message}</div>
        `;
        
        // Remove welcome message if it exists
        const welcomeMsg = this.elements.output.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }
        
        this.elements.output.appendChild(messageElement);
        this.elements.output.scrollTop = this.elements.output.scrollHeight;
        
        // Remove processing messages
        if (type !== 'system') {
            const processingMsgs = this.elements.output.querySelectorAll('.message-system');
            processingMsgs.forEach(msg => {
                if (msg.textContent.includes('Processing')) {
                    msg.remove();
                }
            });
        }
    }
    
    getMessageIcon(type) {
        const icons = {
            'user': '👤',
            'assistant': '🤖',
            'system': 'ℹ️',
            'error': '❌',
            'success': '✅'
        };
        return icons[type] || '💬';
    }
    
    clearOutput() {
        this.elements.output.innerHTML = `
            <div class="welcome-message">
                <i class="fas fa-robot"></i>
                <p>Output cleared. Ready for new commands!</p>
            </div>
        `;
    }
    
    updateStatus(text, type = 'info') {
        this.elements.statusText.textContent = text;
        
        // Update status dot color
        const statusDot = document.querySelector('.status-dot');
        const colors = {
            'success': '#10b981',
            'warning': '#f59e0b',
            'error': '#ef4444',
            'info': '#6366f1'
        };
        
        if (statusDot) {
            statusDot.style.background = colors[type] || colors.info;
        }
    }
    
    async loadRecentApps() {
        try {
            const response = await fetch('/api/apps', {
                headers: this.getAuthHeaders()
            });
            
            if (response.ok) {
                const apps = await response.json();
                // Take first 6 apps for recent apps display
                const recentApps = (Array.isArray(apps) ? apps : apps.apps || []).slice(0, 6);
                
                this.elements.recentApps.innerHTML = recentApps.map(app => {
                    const icon = this.getAppIcon(app.category || app.name);
                    return `
                        <div class="app-item" onclick="assistant.openApp('${app.name}')">
                            <span class="app-icon">${icon}</span>
                            <span class="app-name">${app.name}</span>
                        </div>
                    `;
                }).join('');
            } else {
                throw new Error('Failed to fetch apps');
            }
        } catch (error) {
            console.warn('Failed to load apps from API, using fallback:', error);
            // Fallback to mock apps
            const mockApps = [
                { name: 'Chrome', icon: '🌐' },
                { name: 'VS Code', icon: '💻' },
                { name: 'Spotify', icon: '🎵' },
                { name: 'Discord', icon: '💬' },
                { name: 'Notepad++', icon: '📝' },
                { name: 'Calculator', icon: '🧮' }
            ];
            
            this.elements.recentApps.innerHTML = mockApps.map(app => `
                <div class="app-item" onclick="assistant.openApp('${app.name}')">
                    <span class="app-icon">${app.icon}</span>
                    <span class="app-name">${app.name}</span>
                </div>
            `).join('');
        }
    }
    
    getAppIcon(categoryOrName) {
        const iconMap = {
            'Web Browsers': '🌐',
            'Browser': '🌐',
            'Development': '💻',
            'Media': '🎵',
            'Communication': '💬',
            'System Tools': '🔧',
            'Productivity': '📝',
            'Chrome': '🌐',
            'Firefox': '🌐',
            'Edge': '🌐',
            'VS Code': '💻',
            'Code': '💻',
            'Spotify': '🎵',
            'YouTube Music': '🎵',
            'Discord': '💬',
            'Teams': '💬',
            'Slack': '💬',
            'Notepad': '📝',
            'Calculator': '🧮',
            'Paint': '🎨'
        };
        
        return iconMap[categoryOrName] || '📱';
    }
    
    async openApp(appName) {
        this.addMessage(`Opening ${appName}...`, 'system');
        await this.launchApp(appName);
    }
    
    showModal(title, content) {
        this.elements.modalBody.innerHTML = `
            <h2>${title}</h2>
            <div>${content}</div>
        `;
        this.elements.modal.style.display = 'block';
    }
    
    closeModal() {
        this.elements.modal.style.display = 'none';
    }
}

// Global functions for footer links
function showAbout() {
    const content = `
        <p><strong>YourDaddy Assistant</strong> is an AI-powered personal assistant that helps you:</p>
        <ul>
            <li>🗣️ Control your computer with voice commands</li>
            <li>🚀 Launch applications quickly</li>
            <li>🔍 Search the web and get information</li>
            <li>📝 Take notes and manage tasks</li>
            <li>🎵 Control music playback</li>
            <li>⚙️ Automate system tasks</li>
        </ul>
        <p><strong>Version:</strong> 3.0.0</p>
        <p><strong>Created by:</strong> Your Development Team</p>
    `;
    assistant.showModal('About YourDaddy Assistant', content);
}

function showSettings() {
    const content = `
        <p>Settings panel coming soon! Features will include:</p>
        <ul>
            <li>🎤 Voice recognition settings</li>
            <li>🎨 Theme customization</li>
            <li>🔧 Automation preferences</li>
            <li>📊 Usage analytics</li>
            <li>🔒 Privacy controls</li>
        </ul>
        <p>For now, you can modify settings in the configuration files.</p>
    `;
    assistant.showModal('Settings', content);
}

function showHelp() {
    const content = `
        <h3>Available Commands:</h3>
        <ul>
            <li><strong>"open [app]"</strong> - Open an application</li>
            <li><strong>"search [query]"</strong> - Search on Google</li>
            <li><strong>"weather"</strong> - Get weather information</li>
            <li><strong>"time"</strong> - Get current time</li>
            <li><strong>"date"</strong> - Get current date</li>
            <li><strong>"system status"</strong> - Check system performance</li>
        </ul>
        
        <h3>Voice Commands:</h3>
        <p>Click the microphone button and speak naturally. The assistant will process your voice commands the same way as text commands.</p>
        
        <h3>Quick Actions:</h3>
        <p>Use the quick action buttons below the command input for common tasks.</p>
    `;
    assistant.showModal('Help & Commands', content);
}

// Add message styles to CSS dynamically
const messageStyles = `
    .message {
        margin: 10px 0;
        padding: 12px 16px;
        border-radius: 10px;
        border-left: 4px solid;
        background: rgba(255, 255, 255, 0.05);
    }
    
    .message-user {
        border-left-color: #6366f1;
        background: rgba(99, 102, 241, 0.1);
    }
    
    .message-assistant {
        border-left-color: #10b981;
        background: rgba(16, 185, 129, 0.1);
    }
    
    .message-system {
        border-left-color: #f59e0b;
        background: rgba(245, 158, 11, 0.1);
    }
    
    .message-error {
        border-left-color: #ef4444;
        background: rgba(239, 68, 68, 0.1);
    }
    
    .message-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 5px;
        font-size: 0.85rem;
        opacity: 0.8;
    }
    
    .message-content {
        line-height: 1.5;
    }
    
    .app-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 12px;
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .app-item:hover {
        background: rgba(99, 102, 241, 0.2);
        transform: translateY(-1px);
    }
    
    .app-icon {
        font-size: 1.5rem;
    }
    
    .app-name {
        font-weight: 500;
    }
`;

// Inject styles
const style = document.createElement('style');
style.textContent = messageStyles;
document.head.appendChild(style);

// Initialize the assistant when DOM is loaded
let assistant;
document.addEventListener('DOMContentLoaded', () => {
    assistant = new YourDaddyWebInterface();
});

// Export for global access
window.assistant = assistant;