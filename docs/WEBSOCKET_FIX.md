# WebSocket Connection Fix

## Problem
`Invalid frame header` error when WebSocket tries to upgrade from polling.

## Root Cause
- Backend SocketIO: ✅ Working (verified with curl)
- Frontend trying WebSocket first: ❌ Failing on upgrade
- CORS credentials: ❌ Not set

## Solution
Changed connection options:

```typescript
io('http://localhost:5000', {
  withCredentials: true,          // ← CRITICAL for CORS
  transports: ['polling', 'websocket'],  // ← Try polling FIRST
  forceNew: true
})
```

## Why This Works
1. **Polling first** - Establishes connection reliably
2. **Then upgrades** - WebSocket upgrade happens after handshake
3. **withCredentials** - Allows CORS cookies/auth
4. **forceNew** - Prevents stale connection reuse

## Verification
After page refresh, console should show:
```
✅ Voice interface connected to backend on port 5000
Connected to WebSocket
Backend status: {...}
```

**No more "Invalid frame header" errors!**
