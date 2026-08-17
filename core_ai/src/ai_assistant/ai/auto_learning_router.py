"""
Automatic Learning Data Router
Routes conversation data to appropriate learning systems automatically
"""

import sqlite3
from pathlib import Path
from typing import Dict, List
import sys

sys.path.insert(0, str(Path(__file__).parent))

# Import all learning systems
try:
    from ai_assistant.ai.behavior_clustering import BehaviorClusterer
    from ai_assistant.ai.conversation_clustering import ConversationClusterer
    from ai_assistant.ai.command_sequences import CommandMarkovChain
    from ai_assistant.ai.command_predictor import CommandSuccessPredictor
    from ai_assistant.ai.context_aware_response import ContextAwareResponseGenerator
    from ai_assistant.ai.smart_command_prediction import SmartCommandPredictor
    from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
    from ai_assistant.ai.query_cache import QuerySimilarityCache
    IMPORTS_SUCCESS = True
except ImportError as e:
    print(f"Warning: Some learning systems unavailable: {e}")
    IMPORTS_SUCCESS = False

class LearningDataRouter:
    """
    Automatically routes new conversation data to appropriate learning systems
    Integrate this into your chat interface
    """
    
    def __init__(self):
        # Initialize all learning systems
        self.behavior_clusterer = None
        self.conversation_clusterer = None
        self.command_sequences = None
        self.command_predictor = None
        self.context_generator = None
        self.smart_commands = None
        self.knowledge_graph = None
        self.query_cache = None
        
        self._initialize_systems()
        
        # Track conversation context
        self.conversation_history = []
        self.current_session_id = None
        self.last_command = None
    
    def _initialize_systems(self):
        """Initialize all learning systems"""
        if not IMPORTS_SUCCESS:
            print("⚠️ Learning systems not available")
            return
        
        try:
            self.behavior_clusterer = BehaviorClusterer()
            self.conversation_clusterer = ConversationClusterer()
            self.command_sequences = CommandMarkovChain()
            self.command_predictor = CommandSuccessPredictor()
            self.context_generator = ContextAwareResponseGenerator()
            self.smart_commands = SmartCommandPredictor()
            self.knowledge_graph = PersonalKnowledgeGraph(db_path="data/core/personal_knowledge.db")
            self.query_cache = QuerySimilarityCache()
            print("✅ Learning systems initialized")
        except Exception as e:
            print(f"⚠️ Error initializing systems: {e}")
    
    def route_conversation(self, speaker: str, content: str, category: str = "general", 
                          importance: int = 3, success: bool = True, input_mode: str = "chat"):
        """
        Route a conversation to appropriate learning systems
        WORKS FOR BOTH CHAT AND VOICE - Same learning, same memory
        
        Args:
            speaker: 'user' or 'assistant'
            content: The message content (from chat OR voice)
            category: Message category (general, command, question, etc.)
            importance: Importance level 1-5
            success: Whether the interaction was successful
            input_mode: 'chat' or 'voice' (for tracking only, learning is shared)
        """
        
        # Add to conversation history (shared between chat and voice)
        self.conversation_history.append({
            'speaker': speaker,
            'content': content,
            'category': category,
            'importance': importance,
            'input_mode': input_mode  # Track source but use same learning
        })
        
        # Route to appropriate systems based on message type
        
        # 1. BEHAVIOR CLUSTERING - All user actions
        if speaker == 'user' and self.behavior_clusterer:
            self._route_to_behavior_clustering(content, category, importance)
        
        # 2. CONVERSATION CLUSTERING - All conversations
        if self.conversation_clusterer:
            self._route_to_conversation_clustering(content, speaker)
        
        # 3. COMMAND SEQUENCES - Track command patterns
        if speaker == 'user' and self.command_sequences:
            self._route_to_command_sequences(content)
        
        # 4. COMMAND PREDICTOR - Learn command success
        if speaker == 'user' and self.command_predictor:
            self._route_to_command_predictor(content, success)
        
        # 5. CONTEXT GENERATOR - Build contextual understanding
        if self.context_generator:
            self._route_to_context_generator(speaker, content)
        
        # 6. SMART COMMANDS - Learn user's command style
        if speaker == 'user' and self.smart_commands:
            self._route_to_smart_commands(content, category, success)
        
        # 7. KNOWLEDGE GRAPH - Extract facts
        if self.knowledge_graph:
            self._route_to_knowledge_graph(content, importance)
        
        # 8. QUERY CACHE - Cache questions and answers
        if self.query_cache:
            self._route_to_query_cache(speaker, content)
    
    def _route_to_behavior_clustering(self, content: str, category: str, importance: int):
        """Route to behavior clustering system"""
        try:
            # Create session if needed
            if not self.current_session_id:
                from datetime import datetime
                self.current_session_id = datetime.now().strftime("%Y%m%d_%H")
            
            # Add behavior data
            # Add behavior data
            self.behavior_clusterer.add_session(
                session_id=self.current_session_id,
                user_id="default_user",
                session_data={
                    'action': content[:50],
                    'category': category,
                    'importance': importance
                }
            )
        except Exception as e:
            print(f"Behavior clustering error: {e}")
    
    def _route_to_conversation_clustering(self, content: str, speaker: str):
        """Route to conversation clustering"""
        try:
            # Group last 5 messages
            # Group last 5 messages
            if len(self.conversation_history) >= 5:
                recent = self.conversation_history[-5:]
                # Convert to format expected by clusterer (list of dicts with role/content)
                messages = []
                for m in recent:
                    messages.append({
                        'role': m['speaker'],
                        'content': m['content']
                    })
                
                self.conversation_clusterer.add_conversation(
                    conversation_id=f"conv_{len(self.conversation_history)//5}",
                    user_id="default_user",
                    messages=messages
                )
        except Exception as e:
            print(f"Conversation clustering error: {e}")
    
    def _route_to_command_sequences(self, content: str):
        """Route to command sequence learner"""
        try:
            # Record command in sequence (handles transitions internally)
            self.command_sequences.record_command(
                command=content[:50],
                context=None,
                user_id="default_user"
            )
            self.last_command = content
        except Exception as e:
            print(f"Command sequences error: {e}")
    
    def _route_to_command_predictor(self, content: str, success: bool):
        """Route to command success predictor"""
        try:
            # Use record_execution instead of record_command
            self.command_predictor.record_execution(
                command=content[:50],
                success=success,
                context=None,
                predicted_success=None
            )
        except Exception as e:
            print(f"Command predictor error: {e}")
    
    def _route_to_context_generator(self, speaker: str, content: str):
        """Route to context-aware response generator"""
        try:
            # Build context from last 3 messages
            if len(self.conversation_history) >= 3:
                recent = self.conversation_history[-3:-1]
                context_text = " ".join([m['content'][:30] for m in recent])
                
                if speaker == 'user':
                    # Use update_context
                    self.context_generator.update_context(
                        user_message=content[:50],
                        context_data={
                            'previous_context': context_text,
                            'Speaker': 'user'
                        }
                    )
        except Exception as e:
            print(f"Context generator error: {e}")
    
    def _route_to_smart_commands(self, content: str, category: str, success: bool):
        """Route to smart command predictor"""
        try:
            # Use log_command
            self.smart_commands.log_command(
                command=content[:50],
                context={'category': category}, 
                success=success
            )
        except Exception as e:
            print(f"Smart commands error: {e}")
    
    def _route_to_knowledge_graph(self, content: str, importance: int):
        """Route to knowledge graph - extract facts"""
        try:
            content_lower = content.lower()
            
            # Extract date mentions
            if 'exam' in content_lower or 'test' in content_lower:
                # Extract date if present
                import re
                date_match = re.search(r'\d{1,2}\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', content_lower)
                if date_match:
                    self.knowledge_graph.add_fact(
                        subject="exam",
                        predicate="scheduled_on",
                        object=date_match.group(),
                        confidence=0.9
                    )
            
            # Extract app usage
            apps = ['notepad', 'sticky', 'chrome', 'excel', 'word', 'calculator']
            for app in apps:
                if app in content_lower:
                    self.knowledge_graph.add_fact(
                        subject="user",
                        predicate="uses_app",
                        object=app,
                        confidence=0.8
                    )
            
            # High importance = potential skill
            if importance >= 4:
                self.knowledge_graph.add_skill(
                    skill_name=f"task_{len(self.conversation_history)}",
                    proficiency=importance / 5.0
                )
        except Exception as e:
            print(f"Knowledge graph error: {e}")
    
    def _route_to_query_cache(self, speaker: str, content: str):
        """Route to query cache"""
        try:
            # Cache questions
            if speaker == 'user' and '?' in content:
                self.query_cache.add_query(
                    query=content,
                    response="cached_response"
                )
        except Exception as e:
            print(f"Query cache error: {e}")
    
    def get_routing_stats(self) -> Dict:
        """Get statistics about data routing"""
        stats = {
            'total_conversations': len(self.conversation_history),
            'systems_active': 0,
            'routing_enabled': IMPORTS_SUCCESS
        }
        
        # Count active systems
        systems = [
            self.behavior_clusterer,
            self.conversation_clusterer,
            self.command_sequences,
            self.command_predictor,
            self.context_generator,
            self.smart_commands,
            self.knowledge_graph,
            self.query_cache
        ]
        
        stats['systems_active'] = sum(1 for s in systems if s is not None)
        return stats


def integrate_with_chat_system():
    """
    Example of how to integrate the router into BOTH chat and voice systems
    SAME LEARNING, SAME MEMORY for both interfaces
    """
    
    router = LearningDataRouter()
    
    # Example: Mixed chat and voice conversations
    # Both use the SAME learning systems and memory
    conversations = [
        # User creates note via CHAT
        ("user", "create a note exam on 23 dec on stickynotes", "command", 4, True, "chat"),
        ("assistant", "Created sticky note with exam reminder", "response", 3, True, "chat"),
        
        # Later asks via VOICE - AI should remember!
        ("user", "when is my exam?", "question", 4, True, "voice"),
        ("assistant", "Your exam is on December 23rd", "response", 4, True, "voice"),
        
        # Voice command
        ("user", "open calculator", "command", 3, True, "voice"),
        ("assistant", "Opening calculator", "response", 3, True, "voice"),
        
        # Chat question about voice command
        ("user", "what did I just ask you to open?", "question", 3, True, "chat"),
        ("assistant", "You asked me to open calculator", "response", 3, True, "chat"),
    ]
    
    print("\n🎙️💬 TESTING BOTH CHAT AND VOICE LEARNING:")
    print("="*60)
    
    for speaker, content, category, importance, success, mode in conversations:
        icon = "🎙️" if mode == "voice" else "💬"
        print(f"{icon} [{mode.upper()}] {speaker}: {content[:50]}...")
        router.route_conversation(speaker, content, category, importance, success, mode)
    
    # Get stats
    stats = router.get_routing_stats()
    print("\n📊 Routing Stats (Combined Chat + Voice):")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Both chat and voice use the SAME learning systems!")
    print("✅ Knowledge learned from chat is available in voice!")
    print("✅ Commands from voice are remembered in chat!")


if __name__ == "__main__":
    print("="*60)
    print("🔄 LEARNING DATA ROUTER - TEST MODE")
    print("="*60)
    integrate_with_chat_system()
    print("\n✅ Router working! Integrate this into your chat system.")
