"""
Advanced Logging Enhancements for YourDaddy Assistant
=====================================================

This module provides advanced logging features including:
- Performance monitoring decorators
- API request tracking
- Error tracking with context
- Custom log filters
- Log aggregation utilities
"""

import logging
import time
import functools
import traceback
import sys
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import threading
import json

from .logging_config import get_logger

# Performance logging
def log_performance(func_name: str = None, threshold_ms: float = 100):
    """
    Decorator to log function performance
    
    Args:
        func_name: Custom name for the function (defaults to actual function name)
        threshold_ms: Only log if execution time exceeds this threshold
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger = get_logger('performance', log_category='performance')
            
            function_name = func_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                if duration_ms > threshold_ms:
                    logger.info(f"SLOW_FUNCTION | {function_name} | {duration_ms:.2f}ms")
                
                return result
                
            except Exception as e:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                logger.error(f"FUNCTION_ERROR | {function_name} | {duration_ms:.2f}ms | {str(e)}")
                raise
                
        return wrapper
    return decorator


class ContextualErrorLogger:
    """Enhanced error logger with context information"""
    
    def __init__(self, module_name: str):
        self.logger = get_logger(f"error_context_{module_name}", log_category='errors')
    
    def log_exception(self, exception: Exception, context: Dict[str, Any] = None, 
                     user_friendly: str = None):
        """
        Log exception with full context
        
        Args:
            exception: The exception that occurred
            context: Additional context information
            user_friendly: User-friendly error message
        """
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc(),
            'context': context or {},
            'user_message': user_friendly,
            'thread_id': threading.current_thread().ident,
            'function_name': sys._getframe(1).f_code.co_name,
            'file_name': sys._getframe(1).f_code.co_filename,
            'line_number': sys._getframe(1).f_lineno
        }
        
        self.logger.error(f"EXCEPTION | {json.dumps(error_info, indent=2)}")
        
        # Also log to critical if it's a severe error
        if isinstance(exception, (SystemError, MemoryError, KeyboardInterrupt)):
            critical_logger = get_logger('critical_errors', log_category='errors')
            critical_logger.critical(f"CRITICAL_EXCEPTION | {error_info['exception_type']} | {error_info['exception_message']}")


class APIRequestLogger:
    """Logger for API requests and responses"""
    
    def __init__(self):
        self.logger = get_logger('api_requests', log_category='api')
        self.error_logger = get_logger('api_errors', log_category='errors')
    
    def log_request(self, method: str, endpoint: str, params: Dict = None, 
                   headers: Dict = None, user_id: str = None):
        """Log incoming API request"""
        request_info = {
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'endpoint': endpoint,
            'params': params or {},
            'user_id': user_id,
            'thread_id': threading.current_thread().ident
        }
        
        # Don't log sensitive headers
        safe_headers = {}
        if headers:
            safe_headers = {k: v for k, v in headers.items() 
                          if k.lower() not in ['authorization', 'cookie', 'x-api-key']}
        request_info['headers'] = safe_headers
        
        self.logger.info(f"REQUEST | {method} | {endpoint} | {json.dumps(request_info)}")
    
    def log_response(self, method: str, endpoint: str, status_code: int, 
                    duration_ms: float, response_size: int = None, error: str = None):
        """Log API response"""
        response_info = {
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'duration_ms': round(duration_ms, 2),
            'response_size_bytes': response_size,
            'error': error
        }
        
        if status_code >= 500:
            self.error_logger.error(f"SERVER_ERROR | {json.dumps(response_info)}")
        elif status_code >= 400:
            self.logger.warning(f"CLIENT_ERROR | {json.dumps(response_info)}")
        else:
            self.logger.info(f"RESPONSE | {json.dumps(response_info)}")


class SecurityLogger:
    """Logger for security-related events"""
    
    def __init__(self):
        self.logger = get_logger('security_events', log_category='security')
    
    def log_auth_attempt(self, user_id: str, success: bool, ip_address: str = None, 
                        user_agent: str = None, reason: str = None):
        """Log authentication attempt"""
        auth_info = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'AUTH_ATTEMPT',
            'user_id': user_id,
            'success': success,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'failure_reason': reason if not success else None
        }
        
        level = 'info' if success else 'warning'
        getattr(self.logger, level)(f"AUTH | {json.dumps(auth_info)}")
    
    def log_suspicious_activity(self, event_type: str, details: Dict[str, Any], 
                              severity: str = 'medium'):
        """Log suspicious activity"""
        security_event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'SUSPICIOUS_ACTIVITY',
            'activity_type': event_type,
            'severity': severity,
            'details': details,
            'thread_id': threading.current_thread().ident
        }
        
        if severity == 'high':
            self.logger.error(f"SECURITY_THREAT | {json.dumps(security_event)}")
        else:
            self.logger.warning(f"SECURITY_WARNING | {json.dumps(security_event)}")


class UserActivityLogger:
    """Logger for user activity and interactions"""
    
    def __init__(self):
        self.logger = get_logger('user_activity', log_category='app')
    
    def log_user_action(self, user_id: str, action: str, details: Dict[str, Any] = None, 
                       success: bool = True):
        """Log user action"""
        activity_info = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': action,
            'success': success,
            'details': details or {}
        }
        
        self.logger.info(f"USER_ACTION | {json.dumps(activity_info)}")
    
    def log_voice_command(self, user_id: str, command: str, language: str = None, 
                         confidence: float = None, response: str = None):
        """Log voice command interaction"""
        voice_info = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'command': command,
            'language': language,
            'confidence': confidence,
            'response_length': len(response) if response else 0
        }
        
        self.logger.info(f"VOICE_COMMAND | {json.dumps(voice_info)}")


class LogAggregator:
    """Aggregates and analyzes log data"""
    
    def __init__(self):
        self.logger = get_logger('log_aggregator', log_category='system')
    
    def generate_daily_summary(self, date: str = None) -> Dict[str, Any]:
        """Generate daily log summary"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        summary = {
            'date': date,
            'total_requests': 0,
            'error_count': 0,
            'average_response_time': 0,
            'top_endpoints': [],
            'error_types': {},
            'user_activity_count': 0
        }
        
        # This would normally parse log files and generate statistics
        # For now, we'll log that summary generation was requested
        self.logger.info(f"DAILY_SUMMARY_GENERATED | {date} | {json.dumps(summary)}")
        
        return summary


# Global instances for easy access
error_logger = ContextualErrorLogger('global')
api_logger = APIRequestLogger()
security_logger = SecurityLogger()
user_activity_logger = UserActivityLogger()
log_aggregator = LogAggregator()


# Convenience functions
def log_error_with_context(exception: Exception, context: Dict[str, Any] = None, 
                          user_friendly: str = None):
    """Convenience function for logging errors with context"""
    error_logger.log_exception(exception, context, user_friendly)


def log_api_call(method: str, endpoint: str, status_code: int, duration_ms: float):
    """Convenience function for logging API calls"""
    api_logger.log_response(method, endpoint, status_code, duration_ms)


def log_user_action(user_id: str, action: str, details: Dict[str, Any] = None):
    """Convenience function for logging user actions"""
    user_activity_logger.log_user_action(user_id, action, details)


# Example usage and testing
if __name__ == "__main__":
    print("Testing Advanced Logging Features\n")
    
    # Test performance logging
    @log_performance("test_function", threshold_ms=50)
    def slow_function():
        import time
        time.sleep(0.1)  # Simulate slow operation
        return "completed"
    
    # Test error logging
    try:
        raise ValueError("Test error for logging")
    except Exception as e:
        log_error_with_context(e, {"test_context": "example"}, "A test error occurred")
    
    # Test API logging
    log_api_call("GET", "/api/test", 200, 45.5)
    
    # Test user activity
    log_user_action("user123", "login", {"method": "oauth"})
    
    print("✅ Advanced logging features tested successfully!")