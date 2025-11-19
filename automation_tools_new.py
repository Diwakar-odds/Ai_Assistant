# YourDaddy Assistant - Modular Automation Tools
"""
Main automation tools module that imports functionality from specialized modules.
This provides a clean interface while maintaining modular architecture.

Architecture:
- modules/core.py: Basic Windows automation and file operations
- modules/memory.py: Enhanced memory and knowledge management  
- modules/system.py: System monitoring and maintenance
- modules/calendar.py: Google Calendar integration
"""

# Import all core automation functions
from modules.core import (
    write_a_note,
    open_application,
    open_settings_page,
    search_google,
    search_youtube,
    close_application,
    speak,
    set_system_volume,
    extract_number,
    scan_and_save_apps,
    get_app_path_from_name,
    write_to_file
)

# Import app discovery functions
from modules.app_discovery import (
    discover_applications,
    smart_open_application,
    refresh_app_database,
    list_installed_apps,
    get_apps_for_web,
    search_apps_by_name,
    get_app_usage_stats
)

# Import memory management functions
from modules.memory import (
    setup_memory,
    save_to_memory,
    get_memory,
    search_memory,
    get_conversation_summary,
    save_knowledge,
    get_knowledge
)

# Import system monitoring functions
from modules.system import (
    get_system_status,
    get_running_processes,
    cleanup_temp_files,
    get_network_info,
    monitor_system_alerts,
    get_system_info,
    get_battery_status
)

# Import calendar functions
from modules.google_calendar import (
    setup_calendar_auth,
    get_upcoming_events,
    create_calendar_event,
    get_todays_schedule,
    search_calendar_events,
    delete_calendar_event
)

# Import email functions
from modules.email_handler import (
    setup_email_auth,
    get_inbox_summary,
    send_email,
    search_emails,
    read_email_content,
    get_unread_count,
    mark_email_read,
    delete_email,
    compose_quick_reply
)

# Import music functions
from modules.music import (
    get_spotify_status,
    spotify_play_pause,
    spotify_next_track,
    spotify_previous_track,
    search_and_play_spotify,
    get_media_players,
    control_media_player,
    get_system_volume,
    set_system_volume,
    create_spotify_playlist,
    get_music_recommendations
)

# Import file operations functions
from modules.file_ops import (
    organize_files_by_type,
    find_duplicate_files,
    remove_duplicate_files,
    create_backup_archive,
    smart_file_search,
    batch_rename_files,
    analyze_directory_structure,
    sync_directories
)

# Import web scraping functions
from modules.web_scraping import (
    get_weather_info,
    get_weather_forecast,
    get_latest_news,
    search_web,
    get_stock_price,
    get_crypto_price,
    scrape_website_content,
    get_trending_topics,
    monitor_rss_feeds,
    get_product_price
)

from datetime import datetime
import time

# Import taskbar detection functions
from modules.taskbar_detection import (
    TaskbarDetector
)

# Import document OCR functions
from modules.document_ocr import (
    check_ocr_dependencies,
    extract_text_from_image,
    extract_text_from_pdf,
    analyze_document_structure,
    preprocess_image_for_ocr,
    extract_key_information,
    batch_ocr_directory,
    summarize_document_content
)

# Import taskbar detection functions
from modules.taskbar_detection import (
    detect_taskbar_apps,
    can_see_taskbar
)

# Import multi-modal AI functions
from modules.multimodal import (
    MultiModalAI,
    analyze_current_screen,
    answer_visual_question_quick,
    extract_screen_text,
    describe_current_screen
)

# Import advanced conversational AI functions
from modules.conversational_ai import (
    AdvancedConversationalAI,
    ConversationState,
    MoodType,
    create_conversation_context,
    switch_conversation_context,
    add_conversation_message,
    get_conversation_suggestions,
    detect_user_mood
)

# Import smart automation and workflow functions
from modules.smart_automation import (
    SmartAutomationEngine,
    WorkflowDefinition,
    WorkflowStatus,
    create_simple_workflow,
    execute_workflow_by_name,
    suggest_automation_from_pattern,
    get_workflow_status_simple
)

# ===============================================
# TASKBAR DETECTION AND ANALYSIS FUNCTIONS
# ===============================================

def detect_taskbar_apps():
    """Detect applications currently visible on the taskbar"""
    try:
        detector = TaskbarDetector()
        result = detector.get_running_applications()
        
        # Extract taskbar applications
        taskbar_apps = []
        if "visible_windows" in result:
            for app in result["visible_windows"]:
                taskbar_apps.append({
                    "title": app.get("name", "Unknown"),
                    "process": app.get("process_name", "Unknown"),
                    "pid": app.get("pid", 0),
                    "memory_mb": app.get("memory_mb", 0)
                })
        
        return {
            "taskbar_apps": taskbar_apps,
            "total_apps": len(taskbar_apps),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": f"Could not detect taskbar apps: {str(e)}"}

def can_see_taskbar():
    """Check if the assistant can see the taskbar and return capabilities"""
    try:
        import psutil
        capabilities = []
        limitations = []
        
        # Test process detection
        try:
            list(psutil.process_iter())
            capabilities.append("✅ Process Detection - Can see all running processes")
        except:
            limitations.append("❌ Process Detection - Limited access")
        
        # Test Windows API
        try:
            import win32gui
            capabilities.append("✅ Window Detection - Can see window titles and application states")
        except:
            limitations.append("❌ Windows API - Cannot access detailed window information")
        
        # Test taskbar detection module
        try:
            detector = TaskbarDetector()
            capabilities.append("✅ Taskbar Analysis - Can analyze taskbar applications and system state")
        except:
            limitations.append("❌ Taskbar Detection - Module not available")
        
        return {
            "can_see_taskbar": len(capabilities) >= 2,
            "capabilities": capabilities,
            "limitations": limitations,
            "detection_score": f"{len(capabilities)}/{len(capabilities) + len(limitations)}",
            "summary": "Yes, I can see your taskbar and running applications!" if len(capabilities) >= 2 
                      else "Limited taskbar visibility - some features may not work."
        }
    except Exception as e:
        return {
            "can_see_taskbar": False,
            "error": f"Could not assess taskbar capabilities: {str(e)}"
        }

# Import enhanced learning and memory functions (conditional)
try:
    from modules.enhanced_learning import (
        EnhancedLearningSystem,
        BehavioralLearner,
        SkillAcquisitionManager,
        PredictiveActionEngine,
    )
    ENHANCED_LEARNING_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Enhanced learning features not available: {str(e)}")
    print("Install scientific computing packages: pip install scikit-learn numpy scipy")
    ENHANCED_LEARNING_AVAILABLE = False
    # Create dummy classes
    class EnhancedLearningSystem:
        def __init__(self): pass
    class BehavioralLearner:
        def __init__(self): pass
    class SkillAcquisitionManager:
        def __init__(self): pass
    class PredictiveActionEngine:
        def __init__(self): pass

# Import advanced system integration functions
from modules.advanced_integration import (
    AdvancedIntegrationManager,
    SystemHookManager,
    HardwareMonitor,
    PlatformAdapter
)

# Import modern interface options functions
from modules.modern_interfaces import (
    ModernInterfaceManager,
    WebInterface,
    VoiceOnlyInterface,
    MobileAppBackend,
    InterfaceType,
    VoiceMode
)

# Import performance optimization functions
from modules.performance_optimization import (
    PerformanceOptimizer,
    ResourceMonitor,
    SmartCache,
    MemoryManager,
    DatabaseOptimizer,
    AsyncTaskManager,
    OptimizationSettings,
    PerformanceLevel
)

# Re-export all functions for backward compatibility
__all__ = [
    # Core functions
    'write_a_note', 'open_application', 'open_settings_page',
    'search_google', 'search_youtube', 'close_application',
    'speak', 'set_system_volume', 'extract_number',
    'scan_and_save_apps', 'get_app_path_from_name', 'write_to_file',
    
    # Memory functions
    'setup_memory', 'save_to_memory', 'get_memory',
    'search_memory', 'get_conversation_summary',
    'save_knowledge', 'get_knowledge',
    
    # System functions
    'get_system_status', 'get_running_processes', 'cleanup_temp_files',
    'get_network_info', 'monitor_system_alerts', 'get_system_info',
    'get_battery_status',
    
    # Calendar functions
    'setup_calendar_auth', 'get_upcoming_events', 'create_calendar_event',
    'get_todays_schedule', 'search_calendar_events', 'delete_calendar_event',
    
    # Email functions
    'setup_email_auth', 'get_inbox_summary', 'send_email',
    'search_emails', 'read_email_content', 'get_unread_count',
    'mark_email_read', 'delete_email', 'compose_quick_reply',
    
    # Music functions
    'get_spotify_status', 'spotify_play_pause', 'spotify_next_track',
    'spotify_previous_track', 'search_and_play_spotify', 'get_media_players',
    'control_media_player', 'get_system_volume', 'set_system_volume',
    'create_spotify_playlist', 'get_music_recommendations',
    
    # File Operations functions
    'organize_files_by_type', 'find_duplicate_files', 'remove_duplicate_files',
    'create_backup_archive', 'smart_file_search', 'batch_rename_files',
    'analyze_directory_structure', 'sync_directories',
    
    # Web Scraping functions
    'get_weather_info', 'get_weather_forecast', 'get_latest_news', 'search_web',
    'get_stock_price', 'get_crypto_price', 'scrape_website_content',
    'get_trending_topics', 'monitor_rss_feeds', 'get_product_price',
    
    # Document OCR functions
    'check_ocr_dependencies', 'extract_text_from_image', 'extract_text_from_pdf',
    'analyze_document_structure', 'preprocess_image_for_ocr', 'extract_key_information',
    'batch_ocr_directory', 'summarize_document_content',
    
    # Taskbar Detection functions
    'detect_taskbar_apps', 'can_see_taskbar',
    
    # Enhanced Learning functions
    'EnhancedLearningSystem', 'BehavioralLearner', 'SkillAcquisitionManager',
    'PredictiveActionEngine', 'PersonalKnowledgeGraph',
    
    # Advanced System Integration functions
    'AdvancedIntegrationManager', 'SystemHookManager', 'HardwareMonitor',
    'PlatformAdapter',
    
    # Modern Interface Options functions
    'ModernInterfaceManager', 'WebInterface', 'VoiceOnlyInterface',
    'MobileAppBackend', 'InterfaceType', 'VoiceMode',
    
    # Performance Optimization functions
    'PerformanceOptimizer', 'ResourceMonitor', 'SmartCache', 'MemoryManager',
    'DatabaseOptimizer', 'AsyncTaskManager', 'OptimizationSettings', 'PerformanceLevel'
]

# Module version and information
__version__ = "4.2.0"
__author__ = "YourDaddy AI Assistant"

print("✅ YourDaddy Automation Tools v4.2.0 - Performance Optimization Loaded")
print("📁 Modules: Core, Memory, System, Calendar, Email, Music, FileOps, WebScraping, DocumentOCR, MultiModal, ConversationalAI, SmartAutomation, EnhancedLearning, AdvancedIntegration, ModernInterfaces, PerformanceOptimization")
print(f"🔧 Available Functions: {len(__all__)}")