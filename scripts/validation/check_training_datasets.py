"""
Check for training datasets for task recognition and command execution
"""
import sqlite3
import os
import json
from pathlib import Path

print("="*80)
print(" "*20 + "TRAINING DATASETS FOR TASKS & COMMANDS")
print("="*80)

# Define databases to check
databases = {
    'Command Sequences': 'data/command_sequences.db',
    'Smart Commands': 'data/smart_commands.db',
    'Intent Classifier': 'data/intent_classifier.db',
    'Historical RAG': 'data/historical_rag.db',
    'Conversation AI': 'data/conversation_ai.db',
    'Feedback Learning': 'data/feedback_learning.db',
    'Active Learning': 'data/active_learning.db',
    'Enhanced Learning': 'data/enhanced_learning.db'
}

found_datasets = []

for name, db_path in databases.items():
    full_path = f'F:/bn/assitant/{db_path}'
    if os.path.exists(full_path):
        try:
            conn = sqlite3.connect(full_path)
            cursor = conn.cursor()
            
            # Get tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if tables:
                print(f"\n{'='*80}")
                print(f"📊 {name}")
                print(f"{'='*80}")
                print(f"Database: {db_path}")
                print(f"Tables: {', '.join(tables)}\n")
                
                # Get row counts and sample data
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        
                        if count > 0:
                            print(f"  📁 {table}: {count} records")
                            
                            # Get column info
                            cursor.execute(f"PRAGMA table_info({table})")
                            columns = [col[1] for col in cursor.fetchall()]
                            print(f"     Columns: {', '.join(columns[:8])}")
                            
                            # Get sample data
                            cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                            samples = cursor.fetchall()
                            
                            if samples and len(samples) > 0:
                                print(f"     Sample data:")
                                for i, sample in enumerate(samples, 1):
                                    # Show first few fields
                                    preview = str(sample[:3])[:100]
                                    print(f"       {i}. {preview}...")
                            print()
                            
                            found_datasets.append({
                                'name': name,
                                'table': table,
                                'records': count,
                                'columns': columns
                            })
                    except Exception as e:
                        print(f"  ⚠️  Error reading {table}: {e}")
            
            conn.close()
            
        except Exception as e:
            print(f"⚠️  Could not open {name}: {e}")

# Summary
print("\n" + "="*80)
print("📈 SUMMARY OF AVAILABLE TRAINING DATA")
print("="*80)

if found_datasets:
    # Group by category
    command_datasets = [d for d in found_datasets if 'command' in d['name'].lower() or 'command' in d['table'].lower()]
    intent_datasets = [d for d in found_datasets if 'intent' in d['name'].lower() or 'intent' in d['table'].lower()]
    interaction_datasets = [d for d in found_datasets if 'interaction' in d['table'].lower() or 'rag' in d['name'].lower()]
    
    print(f"\n🎯 COMMAND & TASK RECOGNITION:")
    if command_datasets:
        for ds in command_datasets:
            print(f"  ✓ {ds['name']} - {ds['table']}: {ds['records']} examples")
    else:
        print("  ⚠️  No specific command datasets found")
    
    print(f"\n🧠 INTENT CLASSIFICATION:")
    if intent_datasets:
        for ds in intent_datasets:
            print(f"  ✓ {ds['name']} - {ds['table']}: {ds['records']} examples")
    else:
        print("  ⚠️  No intent classification datasets found")
    
    print(f"\n💬 USER INTERACTIONS:")
    if interaction_datasets:
        for ds in interaction_datasets:
            print(f"  ✓ {ds['name']} - {ds['table']}: {ds['records']} examples")
    
    total_records = sum(d['records'] for d in found_datasets)
    print(f"\n📊 Total Training Examples: {total_records:,}")
    print(f"📊 Total Datasets: {len(found_datasets)}")
    
else:
    print("\n⚠️  No training datasets found in data/ directory")

print("\n" + "="*80)
