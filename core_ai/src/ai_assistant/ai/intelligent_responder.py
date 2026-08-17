"""
Intelligent Response Generator for YourDaddy Assistant

Analyzes user input for intent, mood, context and generates appropriate responses.
Provides personality-driven, context-aware conversation handling.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional
import random

class IntelligentResponder:
    """Generates context-aware, mood-sensitive responses"""
    
    def __init__(self):
        self.conversation_history = []
        
    def analyze_input(self, user_text: str) -> Dict:
        """
        Analyze user input for intent, mood, urgency, and context
        
        Returns:
            {
                'intent': str,  # greeting, question, command, complaint, etc.
                'mood': str,    # happy, frustrated, neutral, urgent, casual
                'keywords': List[str],
                'time_of_day': str,
                'urgency_level': int  # 1-5
            }
        """
        text_lower = user_text.lower().strip()
        
        # Detect intent
        intent = self._detect_intent(text_lower)
        
        # Detect mood
        mood = self._detect_mood(text_lower)
        
        # Extract keywords
        keywords = self._extract_keywords(text_lower)
        
        # Get time context
        hour = datetime.now().hour
        if 5 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        elif 17 <= hour < 22:
            time_of_day = "evening"
        else:
            time_of_day = "night"
        
        # Detect urgency
        urgency = self._detect_urgency(text_lower)
        
        return {
            'intent': intent,
            'mood': mood,
            'keywords': keywords,
            'time_of_day': time_of_day,
            'urgency_level': urgency,
            'original_text': user_text
        }
    
    def _detect_intent(self, text: str) -> str:
        """Detect primary intent from user input"""
        
        # Greetings
        greeting_patterns = [
            r'\b(hey|hi|hello|sup|yo|greetings|good morning|good evening)\b',
            r'\bdaddy\b.*\b(hey|hi|hello)\b',
            r'\b(namaste|namaskar)\b'
        ]
        
        # Questions
        question_patterns = [
            r'\b(what|when|where|why|how|who|can you|could you|will you|would you)\b',
            r'[?]$'
        ]
        
        # Commands
        command_patterns = [
            r'\b(open|close|start|stop|play|pause|search|find|get|set|turn)\b',
            r'\b(kholo|band karo|chalu|shuru)\b'
        ]
        
        # Complaints/Frustration
        complaint_patterns = [
            r'\b(not working|broken|error|issue|problem|help|stuck)\b',
            r'\b(nahi ho raha|kaam nahi kar raha)\b'
        ]
        
        # Thanks/Appreciation
        thanks_patterns = [
            r'\b(thanks|thank you|appreciated|awesome|great|good job)\b',
            r'\b(shukriya|dhanyavaad)\b'
        ]
        
        # Check patterns
        if any(re.search(p, text) for p in greeting_patterns):
            return 'greeting'
        elif any(re.search(p, text) for p in thanks_patterns):
            return 'appreciation'
        elif any(re.search(p, text) for p in complaint_patterns):
            return 'complaint'
        elif any(re.search(p, text) for p in command_patterns):
            return 'command'
        elif any(re.search(p, text) for p in question_patterns):
            return 'question'
        else:
            return 'statement'
    
    def _detect_mood(self, text: str) -> str:
        """Detect user's emotional state"""
        
        # Happy indicators
        if any(word in text for word in ['!', 'great', 'awesome', 'love', 'amazing', '😊', '😄', 'haha', 'lol']):
            return 'happy'
        
        # Frustrated indicators
        if any(word in text for word in ['not working', 'broken', '!!!', 'wtf', 'damn', 'frustrat', 'annoying']):
            return 'frustrated'
        
        # Urgent indicators
        if any(word in text for word in ['urgent', 'asap', 'quickly', 'now', 'immediately', 'hurry']):
            return 'urgent'
        
        # Tired/casual
        if any(word in text for word in ['tired', 'exhausted', 'whatever', 'meh']):
            return 'casual'
        
        return 'neutral'
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords"""
        # Remove common words
        stop_words = {'hey', 'hi', 'hello', 'the', 'a', 'an', 'is', 'are', 'can', 'you', 'please'}
        words = text.split()
        return [w for w in words if w not in stop_words and len(w) > 2]
    
    def _detect_urgency(self, text: str) -> int:
        """Detect urgency level 1-5"""
        urgent_words = ['urgent', 'asap', 'now', 'immediately', 'quick']
        frustrated_words = ['not working', 'broken', 'error']
        
        if any(word in text for word in urgent_words):
            return 5
        elif any(word in text for word in frustrated_words):
            return 4
        elif '!' in text or '!!!' in text:
            return 3
        elif '?' in text:
            return 2
        else:
            return 1
    
    def generate_response(self, analysis: Dict) -> str:
        """
        Generate appropriate response based on analysis
        
        Args:
            analysis: Output from analyze_input()
            
        Returns:
            Appropriate response string
        """
        intent = analysis['intent']
        mood = analysis['mood']
        time = analysis['time_of_day']
        urgency = analysis['urgency_level']
        
        # Handle greetings
        if intent == 'greeting':
            return self._greeting_response(mood, time)
        
        # Handle appreciation
        elif intent == 'appreciation':
            return self._appreciation_response(mood)
        
        # Handle complaints
        elif intent == 'complaint':
            return self._complaint_response(urgency)
        
        # Handle questions
        elif intent == 'question':
            return self._question_response(mood, urgency)
        
        # Handle commands
        elif intent == 'command':
            return self._command_acknowledgment(urgency)
        
        # Default
        else:
            return self._default_response(mood)
    
    def _greeting_response(self, mood: str, time: str) -> str:
        """Generate greeting response"""
        
        if time == "morning":
            responses = [
                "Good morning! Ready to make today productive?",
                "Morning, champ! What's on the agenda?",
                "Hey! Early bird gets the worm. What can I help with?",
                "Morning! Let's tackle the day together."
            ]
        elif time == "afternoon":
            responses = [
                "Hey! How's your afternoon going?",
                "Good afternoon! What do you need?",
                "Hey there! Halfway through the day - what's up?",
                "Afternoon! Ready to help."
            ]
        elif time == "evening":
            responses = [
                "Evening! Winding down or still going strong?",
                "Hey! Good evening. What can I do?",
                "Evening! Time to relax or still working?",
                "Hey! How was your day?"
            ]
        else:  # night
            responses = [
                "Burning the midnight oil? I'm here to help!",
                "Hey! Late night hustle? What do you need?",
                "Still up? I got your back. What's up?",
                "Night owl mode! What can I help with?"
            ]
        
        # Adjust for mood
        if mood == 'happy':
            return random.choice(responses) + " 😊"
        elif mood == 'frustrated':
            return "Hey, I'm here. Let's sort this out together."
        elif mood == 'urgent':
            return "I'm here! What do you need right now?"
        
        return random.choice(responses)
    
    def _appreciation_response(self, mood: str) -> str:
        """Respond to thanks/appreciation"""
        responses = [
            "You're welcome! Happy to help anytime.",
            "No problem at all! That's what I'm here for.",
            "Glad I could help! Let me know if you need anything else.",
            "Anytime! We make a good team.",
            "My pleasure! Don't hesitate to ask again."
        ]
        return random.choice(responses)
    
    def _complaint_response(self, urgency: int) -> str:
        """Respond to complaints/problems"""
        if urgency >= 4:
            return "I understand this is frustrating. Let me help you fix this right away. What exactly is the issue?"
        else:
            return "I hear you. Let's troubleshoot this together. Can you tell me more about what's happening?"
    
    def _question_response(self, mood: str, urgency: int) -> str:
        """Acknowledge questions"""
        if urgency >= 4:
            return "On it! Let me get you that answer."
        else:
            responses = [
                "Good question! Let me find that for you.",
                "I got you. Looking into that now.",
                "Let me check on that for you."
            ]
            return random.choice(responses)
    
    def _command_acknowledgment(self, urgency: int) -> str:
        """Acknowledge commands"""
        if urgency >= 4:
            return "Right away!"
        else:
            responses = [
                "On it!",
                "Got it, working on that.",
                "Sure thing!",
                "Coming right up!"
            ]
            return random.choice(responses)
    
    def _default_response(self, mood: str) -> str:
        """Default fallback response"""
        if mood == 'happy':
            return "I'm listening! What's on your mind? 😊"
        elif mood == 'frustrated':
            return "I'm here to help. What do you need?"
        else:
            return "I'm listening. How can I assist you?"


# Global instance
_responder = None

def get_responder() -> IntelligentResponder:
    """Get global responder instance"""
    global _responder
    if _responder is None:
        _responder = IntelligentResponder()
    return _responder


def generate_intelligent_response(user_input: str) -> Dict:
    """
    Main function to generate intelligent response
    
    Args:
        user_input: User's text input
        
    Returns:
        {
            'response': str,  # The response text
            'analysis': Dict,  # Analysis details
            'should_process_command': bool  # Whether to continue with command processing
        }
    """
    responder = get_responder()
    
    # Analyze input
    analysis = responder.analyze_input(user_input)
    
    # Generate response
    response_text = responder.generate_response(analysis)
    
    # Determine if command processing should continue
    should_process = analysis['intent'] in ['command', 'question']
    
    return {
        'response': response_text,
        'analysis': analysis,
        'should_process_command': should_process
    }
