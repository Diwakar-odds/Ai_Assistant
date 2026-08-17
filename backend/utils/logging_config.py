"""
Centralized Logging Configuration for YourDaddy Assistant
Provides organized, module-specific logging with proper rotation and formatting.

Usage:
    from utils.logging_config import get_logger
    
    logger = get_logger(__name__)  # For module logging
    logger.info("This is an info message")
    logger.error("This is an error message")
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from typing import Optional
import uuid
import os

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')


class SessionManager:
    """Manages logging sessions with unique identifiers"""
    
    _current_session = None
    _session_start_time = None
    _current_date = None
    
    @classmethod
    def get_current_date(cls):
        """Get current date in YYYY-MM-DD format for folder organization"""
        return datetime.now().strftime('%Y-%m-%d')
    
    @classmethod
    def start_new_session(cls):
        """Start a new logging session with timestamp"""
        cls._session_start_time = datetime.now()
        cls._current_session = cls._session_start_time.strftime('%H%M%S')  # Only time, not date
        cls._current_date = cls.get_current_date()
        
        # Create session info file
        session_info = {
            'session_id': cls._current_session,
            'start_time': cls._session_start_time.isoformat(),
            'assistant_version': '1.0.0',
            'python_version': sys.version,
            'platform': sys.platform
        }
        
        # Save session info in date-based folder
        date_folder = cls.get_current_date()
        session_file = Path('logs') / date_folder / 'sessions' / f'session_{cls._current_session}.json'
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(session_file, 'w') as f:
            json.dump(session_info, f, indent=2)
        
        # print(f"📅 New session started: {date_folder}/{cls._current_session}")
        return cls._current_session
    
    @classmethod
    def get_current_session(cls):
        """Get current session ID (returns None if no session started)"""
        return cls._current_session
    
    @classmethod
    def get_session_start_time(cls):
        """Get session start time"""
        return cls._session_start_time


class LoggingConfigMeta(type):
    @property
    def LOG_DIRS(cls):
        return cls.get_dated_log_dirs()


class LoggingConfig(metaclass=LoggingConfigMeta):
    """Centralized logging configuration manager"""
    
    # Base log directory structure
    BASE_LOG_DIR = Path("logs")
    
    @classmethod
    def get_dated_log_dirs(cls):
        """Get log directories organized by current date"""
        current_date = SessionManager.get_current_date()
        date_base = cls.BASE_LOG_DIR / current_date
        
        return {
            'app': date_base / 'app',              # Main application logs
            'modules': date_base / 'modules',      # Module-specific logs
            'backend': date_base / 'backend',      # Web backend logs
            'api': date_base / 'api',              # API request/response logs
            'security': date_base / 'security',    # Security and authentication logs
            'errors': date_base / 'errors',        # All error logs
            'performance': date_base / 'performance',  # Performance metrics
            'integration': date_base / 'integration',  # Third-party integrations
            'voice': date_base / 'voice',          # Voice recognition logs
            'multimodal': date_base / 'multimodal',  # Multimodal AI logs
            'system': date_base / 'system',        # System operations logs
            'sessions': date_base / 'sessions',    # Session information
            'activities': date_base / 'activities', # User activities per session
        }
    
    # Log format templates
    DETAILED_FORMAT = '%(asctime)s | %(name)s | %(levelname)-8s | [%(filename)s:%(lineno)d] | %(funcName)s | %(message)s'
    SIMPLE_FORMAT = '%(asctime)s | %(levelname)-8s | %(message)s'
    DEBUG_FORMAT = '%(asctime)s | %(name)s | %(levelname)-8s | [%(filename)s:%(lineno)d:%(funcName)s] | %(message)s'
    API_FORMAT = '%(asctime)s | %(levelname)-8s | API | %(message)s'
    
    # Date format
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # Rotation settings
    MAX_BYTES = 10 * 1024 * 1024  # 10 MB per file
    BACKUP_COUNT = 10              # Keep 10 backup files
    
    # Logging levels
    DEFAULT_LEVEL = logging.INFO
    CONSOLE_LEVEL = logging.WARNING
    FILE_LEVEL = logging.DEBUG
    ERROR_LEVEL = logging.ERROR
    
    _initialized = False
    _loggers = {}
    
    @classmethod
    def initialize(cls):
        """Initialize logging directory structure"""
        if cls._initialized:
            return
        
        # Create all log directories with date-based structure
        log_dirs = cls.get_dated_log_dirs()
        for log_dir in log_dirs.values():
            log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a README in logs directory
        readme_path = cls.BASE_LOG_DIR / "README.md"
        if not readme_path.exists():
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(cls._generate_readme())
        
        cls._initialized = True
        
        # Configure root logger to prevent stderr leakage
        root_logger = logging.getLogger()
        root_logger.setLevel(cls.DEFAULT_LEVEL)
        
        # Remove existing handlers to avoid duplication
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # Add console handler to root logger with configured level
        console_handler = cls.get_console_handler()
        console_handler.setFormatter(cls.get_formatter('simple'))
        root_logger.addHandler(console_handler)
    
    @classmethod
    def _generate_readme(cls) -> str:
        """Generate README for logs directory"""
        return f"""# YourDaddy Assistant - Logs Directory

## 📁 Directory Structure

This directory contains organized logs for all components of YourDaddy Assistant.

### Log Categories

- **app/** - Main application logs
  - `yourdaddy_app.log` - GUI application logs
  - `startup.log` - Application startup logs

- **backend/** - Web backend logs
  - `web_backend.log` - Flask backend logs
  - `socketio.log` - WebSocket communication logs

- **api/** - API request/response logs
  - `api_requests.log` - All API requests
  - `api_errors.log` - API-specific errors

- **modules/** - Module-specific logs
  - `core.log` - Core module operations
  - `multilingual.log` - Multilingual module
  - `multimodal.log` - Multimodal AI operations
  - `music.log` - Music control operations
  - `email.log` - Email operations
  - `calendar.log` - Calendar operations
  - `file_ops.log` - File operations
  - `automation.log` - Smart automation
  - `integration.log` - Third-party integrations

- **voice/** - Voice recognition logs
  - `voice_recognition.log` - Voice input logs
  - `wake_word.log` - Wake word detection

- **security/** - Security and authentication logs
  - `auth.log` - Authentication events
  - `security_events.log` - Security-related events
  - `rate_limit.log` - Rate limiting logs

- **errors/** - Consolidated error logs
  - `all_errors.log` - All application errors
  - `critical.log` - Critical errors only

- **performance/** - Performance metrics
  - `performance.log` - Performance measurements
  - `slow_queries.log` - Slow operations

- **system/** - System-level operations
  - `system_operations.log` - System commands
  - `process_monitor.log` - Process monitoring

- **integration/** - Third-party service logs
  - `google_calendar.log` - Google Calendar API
  - `gmail.log` - Gmail API
  - `spotify.log` - Spotify integration
  - `youtube.log` - YouTube operations

## 📊 Log Rotation

- **Max File Size:** 10 MB per file
- **Backup Count:** 10 backup files retained
- **Naming Convention:** `filename.log`, `filename.log.1`, `filename.log.2`, etc.
- **Old logs are automatically compressed and archived**

## 🔍 Log Levels

- **DEBUG** - Detailed debugging information
- **INFO** - General informational messages
- **WARNING** - Warning messages for potential issues
- **ERROR** - Error messages for failures
- **CRITICAL** - Critical errors requiring immediate attention

## 📝 Log Format

```
YYYY-MM-DD HH:MM:SS | ModuleName | LEVEL | [file.py:line] | function_name | Message
```

## 🧹 Maintenance

- Logs automatically rotate when they reach 10 MB
- Old backup files (beyond 10) are automatically deleted
- Manual cleanup can be done by removing `.log.*` numbered files

---

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    @classmethod
    def get_session_file_handler(cls, module_name: str, log_category: str, 
                               use_session_files: bool = True) -> logging.Handler:
        """
        Create a session-specific file handler
        
        Args:
            module_name: Name of the module
            log_category: Category of log
            use_session_files: Whether to use session-based naming
        """
        cls.initialize()
        
        log_dirs = cls.get_dated_log_dirs()
        log_dir = log_dirs.get(log_category, log_dirs['modules'])
        
        if use_session_files:
            session_id = SessionManager.get_current_session()
            log_file = log_dir / f"{module_name}_{session_id}.log"
        else:
            log_file = log_dir / f"{module_name}.log"
        
        # Use RotatingFileHandler for session files too
        handler = RotatingFileHandler(
            log_file,
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding='utf-8'
        )
        
        handler.setLevel(cls.FILE_LEVEL)
        return handler
    
    @classmethod
    def get_session_error_handler(cls, module_name: str) -> logging.Handler:
        """Create session-specific error-only file handler"""
        cls.initialize()
        
        session_id = SessionManager.get_current_session()
        log_file = cls.LOG_DIRS['errors'] / f"{module_name}_errors_{session_id}.log"
        
        handler = RotatingFileHandler(
            log_file,
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding='utf-8'
        )
        handler.setLevel(cls.ERROR_LEVEL)
        return handler
    
    @classmethod
    def get_console_handler(cls) -> logging.Handler:
        """Create console handler"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(cls.CONSOLE_LEVEL)
        return handler
    
    @classmethod
    def get_formatter(cls, format_type: str = 'detailed') -> logging.Formatter:
        """
        Get a log formatter
        
        Args:
            format_type: 'detailed', 'simple', 'debug', or 'api'
        """
        formats = {
            'detailed': cls.DETAILED_FORMAT,
            'simple': cls.SIMPLE_FORMAT,
            'debug': cls.DEBUG_FORMAT,
            'api': cls.API_FORMAT,
        }
        
        format_str = formats.get(format_type, cls.DETAILED_FORMAT)
        return logging.Formatter(format_str, datefmt=cls.DATE_FORMAT)


def get_logger(name: str, log_category: str = 'modules', 
               format_type: str = 'detailed',
               include_console: bool = True,
               include_error_file: bool = True,
               use_session_files: bool = True) -> logging.Logger:
    """
    Get or create a configured logger with session support
    
    Args:
        name: Logger name (usually __name__)
        log_category: Category for organizing logs ('modules', 'backend', 'api', etc.)
        format_type: Format style ('detailed', 'simple', 'debug', 'api')
        include_console: Whether to log to console
        include_error_file: Whether to create separate error log file
        use_session_files: Whether to use session-based file naming
    
    Returns:
        Configured logger instance
    """
    
    # Create session-specific logger name
    if use_session_files:
        session_id = SessionManager.get_current_session()
        # If no session yet, use placeholder (session_init.py will create one later)
        if session_id is None:
            session_id = 'PRESESSION'
        logger_key = f"{name}_{session_id}"
    else:
        logger_key = name
    
    # Return existing logger if already configured
    if logger_key in LoggingConfig._loggers:
        return LoggingConfig._loggers[logger_key]
    
    # Create new logger
    logger = logging.getLogger(logger_key)
    logger.setLevel(LoggingConfig.DEFAULT_LEVEL)
    logger.propagate = False  # Don't propagate to root logger
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Get formatter
    formatter = LoggingConfig.get_formatter(format_type)
    
    # Extract module name from full name (e.g., 'modules.core' -> 'core')
    module_name = name.split('.')[-1] if '.' in name else name
    
    # Add session-aware file handler for main logs
    file_handler = LoggingConfig.get_session_file_handler(module_name, log_category, use_session_files)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Add session-aware error-specific file handler
    if include_error_file:
        if use_session_files:
            error_handler = LoggingConfig.get_session_error_handler(module_name)
        else:
            error_handler = LoggingConfig.get_session_error_handler(module_name)  # Use session handler as fallback
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    
    # Add console handler
    if include_console:
        console_handler = LoggingConfig.get_console_handler()
        console_handler.setFormatter(LoggingConfig.get_formatter('simple'))
        logger.addHandler(console_handler)
    
    # Cache the logger
    LoggingConfig._loggers[logger_key] = logger
    
    # Log session start info for this module
    if use_session_files:
        session_start = SessionManager.get_session_start_time()
        if session_start:
            logger.info(f"📅 Session started at {session_start.strftime('%Y-%m-%d %H:%M:%S')} - Module: {module_name}")
    
    return logger


def get_api_logger(name: str = 'api') -> logging.Logger:
    """
    Get a logger configured specifically for API logging
    
    Returns:
        Logger with API-specific formatting
    """
    return get_logger(name, log_category='api', format_type='api')


def get_performance_logger(name: str = 'performance') -> logging.Logger:
    """
    Get a logger configured for performance metrics
    
    Returns:
        Logger for performance logging
    """
    return get_logger(name, log_category='performance', include_console=False)


def log_api_request(logger: logging.Logger, method: str, endpoint: str, 
                   status_code: int, duration_ms: float, message: str = ""):
    """
    Helper function to log API requests with consistent formatting
    
    Args:
        logger: Logger instance
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        message: Optional additional message
    """
    extra = {
        'method': method,
        'endpoint': endpoint,
        'status_code': status_code,
        'duration': f"{duration_ms:.2f}"
    }
    
    if status_code >= 500:
        logger.error(message or "Server error", extra=extra)
    elif status_code >= 400:
        logger.warning(message or "Client error", extra=extra)
    else:
        logger.info(message or "Request completed", extra=extra)


# Initialize logging on module import
LoggingConfig.initialize()


# Example usage and testing
if __name__ == "__main__":
    # Test the logging system
    print("Testing YourDaddy Logging System\n")
    
    # Test different module loggers
    app_logger = get_logger('yourdaddy_app', log_category='app')
    app_logger.info("✅ Application started successfully")
    app_logger.warning("⚠️ This is a warning message")
    app_logger.error("❌ This is an error message")
    
    # Test module logger
    core_logger = get_logger('modules.core', log_category='modules')
    core_logger.info("Core module initialized")
    core_logger.debug("Debug information")
    
    # Test backend logger
    backend_logger = get_logger('backend', log_category='backend')
    backend_logger.info("Backend server starting on port 5000")
    
    # Test API logger
    api_logger = get_api_logger()
    log_api_request(api_logger, 'GET', '/api/chat', 200, 45.3, "Chat request successful")
    log_api_request(api_logger, 'POST', '/api/voice', 500, 123.4, "Voice processing failed")
    
    print("\n✅ Logging test complete!")
    print(f"📁 Check logs in: {LoggingConfig.BASE_LOG_DIR}")
    print("\nLog structure created:")
    for category, path in LoggingConfig.LOG_DIRS.items():
        print(f"  - {category}/: {path}")
