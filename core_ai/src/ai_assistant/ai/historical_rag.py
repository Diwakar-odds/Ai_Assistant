# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Historical Retrieval-Augmented Generation (RAG) — patched.
Uses past successful interactions to improve responses.

Audit fixes applied:
  B5  Absolute DB path (CWD-independent)
  B1  FAISS index persistence (.faiss + .ids.json sidecar)
  B2  Embedding dim/version guard via schema-version stamp
  B3  augment_prompt() rewrite — query is a separate arg, fail loudly
  B4  Larger over-fetch factor (top_k * 5) to compensate for post-filter
  B6  Time-decayed success score in ranking
  B7  Write-time dedup via UNIQUE query_hash
"""

import sqlite3
import json
import threading
import hashlib
import math
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

try:
    import numpy as np
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("[RAG] FAISS not available - using fallback search")

try:
    from sentence_transformers import SentenceTransformer
    SBERT_AVAILABLE = True
except ImportError:
    SBERT_AVAILABLE = False
    logger.warning("[RAG] sentence-transformers not available")

# Audit fix B2: schema version. Bump if you change embedding model or DB layout.
SCHEMA_VERSION = 2
INDEX_FILENAME = "historical_rag.faiss"
IDS_FILENAME = "historical_rag.ids.json"
META_FILENAME = "historical_rag.meta.json"

# Audit fix B5: anchor DB/index files relative to this file's location.
_MODULE_DIR = Path(__file__).resolve().parent
_DATA_DIR = _MODULE_DIR.parent.parent.parent / "data"


def _default_paths() -> Tuple[Path, Path, Path, Path]:
    data_dir = _DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    db = data_dir / "historical_rag.db"
    idx = data_dir / INDEX_FILENAME
    ids = data_dir / IDS_FILENAME
    meta = data_dir / META_FILENAME
    return db, idx, ids, meta


class HistoricalRAG:
    """
    Retrieval-Augmented Generation using historical interactions.
    """

    DEFAULT_OVERFETCH = 5  # Audit fix B4

    def __init__(
        self,
        db_path: Optional[str] = None,
        model_name: str = "all-MiniLM-L6-v2",
        embedding_dim: int = 384,
    ):
        self.model_name = model_name
        db_path, idx_path, ids_path, meta_path = _default_paths() if db_path is None else (
            Path(db_path),
            Path(db_path).with_suffix(".faiss"),
            Path(db_path).with_suffix(".ids.json"),
            Path(db_path).with_suffix(".meta.json"),
        )
        self.db_path = str(db_path)
        self.index_path = str(idx_path)
        self.ids_path = str(ids_path)
        self.meta_path = str(meta_path)
        self.embedding_dim = embedding_dim

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Audit fix A6: thread-local connections.
        self._local = threading.local()

        if SBERT_AVAILABLE:
            try:
                self.embedder = SentenceTransformer(model_name)
                self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
            except Exception as e:
                logger.warning(f"[RAG] Embedder init failed: {e}")
                self.embedder = None
        else:
            self.embedder = None

        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.index_to_id: List[int] = []
        else:
            self.index = None
            self.index_to_id = []

        self._init_database()
        self._load_index()

    # -------------------------------------------------------------------------
    # Connection / persistence
    # -------------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _init_database(self):
        """Initialize database (audit B7: dedup via query_hash)."""
        conn = self._conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                query_hash TEXT NOT NULL UNIQUE,
                response TEXT NOT NULL,
                context TEXT,
                user_feedback REAL DEFAULT 0.5,
                success_score REAL DEFAULT 0.5,
                embedding BLOB,
                embedding_model TEXT,
                embedding_dim INTEGER,
                created_at TEXT NOT NULL,
                used_count INTEGER DEFAULT 0,
                last_used TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS retrieval_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                retrieved_ids TEXT NOT NULL,
                num_retrieved INTEGER NOT NULL,
                response_quality REAL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_success_score ON interactions(success_score DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON interactions(created_at DESC)")
        conn.commit()

    def _read_meta(self) -> Dict:
        p = Path(self.meta_path)
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write_meta(self, meta: Dict) -> None:
        Path(self.meta_path).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def _load_index(self):
        """
        Audit fix B1 + B2:
        - Load persisted FAISS index + ids sidecar if schema version matches.
        - Otherwise rebuild from SQLite, filtering rows whose embedding dim differs.
        """
        if not FAISS_AVAILABLE or not self.embedder:
            return

        meta = self._read_meta()
        persisted_ok = (
            meta.get("schema_version") == SCHEMA_VERSION
            and meta.get("embedding_dim") == self.embedding_dim
            and meta.get("model_name") == self.model_name
            and Path(self.index_path).exists()
            and Path(self.ids_path).exists()
        )

        if persisted_ok:
            try:
                loaded = faiss.read_index(self.index_path)
                if loaded.d == self.embedding_dim:
                    self.index = loaded
                    self.index_to_id = json.loads(Path(self.ids_path).read_text(encoding="utf-8"))
                    logger.info(f"[RAG] Loaded FAISS index ({self.index.ntotal} vectors) from disk")
                    return
            except Exception as e:
                logger.warning(f"[RAG] Failed to load persisted FAISS index: {e}")

        # Fall back: rebuild from SQLite, skipping rows whose dim doesn't match.
        conn = self._conn()
        cursor = conn.execute(
            """
            SELECT id, embedding, embedding_dim
            FROM interactions
            WHERE embedding IS NOT NULL
            ORDER BY id
            """
        )
        embeddings: List[np.ndarray] = []
        ids: List[int] = []
        skipped = 0
        for row in cursor.fetchall():
            row_dim = row["embedding_dim"]
            if row_dim is not None and row_dim != self.embedding_dim:
                skipped += 1
                continue
            try:
                emb = np.frombuffer(row["embedding"], dtype=np.float32)
                if emb.shape[0] != self.embedding_dim:
                    skipped += 1
                    continue
                embeddings.append(emb)
                ids.append(row["id"])
            except Exception:
                skipped += 1

        if embeddings:
            arr = np.array(embeddings).astype("float32")
            self.index.add(arr)
        self.index_to_id = ids
        if skipped:
            logger.warning(f"[RAG] Skipped {skipped} rows with mismatched embedding dim during load")
        self._persist_index()

    def _persist_index(self) -> None:
        """Persist FAISS index + ids sidecar + meta stamp (audit fix B1)."""
        if not FAISS_AVAILABLE or self.index is None:
            return
        try:
            faiss.write_index(self.index, self.index_path)
            Path(self.ids_path).write_text(json.dumps(self.index_to_id), encoding="utf-8")
            self._write_meta({
                "schema_version": SCHEMA_VERSION,
                "embedding_dim": self.embedding_dim,
                "model_name": self.model_name,
                "saved_at": datetime.now().isoformat(),
                "size": int(self.index.ntotal),
            })
        except Exception as e:
            logger.warning(f"[RAG] Failed to persist FAISS index: {e}")

    # -------------------------------------------------------------------------
    # Writes
    # -------------------------------------------------------------------------

    def add_interaction(
        self,
        query: str,
        response: str,
        context: Optional[Dict] = None,
        success_score: float = 0.5,
    ) -> int:
        """
        Add an interaction. Audit fix B7: dedup by query_hash.
        Returns the interaction id (existing id if duplicate).
        """
        qhash = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
        embedding = None
        embedding_blob = None
        if self.embedder:
            try:
                embedding = self.embedder.encode(query, convert_to_numpy=True)
                embedding_blob = embedding.astype("float32").tobytes()
            except Exception:
                pass

        conn = self._conn()
        # Dedup: if hash exists, update response/score and reuse id.
        existing = conn.execute(
            "SELECT id FROM interactions WHERE query_hash = ?", (qhash,)
        ).fetchone()
        if existing:
            interaction_id = existing["id"]
            conn.execute(
                """
                UPDATE interactions
                SET response = ?, context = ?, success_score = ?,
                    embedding = COALESCE(?, embedding),
                    embedding_model = COALESCE(?, embedding_model),
                    embedding_dim = COALESCE(?, embedding_dim)
                WHERE id = ?
                """,
                (
                    response,
                    json.dumps(context) if context else None,
                    float(success_score),
                    embedding_blob,
                    self.model_name if embedding_blob else None,
                    self.embedding_dim if embedding_blob else None,
                    interaction_id,
                ),
            )
            conn.commit()
            return interaction_id

        cursor = conn.execute(
            """
            INSERT INTO interactions
            (query, query_hash, response, context, success_score, embedding,
             embedding_model, embedding_dim, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query,
                qhash,
                response,
                json.dumps(context) if context else None,
                float(success_score),
                embedding_blob,
                self.model_name if embedding_blob else None,
                self.embedding_dim if embedding_blob else None,
                datetime.now().isoformat(),
            ),
        )
        interaction_id = cursor.lastrowid
        conn.commit()

        if FAISS_AVAILABLE and embedding is not None:
            self.index.add(np.array([embedding]).astype("float32"))
            self.index_to_id.append(interaction_id)
            self._persist_index()

        return interaction_id

    # -------------------------------------------------------------------------
    # Retrieval
    # -------------------------------------------------------------------------

    def retrieve_similar(
        self,
        query: str,
        top_k: int = 5,
        min_success_score: float = 0.6,
        half_life_days: float = 180.0,
        overfetch: Optional[int] = None,
    ) -> List[Dict]:
        """
        Retrieve similar past interactions.
        Audit fix B6: success score is time-decayed in ranking.
        Audit fix B4: dynamically fetch from FAISS until top_k is satisfied.
        """
        if not self.embedder or not FAISS_AVAILABLE:
            return self._retrieve_fallback(query, top_k, min_success_score)

        try:
            query_embedding = self.embedder.encode(query, convert_to_numpy=True)
        except Exception:
            return self._retrieve_fallback(query, top_k, min_success_score)

        if self.index.ntotal == 0:
            return []

        now = datetime.now()
        results: List[Dict] = []
        fetched_indices = set()
        
        # Iterative fetching logic (fixes B4 post-filtering reduction)
        k = min(top_k * (overfetch or 2), self.index.ntotal)
        conn = self._conn()
        
        while len(results) < top_k:
            distances, indices = self.index.search(
                np.array([query_embedding]).astype("float32"), k
            )
            
            new_results_found = False
            for idx, distance in zip(indices[0], distances[0]):
                if idx < 0 or idx >= len(self.index_to_id) or idx in fetched_indices:
                    continue
                
                fetched_indices.add(idx)
                interaction_id = self.index_to_id[idx]
                row = conn.execute(
                    """
                    SELECT query, response, context, success_score, used_count, created_at
                    FROM interactions WHERE id = ?
                    """,
                    (interaction_id,),
                ).fetchone()
                
                if not row or row["success_score"] < min_success_score:
                    continue

                try:
                    age_days = (now - datetime.fromisoformat(row["created_at"])).total_seconds() / 86400.0
                    if age_days < 0:
                        age_days = 0.0
                    decay = math.pow(0.5, age_days / max(half_life_days, 1e-6))
                except Exception:
                    decay = 1.0

                similarity = 1 / (1 + float(distance))
                combined = similarity * row["success_score"] * decay

                results.append({
                    'id': interaction_id,
                    'query': row["query"],
                    'response': row["response"],
                    'context': json.loads(row["context"]) if row["context"] else None,
                    'similarity': similarity,
                    'success_score': row["success_score"],
                    'used_count': row["used_count"],
                    'age_days': age_days,
                    'time_decay': decay,
                    'combined_score': combined,
                })
                
                new_results_found = True
                
                conn.execute(
                    """
                    UPDATE interactions
                    SET used_count = used_count + 1, last_used = ?
                    WHERE id = ?
                    """,
                    (now.isoformat(), interaction_id),
                )
            
            if len(results) >= top_k:
                break
                
            if k == self.index.ntotal:
                break
                
            # If we didn't find enough, increase k and try again
            k = min(k * 2, self.index.ntotal)

        conn.commit()

        results.sort(key=lambda x: x['combined_score'], reverse=True)
        top = results[:top_k]
        self._record_retrieval(query, [r['id'] for r in top])
        return top

    def _retrieve_fallback(
        self, query: str, top_k: int = 5, min_success_score: float = 0.6
    ) -> List[Dict]:
        query_words = set(query.lower().split())
        results = []
        conn = self._conn()
        cursor = conn.execute(
            """
            SELECT id, query, response, context, success_score
            FROM interactions
            WHERE success_score >= ?
            ORDER BY created_at DESC
            LIMIT 100
            """,
            (min_success_score,),
        )
        for row in cursor.fetchall():
            q_words = set(row["query"].lower().split())
            intersection = len(query_words & q_words)
            union = len(query_words | q_words)
            if union > 0:
                similarity = intersection / union
                if similarity > 0.3:
                    results.append({
                        'id': row["id"],
                        'query': row["query"],
                        'response': row["response"],
                        'context': json.loads(row["context"]) if row["context"] else None,
                        'similarity': similarity,
                        'success_score': row["success_score"],
                        'used_count': 0,
                    })
        results.sort(key=lambda x: x['similarity'] * x['success_score'], reverse=True)
        return results[:top_k]

    def _record_retrieval(self, query: str, retrieved_ids: List[int]) -> None:
        try:
            conn = self._conn()
            conn.execute(
                """
                INSERT INTO retrieval_stats (query, retrieved_ids, num_retrieved, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (query, json.dumps(retrieved_ids), len(retrieved_ids), datetime.now().isoformat()),
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"[RAG] _record_retrieval failed: {e}")

    # -------------------------------------------------------------------------
    # Prompt construction (audit fix B3 — safe signature)
    # -------------------------------------------------------------------------

    def build_examples_block(
        self,
        query: str,
        max_examples: int = 3,
        per_example_chars: int = 200,
        total_chars: int = 1500,
    ) -> str:
        """
        Audit fix B3: returns an explicit examples block. Caller composes the
        final prompt. No silent {query} substitution. Bounded by total_chars.
        """
        similar = self.retrieve_similar(query, top_k=max_examples)
        if not similar:
            return ""

        out = ["### Relevant past interactions ###"]
        used = len(out[0])
        for i, ex in enumerate(similar, 1):
            chunk = (
                f"\nExample {i}:\n"
                f"Q: {ex['query']}\n"
                f"A: {ex['response'][:per_example_chars]}..."
            )
            if used + len(chunk) > total_chars:
                break
            out.append(chunk)
            used += len(chunk)
        if len(out) == 1:
            return ""
        return "\n".join(out)

    def augment_prompt(self, query: str, base_prompt: str, max_examples: int = 3) -> str:
        """
        Audit fix B3: kept for backward compatibility, but raises loudly if
        base_prompt does not contain a {query} placeholder. Returns a prompt
        with examples prepended and the {query} placeholder replaced.
        """
        if "{query}" not in base_prompt:
            raise ValueError(
                "augment_prompt() requires base_prompt to contain '{query}'. "
                "Use build_examples_block() instead and compose the prompt yourself."
            )
        examples = self.build_examples_block(query, max_examples=max_examples)
        if not examples:
            return base_prompt.replace("{query}", query)
        composed = base_prompt.replace(
            "{query}",
            f"{examples}\n\nCurrent query: {query}",
        )
        return composed

    # -------------------------------------------------------------------------
    # Feedback / stats
    # -------------------------------------------------------------------------

    def update_feedback(self, interaction_id: int, feedback_score: float) -> None:
        conn = self._conn()
        conn.execute(
            """
            UPDATE interactions
            SET user_feedback = ?, success_score = (success_score + ?) / 2
            WHERE id = ?
            """,
            (feedback_score, feedback_score, interaction_id),
        )
        conn.commit()

    def get_stats(self) -> Dict:
        conn = self._conn()
        row = conn.execute(
            """
            SELECT
                COUNT(*) as total,
                AVG(success_score) as avg_success,
                SUM(used_count) as total_retrievals,
                SUM(CASE WHEN success_score >= 0.7 THEN 1 ELSE 0 END) as high_quality
            FROM interactions
            """
        ).fetchone()
        if row:
            total = row["total"] or 0
            return {
                'total_interactions': total,
                'average_success_score': row["avg_success"] or 0.0,
                'total_retrievals': row["total_retrievals"] or 0,
                'high_quality_percentage': (row["high_quality"] / total * 100) if total else 0,
                'index_size': self.index.ntotal if FAISS_AVAILABLE else 0,
                'schema_version': SCHEMA_VERSION,
            }
        return {}


def example_usage():
    """Demonstrate historical RAG (audit fix B3: pass {query} explicitly)."""
    rag = HistoricalRAG()
    rag.add_interaction(
        "How do I open Chrome?",
        "To open Chrome, use the command: open_application('chrome')",
        context={'category': 'automation'},
        success_score=0.9,
    )
    print(rag.get_stats())


if __name__ == "__main__":
    example_usage()
