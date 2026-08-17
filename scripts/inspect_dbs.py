import sqlite3
import os

dbs = ['data/app_usage.db', 'data/chat_history.db', 'data/memory.db', 'data/personal_knowledge.db']

for db_path in dbs:
    if not os.path.exists(db_path):
        print(f"Skipping {db_path} (not found)")
        continue
        
    print(f"\n--- {db_path} ---")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables: {[t[0] for t in tables]}")
        
        # Sample data from first table if exists
        for table in tables:
            table_name = table[0]
            print(f"  Table: {table_name}")
            try:
                # Get column names
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                print(f"    Columns: {columns}")
                
                # Get usage count or sample
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"    Row count: {count}")
                
                if count > 0:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                    rows = cursor.fetchall()
                    print(f"    Sample: {rows}")
            except Exception as e:
                print(f"    Error reading table: {e}")
                
        conn.close()
    except Exception as e:
        print(f"Error accessing database: {e}")
