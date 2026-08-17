#!/usr/bin/env python3
"""
Simple Database Initialization
Creates database structure without imports
"""

import sqlite3
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
data_dir = project_root / 'data'
data_dir.mkdir(exist_ok=True)

print("\n" + "="*80)
print("INITIALIZING LEARNING DATABASES")
print("="*80 + "\n")

# Initialize feedback database
print("📂 Creating feedback.db...")
conn = sqlite3.connect(str(data_dir / 'feedback.db'))
conn.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        feedback_type TEXT NOT NULL,
        prompt TEXT NOT NULL,
        response TEXT NOT NULL,
        feedback_value TEXT NOT NULL,
        context TEXT,
        user_id TEXT DEFAULT 'default',
        session_id TEXT,
        processed INTEGER DEFAULT 0
    )
""")
conn.execute("""
    CREATE TABLE IF NOT EXISTS preference_pairs (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        prompt TEXT NOT NULL,
        chosen_response TEXT NOT NULL,
        rejected_response TEXT NOT NULL,
        chosen_score REAL NOT NULL,
        rejected_score REAL NOT NULL,
        margin REAL NOT NULL,
        context TEXT
    )
""")
conn.execute("""
    CREATE TABLE IF NOT EXISTS response_metrics (
        response_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        prompt TEXT NOT NULL,
        response TEXT NOT NULL,
        helpfulness REAL,
        harmlessness REAL,
        honesty REAL,
        relevance REAL,
        user_satisfaction REAL,
        latency_ms REAL,
        overall_score REAL
    )
""")
conn.commit()
conn.close()
print("✅ Feedback database ready")

# Initialize knowledge graph database
print("📂 Creating knowledge_graph.db...")
conn = sqlite3.connect(str(data_dir / 'knowledge_graph.db'))
conn.execute("""
    CREATE TABLE IF NOT EXISTS nodes (
        node_id TEXT PRIMARY KEY,
        content TEXT NOT NULL,
        node_type TEXT NOT NULL,
        metadata TEXT,
        created_at TEXT NOT NULL,
        last_accessed TEXT NOT NULL,
        importance_score REAL DEFAULT 0.5
    )
""")
conn.execute("""
    CREATE TABLE IF NOT EXISTS edges (
        edge_id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        target_id TEXT NOT NULL,
        relationship TEXT NOT NULL,
        weight REAL DEFAULT 1.0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (source_id) REFERENCES nodes(node_id),
        FOREIGN KEY (target_id) REFERENCES nodes(node_id)
    )
""")
conn.commit()
conn.close()
print("✅ Knowledge graph database ready")

print("\n" + "="*80)
print("✅ ALL DATABASES INITIALIZED!")
print("="*80)
print("\nYour learning systems are ready to use!")
print("Just start your assistant and learning will happen automatically.\n")
