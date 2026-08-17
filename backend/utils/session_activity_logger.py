"""
Session Activity Logger for YourDaddy Assistant
=============================================

This module handles session-specific activity logging with categorized tracking.
Each session gets its own activity log files organized by categories.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from utils.logging_config import get_logger, SessionManager

class SessionActivityLogger:
    """Logs all user activities in session-specific files"""
    
    def __init__(self):
        # Wait for session to be initialized by session_init module
        # Don't create a new one here
        self.session_id = SessionManager.get_current_session() if SessionManager._current_session else None
        if not self.session_id:
            # If no session exists yet, we'll initialize on first use
            self._deferred_init = True
            return
        
        self._deferred_init = False
        self._initialize_logger()
        
    def __getattr__(self, name):
        if name == 'loggers':
            if getattr(self, '_deferred_init', False):
                self._initialize_logger()
                self._deferred_init = False
            if 'loggers' in self.__dict__:
                return self.__dict__['loggers']
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        
    
    def _initialize_logger(self):
        """Initialize logger components (called after session is ready)"""
        self.session_id = SessionManager.get_current_session()
        self.current_date = SessionManager.get_current_date()
        self.activities_dir = Path('logs') / self.current_date / 'activities'
        self.activities_dir.mkdir(parents=True, exist_ok=True)
        
        # Category-specific loggers
        self.loggers = {
            'voice_commands': get_logger(f'voice_commands', log_category='activities'),
            'file_operations': get_logger(f'file_operations', log_category='activities'), 
            'system_commands': get_logger(f'system_commands', log_category='activities'),
            'api_requests': get_logger(f'api_requests', log_category='activities'),
            'user_interactions': get_logger(f'user_interactions', log_category='activities'),
            'music_control': get_logger(f'music_control', log_category='activities'),
            'email_operations': get_logger(f'email_operations', log_category='activities'),
            'calendar_operations': get_logger(f'calendar_operations', log_category='activities'),
            'web_scraping': get_logger(f'web_scraping', log_category='activities'),
            'multimodal_ai': get_logger(f'multimodal_ai', log_category='activities'),
            'automation': get_logger(f'automation', log_category='activities'),
        }
        
        # Initialize session activity summary
        self.session_summary = {
            'session_id': self.session_id,
            'start_time': datetime.now().isoformat(),
            'activities_count': 0,
            'categories': {},
            'last_activity': None
        }
        
        self._save_session_start()
    
    def _save_session_start(self):
        """Save session start information"""
        summary_file = self.activities_dir / f'session_summary_{self.session_id}.json'
        with open(summary_file, 'w') as f:
            json.dump(self.session_summary, f, indent=2)
        
        # Log session start once (not in all category loggers to avoid spam)
        logger = self.loggers.get('system_commands')
        if logger:
            logger.info(f"🚀 NEW SESSION STARTED - {self.session_id}")
    
    def log_voice_command(self, command: str, language: str = None, 
                         confidence: float = None, response: str = None, 
                         execution_time_ms: float = None):
        """Log voice command activity"""
        if hasattr(self, '_deferred_init') and self._deferred_init:
            self._initialize_logger()
            self._deferred_init = False
        
        activity = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'category': 'voice_command',
            'command': command,
            'language': language,
            'confidence': confidence,
            'response_provided': bool(response),
            'response_length': len(response) if response else 0,
            'execution_time_ms': execution_time_ms
        }
        
        self.loggers['voice_commands'].info(f"VOICE_CMD | {json.dumps(activity)}")
        self._update_session_summary('voice_commands', activity)
    
    def log_file_operation(self, operation: str, file_path: str = None, 
                          success: bool = True, details: Dict = None):
        """Log file operation activity"""
        if hasattr(self, '_deferred_init') and self._deferred_init:
            self._initialize_logger()
            self._deferred_init = False
            
        activity = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'category': 'file_operation',
            'operation': operation,
            'file_path': file_path,
            'success': success,
            'details': details or {}
        }
        
        self.loggers['file_operations'].info(f"FILE_OP | {json.dumps(activity)}")
        self._update_session_summary('file_operations', activity)
    
    def log_system_command(self, command: str, command_type: str = None,
                          success: bool = True, output: str = None):
        """Log system command execution"""
        activity = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'category': 'system_command',
            'command': command,
            'command_type': command_type,
            'success': success,
            'has_output': bool(output),
            'output_length': len(output) if output else 0
        }
        
        self.loggers['system_commands'].info(f"SYS_CMD | {json.dumps(activity)}")
        self._update_session_summary('system_commands', activity)
    
    def log_api_request(self, endpoint: str, method: str = 'GET',
                       status_code: int = 200, response_time_ms: float = None,
                       user_id: str = None):
        """Log API request activity"""
        activity = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'category': 'api_request',
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'response_time_ms': response_time_ms,
            'user_id': user_id
        }
        
        self.loggers['api_requests'].info(f"API_REQ | {json.dumps(activity)}")
        self._update_session_summary('api_requests', activity)
    
    def log_user_interaction(self, interaction_type: str, details: Dict = None,
                           duration_ms: float = None):
        """Log user interaction activity"""
        activity = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'category': 'user_interaction',
            'interaction_type': interaction_type,
            'details': details or {},
            'duration_ms': duration_ms
        }
        
        self.loggers['user_interactions'].info(f"USER_INT | {json.dumps(activity)}")
        self._update_session_summary('user_interactions', activity)
    
    def log_music_control(self, action: str, track_info: Dict = None,
                         platform: str = None, success: bool = True):
        """Log music control activity"""
        activity = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'category': 'music_control',
            'action': action,
            'platform': platform,
            'track_info': track_info or {},
            'success': success
        }
        
        self.loggers['music_control'].info(f"MUSIC | {json.dumps(activity)}")
        self._update_session_summary('music_control', activity)
    
    def log_email_operation(self, operation: str, email_count: int = None,
                           sender: str = None, subject: str = None,
                           success: bool = True):
        """Log email operation activity"""
        activity = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'category': 'email_operation',
            'operation': operation,
            'email_count': email_count,
            'sender': sender,
            'subject': subject,
            'success': success
        }
        
        self.loggers['email_operations'].info(f"EMAIL | {json.dumps(activity)}")
        self._update_session_summary('email_operations', activity)
    
    def log_calendar_operation(self, operation: str, event_details: Dict = None,
                              date_range: Dict = None, success: bool = True):
        """Log calendar operation activity"""
        activity = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'category': 'calendar_operation',
            'operation': operation,
            'event_details': event_details or {},
            'date_range': date_range or {},
            'success': success
        }
        
        self.loggers['calendar_operations'].info(f"CALENDAR | {json.dumps(activity)}")
        self._update_session_summary('calendar_operations', activity)
    
    def log_web_scraping(self, url: str, scraping_type: str = None,
                        data_extracted: bool = False, error: str = None):
        """Log web scraping activity"""
        activity = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'category': 'web_scraping',
            'url': url,
            'scraping_type': scraping_type,
            'data_extracted': data_extracted,
            'error': error,
            'success': error is None
        }
        
        self.loggers['web_scraping'].info(f"WEB_SCRAPE | {json.dumps(activity)}")
        self._update_session_summary('web_scraping', activity)
    
    def log_multimodal_ai(self, operation: str, input_type: str = None,
                         processing_time_ms: float = None, 
                         confidence: float = None, success: bool = True):
        """Log multimodal AI activity"""
        activity = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'category': 'multimodal_ai',
            'operation': operation,
            'input_type': input_type,
            'processing_time_ms': processing_time_ms,
            'confidence': confidence,
            'success': success
        }
        
        self.loggers['multimodal_ai'].info(f"MULTIMODAL | {json.dumps(activity)}")
        self._update_session_summary('multimodal_ai', activity)
    
    def log_automation(self, automation_type: str, steps_count: int = None,
                      execution_time_ms: float = None, success: bool = True):
        """Log automation activity"""
        activity = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'category': 'automation',
            'automation_type': automation_type,
            'steps_count': steps_count,
            'execution_time_ms': execution_time_ms,
            'success': success
        }
        
        self.loggers['automation'].info(f"AUTOMATION | {json.dumps(activity)}")
        self._update_session_summary('automation', activity)
    
    def _update_session_summary(self, category: str, activity: Dict):
        """Update session summary with new activity"""
        self.session_summary['activities_count'] += 1
        self.session_summary['last_activity'] = activity['timestamp']
        
        if category not in self.session_summary['categories']:
            self.session_summary['categories'][category] = 0
        self.session_summary['categories'][category] += 1
        
        # Save updated summary
        summary_file = self.activities_dir / f'session_summary_{self.session_id}.json'
        with open(summary_file, 'w') as f:
            json.dump(self.session_summary, f, indent=2)
    
    def end_session(self):
        """Mark session as ended"""
        self.session_summary['end_time'] = datetime.now().isoformat()
        self.session_summary['duration_seconds'] = (
            datetime.fromisoformat(self.session_summary['end_time']) -
            datetime.fromisoformat(self.session_summary['start_time'])
        ).total_seconds()
        
        # Save final summary
        summary_file = self.activities_dir / f'session_summary_{self.session_id}.json'
        with open(summary_file, 'w') as f:
            json.dump(self.session_summary, f, indent=2)
        
        # Log session end in all category loggers
        for category, logger in self.loggers.items():
            logger.info(f"🏁 SESSION ENDED - {self.session_id} - Duration: {self.session_summary.get('duration_seconds', 0):.1f}s")


# Global session activity logger instance (singleton - lazy loaded)
_session_activity_logger_instance = None

def get_session_activity_logger():
    """Get or create singleton session activity logger"""
    global _session_activity_logger_instance
    if _session_activity_logger_instance is None:
        _session_activity_logger_instance = SessionActivityLogger()
        
    # Initialize deferred logger if session is ready
    if hasattr(_session_activity_logger_instance, '_deferred_init') and _session_activity_logger_instance._deferred_init:
        if SessionManager._current_session is not None:
            _session_activity_logger_instance._initialize_logger()
            _session_activity_logger_instance._deferred_init = False
            
    return _session_activity_logger_instance

# Lazy property - only creates logger when first accessed
class _LazyLogger:
    def __getattr__(self, name):
        logger = get_session_activity_logger()
        return getattr(logger, name)

session_activity_logger = _LazyLogger()

# Convenience functions for easy logging
def log_voice_command(command: str, **kwargs):
    """Log a voice command activity"""
    session_activity_logger.log_voice_command(command, **kwargs)

def log_file_operation(operation: str, **kwargs):
    """Log a file operation activity"""
    session_activity_logger.log_file_operation(operation, **kwargs)

def log_system_command(command: str, **kwargs):
    """Log a system command activity"""
    session_activity_logger.log_system_command(command, **kwargs)

def log_api_request(endpoint: str, **kwargs):
    """Log an API request activity"""
    session_activity_logger.log_api_request(endpoint, **kwargs)

def log_user_interaction(interaction_type: str, **kwargs):
    """Log a user interaction activity"""
    session_activity_logger.log_user_interaction(interaction_type, **kwargs)

def log_music_control(action: str, **kwargs):
    """Log a music control activity"""
    session_activity_logger.log_music_control(action, **kwargs)

def log_email_operation(operation: str, **kwargs):
    """Log an email operation activity"""
    session_activity_logger.log_email_operation(operation, **kwargs)

def log_calendar_operation(operation: str, **kwargs):
    """Log a calendar operation activity"""
    session_activity_logger.log_calendar_operation(operation, **kwargs)

def log_web_scraping(url: str, **kwargs):
    """Log a web scraping activity"""
    session_activity_logger.log_web_scraping(url, **kwargs)

def log_multimodal_ai(operation: str, **kwargs):
    """Log a multimodal AI activity"""
    session_activity_logger.log_multimodal_ai(operation, **kwargs)

def log_automation(automation_type: str, **kwargs):
    """Log an automation activity"""
    session_activity_logger.log_automation(automation_type, **kwargs)

def end_current_session():
    """End the current logging session"""
    session_activity_logger.end_session()


# Example usage
if __name__ == "__main__":
    print("Testing Session Activity Logger")
    
    # Test different activity types
    log_voice_command("play some music", language="en", confidence=0.95, 
                     response="Playing music from Spotify", execution_time_ms=1200)
    
    log_file_operation("create_file", file_path="test.txt", success=True,
                      details={"size_bytes": 1024, "encoding": "utf-8"})
    
    log_system_command("volume_up", command_type="audio_control", success=True)
    
    log_user_interaction("gui_button_click", details={"button": "send_message"})
    
    print(f"✅ Session activities logged with ID: {session_activity_logger.session_id}")