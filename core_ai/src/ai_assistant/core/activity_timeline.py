import sqlite3
import logging
import json
from datetime import datetime
from ai_assistant.core.database_config import get_db_path_str

logger = logging.getLogger(__name__)

class ActivityTimeline:
    """Records a chronological log of system actions for user transparency."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or get_db_path_str('timeline')
        self._setup_db()
        
    def _setup_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS timeline_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    category TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    source TEXT
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to setup timeline db: {e}")

    def log_event(self, category: str, action: str, details: dict = None, source: str = 'system'):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            details_json = json.dumps(details) if details else None
            c.execute(
                'INSERT INTO timeline_events (category, action, details, source) VALUES (?, ?, ?, ?)',
                (category, action, details_json, source)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log event: {e}")

    def get_recent_events(self, limit: int = 50) -> list:
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                'SELECT timestamp, category, action, details, source FROM timeline_events ORDER BY timestamp DESC LIMIT ?',
                (limit,)
            )
            rows = c.fetchall()
            conn.close()
            
            events = []
            for row in rows:
                events.append({
                    'timestamp': row[0],
                    'category': row[1],
                    'action': row[2],
                    'details': json.loads(row[3]) if row[3] else None,
                    'source': row[4]
                })
            return events
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []
