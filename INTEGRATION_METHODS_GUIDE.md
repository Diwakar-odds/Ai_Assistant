# 🔐 Universal Integration Methods - Complete Security Guide

**Last Updated:** November 18, 2025  
**For:** YourDaddy Assistant v3.1+

This document explains **every authentication method** available for connecting external services to your assistant, with detailed security analysis, pros/cons, and implementation details.

---

## 📋 Table of Contents

1. [Method 1: Browser Session Capture](#method-1-browser-session-capture) ⭐ **SAFEST**
2. [Method 2: Python Library Authentication](#method-2-python-library-authentication)
3. [Method 3: OAuth2 Authorization Flow](#method-3-oauth2-authorization-flow)
4. [Method 4: Direct API Keys](#method-4-direct-api-keys)
5. [Method 5: Browser Automation (Live)](#method-5-browser-automation-live)
6. [Security Comparison Matrix](#security-comparison-matrix)
7. [Recommended Methods by Service](#recommended-methods-by-service)

---

## Method 1: Browser Session Capture

### 🎯 Overview

The assistant opens a real browser, you login manually, then it captures and saves your session cookies. Future access uses these cookies without requiring password again.

### 🔧 How It Works

```
Step 1: Assistant opens Chrome
Step 2: Navigates to service login page
Step 3: YOU login manually (assistant doesn't see)
Step 4: Press Enter when done
Step 5: Assistant captures session cookies
Step 6: Encrypts and saves cookies locally
Step 7: Closes browser
Step 8: Future access: Loads encrypted cookies
```

### 🔐 Security Analysis

#### ✅ Advantages

- **Your password NEVER exposed to assistant code**
- **You login like normal** (familiar, comfortable)
- **Works for ANY website** (even without APIs)
- **Multi-factor auth supported** (you handle it manually)
- **No API keys needed**
- **Session stored locally** on your PC only
- **Encrypted at rest** using master key

#### ⚠️ Risks

- **Session hijacking risk**: If someone steals your PC and decrypts vault
  - **Mitigation**: Master key stored in OS keychain (requires your PC password)
- **Session expiry**: Need to re-login periodically (30-90 days)
  - **Mitigation**: Auto-detects expiry, prompts for re-login
- **Browser fingerprinting**: Service might detect automation
  - **Mitigation**: Uses anti-detection techniques (stealth mode)

#### 🛡️ Security Rating: ⭐⭐⭐⭐⭐ (5/5)

**Best for:** Instagram, Facebook, Unstop, any website without API

---

### 📊 Technical Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Password Visibility** | ❌ Never | Assistant code never sees password |
| **Storage Location** | Local PC | `~/.yourdaddy/vault.enc` |
| **Encryption** | AES-128 (Fernet) | Military-grade encryption |
| **Master Key Storage** | OS Keychain | Windows Credential Manager / macOS Keychain |
| **Session Duration** | 30-90 days | Depends on service |
| **MFA Support** | ✅ Yes | You handle MFA during manual login |
| **Offline Access** | ✅ Yes | Works without internet (after setup) |
| **Third Party Access** | ❌ None | Direct connection only |
| **Revocation** | Delete cookies | Clear vault or re-login |

---

### 💻 Implementation Details

```python
from selenium import webdriver
from cryptography.fernet import Fernet
import keyring
import json

def capture_session(service_url: str, service_name: str):
    """Capture browser session for any service"""
    
    # Initialize browser with anti-detection
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    browser = webdriver.Chrome(options=options)
    
    # Navigate to service
    browser.get(service_url)
    
    # Wait for user to login
    input(f"Please login to {service_name}, then press Enter...")
    
    # Capture cookies
    cookies = browser.get_cookies()
    
    # Get master key from OS keychain
    master_key = keyring.get_password("yourdaddy", "master_key").encode()
    fernet = Fernet(master_key)
    
    # Encrypt cookies
    cookies_json = json.dumps(cookies).encode()
    encrypted_cookies = fernet.encrypt(cookies_json)
    
    # Save encrypted
    with open(f"vault/{service_name}_session.enc", "wb") as f:
        f.write(encrypted_cookies)
    
    browser.quit()
    
    return "✅ Session captured and encrypted"
```

---

### 🎬 User Experience

**First Time Setup:**
```
User: "Connect to Instagram"
Assistant: "Opening Instagram... Please login."
[Chrome opens to instagram.com]
User: [Enters username/password, handles 2FA]
User: [Presses Enter in terminal]
Assistant: "✅ Instagram connected! Session saved securely."
[Browser closes]
```

**Every Use After:**
```
User: "Post to Instagram"
Assistant: [Loads encrypted cookies silently]
Assistant: "✅ Posted to Instagram!"
[No browser, no login, instant]
```

---

## Method 2: Python Library Authentication

### 🎯 Overview

Uses official or trusted Python libraries (like `instagrapi`, `tweepy`, `spotipy`) that provide programmatic access. You provide credentials ONCE, library handles authentication and token refresh.

### 🔧 How It Works

```
Step 1: Install Python library (pip install instagrapi)
Step 2: Provide username + password
Step 3: Library logs in via API
Step 4: Library receives access token
Step 5: Token encrypted and saved
Step 6: Password deleted from memory
Step 7: Future: Uses token for all requests
```

### 🔐 Security Analysis

#### ✅ Advantages

- **Faster than browser** (no GUI startup)
- **More reliable** (no UI changes break it)
- **Programmatic control** (precise actions)
- **Token auto-refresh** (many libraries handle it)
- **Works headless** (no screen needed)
- **Official libraries** (Instagram, Twitter, etc.)

#### ⚠️ Risks

- **Password visible to library code** (during first login)
  - **Mitigation**: Use only trusted, open-source libraries
  - **Verification**: Review library source code on GitHub
- **Library vulnerabilities** (could be exploited)
  - **Mitigation**: Keep libraries updated, check CVEs
- **Service API changes** (library breaks until updated)
  - **Mitigation**: Fallback to browser method

#### 🛡️ Security Rating: ⭐⭐⭐⭐ (4/5)

**Best for:** Instagram (instagrapi), Twitter (tweepy), Spotify (spotipy)

---

### 📊 Technical Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Password Visibility** | ⚠️ First login only | Library sees password, then deleted |
| **Storage Location** | Local PC | `~/.yourdaddy/vault.enc` |
| **Encryption** | AES-128 (Fernet) | Tokens encrypted at rest |
| **Master Key Storage** | OS Keychain | Same as Method 1 |
| **Session Duration** | 60-180 days | Library manages refresh |
| **MFA Support** | ⚠️ Limited | Some libraries support, some don't |
| **Offline Access** | ❌ No | Needs internet for API calls |
| **Third Party Access** | ❌ None | Direct to service API |
| **Revocation** | Change password | Or delete token from vault |

---

### 💻 Implementation Details

```python
from instagrapi import Client
from cryptography.fernet import Fernet
import keyring
import json

def setup_instagram_library(username: str, password: str):
    """Setup Instagram using instagrapi library"""
    
    # Initialize client
    cl = Client()
    
    # Login (password visible here)
    try:
        cl.login(username, password)
    except Exception as e:
        return f"❌ Login failed: {e}"
    
    # Get session data
    session = cl.get_settings()
    
    # Immediately clear password from memory
    del password
    
    # Get master key
    master_key = keyring.get_password("yourdaddy", "master_key").encode()
    fernet = Fernet(master_key)
    
    # Encrypt session
    session_json = json.dumps(session).encode()
    encrypted_session = fernet.encrypt(session_json)
    
    # Save encrypted
    with open("vault/instagram_library.enc", "wb") as f:
        f.write(encrypted_session)
    
    return "✅ Instagram library configured"


def use_instagram_library(action: str, **params):
    """Use Instagram library for actions"""
    
    # Load encrypted session
    master_key = keyring.get_password("yourdaddy", "master_key").encode()
    fernet = Fernet(master_key)
    
    with open("vault/instagram_library.enc", "rb") as f:
        encrypted = f.read()
    
    decrypted = fernet.decrypt(encrypted)
    session = json.loads(decrypted)
    
    # Create client with saved session
    cl = Client()
    cl.set_settings(session)
    
    # Execute action (NO PASSWORD NEEDED)
    if action == "post":
        cl.photo_upload(params['image'], params['caption'])
        return "✅ Posted"
```

---

### 🎬 User Experience

**First Time Setup:**
```
User: "Setup Instagram with library"
Assistant: "Username?"
User: "myusername"
Assistant: "Password?"
User: "••••••••" [hidden input]
Assistant: "Logging in..."
Assistant: "✅ Instagram library configured!"
[Password never stored, only session token]
```

**Every Use After:**
```
User: "Post to Instagram"
Assistant: [Loads encrypted token]
Assistant: "✅ Posted!" [2 seconds, no browser]
```

---

## Method 3: OAuth2 Authorization Flow

### 🎯 Overview

The gold standard for secure authentication. Service provides a special login page, you authorize the app, service gives a token directly. **Zero password sharing.**

### 🔧 How It Works

```
Step 1: Assistant requests authorization URL
Step 2: Opens service's official auth page in browser
Step 3: YOU login on service's website (not assistant)
Step 4: You click "Allow" to grant permissions
Step 5: Service redirects with authorization code
Step 6: Assistant exchanges code for access token
Step 7: Token encrypted and saved
Step 8: Future: Uses token (auto-refreshes)
```

### 🔐 Security Analysis

#### ✅ Advantages

- **ZERO password sharing** (most secure method)
- **Granular permissions** ("post only", not "full access")
- **Official method** (recommended by services)
- **Easy revocation** (revoke from service settings)
- **Token auto-refresh** (built into OAuth2)
- **Industry standard** (used by all major services)
- **Audit trail** (service logs which app accessed)

#### ⚠️ Risks

- **Token theft** (if PC compromised)
  - **Mitigation**: Encrypted storage, OS keychain
- **Scope creep** (requesting too many permissions)
  - **Mitigation**: Request minimal scopes only
- **Redirect hijacking** (MITM attack)
  - **Mitigation**: Use localhost redirect, HTTPS

#### 🛡️ Security Rating: ⭐⭐⭐⭐⭐ (5/5)

**Best for:** Google (Gmail, Calendar), Spotify, Microsoft, GitHub

---

### 📊 Technical Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Password Visibility** | ❌ Never | You login on service's site, not assistant |
| **Storage Location** | Local PC | `~/.yourdaddy/vault.enc` |
| **Encryption** | AES-128 (Fernet) | Tokens encrypted at rest |
| **Master Key Storage** | OS Keychain | Same as other methods |
| **Session Duration** | 1-7 days (access token) | Refresh token lasts 60+ days |
| **MFA Support** | ✅ Yes | Service handles MFA on their page |
| **Offline Access** | ❌ No | Needs internet for token refresh |
| **Third Party Access** | ❌ None | Direct OAuth flow |
| **Revocation** | Service settings | Revoke from Google/Spotify account |
| **Permissions** | Granular | "read only", "post only", etc. |

---

### 💻 Implementation Details

```python
import webbrowser
from urllib.parse import urlencode, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from cryptography.fernet import Fernet
import keyring
import json

def oauth2_spotify():
    """OAuth2 flow for Spotify"""
    
    # Step 1: Authorization URL
    client_id = "your_app_client_id"
    redirect_uri = "http://localhost:8888/callback"
    scope = "user-read-playback-state user-modify-playback-state"
    
    auth_url = "https://accounts.spotify.com/authorize?" + urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope
    })
    
    # Step 2: Open browser for user to authorize
    print("Opening browser for authorization...")
    webbrowser.open(auth_url)
    
    # Step 3: Start local server to receive callback
    auth_code = None
    
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            query = parse_qs(self.path.split('?')[1])
            auth_code = query.get('code', [None])[0]
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Authorization successful! You can close this window.")
    
    server = HTTPServer(('localhost', 8888), CallbackHandler)
    server.handle_request()  # Wait for one request
    
    # Step 4: Exchange code for token
    token_url = "https://accounts.spotify.com/api/token"
    token_data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": "your_app_secret"
    }
    
    response = requests.post(token_url, data=token_data)
    tokens = response.json()
    
    # Step 5: Encrypt and save tokens
    master_key = keyring.get_password("yourdaddy", "master_key").encode()
    fernet = Fernet(master_key)
    
    tokens_json = json.dumps(tokens).encode()
    encrypted_tokens = fernet.encrypt(tokens_json)
    
    with open("vault/spotify_oauth.enc", "wb") as f:
        f.write(encrypted_tokens)
    
    return "✅ Spotify OAuth2 configured!"
```

---

### 🎬 User Experience

**First Time Setup:**
```
User: "Connect Spotify"
Assistant: "Opening Spotify authorization page..."
[Browser opens to accounts.spotify.com]
[You see: "YourDaddy Assistant wants to access your Spotify"]
[Permissions listed: "Control playback", "View current song"]
User: [Clicks "Allow"]
[Browser redirects to localhost]
Assistant: "✅ Spotify connected securely!"
```

**Every Use After:**
```
User: "Play Bohemian Rhapsody on Spotify"
Assistant: [Uses OAuth token]
Assistant: "🎵 Now playing!"
[Token auto-refreshes if expired]
```

---

## Method 4: Direct API Keys

### 🎯 Overview

Service provides you with an API key (long random string). You give it to assistant, assistant uses it for all requests. Simple but less secure than OAuth2.

### 🔧 How It Works

```
Step 1: Get API key from service dashboard
Step 2: Paste key into assistant config
Step 3: Assistant encrypts and saves key
Step 4: Future: Uses key for API calls
```

### 🔐 Security Analysis

#### ✅ Advantages

- **Simple setup** (just copy-paste key)
- **No browser needed**
- **Long-lasting** (keys don't expire)
- **Programmatic access**
- **No login flow needed**

#### ⚠️ Risks

- **No permission scopes** (full account access)
- **Hard to revoke** (must regenerate key)
- **Key theft = full access** (unlike OAuth refresh tokens)
- **No audit trail** (harder to track which app did what)
- **Manual rotation** (no auto-refresh)

#### 🛡️ Security Rating: ⭐⭐⭐ (3/5)

**Best for:** OpenAI, Weather APIs, News APIs (read-only services)

---

### 📊 Technical Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Password Visibility** | N/A | No password, just API key |
| **Storage Location** | Local PC | `~/.yourdaddy/vault.enc` |
| **Encryption** | AES-128 (Fernet) | Keys encrypted at rest |
| **Master Key Storage** | OS Keychain | Same as other methods |
| **Session Duration** | Indefinite | Until manually revoked |
| **MFA Support** | N/A | Not applicable |
| **Offline Access** | ❌ No | Needs internet for API calls |
| **Third Party Access** | ❌ None | Direct API calls |
| **Revocation** | Manual | Regenerate key in service dashboard |
| **Permissions** | All or nothing | Usually full account access |

---

### 💻 Implementation Details

```python
from cryptography.fernet import Fernet
import keyring
import requests

def save_api_key(service: str, api_key: str):
    """Save encrypted API key"""
    
    # Get master key
    master_key = keyring.get_password("yourdaddy", "master_key").encode()
    fernet = Fernet(master_key)
    
    # Encrypt key
    encrypted_key = fernet.encrypt(api_key.encode())
    
    # Save
    with open(f"vault/{service}_apikey.enc", "wb") as f:
        f.write(encrypted_key)
    
    return f"✅ {service} API key saved"


def use_api_key(service: str, endpoint: str, **params):
    """Use API key for requests"""
    
    # Load encrypted key
    master_key = keyring.get_password("yourdaddy", "master_key").encode()
    fernet = Fernet(master_key)
    
    with open(f"vault/{service}_apikey.enc", "rb") as f:
        encrypted = f.read()
    
    api_key = fernet.decrypt(encrypted).decode()
    
    # Make API call
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(endpoint, headers=headers, params=params)
    
    return response.json()
```

---

## Method 5: Browser Automation (Live)

### 🎯 Overview

Opens browser every time, performs actions in real-time. **No session saving.** Slowest but most reliable for complex interactions.

### 🔧 How It Works

```
Step 1: User commands action
Step 2: Assistant opens browser
Step 3: Loads saved cookies (if any)
Step 4: Navigates to service
Step 5: Performs action (click, type, etc.)
Step 6: Closes browser
```

### 🔐 Security Analysis

#### ✅ Advantages

- **Works for ANY website** (even weird ones)
- **Handles complex flows** (multi-step forms)
- **Adapts to UI changes** (uses AI vision)
- **No API needed**
- **Full control**

#### ⚠️ Risks

- **Slower** (browser startup every time)
- **Visible** (user sees browser window)
- **Resource intensive** (RAM, CPU)
- **Can be detected** (anti-bot measures)
- **Fragile** (UI changes break it)

#### 🛡️ Security Rating: ⭐⭐⭐⭐ (4/5)

**Best for:** Complex workflows, services without APIs, one-off tasks

---

### 📊 Technical Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Password Visibility** | ❌ Never (uses cookies) | Or visible if typed in browser |
| **Storage Location** | Local PC | Cookies saved encrypted |
| **Encryption** | AES-128 (Fernet) | Cookies encrypted |
| **Master Key Storage** | OS Keychain | Same as other methods |
| **Session Duration** | Per service | Depends on cookies |
| **MFA Support** | ✅ Yes | Handled in browser |
| **Offline Access** | ❌ No | Needs internet + browser |
| **Third Party Access** | ❌ None | Local browser only |
| **Revocation** | Clear cookies | Or logout in browser |
| **Speed** | Slow (5-10 seconds) | Browser startup overhead |

---

## Security Comparison Matrix

| Method | Password Exposure | Storage Security | MFA Support | Revocation | Speed | Setup Complexity | Best For |
|--------|-------------------|------------------|-------------|-----------|-------|------------------|----------|
| **Browser Session Capture** | ❌ Never | 🔒 Encrypted | ✅ Yes | Easy | ⚡ Fast | Easy | Instagram, Unstop |
| **Python Library** | ⚠️ First login | 🔒 Encrypted | ⚠️ Limited | Medium | ⚡⚡ Very Fast | Easy | Instagram, Twitter |
| **OAuth2** | ❌ Never | 🔒 Encrypted | ✅ Yes | Very Easy | ⚡ Fast | Medium | Google, Spotify |
| **API Keys** | N/A | 🔒 Encrypted | N/A | Hard | ⚡⚡ Very Fast | Very Easy | OpenAI, Weather |
| **Browser Live** | ⚠️ Sometimes | 🔒 Encrypted | ✅ Yes | Easy | 🐌 Slow | Easy | Complex sites |

---

## Recommended Methods by Service

### Social Media

| Service | Primary Method | Fallback | Reason |
|---------|---------------|----------|--------|
| **Instagram** | Browser Session Capture | Python Library (instagrapi) | No official API |
| **Twitter/X** | OAuth2 | Python Library (tweepy) | Official API available |
| **Facebook** | OAuth2 | Browser Session | Graph API available |
| **LinkedIn** | OAuth2 | Browser Session | Official API available |
| **TikTok** | Browser Session | Browser Live | No public API |
| **Snapchat** | Browser Live | None | Very restricted |

### Productivity

| Service | Primary Method | Fallback | Reason |
|---------|---------------|----------|--------|
| **Gmail** | OAuth2 | None | Official API, secure |
| **Google Calendar** | OAuth2 | None | Official API |
| **Outlook** | OAuth2 | None | Microsoft Graph API |
| **Notion** | API Keys | OAuth2 | Official API |
| **Trello** | OAuth2 | API Keys | Official API |

### Design & Dev

| Service | Primary Method | Fallback | Reason |
|---------|---------------|----------|--------|
| **Figma** | API Keys | OAuth2 | Personal tokens work well |
| **Canva** | Browser Session | Browser Live | Limited API |
| **GitHub** | API Keys | OAuth2 | Personal tokens recommended |
| **GitLab** | API Keys | OAuth2 | Personal tokens recommended |

### Education

| Service | Primary Method | Fallback | Reason |
|---------|---------------|----------|--------|
| **Unstop** | Browser Session Capture | Browser Live | No API |
| **Coursera** | Browser Session | Browser Live | No public API |
| **Udemy** | Browser Session | Browser Live | Limited API |
| **LeetCode** | Browser Session | Browser Live | No public API |

### Music & Media

| Service | Primary Method | Fallback | Reason |
|---------|---------------|----------|--------|
| **Spotify** | OAuth2 | Python Library (spotipy) | Official API |
| **YouTube Music** | Python Library (ytmusicapi) | Browser Session | Unofficial API works well |
| **YouTube** | OAuth2 | API Keys | Official API |
| **SoundCloud** | API Keys | Browser Session | Official API |

---

## Master Key Security

### How Master Key Works

```
Windows: Stored in Credential Manager
    Control Panel > Credential Manager > Generic Credentials
    Name: yourdaddy_assistant_master_key
    Protected by: Your Windows login password

macOS: Stored in Keychain
    Keychain Access app
    Name: yourdaddy_assistant_master_key
    Protected by: Your macOS login password

Linux: Stored in Secret Service
    libsecret / gnome-keyring
    Protected by: Your login password
```

### Master Key Properties

- **Algorithm**: Fernet (AES-128-CBC + HMAC)
- **Key Size**: 256 bits (32 bytes)
- **Derived From**: Random generation (not password-based)
- **Location**: OS-specific secure storage
- **Access**: Requires PC login password
- **Backup**: Should be exported and stored securely

---

## Encryption Details

### What Gets Encrypted

```
Encrypted Files:
├── vault/instagram_session.enc    ← Session cookies
├── vault/twitter_oauth.enc         ← OAuth tokens
├── vault/spotify_oauth.enc         ← OAuth tokens
├── vault/gmail_oauth.enc           ← OAuth tokens
├── vault/figma_apikey.enc          ← API keys
└── vault/unstop_session.enc        ← Session cookies
```

### Encryption Process

```python
# Encryption
plaintext = b"sensitive_data"
master_key = get_from_keychain()  # 32-byte key
fernet = Fernet(master_key)
ciphertext = fernet.encrypt(plaintext)
# Result: b'gAAAAABhkR...' (base64 encoded)

# Decryption
plaintext = fernet.decrypt(ciphertext)
```

### Security Properties

- **Algorithm**: Fernet = AES-128-CBC + HMAC-SHA256
- **Authenticated**: Prevents tampering
- **Timestamp**: Includes creation time
- **Expiration**: Can set TTL (time-to-live)
- **Key Rotation**: Supports key changes

---

## Rate Limiting & Protection

### Built-in Rate Limits

```python
rate_limits = {
    "instagram": {
        "posts_per_hour": 5,
        "actions_per_minute": 10,
        "follows_per_hour": 20
    },
    "twitter": {
        "tweets_per_hour": 10,
        "retweets_per_hour": 20,
        "likes_per_hour": 50
    },
    "unstop": {
        "searches_per_minute": 5,
        "registrations_per_hour": 3
    }
}
```

### Protective Measures

- **Action throttling**: Delays between requests
- **Burst prevention**: Max actions in short time
- **Human-like delays**: Random 1-3 second waits
- **Warning system**: Alerts when approaching limits
- **Auto-pause**: Stops if rate limit hit

---

## Audit Logging

### What Gets Logged

```
Format: TIMESTAMP | SERVICE | ACTION | STATUS | DETAILS

Examples:
2025-11-18 10:30:15 | instagram | post | SUCCESS | caption="Hello World"
2025-11-18 10:31:22 | twitter | tweet | SUCCESS | text="Great day!"
2025-11-18 10:32:10 | unstop | search | SUCCESS | query="AI hackathon"
2025-11-18 10:33:45 | gmail | send | SUCCESS | to="boss@work.com"
2025-11-18 10:34:12 | instagram | delete | BLOCKED | reason="destructive_action"
```

### Log File Location

```
F:/bn/assistant/logs/
├── integration_actions.log      ← All actions
├── integration_errors.log       ← Errors only
└── integration_security.log     ← Security events
```

---

## Emergency Revocation

### How to Revoke Access

**Method 1: Delete Vault**
```bash
# Windows
del "C:\Users\YourName\.yourdaddy\vault.enc"

# macOS/Linux  
rm ~/.yourdaddy/vault.enc
```

**Method 2: Clear Master Key**
```python
import keyring
keyring.delete_password("yourdaddy_assistant", "master_key")
```

**Method 3: Service-Level Revocation**
- Instagram: Change password
- Twitter: Revoke app access in settings
- Google: Remove app from connected apps
- Spotify: Remove app from account settings

---

## Best Practices Summary

### ✅ DO

1. **Use Browser Session Capture** for services without APIs
2. **Use OAuth2** when available (most secure)
3. **Keep libraries updated** (security patches)
4. **Review audit logs** regularly
5. **Set conservative rate limits**
6. **Backup master key** securely
7. **Use strong PC password** (protects keychain)

### ❌ DON'T

1. **Don't use cloud platforms** (Zapier, Make) for sensitive data
2. **Don't share vault files** (encrypted but still risky)
3. **Don't disable encryption** (always keep it on)
4. **Don't skip MFA** (use it when available)
5. **Don't store passwords** in code or config files
6. **Don't use same password** for assistant and services

---

## Troubleshooting

### Session Expired

**Symptoms**: "❌ Authentication failed" or "Session invalid"

**Solution**:
```python
# Re-capture session
assistant.reconnect("instagram")  # Opens browser, you re-login
```

### Master Key Lost

**Symptoms**: "❌ Cannot decrypt vault"

**Solution**:
```python
# Reset vault (WARNING: Loses all sessions)
assistant.reset_vault()  # Requires confirmation
# Then re-setup all services
```

### Rate Limit Hit

**Symptoms**: "⚠️ Rate limit exceeded"

**Solution**:
```python
# Wait for cooldown (shown in message)
# Or adjust rate limits in config
```

---

## Configuration File Example

```json
{
  "security": {
    "master_key_location": "os_keychain",
    "encryption_algorithm": "fernet",
    "require_confirmation": {
      "delete": true,
      "unfollow": true,
      "send_money": true
    }
  },
  "services": {
    "instagram": {
      "method": "browser_session",
      "rate_limits": {
        "posts_per_hour": 5,
        "actions_per_minute": 10
      }
    },
    "twitter": {
      "method": "oauth2",
      "scopes": ["tweet.write", "tweet.read"],
      "rate_limits": {
        "tweets_per_hour": 10
      }
    },
    "gmail": {
      "method": "oauth2",
      "scopes": ["gmail.send", "gmail.readonly"],
      "require_confirmation": true
    }
  },
  "audit": {
    "log_all_actions": true,
    "log_location": "logs/integration_actions.log",
    "retention_days": 90
  }
}
```

---

## Legal & Compliance

### Terms of Service Compliance

**Important**: Using automation may violate some services' TOS:

- ✅ **Gmail, Google Calendar**: OAuth2 is official, allowed
- ✅ **Spotify**: Official API, allowed with proper app
- ⚠️ **Instagram**: No official API, automation in gray area
- ⚠️ **Facebook**: Requires approved app for automation
- ⚠️ **Twitter**: API access requires approval (free tier limited)

**Recommendation**: Use at your own risk. For critical accounts, use OAuth2 methods only.

---

## Support & Updates

**For Issues**: Check `logs/integration_errors.log`  
**For Security Concerns**: Review `logs/integration_security.log`  
**For Updates**: Pull latest from repository

**Security Contact**: If you discover a vulnerability, please report responsibly.

---

**End of Guide**

This document covers all authentication methods available in YourDaddy Assistant v3.1+. Choose the method that best balances convenience and security for your use case.
