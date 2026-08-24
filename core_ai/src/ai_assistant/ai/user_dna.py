import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
from ai_assistant.core.database_config import get_db_path

logger = logging.getLogger(__name__)

class UserDNA:
    """
    User DNA System for maintaining a long-term evolutionary profile of the user.
    Integrates static onboarding preferences with dynamic implicit feedback.
    """
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(get_db_path('personal_knowledge'))
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_dna (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        confidence REAL DEFAULT 1.0,
                        last_updated TEXT NOT NULL
                    )
                """)
        except Exception as e:
            logger.error(f"Error initializing User DNA database: {e}")

    def update_trait(self, key: str, value: Any, confidence: float = 1.0):
        """Update a specific trait in the User's DNA."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO user_dna (key, value, confidence, last_updated)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        confidence = excluded.confidence,
                        last_updated = excluded.last_updated
                """, (key, json.dumps(value), confidence, datetime.now().isoformat()))
        except Exception as e:
            logger.error(f"Error updating User DNA trait '{key}': {e}")

    def get_trait(self, key: str) -> Any:
        """Retrieve a specific trait."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM user_dna WHERE key=?", (key,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception as e:
            logger.error(f"Error retrieving User DNA trait '{key}': {e}")
        return None

    def get_full_profile(self) -> Dict[str, Any]:
        """Get the complete user DNA profile."""
        profile = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM user_dna")
                rows = cursor.fetchall()
                for key, value_str in rows:
                    profile[key] = json.loads(value_str)
        except Exception as e:
            logger.error(f"Error retrieving full User DNA profile: {e}")
        return profile

    def incorporate_onboarding_data(self, onboarding_data: Dict[str, Any]):
        """Incorporate static onboarding preferences into the living DNA."""
        for key, value in onboarding_data.items():
            self.update_trait(key, value, confidence=1.0)
