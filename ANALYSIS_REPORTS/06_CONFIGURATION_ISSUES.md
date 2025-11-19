# ⚙️ Configuration Issues Analysis

**Files Analyzed:** 5  
**Critical Issues:** 6  
**Security Risks:** 4  
**Status:** 🔴 **MAJOR ISSUES**  
**Last Updated:** November 17, 2025

---

## 📁 Configuration Files

### Current Files
- `multimodal_config.json` - Multimodal settings
- `requirements.txt` - Python dependencies
- `prerequisites.txt` - System requirements
- `package.json` - Frontend dependencies
- `.env` (missing) - Environment variables

---

## 🐛 Critical Issues

### Issue #1: No .env File - Hardcoded Secrets 🔴
**Files:** Multiple  
**Severity:** CRITICAL SECURITY

```python
# modules/multimodal.py - Line 23
GOOGLE_API_KEY = "AIzaSyBqN0ooaSDpL8wOh9pv_X9nC7aVpXzZgHQ"  # ❌ HARDCODED

# modules/email.py
EMAIL = "your_email@gmail.com"  # ❌ Placeholder
PASSWORD = "your_password"  # ❌ Plaintext

# modules/calendar.py
CALENDAR_ID = "primary"  # ❌ No credentials
```

**Already documented in Critical Issues - See:**
- [Critical Issues Report - Issue #3](01_CRITICAL_ISSUES.md#issue-3-api-keys-hardcoded-secrets-exposed)

**Fix - Create .env File:**

```bash
# .env
# DO NOT COMMIT THIS FILE - Add to .gitignore

# Google API
GOOGLE_API_KEY=your_actual_api_key_here
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# Spotify API
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:5000/callback

# Email Configuration
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_specific_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# JWT Configuration
JWT_SECRET_KEY=generate_random_secret_key_here
JWT_ACCESS_TOKEN_EXPIRES=3600

# Database
DATABASE_PATH=data/yourdaddy.db

# Flask
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=another_random_secret_key

# Voice Recognition
PICOVOICE_API_KEY=your_picovoice_key

# Server
HOST=127.0.0.1
PORT=5000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

**Load Environment Variables:**

```python
# config.py
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # Server
    HOST = os.getenv('HOST', '127.0.0.1')
    PORT = int(os.getenv('PORT', 5000))
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    
    # Google API
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    
    # Spotify
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
    
    # Email
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    
    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/yourdaddy.db')
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Picovoice
    PICOVOICE_API_KEY = os.getenv('PICOVOICE_API_KEY')
    
    @classmethod
    def validate(cls):
        """Validate that required config is present"""
        required = [
            'SECRET_KEY',
            'JWT_SECRET_KEY',
            'GOOGLE_API_KEY',
        ]
        
        missing = []
        for key in required:
            if not getattr(cls, key):
                missing.append(key)
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

# Use in application
from config import Config

Config.validate()  # Check config on startup
app.config.from_object(Config)
```

---

### Issue #2: multimodal_config.json Duplicates .env 🟡
**File:** `multimodal_config.json`  
**Lines:** 1-30  
**Severity:** MODERATE

```json
{
  "gemini_api_key": "AIzaSyBqN0ooaSDpL8wOh9pv_X9nC7aVpXzZgHQ",
  "vision": {
    "enabled": true,
    "default_model": "gemini-2.0-flash-exp",
    "models": {...}
  }
}
```

**Problems:**
- Duplicates API key from .env
- Mixes config with secrets
- Harder to manage secrets separately

**Fix - Separate Concerns:**

```json
// multimodal_config.json - ONLY non-secret configuration
{
  "vision": {
    "enabled": true,
    "default_model": "gemini-2.0-flash-exp",
    "models": {
      "gemini-2.0-flash-exp": {
        "capabilities": ["vision", "text", "multimodal"],
        "max_tokens": 8192,
        "temperature": 0.7
      },
      "gemini-pro-vision": {
        "capabilities": ["vision", "text"],
        "max_tokens": 4096,
        "temperature": 0.4
      }
    },
    "image_formats": ["jpg", "jpeg", "png", "gif", "bmp"],
    "max_image_size_mb": 10
  },
  "audio": {
    "enabled": false,
    "models": []
  },
  "video": {
    "enabled": false,
    "models": []
  }
}
```

```python
# Load config properly
import json
from config import Config

def load_multimodal_config():
    """Load multimodal configuration"""
    with open('multimodal_config.json') as f:
        config = json.load(f)
    
    # Add API key from environment
    config['gemini_api_key'] = Config.GOOGLE_API_KEY
    
    return config
```

---

### Issue #3: requirements.txt Has Conflicts 🔴
**File:** `requirements.txt`  
**Lines:** Throughout  
**Severity:** HIGH

```txt
# Current requirements.txt
Flask
flask-socketio
flask-cors

# ❌ Version conflicts:
pywinauto  
pywin32==306  # Conflicts with some versions of pywinauto

# ❌ Duplicates:
SpeechRecognition
speechrecognition  # Same package, different case

# ❌ Missing:
- python-dotenv (for .env files)
- flask-jwt-extended (for auth)
- flask-limiter (for rate limiting)
```

**Already documented in Critical Issues - See:**
- [Critical Issues Report - Issue #6](01_CRITICAL_ISSUES.md#issue-6-requirementstxt-duplicate-dependencies)

---

### Issue #4: No Development vs Production Config 🟡
**Severity:** MODERATE

```python
# Currently same config for dev and production
# No way to switch between environments
```

**Fix - Add Environment-Specific Config:**

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY')
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/yourdaddy.db')
    
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Permissive CORS for local development
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5173']
    
    # Verbose logging
    LOG_LEVEL = 'DEBUG'
    
    # Use local server
    HOST = '127.0.0.1'
    PORT = 5000

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Strict CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',')
    
    # Less verbose logging
    LOG_LEVEL = 'INFO'
    
    # Production server settings
    HOST = '0.0.0.0'
    PORT = int(os.getenv('PORT', 5000))
    
    # Enable security features
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    
    # Use in-memory database for tests
    DATABASE_PATH = ':memory:'
    
    # Disable external API calls
    GOOGLE_API_KEY = 'test_key'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
```

```python
# modern_web_backend.py
from config import get_config

# Load appropriate config
app.config.from_object(get_config())
```

---

### Issue #5: No .gitignore - Secrets Could Be Committed 🔴
**File:** Missing  
**Severity:** CRITICAL SECURITY

```bash
# Currently no .gitignore
# Risk of committing:
# - .env files
# - API keys
# - Database files
# - User data
# - Credentials
```

**Fix - Create .gitignore:**

```gitignore
# .gitignore

# Environment variables
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
ENV/
env.bak/
venv.bak/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Database files
*.db
*.sqlite
*.sqlite3
data/yourdaddy.db

# Logs
*.log
logs/
yourdaddy_backend.log*
access.log*
error.log*

# User data
user_data/
conversations/
memory/

# Credentials & API keys
credentials.json
token.json
*_credentials.json
*_token.json

# OAuth tokens
.spotify_cache
spotify_token.json

# Model files (large)
model/vosk-model-*/*.mdl
model/vosk-model-*/final.*

# Temporary files
tmp/
temp/
*.tmp
*.bak

# OS files
Thumbs.db
.DS_Store

# Frontend
node_modules/
dist/
.next/
out/
build/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Documentation builds
docs/_build/
```

---

### Issue #6: package.json Missing Scripts 🟡
**File:** `project/package.json`  
**Severity:** LOW

```json
{
  "name": "yourdaddy-assistant",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview"
    // ❌ Missing useful scripts
  }
}
```

**Fix - Add Useful Scripts:**

```json
{
  "name": "yourdaddy-assistant",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "preview": "vite preview",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage",
    "format": "prettier --write \"src/**/*.{ts,tsx}\"",
    "format:check": "prettier --check \"src/**/*.{ts,tsx}\"",
    "type-check": "tsc --noEmit",
    "clean": "rm -rf dist node_modules",
    "reinstall": "npm run clean && npm install"
  },
  "devDependencies": {
    "@types/react": "^18.3.1",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.4",
    "eslint": "^9.17.0",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-react-refresh": "^0.4.16",
    "typescript": "~5.6.2",
    "vite": "^6.0.5",
    "vitest": "^1.0.0",
    "@vitest/ui": "^1.0.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "prettier": "^3.0.0"
  }
}
```

---

### Issue #7: No Configuration Validation 🟡
**Severity:** MODERATE

**Fix - Add Startup Validation:**

```python
# config.py
class Config:
    # ... existing config ...
    
    @classmethod
    def validate(cls):
        """Validate configuration on startup"""
        errors = []
        warnings = []
        
        # Check required variables
        required = {
            'SECRET_KEY': cls.SECRET_KEY,
            'JWT_SECRET_KEY': cls.JWT_SECRET_KEY,
            'GOOGLE_API_KEY': cls.GOOGLE_API_KEY,
        }
        
        for name, value in required.items():
            if not value:
                errors.append(f"❌ Missing required config: {name}")
        
        # Check optional but recommended
        recommended = {
            'SPOTIFY_CLIENT_ID': cls.SPOTIFY_CLIENT_ID,
            'EMAIL_ADDRESS': cls.EMAIL_ADDRESS,
            'PICOVOICE_API_KEY': cls.PICOVOICE_API_KEY,
        }
        
        for name, value in recommended.items():
            if not value:
                warnings.append(f"⚠️ Optional config missing: {name}")
        
        # Validate formats
        if cls.GOOGLE_API_KEY and not cls.GOOGLE_API_KEY.startswith('AIza'):
            errors.append("❌ Invalid Google API key format")
        
        if cls.PORT < 1024 or cls.PORT > 65535:
            errors.append(f"❌ Invalid port: {cls.PORT}")
        
        # Print results
        if errors:
            print("\n🔴 Configuration Errors:")
            for error in errors:
                print(f"  {error}")
            raise ValueError("Configuration validation failed")
        
        if warnings:
            print("\n⚠️ Configuration Warnings:")
            for warning in warnings:
                print(f"  {warning}")
        
        print("✅ Configuration validated successfully\n")
```

---

## 📋 Configuration Checklist

### Required Files
- [ ] `.env` - Environment variables (create from .env.example)
- [x] `.gitignore` - Prevent secret commits
- [x] `multimodal_config.json` - Multimodal settings
- [x] `requirements.txt` - Python deps (needs cleanup)
- [x] `package.json` - Frontend deps
- [ ] `.env.example` - Template for .env
- [ ] `config.py` - Centralized config management

### Setup Steps
```bash
# 1. Create .env from example
cp .env.example .env

# 2. Edit .env with your actual values
nano .env

# 3. Validate configuration
python -c "from config import Config; Config.validate()"

# 4. Install dependencies
pip install -r requirements.txt
cd project && npm install

# 5. Run application
python modern_web_backend.py
```

---

## 🔧 Fix Priority

### P0 - Critical (Day 1)
- [ ] Create `.env` file (1 hour)
- [ ] Create `.gitignore` (15 min)
- [ ] Create `.env.example` template (15 min)
- [ ] Create `config.py` (2 hours)

### P1 - High (Week 1)
- [ ] Fix `requirements.txt` conflicts (1 hour)
- [ ] Separate config from secrets (30 min)
- [ ] Add config validation (1 hour)
- [ ] Add environment-specific configs (2 hours)

### P2 - Medium (Week 2)
- [ ] Improve `package.json` scripts (1 hour)
- [ ] Create config documentation (2 hours)
- [ ] Add config tests (1 hour)

**Total Effort:** 6-8 hours

---

## 📚 Documentation Needed

### .env.example Template
```bash
# .env.example
# Copy this file to .env and fill in your actual values

# Google API
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret

# Spotify API
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_secret
SPOTIFY_REDIRECT_URI=http://localhost:5000/callback

# Email
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_16_char_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Security
JWT_SECRET_KEY=generate_with_python_secrets_token_hex_32
SECRET_KEY=another_random_secret_32_chars

# Database
DATABASE_PATH=data/yourdaddy.db

# Server
FLASK_ENV=development
HOST=127.0.0.1
PORT=5000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Voice
PICOVOICE_API_KEY=your_picovoice_access_key
```

---

**Priority:** 🔴 P0  
**Status:** Missing critical configuration files  
**Impact:** Blocks secure deployment

**Next Report:** [Dependency Issues →](07_DEPENDENCY_ISSUES.md)
