"""
Database Migrations Engine for YourDaddy AI Assistant.
Provides version-tracked, safe schema migrations for all SQLite databases.
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Callable, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class Migration:
    """Individual schema migration definition."""
    def __init__(self, version: int, name: str, up_sql: str, down_sql: Optional[str] = None):
        self.version = version
        self.name = name
        self.up_sql = up_sql
        self.down_sql = down_sql


# Registry of baseline migrations
DEFAULT_MIGRATIONS = [
    Migration(
        version=1,
        name="initial_knowledge_and_memory",
        up_sql="""
        CREATE TABLE IF NOT EXISTS knowledge_nodes (
            node_id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            node_type TEXT NOT NULL,
            metadata TEXT,
            importance_score REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS knowledge_edges (
            edge_id TEXT PRIMARY KEY,
            source_node TEXT NOT NULL,
            target_node TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            strength REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_node) REFERENCES knowledge_nodes (node_id),
            FOREIGN KEY (target_node) REFERENCES knowledge_nodes (node_id)
        );
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT,
            assistant_response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            context TEXT
        );
        """
    ),
    Migration(
        version=2,
        name="workflow_and_audit",
        up_sql="""
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            definition TEXT NOT NULL,
            status TEXT DEFAULT 'idle',
            enabled INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS workflow_executions (
            execution_id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            status TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            duration_seconds REAL DEFAULT 0.0,
            task_results TEXT,
            error_message TEXT,
            output_data TEXT,
            FOREIGN KEY (workflow_id) REFERENCES workflows(id)
        );
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            user_id TEXT,
            details TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    ),
    Migration(
        version=3,
        name="user_preferences_and_patterns",
        up_sql="""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            preferences_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS automation_patterns (
            pattern_id TEXT PRIMARY KEY,
            pattern_type TEXT NOT NULL,
            pattern_data TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            frequency INTEGER DEFAULT 1,
            last_seen TEXT NOT NULL
        );
        """
    )
]


class MigrationManager:
    """Manages applying and rolling back migrations on a database."""

    def __init__(self, db_path: str, migrations: Optional[List[Migration]] = None):
        self.db_path = str(db_path)
        self.migrations = migrations or DEFAULT_MIGRATIONS
        self._ensure_migrations_table()

    def _ensure_migrations_table(self):
        """Ensure schema_migrations tracking table exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def get_applied_versions(self) -> List[int]:
        """Fetch list of already applied migration version numbers."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_migrations ORDER BY version ASC")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def run_migrations(self) -> int:
        """Apply all pending migrations in version order."""
        applied = set(self.get_applied_versions())
        count = 0
        
        for mig in sorted(self.migrations, key=lambda m: m.version):
            if mig.version not in applied:
                logger.info(f"Applying migration v{mig.version}: {mig.name}")
                conn = sqlite3.connect(self.db_path)
                try:
                    cursor = conn.cursor()
                    cursor.executescript(mig.up_sql)
                    cursor.execute(
                        "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                        (mig.version, mig.name, datetime.now().isoformat())
                    )
                    conn.commit()
                finally:
                    conn.close()
                count += 1
                
        if count > 0:
            logger.info(f"Applied {count} database migrations to {self.db_path}")
        return count


def auto_migrate_all():
    """Helper to auto-migrate the primary application databases."""
    try:
        from ai_assistant.core.database_config import get_db_path
        db_names = ['personal_knowledge', 'workflows', 'audit', 'learning_system']
        for name in db_names:
            try:
                p = get_db_path(name)
                mgr = MigrationManager(str(p))
                mgr.run_migrations()
            except Exception as e:
                logger.debug(f"Auto-migration note for {name}: {e}")
    except Exception as e:
        logger.debug(f"Auto-migrate runner note: {e}")
