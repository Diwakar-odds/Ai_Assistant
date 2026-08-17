"""
AI Learning Progress Viewer
Shows how much your AI has learned from your interactions
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import os

class LearningProgressViewer:
    """View all learning data and progress from your AI assistant"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent / "data"
        self.user_data_dir = Path(__file__).parent / "user_data"
        self.logs_dir = Path(__file__).parent / "logs"
        
    def get_database_stats(self, db_path: Path) -> Dict:
        """Get statistics from a database"""
        if not db_path.exists():
            return {"status": "not created yet", "size": 0}
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            stats = {
                "database": db_path.name,
                "size_kb": db_path.stat().st_size / 1024,
                "tables": {},
                "total_records": 0
            }
            
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                stats["tables"][table_name] = count
                stats["total_records"] += count
            
            conn.close()
            return stats
        except Exception as e:
            return {"error": str(e), "size_kb": db_path.stat().st_size / 1024}
    
    def view_memory_interactions(self):
        """View conversation memory and interactions"""
        print("\n" + "="*80)
        print("💬 CONVERSATION MEMORY")
        print("="*80)
        
        memory_db = self.data_dir / "memory.db"
        if not memory_db.exists():
            print("❌ No conversation memory found yet.")
            return
        
        conn = sqlite3.connect(str(memory_db))
        cursor = conn.cursor()
        
        # Get total conversations
        cursor.execute("SELECT COUNT(*) FROM memory")
        total_messages = cursor.fetchone()[0]
        
        # Get enhanced memory stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT category) as categories,
                AVG(importance_level) as avg_importance
            FROM enhanced_memory
        """)
        enhanced_stats = cursor.fetchone()
        
        # Get recent conversations
        cursor.execute("""
            SELECT timestamp, speaker, content 
            FROM memory 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        recent = cursor.fetchall()
        
        print(f"\n📊 Total Messages Saved: {total_messages}")
        if enhanced_stats:
            print(f"📊 Enhanced Memory Records: {enhanced_stats[0]}")
            print(f"📂 Number of Categories: {enhanced_stats[1]}")
            print(f"⭐ Average Importance: {enhanced_stats[2]:.2f}/5")
        
        if recent:
            print("\n🕐 Recent Conversations:")
            for timestamp, speaker, content in recent[:3]:
                print(f"   [{timestamp}] {speaker}: {content[:60]}...")
        
        # Get knowledge base
        cursor.execute("SELECT COUNT(*) FROM knowledge_base")
        knowledge_count = cursor.fetchone()[0]
        print(f"\n🧠 Knowledge Base Facts: {knowledge_count}")
        
        conn.close()
    
    def view_learning_systems(self):
        """View all learning system databases"""
        print("\n" + "="*80)
        print("🤖 AI LEARNING SYSTEMS")
        print("="*80)
        
        learning_dbs = {
            "active_learning.db": "Active Learning (learns which questions to ask)",
            "behavior_clustering.db": "Behavior Patterns (groups similar behaviors)",
            "conversation_clustering.db": "Conversation Patterns",
            "command_sequences.db": "Command Prediction (predicts next command)",
            "command_success.db": "Success Prediction (learns what works)",
            "anomaly_detection.db": "Anomaly Detection (spots unusual patterns)",
            "causal_inference.db": "Cause & Effect Learning",
            "context_aware_responses.db": "Context Understanding",
            "adaptive_voice.db": "Voice Recognition Training",
            "smart_commands.db": "Smart Command Learning",
            "workflow_recommender.db": "Workflow Optimization",
            "meta_learning.db": "Meta-Learning (learning to learn)",
            "rl_ppo.db": "Reinforcement Learning",
            "federated_learning.db": "Distributed Learning",
            "enhanced_learning.db": "Enhanced Learning Engine",
            "personal_knowledge.db": "Personal Knowledge Graph"
        }
        
        total_learning_records = 0
        active_systems = 0
        
        for db_name, description in learning_dbs.items():
            db_path = self.data_dir / db_name
            if db_path.exists():
                stats = self.get_database_stats(db_path)
                if stats.get("total_records", 0) > 0:
                    active_systems += 1
                    total_learning_records += stats["total_records"]
                    print(f"\n✅ {description}")
                    print(f"   Database: {db_name}")
                    print(f"   Size: {stats['size_kb']:.2f} KB")
                    print(f"   Records: {stats['total_records']}")
                    if 'tables' in stats:
                        for table, count in stats['tables'].items():
                            if count > 0:
                                print(f"      - {table}: {count} entries")
        
        print(f"\n📈 Summary:")
        print(f"   Active Learning Systems: {active_systems}/{len(learning_dbs)}")
        print(f"   Total Learning Records: {total_learning_records}")
    
    def view_user_interactions(self):
        """View logged user interactions"""
        print("\n" + "="*80)
        print("👤 USER INTERACTION DATA")
        print("="*80)
        
        if not self.user_data_dir.exists():
            print("❌ No user interaction data found yet.")
            return
        
        # Count files in each category
        categories = {
            "actions": "User Actions",
            "queries": "User Queries",
            "replies": "AI Replies",
            "modules": "Module Usage"
        }
        
        for folder, description in categories.items():
            folder_path = self.user_data_dir / folder
            if folder_path.exists():
                # Look for both .txt and .json files
                txt_files = list(folder_path.glob("*.txt"))
                json_files = list(folder_path.glob("*.json"))
                all_files = txt_files + json_files
                
                total_entries = 0
                for file in all_files:
                    if file.suffix == '.json':
                        # For JSON files, count as 1 entry per file
                        total_entries += 1
                    else:
                        # For text files, count lines
                        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                            total_entries += len(f.readlines())
                
                print(f"\n📁 {description}: {len(all_files)} files, {total_entries} entries")
    
    def view_chat_history(self):
        """View chat history database"""
        print("\n" + "="*80)
        print("💭 CHAT HISTORY")
        print("="*80)
        
        chat_db = self.data_dir / "chat_history.db"
        if not chat_db.exists():
            print("❌ No chat history found yet.")
            return
        
        stats = self.get_database_stats(chat_db)
        print(f"\n📊 Database Size: {stats['size_kb']:.2f} KB")
        print(f"📊 Total Records: {stats['total_records']}")
        
        if 'tables' in stats:
            for table, count in stats['tables'].items():
                print(f"   - {table}: {count} entries")
        
        # Get sample data
        try:
            conn = sqlite3.connect(str(chat_db))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                sample = cursor.fetchone()
                if sample:
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [col[1] for col in cursor.fetchall()]
                    print(f"\n   Table '{table_name}' structure: {', '.join(columns)}")
            
            conn.close()
        except Exception as e:
            print(f"   Error reading structure: {e}")
    
    def view_learning_process_flow(self):
        """Explain how the learning process works"""
        print("\n" + "="*80)
        print("🔄 HOW YOUR AI LEARNS - COMPLETE FLOW")
        print("="*80)
        
        flow = """
┌─────────────────────────────────────────────────────────────────┐
│                    YOU INTERACT WITH AI                         │
│              (Voice, Text, Commands, Actions)                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: DATA COLLECTION                                        │
│  ────────────────────────                                       │
│  ✓ Every message saved to memory.db                             │
│  ✓ Enhanced memory extracts importance & category               │
│  ✓ User actions logged to user_data/                            │
│  ✓ Chat history stored in chat_history.db                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: DATA PROCESSING                                        │
│  ─────────────────────────                                      │
│  ✓ Conversations clustered by topic                             │
│  ✓ Behavior patterns identified                                 │
│  ✓ Command sequences analyzed                                   │
│  ✓ Context extracted and stored                                 │
│  ✓ Knowledge graph updated                                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: LEARNING SYSTEMS TRAINING                              │
│  ───────────────────────────────────                            │
│  🧠 Active Learning: Learns what questions to ask               │
│  🎯 Command Predictor: Predicts your next command               │
│  📊 Behavior Clustering: Groups similar behaviors               │
│  🔮 Anomaly Detection: Spots unusual patterns                   │
│  💡 Context Learning: Understands situation                     │
│  🗣️ Voice Adaptation: Improves speech recognition              │
│  ⚡ Workflow Optimization: Suggests efficient workflows         │
│  🔗 Causal Learning: Understands cause & effect                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: KNOWLEDGE STORAGE                                      │
│  ──────────────────────────                                     │
│  📁 Personal Knowledge Graph (facts about you)                  │
│  🧮 Learned Patterns (behavioral models)                        │
│  🎯 Success Metrics (what works for you)                        │
│  📝 Conversation Summaries (daily summaries)                    │
│  🔢 Embeddings (semantic understanding)                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: IMPROVED RESPONSES                                     │
│  ────────────────────────────                                   │
│  ✨ Personalized responses based on your style                  │
│  🎯 Predicted needs before you ask                              │
│  💬 Better conversation flow                                    │
│  🚀 Faster, more relevant answers                               │
│  🧠 Contextual understanding                                    │
└─────────────────────────────────────────────────────────────────┘

📍 DATA LOCATIONS:
   • Conversations: data/memory.db
   • Learning Models: data/*.db (27 different systems)
   • User Actions: user_data/ (actions, queries, replies)
   • Logs: logs/ (detailed activity tracking)
   • Knowledge Graph: data/personal_knowledge.db

🔒 SECURITY:
   • Encrypted database support available
   • Local storage only (no cloud)
   • You own all your data

⚡ CONTINUOUS LEARNING:
   Every interaction makes your AI smarter and more personalized!
"""
        print(flow)
    
    def generate_full_report(self):
        """Generate complete learning progress report"""
        print("\n" + "="*80)
        print("🎓 AI LEARNING PROGRESS REPORT")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Show how it works first
        self.view_learning_process_flow()
        
        # Show actual data
        self.view_memory_interactions()
        self.view_learning_systems()
        self.view_chat_history()
        self.view_user_interactions()
        
        # Summary
        print("\n" + "="*80)
        print("📈 OVERALL SUMMARY")
        print("="*80)
        
        # Calculate total storage
        total_size = 0
        if self.data_dir.exists():
            for db_file in self.data_dir.glob("*.db"):
                total_size += db_file.stat().st_size
        
        print(f"\n💾 Total Learning Data Size: {total_size / 1024 / 1024:.2f} MB")
        print(f"📁 Data Directory: {self.data_dir}")
        print(f"👤 User Data Directory: {self.user_data_dir}")
        print(f"📋 Logs Directory: {self.logs_dir}")
        
        print("\n" + "="*80)
        print("✅ Your AI is continuously learning from every interaction!")
        print("💡 Tip: The more you use it, the smarter and more personalized it becomes.")
        print("="*80 + "\n")

if __name__ == "__main__":
    viewer = LearningProgressViewer()
    viewer.generate_full_report()
