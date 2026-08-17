"""
Progress Tracker with Persistence
Tracks execution progress of action chains and persists to SQLite database.
Allows resuming tracking after server restart and provides history.
"""

import logging
import sqlite3
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from ai_assistant.core.action_chain_models import ProgressReport, ChainStatus

logger = logging.getLogger(__name__)

DB_PATH = "user_data/chain_history.db"

class PersistentProgressTracker:
    """
    Persistent progress tracker using SQLite.
    Stores chain execution history and real-time status.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        """Initialize tracker with database path"""
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Initialize database schema"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Chains table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS chains (
                    id TEXT PRIMARY KEY,
                    command TEXT,
                    status TEXT,
                    progress REAL,
                    total_actions INTEGER,
                    completed_actions INTEGER,
                    created_at TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    duration REAL,
                    results_json TEXT,
                    error TEXT
                )
                """)
                
                # Actions table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id TEXT PRIMARY KEY,
                    chain_id TEXT,
                    description TEXT,
                    type TEXT,
                    status TEXT,
                    progress REAL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    result_json TEXT,
                    error TEXT,
                    FOREIGN KEY (chain_id) REFERENCES chains (id)
                )
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize progress DB: {e}")

    def start_chain(self, chain_id: str, command: str, total_actions: int):
        """Record start of a new chain"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT OR REPLACE INTO chains 
                (id, command, status, progress, total_actions, completed_actions, created_at, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chain_id, command, ChainStatus.PENDING.value, 0.0, 
                    total_actions, 0, datetime.now(), datetime.now()
                ))
        except Exception as e:
            logger.error(f"DB Error start_chain: {e}")

    def update_chain_status(self, chain_id: str, status: str, progress: float, 
                           completed_actions: int = None):
        """Update chain status and progress"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                update_fields = ["status = ?", "progress = ?"]
                params = [status, progress]
                
                if completed_actions is not None:
                    update_fields.append("completed_actions = ?")
                    params.append(completed_actions)
                
                if status in [ChainStatus.COMPLETED.value, ChainStatus.FAILED.value]:
                    update_fields.append("completed_at = ?")
                    params.append(datetime.now())
                
                params.append(chain_id)
                
                query = f"UPDATE chains SET {', '.join(update_fields)} WHERE id = ?"
                cursor.execute(query, params)
        except Exception as e:
            logger.error(f"DB Error update_chain_status: {e}")

    def record_action_start(self, action_id: str, chain_id: str, description: str, type: str):
        """Record start of an action"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT OR REPLACE INTO actions 
                (id, chain_id, description, type, status, progress, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    action_id, chain_id, description, type, 
                    "running", 0.0, datetime.now()
                ))
        except Exception as e:
            logger.error(f"DB Error record_action_start: {e}")

    def update_action_status(self, action_id: str, status: str, progress: float = None, 
                            result: Any = None, error: str = None):
        """Update action status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                update_fields = ["status = ?"]
                params = [status]
                
                if progress is not None:
                    update_fields.append("progress = ?")
                    params.append(progress)
                
                if result is not None:
                    update_fields.append("result_json = ?")
                    params.append(json.dumps(result, default=str))
                
                if error is not None:
                    update_fields.append("error = ?")
                    params.append(str(error))
                
                if status in ["completed", "failed"]:
                    update_fields.append("completed_at = ?")
                    params.append(datetime.now())
                
                params.append(action_id)
                
                query = f"UPDATE actions SET {', '.join(update_fields)} WHERE id = ?"
                cursor.execute(query, params)
        except Exception as e:
            logger.error(f"DB Error update_action_status: {e}")

    def save_chain_result(self, chain_id: str, status: str, results: Dict[str, Any], 
                         error: Optional[str] = None):
        """Save final chain results"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                UPDATE chains 
                SET status = ?, completed_at = ?, results_json = ?, error = ?, duration = ?
                WHERE id = ?
                """, (
                    status, datetime.now(), json.dumps(results, default=str), 
                    error, self._calculate_duration(chain_id), chain_id
                ))
        except Exception as e:
            logger.error(f"DB Error save_chain_result: {e}")

    def _calculate_duration(self, chain_id: str) -> float:
        """Calculate duration for a chain"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT started_at FROM chains WHERE id = ?", (chain_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    start = datetime.fromisoformat(row[0])
                    return (datetime.now() - start).total_seconds()
        except:
            pass
        return 0.0

    def get_recent_chains(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of recent execution chains"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                SELECT * FROM chains 
                ORDER BY created_at DESC LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"DB Error get_recent_chains: {e}")
            return []

    def get_chain_details(self, chain_id: str) -> Optional[Dict[str, Any]]:
        """Get full details for a chain including actions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get chain info
                cursor.execute("SELECT * FROM chains WHERE id = ?", (chain_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                
                chain_data = dict(row)
                
                # Get actions
                cursor.execute("SELECT * FROM actions WHERE chain_id = ? ORDER BY started_at", (chain_id,))
                chain_data["actions"] = [dict(r) for r in cursor.fetchall()]
                
                return chain_data
        except Exception as e:
            logger.error(f"DB Error get_chain_details: {e}")
            return None

# Singleton instance
_tracker = None

def get_progress_tracker() -> PersistentProgressTracker:
    """Get singleton progress tracker"""
    global _tracker
    if _tracker is None:
        _tracker = PersistentProgressTracker()
    return _tracker
