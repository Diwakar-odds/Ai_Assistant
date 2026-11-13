"""
Progress Tracker with Persistence
Tracks execution progress of action chains and persists to SQLite database.
Allows resuming tracking after server restart and provides history.
"""

import logging
import sqlite3
import json
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from ai_assistant.core.action_chain_models import ProgressReport, ChainStatus

logger = logging.getLogger(__name__)


def _resolve_default_db_path() -> str:
    """Resolve persistent DB path inside project data/core directory regardless of CWD."""
    try:
        from ai_assistant.core.database_config import PROJECT_ROOT
        return str((PROJECT_ROOT / "data" / "core" / "chain_history.db").resolve())
    except Exception:
        return str((Path(__file__).resolve().parents[4] / "data" / "core" / "chain_history.db").resolve())


DB_PATH = _resolve_default_db_path()


class PersistentProgressTracker:
    """
    Persistent progress tracker using SQLite (thread-safe, WAL mode).
    Stores chain execution history and real-time status.
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize tracker with database path"""
        self.db_path = str(db_path or DB_PATH)
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Open a thread-safe SQLite connection with WAL mode and busy timeout."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _ensure_column(self, cursor: sqlite3.Cursor, table: str, column: str, col_def: str):
        cursor.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in cursor.fetchall()}
        if column not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")

    def _init_db(self):
        """Initialize database schema and migrate legacy columns idempotently."""
        try:
            with self._lock:
                with self._connect() as conn:
                    cursor = conn.cursor()

                    # Chains table
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chains (
                        id TEXT PRIMARY KEY,
                        command TEXT,
                        source TEXT DEFAULT 'chat',
                        status TEXT,
                        progress REAL DEFAULT 0.0,
                        total_actions INTEGER DEFAULT 0,
                        completed_actions INTEGER DEFAULT 0,
                        failed_actions INTEGER DEFAULT 0,
                        app_context TEXT,
                        created_at TIMESTAMP,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        duration REAL DEFAULT 0.0,
                        final_output TEXT,
                        results_json TEXT,
                        steps_json TEXT,
                        metadata_json TEXT,
                        error TEXT
                    )
                    """)

                    # Actions table
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS actions (
                        id TEXT PRIMARY KEY,
                        chain_id TEXT,
                        step_index INTEGER DEFAULT 0,
                        intent TEXT DEFAULT '',
                        description TEXT,
                        type TEXT,
                        agent_id TEXT,
                        dependencies_json TEXT,
                        output_key TEXT,
                        status TEXT,
                        progress REAL DEFAULT 0.0,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        duration REAL DEFAULT 0.0,
                        result_json TEXT,
                        error TEXT,
                        FOREIGN KEY (chain_id) REFERENCES chains (id) ON DELETE CASCADE
                    )
                    """)

                    # Migrate older DBs missing newer columns
                    self._ensure_column(cursor, "chains", "source", "TEXT DEFAULT 'chat'")
                    self._ensure_column(cursor, "chains", "failed_actions", "INTEGER DEFAULT 0")
                    self._ensure_column(cursor, "chains", "app_context", "TEXT")
                    self._ensure_column(cursor, "chains", "final_output", "TEXT")
                    self._ensure_column(cursor, "chains", "steps_json", "TEXT")
                    self._ensure_column(cursor, "chains", "metadata_json", "TEXT")

                    self._ensure_column(cursor, "actions", "step_index", "INTEGER DEFAULT 0")
                    self._ensure_column(cursor, "actions", "intent", "TEXT DEFAULT ''")
                    self._ensure_column(cursor, "actions", "agent_id", "TEXT")
                    self._ensure_column(cursor, "actions", "dependencies_json", "TEXT")
                    self._ensure_column(cursor, "actions", "output_key", "TEXT")
                    self._ensure_column(cursor, "actions", "duration", "REAL DEFAULT 0.0")

                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_actions_chain ON actions(chain_id, step_index)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chains_created ON chains(created_at DESC)")
                    conn.commit()
            self.mark_stale_chains_cancelled()
        except Exception as e:
            logger.error(f"Failed to initialize progress DB: {e}")

    def start_chain(
        self,
        chain_id: str,
        command: str,
        total_actions: int = 0,
        source: str = "chat",
        app_context: Optional[str] = None,
        status: Optional[str] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record creation/planning start of a chain without wiping existing fields on update."""
        try:
            now_iso = datetime.now().isoformat()
            status_val = status or ChainStatus.PENDING.value
            steps_str = json.dumps(steps, default=str) if steps is not None else None
            meta_str = json.dumps(metadata, default=str) if metadata is not None else None
            with self._lock:
                with self._connect() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, created_at FROM chains WHERE id = ?", (chain_id,))
                    existing = cursor.fetchone()
                    if existing:
                        updates = ["command = ?", "total_actions = ?"]
                        params: List[Any] = [command, total_actions]
                        if status is not None:
                            updates.append("status = ?")
                            params.append(status_val)
                        if app_context is not None:
                            updates.append("app_context = ?")
                            params.append(app_context)
                        if steps_str is not None:
                            updates.append("steps_json = ?")
                            params.append(steps_str)
                        if meta_str is not None:
                            updates.append("metadata_json = ?")
                            params.append(meta_str)
                        params.append(chain_id)
                        cursor.execute(f"UPDATE chains SET {', '.join(updates)} WHERE id = ?", params)
                    else:
                        cursor.execute("""
                        INSERT INTO chains
                        (id, command, source, status, progress, total_actions, completed_actions,
                         failed_actions, app_context, created_at, started_at, steps_json, metadata_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            chain_id, command, source, status_val, 0.0,
                            total_actions, 0, 0, app_context, now_iso, now_iso,
                            steps_str, meta_str
                        ))
                    conn.commit()
        except Exception as e:
            logger.error(f"DB Error start_chain: {e}")

    def update_chain_status(
        self,
        chain_id: str,
        status: str,
        progress: float,
        completed_actions: Optional[int] = None,
        failed_actions: Optional[int] = None,
        total_actions: Optional[int] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        final_output: Any = None,
    ):
        """Update chain status and progress"""
        try:
            status_str = status.value if hasattr(status, "value") else str(status).lower()
            with self._lock:
                with self._connect() as conn:
                    cursor = conn.cursor()

                    update_fields = ["status = ?", "progress = ?"]
                    params: List[Any] = [status_str, float(progress)]

                    if completed_actions is not None:
                        update_fields.append("completed_actions = ?")
                        params.append(int(completed_actions))

                    if failed_actions is not None:
                        update_fields.append("failed_actions = ?")
                        params.append(int(failed_actions))

                    if total_actions is not None:
                        update_fields.append("total_actions = ?")
                        params.append(int(total_actions))

                    if steps is not None:
                        update_fields.append("steps_json = ?")
                        params.append(json.dumps(steps, default=str))

                    if final_output is not None:
                        update_fields.append("final_output = ?")
                        params.append(json.dumps(final_output, default=str) if isinstance(final_output, (dict, list)) else str(final_output))

                    if status_str in (
                        ChainStatus.COMPLETED.value,
                        ChainStatus.FAILED.value,
                        ChainStatus.CANCELLED.value,
                    ):
                        update_fields.append("completed_at = ?")
                        params.append(datetime.now().isoformat())
                        update_fields.append("duration = ?")
                        params.append(self._calculate_duration_with_cursor(cursor, chain_id))

                    params.append(chain_id)
                    cursor.execute(f"UPDATE chains SET {', '.join(update_fields)} WHERE id = ?", params)
                    conn.commit()
        except Exception as e:
            logger.error(f"DB Error update_chain_status: {e}")

    def record_action_planned(
        self,
        action_id: str,
        chain_id: str,
        description: str,
        type: str,
        step_index: int = 0,
        intent: str = "",
        agent_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        output_key: Optional[str] = None,
    ):
        """Record a planned action in 'pending' state before execution begins."""
        try:
            deps_str = json.dumps(list(dependencies or []), default=str)
            with self._lock:
                with self._connect() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                    INSERT OR REPLACE INTO actions
                    (id, chain_id, step_index, intent, description, type, agent_id,
                     dependencies_json, output_key, status, progress)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        action_id, chain_id, int(step_index), intent or "",
                        description, type, agent_id, deps_str, output_key,
                        "pending", 0.0
                    ))
                    conn.commit()
        except Exception as e:
            logger.error(f"DB Error record_action_planned: {e}")

    def record_action_start(
        self,
        action_id: str,
        chain_id: str,
        description: str,
        type: str,
        step_index: int = 0,
        intent: str = "",
        agent_id: Optional[str] = None,
        status: str = "running",
    ):
        """Record start of an action"""
        try:
            now_iso = datetime.now().isoformat()
            with self._lock:
                with self._connect() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, step_index, dependencies_json, output_key, intent FROM actions WHERE id = ?", (action_id,))
                    existing = cursor.fetchone()
                    if existing:
                        cursor.execute("""
                        UPDATE actions
                        SET status = ?, progress = ?, started_at = ?, agent_id = COALESCE(?, agent_id)
                        WHERE id = ?
                        """, (status, 0.0, now_iso, agent_id, action_id))
                    else:
                        cursor.execute("""
                        INSERT INTO actions
                        (id, chain_id, step_index, intent, description, type, agent_id, status, progress, started_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            action_id, chain_id, int(step_index), intent or "",
                            description, type, agent_id, status, 0.0, now_iso
                        ))
                    conn.commit()
        except Exception as e:
            logger.error(f"DB Error record_action_start: {e}")

    def update_action_status(
        self,
        action_id: str,
        status: str,
        progress: Optional[float] = None,
        result: Any = None,
        error: Optional[str] = None,
        agent_id: Optional[str] = None,
        duration_seconds: Optional[float] = None,
    ):
        """Update action status"""
        try:
            with self._lock:
                with self._connect() as conn:
                    cursor = conn.cursor()

                    update_fields = ["status = ?"]
                    params: List[Any] = [status]

                    if progress is not None:
                        update_fields.append("progress = ?")
                        params.append(float(progress))

                    if result is not None:
                        update_fields.append("result_json = ?")
                        params.append(json.dumps(result, default=str))

                    if error is not None:
                        update_fields.append("error = ?")
                        params.append(str(error))

                    if agent_id is not None:
                        update_fields.append("agent_id = ?")
                        params.append(agent_id)

                    if duration_seconds is not None:
                        update_fields.append("duration = ?")
                        params.append(float(duration_seconds))

                    if status == "running":
                        update_fields.append("started_at = COALESCE(started_at, ?)")
                        params.append(datetime.now().isoformat())
                    elif status in ("completed", "completed_with_warning", "failed", "skipped", "cancelled"):
                        update_fields.append("completed_at = ?")
                        params.append(datetime.now().isoformat())

                    params.append(action_id)
                    cursor.execute(f"UPDATE actions SET {', '.join(update_fields)} WHERE id = ?", params)
                    conn.commit()
        except Exception as e:
            logger.error(f"DB Error update_action_status: {e}")

    def save_chain_result(
        self,
        chain_id: str,
        status: str,
        results: Dict[str, Any],
        error: Optional[str] = None,
        final_output: Any = None,
        completed_actions: Optional[int] = None,
        failed_actions: Optional[int] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
    ):
        """Save final chain results"""
        try:
            status_str = status.value if hasattr(status, "value") else str(status).lower()
            now_iso = datetime.now().isoformat()
            final_str = (
                json.dumps(final_output, default=str)
                if isinstance(final_output, (dict, list))
                else (str(final_output) if final_output is not None else None)
            )
            with self._lock:
                with self._connect() as conn:
                    cursor = conn.cursor()
                    dur = self._calculate_duration_with_cursor(cursor, chain_id)
                    fields = [
                        "status = ?",
                        "completed_at = ?",
                        "results_json = ?",
                        "error = ?",
                        "duration = ?",
                    ]
                    params: List[Any] = [
                        status_str, now_iso, json.dumps(results, default=str), error, dur
                    ]
                    if status_str == ChainStatus.COMPLETED.value:
                        fields.append("progress = ?")
                        params.append(100.0)
                    if final_str is not None:
                        fields.append("final_output = ?")
                        params.append(final_str)
                    if completed_actions is not None:
                        fields.append("completed_actions = ?")
                        params.append(int(completed_actions))
                    if failed_actions is not None:
                        fields.append("failed_actions = ?")
                        params.append(int(failed_actions))
                    if steps is not None:
                        fields.append("steps_json = ?")
                        params.append(json.dumps(steps, default=str))

                    params.append(chain_id)
                    cursor.execute(f"UPDATE chains SET {', '.join(fields)} WHERE id = ?", params)
                    conn.commit()
        except Exception as e:
            logger.error(f"DB Error save_chain_result: {e}")

    def delete_chain(self, chain_id: str):
        """Delete a chain and its actions (e.g. temporary decomposition cleanup)."""
        try:
            with self._lock:
                with self._connect() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM actions WHERE chain_id = ?", (chain_id,))
                    cursor.execute("DELETE FROM chains WHERE id = ?", (chain_id,))
                    conn.commit()
        except Exception as e:
            logger.error(f"DB Error delete_chain: {e}")

    def clear_all_chains(self):
        """Wipe all chain history and action records cleanly."""
        try:
            with self._lock:
                with self._connect() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM actions")
                    cursor.execute("DELETE FROM chains")
                    conn.commit()
        except Exception as e:
            logger.error(f"DB Error clear_all_chains: {e}")

    def mark_stale_chains_cancelled(self):
        """Mark any uncompleted chains from prior dead/interrupted sessions as cancelled."""
        try:
            with self._lock:
                with self._connect() as conn:
                    cursor = conn.cursor()
                    now = datetime.now().isoformat()
                    cursor.execute("""
                        UPDATE chains
                        SET status = 'cancelled', completed_at = ?, error = 'Session terminated'
                        WHERE status IN ('planning', 'pending', 'executing', 'running', 'paused', 'waiting_confirmation')
                    """, (now,))
                    cursor.execute("""
                        UPDATE actions
                        SET status = 'cancelled', completed_at = ?
                        WHERE status IN ('pending', 'running', 'executing')
                    """, (now,))
                    conn.commit()
        except Exception as e:
            logger.error(f"DB Error mark_stale_chains_cancelled: {e}")

    def _calculate_duration_with_cursor(self, cursor: sqlite3.Cursor, chain_id: str) -> float:
        try:
            cursor.execute("SELECT started_at FROM chains WHERE id = ?", (chain_id,))
            row = cursor.fetchone()
            if row and row[0]:
                start = datetime.fromisoformat(str(row[0]))
                return max(0.0, (datetime.now() - start).total_seconds())
        except Exception:
            pass
        return 0.0

    def _calculate_duration(self, chain_id: str) -> float:
        """Calculate duration for a chain"""
        try:
            with self._lock:
                with self._connect() as conn:
                    return self._calculate_duration_with_cursor(conn.cursor(), chain_id)
        except Exception:
            return 0.0

    @staticmethod
    def _parse_json_safe(raw: Optional[str], default: Any):
        if not raw:
            return default
        try:
            return json.loads(raw)
        except Exception:
            return raw

    def _format_chain_row(self, row_dict: Dict[str, Any], actions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        cid = row_dict.get("id")
        results = self._parse_json_safe(row_dict.get("results_json"), {})
        steps = self._parse_json_safe(row_dict.get("steps_json"), None)
        metadata = self._parse_json_safe(row_dict.get("metadata_json"), {})
        final_output = row_dict.get("final_output")
        if isinstance(final_output, str) and final_output.startswith(("{", "[")):
            final_output = self._parse_json_safe(final_output, final_output)

        formatted = {
            **row_dict,
            "chain_id": cid,
            "progress_percentage": float(row_dict.get("progress") or 0.0),
            "actions_completed": int(row_dict.get("completed_actions") or 0),
            "actions_failed": int(row_dict.get("failed_actions") or 0),
            "duration_seconds": float(row_dict.get("duration") or 0.0),
            "results": results if isinstance(results, dict) else {},
            "final_output": final_output,
            "metadata": metadata if isinstance(metadata, dict) else {},
        }
        if actions is not None:
            formatted["actions"] = actions
        elif isinstance(steps, list):
            formatted["actions"] = steps
        return formatted

    def _format_action_row(self, row_dict: Dict[str, Any]) -> Dict[str, Any]:
        res = self._parse_json_safe(row_dict.get("result_json"), None)
        deps = self._parse_json_safe(row_dict.get("dependencies_json"), [])
        return {
            **row_dict,
            "step": int(row_dict.get("step_index") or 0),
            "result": res,
            "dependencies": deps if isinstance(deps, list) else [],
            "duration_seconds": float(row_dict.get("duration") or 0.0),
        }

    def get_recent_chains(self, limit: int = 10, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of recent execution chains"""
        try:
            with self._lock:
                with self._connect() as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    if status:
                        cursor.execute("""
                        SELECT * FROM chains
                        WHERE LOWER(status) = LOWER(?)
                        ORDER BY created_at DESC LIMIT ?
                        """, (status, limit))
                    else:
                        cursor.execute("""
                        SELECT * FROM chains
                        ORDER BY created_at DESC LIMIT ?
                        """, (limit,))
                    return [self._format_chain_row(dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"DB Error get_recent_chains: {e}")
            return []

    def get_chain_details(self, chain_id: str) -> Optional[Dict[str, Any]]:
        """Get full details for a chain including ordered actions"""
        try:
            with self._lock:
                with self._connect() as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    cursor.execute("SELECT * FROM chains WHERE id = ?", (chain_id,))
                    row = cursor.fetchone()
                    if not row:
                        return None

                    cursor.execute(
                        "SELECT * FROM actions WHERE chain_id = ? ORDER BY step_index ASC, rowid ASC",
                        (chain_id,),
                    )
                    actions = [self._format_action_row(dict(r)) for r in cursor.fetchall()]
                    return self._format_chain_row(dict(row), actions=actions)
        except Exception as e:
            logger.error(f"DB Error get_chain_details: {e}")
            return None

    # Canonical aliases
    get_chain = get_chain_details
    list_chains = get_recent_chains


# Singleton instance
_tracker = None
_tracker_lock = threading.Lock()


def get_progress_tracker() -> PersistentProgressTracker:
    """Get singleton progress tracker"""
    global _tracker
    if _tracker is None:
        with _tracker_lock:
            if _tracker is None:
                _tracker = PersistentProgressTracker()
    return _tracker
