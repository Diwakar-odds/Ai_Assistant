"""
One-time / Delta sync script:
Scans data/core/conversation_ai.db conversations table and backfills any turns
that do not have embeddings in the conversation_vectors table.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).resolve().parents[1]
sys.path.extend([str(project_root), str(project_root / "core_ai" / "src"), str(project_root / "backend")])

os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import numpy as np
from ai_assistant.core.database_config import get_db_path
from ai_assistant.ai.shared_embedder import encode_batch


def sync_vectors():
    db_path = str(get_db_path("conversation_ai"))
    print(f"Connecting to: {db_path}")

    with sqlite3.connect(db_path) as conn:
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

        existing_cids = {
            r[0] for r in conn.execute("SELECT DISTINCT conversation_id FROM conversation_vectors").fetchall()
        }

        rows = conn.execute(
            "SELECT id, started_at, messages FROM conversations ORDER BY started_at ASC"
        ).fetchall()

        items_to_embed = []  # tuples of (conv_id, speaker, text, created_at)
        texts_to_embed = []

        for cid, started_at, msgs_json in rows:
            if cid in existing_cids:
                continue
            if not msgs_json:
                continue
            try:
                msgs = json.loads(msgs_json)
            except Exception:
                continue

            for m in msgs:
                if not isinstance(m, dict):
                    continue
                role = str(m.get("role", "user")).lower()
                txt = str(m.get("content", "")).strip()
                if not txt or len(txt) < 3 or txt.startswith("Error:"):
                    continue
                ts = str(m.get("timestamp") or started_at or datetime.now().isoformat())
                items_to_embed.append((cid, role, txt, ts))
                texts_to_embed.append(txt[:300])

        if not texts_to_embed:
            cnt = conn.execute("SELECT COUNT(*) FROM conversation_vectors").fetchone()[0]
            print(f"✅ All conversations already vectorized. Total vectors: {cnt}")
            return

        print(f"⚡ Vectorizing {len(texts_to_embed)} historical turns across conversations...")
        batch_size = 64
        total_inserted = 0

        for i in range(0, len(texts_to_embed), batch_size):
            b_texts = texts_to_embed[i:i + batch_size]
            b_items = items_to_embed[i:i + batch_size]
            vecs = encode_batch(b_texts, normalize=True)
            if vecs is None:
                continue

            insert_rows = []
            for j, (cid, role, txt, ts) in enumerate(b_items):
                blob = vecs[j].astype(np.float16).tobytes()
                insert_rows.append((cid, role, txt, blob, ts))

            conn.executemany(
                "INSERT INTO conversation_vectors (conversation_id, speaker, text, embedding, created_at) VALUES (?, ?, ?, ?, ?)",
                insert_rows
            )
            total_inserted += len(insert_rows)
            print(f"  Inserted {total_inserted}/{len(texts_to_embed)} vectors...")

        conn.commit()
        total_in_db = conn.execute("SELECT COUNT(*) FROM conversation_vectors").fetchone()[0]
        min_date, max_date = conn.execute("SELECT MIN(created_at), MAX(created_at) FROM conversation_vectors").fetchone()
        print(f"✅ Sync complete! Total vectors in database: {total_in_db}")
        print(f"📅 Vectorized date span: {str(min_date)[:10]} to {str(max_date)[:10]}")


if __name__ == "__main__":
    sync_vectors()
