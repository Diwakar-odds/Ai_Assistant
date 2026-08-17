# PIN Authentication System for YourDaddy AI Assistant

Your AI Assistant now features a secure PIN authentication system that replaces traditional login pages. This system requires a PIN to be entered every time the assistant starts, providing better security and a simpler authentication experience.

## 🔐 Features

- **PIN-based authentication**: Simple numeric PIN instead of username/password
- **Secure storage**: PIN is hashed using PBKDF2 with salt for security
- **Automatic setup**: First-time users are guided through PIN setup
- **Easy management**: Change or test PIN anytime with built-in utilities
- **Failed attempt protection**: Limited attempts prevent brute force attacks
- **Cross-platform**: Works on Windows, Linux, and macOS

## 🚀 Quick Start

### First Time Setup

1. **Start the assistant normally:**
   ```bash
   # Windows
   start.bat app
   
   # Linux/macOS
   ./start.sh app
   ```

2. **Set up your PIN when prompted:**
   - You'll be asked to create a 4+ digit PIN
   - PIN must contain only numbers
   - Confirm your PIN to complete setup

3. **Start using the assistant:**
   - Enter your PIN each time you start the assistant
   - The assistant will start normally after successful authentication

### Manual PIN Setup

You can also set up or change your PIN manually:

```bash
# Using the dedicated PIN utility
python setup_pin.py

# Using the main application
python main.py --setup-pin

# Using start scripts
start.bat setup-pin    # Windows
./start.sh setup-pin   # Linux/macOS
```

## 📋 PIN Requirements

- **Minimum length**: 4 digits
- **Character type**: Numbers only (0-9)
- **Security**: Should be memorable but not obvious
- **Examples**: 1234 ❌ (too obvious), 2847 ✅, 9512 ✅

## 🔧 Usage Examples

### Starting the Assistant

```bash
# Desktop interface (requires PIN)
python main.py --interface desktop

# Web interface (requires PIN)
python main.py --interface web

# CLI interface (requires PIN)
python main.py --interface cli
```

### PIN Management

```bash
# Setup new PIN
python setup_pin.py

# Change existing PIN
python setup_pin.py

# Test current PIN
python setup_pin.py
```

### Development Mode

```bash
# Skip authentication for development
python main.py --skip-auth --interface cli

# Debug mode (no authentication)
start.bat debug    # Windows
./start.sh debug   # Linux/macOS
```

## 📁 File Structure

The PIN authentication system consists of:

```
ai_assistant/
└── auth/
    ├── __init__.py           # Auth module exports
    └── pin_auth.py           # Main PIN authentication class
setup_pin.py                  # Standalone PIN setup utility
main.py                       # Updated with PIN authentication
config/
└── app_integration.env       # PIN hash and salt stored here
```

## 🔒 Security Features

### PIN Hashing
- Uses PBKDF2-HMAC-SHA256 with 100,000 iterations
- Random 32-byte salt for each PIN
- Hash and salt stored separately in config file

### Failed Attempt Protection
- Maximum 3 authentication attempts per session
- Graceful handling of authentication failures
- Secure logging of authentication events

### Configuration Security
- PIN never stored in plain text
- Salt prevents rainbow table attacks
- Environment file can be secured with file permissions

## 🛠️ Configuration

### Environment Variables

The PIN system adds these variables to `config/app_integration.env`:

```bash
# PIN Authentication (auto-generated)
PIN_HASH=<secure_hash>
PIN_SALT=<random_salt>
```

### Start Script Options

Updated start scripts include new options:

```bash
# Windows (start.bat)
start.bat setup-pin    # PIN management
start.bat debug        # Skip authentication

# Linux/macOS (start.sh)
./start.sh setup-pin   # PIN management
./start.sh debug       # Skip authentication
```

## 🔍 Troubleshooting

### PIN Not Working
1. Ensure you're entering the correct PIN
2. Check if caps lock affects number input
3. Reset PIN using `python setup_pin.py`

### Setup Issues
1. Verify Python environment is activated
2. Check file permissions on config directory
3. Run setup with administrator/sudo if needed

### Import Errors
1. Ensure all dependencies are installed: `pip install -r requirements.txt`
2. Check Python path includes project directory
3. Activate virtual environment if used

### Configuration Problems
1. Check `config/app_integration.env` exists
2. Verify PIN_HASH and PIN_SALT are present
3. Re-run PIN setup if config is corrupted

## 🔄 Migrating from Old System

If you're upgrading from a previous version:

1. **Backup your current config** (optional but recommended)
2. **Run the PIN setup**: `python setup_pin.py`
3. **Test authentication**: Start the assistant normally
4. **Update start scripts**: Use new `setup-pin` option

The PIN system works alongside existing authentication without conflicts.

## 📚 Advanced Usage

### Programmatic Access

You can use the PIN authentication in your own scripts:

```python
from ai_assistant.auth import PINAuth

# Initialize PIN authentication
auth = PINAuth()

# Check if PIN is configured
if not auth.is_pin_configured():
    print("Please set up a PIN first")
    exit(1)

# Prompt for PIN
if auth.prompt_for_pin():
    print("Authentication successful!")
    # Your code here
else:
    print("Authentication failed!")
    exit(1)
```

### Custom Configuration Path

```python
# Use custom config file
auth = PINAuth(config_file="custom/path/to/config.env")
```

### Batch Operations

```bash
# Setup PIN non-interactively (for scripts)
echo "1234" | python setup_pin.py

# Test authentication in scripts
python -c "from ai_assistant.auth import authenticate; exit(0 if authenticate() else 1)"
```

## 🆘 Support

If you encounter issues with the PIN authentication system:

1. Check the troubleshooting section above
2. Review logs in `logs/security/` directory
3. Reset PIN using `python setup_pin.py`
4. Contact support with specific error messages

## 🔒 Security Best Practices

1. **Choose a strong PIN**: Avoid obvious patterns like 1234, 0000
2. **Keep PIN private**: Don't share with others
3. **Regular updates**: Change PIN periodically
4. **Secure storage**: Protect config files with appropriate permissions
5. **Monitor logs**: Check security logs for unauthorized attempts

---

**Note**: This PIN authentication system provides basic security for personal use. For enterprise environments, consider implementing additional security measures like two-factor authentication or integration with corporate authentication systems.