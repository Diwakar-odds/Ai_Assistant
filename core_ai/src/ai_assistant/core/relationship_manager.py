import logging
import sqlite3
from ai_assistant.core.database_config import get_db_path

logger = logging.getLogger(__name__)

class RelationshipManager:
    """Manages the trust level and relationship state between the user and AI."""
    
    def __init__(self):
        self.db_path = get_db_path('personal_knowledge')
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS relationship_metrics (
                    id INTEGER PRIMARY KEY,
                    interaction_count INTEGER DEFAULT 0,
                    trust_score REAL DEFAULT 0.0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Initialize if empty
            cursor = conn.execute("SELECT COUNT(*) FROM relationship_metrics")
            if cursor.fetchone()[0] == 0:
                conn.execute("INSERT INTO relationship_metrics (interaction_count, trust_score) VALUES (0, 0.0)")

    def increment_interaction(self):
        """Called after every successful interaction to slowly build trust."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE relationship_metrics 
                SET interaction_count = interaction_count + 1,
                    trust_score = MIN(100.0, trust_score + 0.1),
                    last_updated = CURRENT_TIMESTAMP
            """)

    def get_trust_level(self) -> float:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT trust_score FROM relationship_metrics")
            row = cursor.fetchone()
            return row[0] if row else 0.0

    def get_relationship_stage(self) -> str:
        score = self.get_trust_level()
        if score < 10:
            return "Formal"
        elif score < 50:
            return "Friendly"
        else:
            return "Trusted Companion"
