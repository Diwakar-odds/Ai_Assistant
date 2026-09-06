import sqlite3
import os

db_paths = [
    r'd:\Projects\Ai_Assistant\data\personal_knowledge.db',
    r'd:\Projects\Ai_Assistant\core_ai\src\ai_assistant\data\personal_knowledge.db',
    r'd:\Projects\Ai_Assistant\personal_knowledge.db'
]

for p in db_paths:
    if os.path.exists(p):
        print(f"Checking {p}")
        conn = sqlite3.connect(p)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = c.fetchall()
        for t in tables:
            table_name = t[0]
            rows = c.execute(f"SELECT * FROM {table_name}").fetchall()
            if rows:
                print(f"Table {table_name} has {len(rows)} rows: {rows}")
                c.execute(f"DELETE FROM {table_name}")
                print(f"Cleared {table_name}")
        conn.commit()
        conn.close()
