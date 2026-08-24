"""
Logging Configuration for AI Assistant Modules
Centralized logger access point for core_ai package.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

try:
    from utils.logging_config import SessionManager, LoggingConfig, get_logger, get_api_logger
except ImportError:
    # Fallback to standard logging if backend utils not in sys.path
    class SessionManager:
        @classmethod
        def get_current_date(cls):
            from datetime import datetime
            return datetime.now().strftime('%Y-%m-%d')
            
        @classmethod
        def get_session_id(cls):
            return "default"

    class LoggingConfig:
        pass

    def get_logger(name: str, log_category: str = 'modules', **kwargs) -> logging.Logger:
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def get_api_logger(name: str = 'api_requests', **kwargs) -> logging.Logger:
        return get_logger(name, log_category='api')

__all__ = [
    'SessionManager',
    'LoggingConfig',
    'get_logger',
    'get_api_logger'
]
