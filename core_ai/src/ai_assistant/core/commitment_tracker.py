import logging
import sqlite3
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from ai_assistant.core.database_config import DATA_DIR
from ai_assistant.ai.llm_provider import UnifiedChatInterface

logger = logging.getLogger(__name__)

@dataclass
class Commitment:
    id: str
    text: str
    action: str
    deadline: Optional[str] = None
    party: Optional[str] = None
    status: str = "pending" # pending, fulfilled, overdue, cancelled
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

class CommitmentTracker:
    """Tracks promises, reminders, and deadlines."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DATA_DIR / "commitments.db")
        self._setup_db()
        self.llm = UnifiedChatInterface()
        self.llm.add_system_message(
            "Extract any commitments, promises, or deadlines from the user's text. "
            "Return a JSON list of objects with keys: 'text', 'action', 'deadline', 'party'. "
            "If none are found, return an empty list []."
        )
        
    def _setup_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS commitments (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                action TEXT NOT NULL,
                deadline TIMESTAMP,
                party TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def add_commitment(self, text: str, action: str, deadline: str = None, party: str = None) -> str:
        cid = f"cmt_{hash(text + str(datetime.now())) % 100000:05d}"
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO commitments (id, text, action, deadline, party, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
        ''', (cid, text, action, deadline, party))
        conn.commit()
        conn.close()
        return cid

    def update_status(self, commitment_id: str, status: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('UPDATE commitments SET status = ? WHERE id = ?', (status, commitment_id))
        conn.commit()
        conn.close()

    def get_pending(self) -> List[Commitment]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT id, text, action, deadline, party, status, created_at FROM commitments WHERE status = "pending"')
        rows = c.fetchall()
        conn.close()
        return [Commitment(id=r[0], text=r[1], action=r[2], deadline=r[3], party=r[4], status=r[5], created_at=r[6]) for r in rows]

    def get_overdue(self) -> List[Commitment]:
        # Simple overdue check (string comparison for ISO dates works generally)
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT id, text, action, deadline, party, status, created_at FROM commitments WHERE status = "pending" AND deadline IS NOT NULL AND deadline < ?', (now,))
        rows = c.fetchall()
        conn.close()
        return [Commitment(id=r[0], text=r[1], action=r[2], deadline=r[3], party=r[4], status=r[5], created_at=r[6]) for r in rows]

    def extract_and_store(self, user_text: str):
        prompt = f"Extract commitments from: {user_text}"
        try:
            response = self.llm.chat(prompt, stream=False).strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            commitments = json.loads(response)
            for c in commitments:
                self.add_commitment(
                    text=c.get("text", ""),
                    action=c.get("action", ""),
                    deadline=c.get("deadline"),
                    party=c.get("party")
                )
        except Exception as e:
            logger.error(f"Failed to extract commitments: {e}")
