# 🔒 Security & Privacy Guide

## Overview
This document outlines the security measures and privacy protections implemented in the AI Assistant to prevent sensitive data exposure.

## 🚨 Protected Files (Never Committed to Git)

### User-Specific Configuration Files
These files contain personal data and are automatically excluded from version control:

1. **`config/discovered_apps.json`** - Your installed applications list
2. **`config/app_usage.db`** - Your application usage tracking database  
3. **`config/user_settings.json`** - Your personal preferences and settings
4. **`config/multimodal_config.json`** - API keys and voice configuration
5. **`ai_assistant/config/contacts.json`** - Phone numbers and contact information
6. **`config/app_integration.env`** - Application integration credentials
7. **All `*.db` files** - SQLite databases with personal data
8. **All `*.env` files** (except `.example` files) - Environment variables with secrets

### Auto-Generated Directories (Never Committed)
- **`data/`** - 30+ database files with learning history, chat logs, commands, etc.
- **`user_data/`** - User actions, queries, and replies logs
- **`logs/`** - Application logs that may contain PII
- **`offline_cache/`** - Cached data
- **`model/vosk-*`** - Large voice recognition models

## ✅ Safe to Commit (Example Files Only)

These template files are tracked in git and contain no personal data:
- `config/*.example` - Template configuration files
- `api_keys.json.example` - API key structure example
- Documentation and README files
- Source code files

## 🛠️ First-Time Setup

When you clone this repository on a new machine:

1. **Run the setup script** (automatically copies example files):
   ```bash
   python setup_config.py
   ```
   OR just start the app (auto-initializes):
   ```bash
   python main.py
   ```

2. **Configure your personal data**:
   - Edit `config/multimodal_config.json` - Add your API keys
   - Edit `ai_assistant/config/contacts.json` - Add your contacts
   - Edit `config/user_settings.json` - Customize your preferences
   - Create `config/app_integration.env` - Add integration credentials

3. **Your data stays local** - These files will never be pushed to GitHub

## 🔐 Security Best Practices

### For Developers
- ✅ Always use `.example` files for templates
- ✅ Update `.gitignore` before adding new config files
- ✅ Use `git ls-files` to verify nothing sensitive is tracked
- ✅ Review commits before pushing: `git diff --cached`
- ❌ Never commit files with real API keys, passwords, or personal data
- ❌ Never hardcode secrets in source code

### For Users
- ✅ Keep your `.env` and config files backed up locally
- ✅ Review your `.gitignore` if you fork this repo
- ✅ Use environment variables for sensitive data
- ❌ Don't share your `data/` or `config/` directories
- ❌ Don't commit personalized configuration files

## 🚀 Auto-Initialization

The application automatically:
1. Checks if config files exist on startup
2. Copies `.example` files to actual config files if missing
3. Scans for installed applications (stored locally only)
4. Creates databases as needed (never tracked in git)

## 🔍 Auditing Your Repository

To check for accidentally committed sensitive data:

```bash
# Check tracked files in sensitive directories
git ls-files | grep -E "(config|data|user_data|logs)/"

# Search for potential secrets in tracked files  
git ls-files -z | xargs -0 grep -E "(api_key|secret|password|token)" --include="*.py" --include="*.json"

# Check what's in your last commit
git show --name-only

# See file sizes in repo (detect large databases)
git count-objects -vH
```

## 📋 Vulnerability Checklist

- [x] Personal app list not committed (`discovered_apps.json`)
- [x] User preferences not committed (`user_settings.json`)
- [x] API keys protected (`multimodal_config.json`, `.env` files)
- [x] Contact information protected (`contacts.json`)
- [x] Database files ignored (`*.db`)
- [x] Log files ignored (`*.log`)
- [x] Cache directories ignored
- [x] User data directories ignored
- [x] Example files created for all sensitive configs
- [x] Auto-initialization implemented
- [x] Documentation updated

## 🆘 If You Accidentally Committed Sensitive Data

1. **Remove from git tracking** (keeps local file):
   ```bash
   git rm --cached path/to/sensitive/file
   ```

2. **Add to .gitignore**:
   ```bash
   echo "path/to/sensitive/file" >> .gitignore
   ```

3. **Commit the fix**:
   ```bash
   git add .gitignore
   git commit -m "security: Remove sensitive file from tracking"
   ```

4. **Remove from git history** (if already pushed):
   ```bash
   git filter-branch --force --index-filter \
   "git rm --cached --ignore-unmatch path/to/sensitive/file" \
   --prune-empty --tag-name-filter cat -- --all
   ```
   
   ⚠️ **Warning**: This rewrites history. Force push required: `git push origin --force --all`

5. **Rotate compromised secrets**: If API keys or passwords were exposed, rotate them immediately!

## 📞 Security Contact

If you discover a security vulnerability, please:
1. Do NOT open a public issue
2. Contact the maintainer privately
3. Provide details about the vulnerability
4. Allow time for a fix before public disclosure

## 🔄 Regular Maintenance

Periodically audit your repository:
- Run `git ls-files | grep -E "(json|db|env)$"` monthly
- Review `.gitignore` when adding new features
- Check for hardcoded secrets in code reviews
- Update this document when adding new config files

---

Last Updated: December 19, 2025
Version: 1.0
