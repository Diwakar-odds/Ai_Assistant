"""
Unit tests for Calendar Module (Google Calendar Integration)
Tests authentication, event creation, retrieval, and management
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import datetime

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules import google_calendar as cal_module


class TestCalendarManager(unittest.TestCase):
    """Test CalendarManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Reset singleton instance for each test
        cal_module.CalendarManager._instance = None
    
    def test_calendar_manager_singleton(self):
        """Test CalendarManager is a singleton"""
        manager1 = cal_module.CalendarManager()
        manager2 = cal_module.CalendarManager()
        self.assertIs(manager1, manager2)
    
    @patch('modules.google_calendar.Path.exists', return_value=False)
    def test_setup_auth_no_credentials(self, mock_exists):
        """Test setup_auth when credentials.json doesn't exist"""
        manager = cal_module.CalendarManager()
        result = manager.setup_auth()
        self.assertIn("not configured", result)
        self.assertIn("Google Cloud Console", result)
        self.assertIn("❌", result)
    
    @patch('modules.google_calendar.build')
    @patch('modules.google_calendar.pickle.load')
    @patch('modules.google_calendar.Path.exists', return_value=True)
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_setup_auth_valid_token(self, mock_open, mock_exists, mock_pickle_load, mock_build):
        """Test setup_auth with valid existing token"""
        # Mock valid credentials
        mock_creds = Mock()
        mock_creds.valid = True
        mock_pickle_load.return_value = mock_creds
        
        # Mock calendar service
        mock_service = Mock()
        mock_service.calendarList().get().execute.return_value = {
            'summary': 'Test Calendar'
        }
        mock_build.return_value = mock_service
        
        manager = cal_module.CalendarManager()
        result = manager.setup_auth()
        
        self.assertIn("✅", result)
        self.assertIn("authenticated", result.lower())
        self.assertIn("Test Calendar", result)
    
    def test_get_service_not_authenticated(self):
        """Test get_service when not authenticated"""
        manager = cal_module.CalendarManager()
        manager.service = None
        
        with patch.object(manager, 'setup_auth', return_value="❌ Error"):
            service = manager.get_service()
            self.assertIsNone(service)


class TestCalendarEvents(unittest.TestCase):
    """Test calendar event functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        cal_module.CalendarManager._instance = None
    
    @patch('modules.google_calendar.get_calendar_service', return_value=None)
    def test_get_upcoming_events_not_authenticated(self, mock_service):
        """Test get_upcoming_events when not authenticated"""
        result = cal_module.get_upcoming_events(7)
        self.assertIn("not authenticated", result)
        self.assertIn("❌", result)
    
    @patch('modules.google_calendar.get_calendar_service')
    def test_get_upcoming_events_no_events(self, mock_service):
        """Test get_upcoming_events when no events exist"""
        mock_svc = Mock()
        mock_svc.events().list().execute.return_value = {'items': []}
        mock_service.return_value = mock_svc
        
        result = cal_module.get_upcoming_events(7)
        self.assertIn("No upcoming events", result)
    
    @patch('modules.google_calendar.get_calendar_service')
    def test_get_upcoming_events_with_events(self, mock_service):
        """Test get_upcoming_events with existing events"""
        mock_svc = Mock()
        mock_svc.events().list().execute.return_value = {
            'items': [
                {
                    'summary': 'Test Meeting',
                    'start': {'dateTime': '2025-11-18T10:00:00Z'},
                    'location': 'Conference Room'
                },
                {
                    'summary': 'Lunch',
                    'start': {'date': '2025-11-19'},
                }
            ]
        }
        mock_service.return_value = mock_svc
        
        result = cal_module.get_upcoming_events(7)
        self.assertIn("Test Meeting", result)
        self.assertIn("Lunch", result)
        self.assertIn("Conference Room", result)
    
    @patch('modules.google_calendar.get_calendar_service', return_value=None)
    def test_create_event_not_authenticated(self, mock_service):
        """Test create_calendar_event when not authenticated"""
        result = cal_module.create_calendar_event('Test', '2025-11-20')
        self.assertIn("not authenticated", result)
        self.assertIn("❌", result)
    
    @patch('modules.google_calendar.get_calendar_service')
    def test_create_event_all_day(self, mock_service):
        """Test creating an all-day event"""
        mock_svc = Mock()
        mock_svc.events().insert().execute.return_value = {
            'htmlLink': 'https://calendar.google.com/event?id=123'
        }
        mock_service.return_value = mock_svc
        
        result = cal_module.create_calendar_event(
            title='Birthday',
            date='2025-12-25'
        )
        
        self.assertIn("✅", result)
        self.assertIn("Birthday", result)
        self.assertIn("all day", result)
    
    @patch('modules.google_calendar.get_calendar_service')
    def test_create_event_with_time(self, mock_service):
        """Test creating a timed event"""
        mock_svc = Mock()
        mock_svc.events().insert().execute.return_value = {
            'htmlLink': 'https://calendar.google.com/event?id=123'
        }
        mock_service.return_value = mock_svc
        
        result = cal_module.create_calendar_event(
            title='Team Meeting',
            date='2025-11-20',
            time='2:00 PM',
            duration_hours=1,
            description='Weekly sync',
            location='Zoom'
        )
        
        self.assertIn("✅", result)
        self.assertIn("Team Meeting", result)
        self.assertIn("2:00 PM", result)
    
    def test_create_event_invalid_date(self):
        """Test create_calendar_event with invalid date format"""
        result = cal_module.create_calendar_event('Test', '2025/99/99')
        self.assertIn("❌", result)


class TestTodaysSchedule(unittest.TestCase):
    """Test today's schedule function"""
    
    @patch('modules.google_calendar.get_calendar_service')
    @patch('modules.google_calendar.datetime')
    def test_todays_schedule_with_events(self, mock_datetime, mock_service):
        """Test get_todays_schedule with events today"""
        # Mock today's date
        mock_today = datetime.date(2025, 11, 18)
        mock_datetime.date.today.return_value = mock_today
        mock_datetime.datetime.combine = datetime.datetime.combine
        mock_datetime.time = datetime.time
        mock_datetime.datetime.fromisoformat = datetime.datetime.fromisoformat
        
        mock_svc = Mock()
        mock_svc.events().list().execute.return_value = {
            'items': [
                {
                    'summary': 'Morning Standup',
                    'start': {'dateTime': '2025-11-18T09:00:00Z'}
                }
            ]
        }
        mock_service.return_value = mock_svc
        
        result = cal_module.get_todays_schedule()
        self.assertIn("TODAY'S SCHEDULE", result)
        self.assertIn("Morning Standup", result)


class TestSearchEvents(unittest.TestCase):
    """Test search calendar events"""
    
    @patch('modules.google_calendar.get_calendar_service')
    def test_search_events_found(self, mock_service):
        """Test searching for events with results"""
        mock_svc = Mock()
        mock_svc.events().list().execute.return_value = {
            'items': [
                {
                    'summary': 'Project Meeting',
                    'start': {'dateTime': '2025-11-20T14:00:00Z'}
                }
            ]
        }
        mock_service.return_value = mock_svc
        
        result = cal_module.search_calendar_events('project', 30, 30)
        self.assertIn("SEARCH RESULTS", result)
        self.assertIn("Project Meeting", result)
    
    @patch('modules.google_calendar.get_calendar_service')
    def test_search_events_not_found(self, mock_service):
        """Test searching with no results"""
        mock_svc = Mock()
        mock_svc.events().list().execute.return_value = {'items': []}
        mock_service.return_value = mock_svc
        
        result = cal_module.search_calendar_events('nonexistent', 30, 30)
        self.assertIn("No events found", result)


class TestDeleteEvent(unittest.TestCase):
    """Test delete calendar event"""
    
    @patch('modules.google_calendar.get_calendar_service')
    def test_delete_event_success(self, mock_service):
        """Test successful event deletion"""
        mock_svc = Mock()
        mock_svc.events().list().execute.return_value = {
            'items': [
                {
                    'id': 'event123',
                    'summary': 'Meeting to Delete',
                    'start': {'dateTime': '2025-11-20T10:00:00Z'}
                }
            ]
        }
        mock_service.return_value = mock_svc
        
        result = cal_module.delete_calendar_event('Meeting to Delete')
        
        self.assertIn("✅", result)
        self.assertIn("Successfully deleted", result)
        mock_svc.events().delete.assert_called_once()
    
    @patch('modules.google_calendar.get_calendar_service')
    def test_delete_event_not_found(self, mock_service):
        """Test deleting non-existent event"""
        mock_svc = Mock()
        mock_svc.events().list().execute.return_value = {'items': []}
        mock_service.return_value = mock_svc
        
        result = cal_module.delete_calendar_event('Nonexistent')
        self.assertIn("No events found", result)
        self.assertIn("❌", result)
    
    @patch('modules.google_calendar.get_calendar_service')
    def test_delete_event_multiple_found(self, mock_service):
        """Test deleting when multiple events match"""
        mock_svc = Mock()
        mock_svc.events().list().execute.return_value = {
            'items': [
                {'id': 'event1', 'summary': 'Meeting', 'start': {'date': '2025-11-20'}},
                {'id': 'event2', 'summary': 'Meeting', 'start': {'date': '2025-11-21'}}
            ]
        }
        mock_service.return_value = mock_svc
        
        result = cal_module.delete_calendar_event('Meeting')
        self.assertIn("Multiple events found", result)
        self.assertIn("❌", result)


class TestUpdateEvent(unittest.TestCase):
    """Test update calendar event"""
    
    @patch('modules.google_calendar.get_calendar_service')
    def test_update_event_success(self, mock_service):
        """Test successful event update"""
        mock_svc = Mock()
        mock_svc.events().list().execute.return_value = {
            'items': [
                {
                    'id': 'event123',
                    'summary': 'Old Title',
                    'start': {'dateTime': '2025-11-20T10:00:00Z'}
                }
            ]
        }
        mock_svc.events().update().execute.return_value = {
            'summary': 'New Title'
        }
        mock_service.return_value = mock_svc
        
        result = cal_module.update_calendar_event(
            'Old Title',
            title='New Title',
            description='Updated description'
        )
        
        self.assertIn("✅", result)
        self.assertIn("Successfully updated", result)


if __name__ == '__main__':
    unittest.main()
