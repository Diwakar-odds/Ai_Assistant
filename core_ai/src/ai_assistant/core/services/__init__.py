"""
Services Package for ModernAssistant

Contains extracted service classes for better modularity:
- CommandProcessor: Command processing and multilingual support
- MonitoringService: System monitoring and statistics
- AIServiceManager: AI service management
- VoiceServiceManager: Voice service management
- Initialization Service: Initialization logic
"""

__all__ = [
    'CommandProcessor',
    'MonitoringService',
    'AIServiceManager',
    'VoiceServiceManager',
    'InitializationService'
]

try:
    from .command_processor import CommandProcessor
except ImportError:
    CommandProcessor = None

try:
    from .monitoring_service import MonitoringService
except ImportError:
    MonitoringService = None

try:
    from .ai_service_manager import AIServiceManager
except ImportError:
    AIServiceManager = None

try:
    from ai_assistant.services.voice_service import VoiceServiceManager
except ImportError:
    VoiceServiceManager = None

try:
    from .initialization_service import InitializationService
except ImportError:
    InitializationService = None
