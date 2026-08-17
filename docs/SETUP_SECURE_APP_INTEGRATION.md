# 🔒 Secure App Integration Setup Guide

This guide will help you securely connect your applications to the AI Assistant while protecting your personal information.

## 🚀 Quick Start

### 1. Install Dependencies

Make sure you have the required security packages:

```bash
pip install cryptography flask flask-cors
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### 2. Configure Security Settings

Copy the security configuration template:

```bash
cp config/app_integration.env.example config/app_integration.env
```

**IMPORTANT**: Edit `config/app_integration.env` and set secure passwords:

```env
ADMIN_PASSWORD=your-very-secure-password-here
APP_SECRET_KEY=your-secret-key-for-encryption
```

**Generate secure keys**:
```python
import secrets
print("Admin Password:", secrets.token_urlsafe(32))
print("Secret Key:", secrets.token_hex(32))
```

### 3. Start the App Integration System

**Windows:**
```cmd
scripts\start_app_integration.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/start_app_integration.sh
./scripts/start_app_integration.sh
```

**Manual start:**
```bash
python -m ai_assistant.services.app_integration_api
```

### 4. Access the Interface

- **Web Interface**: http://localhost:5001
- **CLI Tool**: `python -m ai_assistant.cli.app_manager`

## 🔐 Security Features

### ✅ What's Protected
- **API Keys & Secrets**: Encrypted using industry-standard cryptography
- **OAuth Tokens**: Stored encrypted, never in plain text
- **Personal Credentials**: Never leave your machine
- **Git Safety**: All sensitive files automatically excluded from version control

### ✅ Privacy Guarantees
- **No Telemetry**: Zero data collection or analytics
- **Local Storage**: All data remains on your machine
- **No Cloud Dependencies**: Works completely offline
- **Open Source**: Full transparency, no hidden code

### ✅ Access Controls
- **Permission System**: Apps require explicit permissions
- **Admin Authentication**: Password-protected management interface
- **Process Isolation**: Apps run in separate, controlled processes
- **Audit Logging**: All actions logged for security review

## 📱 Registering Apps

### Via Web Interface

1. Open http://localhost:5001
2. Login with your admin password
3. Click "Register App"
4. Fill in the app details
5. For API integrations, enter your credentials securely

### Via Command Line

```bash
# Interactive registration
python -m ai_assistant.cli.app_manager register

# List registered apps
python -m ai_assistant.cli.app_manager list

# Launch an app
python -m ai_assistant.cli.app_manager launch spotify

# Check app status
python -m ai_assistant.cli.app_manager status discord_bot
```

## 🔧 Integration Examples

### Basic App (Executable)

```bash
python -m ai_assistant.cli.app_manager register
# Name: notepad
# Display Name: Notepad
# Category: productivity
# Integration Type: basic
# Executable Path: C:\Windows\System32\notepad.exe
```

### API Integration (Spotify)

```bash
python -m ai_assistant.cli.app_manager register
# Name: spotify
# Display Name: Spotify
# Category: media
# Integration Type: api
# API Endpoint: https://api.spotify.com/v1
# API Key: [your-spotify-api-key]
```

### OAuth App (Discord Bot)

```json
{
  "name": "discord_bot",
  "display_name": "Discord Bot",
  "category": "communication",
  "integration_type": "oauth",
  "api_endpoint": "https://discord.com/api/v10",
  "permissions": ["network_access", "notification_access"],
  "auto_start": true
}
```

## 🛡️ Best Practices

### 1. Credential Management
- **Never commit credentials** to version control
- **Use environment variables** for development
- **Rotate API keys regularly**
- **Use least-privilege permissions**

### 2. Network Security
- **Use HTTPS** for all API calls
- **Validate SSL certificates**
- **Monitor network traffic**
- **Use VPN for sensitive operations**

### 3. App Permissions

Grant only the minimum required permissions:

| Permission | Description | Risk Level |
|------------|-------------|------------|
| `file_access` | Read/write files | High |
| `system_access` | System operations | High |
| `network_access` | Internet connectivity | Medium |
| `audio_control` | Control audio playback | Low |
| `clipboard_access` | Read/write clipboard | Medium |
| `notification_access` | Show notifications | Low |

### 4. Monitoring & Auditing

Check logs regularly:
```bash
# View integration logs
tail -f logs/integration/app_integration.log

# Check security events
tail -f logs/security/security.log
```

## 🔍 Troubleshooting

### Common Issues

**1. Authentication Failed**
```
Solution: Check ADMIN_PASSWORD in config/app_integration.env
```

**2. App Won't Launch**
```
Solution: Verify executable path and permissions
```

**3. API Credentials Invalid**
```
Solution: Check API key encryption and decryption
```

**4. Permission Denied**
```
Solution: Review app permissions and security level
```

### Debug Mode

Enable debug logging:
```env
# In config/app_integration.env
FLASK_DEBUG=true
ENABLE_APP_INTEGRATION_LOGGING=true
```

### Reset Everything

If you need to start fresh:
```bash
# Remove all apps and credentials
rm -rf config/secure/
rm config/registered_apps.json

# Restart the system
python -m ai_assistant.services.app_integration_api
```

## 📁 File Structure

```
config/
├── app_integration.env          # Your secure config (private)
├── app_integration.env.example  # Template
├── registered_apps.json         # Public app registry
└── secure/                      # Encrypted credentials (git-ignored)
    ├── .gitignore              # Protects sensitive files
    ├── .key                    # Encryption key (auto-generated)
    └── *_credentials.json      # Encrypted app credentials
```

## 🚨 Emergency Procedures

### If Credentials Are Compromised

1. **Immediately rotate** all API keys
2. **Remove compromised apps**:
   ```bash
   python -m ai_assistant.cli.app_manager remove compromised_app
   ```
3. **Change admin password** in config
4. **Check audit logs** for unauthorized access
5. **Regenerate encryption keys**:
   ```bash
   rm config/secure/.key
   # Restart the system to generate new key
   ```

### If System Is Compromised

1. **Stop all integrations**:
   ```bash
   pkill -f app_integration_api
   ```
2. **Backup important data**
3. **Review all registered apps**
4. **Scan for malware**
5. **Rebuild from clean state**

## 📞 Support

For security issues or questions:

1. **Check the logs** first: `logs/integration/`
2. **Review documentation**: `docs/APP_INTEGRATION_SECURITY.md`
3. **Test with simple apps** before complex integrations
4. **Verify network connectivity** and permissions

## 🔄 Updates and Maintenance

### Regular Maintenance

- **Update dependencies** monthly
- **Rotate credentials** quarterly  
- **Review permissions** regularly
- **Clean up unused apps**
- **Monitor resource usage**

### Security Updates

The system will automatically:
- **Encrypt new credentials**
- **Validate app permissions**
- **Log security events**
- **Exclude sensitive files from git**

### Backup Strategy

**Critical files to backup**:
- `config/app_integration.env` (securely)
- `config/registered_apps.json`
- `config/secure/` directory (encrypted)

**Never backup**:
- Decrypted credentials
- Temporary files
- Log files with sensitive data

---

**Remember**: This system is designed to keep your personal information private and secure. All sensitive data remains encrypted on your local machine and is never transmitted to external servers.