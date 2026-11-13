# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

# Pulsar Assistant - Modular Automation Tools
"""
Main automation tools module that imports functionality from specialized modules.
This provides a clean interface while maintaining modular architecture.
⚡ LAZY LOADING ENABLED: Modules are imported only when their functions are accessed.

Architecture:
- modules/core.py: Basic Windows automation and file operations
- modules/memory.py: Enhanced memory and knowledge management  
- modules/system.py: System monitoring and maintenance
- modules/calendar.py: Google Calendar integration
"""

import sys
import importlib
from typing import Any

# =============================================================================
# LAZY IMPORT MAPPING
# =============================================================================
# Function Name -> Module Path (Mapped to active codebase namespaces)
_LAZY_IMPORTS = {
    # Core functions
    'write_a_note': 'ai_assistant.core.core',
    'open_application': 'ai_assistant.core.core',
    'open_settings_page': 'ai_assistant.core.core',
    'search_google': 'ai_assistant.core.core',
    'search_youtube': 'ai_assistant.core.core',
    'close_application': 'ai_assistant.core.core',
    'set_system_volume': 'ai_assistant.core.core',
    'get_system_volume': 'ai_assistant.core.core',
    'extract_number': 'ai_assistant.core.core',
    'scan_and_save_apps': 'ai_assistant.core.core',
    'get_app_path_from_name': 'ai_assistant.core.core',
    'write_to_file': 'ai_assistant.core.core',

    # App Discovery
    'discover_applications': 'ai_assistant.automation.app_discovery',
    'smart_open_application': 'ai_assistant.automation.app_discovery',
    'refresh_app_database': 'ai_assistant.automation.app_discovery',
    'list_installed_apps': 'ai_assistant.automation.app_discovery',
    'get_apps_for_web': 'ai_assistant.automation.app_discovery',
    'search_apps_by_name': 'ai_assistant.automation.app_discovery',
    'get_app_usage_stats': 'ai_assistant.automation.app_discovery',

    # Memory Management
    'setup_memory': 'ai_assistant.ai.memory',
    'save_to_memory': 'ai_assistant.ai.memory',
    'get_memory': 'ai_assistant.ai.memory',
    'search_memory': 'ai_assistant.ai.memory',
    'get_conversation_summary': 'ai_assistant.ai.memory',
    'save_knowledge': 'ai_assistant.ai.memory',
    'get_knowledge': 'ai_assistant.ai.memory',

    # System Monitoring
    'get_system_status': 'ai_assistant.core.system',
    'get_running_processes': 'ai_assistant.core.system',
    'cleanup_temp_files': 'ai_assistant.core.system',
    'get_network_info': 'ai_assistant.core.system',
    'monitor_system_alerts': 'ai_assistant.core.system',
    'get_system_info': 'ai_assistant.core.system',
    'get_battery_status': 'ai_assistant.core.system',

    # Calendar
    'setup_calendar_auth': 'ai_assistant.integrations.google_calendar',
    'get_upcoming_events': 'ai_assistant.integrations.google_calendar',
    'create_calendar_event': 'ai_assistant.integrations.google_calendar',
    'get_todays_schedule': 'ai_assistant.integrations.google_calendar',
    'search_calendar_events': 'ai_assistant.integrations.google_calendar',
    'delete_calendar_event': 'ai_assistant.integrations.google_calendar',

    # Email
    'setup_email_auth': 'ai_assistant.integrations.email_handler',
    'get_inbox_summary': 'ai_assistant.integrations.email_handler',
    'send_email': 'ai_assistant.integrations.email_handler',
    'search_emails': 'ai_assistant.integrations.email_handler',
    'read_email_content': 'ai_assistant.integrations.email_handler',
    'get_unread_count': 'ai_assistant.integrations.email_handler',
    'mark_email_read': 'ai_assistant.integrations.email_handler',
    'delete_email': 'ai_assistant.integrations.email_handler',
    'compose_quick_reply': 'ai_assistant.integrations.email_handler',

    # Music
    'get_spotify_status': 'ai_assistant.integrations.music',
    'spotify_play_pause': 'ai_assistant.integrations.music',
    'spotify_next_track': 'ai_assistant.integrations.music',
    'spotify_previous_track': 'ai_assistant.integrations.music',
    'search_and_play_spotify': 'ai_assistant.integrations.music',
    'get_media_players': 'ai_assistant.integrations.music',
    'control_media_player': 'ai_assistant.integrations.music',
    'create_spotify_playlist': 'ai_assistant.integrations.music',
    'get_music_recommendations': 'ai_assistant.integrations.music',

    # File Operations
    'organize_files_by_type': 'ai_assistant.utils.file_ops',
    'find_duplicate_files': 'ai_assistant.utils.file_ops',
    'remove_duplicate_files': 'ai_assistant.utils.file_ops',
    'create_backup_archive': 'ai_assistant.utils.file_ops',
    'smart_file_search': 'ai_assistant.utils.file_ops',
    'batch_rename_files': 'ai_assistant.utils.file_ops',
    'analyze_directory_structure': 'ai_assistant.utils.file_ops',
    'sync_directories': 'ai_assistant.utils.file_ops',

    # Web Scraping
    'get_weather_info': 'ai_assistant.integrations.web_scraping',
    'get_weather_forecast': 'ai_assistant.integrations.web_scraping',
    'get_latest_news': 'ai_assistant.integrations.web_scraping',
    'search_web': 'ai_assistant.integrations.web_scraping',
    'get_stock_price': 'ai_assistant.integrations.web_scraping',
    'get_crypto_price': 'ai_assistant.integrations.web_scraping',
    'scrape_website_content': 'ai_assistant.integrations.web_scraping',
    'get_trending_topics': 'ai_assistant.integrations.web_scraping',
    'monitor_rss_feeds': 'ai_assistant.integrations.web_scraping',
    'get_product_price': 'ai_assistant.integrations.web_scraping',

    # Research
    'research_topic': 'ai_assistant.integrations.research',

    # WhatsApp
    'send_whatsapp_message': 'ai_assistant.integrations.whatsapp',

    # Document OCR
    'check_ocr_dependencies': 'ai_assistant.vision.document_ocr',
    'extract_text_from_image': 'ai_assistant.vision.document_ocr',
    'extract_text_from_pdf': 'ai_assistant.vision.document_ocr',
    'analyze_document_structure': 'ai_assistant.vision.document_ocr',
    'preprocess_image_for_ocr': 'ai_assistant.vision.document_ocr',
    'extract_key_information': 'ai_assistant.vision.document_ocr',
    'batch_ocr_directory': 'ai_assistant.vision.document_ocr',
    'summarize_document_content': 'ai_assistant.vision.document_ocr',

    # Taskbar Detection
    'detect_taskbar_apps': 'ai_assistant.automation.app_discovery',
    'can_see_taskbar': 'ai_assistant.automation.app_discovery',

    # Multimodal
    'MultiModalAI': 'ai_assistant.vision.multimodal',
    'analyze_current_screen': 'ai_assistant.vision.multimodal',
    'answer_visual_question_quick': 'ai_assistant.vision.multimodal',
    'extract_screen_text': 'ai_assistant.vision.multimodal',
    'describe_current_screen': 'ai_assistant.vision.multimodal',

    # Conversational AI
    'AdvancedConversationalAI': 'ai_assistant.ai.conversational_ai',
    'ConversationState': 'ai_assistant.ai.conversational_ai',
    'MoodType': 'ai_assistant.ai.conversational_ai',
    'create_conversation_context': 'ai_assistant.ai.conversational_ai',
    'switch_conversation_context': 'ai_assistant.ai.conversational_ai',
    'add_conversation_message': 'ai_assistant.ai.conversational_ai',
    'get_conversation_suggestions': 'ai_assistant.ai.conversational_ai',
    'detect_user_mood': 'ai_assistant.ai.conversational_ai',

    # Smart Automation
    'SmartAutomationEngine': 'ai_assistant.automation.automation_engine',
    'WorkflowDefinition': 'ai_assistant.automation.automation_engine',
    'WorkflowStatus': 'ai_assistant.automation.automation_engine',
    'create_simple_workflow': 'ai_assistant.automation.automation_engine',
    'execute_workflow_by_name': 'ai_assistant.automation.automation_engine',
    'suggest_automation_from_pattern': 'ai_assistant.automation.automation_engine',
    'get_workflow_status_simple': 'ai_assistant.automation.automation_engine',

    # Enhanced Learning
    'EnhancedLearningSystem': 'ai_assistant.ai.enhanced_learning',
    'BehavioralLearner': 'ai_assistant.ai.enhanced_learning',
    'SkillAcquisitionManager': 'ai_assistant.ai.enhanced_learning',
    'PredictiveActionEngine': 'ai_assistant.ai.enhanced_learning',
    'PersonalKnowledgeGraph': 'ai_assistant.ai.enhanced_learning',

    # Advanced Integration
    'AdvancedIntegrationManager': 'ai_assistant.automation.automation_engine',
    'SystemHookManager': 'ai_assistant.automation.automation_engine',
    'HardwareMonitor': 'ai_assistant.automation.automation_engine',
    'PlatformAdapter': 'ai_assistant.automation.automation_engine',

    # Performance Optimization
    'PerformanceOptimizer': 'ai_assistant.core.performance_optimization',
    'ResourceMonitor': 'ai_assistant.core.performance_optimization',
    'SmartCache': 'ai_assistant.core.performance_optimization',
    'MemoryManager': 'ai_assistant.core.memory_manager',
    'DatabaseOptimizer': 'ai_assistant.core.performance_optimization',
    'AsyncTaskManager': 'ai_assistant.core.performance_optimization',
    'OptimizationSettings': 'ai_assistant.core.performance_optimization',
    'PerformanceLevel': 'ai_assistant.core.performance_optimization',
}

def speak(text: str, *args, **kwargs):
    """Fallback speak function delegating to active TTS service."""
    try:
        from ai_assistant.voice.tts_output_service import get_tts_service
        tts = get_tts_service()
        if tts:
            return tts.speak(text)
    except Exception:
        pass
    print(f"[Pulsar TTS]: {text}")
    return text

# Re-export speak explicitly
globals()['speak'] = speak

# =============================================================================
# LAZY LOADING MACHINERY
# =============================================================================

def __getattr__(name: str) -> Any:
    """
    Lazy load modules/functions when accessed.
    This prevents importing all 15+ submodules at startup.
    """
    if name == 'speak':
        return speak

    # Graceful fallback for legacy interface stubs
    if name in ('ModernInterfaceManager', 'WebInterface', 'VoiceOnlyInterface', 'MobileAppBackend', 'InterfaceType', 'VoiceMode'):
        dummy = type(name, (), {})
        globals()[name] = dummy
        return dummy

    if name in _LAZY_IMPORTS:
        module_path = _LAZY_IMPORTS[name]
        try:
            module = importlib.import_module(module_path)
            # Cache it in globals to avoid subsequent lookups
            attr = getattr(module, name)
            globals()[name] = attr
            return attr
        except (ImportError, AttributeError) as e:
            logger.warning(f"⚠️ Lazy import failed for '{name}' from '{module_path}': {e}")
            # Return dummy callable to prevent crashes
            if name[0].isupper(): # Likely a class
                 return type(name, (), {}) 
            return lambda *args, **kwargs: f"Error: {name} not available"
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# =============================================================================
# EXPORTS
# =============================================================================
# Re-export all functions so IDEs/tools know they exist
__all__ = list(_LAZY_IMPORTS.keys())

# Module version and information
__version__ = "4.2.0"
__author__ = "Pulsar AI Assistant"

if __name__ != '__main__':
    logger.info("✅ Pulsar Automation Tools v4.2.0 - Lazy Loading Enabled")
    # Tool count recorded cleanly in telemetry dashboard