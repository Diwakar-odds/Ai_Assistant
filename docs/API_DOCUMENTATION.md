# YourDaddy Assistant - API Documentation

## Overview
The YourDaddy Assistant Web Backend provides a RESTful API and WebSocket interface for real-time communication with the AI assistant.

**Base URL:** `http://localhost:5000`  
**WebSocket URL:** `ws://localhost:5000`

---

## Authentication

All protected endpoints require JWT Bearer token authentication.

### Register New User
**POST** `/api/auth/register`

Creates a new user account.

**Request Body:**
```json
{
  "username": "string (3-20 characters, alphanumeric + underscore)",
  "password": "string (minimum 6 characters)"
}
```

**Response (201 Created):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user": {
    "username": "johndoe",
    "role": "user"
  },
  "message": "Registration successful"
}
```

**Rate Limit:** 3 requests per hour

---

### Login
**POST** `/api/auth/login`

Authenticate with username and password.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response (200 OK):**
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

**Error Response (401 Unauthorized):**
```json
{
  "error": "Invalid credentials"
}
```

**Rate Limit:** 5 requests per minute

---

### Verify Token
**GET** `/api/auth/verify`

Verify JWT token validity.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "valid": true,
  "user": {
    "username": "admin",
    "role": "admin"
  }
}
```

---

## System Status

### Get API Status
**GET** `/api/status`

Check API availability and service status (public endpoint).

**Response (200 OK):**
```json
{
  "status": "online",
  "timestamp": "2025-11-17T12:34:56.789Z",
  "authenticated": false,
  "services": {
    "automation": true,
    "multimodal": true,
    "conversational_ai": true,
    "voice": true,
    "system_monitoring": true
  }
}
```

---

## Commands

### Execute Command
**POST** `/api/command`

Process a text command through the AI assistant.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "command": "string (max 1000 characters)"
}
```

**Response (200 OK):**
```json
{
  "command": "open chrome",
  "response": "Opening Google Chrome...",
  "user": "admin",
  "timestamp": "2025-11-17T12:34:56.789Z"
}
```

**Rate Limit:** 30 requests per minute

---

## System Monitoring

### Get System Statistics
**GET** `/api/system/stats`

Retrieve real-time system performance metrics.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "timestamp": "2025-11-17T12:34:56.789Z",
  "cpu_usage": 45.2,
  "memory_usage": 67.8,
  "disk_usage": 52.3,
  "network_mbps": 12.5,
  "active_tasks": 156,
  "temperature": "N/A"
}
```

**Rate Limit:** 60 requests per minute  
**Cache:** 2 seconds

---

## Applications

### List Installed Applications
**GET** `/api/apps`

Get list of installed applications on the system.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
[
  {
    "name": "Chrome",
    "path": "chrome.exe",
    "category": "Browser",
    "usage": 89
  },
  {
    "name": "Code",
    "path": "code.exe",
    "category": "Development",
    "usage": 92
  }
]
```

**Rate Limit:** 30 requests per minute

---

### Launch Application
**POST** `/api/apps/launch`

Launch an installed application.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "app_name": "chrome"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Launched chrome successfully",
  "app_name": "chrome",
  "user": "admin"
}
```

**Rate Limit:** 20 requests per minute

---

## Spotify Integration

### Get Spotify Status
**GET** `/api/spotify/status`

Get current Spotify playback status.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "is_playing": true,
  "track": "Song Title",
  "artist": "Artist Name",
  "album": "Album Name",
  "progress": "2:15",
  "duration": "3:45"
}
```

**Rate Limit:** 30 requests per minute

---

### Spotify Play/Pause
**POST** `/api/spotify/play-pause`

Toggle Spotify playback.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Playback toggled"
}
```

**Rate Limit:** 20 requests per minute

---

### Spotify Next Track
**POST** `/api/spotify/next`

Skip to next track.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Skipped to next track"
}
```

**Rate Limit:** 20 requests per minute

---

### Spotify Previous Track
**POST** `/api/spotify/previous`

Go to previous track.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Returned to previous track"
}
```

**Rate Limit:** 20 requests per minute

---

## WebSocket Events

### Connect
**Event:** `connect`

Emitted when WebSocket connection is established.

**Server Response:**
```json
{
  "status": "connected",
  "message": "Welcome to YourDaddy Assistant WebSocket",
  "timestamp": "2025-11-17T12:34:56.789Z"
}
```

---

### Send Command
**Event:** `command`

Send command through WebSocket for real-time processing.

**Client Payload:**
```json
{
  "command": "what's the weather"
}
```

**Server Response (command_response):**
```json
{
  "response": "The weather is sunny, 72°F",
  "timestamp": "2025-11-17T12:34:56.789Z"
}
```

---

### Request System Stats
**Event:** `request_system_stats`

Request real-time system statistics.

**Server Response (system_stats):**
```json
{
  "timestamp": "2025-11-17T12:34:56.789Z",
  "cpu_usage": 45.2,
  "memory_usage": 67.8,
  "disk_usage": 52.3,
  "network_mbps": 12.5,
  "active_tasks": 156
}
```

---

### Start Voice Listening
**Event:** `start_voice_listening`

Start voice recognition session.

**Server Response (voice_start_response):**
```json
{
  "status": "listening",
  "message": "Voice recognition started"
}
```

**Voice Status Updates (voice_status):**
```json
{
  "listening": true
}
```

**Voice Transcript (voice_transcript):**
```json
{
  "text": "open chrome"
}
```

**Voice Response (voice_response):**
```json
{
  "text": "recognized command",
  "response": "Opening Chrome..."
}
```

---

## Error Responses

All endpoints may return error responses in this format:

**400 Bad Request:**
```json
{
  "error": "command is required"
}
```

**401 Unauthorized:**
```json
{
  "msg": "Missing Authorization Header"
}
```

**429 Too Many Requests:**
```json
{
  "error": "Rate limit exceeded"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Command processing failed"
}
```

---

## Rate Limits

- **Authentication:** 5 login attempts per minute, 3 registrations per hour
- **Commands:** 30 requests per minute
- **System Stats:** 60 requests per minute
- **Applications:** 20-30 requests per minute
- **Music Controls:** 20 requests per minute
- **Weather:** 20 requests per minute

---

## Security

1. All protected endpoints require JWT Bearer token
2. Tokens expire after 24 hours
3. Rate limiting prevents abuse
4. Input validation prevents injection attacks
5. CORS restricted to allowed origins
6. Command sanitization removes dangerous characters

---

## Example Usage

### Python Example
```python
import requests

# Login
response = requests.post('http://localhost:5000/api/auth/login', json={
    'username': 'admin',
    'password': 'changeme123'
})
token = response.json()['access_token']

# Execute command
headers = {'Authorization': f'Bearer {token}'}
response = requests.post('http://localhost:5000/api/command', 
    headers=headers,
    json={'command': 'open chrome'}
)
print(response.json())
```

### JavaScript/TypeScript Example
```typescript
// Login
const loginResponse = await fetch('http://localhost:5000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'admin', password: 'changeme123' })
});
const { access_token } = await loginResponse.json();

// Execute command
const commandResponse = await fetch('http://localhost:5000/api/command', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ command: 'open chrome' })
});
const result = await commandResponse.json();
console.log(result);
```

---

## Support

For issues or questions, please refer to the project documentation or submit an issue on GitHub.
