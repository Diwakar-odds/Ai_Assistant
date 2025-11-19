# YourDaddy Assistant Modules Package
"""
Modular architecture for YourDaddy AI Assistant

This package contains specialized modules for different functionality:
- core: Basic Windows automation and file operations
- memory: Enhanced memory and knowledge management
- system: System monitoring and maintenance
- calendar: Google Calendar integration
- email: Email management (future)
- media: Music/media control (future)
- web: Web scraping and online services (future)
- vision: Computer vision and OCR (future)
"""

__version__ = "3.0.0"
__author__ = "YourDaddy AI Assistant"

# Import all main functions for backward compatibility
from .core import *
from .memory import *
from .system import *
from .google_calendar import *
from .email_handler import *
from .music import *
from .file_ops import *
from .web_scraping import *
from .document_ocr import *