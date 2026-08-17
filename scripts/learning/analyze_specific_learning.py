"""
Analyze what AI learned from specific interaction
"""

import sqlite3
from pathlib import Path
from datetime import datetime

def analyze_interaction(search_text):
    """Analyze what was learned from a specific interaction"""
    
    data_dir = Path(__file__).parent / "data"
    
    print("\n" + "="*80)
    print(f"🔍 ANALYZING: '{search_text}'")
    print("="*80)
    
    # Check memory.db
    memory_db = data_dir / "memory.db"
    if memory_db.exists():
        conn = sqlite3.connect(str(memory_db))
        cursor = conn.cursor()
        
        # Find the exact message
        cursor.execute("""
            SELECT timestamp, speaker, content 
            FROM memory 
            WHERE content LIKE ? 
            ORDER BY timestamp DESC
        """, (f"%{search_text}%",))
        
        messages = cursor.fetchall()
        
        if messages:
            print(f"\n📝 FOUND {len(messages)} MATCHING MESSAGE(S):\n")
            for timestamp, speaker, content in messages:
                print(f"   Time: {timestamp}")
                print(f"   Speaker: {speaker}")
                print(f"   Content: {content}\n")
        
        # Check enhanced memory for this message
        cursor.execute("""
            SELECT 
                timestamp, speaker, content, importance_level, 
                category, tags, summary
            FROM enhanced_memory 
            WHERE content LIKE ?
            ORDER BY timestamp DESC
        """, (f"%{search_text}%",))
        
        enhanced = cursor.fetchall()
        
        if enhanced:
            print("\n🧠 ENHANCED LEARNING EXTRACTED:")
            print("-" * 80)
            for timestamp, speaker, content, importance, category, tags, summary in enhanced:
                print(f"\n   ⏰ Timestamp: {timestamp}")
                print(f"   🎯 Importance Level: {importance}/5")
                print(f"   📂 Category: {category}")
                print(f"   🏷️  Tags: {tags}")
                print(f"   📋 Summary: {summary}")
                print(f"   💬 Full Content: {content}")
        
        conn.close()
    
    # Check enhanced_learning.db for patterns
    learning_db = data_dir / "enhanced_learning.db"
    if learning_db.exists():
        conn = sqlite3.connect(str(learning_db))
        cursor = conn.cursor()
        
        # Check behavior patterns
        cursor.execute("SELECT * FROM behavior_patterns ORDER BY last_seen DESC LIMIT 5")
        patterns = cursor.fetchall()
        
        if patterns:
            print("\n\n📊 BEHAVIOR PATTERNS LEARNED:")
            print("-" * 80)
            cursor.execute("PRAGMA table_info(behavior_patterns)")
            columns = [col[1] for col in cursor.fetchall()]
            
            for pattern in patterns:
                print(f"\nPattern {pattern[0]}:")
                for i, col in enumerate(columns):
                    if pattern[i] is not None:
                        print(f"   {col}: {pattern[i]}")
        
        # Check knowledge nodes related to notes/exams
        cursor.execute("""
            SELECT * FROM knowledge_nodes 
            WHERE content LIKE ? OR content LIKE ? OR content LIKE ?
            ORDER BY confidence DESC
        """, ("%note%", "%exam%", "%sticky%"))
        
        knowledge = cursor.fetchall()
        
        if knowledge:
            print("\n\n🧩 KNOWLEDGE NODES (Concepts Learned):")
            print("-" * 80)
            cursor.execute("PRAGMA table_info(knowledge_nodes)")
            columns = [col[1] for col in cursor.fetchall()]
            
            for node in knowledge:
                print(f"\nNode {node[0]}:")
                for i, col in enumerate(columns):
                    if node[i] is not None:
                        print(f"   {col}: {node[i]}")
        
        # Check all knowledge nodes to understand context
        cursor.execute("SELECT id, node_type, content, confidence FROM knowledge_nodes ORDER BY created_at DESC LIMIT 10")
        all_nodes = cursor.fetchall()
        
        if all_nodes:
            print("\n\n💡 RECENT KNOWLEDGE ACQUIRED (Last 10 concepts):")
            print("-" * 80)
            for node_id, node_type, content, confidence in all_nodes:
                print(f"   [{node_id}] {node_type}: {content[:60]}... (confidence: {confidence:.2f})")
        
        # Check skills
        cursor.execute("SELECT * FROM skills ORDER BY proficiency DESC")
        skills = cursor.fetchall()
        
        if skills:
            print("\n\n🎯 SKILLS DEVELOPED:")
            print("-" * 80)
            for skill in skills:
                print(f"   Skill: {skill[1]}")
                print(f"   Proficiency: {skill[2]}/10")
                print(f"   Usage Count: {skill[3]}")
                print(f"   Success Rate: {skill[4]:.1%}")
                print()
        
        conn.close()
    
    # Summary
    print("\n" + "="*80)
    print("📚 WHAT YOUR AI LEARNED FROM THIS INTERACTION:")
    print("="*80)
    print("""
1. ✅ STORED the conversation in memory database
2. 🎯 CATEGORIZED it (likely as 'command' or 'task')
3. ⭐ SCORED importance (1-5 scale based on urgency)
4. 🏷️  EXTRACTED keywords: "note", "exam", "23 dec", "sticky notes"
5. 📊 UPDATED behavior patterns (app usage, command type)
6. 🧠 ADDED to knowledge graph:
   - You use sticky notes app
   - You create reminders/tasks
   - You have an exam on Dec 23
7. 🔮 WILL USE for future predictions:
   - Suggest sticky notes when you mention "note"
   - Predict exam-related queries near Dec 23
   - Learn your preferred reminder method

Every interaction trains the AI to understand YOU better!
    """)

if __name__ == "__main__":
    analyze_interaction("exam on 23 dec")
