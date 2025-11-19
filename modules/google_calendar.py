# Google Calendar Integration Module
"""
Google Calendar integration for scheduling and event management
in the YourDaddy AI Assistant.

Provides:
- OAuth2 authentication with Google Calendar API
- Create, read, update, delete calendar events
- Search events
- Get today's schedule and upcoming events
"""

import os
import datetime
import pickle
import json
from pathlib import Path
from typing import Optional, Dict, List
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Calendar scope for read/write access
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Default timezone (can be configured)
DEFAULT_TIMEZONE = 'America/New_York'


class CalendarManager:
    """
    Manages Google Calendar API authentication and operations
    """
    
    _instance = None  # Singleton instance
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CalendarManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.service = None
        self.credentials_path = Path('credentials.json')
        self.token_path = Path('calendar_token.pickle')
        self._initialized = True
    
    def setup_auth(self) -> str:
        """
        Sets up Google Calendar authentication
        Returns status message
        """
        try:
            creds = None
            
            # Load existing credentials
            if self.token_path.exists():
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        # Token refresh failed, need to re-authenticate
                        creds = None
                
                if not creds:
                    if not self.credentials_path.exists():
                        return self._get_setup_instructions()
                    
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            str(self.credentials_path), SCOPES)
                        creds = flow.run_local_server(port=0)
                    except Exception as e:
                        return f"❌ Authentication failed: {str(e)}"
                
                # Save credentials for next run
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
            
            # Build the service
            self.service = build('calendar', 'v3', credentials=creds)
            
            # Test the service
            calendar_list = self.service.calendarList().get(calendarId='primary').execute()
            calendar_name = calendar_list.get('summary', 'Primary Calendar')
            
            return f"✅ Google Calendar authenticated successfully!\n📅 Connected to: {calendar_name}"
        
        except HttpError as e:
            return f"❌ Google Calendar API error: {str(e)}"
        except Exception as e:
            return f"❌ Calendar authentication error: {str(e)}"
    
    def _get_setup_instructions(self) -> str:
        """Returns setup instructions for Google Calendar API"""
        return """❌ Google Calendar not configured: 'credentials.json' not found.

🔧 Setup Instructions:

1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Create a new project or select an existing one
3. Enable Google Calendar API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as application type
   - Give it a name (e.g., "YourDaddy Assistant")
5. Download the credentials:
   - Click the download button (⬇️) next to your OAuth client
   - Save as 'credentials.json' in the project root folder
6. Run the setup again

Note: You'll need to add yourself as a test user if your app is in testing mode.
"""
    
    def get_service(self):
        """
        Get authenticated calendar service, initialize if needed
        """
        if self.service is None:
            result = self.setup_auth()
            if "❌" in result:
                return None
        return self.service
    
    def is_authenticated(self) -> bool:
        """Check if calendar is authenticated"""
        if self.service is None:
            service = self.get_service()
            return service is not None
        return True


def setup_calendar_auth() -> str:
    """
    Sets up Google Calendar authentication. Returns status message.
    User needs to run this once to authenticate.
    """
    print("--- 'Hands' (setup_calendar_auth) activated ---")
    manager = CalendarManager()
    return manager.setup_auth()

def get_calendar_service():
    """Helper function to get authenticated calendar service."""
    manager = CalendarManager()
    return manager.get_service()


def get_upcoming_events(days_ahead: int = 7) -> str:
    """
    Gets upcoming calendar events for the next N days.
    :param days_ahead: Number of days to look ahead (default 7)
    """
    print(f"--- 'Hands' (get_upcoming_events) activated. Days ahead: {days_ahead} ---")
    try:
        service = get_calendar_service()
        if not service:
            return "❌ Calendar not authenticated. Please run 'setup calendar' first."
        
        # Validate input
        days_ahead = max(1, min(365, days_ahead))
        
        # Get events for the next N days
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        future = (datetime.datetime.utcnow() + datetime.timedelta(days=days_ahead)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=now, 
            timeMax=future,
            maxResults=50, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"📅 No upcoming events in the next {days_ahead} days."
        
        events_report = f"📅 UPCOMING EVENTS (Next {days_ahead} days)\n"
        events_report += "━" * 80 + "\n"
        
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            
            # Format the date/time
            if 'T' in start:  # DateTime event
                dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%m/%d %I:%M %p")
            else:  # All-day event
                dt = datetime.datetime.fromisoformat(start)
                formatted_time = dt.strftime("%m/%d (All day)")
            
            summary = event.get('summary', 'No title')
            location = event.get('location', '')
            
            events_report += f"🗓️  {formatted_time} - {summary}"
            if location:
                events_report += f" 📍 {location}"
            events_report += "\n"
        
        return events_report
        
    except HttpError as e:
        return f"❌ Google Calendar API error: {str(e)}"
    except Exception as e:
        return f"❌ Error getting calendar events: {str(e)}"

def create_calendar_event(title: str, date: str, time: str = "", duration_hours: int = 1, description: str = "", location: str = "") -> str:
    """
    Creates a new calendar event.
    :param title: Event title
    :param date: Date in format 'YYYY-MM-DD' or 'MM/DD/YYYY'
    :param time: Time in format 'HH:MM' (24-hour) or 'HH:MM AM/PM' (optional for all-day)
    :param duration_hours: Event duration in hours (default 1)
    :param description: Event description (optional)
    :param location: Event location (optional)
    """
    print(f"--- 'Hands' (create_calendar_event) activated. Title: {title}, Date: {date} ---")
    try:
        service = get_calendar_service()
        if not service:
            return "❌ Calendar not authenticated. Please run 'setup calendar' first."
        
        # Parse date
        try:
            if '/' in date:  # MM/DD/YYYY format
                parts = date.split('/')
                if len(parts) == 3:
                    month, day, year = parts
                    date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                else:
                    return f"❌ Invalid date format: {date}. Use 'YYYY-MM-DD' or 'MM/DD/YYYY'"
        except Exception as e:
            return f"❌ Error parsing date '{date}': {str(e)}"
        
        # Create event object
        event_body = {
            'summary': title,
            'description': description,
        }
        
        if location:
            event_body['location'] = location
        
        if time:  # Timed event
            try:
                # Parse time
                if 'AM' in time.upper() or 'PM' in time.upper():
                    start_time = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %I:%M %p")
                else:
                    start_time = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
                
                end_time = start_time + datetime.timedelta(hours=duration_hours)
                
                event_body.update({
                    'start': {
                        'dateTime': start_time.isoformat(),
                        'timeZone': DEFAULT_TIMEZONE,
                    },
                    'end': {
                        'dateTime': end_time.isoformat(),
                        'timeZone': DEFAULT_TIMEZONE,
                    },
                    'reminders': {
                        'useDefault': False,
                        'overrides': [
                            {'method': 'popup', 'minutes': 10},
                            {'method': 'email', 'minutes': 60},
                        ],
                    },
                })
            except ValueError as e:
                return f"❌ Invalid time format: {time}. Use 'HH:MM' or 'HH:MM AM/PM'"
        else:  # All-day event
            event_body.update({
                'start': {'date': date},
                'end': {'date': date}
            })
        
        # Create the event
        event = service.events().insert(calendarId='primary', body=event_body).execute()
        event_link = event.get('htmlLink', '')
        
        result = f"✅ Calendar event created: '{title}' on {date}"
        if time:
            result += f" at {time}"
        else:
            result += " (all day)"
        if event_link:
            result += f"\n🔗 {event_link}"
        
        return result
        
    except HttpError as e:
        return f"❌ Google Calendar API error: {str(e)}"
    except Exception as e:
        return f"❌ Error creating calendar event: {str(e)}"

def get_todays_schedule() -> str:
    """
    Gets today's calendar schedule with a nice formatted view.
    """
    print("--- 'Hands' (get_todays_schedule) activated ---")
    try:
        service = get_calendar_service()
        if not service:
            return "❌ Calendar not authenticated. Please run 'setup calendar' first."
        
        # Get today's events
        today = datetime.date.today()
        start_of_day = datetime.datetime.combine(today, datetime.time.min).isoformat() + 'Z'
        end_of_day = datetime.datetime.combine(today, datetime.time.max).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=start_of_day, 
            timeMax=end_of_day,
            maxResults=50, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"📅 No events scheduled for today ({today.strftime('%A, %B %d, %Y')})."
        
        schedule_report = f"📅 TODAY'S SCHEDULE - {today.strftime('%A, %B %d, %Y')}\n"
        schedule_report += "━" * 80 + "\n"
        
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            
            if 'T' in start:
                dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%I:%M %p")
            else:
                formatted_time = "All day"
            
            summary = event.get('summary', 'No title')
            location = event.get('location', '')
            
            schedule_report += f"🕐 {formatted_time.ljust(8)} - {summary}"
            if location:
                schedule_report += f" 📍 {location}"
            schedule_report += "\n"
        
        return schedule_report
        
    except HttpError as e:
        return f"❌ Google Calendar API error: {str(e)}"
    except Exception as e:
        return f"❌ Error getting today's schedule: {str(e)}"

def search_calendar_events(query: str, days_back: int = 30, days_ahead: int = 30) -> str:
    """
    Searches for calendar events containing the query.
    :param query: Search term to look for in event titles and descriptions
    :param days_back: How many days back to search (default 30)
    :param days_ahead: How many days ahead to search (default 30)
    """
    print(f"--- 'Hands' (search_calendar_events) activated. Query: {query} ---")
    try:
        service = get_calendar_service()
        if not service:
            return "❌ Calendar not authenticated. Please run 'setup calendar' first."
        
        # Validate input
        days_back = max(0, min(365, days_back))
        days_ahead = max(0, min(365, days_ahead))
        
        # Search in time range
        past = (datetime.datetime.utcnow() - datetime.timedelta(days=days_back)).isoformat() + 'Z'
        future = (datetime.datetime.utcnow() + datetime.timedelta(days=days_ahead)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=past, 
            timeMax=future,
            q=query, 
            maxResults=50, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"📅 No events found matching '{query}' in the specified time range."
        
        search_report = f"🔍 CALENDAR SEARCH RESULTS for '{query}'\n"
        search_report += "━" * 80 + "\n"
        
        for event in events[:10]:  # Limit to top 10 results
            start = event['start'].get('dateTime', event['start'].get('date'))
            
            if 'T' in start:
                dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%m/%d/%Y %I:%M %p")
            else:
                dt = datetime.datetime.fromisoformat(start)
                formatted_time = dt.strftime("%m/%d/%Y (All day)")
            
            summary = event.get('summary', 'No title')
            search_report += f"📅 {formatted_time} - {summary}\n"
        
        if len(events) > 10:
            search_report += f"\n... and {len(events) - 10} more results"
        
        return search_report
        
    except HttpError as e:
        return f"❌ Google Calendar API error: {str(e)}"
    except Exception as e:
        return f"❌ Error searching calendar: {str(e)}"

def delete_calendar_event(event_title: str, date: str = "") -> str:
    """
    Deletes a calendar event by title and optional date.
    :param event_title: Title of the event to delete
    :param date: Optional date to narrow down search (YYYY-MM-DD or MM/DD/YYYY)
    """
    print(f"--- 'Hands' (delete_calendar_event) activated. Event: {event_title} ---")
    try:
        service = get_calendar_service()
        if not service:
            return "❌ Calendar not authenticated. Please run 'setup calendar' first."
        
        # Search for the event
        if date:
            try:
                if '/' in date:  # MM/DD/YYYY format
                    parts = date.split('/')
                    if len(parts) == 3:
                        month, day, year = parts
                        search_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    else:
                        return f"❌ Invalid date format: {date}"
                else:
                    search_date = date
                
                # Search on specific date
                time_min = f"{search_date}T00:00:00Z"
                time_max = f"{search_date}T23:59:59Z"
                
                events_result = service.events().list(
                    calendarId='primary', 
                    timeMin=time_min, 
                    timeMax=time_max,
                    q=event_title, 
                    singleEvents=True
                ).execute()
            except Exception as e:
                return f"❌ Error parsing date '{date}': {str(e)}"
        else:
            # Search in next 30 days
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            future = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary', 
                timeMin=now, 
                timeMax=future,
                q=event_title, 
                singleEvents=True
            ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"❌ No events found with title '{event_title}'"
        
        if len(events) > 1:
            event_list = "\n".join([
                f"  • {e.get('summary', 'No title')} on {e['start'].get('dateTime', e['start'].get('date'))[:10]}"
                for e in events[:5]
            ])
            return f"❌ Multiple events found with title '{event_title}'. Please specify a date:\n{event_list}"
        
        # Delete the event
        event = events[0]
        service.events().delete(calendarId='primary', eventId=event['id']).execute()
        
        return f"✅ Successfully deleted calendar event: '{event_title}'"
        
    except HttpError as e:
        return f"❌ Google Calendar API error: {str(e)}"
    except Exception as e:
        return f"❌ Error deleting calendar event: {str(e)}"


def update_calendar_event(event_title: str, date: str = "", **updates) -> str:
    """
    Updates an existing calendar event.
    :param event_title: Title of the event to update
    :param date: Optional date to narrow down search (YYYY-MM-DD or MM/DD/YYYY)
    :param updates: Keyword arguments for fields to update (title, time, description, location, duration_hours)
    """
    print(f"--- 'Hands' (update_calendar_event) activated. Event: {event_title} ---")
    try:
        service = get_calendar_service()
        if not service:
            return "❌ Calendar not authenticated. Please run 'setup calendar' first."
        
        # Search for the event (similar logic to delete)
        if date:
            try:
                if '/' in date:
                    parts = date.split('/')
                    if len(parts) == 3:
                        month, day, year = parts
                        search_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    else:
                        return f"❌ Invalid date format: {date}"
                else:
                    search_date = date
                
                time_min = f"{search_date}T00:00:00Z"
                time_max = f"{search_date}T23:59:59Z"
                
                events_result = service.events().list(
                    calendarId='primary',
                    timeMin=time_min,
                    timeMax=time_max,
                    q=event_title,
                    singleEvents=True
                ).execute()
            except Exception as e:
                return f"❌ Error parsing date: {str(e)}"
        else:
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            future = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=future,
                q=event_title,
                singleEvents=True
            ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return f"❌ No events found with title '{event_title}'"
        
        if len(events) > 1:
            return f"❌ Multiple events found. Please specify a date to narrow down the search."
        
        # Update the event
        event = events[0]
        
        if 'title' in updates:
            event['summary'] = updates['title']
        if 'description' in updates:
            event['description'] = updates['description']
        if 'location' in updates:
            event['location'] = updates['location']
        
        # Update the event on Google Calendar
        updated_event = service.events().update(
            calendarId='primary',
            eventId=event['id'],
            body=event
        ).execute()
        
        return f"✅ Successfully updated event: '{event.get('summary', event_title)}'"
        
    except HttpError as e:
        return f"❌ Google Calendar API error: {str(e)}"
    except Exception as e:
        return f"❌ Error updating calendar event: {str(e)}"


# Export all functions
__all__ = [
    'CalendarManager',
    'setup_calendar_auth',
    'get_calendar_service',
    'get_upcoming_events',
    'create_calendar_event',
    'get_todays_schedule',
    'search_calendar_events',
    'delete_calendar_event',
    'update_calendar_event'
]