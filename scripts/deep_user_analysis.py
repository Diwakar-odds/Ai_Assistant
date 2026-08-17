import sqlite3
import os
import json
from datetime import datetime
from collections import Counter
import re

def get_db_connection(db_name):
    path = f"data/{db_name}"
    if os.path.exists(path):
        return sqlite3.connect(path)
    return None

def analyze_personal_knowledge():
    print("\n=== PERSONAL PROFILE (Structured) ===")
    conn = get_db_connection("personal_knowledge.db")
    if not conn:
        print("No personal knowledge database found.")
        return

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT content, node_type, metadata FROM knowledge_nodes WHERE node_type IN ('person', 'role', 'topic', 'skill', 'goal')")
        nodes = cursor.fetchall()
        
        user_node = None
        for content, ntype, meta in nodes:
            if ntype == 'person':
                try:
                    m = json.loads(meta)
                    if m.get('is_primary_user'):
                        user_node = (content, m)
                        break
                except: pass
        
        if user_node:
            name, meta = user_node
            print(f"Name: {name}")
            print(f"Role: {meta.get('role', 'Unknown')}")
            print(f"Location: {meta.get('location', 'Unknown')}")
            print(f"Communication Style: {meta.get('communication_style', 'Unknown')}")
            print(f"Work Pattern: {meta.get('work_pattern', 'Unknown')}")
            
            if 'skills' in meta:
                print(f"Skills: {', '.join(meta['skills'])}")
            if 'interests' in meta:
                print(f"Interests: {', '.join(meta['interests'])}")
            if 'goals' in meta:
                print(f"Goals: {', '.join(meta['goals'])}")
        else:
            print("No primary user profile found.")
            
    except Exception as e:
        print(f"Error reading personal knowledge: {e}")
    finally:
        conn.close()

def analyze_opinions_and_thoughts():
    print("\n=== OPINIONS & THOUGHTS (From Chat History) ===")
    # Check both chat_history.db and conversation_ai.db as they seem to exist
    dbs = ['chat_history.db', 'conversation_ai.db']
    
    opinions = []
    
    start_phrases = ["i think", "i believe", "i feel", "in my opinion", "i like", "i love", "i hate", "i dislike", "i prefer", "i want"]
    
    for db_name in dbs:
        conn = get_db_connection(db_name)
        if not conn: continue
        
        try:
            cursor = conn.cursor()
            # Try to find message tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [t[0] for t in cursor.fetchall()]
            
            messages = []
            if 'messages' in tables:
                # Assuming standard schema id, role, content...
                try:
                    cursor.execute("SELECT content FROM messages WHERE role='user'")
                    messages = [r[0] for r in cursor.fetchall()]
                except:
                    # Try looking for a sender column
                    try:
                        cursor.execute("SELECT content FROM messages WHERE sender='user'")
                        messages = [r[0] for r in cursor.fetchall()]
                    except: pass
            
            elif 'conversations' in tables:
                # conversation_ai.db stores messages as JSON blob usually
                cursor.execute("SELECT messages FROM conversations")
                rows = cursor.fetchall()
                for r in rows:
                    try:
                        msgs = json.loads(r[0])
                        for m in msgs:
                            if m.get('role') == 'user' or m.get('sender') == 'user':
                                messages.append(m.get('content', ''))
                    except: pass

            # Analyze messages for opinions
            for msg in messages:
                if not msg: continue
                msg_lower = msg.lower()
                for phrase in start_phrases:
                    if phrase in msg_lower:
                        # Extract the sentence containing the phrase
                        sentences = re.split(r'[.!?]+', msg)
                        for s in sentences:
                            if phrase in s.lower():
                                opinions.append(s.strip())
        except Exception as e:
            # print(f"Error in {db_name}: {e}")
            pass
        finally:
            conn.close()
            
    if opinions:
        # Deduplicate and show top ones
        unique_opinions = list(set(opinions))
        print(f"Found {len(unique_opinions)} potential opinion statements. Here are some:")
        for op in unique_opinions[:10]:
            print(f"  - \"{op}\"")
    else:
        print("No strong opinions found in conversation history yet.")

def analyze_behavior():
    print("\n=== BEHAVIORAL PATTERNS ===")
    
    # 1. App Usage
    conn = get_db_connection("app_usage.db")
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='app_usage'")
            if cursor.fetchone():
                print("Top Used Applications:")
                cursor.execute("SELECT app_name, duration_seconds FROM app_usage ORDER BY duration_seconds DESC LIMIT 5")
                for app, duration in cursor.fetchall():
                    minutes = duration // 60
                    print(f"  - {app}: {minutes} minutes")
        except: pass
        finally:
            conn.close()

    # 2. Activity Times (Inferred from chat logs if available)
    # Skipping detailed histogram for now, just checking connection
    
    # 3. Learning System Patterns
    conn = get_db_connection("enhanced_learning.db")
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='behavior_patterns'")
            if cursor.fetchone():
                print("\nLearned Routine Patterns:")
                cursor.execute("SELECT context, action, frequency, time_of_day FROM behavior_patterns ORDER BY frequency DESC LIMIT 5")
                for ctx, action, freq, time in cursor.fetchall():
                    print(f"  - Action '{action}' (Freq: {freq})")
        except: pass
        finally:
            conn.close()

def analyze_memories():
    print("\n=== EXTRACTED MEMORIES ===")
    conn = get_db_connection("memory.db")
    if not conn: return
    
    try:
        cursor = conn.cursor()
        # smart_memory_retrieval.py referenced 'enhanced_memory' table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='enhanced_memory'")
        if cursor.fetchone():
            cursor.execute("SELECT content, importance_level, timestamp FROM enhanced_memory ORDER BY importance_level DESC LIMIT 10")
            rows = cursor.fetchall()
            if rows:
                for content, imp, time in rows:
                    print(f"  - [{time}] (Imp: {imp}) {content}")
            else:
                print("No specific long-term memories stored yet.")
    except Exception as e:
        print(f"Error reading memory: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    analyze_personal_knowledge()
    analyze_opinions_and_thoughts()
    analyze_behavior()
    analyze_memories()
