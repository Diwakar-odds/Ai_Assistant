# Setup centralized logging
try:
    from ai_assistant.utils.logging_config import get_logger
except ImportError:
    from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Memory Retrieval Engine (RAG)
============================
Zero-dependency long-term memory search using SQLite FTS5 across:
- conversation_ai.db (historical conversations + live synced turns)
- data/sessions/history.json (archived WebUI/Orb sessions)
- personal_knowledge.db (user_dna profile facts)
- commitments.db & automation/commitments.db
- memory.db (plaintext memory / knowledge_base / daily_summaries)
- historical_rag.db (interactions)

Uses only stdlib (`sqlite3`, `re`, `json`, `datetime`, `pathlib`, `threading`) on
the hot retrieval path so context injection completes in <25ms without blocking
on SentenceTransformer weight downloads.
"""

import sqlite3
import json
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Locate this file and resolve relative DB path to be CWD-independent.
from ai_assistant.core.database_config import DATA_DIR, PROJECT_ROOT, get_db_path_str
_DEFAULT_DB = get_db_path_str('conversation_ai')
_persist_lock = threading.Lock()
_singleton_lock = threading.Lock()
_default_retriever: Optional["MemoryRetrieval"] = None


class MemoryRetrieval:
    """Search engine for past conversations and historical stores using SQLite FTS5 + SQL fallbacks."""

    STOP_WORDS = frozenset({
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'was', 'are', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'can', 'shall', 'i', 'me', 'my', 'you',
        'your', 'we', 'our', 'they', 'their', 'it', 'its', 'this', 'that',
        'what', 'which', 'who', 'whom', 'when', 'where', 'how', 'not', 'no',
        'so', 'if', 'then', 'than', 'too', 'very', 'just', 'about', 'up',
        'out', 'some', 'any', 'all', 'more', 'also', 'like', 'into', 'from',
        'look', 'tell', 'mera', 'meri', 'mere', 'kon', 'kaun', 'kya', 'hai',
        'ka', 'ki', 'ke', 'ko', 'se', 'mein', 'ne', 'par', 'ho', 'tha',
        'thi', 'the', 'ye', 'wo', 'jo', 'aur', 'ya', 'bhi', 'sa', 'hum',
        'remember', 'recall', 'did', 'last', 'time', 'ago', 'before',
        'previously', 'earlier', 'history', 'yaad', 'pehle', 'chat', 'session',
        'talked', 'talk', 'baat', 'pichli', 'pichle', 'previous', 'old', 'purani',
    })

    MEMORY_TRIGGERS = [
        'remember', 'recall', 'did i', 'what did', 'when did', 'last time',
        'yesterday', 'last week', 'ago', 'before', 'previously', 'earlier',
        'history', 'kab', 'pehle', 'yaad', 'what was', 'have i', 'was i',
        'did we', 'what were', 'which app', 'which song', 'what song',
        'what music', 'what job', 'today earlier', 'this morning',
        'past', 'month', 'months', 'mahine', 'previous chat', 'previous session',
        'previous conversation', 'pichli chat', 'pichli baat', 'we talked',
        'humne baat', 'baat ki thi', 'who is', 'kaun hai', 'kon hai',
        'remind me', 'kya bataya', 'earlier today', 'old chat', 'purani chat',
        'purani baat', 'kl ', 'kal ', 'favorite', 'know about me',
    ]

    _BROAD_HISTORY_RE = re.compile(
        r'(?:\b(?:past|last|pichle)\s+(?:\d+(?:\s*(?:or|to|-)\s*\d+)?\s*)?(?:months?|mahine|weeks?|days?)\b'
        r'|\b(?:previous\s+(?:chat|chats|session|sessions|conversation|conversations)|old\s+chats?|pichli\s+(?:chat|baat)|purani\s+(?:chat|baat)|history|we\s+talked|humne\s+baat|baat\s+ki\s+thi|look\s+into\s+previous)\b)',
        re.IGNORECASE,
    )

    _PERSONAL_MEMORY_RE = re.compile(
        r'(?:\b(?:remember|recall|did\s+i|what\s+did|when\s+did|what\s+was|remind\s+me|history|yaad|pehle|bataya|bola\s+tha|purani|pichli|previous|old)\b'
        r'|\b(?:chat\s+history|old\s+conversation|old\s+conversations|old\s+chats?|previous\s+conversation|previous\s+session|chat\s+me\s+dekho|history\s+me|purane\s+chats?|pichli\s+chat|old\s+conversation)\b'
        r'|\b(?:dost|friend|friends|exam|paper|pariksha|test|tests|interview|birthday|janamdin|kaam|workplace|company|rehta|location)\b'
        r'|\b(?:mera|meri|mere|my)\s+[\w\u0900-\u097F\s]{1,30}?\b(?:kab|kb|when|kya|what|kahan|where|konsa|kaun\s+sa|hai|tha|thi)\b'
        r'|\b(?:konsa|kaun\s+sa|kya)\s+(?:paper|exam|dost|test|interview|subject|naam)\b'
        r'|\b(?:who\s+is|kaun\s+hai|kon\s+hai|naam\s+kya\s+hai|kya\s+naam\s+hai)\b)',
        re.IGNORECASE | re.UNICODE,
    )

    DNA_KEY_SYNONYMS = {
        "friend_name": {
            "dost", "dost ka naam", "friend", "friends", "yaar", "mitra", "doston", "dosto",
            "naam", "नाम", "दोस्त", "यार", "मित्र", "friend name", "best friend",
        },
        "user_name": {
            "naam", "name", "mera naam", "my name", "kaun hoon", "who am i", "call me", "नाम",
        },
        "upcoming_exam": {
            "paper", "exam", "exams", "pariksha", "test", "tests", "kab hai", "kb hai",
            "when is", "परीक्षा", "पेपर", "एग्जाम", "टेस्ट", "upcoming exam",
        },
        "upcoming_interview": {
            "interview", "interviews", "job interview", "interview kab hai", "इंटरव्यू",
        },
        "job_title": {
            "job", "work", "role", "kaam", "naukri", "profession", "occupation", "काम", "नौकरी",
        },
        "workplace": {
            "company", "office", "workplace", "kaam", "कंपनी", "ऑफिस",
        },
        "user_location": {
            "location", "city", "rehta", "rehte", "live", "kahan", "based", "place", "home", "ghar",
            "शहर", "कहाँ", "घर",
        },
        "favorite_color": {
            "color", "colour", "favorite color", "rang", "pasandida rang", "रंग",
        },
        "favorite_food": {
            "food", "dish", "khana", "khana peena", "favorite food", "खाना",
        },
    }

    _STARTUP_SOURCES = frozenset({
        'webui_startup', 'startup_greeting', 'new_session', 'webui_new_session',
        'backend_startup', 'webui_startup_offline', 'webui_new_session_offline',
    })

    # Audit fix A1: when True, retrieval runs on every LLM call (background context).
    RUN_AS_BACKGROUND_CONTEXT = False

    def __init__(self, db_path: Optional[str] = None, data_dir: Optional[Path] = None):
        """
        Initialize the memory retrieval engine.

        Args:
            db_path: Path to the conversation_ai.db SQLite database.
                     Defaults to `data/core/conversation_ai.db`.
            data_dir: Optional root data directory (for testing isolation).
        """
        self._explicit_db = db_path is not None
        self.db_path = str(db_path) if db_path else _DEFAULT_DB
        db_p = Path(self.db_path)
        db_p.parent.mkdir(parents=True, exist_ok=True)
        if data_dir is not None:
            self.data_dir = Path(data_dir)
            self._is_isolated = True
        elif self._explicit_db:
            self.data_dir = db_p.parent.parent if db_p.parent.name == 'core' else db_p.parent
            self._is_isolated = True
        else:
            self.data_dir = DATA_DIR
            self._is_isolated = False

        # Audit fix A6: thread-safe connections.
        self._local = threading.local()
        # Audit fix A9 (X1): lazy embedder, no import-time cost.
        self._embedder = None
        self._embedder_lock = threading.Lock()
        self._ensure_fts_index()

    # -------------------------------------------------------------------------
    # Connection management (thread-safe)
    # -------------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        """Return a thread-local SQLite connection with WAL + reasonable pragmas."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                self.db_path,
                timeout=10.0,
                check_same_thread=False,  # serialized per-thread via _local
            )
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def close(self):
        """Close thread-local SQLite connection cleanly."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

    def _ensure_conversations_table(self, conn: sqlite3.Connection):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                topic TEXT NOT NULL,
                started_at TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                state TEXT NOT NULL,
                messages TEXT NOT NULL,
                metadata TEXT NOT NULL,
                priority INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                speaker TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_vectors_cid ON conversation_vectors(conversation_id)")

    def _ensure_fts_index(self):
        """Create the FTS5 virtual table if needed, and sync any unindexed rows."""
        try:
            conn = self._conn()
            self._ensure_conversations_table(conn)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS conversation_fts USING fts5(
                    conversation_id,
                    topic,
                    message_text,
                    conversation_date,
                    tokenize='unicode61'
                )
            """)
            conn.commit()

            fts_count = conn.execute("SELECT COUNT(*) FROM conversation_fts").fetchone()[0]
            conv_count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]

            if fts_count == 0 and conv_count > 0:
                logger.info("[RAG] First run: Building memory search index...")
                self._rebuild_index_internal(conn)
                new_count = conn.execute("SELECT COUNT(*) FROM conversation_fts").fetchone()[0]
                logger.info(f"[RAG] Memory index built: {new_count} conversation entries indexed")
            elif conv_count > fts_count:
                self._sync_missing_fts_internal(conn)
            else:
                logger.info(f"[RAG] Memory search index ready ({fts_count} entries)")
        except Exception as e:
            logger.error(f"[RAG] Memory retrieval init failed: {e}")

    def _sync_missing_fts_internal(self, conn: sqlite3.Connection) -> int:
        """Index any rows in conversations that are missing from conversation_fts."""
        added = 0
        try:
            missing_rows = conn.execute("""
                SELECT c.id, c.topic, c.messages, c.started_at
                FROM conversations c
                WHERE c.id NOT IN (SELECT conversation_id FROM conversation_fts)
            """).fetchall()
            for row in missing_rows:
                conv_id, topic, messages_json, started_at = row[0], row[1], row[2], row[3]
                try:
                    messages = json.loads(messages_json) if messages_json else []
                    message_text = self._flatten_messages(messages)
                    if message_text.strip():
                        conv_date = started_at[:10] if started_at else ""
                        conn.execute(
                            "INSERT INTO conversation_fts (conversation_id, topic, message_text, conversation_date) VALUES (?, ?, ?, ?)",
                            (conv_id, topic or "", message_text, conv_date),
                        )
                        added += 1
                except Exception:
                    continue
            if added:
                conn.commit()
                logger.info(f"[RAG] Delta-synced {added} missing conversation(s) to FTS5")
        except Exception as exc:
            logger.debug(f"[RAG] Delta sync skipped: {exc}")
        return added

    def _rebuild_index_internal(self, conn: sqlite3.Connection):
        """Rebuild the FTS index from all existing conversations."""
        conn.execute("DELETE FROM conversation_fts")
        cursor = conn.execute(
            "SELECT id, topic, messages, started_at FROM conversations ORDER BY last_activity DESC"
        )
        for row in cursor:
            conv_id, topic, messages_json, started_at = row
            try:
                messages = json.loads(messages_json)
                message_text = self._flatten_messages(messages)
                if message_text.strip():
                    conv_date = started_at[:10] if started_at else ""
                    conn.execute(
                        "INSERT INTO conversation_fts (conversation_id, topic, message_text, conversation_date) VALUES (?, ?, ?, ?)",
                        (conv_id, topic, message_text, conv_date),
                    )
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Skipping conversation {conv_id}: {e}")
        conn.commit()

    def rebuild_index(self):
        """Public method to rebuild the full FTS index from scratch."""
        conn = self._conn()
        self._rebuild_index_internal(conn)
        logger.info("[RAG] Memory index rebuilt successfully")

    def index_conversation(self, context_id: str, topic: str, messages: List[Dict], timestamp: datetime):
        """Index a single conversation."""
        try:
            message_text = self._flatten_messages(messages)
            if not message_text.strip():
                return

            conv_date = timestamp.isoformat()[:10] if isinstance(timestamp, datetime) else str(timestamp)[:10]

            conn = self._conn()
            conn.execute(
                "DELETE FROM conversation_fts WHERE conversation_id = ?",
                (context_id,),
            )
            conn.execute(
                "INSERT INTO conversation_fts (conversation_id, topic, message_text, conversation_date) VALUES (?, ?, ?, ?)",
                (context_id, topic, message_text, conv_date),
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"[RAG] Failed to index conversation {context_id}: {e}")

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------

    def _build_safe_fts_query(self, keywords: List[str]) -> str:
        safe_terms = []
        for kw in keywords:
            cleaned = re.sub(r'[^a-zA-Z0-9\u0900-\u097F_]+', '', str(kw))
            if len(cleaned) >= 2:
                safe_terms.append(f'"{cleaned}"')
        return " OR ".join(safe_terms)

    def _run_fts_query(
        self,
        conn: sqlite3.Connection,
        fts_query: str,
        limit: int,
        date_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not fts_query:
            return []
        if date_filter:
            cursor = conn.execute(
                """
                SELECT conversation_id, topic, message_text, conversation_date, rank
                FROM conversation_fts
                WHERE conversation_fts MATCH ?
                AND conversation_date BETWEEN ? AND ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, date_filter['start'], date_filter['end'], limit),
            )
        else:
            cursor = conn.execute(
                """
                SELECT conversation_id, topic, message_text, conversation_date, rank
                FROM conversation_fts
                WHERE conversation_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, limit),
            )

        results = []
        seen_ids = set()
        for row in cursor:
            conv_id, topic, _message_text, conv_date, rank = row
            if conv_id in seen_ids:
                continue
            seen_ids.add(conv_id)
            msg_row = conn.execute(
                "SELECT messages, started_at, last_activity FROM conversations WHERE id = ?",
                (conv_id,),
            ).fetchone()
            actual_messages = []
            resolved_date = conv_date
            if msg_row:
                try:
                    actual_messages = json.loads(msg_row["messages"])
                except (json.JSONDecodeError, TypeError):
                    pass
                if not resolved_date and msg_row["started_at"]:
                    resolved_date = str(msg_row["started_at"])[:10]

            results.append({
                'conversation_id': conv_id,
                'topic': topic,
                'date': resolved_date,
                'messages': actual_messages,
                'relevance_score': abs(rank) if rank else 0,
            })
        return results

    def search_memory_vectors(
        self,
        query: str,
        limit: int = 4,
        min_score: float = 0.38,
        date_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search conversation history using SQLite-backed BLOB vector cosine similarity.
        Runs in-process via NumPy dot-product on L2-normalized float16 embeddings (<5ms).
        Returns top semantic matches sorted by similarity score.
        Supports date_filter (e.g. {'start': '2026-08-24', 'end': '2026-10-03'}).
        """
        clean_q = str(query or "").strip()
        if not clean_q or len(clean_q) < 3:
            return []

        try:
            from ai_assistant.ai.shared_embedder import encode_text
            import numpy as np

            q_vec = encode_text(clean_q, normalize=True)
            if q_vec is None:
                return []

            conn = self._conn()
            self._ensure_conversations_table(conn)

            where_sql = ""
            params: List[Any] = []
            if date_filter and 'start' in date_filter and 'end' in date_filter:
                where_sql = "WHERE substr(created_at, 1, 10) BETWEEN ? AND ?"
                params.extend([date_filter['start'], date_filter['end']])

            rows = conn.execute(f"""
                SELECT conversation_id, speaker, text, embedding, created_at
                FROM conversation_vectors
                {where_sql}
                ORDER BY id DESC
                LIMIT 1500
            """, params).fetchall()

            # If filtered search returned zero rows and date_filter wasn't a strict point-in-time, fallback to all
            if not rows and date_filter and not date_filter.get('point_in_time'):
                rows = conn.execute("""
                    SELECT conversation_id, speaker, text, embedding, created_at
                    FROM conversation_vectors
                    ORDER BY id DESC
                    LIMIT 1500
                """).fetchall()

            if not rows:
                return []

            blobs_concat = b"".join(bytes(r[3]) for r in rows if r[3])
            num_rows = len(blobs_concat) // 768  # 384 dimensions * 2 bytes for float16
            if num_rows == 0:
                return []

            matrix = np.frombuffer(blobs_concat[:num_rows * 768], dtype=np.float16).reshape(num_rows, 384).astype(np.float32)

            scores = np.dot(matrix, q_vec)
            ranked_indices = np.argsort(scores)[::-1]

            results = []
            seen_texts = set()
            for idx in ranked_indices:
                score = float(scores[idx])
                if score < min_score:
                    break
                row = rows[idx]
                snippet = str(row[2]).strip()
                if not snippet or snippet in seen_texts:
                    continue
                seen_texts.add(snippet)
                results.append({
                    "conversation_id": row[0],
                    "speaker": row[1],
                    "text": snippet,
                    "score": round(score, 3),
                    "created_at": row[4],
                    "date": str(row[4])[:10] if row[4] else "",
                })
                if len(results) >= limit:
                    break

            return results
        except Exception as e:
            logger.debug(f"[RAG] search_memory_vectors skipped: {e}")
            return []

    def _sql_like_fallback(
        self,
        conn: sqlite3.Connection,
        keywords: List[str],
        limit: int,
        date_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not keywords:
            return []
        like_clauses = []
        params: List[Any] = []
        for kw in keywords[:6]:
            like_val = f"%{kw}%"
            like_clauses.append("(topic LIKE ? OR messages LIKE ?)")
            params.extend([like_val, like_val])
        where_parts = [f"({' OR '.join(like_clauses)})"]
        if date_filter:
            where_parts.append("substr(started_at, 1, 10) BETWEEN ? AND ?")
            params.extend([date_filter['start'], date_filter['end']])
        params.append(limit)
        sql = f"""
            SELECT id, topic, messages, started_at, last_activity
            FROM conversations
            WHERE {' AND '.join(where_parts)}
            ORDER BY last_activity DESC
            LIMIT ?
        """
        rows = conn.execute(sql, params).fetchall()
        results = []
        for row in rows:
            try:
                actual_messages = json.loads(row["messages"]) if row["messages"] else []
            except Exception:
                actual_messages = []
            results.append({
                'conversation_id': row["id"],
                'topic': row["topic"],
                'date': str(row["started_at"] or "")[:10],
                'messages': actual_messages,
                'relevance_score': 0.5,
                'source': 'sql_like_fallback',
            })
        return results

    def _get_recent_substantive_conversations(
        self,
        conn: sqlite3.Connection,
        limit: int = 5,
        date_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent non-empty substantive conversations for broad historical overview queries."""
        where_sql = ""
        params: List[Any] = []
        if date_filter:
            where_sql = "WHERE substr(started_at, 1, 10) BETWEEN ? AND ?"
            params.extend([date_filter['start'], date_filter['end']])
        params.append(max(20, limit * 4))
        rows = conn.execute(
            f"""
            SELECT id, topic, messages, started_at, last_activity
            FROM conversations
            {where_sql}
            ORDER BY last_activity DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        if not rows and date_filter and not date_filter.get('point_in_time'):
            rows = conn.execute(
                """
                SELECT id, topic, messages, started_at, last_activity
                FROM conversations
                ORDER BY last_activity DESC
                LIMIT ?
                """,
                (max(20, limit * 4),),
            ).fetchall()

        results = []
        for row in rows:
            try:
                msgs = json.loads(row["messages"]) if row["messages"] else []
            except Exception:
                msgs = []
            if not msgs:
                continue
            combined_len = sum(len(str(m.get("content", m.get("text", ""))).strip()) for m in msgs)
            first_user = next(
                (str(m.get("content", m.get("text", ""))).strip().lower() for m in msgs if m.get("role") == "user"),
                "",
            )
            # Prefer real multi-word discussions over bare 1-word "hello" ping rows
            if first_user in ("hello", "hi", "hey") and len(msgs) <= 4 and combined_len < 180:
                continue
            results.append({
                'conversation_id': row["id"],
                'topic': row["topic"],
                'date': str(row["started_at"] or row["last_activity"] or "")[:10],
                'messages': msgs,
                'relevance_score': 0.3,
                'source': 'recent_history',
            })
            if len(results) >= limit:
                break
        return results

    def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search past conversations. Returns list of result dicts."""
        try:
            conn = self._conn()
            self._sync_missing_fts_internal(conn)

            keywords = self._extract_keywords(query)
            if not keywords:
                keywords = [
                    w for w in re.findall(r'[a-zA-Z0-9\u0900-\u097F]+', query.lower())
                    if len(w) >= 2 and w not in self.STOP_WORDS
                ]
            if not keywords:
                return []

            date_filter = self._extract_date_filter(query)
            fts_query = self._build_safe_fts_query(keywords)

            results = self._run_fts_query(conn, fts_query, limit, date_filter=date_filter)

            # Retry WITHOUT narrow date_filter if nothing found in that window
            # (e.g., "kal" can refer to tomorrow's exam discussed in an earlier session today)
            # But do NOT fallback if query was an explicit point-in-time query like "2 mahine pehle"
            if not results and date_filter and not date_filter.get('point_in_time'):
                results = self._run_fts_query(conn, fts_query, limit, date_filter=None)

            # Fast SQL LIKE fallback when FTS missed (partial substrings / non-indexed tokens)
            if not results:
                results = self._sql_like_fallback(conn, keywords, limit, date_filter=date_filter)
                if not results and date_filter and not date_filter.get('point_in_time'):
                    results = self._sql_like_fallback(conn, keywords, limit, date_filter=None)

            logger.info(f"[RAG] Memory search for '{query[:50]}' returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"[RAG] Memory search failed: {e}")
            return []

    def _semantic_fallback(
        self, query: str, limit: int, date_filter: Optional[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Best-effort optional vector fallback if an embedder is ALREADY loaded in memory.
        Never downloads weights on demand in hot chat path.
        """
        try:
            if self._embedder is None:
                return []

            q_vec = self._embedder.encode(query, convert_to_numpy=True)
            conn = self._conn()
            where_clauses = ["embedding IS NOT NULL"]
            params: List[Any] = []
            if date_filter:
                where_clauses.append("conversation_date BETWEEN ? AND ?")
                params.extend([date_filter["start"], date_filter["end"]])
            where_sql = " AND ".join(where_clauses)

            rows = conn.execute(
                f"""
                SELECT id, topic, messages, conversation_date, embedding
                FROM conversations
                WHERE {where_sql}
                ORDER BY last_activity DESC
                LIMIT 500
                """,
                params,
            ).fetchall()

            if not rows:
                return []

            import numpy as np
            scored: List[Tuple[float, sqlite3.Row]] = []
            for row in rows:
                emb_blob = row["embedding"] if "embedding" in row.keys() else None
                if not emb_blob:
                    continue
                try:
                    emb = np.frombuffer(emb_blob, dtype=np.float32)
                    score = float(np.dot(q_vec, emb) / (np.linalg.norm(q_vec) * np.linalg.norm(emb) + 1e-9))
                    scored.append((score, row))
                except Exception:
                    continue

            scored.sort(key=lambda x: x[0], reverse=True)
            top = scored[:limit]
            if not top or top[0][0] < 0.25:
                return []

            results = []
            for score, row in top:
                try:
                    actual_messages = json.loads(row["messages"])
                except (json.JSONDecodeError, TypeError):
                    actual_messages = []
                results.append({
                    'conversation_id': row["id"],
                    'topic': row["topic"],
                    'date': row["conversation_date"][:10] if row["conversation_date"] else "",
                    'messages': actual_messages,
                    'relevance_score': score,
                    'source': 'semantic_fallback',
                })
            return results

        except Exception as e:
            logger.debug(f"[RAG] Semantic fallback skipped: {e}")
            return []

    def is_memory_query(self, message: str) -> bool:
        """Return True when the user's message references past chats, history, people, or facts."""
        if self.RUN_AS_BACKGROUND_CONTEXT:
            return True
        if not message:
            return False
        message_lower = message.lower()
        if self._PERSONAL_MEMORY_RE.search(message_lower):
            return True
        if any(trigger in message_lower for trigger in self.MEMORY_TRIGGERS):
            return True
        if re.search(r'\b(?:kl|kal|aaj|pehle|pichli|pichle|purani|abhishek|mahine)\b', message_lower):
            return True
        if self._BROAD_HISTORY_RE.search(message_lower):
            return True
        return False

    def _is_broad_history_query(self, query: str) -> bool:
        if not query:
            return False
        if self._BROAD_HISTORY_RE.search(query):
            return True
        kws = self._extract_keywords(query)
        return len(kws) <= 1 and self.is_memory_query(query)

    # -------------------------------------------------------------------------
    # Cross-Store Unified Historical Context (<25ms, stdlib-only)
    # -------------------------------------------------------------------------

    def _search_session_history_json(
        self,
        keywords: List[str],
        broad: bool,
        current_session_id: Optional[str] = None,
        limit: int = 3,
    ) -> List[str]:
        history_path = self.data_dir / "sessions" / "history.json"
        if not history_path.exists():
            return []
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                sessions = json.load(f)
            if not isinstance(sessions, list):
                return []
        except Exception:
            return []

        scored: List[Tuple[int, str, str]] = []
        for idx, sess in enumerate(sessions[:50]):
            if not isinstance(sess, dict):
                continue
            sid = sess.get("id")
            if current_session_id and sid == current_session_id:
                continue

            date_label = str(sess.get("date") or sess.get("formattedDate") or "Past session")
            lines: List[str] = []
            for m in sess.get("messages") or []:
                if not isinstance(m, dict):
                    continue
                if m.get("source") in self._STARTUP_SOURCES:
                    continue
                txt = str(m.get("text") or "").strip()
                if not txt:
                    continue
                role = "User" if m.get("type") == "user" else "Pulsar"
                lines.append(f"{role}: {txt[:180]}")

            for vc in sess.get("voiceCommands") or []:
                cmd = str(vc.get("command") or "").strip() if isinstance(vc, dict) else ""
                if cmd and not any(cmd in l for l in lines):
                    lines.append(f"User (voice): {cmd[:150]}")

            if not lines:
                continue

            joined_low = " ".join(lines).lower()
            hits = sum(1 for kw in keywords if kw in joined_low) if keywords else 0
            if hits == 0 and not broad:
                continue

            snippet = " | ".join(lines[:6])
            if len(snippet) > 420:
                snippet = snippet[:417] + "..."
            entry = f"[{date_label} | Session {sid}] {snippet}"
            scored.append((hits * 10 + max(0, 5 - idx), str(sess.get("startTimestamp") or ""), entry))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[2] for item in scored[:limit]]

    def _search_personal_knowledge(self, keywords: List[str], broad: bool, query: str = "") -> List[str]:
        db_path = self.data_dir / "core" / "personal_knowledge.db"
        if not db_path.exists():
            return []
        primary_facts: List[str] = []
        secondary_facts: List[str] = []
        q_low = str(query or "").lower()
        kws_set = set(str(k).lower() for k in keywords)

        try:
            with sqlite3.connect(str(db_path), timeout=3.0) as conn:
                has_tbl = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_dna'"
                ).fetchone()
                if not has_tbl:
                    return []
                rows = conn.execute(
                    "SELECT key, value FROM user_dna ORDER BY confidence DESC, last_updated DESC LIMIT 30"
                ).fetchall()
                for k, v in rows:
                    try:
                        val_decoded = json.loads(v) if isinstance(v, str) and (v.startswith('"') or v.startswith('{') or v.startswith('[')) else v
                    except Exception:
                        val_decoded = v
                    fact_str = f"{k}: {val_decoded}"
                    fact_low = fact_str.lower()
                    syns = self.DNA_KEY_SYNONYMS.get(k, set())

                    # Check direct keyword or domain synonym match
                    is_match = (
                        broad
                        or not keywords
                        or any(kw in fact_low for kw in kws_set)
                        or any(syn in q_low for syn in syns)
                        or any(syn in kws_set for syn in syns)
                    )
                    if is_match:
                        primary_facts.append(fact_str)
                    else:
                        secondary_facts.append(fact_str)
        except Exception:
            pass

        # Also search personal knowledge traits semantically via vector similarity
        if query:
            try:
                from ai_assistant.ai.user_dna import UserDNA
                vec_traits = UserDNA(db_path=str(db_path)).search_traits_by_vector(query, limit=2, min_score=0.38)
                for vt in vec_traits:
                    f_str = f"{vt['key']}: {vt['value']}"
                    if f_str not in primary_facts:
                        primary_facts.append(f_str)
            except Exception:
                pass

        # Return targeted matching facts at the top, followed by other active facts
        if primary_facts:
            return primary_facts + secondary_facts[:6]
        if broad:
            return secondary_facts[:12]
        return []

    def _search_commitments(self, keywords: List[str], broad: bool) -> List[str]:
        candidates = [
            self.data_dir / "commitments.db",
            self.data_dir / "automation" / "commitments.db",
        ]
        items: List[str] = []
        seen = set()
        for db_path in candidates:
            if not db_path.exists():
                continue
            try:
                with sqlite3.connect(str(db_path), timeout=3.0) as conn:
                    has_tbl = conn.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='commitments'"
                    ).fetchone()
                    if not has_tbl:
                        continue
                    rows = conn.execute(
                        "SELECT text, action, deadline, party, status, created_at FROM commitments ORDER BY created_at DESC LIMIT 20"
                    ).fetchall()
                    for text, action, deadline, party, status, created_at in rows:
                        blob = f"{text or ''} {action or ''} {party or ''}".strip()
                        if not blob or blob in seen:
                            continue
                        blob_low = blob.lower()
                        if broad or not keywords or any(kw in blob_low for kw in keywords):
                            seen.add(blob)
                            date_p = str(created_at or "")[:10]
                            parts = [f"[{date_p or 'commitment'} | {status}] {text or action}"]
                            if party:
                                parts.append(f"(party: {party})")
                            if deadline:
                                parts.append(f"(deadline: {str(deadline)[:16]})")
                            items.append(" ".join(parts))
            except Exception:
                continue
        return items[:6]

    def _search_memory_db(self, keywords: List[str], broad: bool) -> List[str]:
        db_path = self.data_dir / "core" / "memory.db"
        if not db_path.exists():
            return []
        lines: List[str] = []
        try:
            with sqlite3.connect(str(db_path), timeout=3.0) as conn:
                tables = {
                    r[0]
                    for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                }
                if "knowledge_base" in tables:
                    for topic, content, created_at in conn.execute(
                        "SELECT topic, content, created_at FROM knowledge_base ORDER BY confidence DESC, created_at DESC LIMIT 20"
                    ).fetchall():
                        c_str = str(content or "")
                        if not c_str or c_str.startswith("enc:"):
                            continue
                        row_str = f"[{str(created_at or '')[:10]} KB] {topic}: {c_str[:180]}"
                        if broad or not keywords or any(kw in row_str.lower() for kw in keywords):
                            lines.append(row_str)

                if "enhanced_memory" in tables:
                    for ts, speaker, content in conn.execute(
                        "SELECT timestamp, speaker, content FROM enhanced_memory WHERE content IS NOT NULL AND content NOT LIKE 'enc:%' ORDER BY timestamp DESC LIMIT 20"
                    ).fetchall():
                        c_str = str(content or "")
                        row_str = f"[{str(ts or '')[:10]}] {speaker}: {c_str[:180]}"
                        if broad or not keywords or any(kw in row_str.lower() for kw in keywords):
                            lines.append(row_str)

                if "daily_summaries" in tables:
                    for d_str, summary, key_topics in conn.execute(
                        "SELECT date, summary, key_topics FROM daily_summaries ORDER BY date DESC LIMIT 10"
                    ).fetchall():
                        row_str = f"[{d_str}] Summary: {summary} (Topics: {key_topics})"
                        if broad or not keywords or any(kw in row_str.lower() for kw in keywords):
                            lines.append(row_str)
        except Exception:
            pass
        return lines[:6]

    def _search_historical_rag(self, keywords: List[str], broad: bool) -> List[str]:
        candidate_paths = [self.data_dir / "core" / "historical_rag.db"]
        if not self._is_isolated:
            extra_rag = PROJECT_ROOT / "core_ai" / "data" / "historical_rag.db"
            if extra_rag not in candidate_paths:
                candidate_paths.append(extra_rag)

        entries: List[str] = []
        seen = set()
        for db_path in candidate_paths:
            if not db_path.exists():
                continue
            try:
                with sqlite3.connect(str(db_path), timeout=3.0) as conn:
                    has_tbl = conn.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='interactions'"
                    ).fetchone()
                    if not has_tbl:
                        continue
                    rows = conn.execute(
                        "SELECT query, response, created_at FROM interactions ORDER BY created_at DESC LIMIT 30"
                    ).fetchall()
                    for q_txt, r_txt, ts in rows:
                        q_s = str(q_txt or "").strip()
                        r_s = str(r_txt or "").strip()
                        if not q_s or (q_s, r_s) in seen:
                            continue
                        blob_low = f"{q_s} {r_s}".lower()
                        if broad or not keywords or any(kw in blob_low for kw in keywords):
                            seen.add((q_s, r_s))
                            entries.append(f"[{str(ts or '')[:10]}] User: {q_s[:100]} -> Pulsar: {r_s[:140]}")
            except Exception:
                continue
        return entries[:5]

    def retrieve_unified_context(
        self,
        query: str,
        max_chars: int = 1600,
        max_results: int = 6,
        current_session_id: Optional[str] = None,
    ) -> str:
        """
        Aggregate relevant historical facts & past conversation snippets across all
        persistent stores cleanly within `max_chars`. Zero heavy ML weights loaded.
        """
        if not query or not str(query).strip():
            return ""

        keywords = self._extract_keywords(query)
        if not keywords:
            keywords = [
                w for w in re.findall(r'[a-zA-Z0-9\u0900-\u097F]+', query.lower())
                if len(w) >= 2 and w not in self.STOP_WORDS
            ]
        broad = self._is_broad_history_query(query)
        date_filter = self._extract_date_filter(query)

        # 1. Conversation AI FTS5 + SQL LIKE
        conv_results = self.search_memory(query, limit=max_results) if keywords else []
        if (broad or len(conv_results) < 2) and self._conn() is not None:
            try:
                recent = self._get_recent_substantive_conversations(
                    self._conn(),
                    limit=max_results,
                    date_filter=date_filter,
                )
                existing_ids = {r['conversation_id'] for r in conv_results}
                for rec in recent:
                    if rec['conversation_id'] not in existing_ids:
                        conv_results.append(rec)
                        existing_ids.add(rec['conversation_id'])
                    if len(conv_results) >= max_results:
                        break
            except Exception:
                pass

        # 2. Archived WebUI/Orb session history.json
        hist_snippets = self._search_session_history_json(
            keywords=keywords,
            broad=broad,
            current_session_id=current_session_id,
            limit=3,
        )

        # 3. User DNA (personal knowledge)
        dna_facts = self._search_personal_knowledge(keywords=keywords, broad=broad, query=query)

        # 4. Commitments
        commitment_items = self._search_commitments(keywords=keywords, broad=broad)

        # 5. Memory DB (plaintext entries, summaries, knowledge base)
        memory_items = self._search_memory_db(keywords=keywords, broad=broad)

        # 6. Historical RAG interactions
        rag_items = self._search_historical_rag(keywords=keywords, broad=broad)

        # 7. SQLite Vector Memory (Semantic Similarity across conversations)
        v_min_score = 0.25 if (date_filter and date_filter.get('point_in_time')) else 0.40
        vector_items = self.search_memory_vectors(
            query,
            limit=4,
            min_score=v_min_score,
            date_filter=date_filter,
        )

        if not any((conv_results, hist_snippets, dna_facts, commitment_items, memory_items, rag_items, vector_items)):
            return ""

        parts: List[str] = ["### VERIFIED HISTORICAL USER FACTS & RECALLED MEMORY ###"]
        budget = max_chars - 110

        def _append_section(header: str, lines: List[str]) -> None:
            if not lines:
                return
            current_len = sum(len(p) + 1 for p in parts)
            if current_len + len(header) >= budget:
                return
            parts.append(header)
            for line in lines:
                current_len = sum(len(p) + 1 for p in parts)
                if current_len + len(line) + 1 > budget:
                    break
                parts.append(line)

        if dna_facts:
            _append_section("User Facts:", [f"- {f}" for f in dna_facts])

        if hist_snippets:
            _append_section("Recent Archived Sessions:", [f"- {s}" for s in hist_snippets])

        if conv_results:
            conv_lines: List[str] = []
            for r in conv_results:
                header = f"- [{r.get('date') or 'past'}] {r.get('topic') or 'Chat'}:"
                msg_snippets = []
                for msg in (r.get('messages') or [])[:4]:
                    role = "User" if str(msg.get('role', 'user')).lower() == 'user' else "Pulsar"
                    c_txt = str(msg.get('content', msg.get('text', ''))).strip().replace('\n', ' ')
                    if not c_txt:
                        continue
                    if len(c_txt) > 150:
                        c_txt = c_txt[:147] + "..."
                    msg_snippets.append(f"{role}: {c_txt}")
                if msg_snippets:
                    conv_lines.append(f"{header} " + " | ".join(msg_snippets))
            _append_section("Past Conversations (conversation_ai.db):", conv_lines)

        if commitment_items:
            _append_section("Tracked Commitments/Notes:", [f"- {c}" for c in commitment_items])

        if memory_items:
            _append_section("Stored Memory Entries:", [f"- {m}" for m in memory_items])

        if rag_items:
            _append_section("Historical Q&A Log:", [f"- {g}" for g in rag_items])

        if vector_items:
            vec_lines = [
                f"- [{v.get('date') or 'past'}] {v.get('speaker', 'user').capitalize()}: {v.get('text')}"
                for v in vector_items
            ]
            _append_section("Semantically Recalled Conversations (Vector DB):", vec_lines)

        if len(parts) <= 1:
            return ""

        parts.append("[CRITICAL MEMORY DIRECTIVE: Answer the user's question directly using the verified facts above. Never claim you don't know or don't remember if the fact appears above.]")
        return "\n".join(parts)[:max_chars]

    def format_for_llm(self, results: List[Dict[str, Any]], max_chars: int = 1500) -> str:
        """Format search results into a context string suitable for LLM injection."""
        if not results:
            return ""

        context_parts = ["### RETRIEVED MEMORIES (from past conversations) ###"]
        chars_used = len(context_parts[0])

        for r in results:
            header = f"\n[{r['date']}] Topic: {r['topic']}"
            chars_used += len(header)
            if chars_used > max_chars:
                break
            context_parts.append(header)

            for msg in r['messages'][:6]:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if len(content) > 200:
                    content = content[:200] + "..."
                line = f"  {role}: {content}"
                chars_used += len(line)
                if chars_used > max_chars:
                    break
                context_parts.append(line)

        context_parts.append("\n(Use these memories to answer the user's question about past events)")
        return "\n".join(context_parts)

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _flatten_messages(self, messages: List[Dict]) -> str:
        parts = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            content = msg.get('content', '') or msg.get('text', '')
            if content:
                parts.append(str(content))
        return " ".join(parts)

    def _extract_keywords(self, query: str) -> List[str]:
        words = re.findall(r'[a-zA-Z0-9\u0900-\u097F]+', query.lower())
        seen = set()
        out = []
        synonym_map = {
            "paper": ["exam", "test"],
            "exam": ["paper", "test"],
            "dost": ["friend", "yaar"],
            "friend": ["dost"],
            "naam": ["name"],
            "name": ["naam"],
            "pariksha": ["exam", "paper"],
        }
        for w in words:
            if w not in self.STOP_WORDS and len(w) >= 2 and w not in seen:
                seen.add(w)
                out.append(w)
                for syn in synonym_map.get(w, []):
                    if syn not in seen:
                        seen.add(syn)
                        out.append(syn)
        return out

    def _extract_date_filter(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Extract explicit date ranges including multi-month spans ("past 4 or 5 months",
        "last 3 months", "pichle 4 mahine").
        """
        query_lower = query.lower()
        today = datetime.now()

        # Point-in-time: "X mahine pehle" / "X months ago" (target specifically around that time)
        point_in_time = re.search(
            r'(\d+)\s*(?:months?|mahine|mahino)\s*(?:ago|pehle)',
            query_lower,
        )
        if point_in_time and not re.search(r'\b(?:pichle|pichhle|past|last)\b', query_lower):
            m_count = int(point_in_time.group(1))
            target_date = today - timedelta(days=m_count * 30)
            start = (target_date - timedelta(days=20)).strftime('%Y-%m-%d')
            end = (target_date + timedelta(days=20)).strftime('%Y-%m-%d')
            return {'start': start, 'end': end, 'broad': True, 'point_in_time': True}

        # Multi-month span patterns ("past 4 or 5 months", "last 3 months", "pichle 4 mahine")
        multi_month = re.search(
            r'(?:last|past|pichle|pichhle)\s+(\d+)(?:\s*(?:to|or|-)\s*(\d+))?\s*(?:months?|mahine|mahino)'
            r'|(\d+)(?:\s*(?:to|or|-)\s*(\d+))?\s*(?:months?|mahine|mahino)\s*(?:ago|pehle|tak|se)?',
            query_lower,
        )
        if multi_month:
            raw_nums = [int(x) for x in multi_month.groups() if x is not None]
            if raw_nums:
                months_count = max(1, min(120, max(raw_nums)))
                start = (today - timedelta(days=months_count * 31)).strftime('%Y-%m-%d')
                end = today.strftime('%Y-%m-%d')
                return {'start': start, 'end': end, 'broad': True}

        if any(word in query_lower for word in ['today', 'aaj', 'this morning', 'today earlier']):
            date_str = today.strftime('%Y-%m-%d')
            return {'start': date_str, 'end': date_str}

        if re.search(r'\b(?:yesterday|kal|kl)\b', query_lower):
            yesterday = today - timedelta(days=1)
            date_str = yesterday.strftime('%Y-%m-%d')
            return {'start': date_str, 'end': date_str}

        if any(phrase in query_lower for phrase in ['last week', 'pichle hafte', 'past week']):
            start = (today - timedelta(days=7)).strftime('%Y-%m-%d')
            end = today.strftime('%Y-%m-%d')
            return {'start': start, 'end': end}

        if any(phrase in query_lower for phrase in ['last month', 'pichle mahine', 'past month']):
            start = (today - timedelta(days=31)).strftime('%Y-%m-%d')
            end = today.strftime('%Y-%m-%d')
            return {'start': start, 'end': end}

        days_ago_match = re.search(r'(\d+)\s*days?\s*ago', query_lower)
        if days_ago_match:
            days = int(days_ago_match.group(1))
            target = today - timedelta(days=days)
            date_str = target.strftime('%Y-%m-%d')
            return {'start': date_str, 'end': date_str}

        ordinal_match = re.search(r'\b(\d{1,2})(st|nd|rd|th)\b', query_lower)
        if ordinal_match:
            day = int(ordinal_match.group(1))
            if 1 <= day <= 31:
                try:
                    target = today.replace(day=day)
                    if target > today:
                        if today.month == 1:
                            target = today.replace(year=today.year - 1, month=12, day=day)
                        else:
                            target = today.replace(month=today.month - 1, day=day)
                    date_str = target.strftime('%Y-%m-%d')
                    return {'start': date_str, 'end': date_str}
                except ValueError:
                    logger.warning(
                        f"[RAG] Date filter: ordinal day {day} is not valid in current month; "
                        f"query='{query[:80]}' will fall back cleanly."
                    )

        month_names = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        }
        for month_name, month_num in month_names.items():
            pattern1 = rf'\b(\d{{1,2}})\s*{month_name}\b'
            pattern2 = rf'\b{month_name}\s*(\d{{1,2}})\b'
            match = re.search(pattern1, query_lower) or re.search(pattern2, query_lower)
            if match:
                day = int(match.group(1))
                try:
                    target = today.replace(month=month_num, day=day)
                    date_str = target.strftime('%Y-%m-%d')
                    return {'start': date_str, 'end': date_str}
                except ValueError:
                    logger.warning(
                        f"[RAG] Date filter: {month_name} {day} is not a real date; "
                        f"query='{query[:80]}' will fall back cleanly."
                    )

        return None


def get_memory_retriever(db_path: Optional[str] = None) -> MemoryRetrieval:
    """Return process-wide singleton MemoryRetrieval instance (or dedicated path instance)."""
    global _default_retriever
    if db_path:
        return MemoryRetrieval(db_path=db_path)
    if _default_retriever is None:
        with _singleton_lock:
            if _default_retriever is None:
                _default_retriever = MemoryRetrieval()
    return _default_retriever


def is_memory_query(message: str) -> bool:
    """Convenience module helper to test whether a message is a memory/history query."""
    return get_memory_retriever().is_memory_query(message)


def retrieve_unified_historical_context(
    query: str,
    *,
    max_chars: int = 1600,
    max_results: int = 6,
    current_session_id: Optional[str] = None,
    db_path: Optional[str] = None,
    only_when_triggered: bool = False,
) -> str:
    """Fast cross-store historical retrieval helper safe to invoke before LLM calls."""
    if not query or not str(query).strip():
        return ""
    retriever = get_memory_retriever(db_path=db_path)
    if only_when_triggered and not retriever.is_memory_query(query):
        return ""
    return retriever.retrieve_unified_context(
        query,
        max_chars=max_chars,
        max_results=max_results,
        current_session_id=current_session_id,
    )


def persist_turn_to_conversation_ai(
    user_text: str,
    ai_text: str,
    *,
    source: str = "chat",
    session_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """
    Lightweight thread-safe persistence of completed turns into conversation_ai.db
    + conversation_fts so every WebUI/Orb turn becomes searchable in future sessions.
    """
    u_clean = str(user_text or "").strip()
    a_clean = str(ai_text or "").strip()
    if not u_clean or not a_clean or a_clean.lower().startswith("error:"):
        return False

    target_db = str(db_path or _DEFAULT_DB)
    Path(target_db).parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    now_iso = now.isoformat()
    conv_id = f"live_{session_id}" if session_id else f"live_{now.strftime('%Y%m%d')}_{source}"
    topic_seed = re.sub(r'\s+', ' ', u_clean)[:64]

    try:
        with _persist_lock:
            with sqlite3.connect(target_db, timeout=5.0) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        topic TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        last_activity TEXT NOT NULL,
                        state TEXT NOT NULL,
                        messages TEXT NOT NULL,
                        metadata TEXT NOT NULL,
                        priority INTEGER DEFAULT 1
                    )
                """)
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS conversation_fts USING fts5(
                        conversation_id,
                        topic,
                        message_text,
                        conversation_date,
                        tokenize='unicode61'
                    )
                """)
                row = conn.execute(
                    "SELECT topic, started_at, messages, metadata FROM conversations WHERE id = ?",
                    (conv_id,),
                ).fetchone()

                if row:
                    topic = row[0] or topic_seed
                    started_at = row[1] or now_iso
                    try:
                        msgs = json.loads(row[2]) if row[2] else []
                    except Exception:
                        msgs = []
                    meta = row[3] or json.dumps({"source": source})
                else:
                    topic = topic_seed
                    started_at = now_iso
                    msgs = []
                    meta = json.dumps({"source": source, "session_id": session_id})

                msgs.append({"role": "user", "content": u_clean, "timestamp": now_iso, "source": source})
                msgs.append({"role": "assistant", "content": a_clean, "timestamp": now_iso, "source": source})
                if len(msgs) > 80:
                    msgs = msgs[-80:]

                msgs_json = json.dumps(msgs, ensure_ascii=False)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO conversations
                    (id, name, topic, started_at, last_activity, state, messages, metadata, priority)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (conv_id, f"Session {session_id or now.strftime('%Y-%m-%d')}", topic, started_at, now_iso, "active", msgs_json, meta, 1),
                )

                flattened = " ".join(
                    str(m.get("content", "")).strip()
                    for m in msgs
                    if isinstance(m, dict) and m.get("content")
                )
                conv_date = started_at[:10]
                conn.execute("DELETE FROM conversation_fts WHERE conversation_id = ?", (conv_id,))
                conn.execute(
                    "INSERT INTO conversation_fts (conversation_id, topic, message_text, conversation_date) VALUES (?, ?, ?, ?)",
                    (conv_id, topic, flattened, conv_date),
                )

                # Persist turn embeddings into SQLite conversation_vectors
                try:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS conversation_vectors (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            conversation_id TEXT NOT NULL,
                            speaker TEXT NOT NULL,
                            text TEXT NOT NULL,
                            embedding BLOB NOT NULL,
                            created_at TEXT NOT NULL
                        )
                    """)
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_vectors_cid ON conversation_vectors(conversation_id)")

                    from ai_assistant.ai.shared_embedder import encode_text
                    import numpy as np

                    u_vec = encode_text(u_clean, normalize=True)
                    if u_vec is not None:
                        u_blob = u_vec.astype(np.float16).tobytes()
                        conn.execute(
                            "INSERT INTO conversation_vectors (conversation_id, speaker, text, embedding, created_at) VALUES (?, ?, ?, ?, ?)",
                            (conv_id, "user", u_clean, u_blob, now_iso),
                        )
                    if len(a_clean) >= 15 and not a_clean.lower().startswith("error:"):
                        a_vec = encode_text(a_clean[:300], normalize=True)
                        if a_vec is not None:
                            a_blob = a_vec.astype(np.float16).tobytes()
                            conn.execute(
                                "INSERT INTO conversation_vectors (conversation_id, speaker, text, embedding, created_at) VALUES (?, ?, ?, ?, ?)",
                                (conv_id, "assistant", a_clean[:300], a_blob, now_iso),
                            )
                except Exception as v_err:
                    logger.debug(f"[RAG] Vector turn persist warning: {v_err}")

                conn.commit()
        return True
    except Exception as exc:
        logger.debug(f"[RAG] persist_turn_to_conversation_ai skipped: {exc}")
        return False
