"""
Simple Integration Example
Shows how to integrate advanced learning systems into existing AI assistant
"""

from ai_assistant.ai import (
    get_feedback_engine,
    get_intent_classifier,
    get_prompt_optimizer,
    get_multimodal_engine
)
from datetime import datetime
import json


class EnhancedAssistant:
    """
    Example of AI assistant with advanced learning integrated
    """
    
    def __init__(self):
        # Initialize learning systems
        self.feedback_engine = get_feedback_engine()
        self.intent_classifier = get_intent_classifier()
        self.prompt_optimizer = get_prompt_optimizer()
        self.multimodal_engine = get_multimodal_engine()
        
        # Track pending feedback
        self.pending_responses = {}
    
    def process_message(self, message: str, user_id: str = "default", 
                       voice_features: dict = None) -> dict:
        """
        Process user message with full learning integration
        
        Args:
            message: User's text input
            user_id: User identifier
            voice_features: Optional voice data (pitch, energy, etc.)
        
        Returns:
            dict with response, response_id, intent, and metadata
        """
        
        # Step 1: Classify intent and extract entities
        intent, confidence, entities = self.intent_classifier.classify_intent(
            text=message,
            context={'time': datetime.now().strftime('%H:%M')}
        )
        
        print(f"🎯 Intent: {intent} ({confidence:.1%})")
        if entities:
            print(f"📋 Entities: {json.dumps(entities, indent=2)}")
        
        # Step 2: Predict user state from voice (if available)
        user_state = None
        if voice_features and self.multimodal_engine:
            user_state = self.multimodal_engine.predict_user_state(
                user_id=user_id,
                voice_features=voice_features
            )
            print(f"😊 Detected emotion: {user_state['emotion']}")
            print(f"📈 Engagement: {user_state['engagement_level']:.1%}")
        
        # Step 3: Get optimal prompt template
        template = self.prompt_optimizer.get_best_template(intent)
        
        if template:
            print(f"📄 Using template: {template.name} (success rate: {template.success_rate:.1%})")
        
        # Step 4: Generate response (mock for this example)
        response = self._generate_response(
            message=message,
            intent=intent,
            entities=entities,
            template=template,
            user_state=user_state
        )
        
        # Step 5: Store for feedback collection
        response_id = f"resp_{datetime.now().timestamp()}"
        self.pending_responses[response_id] = {
            'response': response,
            'intent': intent,
            'template_id': template.id if template else None,
            'context': {
                'user_id': user_id,
                'voice_features': voice_features,
                'user_state': user_state
            }
        }
        
        # Step 6: Record interaction in multi-modal system
        if self.multimodal_engine:
            self.multimodal_engine.record_interaction(
                user_id=user_id,
                voice_data=voice_features,
                text_data={'length': len(response), 'intent': intent},
                emotion=user_state['emotion'] if user_state else 'neutral',
                context=intent,
                quality=0.5  # Will be updated with actual feedback
            )
        
        return {
            'response': response,
            'response_id': response_id,
            'intent': intent,
            'confidence': confidence,
            'entities': entities,
            'emotion': user_state['emotion'] if user_state else None
        }
    
    def _generate_response(self, message, intent, entities, template, user_state):
        """
        Generate response (simplified for example)
        In real implementation, this would call your LLM
        """
        
        # Adjust response style based on emotion
        if user_state:
            if user_state['emotion'] == 'frustrated':
                style = "I understand this can be frustrating. Let me help you with that."
            elif user_state['emotion'] == 'happy':
                style = "Great! Let's make this happen!"
            else:
                style = ""
        else:
            style = ""
        
        # Mock responses based on intent
        responses = {
            'greeting': f"{style} Hello! How can I assist you today?",
            'command': f"{style} I'll execute that command for you.",
            'query': f"{style} Based on your question about '{message}', here's what I found...",
            'automation': f"{style} I'll set up that automation. Here are the steps...",
            'coding': f"{style} Here's the code solution:\n```python\n# Code here\n```",
            'file_ops': f"{style} I'll handle that file operation.",
            'conversation': f"{style} I appreciate you sharing that!",
            'system': f"{style} I'll check the system settings."
        }
        
        return responses.get(intent, f"{style} I'm processing your request about: {message}")
    
    def collect_feedback(self, response_id: str, feedback_type: str):
        """
        Collect user feedback (thumbs up/down)
        
        Args:
            response_id: ID from process_message
            feedback_type: 'thumbs_up' or 'thumbs_down'
        """
        
        if response_id not in self.pending_responses:
            print(f"⚠️  Response ID {response_id} not found")
            return
        
        data = self.pending_responses[response_id]
        
        # Record in feedback system
        if self.feedback_engine:
            self.feedback_engine.collect_feedback(
                response_id=response_id,
                feedback_type=feedback_type,
                response_text=data['response'],
                context=data['context']
            )
        
        # Update prompt optimizer
        if self.prompt_optimizer and data['template_id']:
            quality = 1.0 if feedback_type == 'thumbs_up' else 0.0
            self.prompt_optimizer.record_feedback(
                template_id=data['template_id'],
                quality_score=quality,
                feedback=feedback_type
            )
        
        print(f"✅ Feedback recorded: {feedback_type}")
    
    def compare_responses(self, prompt: str, response_a: str, response_b: str, 
                         winner: str):
        """
        Learn from response comparison
        
        Args:
            prompt: Original question/command
            response_a: First response option
            response_b: Second response option
            winner: 'a' or 'b'
        """
        
        if winner == 'a':
            chosen = response_a
            rejected = response_b
        else:
            chosen = response_b
            rejected = response_a
        
        if self.feedback_engine:
            self.feedback_engine.collect_preference_pair(
                prompt=prompt,
                chosen_response=chosen,
                rejected_response=rejected
            )
        
        print(f"✅ Preference learned: Response {winner} is better")
    
    def correct_intent(self, message: str, correct_intent: str):
        """
        Learn from intent misclassification
        
        Args:
            message: Original message
            correct_intent: What it should have been classified as
        """
        
        if self.intent_classifier:
            self.intent_classifier.correct_intent(
                text=message,
                correct_intent=correct_intent,
                context={}
            )
        
        print(f"✅ Learned: '{message}' should be classified as '{correct_intent}'")
    
    def get_insights(self, user_id: str = "default") -> dict:
        """
        Get learning insights and analytics
        """
        
        insights = {}
        
        # Feedback learning stats
        if self.feedback_engine:
            insights['feedback'] = self.feedback_engine.get_learning_stats()
        
        # Prompt optimization
        if self.prompt_optimizer:
            insights['prompts'] = self.prompt_optimizer.get_optimization_insights()
        
        # Multi-modal insights
        if self.multimodal_engine:
            insights['user_profile'] = self.multimodal_engine.get_contextual_insights(user_id)
        
        return insights


def demo():
    """
    Demonstration of the enhanced assistant
    """
    
    print("=" * 70)
    print("🤖 ENHANCED AI ASSISTANT WITH ADVANCED LEARNING")
    print("=" * 70)
    
    # Create assistant
    assistant = EnhancedAssistant()
    
    # Example 1: Process a command with voice
    print("\n" + "=" * 70)
    print("Example 1: Command with voice features")
    print("=" * 70)
    
    result = assistant.process_message(
        message="Open Chrome and search for machine learning tutorials",
        user_id="demo_user",
        voice_features={
            'pitch': 145.0,
            'energy': 0.75,
            'tempo': 115.0
        }
    )
    
    print(f"\n💬 Response: {result['response']}")
    print(f"🆔 Response ID: {result['response_id']}")
    
    # Collect positive feedback
    assistant.collect_feedback(result['response_id'], 'thumbs_up')
    
    # Example 2: Process a query
    print("\n" + "=" * 70)
    print("Example 2: Information query")
    print("=" * 70)
    
    result2 = assistant.process_message(
        message="What's the best way to learn Python?",
        user_id="demo_user"
    )
    
    print(f"\n💬 Response: {result2['response']}")
    
    # Collect negative feedback and correct
    assistant.collect_feedback(result2['response_id'], 'thumbs_down')
    
    # Example 3: Compare responses
    print("\n" + "=" * 70)
    print("Example 3: Learning from comparison")
    print("=" * 70)
    
    assistant.compare_responses(
        prompt="Explain decorators",
        response_a="Use @ symbol before function",
        response_b="A decorator is a function that modifies another function. Example: @cache...",
        winner='b'
    )
    
    # Example 4: Correct intent
    print("\n" + "=" * 70)
    print("Example 4: Learning from correction")
    print("=" * 70)
    
    assistant.correct_intent(
        message="launch notepad",
        correct_intent="automation"
    )
    
    # Example 5: Get insights
    print("\n" + "=" * 70)
    print("Example 5: Analytics & Insights")
    print("=" * 70)
    
    insights = assistant.get_insights("demo_user")
    print("\n📊 Learning Insights:")
    print(json.dumps(insights, indent=2, default=str))
    
    print("\n" + "=" * 70)
    print("✅ Demo complete! The assistant is learning from interactions.")
    print("=" * 70)


if __name__ == "__main__":
    demo()
