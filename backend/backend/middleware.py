"""
Pulsar AI Assistant - Request/Response Middleware

Handles request validation, response formatting, security headers, and logging.
"""

import logging
import time
from functools import wraps
from flask import request, jsonify, g
from typing import Callable

logger = logging.getLogger(__name__)


def request_logger(f: Callable) -> Callable:
    """Log all incoming requests"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        g.start_time = time.time()
        logger.info(f"{request.method} {request.path} from {request.remote_addr}")
        
        response = f(*args, **kwargs)
        
        duration = time.time() - g.start_time
        logger.info(f"{request.method} {request.path} completed in {duration:.3f}s")
        
        return response
    return wrapper


def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


def validate_json(f: Callable) -> Callable:
    """Ensure request contains valid JSON"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'PATCH']:
            if not request.is_json:
                return jsonify({"success": False, "error": "Content-Type must be application/json"}), 400
            
            try:
                request.get_json()
            except Exception as e:
                return jsonify({"success": False, "error": f"Invalid JSON: {str(e)}"}), 400
        
        return f(*args, **kwargs)
    return wrapper


def sanitize_input(data: dict) -> dict:
    """Basic input sanitization"""
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            # Limit string length
            sanitized[key] = value[:10000]
        elif isinstance(value, dict):
            sanitized[key] = sanitize_input(value)
        else:
            sanitized[key] = value
    
    return sanitized
