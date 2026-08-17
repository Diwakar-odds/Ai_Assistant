"""
YourDaddy AI Assistant - Error Handling Utilities

Centralized error handling for consistent error responses and logging.
"""

import logging
import traceback
from functools import wraps
from flask import jsonify, request

logger = logging.getLogger(__name__)


class AIAssistantError(Exception):
    """Base exception for AI Assistant"""
    pass


class VoiceError(AIAssistantError):
    """Voice-related errors"""
    pass


class AutomationError(AIAssistantError):
    """Automation-related errors"""
    pass


class ValidationError(AIAssistantError):
    """Input validation errors"""
    pass


def handle_error(error, context="", user_friendly=True):
    """
    Centralized error handling with logging
    
    Args:
        error: The exception that occurred
        context: Context string for logging
        user_friendly: Whether to return user-friendly message
        
    Returns:
        dict: Error response dictionary
    """
    # Log the full error
    error_msg = f"{context}: {str(error)}" if context else str(error)
    logger.error(error_msg)
    logger.debug(traceback.format_exc())
    
    # Return user-friendly or detailed message
    if user_friendly:
        return {
            "success": False,
            "error": "An error occurred. Please try again.",
            "details": str(error) if logger.level == logging.DEBUG else None
        }
    else:
        return {
            "success": False,
            "error": str(error),
            "traceback": traceback.format_exc() if logger.level == logging.DEBUG else None
        }


def error_handler(context=""):
    """
    Decorator for consistent error handling in routes
    
    Usage:
        @app.route('/api/something')
        @error_handler("Something endpoint")
        def something():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValidationError as e:
                logger.warning(f"{context} - Validation error: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 400
            except Exception as e:
                logger.error(f"{context} - Error: {e}")
                logger.debug(traceback.format_exc())
                return jsonify({
                    "success": False,
                    "error": "An error occurred. Please try again."
                }), 500
        return wrapper
    return decorator


def log_request():
    """Log incoming request details"""
    logger.info(f"{request.method} {request.path} from {request.remote_addr}")
    if request.is_json:
        logger.debug(f"Request body: {request.get_json()}")
