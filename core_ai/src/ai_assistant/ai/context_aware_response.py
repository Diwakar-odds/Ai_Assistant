"""
Context-Aware Response Generation (Application)
Intelligent context-aware response generation
"""

import numpy as np
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class ContextAwareResponseGenerator:
    """
    Application-level context-aware response generation
    Generates intelligent responses based on conversation context
    """
    
    def __init__(self, db_path: str = "data/context/context_aware_responses.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        self.conversation_history = deque(maxlen=50)
        self.context_stack = []
        self.user_preferences = {}
        self.response_templates = self._load_templates()
        
        logger.info("Context-Aware Response Generator initialized")
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TEXT,
                    user_message TEXT,
                    bot_response TEXT,
                    context_data TEXT,
                    user_feedback INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS response_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_name TEXT,
                    pattern TEXT,
                    response_template TEXT,
                    context_requirements TEXT,
                    usage_count INTEGER,
                    avg_rating REAL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS context_state (
                    session_id TEXT PRIMARY KEY,
                    current_context TEXT,
                    context_stack TEXT,
                    last_updated TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    preferences TEXT,
                    conversation_style TEXT,
                    last_updated TEXT
                )
            """)
    
    def _load_templates(self) -> Dict:
        """Load response templates"""
        templates = {
            'greeting': {
                'patterns': ['hello', 'hi', 'hey'],
                'responses': [
                    "Hello! How can I help you today?",
                    "Hi there! What can I do for you?",
                    "Hey! What would you like help with?"
                ]
            },
            'help_request': {
                'patterns': ['help', 'assist', 'guide'],
                'responses': [
                    "I'd be happy to help! What do you need assistance with?",
                    "Sure, I can guide you. What would you like to do?"
                ]
            },
            'command_execution': {
                'patterns': ['open', 'close', 'start', 'stop'],
                'responses': [
                    "I'll {action} {target} for you.",
                    "Opening {target} now.",
                    "Let me {action} that for you."
                ]
            }
        }
        
        return templates
    
    def update_context(self, user_message: str, context_data: Dict):
        """Update conversation context"""
        self.conversation_history.append({
            'timestamp': datetime.now(),
            'user_message': user_message,
            'context': context_data
        })
        
        # Manage context stack
        if 'topic_shift' in context_data:
            self.context_stack.append(context_data['previous_topic'])
        
        # Keep stack manageable
        if len(self.context_stack) > 5:
            self.context_stack.pop(0)
    
    def generate_response(self,
                         user_message: str,
                         context: Optional[Dict] = None) -> Tuple[str, Dict]:
        """Generate context-aware response"""
        context = context or {}
        
        # Analyze user message
        message_lower = user_message.lower()
        
        # Extract intent
        intent = self._extract_intent(message_lower)
        
        # Get relevant context
        conversation_context = self._get_conversation_context()
        
        # Merge contexts
        full_context = {
            **context,
            **conversation_context,
            'intent': intent,
            'history_length': len(self.conversation_history)
        }
        
        # Generate response
        response = self._generate_contextual_response(
            user_message,
            intent,
            full_context
        )
        
        # Log conversation
        self._log_conversation(user_message, response, full_context)
        
        return response, full_context
    
    def _extract_intent(self, message: str) -> str:
        """Extract user intent from message"""
        # Simple keyword-based intent detection
        if any(word in message for word in ['hello', 'hi', 'hey']):
            return 'greeting'
        elif any(word in message for word in ['help', 'how', 'what']):
            return 'help_request'
        elif any(word in message for word in ['open', 'launch', 'start']):
            return 'command_execution'
        elif any(word in message for word in ['thank', 'thanks']):
            return 'gratitude'
        else:
            return 'general_query'
    
    def _get_conversation_context(self) -> Dict:
        """Get current conversation context"""
        if not self.conversation_history:
            return {}
        
        recent = list(self.conversation_history)[-5:]
        
        # Extract topics from recent messages
        topics = []
        for entry in recent:
            if 'topic' in entry.get('context', {}):
                topics.append(entry['context']['topic'])
        
        # Determine current mood/tone
        tone = 'neutral'
        if len(recent) > 2:
            if all('?' in entry['user_message'] for entry in recent[-3:]):
                tone = 'curious'
        
        return {
            'recent_topics': topics,
            'tone': tone,
            'conversation_length': len(self.conversation_history),
            'last_intent': recent[-1].get('context', {}).get('intent') if recent else None
        }
    
    def _generate_contextual_response(self,
                                     user_message: str,
                                     intent: str,
                                     context: Dict) -> str:
        """Generate response with context awareness"""
        
        # Check for template match
        if intent in self.response_templates:
            template_data = self.response_templates[intent]
            
            # Context-based template selection
            if context.get('conversation_length', 0) > 5:
                # Longer conversation - be more casual
                responses = template_data['responses']
            else:
                # New conversation - be more formal
                responses = template_data['responses']
            
            response = np.random.choice(responses)
            
            # Fill in placeholders
            if '{action}' in response and 'action' in context:
                response = response.replace('{action}', context['action'])
            if '{target}' in response and 'target' in context:
                response = response.replace('{target}', context['target'])
            
            return response
        
        # Context-aware follow-up
        if context.get('last_intent') == 'help_request':
            return f"Regarding your previous question about {context.get('recent_topics', ['that'])[-1]}, I can provide more details if needed. What would you like to know?"
        
        # Default response
        return "I understand. How can I assist you with that?"
    
    def _log_conversation(self, user_message: str, response: str, context: Dict):
        """Log conversation to database"""
        session_id = context.get('session_id', 'default')
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO conversations 
                (session_id, timestamp, user_message, bot_response, context_data)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id,
                datetime.now().isoformat(),
                user_message,
                response,
                json.dumps(context)
            ))
    
    def learn_from_feedback(self, response_id: int, feedback: int):
        """Learn from user feedback on responses"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE conversations
                SET user_feedback = ?
                WHERE id = ?
            """, (feedback, response_id))
        
        # Analyze patterns in positive/negative feedback
        self._analyze_feedback_patterns()
    
    def _analyze_feedback_patterns(self):
        """Analyze patterns in user feedback"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get responses with positive feedback
            cursor.execute("""
                SELECT context_data, COUNT(*)
                FROM conversations
                WHERE user_feedback > 0
                GROUP BY context_data
                LIMIT 10
            """)
            
            positive_patterns = cursor.fetchall()
            
            # Update response templates based on patterns
            # (Simplified - would need more sophisticated analysis)
            logger.info(f"Analyzed {len(positive_patterns)} positive feedback patterns")
    
    def get_personalization_suggestions(self, session_id: str) -> List[str]:
        """Get personalization suggestions based on conversation history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT context_data FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT 20
            """, (session_id,))
            
            contexts = [json.loads(row[0]) for row in cursor.fetchall()]
        
        suggestions = []
        
        # Analyze preferences
        intents = [c.get('intent') for c in contexts]
        most_common_intent = max(set(intents), key=intents.count) if intents else None
        
        if most_common_intent:
            suggestions.append(f"User frequently requests {most_common_intent} - optimize for this")
        
        return suggestions
    
    def get_stats(self) -> Dict:
        """Get statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM conversations")
            total_conversations = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM conversations WHERE user_feedback > 0")
            positive_feedback = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM conversations WHERE user_feedback < 0")
            negative_feedback = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT session_id) FROM conversations")
            unique_sessions = cursor.fetchone()[0]
        
        return {
            'total_conversations': total_conversations,
            'positive_feedback': positive_feedback,
            'negative_feedback': negative_feedback,
            'unique_sessions': unique_sessions,
            'satisfaction_rate': positive_feedback / max(positive_feedback + negative_feedback, 1),
            'current_context_depth': len(self.context_stack)
        }
