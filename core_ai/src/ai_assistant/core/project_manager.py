import logging
import sqlite3
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from ai_assistant.core.database_config import get_db_path_str

logger = logging.getLogger(__name__)

@dataclass
class Task:
    id: str
    description: str
    status: str = "pending" # pending, in_progress, completed
    due_date: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)

@dataclass
class Milestone:
    id: str
    name: str
    target_date: Optional[str] = None
    tasks: List[Task] = field(default_factory=list)
    completed: bool = False

@dataclass
class Project:
    id: str
    name: str
    description: str = ""
    status: str = "active" # active, on_hold, completed
    priority: str = "medium"
    deadline: Optional[str] = None
    milestones: List[Milestone] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def progress_pct(self) -> float:
        total_tasks = 0
        completed_tasks = 0
        for m in self.milestones:
            for t in m.tasks:
                total_tasks += 1
                if t.status == "completed":
                    completed_tasks += 1
        return (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0

class ProjectManager:
    """Manages user projects, milestones, tasks, and goals."""
    
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            import os
            from ai_assistant.core.database_config import DATA_DIR
            self.db_path = str(DATA_DIR / "projects.db")
        else:
            self.db_path = db_path
        self._setup_db()
        
    def _setup_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                target_date TIMESTAMP,
                status TEXT NOT NULL,
                progress_pct REAL DEFAULT 0.0,
                created_at TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def save_project(self, project: Project):
        project.updated_at = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO projects (id, data, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (project.id, json.dumps(asdict(project)), project.status, project.created_at, project.updated_at))
        conn.commit()
        conn.close()

    def get_project(self, project_id: str) -> Optional[Project]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT data FROM projects WHERE id = ?', (project_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            data = json.loads(row[0])
            # Reconstruct nested objects
            milestones = []
            for m_data in data.get('milestones', []):
                tasks = [Task(**t) for t in m_data.get('tasks', [])]
                m_data['tasks'] = tasks
                milestones.append(Milestone(**m_data))
            data['milestones'] = milestones
            return Project(**data)
        return None

    def get_all_projects(self, status: str = None) -> List[Project]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if status:
            c.execute('SELECT data FROM projects WHERE status = ?', (status,))
        else:
            c.execute('SELECT data FROM projects')
        rows = c.fetchall()
        conn.close()
        
        projects = []
        for row in rows:
            data = json.loads(row[0])
            milestones = []
            for m_data in data.get('milestones', []):
                tasks = [Task(**t) for t in m_data.get('tasks', [])]
                m_data['tasks'] = tasks
                milestones.append(Milestone(**m_data))
            data['milestones'] = milestones
            projects.append(Project(**data))
        return projects

    def add_goal(self, name: str, description: str = "", target_date: str = None) -> str:
        goal_id = f"goal_{hash(name + str(datetime.now())) % 100000:05d}"
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO goals (id, name, description, target_date, status, created_at)
            VALUES (?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
        ''', (goal_id, name, description, target_date))
        conn.commit()
        conn.close()
        return goal_id

    def get_active_goals(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT id, name, description, target_date, progress_pct FROM goals WHERE status = "active"')
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "description": r[2], "target_date": r[3], "progress_pct": r[4]} for r in rows]

    def update_goal_progress(self, goal_id: str, progress_pct: float):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        status = "completed" if progress_pct >= 100.0 else "active"
        c.execute('UPDATE goals SET progress_pct = ?, status = ? WHERE id = ?', (progress_pct, status, goal_id))
        conn.commit()
        conn.close()
