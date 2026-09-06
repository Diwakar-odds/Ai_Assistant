# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Memory Retrieval Engine (RAG)
============================
Zero-dependency long-term memory search using SQLite FTS5.
Allows Pulsar to answer questions about past conversations
by searching the conversation_ai.db database.

Uses only: sqlite3, re, json, datetime (all stdlib).

Optional semantic fallback: if a sentence-transformers embedder is available
via ai.memory.get_embedding_model(), we run a BM25+vector hybrid search.
Otherwise FTS5-only.
"""

import sqlite3
import json
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Locate this file and resolve relative DB path to be CWD-independent.
_MODULE_DIR = Path(__file__).resolve().parent
_DEFAULT_DB = _MODULE_DIR.parent.parent.parent / "data" / "core" / "conversation_ai.db"


class MemoryRetrieval:
    """Search engine for past conversations using SQLite FTS5 full-text search."""

    STOP_WORDS = frozenset({
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'was', 'are', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'can', 'shall', 'i', 'me', 'my', 'you',
        'your', 'we', 'our', 'they', 'their', 'it', 'its', 'this', 'that',
        'what', 'which', 'who', 'whom', 'when', 'where', 'how', 'not', 'no',
        'so', 'if', 'then', 'than', 'too', 'very', 'just', 'about', 'up',
        'out', 'some', 'any', 'all', 'more', 'also', 'like',
        'kya', 'hai', 'ka', 'ki', 'ke', 'ko', 'se', 'mein', 'ne', 'par',
        'ho', 'tha', 'thi', 'the', 'ye', 'wo', 'jo', 'aur', 'ya', 'bhi',
        'remember', 'recall', 'did', 'last', 'time', 'ago', 'before',
        'previously', 'earlier', 'history', 'yaad', 'pehle',
    })

    MEMORY_TRIGGERS = [
        'remember', 'recall', 'did i', 'what did', 'when did', 'last time',
        'yesterday', 'last week', 'ago', 'before', 'previously', 'earlier',
        'history', 'kab', 'pehle', 'yaad', 'what was', 'have i', 'was i',
        'did we', 'what were', 'which app', 'which song', 'what song',
        'what music', 'what job', 'today earlier', 'this morning',
    ]

    # Audit fix A1: when True, retrieval runs on every LLM call (background context).
    # Default keeps backward compatibility; flip to True once you've verified the
    # prompt overhead is acceptable for your model.
    RUN_AS_BACKGROUND_CONTEXT = False

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the memory retrieval engine.

        Args:
            db_path: Path to the conversation_ai.db SQLite database.
                     Defaults to a path anchored to this file's location.
        """
        self.db_path = str(db_path) if db_path else str(_DEFAULT_DB)
        # Audit fix A5: ensure parent directory exists.
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
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
                check_same_thread=False,  # we serialize via _local anyway
            )
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _ensure_fts_index(self):
        """Create the FTS5 virtual table if it doesn't exist, and do initial indexing."""
        try:
            conn = self._conn()
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

            cursor = conn.execute("SELECT COUNT(*) FROM conversation_fts")
            count = cursor.fetchone()[0]

            if count == 0:
                logger.info("[RAG] First run: Building memory search index...")
                self._rebuild_index_internal(conn)
                cursor = conn.execute("SELECT COUNT(*) FROM conversation_fts")
                new_count = cursor.fetchone()[0]
                logger.info(f"[RAG] Memory index built: {new_count} conversation entries indexed")
                print(f"[OK] Memory index built: {new_count} conversation entries indexed")
            else:
                logger.info(f"[RAG] Memory search index ready ({count} entries)")
        except Exception as e:
            logger.error(f"[RAG] Memory retrieval init failed: {e}")
            print(f"[WARN] Memory retrieval init failed: {e}")

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
        """Index a single conversation. Audit note A4: O(n) per save — acceptable for chat."""
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

    def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search past conversations. Returns list of result dicts."""
        try:
            keywords = self._extract_keywords(query)
            if not keywords:
                keywords = [w for w in query.lower().split() if len(w) > 2 and w not in self.STOP_WORDS]
            if not keywords:
                return []

            date_filter = self._extract_date_filter(query)
            fts_query = " OR ".join(keywords)
            conn = self._conn()

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
            for row in cursor:
                conv_id, topic, message_text, conv_date, rank = row
                msg_cursor = conn.execute(
                    "SELECT messages FROM conversations WHERE id = ?", (conv_id,)
                )
                msg_row = msg_cursor.fetchone()
                actual_messages = []
                if msg_row:
                    try:
                        actual_messages = json.loads(msg_row["messages"])
                    except (json.JSONDecodeError, TypeError):
                        pass

                results.append({
                    'conversation_id': conv_id,
                    'topic': topic,
                    'date': conv_date,
                    'messages': actual_messages,
                    'relevance_score': abs(rank) if rank else 0,
                })

            # Audit fix A2: optional semantic fallback (hybrid).
            if not results:
                results = self._semantic_fallback(query, limit=limit, date_filter=date_filter)

            logger.info(f"[RAG] Memory search for '{query[:50]}' returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"[RAG] Memory search failed: {e}")
            return []

    def _semantic_fallback(
        self, query: str, limit: int, date_filter: Optional[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Audit fix A2: if FTS returns nothing and an embedder is available, try vector search.
        Best-effort only — degrades gracefully if sentence-transformers is missing.
        """
        try:
            with self._embedder_lock:
                if self._embedder is None:
                    try:
                        from ai_assistant.ai.memory import get_embedding_model
                        self._embedder = get_embedding_model()
                    except Exception:
                        return []
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
        """Audit fix A1: gate stays as opt-in default; flip RUN_AS_BACKGROUND_CONTEXT to bypass."""
        if self.RUN_AS_BACKGROUND_CONTEXT:
            return True
        message_lower = message.lower()
        return any(trigger in message_lower for trigger in self.MEMORY_TRIGGERS)

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
            content = msg.get('content', '')
            if content:
                parts.append(content)
        return " ".join(parts)

    def _extract_keywords(self, query: str) -> List[str]:
        words = re.findall(r'[a-zA-Z\u0900-\u097F]+', query.lower())
        return [w for w in words if w not in self.STOP_WORDS and len(w) > 2]

    def _extract_date_filter(self, query: str) -> Optional[Dict[str, str]]:
        """
        Audit fix A3: log a WARNING when an extracted filter would yield zero rows
        (e.g. feb 30) instead of silently returning an unmatchable filter.
        """
        query_lower = query.lower()
        today = datetime.now()

        if any(word in query_lower for word in ['today', 'aaj', 'this morning', 'today earlier']):
            date_str = today.strftime('%Y-%m-%d')
            return {'start': date_str, 'end': date_str}

        if any(word in query_lower for word in ['yesterday', 'kal']):
            yesterday = today - timedelta(days=1)
            date_str = yesterday.strftime('%Y-%m-%d')
            return {'start': date_str, 'end': date_str}

        if any(phrase in query_lower for phrase in ['last week', 'pichle hafte', 'past week']):
            start = (today - timedelta(days=7)).strftime('%Y-%m-%d')
            end = today.strftime('%Y-%m-%d')
            return {'start': start, 'end': end}

        if any(phrase in query_lower for phrase in ['last month', 'pichle mahine', 'past month']):
            start = (today - timedelta(days=30)).strftime('%Y-%m-%d')
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
                        f"query='{query[:80]}' will return no date-scoped results."
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
                        f"query='{query[:80]}' will return no date-scoped results."
                    )

        return None
