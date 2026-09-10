# Setup centralized logging
from ai_assistant.utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Database Configuration Module

Centralized database path management for Pulsar AI Assistant.
All database files are stored in the data/ directory.
"""

import os
import sys
from pathlib import Path

# Smart Data Root Detection
def get_data_root() -> Path:
    if getattr(sys, 'frozen', False):
        # PyInstaller/packaged app -> user's AppData
        # Fallback to local APPDATA if not on Windows, though this is a Windows app
        appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~/.pulsar_ai'))
        data_root = Path(appdata) / 'PulsarAI' / 'data'
    else:
        # Development -> project folder (4 levels up from this file)
        # __file__ is core_ai/src/ai_assistant/core/database_config.py
        data_root = Path(__file__).resolve().parents[4] / "data"
    
    return data_root

DATA_DIR = get_data_root()
PROJECT_ROOT = DATA_DIR.parent

# Ensure essential data subdirectories exist
(DATA_DIR / "core").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "analytics").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "automation").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "caches").mkdir(parents=True, exist_ok=True)

# Database file paths
DATABASES = {
    'app_usage': DATA_DIR / 'analytics' / 'app_usage.db',
    'chat_history': DATA_DIR / 'core' / 'chat_history.db',
    'conversation_ai': DATA_DIR / 'core' / 'conversation_ai.db',
    'enhanced_learning': DATA_DIR / 'analytics' / 'enhanced_learning.db',
    'language_data': DATA_DIR / 'core' / 'language_data.db',
    'memory': DATA_DIR / 'core' / 'memory.db',
    'personal_knowledge': DATA_DIR / 'core' / 'personal_knowledge.db',
    'commitments': DATA_DIR / 'automation' / 'commitments.db',
    'historical_rag': DATA_DIR / 'core' / 'historical_rag.db',
    'intent_classifier': DATA_DIR / 'core' / 'intent_classifier.db',
    'advanced_integration': DATA_DIR / 'automation' / 'advanced_integration.db',
    'active_learning': DATA_DIR / 'analytics' / 'active_learning.db',
    'adaptive_voice': DATA_DIR / 'core' / 'adaptive_voice.db',
    'behavior_clustering': DATA_DIR / 'analytics' / 'behavior_clustering.db',
    'conversation_clustering': DATA_DIR / 'analytics' / 'conversation_clustering.db',
    'feedback_learning': DATA_DIR / 'analytics' / 'feedback_learning.db',
    'anomaly_detection': DATA_DIR / 'analytics' / 'anomaly_detection.db',
    'automation_engine': DATA_DIR / 'automation' / 'automation_engine.db',
    'command_sequences': DATA_DIR / 'automation' / 'command_sequences.db',
    'command_success': DATA_DIR / 'automation' / 'command_success.db',
    'smart_commands': DATA_DIR / 'automation' / 'smart_commands.db',
    'task_scheduler': DATA_DIR / 'automation' / 'task_scheduler.db',
    'query_cache': DATA_DIR / 'caches' / 'query_cache.db',
    'causal_inference': DATA_DIR / 'analytics' / 'causal_inference.db',
    'context_aware_responses': DATA_DIR / 'context' / 'context_aware_responses.db',
    'contrastive_learning': DATA_DIR / 'models' / 'contrastive_learning.db',
    'domain_embeddings': DATA_DIR / 'models' / 'domain_embeddings.db',
    'explainability': DATA_DIR / 'analytics' / 'explainability.db',
    'federated_learning': DATA_DIR / 'models' / 'federated_learning.db',
    'gnn': DATA_DIR / 'models' / 'gnn.db',
    'knowledge_graph': DATA_DIR / 'core' / 'knowledge_graph.db',
    'llm_bandit': DATA_DIR / 'models' / 'llm_bandit.db',
    'meta_learning': DATA_DIR / 'models' / 'meta_learning.db',
    'model_compression': DATA_DIR / 'models' / 'model_compression.db',
    'multimodal_learning': DATA_DIR / 'models' / 'multimodal_learning.db',
    'ner': DATA_DIR / 'models' / 'ner.db',
    'prompt_optimizer': DATA_DIR / 'models' / 'prompt_optimizer.db',
    'rl_ppo': DATA_DIR / 'models' / 'rl_ppo.db',
    'self_supervised': DATA_DIR / 'models' / 'self_supervised.db',
    'workflow_recommender': DATA_DIR / 'automation' / 'workflow_recommender.db',
    'workflow_scheduler': DATA_DIR / 'automation' / 'workflow_scheduler.db',
    'semantic_history': DATA_DIR / 'core' / 'semantic_history.db',
    'system_hooks': DATA_DIR / 'automation' / 'system_hooks.db',
    'test_encrypted': DATA_DIR / 'caches' / 'test_encrypted.db',
    'automation_analytics': DATA_DIR / 'user_data' / 'automation_analytics.db',
    'automation_rules': DATA_DIR / 'user_data' / 'automation_rules.db',
    'automation_security': DATA_DIR / 'user_data' / 'automation_security.db',
    'context_automation': DATA_DIR / 'user_data' / 'context_automation.db',
    'security_audit': DATA_DIR / 'user_data' / 'security_audit.db'
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
