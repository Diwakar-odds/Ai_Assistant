"""
Automation Storage Module
SQLite persistence for workflow definitions, execution records, and patterns.
Extracted from automation_engine.py.
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ai_assistant.automation.automation_models import Workflow, WorkflowResult, WorkflowStatus

logger = logging.getLogger(__name__)


class AutomationStorage:
    """Manages SQLite storage for workflows and execution records."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_dir = Path(os.getenv('USERPROFILE', '.')) / '.ai_assistant' / 'data'
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(db_dir / 'workflows.db')
        else:
            self.db_path = db_path
            
        self._init_db()

    def _init_db(self):
        """Create necessary database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS workflows (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        definition TEXT NOT NULL,
                        status TEXT DEFAULT 'idle',
                        enabled INTEGER DEFAULT 1,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                cursor.execute("""
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
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS automation_patterns (
                        pattern_id TEXT PRIMARY KEY,
                        pattern_type TEXT NOT NULL,
                        pattern_data TEXT NOT NULL,
                        confidence REAL DEFAULT 0.5,
                        frequency INTEGER DEFAULT 1,
                        last_seen TEXT NOT NULL
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize workflow database: {e}")

    def save_workflow(self, workflow: Workflow) -> bool:
        """Save or update workflow in database."""
        try:
            workflow.updated_at = datetime.now().isoformat()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO workflows (id, name, description, definition, status, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    workflow.id,
                    workflow.name,
                    workflow.description,
                    json.dumps(workflow.to_dict()),
                    workflow.status.value if hasattr(workflow.status, 'value') else workflow.status,
                    1 if workflow.enabled else 0,
                    workflow.created_at,
                    workflow.updated_at
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save workflow {workflow.id}: {e}")
            return False

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Load workflow by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT definition FROM workflows WHERE id = ?", (workflow_id,))
                row = cursor.fetchone()
                if row:
                    data = json.loads(row[0])
                    return Workflow.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to get workflow {workflow_id}: {e}")
        return None

    def list_workflows(self) -> List[Workflow]:
        """List all workflows."""
        workflows = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT definition FROM workflows ORDER BY updated_at DESC")
                for row in cursor.fetchall():
                    workflows.append(Workflow.from_dict(json.loads(row[0])))
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
        return workflows

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete workflow by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
                cursor.execute("DELETE FROM workflow_executions WHERE workflow_id = ?", (workflow_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete workflow {workflow_id}: {e}")
            return False

    def record_execution(self, result: WorkflowResult) -> bool:
        """Record workflow execution result."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO workflow_executions
                    (execution_id, workflow_id, status, start_time, end_time, duration_seconds, task_results, error_message, output_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.execution_id,
                    result.workflow_id,
                    result.status.value if hasattr(result.status, 'value') else result.status,
                    result.start_time,
                    result.end_time,
                    result.duration_seconds,
                    json.dumps(result.task_results),
                    result.error_message,
                    json.dumps(result.output_data)
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to record execution {result.execution_id}: {e}")
            return False
