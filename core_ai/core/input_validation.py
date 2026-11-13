"""
Comprehensive Input Validation Framework for AI Assistant

Provides centralized validation for all input types across the system:
- Web API endpoints
- WebSocket messages  
- CLI command inputs
- Configuration parameters
- File uploads and data imports

Includes sanitization, type checking, and security validation.
"""

import re
import json
import html
import urllib.parse
from typing import Any, Dict, List, Optional, Union, Callable, Type
from dataclasses import dataclass
from enum import Enum
import ipaddress
import email.utils
from pathlib import Path

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from core.audit_logger import audit_security_event, SeverityLevel
    AUDIT_AVAILABLE = True
except ImportError:
    AUDIT_AVAILABLE = False


class ValidationError(Exception):
    """Custom exception for validation failures"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)


class InputType(Enum):
    """Types of input validation"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    EMAIL = "email"
    URL = "url"
    IP_ADDRESS = "ip_address"
    FILE_PATH = "file_path"
    JSON = "json"
    HTML = "html"
    COMMAND = "command"
    API_KEY = "api_key"
    PIN = "pin"
    PHONE = "phone"
    DATE = "date"
    UUID = "uuid"


@dataclass
class ValidationRule:
    """Validation rule configuration"""
    field_name: str
    input_type: InputType
    required: bool = True
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    custom_validator: Optional[Callable[[Any], bool]] = None
    sanitize: bool = True
    description: str = ""


class InputValidator:
    """
    Comprehensive input validation system
    
    Features:
    - Type-specific validation
    - Security sanitization
    - Pattern matching
    - Range validation
    - Custom validation functions
    - XSS and injection prevention
    """
    
    def __init__(self):
        """Initialize validator with security patterns"""
        # Common security patterns
        self.sql_injection_patterns = [
            r"('|(\\')|(;|\\x27|\\x3D))",
            r"union\s+select",
            r"select\s+.*\s+from",
            r"drop\s+table",
            r"delete\s+from",
            r"insert\s+into",
            r"update\s+.*\s+set"
        ]
        
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe",
            r"<object",
            r"<embed"
        ]
        
        self.command_injection_patterns = [
            r"[;&|`$()]",
            r"../",
            r"\.\./",
            r"\\\\",
            r"%2e%2e",
            r"cmd\.exe",
            r"/bin/",
            r"powershell"
        ]
        
        # File extension restrictions
        self.dangerous_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.ps1', '.sh', '.php', '.asp', '.jsp', '.py'
        }
        
        # Common validation patterns
        self.patterns = {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'url': r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?$',
            'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            'pin': r'^\d{4,8}$',
            'phone': r'^\+?[\d\s\-\(\)]{7,15}$',
            'api_key': r'^[A-Za-z0-9_\-]{16,128}$',
            'safe_filename': r'^[a-zA-Z0-9._\-\s]{1,255}$',
            'command_safe': r'^[a-zA-Z0-9\s\-_.:/\\]+$'
        }
    
    def validate_field(self, value: Any, rule: ValidationRule) -> Any:
        """
        Validate a single field against its rule
        
        Args:
            value: Value to validate
            rule: Validation rule
            
        Returns:
            Validated and sanitized value
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Check if field is required
            if value is None or value == "":
                if rule.required:
                    raise ValidationError(f"Field '{rule.field_name}' is required", rule.field_name, value)
                return None
            
            # Type-specific validation
            validated_value = self._validate_type(value, rule)
            
            # Length validation for strings
            if rule.input_type == InputType.STRING and isinstance(validated_value, str):
                if rule.min_length and len(validated_value) < rule.min_length:
                    raise ValidationError(
                        f"Field '{rule.field_name}' must be at least {rule.min_length} characters",
                        rule.field_name, value
                    )
                if rule.max_length and len(validated_value) > rule.max_length:
                    raise ValidationError(
                        f"Field '{rule.field_name}' must not exceed {rule.max_length} characters",
                        rule.field_name, value
                    )
            
            # Range validation for numbers
            if rule.input_type in [InputType.INTEGER, InputType.FLOAT]:
                if rule.min_value is not None and validated_value < rule.min_value:
                    raise ValidationError(
                        f"Field '{rule.field_name}' must be at least {rule.min_value}",
                        rule.field_name, value
                    )
                if rule.max_value is not None and validated_value > rule.max_value:
                    raise ValidationError(
                        f"Field '{rule.field_name}' must not exceed {rule.max_value}",
                        rule.field_name, value
                    )
            
            # Pattern validation
            if rule.pattern and isinstance(validated_value, str):
                if not re.match(rule.pattern, validated_value, re.IGNORECASE):
                    raise ValidationError(
                        f"Field '{rule.field_name}' format is invalid",
                        rule.field_name, value
                    )
            
            # Allowed values validation
            if rule.allowed_values and validated_value not in rule.allowed_values:
                raise ValidationError(
                    f"Field '{rule.field_name}' must be one of: {rule.allowed_values}",
                    rule.field_name, value
                )
            
            # Custom validation
            if rule.custom_validator and not rule.custom_validator(validated_value):
                raise ValidationError(
                    f"Field '{rule.field_name}' failed custom validation",
                    rule.field_name, value
                )
            
            # Security checks
            if isinstance(validated_value, str):
                self._check_security_threats(validated_value, rule.field_name)
            
            # Sanitization
            if rule.sanitize and isinstance(validated_value, str):
                validated_value = self._sanitize_string(validated_value, rule.input_type)
            
            return validated_value
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Validation error for field {rule.field_name}: {e}")
            raise ValidationError(f"Validation failed for field '{rule.field_name}': {str(e)}", rule.field_name, value)
    
    def _validate_type(self, value: Any, rule: ValidationRule) -> Any:
        """Validate and convert value to expected type"""
        try:
            if rule.input_type == InputType.STRING:
                return str(value)
            
            elif rule.input_type == InputType.INTEGER:
                if isinstance(value, str):
                    return int(value)
                elif isinstance(value, (int, float)):
                    return int(value)
                else:
                    raise ValidationError(f"Cannot convert {type(value)} to integer")
            
            elif rule.input_type == InputType.FLOAT:
                if isinstance(value, str):
                    return float(value)
                elif isinstance(value, (int, float)):
                    return float(value)
                else:
                    raise ValidationError(f"Cannot convert {type(value)} to float")
            
            elif rule.input_type == InputType.BOOLEAN:
                if isinstance(value, bool):
                    return value
                elif isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                elif isinstance(value, int):
                    return bool(value)
                else:
                    raise ValidationError(f"Cannot convert {type(value)} to boolean")
            
            elif rule.input_type == InputType.EMAIL:
                email_str = str(value).lower().strip()
                if not re.match(self.patterns['email'], email_str):
                    raise ValidationError("Invalid email format")
                return email_str
            
            elif rule.input_type == InputType.URL:
                url_str = str(value).strip()
                if not re.match(self.patterns['url'], url_str):
                    raise ValidationError("Invalid URL format")
                return url_str
            
            elif rule.input_type == InputType.IP_ADDRESS:
                try:
                    ip = ipaddress.ip_address(str(value).strip())
                    return str(ip)
                except ValueError:
                    raise ValidationError("Invalid IP address format")
            
            elif rule.input_type == InputType.FILE_PATH:
                path_str = str(value).strip()
                # Security check for path traversal
                if '..' in path_str or path_str.startswith('/') or '\\\\' in path_str:
                    raise ValidationError("Invalid file path: potential directory traversal")
                
                # Check file extension
                path = Path(path_str)
                if path.suffix.lower() in self.dangerous_extensions:
                    raise ValidationError(f"Dangerous file extension: {path.suffix}")
                
                return path_str
            
            elif rule.input_type == InputType.JSON:
                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError as e:
                        raise ValidationError(f"Invalid JSON: {e}")
                else:
                    return value  # Already parsed
            
            elif rule.input_type == InputType.PIN:
                pin_str = str(value).strip()
                if not re.match(self.patterns['pin'], pin_str):
                    raise ValidationError("PIN must be 4-8 digits")
                return pin_str
            
            elif rule.input_type == InputType.API_KEY:
                key_str = str(value).strip()
                if not re.match(self.patterns['api_key'], key_str):
                    raise ValidationError("Invalid API key format")
                return key_str
            
            elif rule.input_type == InputType.UUID:
                uuid_str = str(value).lower().strip()
                if not re.match(self.patterns['uuid'], uuid_str):
                    raise ValidationError("Invalid UUID format")
                return uuid_str
            
            elif rule.input_type == InputType.COMMAND:
                cmd_str = str(value).strip()
                if not re.match(self.patterns['command_safe'], cmd_str):
                    raise ValidationError("Command contains unsafe characters")
                return cmd_str
            
            else:
                return str(value)
                
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Type conversion failed: {e}")
    
    def _check_security_threats(self, value: str, field_name: str):
        """Check for common security threats in string inputs"""
        value_lower = value.lower()
        
        # SQL Injection detection
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                if AUDIT_AVAILABLE:
                    audit_security_event(
                        f"SQL injection attempt detected in field {field_name}: {value[:100]}",
                        SeverityLevel.HIGH
                    )
                raise ValidationError(f"Potential SQL injection detected in field '{field_name}'")
        
        # XSS detection
        for pattern in self.xss_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                if AUDIT_AVAILABLE:
                    audit_security_event(
                        f"XSS attempt detected in field {field_name}: {value[:100]}",
                        SeverityLevel.HIGH
                    )
                raise ValidationError(f"Potential XSS attack detected in field '{field_name}'")
        
        # Command injection detection
        for pattern in self.command_injection_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                if AUDIT_AVAILABLE:
                    audit_security_event(
                        f"Command injection attempt detected in field {field_name}: {value[:100]}",
                        SeverityLevel.HIGH
                    )
                raise ValidationError(f"Potential command injection detected in field '{field_name}'")
    
    def _sanitize_string(self, value: str, input_type: InputType) -> str:
        """Sanitize string input based on type"""
        if input_type == InputType.HTML:
            # HTML sanitization (escape dangerous characters)
            return html.escape(value, quote=True)
        
        elif input_type == InputType.URL:
            # URL encoding for unsafe characters
            return urllib.parse.quote(value, safe=":/?#[]@!$&'()*+,;=")
        
        elif input_type == InputType.STRING:
            # Basic string sanitization
            # Remove null bytes and control characters
            sanitized = re.sub(r'[\\x00-\\x1f\\x7f-\\x9f]', '', value)
            # Normalize whitespace
            sanitized = ' '.join(sanitized.split())
            return sanitized.strip()
        
        else:
            return value.strip()
    
    def validate_dict(self, data: Dict[str, Any], rules: List[ValidationRule]) -> Dict[str, Any]:
        """
        Validate a dictionary against a set of rules
        
        Args:
            data: Dictionary to validate
            rules: List of validation rules
            
        Returns:
            Validated and sanitized dictionary
            
        Raises:
            ValidationError: If any field fails validation
        """
        validated_data = {}
        errors = []
        
        # Create rule lookup
        rule_map = {rule.field_name: rule for rule in rules}
        
        # Validate each field
        for field_name, rule in rule_map.items():
            try:
                value = data.get(field_name)
                validated_value = self.validate_field(value, rule)
                if validated_value is not None:  # Don't include None values
                    validated_data[field_name] = validated_value
            except ValidationError as e:
                errors.append(e)
        
        # Check for unexpected fields
        expected_fields = set(rule_map.keys())
        provided_fields = set(data.keys())
        unexpected_fields = provided_fields - expected_fields
        
        if unexpected_fields:
            logger.warning(f"Unexpected fields in input: {unexpected_fields}")
            # Optionally reject unexpected fields
            # errors.append(ValidationError(f"Unexpected fields: {unexpected_fields}"))
        
        if errors:
            # Combine error messages
            error_messages = [str(e) for e in errors]
            raise ValidationError(f"Validation failed: {'; '.join(error_messages)}")
        
        return validated_data
    
    def validate_api_request(self, data: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
        """Validate API request data based on endpoint"""
        rules = self._get_api_rules(endpoint)
        return self.validate_dict(data, rules)
    
    def _get_api_rules(self, endpoint: str) -> List[ValidationRule]:
        """Get validation rules for specific API endpoints"""
        # Common API validation rules
        common_rules = {
            '/api/auth/login': [
                ValidationRule('pin', InputType.PIN, required=True, description='User PIN')
            ],
            '/api/chat': [
                ValidationRule('message', InputType.STRING, required=True, max_length=10000, description='Chat message'),
                ValidationRule('session_id', InputType.UUID, required=False, description='Session identifier'),
                ValidationRule('model_preference', InputType.STRING, required=False, 
                             allowed_values=['gpt-4', 'gpt-3.5-turbo', 'claude', 'gemini'], description='AI model preference')
            ],
            '/api/system/command': [
                ValidationRule('command', InputType.COMMAND, required=True, max_length=500, description='System command'),
                ValidationRule('user_id', InputType.STRING, required=True, description='User identifier')
            ],
            '/api/settings': [
                ValidationRule('setting_name', InputType.STRING, required=True, max_length=100, description='Setting name'),
                ValidationRule('setting_value', InputType.STRING, required=True, max_length=1000, description='Setting value')
            ],
            '/api/file/upload': [
                ValidationRule('filename', InputType.FILE_PATH, required=True, description='File name'),
                ValidationRule('content_type', InputType.STRING, required=True, 
                             allowed_values=['text/plain', 'application/json', 'image/jpeg', 'image/png'],
                             description='File content type')
            ]
        }
        
        return common_rules.get(endpoint, [])


class WebSocketValidator:
    """Specialized validator for WebSocket messages"""
    
    def __init__(self, input_validator: InputValidator):
        self.validator = input_validator
        
        # WebSocket message types and their validation rules
        self.message_rules = {
            'chat': [
                ValidationRule('type', InputType.STRING, required=True, allowed_values=['chat']),
                ValidationRule('message', InputType.STRING, required=True, max_length=10000),
                ValidationRule('session_id', InputType.STRING, required=False)
            ],
            'command': [
                ValidationRule('type', InputType.STRING, required=True, allowed_values=['command']),
                ValidationRule('command', InputType.STRING, required=True, max_length=500),
                ValidationRule('parameters', InputType.JSON, required=False)
            ],
            'system': [
                ValidationRule('type', InputType.STRING, required=True, allowed_values=['system']),
                ValidationRule('action', InputType.STRING, required=True, 
                             allowed_values=['status', 'stats', 'config']),
                ValidationRule('data', InputType.JSON, required=False)
            ]
        }
    
    def validate_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Validate WebSocket message"""
        # Validate message structure
        if not isinstance(message, dict):
            raise ValidationError("WebSocket message must be a JSON object")
        
        message_type = message.get('type')
        if not message_type:
            raise ValidationError("WebSocket message must include 'type' field")
        
        rules = self.message_rules.get(message_type, [])
        if not rules:
            raise ValidationError(f"Unknown WebSocket message type: {message_type}")
        
        return self.validator.validate_dict(message, rules)


class CLIValidator:
    """Specialized validator for CLI command inputs"""
    
    def __init__(self, input_validator: InputValidator):
        self.validator = input_validator
    
    def validate_command_args(self, args: List[str]) -> List[str]:
        """Validate CLI command arguments"""
        validated_args = []
        
        for arg in args:
            # Basic sanitization
            if not isinstance(arg, str):
                raise ValidationError(f"Command argument must be string, got {type(arg)}")
            
            # Check for injection attempts
            self.validator._check_security_threats(arg, 'cli_argument')
            
            # Sanitize
            sanitized_arg = self.validator._sanitize_string(arg, InputType.COMMAND)
            validated_args.append(sanitized_arg)
        
        return validated_args
    
    def validate_file_path(self, file_path: str) -> str:
        """Validate file path for CLI operations"""
        rule = ValidationRule('file_path', InputType.FILE_PATH, required=True)
        return self.validator.validate_field(file_path, rule)


# Global validator instances
_input_validator = None
_websocket_validator = None
_cli_validator = None

def get_input_validator() -> InputValidator:
    """Get global input validator instance"""
    global _input_validator
    if _input_validator is None:
        _input_validator = InputValidator()
    return _input_validator

def get_websocket_validator() -> WebSocketValidator:
    """Get WebSocket validator instance"""
    global _websocket_validator
    if _websocket_validator is None:
        _websocket_validator = WebSocketValidator(get_input_validator())
    return _websocket_validator

def get_cli_validator() -> CLIValidator:
    """Get CLI validator instance"""
    global _cli_validator
    if _cli_validator is None:
        _cli_validator = CLIValidator(get_input_validator())
    return _cli_validator


# Convenience functions for common validation scenarios
def validate_api_input(data: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
    """Validate API input data"""
    return get_input_validator().validate_api_request(data, endpoint)

def validate_websocket_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Validate WebSocket message"""
    return get_websocket_validator().validate_message(message)

def validate_cli_command(args: List[str]) -> List[str]:
    """Validate CLI command arguments"""
    return get_cli_validator().validate_command_args(args)

def validate_pin(pin: str) -> str:
    """Validate PIN format"""
    rule = ValidationRule('pin', InputType.PIN, required=True)
    return get_input_validator().validate_field(pin, rule)

def validate_email(email: str) -> str:
    """Validate email address"""
    rule = ValidationRule('email', InputType.EMAIL, required=True)
    return get_input_validator().validate_field(email, rule)

def validate_file_upload(filename: str, content_type: str) -> Dict[str, str]:
    """Validate file upload parameters"""
    rules = [
        ValidationRule('filename', InputType.FILE_PATH, required=True),
        ValidationRule('content_type', InputType.STRING, required=True)
    ]
    data = {'filename': filename, 'content_type': content_type}
    return get_input_validator().validate_dict(data, rules)


if __name__ == "__main__":
    # Test input validation system
    logger.debug("Testing input validation system...")
    
    validator = InputValidator()
    
    # Test API validation
    try:
        login_data = {'pin': '1234'}
        validated = validate_api_input(login_data, '/api/auth/login')
        print(f"Valid login data: {validated}")
    except ValidationError as e:
        print(f"Login validation error: {e}")
    
    # Test WebSocket validation
    try:
        ws_message = {
            'type': 'chat',
            'message': 'Hello, assistant!',
            'session_id': 'abc123'
        }
        validated_ws = validate_websocket_message(ws_message)
        print(f"Valid WebSocket message: {validated_ws}")
    except ValidationError as e:
        print(f"WebSocket validation error: {e}")
    
    # Test security detection
    try:
        malicious_input = "'; DROP TABLE users; --"
        validator._check_security_threats(malicious_input, 'test_field')
    except ValidationError as e:
        print(f"Security threat detected: {e}")
    
    # Test file validation
    try:
        safe_file = validate_file_upload('document.pdf', 'application/pdf')
        print(f"Valid file upload: {safe_file}")
    except ValidationError as e:
        print(f"File validation error: {e}")
    
    logger.info("✅ Input validation test completed!")
    