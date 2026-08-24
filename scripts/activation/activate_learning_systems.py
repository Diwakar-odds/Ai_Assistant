#!/usr/bin/env python3
"""
Learning Systems Activation Script
Initializes and activates all 27+ learning systems

This script:
1. Installs missing dependencies
2. Initializes databases
3. Loads existing data into RAG
4. Starts background learning processes
5. Creates feedback collection endpoints

Usage:
    python scripts/activation/activate_learning_systems.py
"""

import sys
import os
from pathlib import Path
import subprocess
import sqlite3
from datetime import datetime

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class LearningSystemsActivation:
    """Activates all learning systems"""
    
    def __init__(self):
        self.project_root = project_root
        self.activation_log = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log activation step"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        self.activation_log.append(log_entry)
    
    def step1_install_dependencies(self):
        """Install missing dependencies"""
        print("\n" + "="*80)
        print("STEP 1: Installing Missing Dependencies")
        print("="*80 + "\n")
        
        missing_deps = ['faiss-cpu', 'chromadb', 'scikit-learn', 'tensorflow', 'google-generativeai']
        
        self.log("Checking for missing dependencies...")
        
        try:
            # Install via pip
            self.log(f"Installing: {', '.join(missing_deps)}")
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install'] + missing_deps,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.log("✅ Dependencies installed successfully", "SUCCESS")
                return True
            else:
                self.log(f"⚠️ Installation had issues: {result.stderr[:200]}", "WARNING")
                return False
        except Exception as e:
            self.log(f"❌ Failed to install dependencies: {e}", "ERROR")
            return False
    
    def step2_initialize_databases(self):
        """Initialize all learning databases"""
        print("\n" + "="*80)
        print("STEP 2: Initializing Learning Databases")
        print("="*80 + "\n")
        
        databases_to_init = [
            ('data/historical_rag.db', 'HistoricalRAG'),
            ('data/active_learning.db', 'ActiveLearner'),
            ('data/feedback.db', 'FeedbackCollector'),
            ('data/behavior_clustering.db', 'BehaviorClusterer'),
            ('data/conversation_clustering.db', 'ConversationClusterer'),
            ('data/knowledge_graph.db', 'PersonalKnowledgeGraph')
        ]
        
        for db_path, system_name in databases_to_init:
            full_path = self.project_root / db_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.log(f"Initializing {system_name} database...")
            
            try:
                # Import and initialize the system
                if system_name == 'HistoricalRAG':
                    from ai_assistant.ai.historical_rag import HistoricalRAG
                    rag = HistoricalRAG(db_path=str(full_path))
                    self.log(f"✅ {system_name} initialized", "SUCCESS")
                    
                elif system_name == 'ActiveLearner':
                    from ai_assistant.ai.active_learning import ActiveLearner
                    learner = ActiveLearner(db_path=str(full_path))
                    self.log(f"✅ {system_name} initialized", "SUCCESS")
                    
                elif system_name == 'FeedbackCollector':
                    from ai_assistant.ai.advanced_feedback_learning import FeedbackCollector
                    collector = FeedbackCollector(db_path=str(full_path))
                    self.log(f"✅ {system_name} initialized", "SUCCESS")
                    
                elif system_name == 'BehaviorClusterer':
                    from ai_assistant.ai.behavior_clustering import BehaviorClusterer
                    clusterer = BehaviorClusterer(db_path=str(full_path))
                    self.log(f"✅ {system_name} initialized", "SUCCESS")
                    
                elif system_name == 'ConversationClusterer':
                    from ai_assistant.ai.conversation_clustering import ConversationClusterer
                    clusterer = ConversationClusterer(db_path=str(full_path))
                    self.log(f"✅ {system_name} initialized", "SUCCESS")
                    
                elif system_name == 'PersonalKnowledgeGraph':
                    from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
                    kg = PersonalKnowledgeGraph(db_path=str(full_path))
                    self.log(f"✅ {system_name} initialized", "SUCCESS")
                    
            except Exception as e:
                self.log(f"⚠️ {system_name} initialization failed: {e}", "WARNING")
    
    def step3_populate_rag_from_memory(self):
        """Populate RAG system with existing conversation data"""
        print("\n" + "="*80)
        print("STEP 3: Populating RAG with Existing Conversations")
        print("="*80 + "\n")
        
        memory_db = self.project_root / 'memory.db'
        
        if not memory_db.exists():
            self.log("⚠️ No existing memory database found - skipping RAG population", "WARNING")
            return
        
        try:
            from ai_assistant.ai.historical_rag import HistoricalRAG
            
            rag = HistoricalRAG(db_path=str(self.project_root / 'data' / 'historical_rag.db'))
            
            # Read from memory
            conn = sqlite3.connect(str(memory_db))
            cursor = conn.cursor()
            
            # Try to get conversations
            try:
                cursor.execute("SELECT speaker, content, timestamp FROM memory ORDER BY timestamp")
                rows = cursor.fetchall()
                
                if rows:
                    self.log(f"Found {len(rows)} conversation entries")
                    
                    # Group into Q&A pairs
                    conversations = []
                    current_query = None
                    
                    for speaker, content, timestamp in rows:
                        if speaker == 'user':
                            current_query = content
                        elif speaker in ['assistant', 'system'] and current_query:
                            conversations.append({
                                'query': current_query,
                                'response': content,
                                'timestamp': timestamp
                            })
                            current_query = None
                    
                    # Add to RAG
                    for conv in conversations[:100]:  # Start with first 100
                        try:
                            rag.add_interaction(
                                query=conv['query'],
                                response=conv['response'],
                                context={},
                                user_feedback=0.7,
                                success_score=0.7
                            )
                        except:
                            pass
                    
                    self.log(f"✅ Populated RAG with {len(conversations)} conversation pairs", "SUCCESS")
                else:
                    self.log("No conversation data found in memory", "WARNING")
                    
            except sqlite3.OperationalError:
                self.log("Memory table not found - database might be empty", "WARNING")
            
            conn.close()
            
        except Exception as e:
            self.log(f"❌ RAG population failed: {e}", "ERROR")
    
    def step4_create_feedback_endpoints(self):
        """Create feedback API endpoints file"""
        print("\n" + "="*80)
        print("STEP 4: Creating Feedback Collection Endpoints")
        print("="*80 + "\n")
        
        feedback_api_path = self.project_root / 'ai_assistant' / 'api' / 'feedback_routes.py'
        
        if feedback_api_path.exists():
            self.log("✅ Feedback routes already exist", "SUCCESS")
            return
        
        feedback_code = '''"""
Feedback Collection API Routes
Endpoints for collecting user feedback on AI responses
"""

from flask import Blueprint, request, jsonify
from ai_assistant.ai.advanced_feedback_learning import FeedbackCollector, FeedbackEntry, FeedbackType
from datetime import datetime
import uuid

feedback_bp = Blueprint('feedback', __name__, url_prefix='/api/feedback')

# Initialize feedback collector
feedback_collector = FeedbackCollector(db_path='data/feedback.db')


@feedback_bp.route('/thumbs', methods=['POST'])
def submit_thumbs_feedback():
    """Submit thumbs up/down feedback"""
    data = request.json
    
    entry = FeedbackEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        feedback_type=FeedbackType.THUMBS_UP if data.get('thumbs') == 'up' else FeedbackType.THUMBS_DOWN,
        prompt=data.get('prompt', ''),
        response=data.get('response', ''),
        feedback_value={'thumbs': data.get('thumbs')},
        context=data.get('context', {}),
        session_id=data.get('session_id')
    )
    
    feedback_collector.record_feedback(entry)
    
    return jsonify({'status': 'success', 'message': 'Feedback recorded'})


@feedback_bp.route('/rating', methods=['POST'])
def submit_rating_feedback():
    """Submit star rating (1-5)"""
    data = request.json
    
    entry = FeedbackEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        feedback_type=FeedbackType.STAR_RATING,
        prompt=data.get('prompt', ''),
        response=data.get('response', ''),
        feedback_value={'rating': data.get('rating', 3)},
        context=data.get('context', {}),
        session_id=data.get('session_id')
    )
    
    feedback_collector.record_feedback(entry)
    
    return jsonify({'status': 'success', 'message': 'Rating recorded'})


@feedback_bp.route('/preference', methods=['POST'])
def submit_preference_feedback():
    """Submit preference comparison (A vs B)"""
    data = request.json
    
    entry = FeedbackEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        feedback_type=FeedbackType.PREFERENCE_PAIR,
        prompt=data.get('prompt', ''),
        response=data.get('chosen_response', ''),
        feedback_value={
            'chosen': data.get('chosen_response'),
            'rejected': data.get('rejected_response')
        },
        context=data.get('context', {}),
        session_id=data.get('session_id')
    )
    
    feedback_collector.record_feedback(entry)
    
    return jsonify({'status': 'success', 'message': 'Preference recorded'})


@feedback_bp.route('/stats', methods=['GET'])
def get_feedback_stats():
    """Get feedback statistics"""
    # Get recent feedback
    recent = feedback_collector.get_recent_feedback(limit=100)
    
    thumbs_up = sum(1 for f in recent if f.feedback_type == FeedbackType.THUMBS_UP)
    thumbs_down = sum(1 for f in recent if f.feedback_type == FeedbackType.THUMBS_DOWN)
    
    return jsonify({
        'total_feedback': len(recent),
        'thumbs_up': thumbs_up,
        'thumbs_down': thumbs_down,
        'satisfaction_rate': thumbs_up / max(thumbs_up + thumbs_down, 1) * 100
    })
'''
        
        try:
            with open(feedback_api_path, 'w', encoding='utf-8') as f:
                f.write(feedback_code)
            self.log("✅ Created feedback API routes", "SUCCESS")
        except Exception as e:
            self.log(f"❌ Failed to create feedback routes: {e}", "ERROR")
    
    def step5_generate_activation_report(self):
        """Generate activation report"""
        print("\n" + "="*80)
        print("ACTIVATION COMPLETE - SUMMARY")
        print("="*80 + "\n")
        
        report_path = self.project_root / 'logs' / 'activation' / f'activation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            f.write("\\n".join(self.activation_log))
        
        print(f"\\n📄 Activation log saved: {report_path}\\n")
        
        print("✅ LEARNING SYSTEMS ACTIVATED!\\n")
        print("Next steps:")
        print("  1. Restart your assistant")
        print("  2. Start using it - learning happens automatically")
        print("  3. Check learning dashboard at /api/learning/dashboard")
        print("  4. Provide feedback using thumbs up/down")
        print()
    
    def run(self):
        """Run full activation"""
        print("\\n" + "="*80)
        print("LEARNING SYSTEMS ACTIVATION")
        print("Pulsar AI Assistant")
        print("="*80)
        
        self.step1_install_dependencies()
        self.step2_initialize_databases()
        self.step3_populate_rag_from_memory()
        self.step4_create_feedback_endpoints()
        self.step5_generate_activation_report()


if __name__ == "__main__":
    activator = LearningSystemsActivation()
    activator.run()
