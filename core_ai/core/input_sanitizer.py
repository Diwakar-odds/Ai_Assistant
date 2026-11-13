"""
Centralized Input Validation and Sanitization System

This module provides comprehensive input sanitization to prevent:
- SQL injection
- XSS (Cross-Site Scripting)
- Command injection
- Path traversal
- AI prompt injection

Author: Pulsar AI Assistant Team
Date: January 9, 2026
"""

import re
import html
import os
import logging
from typing import Any, Optional, List, Dict
from pathlib import Path
from urllib.parse import urlparse, quote

logger = logging.getLogger(__name__)


class InputSanitizer:
    """
    Comprehensive input validation and sanitization
    
    Provides methods to sanitize various types of user inputs to prevent
    security vulnerabilities including injection attacks.
    """
    
    # SQL keywords and patterns
    SQL_KEYWORDS = [
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'EXEC', 'EXECUTE', 'UNION', 'DECLARE', 'CAST', 'CONVERT'
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r'[;&|`$]',  # Shell metacharacters
        r'\$\(',  # Command substitution
        r'`',  # Backtick substitution
        r'>\s*\/dev',  # Device redirection
        r'<\s*\/dev',
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\.',  # Parent directory
        r'\.\/\.\.', 
        r'\.\.\\',
        r'%2e%2e',  # URL encoded ..
        r'%252e%252e',  # Double URL encoded
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # Event handlers (onclick, onload, etc.)
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
    ]
    
    def __init__(self):
        logger.info("Input sanitizer initialized")
    
    def sanitize_sql(self, value: str) -> str:
        """
        Sanitize input for SQL queries
        
        Note: This is a defense-in-depth measure. Always use parameterized queries!
        
        Args:
            value: Input string to sanitize
            
        Returns:
            Sanitized string safe for SQL
        """
        if not isinstance(value, str):
            return str(value)
        
        # Remove SQL comments
        value = re.sub(r'--.*$', '', value, flags=re.MULTILINE)
        value = re.sub(r'/\*.*?\*/', '', value, flags=re.DOTALL)
        
        # Check for SQL keywords in suspicious contexts
        for keyword in self.SQL_KEYWORDS:
            pattern = rf'\b{keyword}\b'
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"SQL keyword detected in input: {keyword}")
        
        # Escape single quotes (common SQL injection vector)
        value = value.replace("'", "''")
        
        return value
    
    def validate_sql_input(self, value: str, field_name: str = "input") -> bool:
        """
        Validate if input is safe for SQL
        
        Args:
            value: Input to validate
            field_name: Name of the field for logging
            
        Returns:
            True if safe, False if suspicious
        """
        if not isinstance(value, str):
            return True
        
        # Check for SQL injection patterns
        for keyword in self.SQL_KEYWORDS:
            pattern = rf'\b{keyword}\b'
            if re.search(pattern, value, re.IGNORECASE):
                logger.error(f"Potential SQL injection in {field_name}: SQL keyword '{keyword}' detected")
                return False
        
        # Check for multiple statements (semicolon followed by SQL)
        if ';' in value:
            logger.warning(f"Semicolon detected in {field_name}, possible SQL injection")
            return False
        
        return True
    
    def sanitize_html(self, value: str) -> str:
        """
        Sanitize HTML input to prevent XSS
        
        Args:
            value: Input string with potential HTML
            
        Returns:
            HTML-escaped string
        """
        if not isinstance(value, str):
            return str(value)
        
        # First, check for XSS patterns
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"XSS pattern detected: {pattern}")
        
        # HTML escape
        return html.escape(value, quote=True)
    
    def sanitize_command(self, command: str) -> str:
        """
        Sanitize system command to prevent command injection
        
        Args:
            command: Command string to sanitize
            
        Returns:
            Sanitized command
            
        Raises:
            ValueError: If command contains injection patterns
        """
        if not isinstance(command, str):
            command = str(command)
        
        # Check for command injection patterns
        for pattern in self.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, command):
                logger.error(f"Command injection pattern detected: {pattern}")
                raise ValueError(f"Command contains suspicious pattern: {pattern}")
        
        return command
    
    def validate_file_path(self, path: str, allowed_base: Optional[str] = None) -> bool:
        """
        Validate file path to prevent path traversal attacks
        
        Args:
            path: File path to validate
            allowed_base: Base directory that path must be within (optional)
            
        Returns:
            True if path is safe, False otherwise
        """
        if not isinstance(path, str):
            return False
        
        # Check for path traversal patterns
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                logger.error(f"Path traversal pattern detected: {pattern}")
                return False
        
        # Check for absolute paths if base directory specified
        if allowed_base:
            try:
                # Resolve to absolute path
                abs_path = Path(path).resolve()
                abs_base = Path(allowed_base).resolve()
                
                # Check if path is within base directory
                try:
                    abs_path.relative_to(abs_base)
                except ValueError:
                    logger.error(f"Path {path} is outside allowed base {allowed_base}")
                    return False
                    
            except Exception as e:
                logger.error(f"Error validating path: {e}")
                return False
        
        return True
    
    def sanitize_file_path(self, path: str, allowed_base: Optional[str] = None) -> str:
        """
        Sanitize file path
        
        Args:
            path: File path to sanitize
            allowed_base: Base directory to restrict to
            
        Returns:
            Sanitized path
            
        Raises:
            ValueError: If path is invalid or contains traversal
        """
        if not self.validate_file_path(path, allowed_base):
            raise ValueError(f"Invalid or unsafe file path: {path}")
        
        # Normalize path
        return os.path.normpath(path)
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to remove dangerous characters
        
        Args:
            filename: Original filename
            
        Returns:
            Safe filename
        """
        if not isinstance(filename, str):
            filename = str(filename)
        
        # Remove any path components
        filename = os.path.basename(filename)
        
        # Remove or replace dangerous characters
        # Allow only alphanumeric, dash, underscore, and period
        filename = re.sub(r'[^\w\-.]', '_', filename)
        
        # Prevent hidden files
        if filename.startswith('.'):
            filename = '_' + filename
        
        # Limit length
        max_length = 255
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length - len(ext)] + ext
        
        return filename
    
    def sanitize_url(self, url: str, allowed_schemes: Optional[List[str]] = None) -> str:
        """
        Sanitize and validate URL
        
        Args:
            url: URL to sanitize
            allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])
            
        Returns:
            Sanitized URL
            
        Raises:
            ValueError: If URL is invalid
        """
        if not isinstance(url, str):
            url = str(url)
        
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        try:
            parsed = urlparse(url)
            
            # Validate scheme
            if parsed.scheme not in allowed_schemes:
                raise ValueError(f"URL scheme '{parsed.scheme}' not allowed")
            
            # Check for javascript: or data: URLs (XSS vectors)
            if parsed.scheme in ['javascript', 'data', 'file']:
                raise ValueError(f"Dangerous URL scheme: {parsed.scheme}")
            
            return url
            
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            raise ValueError(f"Invalid URL: {url}")
    
    def sanitize_prompt(self, prompt: str, max_length: int = 10000) -> str:
        """
        Sanitize AI prompt to prevent prompt injection
        
        Args:
            prompt: User prompt to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized prompt
        """
        if not isinstance(prompt, str):
            prompt = str(prompt)
        
        # Remove or escape potential prompt injection patterns
        dangerous_patterns = [
            r'ignore previous instructions',
            r'disregard.*instructions',
            r'system:',
            r'SYSTEM:',
            r'\[INST\]',  # Common instruction markers
            r'\[\/INST\]',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                logger.warning(f"Potential prompt injection pattern detected: {pattern}")
                # Don't auto-modify, just log for now
        
        # Limit length to prevent DoS
        if len(prompt) > max_length:
            logger.warning(f"Prompt length ({len(prompt)}) exceeds maximum ({max_length})")
            prompt = prompt[:max_length]
        
        return prompt
    
    def sanitize_json(self, data: Any, max_depth: int = 10) -> Any:
        """
        Sanitize JSON data recursively
        
        Args:
            data: JSON data to sanitize
            max_depth: Maximum nesting depth
            
        Returns:
            Sanitized data
        """
        def _sanitize_recursive(obj: Any, depth: int = 0) -> Any:
            if depth > max_depth:
                raise ValueError("JSON nesting depth exceeded")
            
            if isinstance(obj, str):
                return self.sanitize_html(obj)
            elif isinstance(obj, dict):
                return {
                    k: _sanitize_recursive(v, depth + 1)
                    for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [_sanitize_recursive(item, depth + 1) for item in obj]
            else:
                return obj
        
        return _sanitize_recursive(data)
    
    def validate_email(self, email: str) -> bool:
        """
        Validate email address format
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(email, str):
            return False
        
        # Simple email regex
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_integer(self, value: Any, min_val: Optional[int] = None,
                        max_val: Optional[int] = None) -> bool:
        """
        Validate integer input with optional range
        
        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            True if valid, False otherwise
        """
        try:
            int_val = int(value)
            
            if min_val is not None and int_val < min_val:
                return False
            
            if max_val is not None and int_val > max_val:
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    def sanitize_dict(self, data: Dict[str, Any], 
                     allowed_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Sanitize dictionary by filtering keys and sanitizing values
        
        Args:
            data: Dictionary to sanitize
            allowed_keys: List of allowed keys (if specified, others are removed)
            
        Returns:
            Sanitized dictionary
        """
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary")
        
        sanitized = {}
        
        for key, value in data.items():
            # Filter keys if whitelist provided
            if allowed_keys and key not in allowed_keys:
                logger.warning(f"Filtering out disallowed key: {key}")
                continue
            
            # Sanitize string values
            if isinstance(value, str):
                sanitized[key] = self.sanitize_html(value)
            else:
                sanitized[key] = value
        
        return sanitized


# Global input sanitizer instance
_input_sanitizer_instance: Optional[InputSanitizer] = None


def get_input_sanitizer() -> InputSanitizer:
    """Get global input sanitizer instance (singleton)"""
    global _input_sanitizer_instance
    if _input_sanitizer_instance is None:
        _input_sanitizer_instance = InputSanitizer()
    return _input_sanitizer_instance
