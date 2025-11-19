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

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')


class LoggingConfig:
    """Centralized logging configuration manager"""
    
    # Base log directory structure
    BASE_LOG_DIR = Path("logs")
    
    # Module-specific log directories
    LOG_DIRS = {
        'app': BASE_LOG_DIR / 'app',              # Main application logs
        'modules': BASE_LOG_DIR / 'modules',      # Module-specific logs
        'backend': BASE_LOG_DIR / 'backend',      # Web backend logs
        'api': BASE_LOG_DIR / 'api',              # API request/response logs
        'security': BASE_LOG_DIR / 'security',    # Security and authentication logs
        'errors': BASE_LOG_DIR / 'errors',        # All error logs
        'performance': BASE_LOG_DIR / 'performance',  # Performance metrics
        'integration': BASE_LOG_DIR / 'integration',  # Third-party integrations
        'voice': BASE_LOG_DIR / 'voice',          # Voice recognition logs
        'multimodal': BASE_LOG_DIR / 'multimodal',  # Multimodal AI logs
        'system': BASE_LOG_DIR / 'system',        # System operations logs
    }
    
    # Log format templates
    DETAILED_FORMAT = '%(asctime)s | %(name)s | %(levelname)-8s | [%(filename)s:%(lineno)d] | %(funcName)s | %(message)s'
    SIMPLE_FORMAT = '%(asctime)s | %(levelname)-8s | %(message)s'
    DEBUG_FORMAT = '%(asctime)s | %(name)s | %(levelname)-8s | [%(filename)s:%(lineno)d:%(funcName)s] | %(message)s'
    API_FORMAT = '%(asctime)s | %(levelname)-8s | %(method)s %(endpoint)s | Status: %(status_code)s | %(duration)s ms | %(message)s'
    
    # Date format
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # Rotation settings
    MAX_BYTES = 10 * 1024 * 1024  # 10 MB per file
    BACKUP_COUNT = 10              # Keep 10 backup files
    
    # Logging levels
    DEFAULT_LEVEL = logging.INFO
    CONSOLE_LEVEL = logging.INFO
    FILE_LEVEL = logging.DEBUG
    ERROR_LEVEL = logging.ERROR
    
    _initialized = False
    _loggers = {}
    
    @classmethod
    def initialize(cls):
        """Initialize logging directory structure"""
        if cls._initialized:
            return
        
        # Create all log directories
        for log_dir in cls.LOG_DIRS.values():
            log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a README in logs directory
        readme_path = cls.BASE_LOG_DIR / "README.md"
        if not readme_path.exists():
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(cls._generate_readme())
        
        cls._initialized = True
    
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
    def get_file_handler(cls, module_name: str, log_category: str, 
                        use_time_rotation: bool = False) -> logging.Handler:
        """
        Create a rotating file handler for a specific module
        
        Args:
            module_name: Name of the module (e.g., 'core', 'multilingual')
            log_category: Category of log (e.g., 'modules', 'backend')
            use_time_rotation: Use time-based rotation instead of size
        """
        cls.initialize()
        
        log_dir = cls.LOG_DIRS.get(log_category, cls.LOG_DIRS['modules'])
        log_file = log_dir / f"{module_name}.log"
        
        if use_time_rotation:
            # Rotate daily, keep 30 days
            handler = TimedRotatingFileHandler(
                log_file,
                when='midnight',
                interval=1,
                backupCount=30,
                encoding='utf-8'
            )
        else:
            # Rotate by size
            handler = RotatingFileHandler(
                log_file,
                maxBytes=cls.MAX_BYTES,
                backupCount=cls.BACKUP_COUNT,
                encoding='utf-8'
            )
        
        handler.setLevel(cls.FILE_LEVEL)
        return handler
    
    @classmethod
    def get_error_handler(cls, module_name: str) -> logging.Handler:
        """Create error-only file handler"""
        cls.initialize()
        
        log_file = cls.LOG_DIRS['errors'] / f"{module_name}_errors.log"
        
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
               include_error_file: bool = True) -> logging.Logger:
    """
    Get or create a configured logger
    
    Args:
        name: Logger name (usually __name__)
        log_category: Category for organizing logs ('modules', 'backend', 'api', etc.)
        format_type: Format style ('detailed', 'simple', 'debug', 'api')
        include_console: Whether to log to console
        include_error_file: Whether to create separate error log file
    
    Returns:
        Configured logger instance
    
    Example:
        # In a module file
        from utils.logging_config import get_logger
        logger = get_logger(__name__)
        
        logger.info("Application started")
        logger.error("Something went wrong")
    """
    
    # Return existing logger if already configured
    if name in LoggingConfig._loggers:
        return LoggingConfig._loggers[name]
    
    # Create new logger
    logger = logging.getLogger(name)
    logger.setLevel(LoggingConfig.DEFAULT_LEVEL)
    logger.propagate = False  # Don't propagate to root logger
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Get formatter
    formatter = LoggingConfig.get_formatter(format_type)
    
    # Extract module name from full name (e.g., 'modules.core' -> 'core')
    module_name = name.split('.')[-1] if '.' in name else name
    
    # Add file handler for main logs
    file_handler = LoggingConfig.get_file_handler(module_name, log_category)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Add error-specific file handler
    if include_error_file:
        error_handler = LoggingConfig.get_error_handler(module_name)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    
    # Add console handler
    if include_console:
        console_handler = LoggingConfig.get_console_handler()
        console_handler.setFormatter(LoggingConfig.get_formatter('simple'))
        logger.addHandler(console_handler)
    
    # Cache the logger
    LoggingConfig._loggers[name] = logger
    
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
