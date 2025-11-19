# 📅 Calendar Module Analysis

**File:** `modules/calendar.py`  
**Lines:** 215  
**Status:** ❌ **COMPLETELY BROKEN**  
**Functionality:** 0%  
**Last Updated:** November 17, 2025

---

## 🐛 Critical Issues

### Issue #1: No OAuth Implementation 🔴
**Lines:** 28-45  
**Severity:** CRITICAL

```python
def __init__(self):
    self.service = None  # ❌ Never initialized
    # ❌ No OAuth flow
    # ❌ No credentials.json check
    # ❌ No token.json handling
```

**Fix:**
```python
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os.path
import pickle

SCOPES = ['https://www.googleapis.com/auth/calendar']

def __init__(self):
    self.service = self._authenticate()

def _authenticate(self):
    """Authenticate with Google Calendar API"""
    creds = None
    
    # Load existing credentials
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('calendar', 'v3', credentials=creds)
```

### Issue #2: All Methods Return Stubs 🔴

Every method returns stub responses:
```python
def create_event(self, summary, start_time, end_time):
    return "Event creation not implemented"  # ❌

def get_upcoming_events(self, max_results=10):
    return []  # ❌

def delete_event(self, event_id):
    return "Deletion not implemented"  # ❌
```

**Status:** Module is 0% functional

---

## ✅ Required Implementation

```python
def create_event(self, summary, start_time, end_time, description='', location=''):
    """Create calendar event"""
    try:
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {'dateTime': start_time, 'timeZone': 'America/Los_Angeles'},
            'end': {'dateTime': end_time, 'timeZone': 'America/Los_Angeles'},
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }
        
        event = self.service.events().insert(calendarId='primary', body=event).execute()
        return {'success': True, 'event_id': event['id'], 'link': event['htmlLink']}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_upcoming_events(self, max_results=10):
    """Get upcoming calendar events"""
    try:
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return [{
            'id': event['id'],
            'summary': event.get('summary', 'No title'),
            'start': event['start'].get('dateTime', event['start'].get('date')),
            'end': event['end'].get('dateTime', event['end'].get('date')),
            'location': event.get('location', ''),
            'description': event.get('description', '')
        } for event in events]
    except Exception as e:
        return []
```

---

## 🔧 Fix Priority

### P0 - Critical (Week 1) - 8 hours
- [ ] Implement OAuth authentication (3 hours)
- [ ] Implement create_event (1 hour)
- [ ] Implement get_upcoming_events (1 hour)
- [ ] Implement delete_event (1 hour)
- [ ] Implement update_event (1 hour)
- [ ] Error handling (1 hour)

### P1 - High (Week 2) - 4 hours
- [ ] Add recurring events (2 hours)
- [ ] Add reminders (1 hour)
- [ ] Write tests (1 hour)

**Total:** 12 hours

---

**Priority:** 🔴 P0  
**Impact:** Complete feature missing

**Next:** [Email Module →](EMAIL_MODULE.md)
