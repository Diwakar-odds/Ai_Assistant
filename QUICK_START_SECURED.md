# 🚀 Quick Start Guide - Secured YourDaddy Assistant

## Prerequisites

1. Python 3.8 or higher installed
2. All dependencies from requirements.txt

## Installation Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Environment File

```bash
# Copy the example environment file
cp .env.example .env
```

### 3. Generate Secure Keys

Run this Python script to generate secure keys:

```python
import secrets

print("Add these to your .env file:")
print(f"SECRET_KEY={secrets.token_hex(32)}")
print(f"JWT_SECRET_KEY={secrets.token_hex(32)}")
```

### 4. Edit .env File

Open `.env` and update:

```bash
# Security Configuration
SECRET_KEY=<paste-generated-key-here>
JWT_SECRET_KEY=<paste-generated-key-here>
ADMIN_PASSWORD=YourStrongPassword123!  # CHANGE THIS!

# Server Configuration (defaults are fine for local use)
HOST=127.0.0.1
PORT=5000
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5000,http://127.0.0.1:3000,http://127.0.0.1:5000
```

### 5. Start the Server

```bash
python modern_web_backend.py
```

You should see:

```
🚀 YourDaddy Assistant - Modern Web Backend
============================================================
🌐 Server starting on: http://localhost:5000
📱 React frontend will be served automatically
⚡ Real-time features enabled via WebSockets
🔧 API endpoints available at /api/*
🔒 Security: JWT authentication enabled
🔒 Security: Rate limiting enabled
🔒 Security: CORS restricted to: http://localhost:3000, ...
🔒 Security: Host binding: 127.0.0.1
🛑 Press Ctrl+C to stop the server
============================================================
```

## Using the API

### 1. Login to Get Token

```bash
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"YourStrongPassword123!"}'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user": {
    "username": "admin",
    "role": "admin"
  }
}
```

### 2. Use the Token for API Calls

```bash
# Set your token
TOKEN="<your-access-token-here>"

# Make authenticated requests
curl -X POST http://127.0.0.1:5000/api/command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"command":"open notepad"}'
```

### 3. Check System Stats

```bash
curl -X GET http://127.0.0.1:5000/api/system/stats \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Launch Applications

```bash
curl -X POST http://127.0.0.1:5000/api/apps/launch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"app_name":"chrome"}'
```

## Frontend Integration

### React Example

```javascript
// Login
const login = async (username, password) => {
  const response = await fetch('http://127.0.0.1:5000/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  });
  
  const data = await response.json();
  localStorage.setItem('token', data.access_token);
  return data;
};

// Make authenticated request
const sendCommand = async (command) => {
  const token = localStorage.getItem('token');
  
  const response = await fetch('http://127.0.0.1:5000/api/command', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ command }),
  });
  
  return await response.json();
};
```

## Security Features

### ✅ What's Protected

- **JWT Authentication**: All sensitive endpoints require valid token
- **Rate Limiting**: Prevents abuse (5 login attempts/minute, 30 commands/minute)
- **Input Validation**: All inputs sanitized and validated
- **Command Injection Protection**: Safe execution methods used
- **CORS**: Restricted to specified origins only
- **Localhost Binding**: Server only accessible from local machine

### ⚠️ Important Security Notes

1. **Change the default password** in `.env` immediately
2. **Keep your tokens secret** - never share or commit them
3. **Tokens expire after 24 hours** - you'll need to login again
4. **Never expose the server to the internet** without proper security (HTTPS, firewall)
5. **For production**, use a reverse proxy (nginx) with HTTPS

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Login | 5 per minute |
| Commands | 30 per minute |
| System Stats | 60 per minute |
| Weather | 20 per minute |
| App Launch | 20 per minute |
| Screen Analysis | 10 per minute |
| Voice Operations | 10-20 per minute |

## Troubleshooting

### "Invalid credentials" Error
- Check your username and password in `.env`
- Default username is `admin`

### "Unauthorized" Error
- Token expired (24 hours) - login again
- Invalid token - login again
- Missing Authorization header

### "Too Many Requests" Error
- You hit the rate limit
- Wait a minute and try again

### "CORS Error" in Browser
- Check `ALLOWED_ORIGINS` in `.env`
- Make sure your frontend URL is listed

### Server Won't Start
- Check if port 5000 is already in use
- Install missing dependencies: `pip install -r requirements.txt`
- Check Python version (3.8+)

## Testing the Security

### Test Input Validation

```bash
# This should be blocked (dangerous characters)
curl -X POST http://127.0.0.1:5000/api/command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"command":"test; rm -rf /"}'
```

### Test Rate Limiting

```bash
# Make rapid requests - should get blocked
for i in {1..10}; do
  curl -X POST http://127.0.0.1:5000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"wrong"}'
done
```

### Test Authentication

```bash
# This should fail without token
curl -X POST http://127.0.0.1:5000/api/command \
  -H "Content-Type: application/json" \
  -d '{"command":"test"}'
```

## Next Steps

1. ✅ Server is secured and running
2. Build/update React frontend with authentication
3. Test all endpoints with JWT
4. Add user management if needed
5. Deploy with HTTPS for production

## Need Help?

Check the documentation:
- `SECURITY_FIXES_COMPLETE.md` - Full security implementation details
- `02_SECURITY_ISSUES.md` - Original security audit
- `10_FIX_ROADMAP.md` - Complete fix roadmap

---

**Status:** ✅ Security hardened and ready for development

**Version:** 1.0 (November 17, 2025)
