# YourDaddy Assistant - Modular Automation Tools
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
# Function Name -> Module Path
_LAZY_IMPORTS = {
    # Core functions
    'write_a_note': 'ai_assistant.modules.core',
    'open_application': 'ai_assistant.modules.core',
    'open_settings_page': 'ai_assistant.modules.core',
    'search_google': 'ai_assistant.modules.core',
    'search_youtube': 'ai_assistant.modules.core',
    'close_application': 'ai_assistant.modules.core',
    'speak': 'ai_assistant.modules.core',
    'set_system_volume': 'ai_assistant.modules.core',
    'extract_number': 'ai_assistant.modules.core',
    'scan_and_save_apps': 'ai_assistant.modules.core',
    'get_app_path_from_name': 'ai_assistant.modules.core',
    'write_to_file': 'ai_assistant.modules.core',

    # App Discovery
    'discover_applications': 'ai_assistant.modules.app_discovery',
    'smart_open_application': 'ai_assistant.modules.app_discovery',
    'refresh_app_database': 'ai_assistant.modules.app_discovery',
    'list_installed_apps': 'ai_assistant.modules.app_discovery',
    'get_apps_for_web': 'ai_assistant.modules.app_discovery',
    'search_apps_by_name': 'ai_assistant.modules.app_discovery',
    'get_app_usage_stats': 'ai_assistant.modules.app_discovery',

    # Memory Management
    'setup_memory': 'ai_assistant.modules.memory',
    'save_to_memory': 'ai_assistant.modules.memory',
    'get_memory': 'ai_assistant.modules.memory',
    'search_memory': 'ai_assistant.modules.memory',
    'get_conversation_summary': 'ai_assistant.modules.memory',
    'save_knowledge': 'ai_assistant.modules.memory',
    'get_knowledge': 'ai_assistant.modules.memory',

    # System Monitoring
    'get_system_status': 'ai_assistant.modules.system',
    'get_running_processes': 'ai_assistant.modules.system',
    'cleanup_temp_files': 'ai_assistant.modules.system',
    'get_network_info': 'ai_assistant.modules.system',
    'monitor_system_alerts': 'ai_assistant.modules.system',
    'get_system_info': 'ai_assistant.modules.system',
    'get_battery_status': 'ai_assistant.modules.system',

    # Calendar
    'setup_calendar_auth': 'ai_assistant.modules.google_calendar',
    'get_upcoming_events': 'ai_assistant.modules.google_calendar',
    'create_calendar_event': 'ai_assistant.modules.google_calendar',
    'get_todays_schedule': 'ai_assistant.modules.google_calendar',
    'search_calendar_events': 'ai_assistant.modules.google_calendar',
    'delete_calendar_event': 'ai_assistant.modules.google_calendar',

    # Email
    'setup_email_auth': 'ai_assistant.modules.email_handler',
    'get_inbox_summary': 'ai_assistant.modules.email_handler',
    'send_email': 'ai_assistant.modules.email_handler',
    'search_emails': 'ai_assistant.modules.email_handler',
    'read_email_content': 'ai_assistant.modules.email_handler',
    'get_unread_count': 'ai_assistant.modules.email_handler',
    'mark_email_read': 'ai_assistant.modules.email_handler',
    'delete_email': 'ai_assistant.modules.email_handler',
    'compose_quick_reply': 'ai_assistant.modules.email_handler',

    # Music
    'get_spotify_status': 'ai_assistant.modules.music',
    'spotify_play_pause': 'ai_assistant.modules.music',
    'spotify_next_track': 'ai_assistant.modules.music',
    'spotify_previous_track': 'ai_assistant.modules.music',
    'search_and_play_spotify': 'ai_assistant.modules.music',
    'get_media_players': 'ai_assistant.modules.music',
    'control_media_player': 'ai_assistant.modules.music',
    'get_system_volume': 'ai_assistant.modules.music',
    'create_spotify_playlist': 'ai_assistant.modules.music',
    'get_music_recommendations': 'ai_assistant.modules.music',

    # File Operations
    'organize_files_by_type': 'ai_assistant.modules.file_ops',
    'find_duplicate_files': 'ai_assistant.modules.file_ops',
    'remove_duplicate_files': 'ai_assistant.modules.file_ops',
    'create_backup_archive': 'ai_assistant.modules.file_ops',
    'smart_file_search': 'ai_assistant.modules.file_ops',
    'batch_rename_files': 'ai_assistant.modules.file_ops',
    'analyze_directory_structure': 'ai_assistant.modules.file_ops',
    'sync_directories': 'ai_assistant.modules.file_ops',

    # Web Scraping
    'get_weather_info': 'ai_assistant.modules.web_scraping',
    'get_weather_forecast': 'ai_assistant.modules.web_scraping',
    'get_latest_news': 'ai_assistant.modules.web_scraping',
    'search_web': 'ai_assistant.modules.web_scraping',
    'get_stock_price': 'ai_assistant.modules.web_scraping',
    'get_crypto_price': 'ai_assistant.modules.web_scraping',
    'scrape_website_content': 'ai_assistant.modules.web_scraping',
    'get_trending_topics': 'ai_assistant.modules.web_scraping',
    'monitor_rss_feeds': 'ai_assistant.modules.web_scraping',
    'get_product_price': 'ai_assistant.modules.web_scraping',

    # Research
    'research_topic': 'ai_assistant.modules.research',

    # WhatsApp
    'send_whatsapp_message': 'ai_assistant.modules.whatsapp',

    # Document OCR
    'check_ocr_dependencies': 'ai_assistant.modules.document_ocr',
    'extract_text_from_image': 'ai_assistant.modules.document_ocr',
    'extract_text_from_pdf': 'ai_assistant.modules.document_ocr',
    'analyze_document_structure': 'ai_assistant.modules.document_ocr',
    'preprocess_image_for_ocr': 'ai_assistant.modules.document_ocr',
    'extract_key_information': 'ai_assistant.modules.document_ocr',
    'batch_ocr_directory': 'ai_assistant.modules.document_ocr',
    'summarize_document_content': 'ai_assistant.modules.document_ocr',

    # Taskbar (Local override below, but can map for consistency)
    'detect_taskbar_apps': 'ai_assistant.modules.taskbar_detection',
    'can_see_taskbar': 'ai_assistant.modules.taskbar_detection',

    # Multimodal
    'MultiModalAI': 'ai_assistant.modules.multimodal',
    'analyze_current_screen': 'ai_assistant.modules.multimodal',
    'answer_visual_question_quick': 'ai_assistant.modules.multimodal',
    'extract_screen_text': 'ai_assistant.modules.multimodal',
    'describe_current_screen': 'ai_assistant.modules.multimodal',

    # Conversational AI
    'AdvancedConversationalAI': 'ai_assistant.modules.conversational_ai',
    'ConversationState': 'ai_assistant.modules.conversational_ai',
    'MoodType': 'ai_assistant.modules.conversational_ai',
    'create_conversation_context': 'ai_assistant.modules.conversational_ai',
    'switch_conversation_context': 'ai_assistant.modules.conversational_ai',
    'add_conversation_message': 'ai_assistant.modules.conversational_ai',
    'get_conversation_suggestions': 'ai_assistant.modules.conversational_ai',
    'detect_user_mood': 'ai_assistant.modules.conversational_ai',

    # Smart Automation
    'SmartAutomationEngine': 'ai_assistant.modules.smart_automation',
    'WorkflowDefinition': 'ai_assistant.modules.smart_automation',
    'WorkflowStatus': 'ai_assistant.modules.smart_automation',
    'create_simple_workflow': 'ai_assistant.modules.smart_automation',
    'execute_workflow_by_name': 'ai_assistant.modules.smart_automation',
    'suggest_automation_from_pattern': 'ai_assistant.modules.smart_automation',
    'get_workflow_status_simple': 'ai_assistant.modules.smart_automation',

    # Enhanced Learning
    'EnhancedLearningSystem': 'ai_assistant.modules.enhanced_learning',
    'BehavioralLearner': 'ai_assistant.modules.enhanced_learning',
    'SkillAcquisitionManager': 'ai_assistant.modules.enhanced_learning',
    'PredictiveActionEngine': 'ai_assistant.modules.enhanced_learning',
    'PersonalKnowledgeGraph': 'ai_assistant.modules.enhanced_learning',

    # Advanced Integration
    'AdvancedIntegrationManager': 'ai_assistant.modules.advanced_integration',
    'SystemHookManager': 'ai_assistant.modules.advanced_integration',
    'HardwareMonitor': 'ai_assistant.modules.advanced_integration',
    'PlatformAdapter': 'ai_assistant.modules.advanced_integration',

    # Modern Interfaces
    'ModernInterfaceManager': 'ai_assistant.modules.modern_interfaces',
    'WebInterface': 'ai_assistant.modules.modern_interfaces',
    'VoiceOnlyInterface': 'ai_assistant.modules.modern_interfaces',
    'MobileAppBackend': 'ai_assistant.modules.modern_interfaces',
    'InterfaceType': 'ai_assistant.modules.modern_interfaces',
    'VoiceMode': 'ai_assistant.modules.modern_interfaces',

    # Performance Optimization
    'PerformanceOptimizer': 'ai_assistant.modules.performance_optimization',
    'ResourceMonitor': 'ai_assistant.modules.performance_optimization',
    'SmartCache': 'ai_assistant.modules.performance_optimization',
    'MemoryManager': 'ai_assistant.modules.performance_optimization',
    'DatabaseOptimizer': 'ai_assistant.modules.performance_optimization',
    'AsyncTaskManager': 'ai_assistant.modules.performance_optimization',
    'OptimizationSettings': 'ai_assistant.modules.performance_optimization',
    'PerformanceLevel': 'ai_assistant.modules.performance_optimization',
}

# =============================================================================
# LAZY LOADING MACHINERY
# =============================================================================

def __getattr__(name: str) -> Any:
    """
    Lazy load modules/functions when accessed.
    This prevents importing all 15+ submodules at startup.
    """
    if name in _LAZY_IMPORTS:
        module_path = _LAZY_IMPORTS[name]
        try:
            module = importlib.import_module(module_path)
            # Cache it in globals to avoid subsequent lookups
            attr = getattr(module, name)
            globals()[name] = attr
            return attr
        except ImportError as e:
            print(f"⚠️ Lazy import failed for '{name}' from '{module_path}': {e}")
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
__author__ = "YourDaddy AI Assistant"

if __name__ != '__main__':
    print("✅ YourDaddy Automation Tools v4.2.0 - Lazy Loading Enabled")
    print(f"🔧 Registered Functions: {len(__all__)}")