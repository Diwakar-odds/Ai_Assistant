# AI Assistant - Secure App Integration

## Overview

The AI Assistant now includes a secure app integration system that allows you to safely connect third-party applications while protecting your personal information and credentials.

## 🔒 Security Features

- **Encrypted Credential Storage**: API keys and sensitive data are encrypted using industry-standard cryptography
- **Local-Only Storage**: All credentials remain on your machine and are never sent to external servers
- **Git-Safe Configuration**: Sensitive files are automatically excluded from version control
- **Permission-Based Access**: Apps require explicit permissions for system operations
- **Secure Communication**: All API communications use authentication tokens
- **Process Isolation**: Apps run in separate processes with controlled access

## 🚀 Quick Start

### 1. Set Up Environment

Copy the example configuration file:
```bash
cp config/app_integration.env.example config/app_integration.env
```

Edit `config/app_integration.env` and set your admin password:
```env
ADMIN_PASSWORD=your-very-secure-password
APP_SECRET_KEY=your-secure-secret-key
```

### 2. Register Your First App

Use the CLI tool to register an application:
```bash
python -m ai_assistant.cli.app_manager register
```

Follow the interactive prompts to configure your app.

### 3. Start the Integration API

```bash
python -m ai_assistant.services.app_integration_api
```

The API will be available at `http://localhost:5001`

## 📱 Managing Apps

### Command Line Interface

```bash
# Register a new app
python -m ai_assistant.cli.app_manager register

# List all registered apps
python -m ai_assistant.cli.app_manager list

# Launch an app
python -m ai_assistant.cli.app_manager launch my_app

# Stop an app
python -m ai_assistant.cli.app_manager stop my_app

# Check app status
python -m ai_assistant.cli.app_manager status my_app

# Remove an app
python -m ai_assistant.cli.app_manager remove my_app

# Auto-start all configured apps
python -m ai_assistant.cli.app_manager autostart
```

### Web Interface

Access the web management interface at:
```
http://localhost:5001
```

Login with your admin password to manage apps through the web UI.

## 🔧 Integration Types

### 1. Basic Integration
- Simple executable launch
- No API communication
- Lowest security requirements

### 2. API Integration
- RESTful API communication
- Requires API keys/tokens
- Medium security requirements

### 3. OAuth Integration
- OAuth 2.0 authentication flow
- Access and refresh tokens
- High security requirements

### 4. Webhook Integration
- Event-driven communication
- Callback URL configuration
- High security requirements

## 🛡️ Security Best Practices

### 1. Credential Management
- Never hardcode credentials in your configuration
- Use environment variables for sensitive data
- Regularly rotate API keys and tokens
- Review app permissions periodically

### 2. Network Security
- Use HTTPS for all API communications
- Restrict network access where possible
- Monitor outbound connections
- Use VPN for sensitive integrations

### 3. Access Control
- Use strong admin passwords
- Enable two-factor authentication when available
- Limit app permissions to minimum required
- Regularly audit app access logs

### 4. Data Protection
- Keep local backups of important configurations
- Monitor file system permissions
- Use disk encryption for sensitive machines
- Implement data retention policies

## 📁 File Structure

```
config/
├── app_integration.env          # Your configuration (keep private)
├── app_integration.env.example  # Example configuration
├── registered_apps.json         # Public app registry
└── secure/                      # Encrypted credentials (git-ignored)
    ├── .gitignore
    ├── .key                     # Encryption key (auto-generated)
    └── *_credentials.json       # Encrypted app credentials
```

## 🔍 Example App Configurations

### Spotify Integration
```json
{
  "name": "spotify",
  "display_name": "Spotify Music Player",
  "category": "media",
  "integration_type": "api",
  "api_endpoint": "https://api.spotify.com/v1",
  "permissions": ["audio_control", "network_access"],
  "auto_start": false
}
```

### VS Code Integration
```json
{
  "name": "vscode",
  "display_name": "Visual Studio Code",
  "category": "development",
  "integration_type": "basic",
  "executable_path": "C:\\Program Files\\Microsoft VS Code\\Code.exe",
  "startup_args": ["--new-window"],
  "permissions": ["file_access"],
  "auto_start": false
}
```

### Discord Bot Integration
```json
{
  "name": "discord_bot",
  "display_name": "Discord Bot",
  "category": "communication",
  "integration_type": "webhook",
  "api_endpoint": "https://discord.com/api/webhooks/...",
  "permissions": ["network_access", "notification_access"],
  "auto_start": true
}
```

## 🚨 Important Security Notes

### What Gets Encrypted
- API keys and secrets
- Access tokens and refresh tokens
- Passwords and credentials
- Any field containing 'key', 'secret', 'token', or 'password'

### What Stays Public
- App names and display names
- Categories and descriptions
- Executable paths (local only)
- Permission lists
- Integration types

### Git Safety
The following files/directories are automatically excluded from Git:
- `config/app_integration.env`
- `config/secure/`
- Any files matching `*credentials*`
- Any files matching `*.key`, `*.pem`, `*.cert`

### Network Privacy
- All credentials remain local to your machine
- No telemetry or usage data is collected
- API communications use your own tokens
- No data is sent to external analytics services

## 📞 Support

If you encounter issues:
1. Check the logs in `logs/integration/`
2. Verify your environment configuration
3. Test with a simple app first
4. Review the security settings

Remember: This system is designed to keep your personal information private and secure. All sensitive data remains encrypted on your local machine.