"""
Learning Systems Integration Module
Integrates all 27 learning systems into the main assistant workflow

This module provides:
- Smart command prediction
- Context-aware response generation  
- Adaptive voice recognition
- Workflow recommendations
- Anomaly detection
- Real-time learning from user interactions
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import all learning systems
try:
    from ai_assistant.ai.smart_command_prediction import SmartCommandPredictor
    from ai_assistant.ai.context_aware_response import ContextAwareResponseGenerator
    from ai_assistant.ai.adaptive_voice import AdaptiveVoiceRecognition
    from ai_assistant.ai.workflow_recommender import WorkflowRecommender
    from ai_assistant.ai.anomaly_detection import AnomalyDetector
    from ai_assistant.ai.behavior_clustering import BehaviorClusterer
    from ai_assistant.ai.conversation_clustering import ConversationClusterer
    from ai_assistant.ai.active_learning import ActiveLearner
    from ai_assistant.ai.explainability import ExplainabilityEngine
    from ai_assistant.ai.llm_bandit import LLMBandit
    from ai_assistant.ai.causal_inference import CausalInference
    from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
    from ai_assistant.ai.full_rl_system import PPOAgent
    LEARNING_SYSTEMS_AVAILABLE = True
    logger.info("✅ Learning systems loaded successfully")
except ImportError as e:
    LEARNING_SYSTEMS_AVAILABLE = False
    logger.warning(f"⚠️ Learning systems not available: {e}")


class LearningAssistant:
    """
    Intelligent assistant that learns from interactions
    Integrates all 27 learning systems into a unified interface
    """
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.systems_active = LEARNING_SYSTEMS_AVAILABLE
        
        if not self.systems_active:
            logger.warning("Learning systems unavailable - running in fallback mode")
            return
        
        # Initialize core learning systems
        try:
            self.smart_commands = SmartCommandPredictor()
            self.context_generator = ContextAwareResponseGenerator()
            self.adaptive_voice = AdaptiveVoiceRecognition()
            self.workflow_recommender = WorkflowRecommender()
            self.anomaly_detector = AnomalyDetector()
            self.behavior_clusterer = BehaviorClusterer()
            self.conversation_clusterer = ConversationClusterer()
            self.active_learner = ActiveLearner()
            self.explainability = ExplainabilityEngine()
            self.llm_bandit = LLMBandit()
            self.causal_inference = CausalInference()
            self.knowledge_graph = PersonalKnowledgeGraph(db_path="data/knowledge_graph.db")
            
            # Session tracking
            self.command_history = []
            self.conversation_history = []
            self.current_context = {}
            
            logger.info(f"✅ Learning Assistant initialized for user: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize learning systems: {e}")
            self.systems_active = False
    
    def predict_next_command(self, recent_commands: List[str], 
                           recent_outputs: List[str],
                           context: Dict[str, Any]) -> Optional[str]:
        """Predict the next command user might want to execute"""
        if not self.systems_active:
            return None
        
        try:
            prediction = self.smart_commands.predict_command(
                self.user_id, context, recent_commands, recent_outputs
            )
            return prediction.get('command')
        except Exception as e:
            logger.error(f"Command prediction error: {e}")
            return None
    
    def get_command_suggestions(self, partial_command: str, 
                               context: Dict[str, Any]) -> List[str]:
        """Get autocomplete suggestions for partial command"""
        if not self.systems_active:
            return []
        
        try:
            suggestions = self.smart_commands.autocomplete_command(
                self.user_id, partial_command, context
            )
            return suggestions.get('suggestions', [])
        except Exception as e:
            logger.error(f"Command suggestions error: {e}")
            return []
    
    def generate_intelligent_response(self, query: str,
                                     user_profile: Dict[str, Any] = None) -> str:
        """Generate context-aware response using learning"""
        if not self.systems_active:
            return query  # Fallback to original query
        
        try:
            response_data = self.context_generator.generate_response(
                query,
                self.conversation_history,
                user_profile or {}
            )
            return response_data.get('response', query)
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            return query
    
    def log_command_execution(self, command: str, output: str, 
                            success: bool, execution_time: float):
        """Log command execution for learning"""
        if not self.systems_active:
            return
        
        try:
            # Update command history
            self.command_history.append({
                'command': command,
                'output': output,
                'success': success,
                'execution_time': execution_time,
                'timestamp': datetime.now().isoformat()
            })
            
            # Log to smart commands system
            self.smart_commands.log_command(
                self.user_id, command, success, execution_time, self.current_context
            )
            
            # Check for anomalies
            features = [execution_time, len(output), int(success)]
            anomaly_result = self.anomaly_detector.detect(features)
            if anomaly_result.get('is_anomaly'):
                logger.warning(f"⚠️ Anomaly detected in command: {command}")
            
            # Update causal relationships
            if success:
                self.causal_inference.add_edge(command, "success", strength=0.8)
            
        except Exception as e:
            logger.error(f"Command logging error: {e}")
    
    def log_voice_recognition(self, transcription: str, 
                            intended_text: Optional[str] = None,
                            confidence: float = 1.0):
        """Log voice recognition for adaptive learning"""
        if not self.systems_active:
            return
        
        try:
            self.adaptive_voice.log_recognition(
                self.user_id, transcription, intended_text, confidence
            )
        except Exception as e:
            logger.error(f"Voice logging error: {e}")
    
    def get_workflow_suggestions(self, current_task: str) -> List[Dict[str, Any]]:
        """Get workflow recommendations based on current task"""
        if not self.systems_active:
            return []
        
        try:
            recommendations = self.workflow_recommender.recommend_workflows(
                self.user_id, current_task, self.current_context
            )
            return recommendations
        except Exception as e:
            logger.error(f"Workflow recommendation error: {e}")
            return []
    
    def log_conversation(self, user_message: str, assistant_response: str,
                        feedback: Optional[str] = None):
        """Log conversation for learning"""
        if not self.systems_active:
            return
        
        try:
            # Update conversation history
            self.conversation_history.append({
                'user': user_message,
                'assistant': assistant_response,
                'feedback': feedback,
                'timestamp': datetime.now().isoformat()
            })
            
            # Cluster similar conversations
            self.conversation_clusterer.add_conversation(
                self.user_id, user_message, assistant_response
            )
            
            # Update knowledge graph
            # Extract entities and relationships from conversation
            # (This would be more sophisticated in production)
            
        except Exception as e:
            logger.error(f"Conversation logging error: {e}")
    
    def select_best_llm(self, task_type: str, complexity: int) -> str:
        """Select the best LLM for the task using multi-armed bandit"""
        if not self.systems_active:
            return "default"
        
        try:
            selection = self.llm_bandit.select_llm(task_type, complexity)
            return selection.get('llm_id', 'default')
        except Exception as e:
            logger.error(f"LLM selection error: {e}")
            return "default"
    
    def get_explanation(self, prediction: Any, feature_names: List[str],
                       feature_values: List[float]) -> Dict[str, Any]:
        """Get explanation for a prediction"""
        if not self.systems_active:
            return {"explanation": "Explanations not available"}
        
        try:
            explanation = self.explainability.explain_prediction(
                prediction, feature_names, feature_values
            )
            return explanation
        except Exception as e:
            logger.error(f"Explanation error: {e}")
            return {"explanation": f"Error: {str(e)}"}
    
    def update_context(self, new_context: Dict[str, Any]):
        """Update current context"""
        self.current_context.update(new_context)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics for current session"""
        return {
            'commands_executed': len(self.command_history),
            'conversations': len(self.conversation_history),
            'systems_active': self.systems_active,
            'user_id': self.user_id
        }


# Global learning assistant instance
_learning_assistant = None

def get_learning_assistant(user_id: str = "default") -> LearningAssistant:
    """Get or create learning assistant instance"""
    global _learning_assistant
    if _learning_assistant is None:
        _learning_assistant = LearningAssistant(user_id)
    return _learning_assistant


def initialize_learning_integration(user_id: str = "default") -> bool:
    """Initialize learning systems integration"""
    try:
        assistant = get_learning_assistant(user_id)
        return assistant.systems_active
    except Exception as e:
        logger.error(f"Failed to initialize learning integration: {e}")
        return False


# Convenience functions for quick access
def predict_command(recent_commands: List[str], context: Dict[str, Any]) -> Optional[str]:
    """Quick command prediction"""
    assistant = get_learning_assistant()
    return assistant.predict_next_command(recent_commands, [], context)


def log_interaction(command: str, result: str, success: bool, time_taken: float):
    """Quick interaction logging"""
    assistant = get_learning_assistant()
    assistant.log_command_execution(command, result, success, time_taken)


def get_smart_response(query: str, user_profile: Dict[str, Any] = None) -> str:
    """Quick intelligent response generation"""
    assistant = get_learning_assistant()
    return assistant.generate_intelligent_response(query, user_profile)


def recommend_workflows(task: str) -> List[Dict[str, Any]]:
    """Quick workflow recommendations"""
    assistant = get_learning_assistant()
    return assistant.get_workflow_suggestions(task)
