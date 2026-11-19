"""
Clean personal names, test chats, and hardcoded developer entries from all SQLite databases
"""

import sqlite3
import os

bad_terms = ["abhishek", "maurya", "bhadwa", "bdiwa", "diwakar", "anshuman", "rancho"]
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
data_dir = os.path.join(PROJECT_ROOT, "data")

total_deleted = 0

for root, dirs, files in os.walk(data_dir):
    for f in files:
        if f.endswith(".db"):
            p = os.path.join(root, f)
            try:
                conn = sqlite3.connect(p)
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [t[0] for t in cur.fetchall()]
                for t in tables:
                    try:
                        cur.execute(f"PRAGMA table_info({t})")
                        cols = [c[1] for c in cur.fetchall() if 'text' in c[2].lower() or 'char' in c[2].lower() or c[2] == '']
                        for col in cols:
                            for term in bad_terms:
                                try:
                                    cur.execute(f"DELETE FROM {t} WHERE {col} LIKE ?", (f"%{term}%",))
                                    if cur.rowcount > 0:
                                        rel = os.path.relpath(p, PROJECT_ROOT)
                                        print(f"Deleted {cur.rowcount} rows with '{term}' from {rel} [{t}.{col}]")
                                        total_deleted += cur.rowcount
                                except Exception:
                                    pass
                    except Exception:
                        pass
                conn.commit()
                # Run vacuum to remove deleted data pages
                try:
                    cur.execute("VACUUM")
                except Exception:
                    pass
                conn.close()
            except Exception:
                pass

# Truncate rag_traces.jsonl
rag_traces = os.path.join(data_dir, "rag_traces.jsonl")
if os.path.exists(rag_traces):
    with open(rag_traces, "w", encoding="utf-8") as f:
        pass
    print("Truncated data/rag_traces.jsonl")

# Clean old user_data queries/replies/modules
user_data_dir = os.path.join(data_dir, "user_data")
if os.path.exists(user_data_dir):
    for sub in ["queries", "replies", "modules"]:
        sub_path = os.path.join(user_data_dir, sub)
        if os.path.exists(sub_path):
            import shutil
            shutil.rmtree(sub_path, ignore_errors=True)
            print(f"Removed personal historical queries in {sub_path}")

print(f"\nTotal personal records wiped: {total_deleted}")
