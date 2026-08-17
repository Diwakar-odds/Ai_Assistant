"""
Test Date-Based Logging System

This script tests the new date-based logging organization.
"""

from utils.logging_config import get_logger, SessionManager, LoggingConfig
from pathlib import Path
import os

def test_date_based_logging():
    """Test that logs are organized by date"""
    
    print("=" * 70)
    print("🧪 Testing Date-Based Logging System")
    print("=" * 70)
    
    # Start a new session
    session_id = SessionManager.start_new_session()
    current_date = SessionManager.get_current_date()
    
    print(f"\n✅ Session started: {session_id}")
    print(f"✅ Current date: {current_date}")
    
    # Get dated log directories
    log_dirs = LoggingConfig.get_dated_log_dirs()
    
    print(f"\n📁 Date-based log directory structure:")
    print(f"   Base: logs/{current_date}/")
    
    # Test creating loggers for different categories
    categories = ['app', 'backend', 'modules', 'api', 'voice', 'security']
    
    print(f"\n🔍 Testing log creation in each category:")
    
    for category in categories:
        logger = get_logger(f'test_{category}', log_category=category)
        logger.info(f"Test log message for {category}")
        
        # Check if log file was created
        log_dir = log_dirs[category]
        expected_file = log_dir / f"test_{category}_{session_id}.log"
        
        if expected_file.exists():
            print(f"   ✅ {category:12} -> {expected_file}")
        else:
            print(f"   ❌ {category:12} -> NOT CREATED")
    
    # Check session file
    session_file = Path('logs') / current_date / 'sessions' / f'session_{session_id}.json'
    if session_file.exists():
        print(f"   ✅ {'sessions':12} -> {session_file}")
    else:
        print(f"   ❌ {'sessions':12} -> NOT CREATED")
    
    # Show directory structure
    print(f"\n📂 Created directory structure:")
    date_folder = Path('logs') / current_date
    if date_folder.exists():
        for item in sorted(date_folder.iterdir()):
            if item.is_dir():
                file_count = len(list(item.glob('*')))
                print(f"   📁 {item.name:15} ({file_count} files)")
    
    print(f"\n{'=' * 70}")
    print("✅ Date-based logging test complete!")
    print("=" * 70)
    
    # Show example paths
    print(f"\n💡 Example log paths:")
    print(f"   logs/{current_date}/app/test_app_{session_id}.log")
    print(f"   logs/{current_date}/backend/test_backend_{session_id}.log")
    print(f"   logs/{current_date}/voice/test_voice_{session_id}.log")
    print(f"   logs/{current_date}/sessions/session_{session_id}.json")

if __name__ == "__main__":
    test_date_based_logging()
