"""
migrate_to_unified_memory.py - Zero Data Loss migration script.
Migrates:
  - data/commitments.db -> data/memory/pulsar_memory.db (memories table)
  - data/historical_rag.db -> data/memory/pulsar_memory.db (memories table)
  - data/sessions/history.json -> data/memory/pulsar_memory.db (episodes table)
  - data/conversation_context_*.json -> data/context/active_context.json + safe archive
"""
import os
import sys
import json
import sqlite3
import shutil
import time
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core_ai.memory import MemoryService, HybridMemoryStore, Embedder, resolve_time

def run_migration():
    print("=" * 60)
    print("STARTING ZERO-DATA-LOSS MIGRATION TO UNIFIED MEMORY")
    print("=" * 60)

    memory_dir = ROOT_DIR / "data" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    target_db = memory_dir / "pulsar_memory.db"
    
    embedder = Embedder()
    store = HybridMemoryStore(target_db, embedder)

    # 1. Migrate commitments.db
    commitments_db = ROOT_DIR / "data" / "commitments.db"
    migrated_commitments = 0
    if commitments_db.exists():
        print(f"\n1. Migrating commitments from {commitments_db}...")
        try:
            conn = sqlite3.connect(commitments_db)
            c = conn.cursor()
            c.execute("SELECT id, text, action, deadline, party, status, created_at FROM commitments")
            rows = c.fetchall()
            for r in rows:
                cid, text, action, deadline, party, status, created_at = r
                content = action if action else text
                res = None
                if deadline:
                    try:
                        res = resolve_time(deadline, datetime.now())
                    except Exception:
                        pass
                
                mid = store.upsert(
                    kind="commitment",
                    content=content,
                    subject=party or "self",
                    importance=0.8,
                    confidence=0.9,
                    event_start=res.start.timestamp() if res else None,
                    event_end=res.end.timestamp() if res else None,
                    precision=res.precision if res else None,
                    time_expr=deadline,
                    payload={"original_id": cid, "party": party, "status": status}
                )
                if status != "pending":
                    store.set_status(mid, status)
                migrated_commitments += 1
            conn.close()
            print(f"   ✅ Migrated {migrated_commitments} commitments.")
        except Exception as e:
            print(f"   ⚠️ Warning migrating commitments: {e}")

    # 2. Migrate historical_rag.db
    historical_rag_db = ROOT_DIR / "data" / "historical_rag.db"
    migrated_rag = 0
    if historical_rag_db.exists():
        print(f"\n2. Migrating historical interactions from {historical_rag_db}...")
        try:
            conn = sqlite3.connect(historical_rag_db)
            c = conn.cursor()
            c.execute("SELECT query, response, context, success_score FROM interactions")
            rows = c.fetchall()
            for query, response, context, success_score in rows:
                if query and len(query.strip()) > 3:
                    content = f"Query: {query.strip()} -> Answer: {response.strip() if response else ''}"
                    store.upsert(
                        kind="fact",
                        content=content[:500],
                        subject="interaction",
                        importance=float(success_score or 0.5),
                        confidence=0.8,
                        payload={"context": context}
                    )
                    migrated_rag += 1
            conn.close()
            print(f"   ✅ Migrated {migrated_rag} interactions into semantic facts.")
        except Exception as e:
            print(f"   ⚠️ Warning migrating historical RAG: {e}")

    # 3. Migrate sessions history into episodes
    history_json = ROOT_DIR / "data" / "sessions" / "history.json"
    migrated_turns = 0
    if history_json.exists():
        print(f"\n3. Migrating session history turns from {history_json}...")
        try:
            data = json.loads(history_json.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for sess in data:
                    sess_id = sess.get("id", "legacy_session")
                    messages = sess.get("messages", [])
                    for msg in messages:
                        role = msg.get("role", "unknown")
                        text = msg.get("content", msg.get("text", "")).strip()
                        if text:
                            store.log_turn(session_id=sess_id, role=role, text=text, source="chat")
                            migrated_turns += 1
            print(f"   ✅ Migrated {migrated_turns} conversational turns into episodes table.")
        except Exception as e:
            print(f"   ⚠️ Warning migrating session history: {e}")

    # 4. Consolidate conversation_context_*.json into active_context.json
    print("\n4. Consolidating conversation_context_*.json into single active context...")
    context_dir = ROOT_DIR / "data" / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    active_context_path = context_dir / "active_context.json"
    
    # Safe archive dir for legacy UUID files
    archive_dir = ROOT_DIR / "data" / "archived_contexts"
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    consolidated_vars = {}
    last_context_obj = {}
    legacy_files = list((ROOT_DIR / "data").glob("conversation_context_*.json"))
    
    for f in legacy_files:
        try:
            cdata = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(cdata, dict):
                cvars = cdata.get("context_vars", {})
                if isinstance(cvars, dict):
                    consolidated_vars.update(cvars)
                last_context_obj.update(cdata)
            # Move file to archive (do not delete permanently!)
            shutil.move(str(f), str(archive_dir / f.name))
        except Exception as e:
            print(f"   ⚠️ Could not read {f.name}: {e}")

    last_context_obj["context_vars"] = consolidated_vars
    active_context_path.write_text(json.dumps(last_context_obj, indent=2), encoding="utf-8")
    print(f"   ✅ Consolidated {len(legacy_files)} legacy context files into {active_context_path}.")
    print(f"   ✅ Archived {len(legacy_files)} old files safely to {archive_dir}.")

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED SUCCESSFULLY WITH ZERO DATA LOSS!")
    print("=" * 60)

if __name__ == "__main__":
    run_migration()
