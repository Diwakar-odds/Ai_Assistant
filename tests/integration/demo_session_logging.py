"""
Session-Based Logging Demonstration
==================================

This script demonstrates the new session-based logging system.
Run this to see how logs are organized by session with timestamps.
"""

# Initialize new session (this creates timestamped log files)
import utils.session_init

from utils.logging_config import get_logger
from utils.session_activity_logger import *
import time
from datetime import datetime

def demonstrate_session_logging():
    """Demonstrate the session-based logging system"""
    
    print("🎯 Demonstrating Session-Based Logging System")
    print("=" * 60)
    
    # Get session info
    session_info = utils.session_init.get_session_info()
    print(f"Session ID: {session_info['session_id']}")
    print(f"Start Time: {session_info['start_time']}")
    
    # Create different types of loggers
    app_logger = get_logger('demo_app', log_category='app')
    module_logger = get_logger('demo_module', log_category='modules')
    api_logger = get_logger('demo_api', log_category='api')
    
    print(f"\\n📝 Logging various activities...")
    
    # Demonstrate different log levels
    app_logger.info("🚀 Application demo started")
    app_logger.warning("⚠️ This is a warning message")
    app_logger.error("❌ This is an error message (for demo)")
    
    # Demonstrate module logging
    module_logger.info("📦 Module operation completed")
    module_logger.debug("🔍 Debug information logged")
    
    # Demonstrate API logging
    api_logger.info("🌐 API request processed")
    
    # Demonstrate activity logging
    print(f"\\n📊 Logging user activities...")
    
    # Voice command
    log_voice_command(
        "play some music",
        language="en",
        confidence=0.95,
        response="Playing music from Spotify",
        execution_time_ms=1250
    )
    
    # File operation
    log_file_operation(
        "create_document",
        file_path="demo_document.txt",
        success=True,
        details={"size_bytes": 2048, "format": "txt"}
    )
    
    # System command
    log_system_command(
        "volume_up",
        command_type="audio_control",
        success=True,
        output="Volume increased to 75%"
    )
    
    # API request
    log_api_request(
        "/api/chat",
        method="POST",
        status_code=200,
        response_time_ms=234.5
    )
    
    # User interaction
    log_user_interaction(
        "button_click",
        details={"button_name": "send_message", "page": "chat"},
        duration_ms=150
    )
    
    # Music control
    log_music_control(
        "play",
        track_info={"title": "Bohemian Rhapsody", "artist": "Queen"},
        platform="spotify",
        success=True
    )
    
    # Email operation
    log_email_operation(
        "check_inbox",
        email_count=5,
        success=True
    )
    
    # Calendar operation
    log_calendar_operation(
        "add_event",
        event_details={"title": "Meeting", "duration": "1h"},
        success=True
    )
    
    # Web scraping
    log_web_scraping(
        "https://example.com",
        scraping_type="news",
        data_extracted=True
    )
    
    # Multimodal AI
    log_multimodal_ai(
        "image_analysis",
        input_type="screenshot",
        processing_time_ms=2100,
        confidence=0.89
    )
    
    # Automation
    log_automation(
        "morning_routine",
        steps_count=5,
        execution_time_ms=3400,
        success=True
    )
    
    print(f"\\n✅ Demo completed! Check the following locations for logs:")
    print(f"")
    
    # Show log file locations
    session_id = session_info['session_id']
    log_locations = [
        f"📁 App logs: logs/app/demo_app_{session_id}.log",
        f"📁 Module logs: logs/modules/demo_module_{session_id}.log", 
        f"📁 API logs: logs/api/demo_api_{session_id}.log",
        f"📁 Error logs: logs/errors/demo_*_errors_{session_id}.log",
        f"📊 Activity summary: logs/activities/session_summary_{session_id}.json",
        f"📋 Session info: logs/sessions/session_{session_id}.json"
    ]
    
    for location in log_locations:
        print(f"   {location}")
    
    print(f"")
    print(f"🔍 You can view logs using:")
    print(f"   python utils/log_viewer.py app")
    print(f"   python utils/log_viewer.py modules --tail")
    print(f"   python utils/log_viewer.py activities")
    
    return session_info

def show_log_structure():
    """Show the current log directory structure"""
    import os
    from pathlib import Path
    
    print(f"\\n📁 Current Log Directory Structure:")
    print(f"=" * 50)
    
    logs_dir = Path("logs")
    if logs_dir.exists():
        for root, dirs, files in os.walk(logs_dir):
            level = root.replace(str(logs_dir), '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            
            # Show recent files (limit to avoid clutter)
            sub_indent = ' ' * 2 * (level + 1)
            for file in sorted(files)[-5:]:  # Show last 5 files
                if file.endswith(('.log', '.json')):
                    print(f"{sub_indent}{file}")
            if len(files) > 5:
                print(f"{sub_indent}... and {len(files) - 5} more files")

if __name__ == "__main__":
    print("🎯 YourDaddy Assistant - Session Logging Demo")
    print("=" * 60)
    
    # Run demonstration
    session_info = demonstrate_session_logging()
    
    # Show log structure
    show_log_structure()
    
    print(f"\\n🎉 Session-based logging demonstration completed!")
    print(f"Every time you start the assistant, new timestamped log files will be created.")
    print(f"This allows you to track each session separately and review specific activities.")