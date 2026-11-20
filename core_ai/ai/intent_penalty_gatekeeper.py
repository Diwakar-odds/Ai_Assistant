"""
Generalized Active Intent Penalty Gatekeeper (Closed-Loop Telemetry & Actuation).
Persists intent penalties derived from user negative feedback, command execution aborts,
and error corrections. Prevents brittle Tier 1 regex patterns or semantic misclassifications
from repeatedly misrouting commands.
"""

from datetime import datetime
import json
import logging
from pathlib import Path
import re
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

_CONVERSATIONAL_FILLERS = {
    "bhai", "yaar", "dost", "bro", "please", "plz", "sir", "suno", "sun",
    "mujhe", "mera", "meri", "mere", "ko", "karo", "karein", "do", "dijiye",
    "can", "you", "tell", "me", "how", "to", "kya", "aap", "kar", "sakte", "ho",
    "ek", "zara", "thoda"
}


class IntentPenaltyGatekeeper:
    """
    Active Gatekeeper that records and enforces negative feedback on intent routing.
    Thread-safe, backed by SQLite with in-memory caching for <0.1ms checks.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from core_ai.core.database_config import get_db_path_str
            self.db_path = get_db_path_str("intent_penalties")
        else:
            self.db_path = str(db_path)

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._mem_cache: Dict[Tuple[str, str], float] = {}  # (pattern_key, intent_name) -> penalty_score
        self._cache_initialized = False

        self._init_db()
        self._load_cache()

    def _init_db(self):
        """Initialize database schema with WAL mode."""
        with self._lock, sqlite3.connect(self.db_path, timeout=5.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS intent_penalties (
                    pattern_key TEXT NOT NULL,
                    intent_name TEXT NOT NULL,
                    raw_example TEXT,
                    penalty_score REAL DEFAULT 1.0,
                    fail_count INTEGER DEFAULT 1,
                    success_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    PRIMARY KEY (pattern_key, intent_name)
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_penalties_intent ON intent_penalties(intent_name);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_penalties_score ON intent_penalties(penalty_score);")
            conn.commit()

    def _load_cache(self):
        """Warm in-memory cache for ultra-fast lookup."""
        with self._lock, sqlite3.connect(self.db_path, timeout=5.0) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pattern_key, intent_name, penalty_score FROM intent_penalties WHERE penalty_score > 0;")
            rows = cursor.fetchall()
            self._mem_cache = {(r[0], r[1]): float(r[2]) for r in rows}
            self._cache_initialized = True

    @staticmethod
    def extract_pattern_tokens(message: str) -> List[str]:
        """
        Extracts canonicalized tokens from user query.
        Normalizes Devanagari script, strips punctuation, and removes generic conversational fillers.
        """
        if not message or not message.strip():
            return []

        from core_ai.core.local_command_normalizer import normalize_hinglish_devanagari
        normalized = normalize_hinglish_devanagari(message).lower().strip()

        # Replace punctuation with whitespace
        cleaned = re.sub(r"[^\w\s]", " ", normalized)
        tokens = cleaned.split()

        filtered = [t for t in tokens if t not in _CONVERSATIONAL_FILLERS and len(t) > 1]
        return sorted(list(set(filtered)))

    def generate_pattern_key(self, message: str) -> str:
        """
        Generates a canonical token key for generalized matching.
        E.g. 'ek chutkula sunao bhai' -> 'chutkula_sunao'
             'chutkula sunao please'  -> 'chutkula_sunao'
        """
        tokens = self.extract_pattern_tokens(message)
        if not tokens:
            # Fallback to alphanumeric-only normalized string
            cleaned = re.sub(r"[^\w]", "", message.lower())
            return cleaned or "empty"
        return "_".join(tokens)

    def is_penalized(self, message: str, intent_name: str, threshold: float = 0.5) -> bool:
        """
        Checks if an intent has an active penalty on this query or its generalized pattern.
        Runs in < 0.1ms using in-memory cache.
        """
        if not message or not intent_name:
            return False

        key = self.generate_pattern_key(message)
        tokens = set(self.extract_pattern_tokens(message))

        with self._lock:
            # 1. Exact canonical key check
            score = self._mem_cache.get((key, intent_name), 0.0)
            if score >= threshold:
                return True

            # 2. Generalized token overlap / subset check across stored patterns for this intent
            if tokens:
                for (stored_key, stored_intent), stored_score in self._mem_cache.items():
                    if stored_intent != intent_name or stored_score < threshold:
                        continue
                    stored_tokens = set(stored_key.split("_"))
                    if not stored_tokens:
                        continue
                    # Check token overlap
                    intersection = tokens & stored_tokens
                    if not intersection:
                        continue
                    # If stored pattern tokens are a subset of current query tokens
                    if stored_tokens.issubset(tokens):
                        return True
                    # Or high Jaccard similarity
                    union = tokens | stored_tokens
                    similarity = len(intersection) / len(union) if union else 0.0
                    if similarity >= 0.70:
                        return True

        return False

    def record_negative_feedback(
        self,
        message: str,
        intent_name: str,
        penalty_delta: float = 1.0,
        reason: str = ""
    ) -> float:
        """
        Actuator: Penalizes an intent for a query pattern when negative feedback is received.
        Increases penalty_score and fail_count.
        """
        if not message or not intent_name:
            return 0.0

        key = self.generate_pattern_key(message)
        with self._lock, sqlite3.connect(self.db_path, timeout=5.0) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT penalty_score, fail_count FROM intent_penalties WHERE pattern_key = ? AND intent_name = ?;",
                (key, intent_name)
            )
            row = cursor.fetchone()
            if row:
                new_score = min(5.0, float(row[0]) + penalty_delta)
                new_fails = int(row[1]) + 1
                cursor.execute(
                    """
                    UPDATE intent_penalties
                    SET penalty_score = ?, fail_count = ?, last_updated = CURRENT_TIMESTAMP, notes = ?
                    WHERE pattern_key = ? AND intent_name = ?;
                    """,
                    (new_score, new_fails, reason, key, intent_name)
                )
            else:
                new_score = penalty_delta
                new_fails = 1
                cursor.execute(
                    """
                    INSERT INTO intent_penalties (pattern_key, intent_name, raw_example, penalty_score, fail_count, notes)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (key, intent_name, message.strip(), new_score, new_fails, reason)
                )
            conn.commit()

            self._mem_cache[(key, intent_name)] = new_score
            logger.info(
                f"🚨 Intent penalty recorded: intent='{intent_name}', pattern='{key}', score={new_score:.2f}, fails={new_fails}"
            )
            return new_score

    def record_positive_feedback(
        self,
        message: str,
        intent_name: str,
        reward_delta: float = 0.5
    ) -> float:
        """
        Rewards an intent for successful execution or user confirmation.
        Decreases penalty_score and increments success_count.
        """
        if not message or not intent_name:
            return 0.0

        key = self.generate_pattern_key(message)
        with self._lock, sqlite3.connect(self.db_path, timeout=5.0) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT penalty_score, success_count FROM intent_penalties WHERE pattern_key = ? AND intent_name = ?;",
                (key, intent_name)
            )
            row = cursor.fetchone()
            if not row:
                return 0.0

            new_score = max(0.0, float(row[0]) - reward_delta)
            new_success = int(row[1]) + 1
            if new_score <= 0.0:
                cursor.execute(
                    "DELETE FROM intent_penalties WHERE pattern_key = ? AND intent_name = ?;",
                    (key, intent_name)
                )
                self._mem_cache.pop((key, intent_name), None)
            else:
                cursor.execute(
                    """
                    UPDATE intent_penalties
                    SET penalty_score = ?, success_count = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE pattern_key = ? AND intent_name = ?;
                    """,
                    (new_score, new_success, key, intent_name)
                )
                self._mem_cache[(key, intent_name)] = new_score
            conn.commit()
            return new_score

    def clear_penalty(self, pattern_or_intent: str) -> int:
        """Clears penalties by intent_name or pattern_key."""
        target = pattern_or_intent.strip()
        with self._lock, sqlite3.connect(self.db_path, timeout=5.0) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM intent_penalties WHERE intent_name = ? OR pattern_key = ?;",
                (target, target)
            )
            deleted = cursor.rowcount
            conn.commit()
            # Update cache
            to_remove = [k for k in self._mem_cache if k[0] == target or k[1] == target]
            for k in to_remove:
                self._mem_cache.pop(k, None)
            return deleted

    def get_all_penalties(self) -> List[Dict[str, Any]]:
        """Returns all currently active penalties for diagnostics and dashboards."""
        with self._lock, sqlite3.connect(self.db_path, timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM intent_penalties ORDER BY penalty_score DESC, fail_count DESC;")
            return [dict(r) for r in cursor.fetchall()]


# Singleton instance
_gatekeeper_lock = threading.RLock()
_gatekeeper_instance: Optional[IntentPenaltyGatekeeper] = None


def get_intent_penalty_gatekeeper() -> IntentPenaltyGatekeeper:
    """Return process-wide singleton IntentPenaltyGatekeeper instance."""
    global _gatekeeper_instance
    with _gatekeeper_lock:
        if _gatekeeper_instance is None:
            _gatekeeper_instance = IntentPenaltyGatekeeper()
        return _gatekeeper_instance
