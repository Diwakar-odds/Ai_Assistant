# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Database Configuration Module

Centralized database path management for Pulsar AI Assistant.
All database files are stored in the data/ directory.
"""

import os
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Database file paths
DATABASES = {
    'app_usage': DATA_DIR / 'app_usage.db',
    'chat_history': DATA_DIR / 'chat_history.db',
    'conversation_ai': DATA_DIR / 'data/core/conversation_ai.db',
    'enhanced_learning': DATA_DIR / 'enhanced_learning.db',
    'language_data': DATA_DIR / 'data/core/language_data.db',
    'memory': DATA_DIR / 'memory.db',
    'personal_knowledge': DATA_DIR / 'personal_knowledge.db',
}

def get_db_path(db_name: str) -> Path:
    """
    Get the path to a database file.
    
    Args:
        db_name: Name of the database (e.g., 'memory', 'chat_history')
        
    Returns:
        Path object pointing to the database file
        
    Raises:
        KeyError: If database name is not recognized
    """
    if db_name not in DATABASES:
        raise KeyError(f"Unknown database: {db_name}. Available: {list(DATABASES.keys())}")
    return DATABASES[db_name]

def get_db_path_str(db_name: str) -> str:
    """
    Get the path to a database file as a string.
    
    Args:
        db_name: Name of the database (e.g., 'memory', 'chat_history')
        
    Returns:
        String path to the database file
    """
    return str(get_db_path(db_name))

def list_databases() -> dict:
    """
    List all configured databases and their paths.
    
    Returns:
        Dictionary mapping database names to their paths
    """
    return {name: str(path) for name, path in DATABASES.items()}

def database_exists(db_name: str) -> bool:
    """
    Check if a database file exists.
    
    Args:
        db_name: Name of the database
        
    Returns:
        True if the database file exists, False otherwise
    """
    try:
        return get_db_path(db_name).exists()
    except KeyError:
        return False

def get_database_size(db_name: str) -> int:
    """
    Get the size of a database file in bytes.
    
    Args:
        db_name: Name of the database
        
    Returns:
        Size in bytes, or 0 if file doesn't exist
    """
    try:
        path = get_db_path(db_name)
        return path.stat().st_size if path.exists() else 0
    except KeyError:
        return 0

# Backward compatibility - maintain old paths for migration
LEGACY_PATHS = {
    'app_usage': 'app_usage.db',
    'chat_history': 'chat_history.db',
    'conversation_ai': 'data/core/conversation_ai.db',
    'enhanced_learning': 'enhanced_learning.db',
    'language_data': 'data/core/language_data.db',
    'memory': 'memory.db',
}

def migrate_legacy_databases():
    """
    Migrate databases from root directory to data/ directory.
    This should be called once during application startup.
    """
    import shutil
    
    migrated = []
    for db_name, legacy_path in LEGACY_PATHS.items():
        legacy_file = PROJECT_ROOT / legacy_path
        new_path = DATABASES[db_name]
        
        # If legacy file exists and new file doesn't, migrate it
        if legacy_file.exists() and not new_path.exists():
            try:
                shutil.move(str(legacy_file), str(new_path))
                migrated.append(db_name)
                print(f"[OK] Migrated {db_name} database to data/ directory")
            except Exception as e:
                print(f"[ERROR] Failed to migrate {db_name}: {e}")
    
    if migrated:
        print(f"\nMigrated {len(migrated)} database(s) to data/ directory")
    
    return migrated

if __name__ == "__main__":
    print("Database Configuration")
    print("=" * 60)
    print(f"Data Directory: {DATA_DIR}")
    print(f"\nConfigured Databases:")
    for name, path in list_databases().items():
        exists = "[OK]" if database_exists(name) else "[  ]"
        size = get_database_size(name)
        size_str = f"{size:,} bytes" if size > 0 else "N/A"
        print(f"  {exists} {name:20} {path} ({size_str})")
    
    print(f"\nChecking for legacy databases to migrate...")
    migrated = migrate_legacy_databases()
    if not migrated:
        print("[OK] No legacy databases found. All databases are in the correct location.")
