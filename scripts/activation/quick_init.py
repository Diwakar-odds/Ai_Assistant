#!/usr/bin/env python3
"""
Quick Learning Systems Initialization
Initializes databases and configuration without installing dependencies

Run this AFTER: pip install faiss-cpu chromadb scikit-learn google-generativeai
"""

import sys
from pathlib import Path
import sqlite3
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

print("\n" + "="*80)
print("QUICK LEARNING SYSTEMS INITIALIZATION")
print("="*80 + "\n")

# Step 1: Initialize databases
print("📂 Initializing databases...")

try:
    from ai_assistant.ai.historical_rag import HistoricalRAG
    rag = HistoricalRAG(db_path=str(project_root / 'data' / 'historical_rag.db'))
    print("✅ Historical RAG initialized")
except Exception as e:
    print(f"⚠️ Historical RAG: {e}")

try:
    from ai_assistant.ai.active_learning import ActiveLearner
    learner = ActiveLearner(db_path=str(project_root / 'data' / 'active_learning.db'))
    print("✅ Active Learning initialized")
except Exception as e:
    print(f"⚠️ Active Learning: {e}")

try:
    from ai_assistant.ai.advanced_feedback_learning import FeedbackCollector
    collector = FeedbackCollector(db_path=str(project_root / 'data' / 'feedback.db'))
    print("✅ Feedback Collector initialized")
except Exception as e:
    print(f"⚠️ Feedback Collector: {e}")

try:
    from ai_assistant.ai.behavior_clustering import BehaviorClusterer
    clusterer = BehaviorClusterer(db_path=str(project_root / 'data' / 'behavior_clustering.db'))
    print("✅ Behavior Clustering initialized")
except Exception as e:
    print(f"⚠️ Behavior Clustering: {e}")

try:
    from ai_assistant.ai.conversation_clustering import ConversationClusterer
    conv_clusterer = ConversationClusterer(db_path=str(project_root / 'data' / 'conversation_clustering.db'))
    print("✅ Conversation Clustering initialized")
except Exception as e:
    print(f"⚠️ Conversation Clustering: {e}")

try:
    from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
    kg = PersonalKnowledgeGraph(db_path=str(project_root / 'data' / 'knowledge_graph.db'))
    print("✅ Knowledge Graph initialized")
except Exception as e:
    print(f"⚠️ Knowledge Graph: {e}")

print("\n✅ INITIALIZATION COMPLETE!\n")
print("Next steps:")
print("  1. Install missing dependencies:")
print("     pip install faiss-cpu chromadb scikit-learn google-generativeai")
print("  2. Restart your assistant")
print("  3. Learning systems will activate automatically")
print()
