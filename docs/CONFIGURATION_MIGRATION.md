# Configuration Migration Guide

## Overview

Pulsar AI Assistant now uses `.env` files for configuration instead of `api_keys.json`. This provides:
- ✅ Better security (`.env` is gitignored by default)
- ✅ Standard industry practice
- ✅ Easier deployment across environments
- ✅ Centralized configuration management

## Quick Start

### 1. Create your `.env` file

```bash
# Copy the template
cp .env.template .env
```

### 2. Fill in your API keys

Edit `.env` and add your actual API keys:

```env
GOOGLE_GEMINI_API_KEY=your_actual_key_here
OPENAI_API_KEY=your_actual_key_here
```

### 3. Generate security keys

Generate random keys for encryption:

```bash
# On Linux/Mac
openssl rand -hex 32

# On Windows (PowerShell)
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

Add these to your `.env`:

```env
SECRET_KEY=generated_key_here
JWT_SECRET_KEY=another_generated_key_here
DATABASE_ENCRYPTION_KEY=another_generated_key_here
```

## Usage in Code

### Old Way (api_keys.json):
```python
import json

with open('api_keys.json') as f:
    keys = json.load(f)
    
gemini_key = keys['gemini_api_key']
```

### New Way (.env):
```python
from ai_assistant.core.config_loader import get_config

config = get_config()
gemini_key = config['GOOGLE_GEMINI_API_KEY']

# Or with default value
openai_key = config.get('OPENAI_API_KEY', 'default_value')
```

## Available Configuration Values

See `.env.template` for all available options.

**Main categories:**
- AI API Keys (Gemini, OpenAI, Google Cloud)
- Security keys (SECRET_KEY, JWT_SECRET_KEY, etc.)
- Feature flags (ENABLE_VOICE, ENABLE_MULTIMODAL, etc.)
- API rate limits
- Backend configuration
- Paths

## Security Best Practices

1. **Never commit `.env` to git**
   - Already in `.gitignore`
   
2. **Use different keys for development/production**
   - Create `.env.dev` and `.env.prod`
   
3. **Rotate keys regularly**
   - Especially if they may have been exposed

4. **Use strong passwords**
   - For ADMIN_PASSWORD, use at least 12 characters

## Migration from api_keys.json

If you have an existing `api_keys.json`:

1. Copy values to `.env`:
   ```env
   GOOGLE_GEMINI_API_KEY=<value from json>
   OPENAI_API_KEY=<value from json>
   ```

2. **Delete or backup `api_keys.json`**
   ```bash
   mv api_keys.json api_keys.json.backup
   ```

3. Update any custom code that loads `api_keys.json` to use `config_loader`

## Troubleshooting

### "Configuration key not found"

Make sure the key exists in your `.env` file and is not commented out.

### "No AI API keys configured"

You need at least one of:
- `GOOGLE_GEMINI_API_KEY`
- `OPENAI_API_KEY`

### ".env file not found"

The `.env` file should be in the project root (same directory as `main.py`).

If it's elsewhere, specify the path:
```python
from ai_assistant.core.config_loader import load_config
from pathlib import Path

config = load_config(Path('/custom/path/.env'))
```

## Testing Configuration

Test that your configuration loads correctly:

```bash
python -m ai_assistant.core.config_loader
```

This will show:
- Whether `.env` was found
- Which API keys are configured (masked)
- Current backend port and settings

## Environment-Specific Configurations

For different environments, create separate files:

- `.env` - Default/development
- `.env.production` - Production settings
- `.env.test` - Test environment

Load specific environment:

```python
from ai_assistant.core.config_loader import load_config
from pathlib import Path

config = load_config(Path('.env.production'))
```

---

**Questions?** Check the `.env.template` for detailed comments on each setting.
