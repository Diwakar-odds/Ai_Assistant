"""
Command Processor Service

Handles command processing, multilingual support, and response formatting.
Extracted from ModernAssistant for better modularity.
"""

import logging

logger = logging.getLogger(__name__)

class CommandProcessor:
    """Process user commands with multilingual support"""
    
    def __init__(self, ai_manager=None, voice_manager=None):
        """
        Initialize command processor
        
        Args:
            ai_manager: AI service manager for LLM interactions
            voice_manager: Voice service manager for TTS
        """
        self.ai_manager = ai_manager
        self.voice_manager = voice_manager
        self.conversation_history = []
    
    def process_command(self, command_text, model_preference=None):
        """
        Main command processing entry point
        
        Args:
            command_text: Command string to process
            model_preference: Optional model preference
            
        Returns:
            str: Response to the command
        """
        try:
            if not command_text or not command_text.strip():
                return "Please provide a command."
            
            # Clean command
            command = command_text.strip()
            
            # Add to history
            self.conversation_history.append({
                'role': 'user',
                'content': command
            })
            
            # Process with AI if available
            if self.ai_manager and hasattr(self.ai_manager, 'conversational_ai'):
                ai = self.ai_manager.conversational_ai
                if ai is not None:
                    response = ai.process_query(command)
                else:
                    response = self._fallback_response(command)
            else:
                response = self._fallback_response(command)
            
            # Add response to history
            self.conversation_history.append({
                'role': 'assistant',
                'content': response
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            return f"I encountered an error processing that command: {str(e)}"
    
    def _fallback_response(self, command):
        """
        Fallback response when AI is not available
        
        Args:
            command: User command
            
        Returns:
            str: Basic response
        """
        command_lower = command.lower()
        
        # Simple pattern matching
        if any(word in command_lower for word in ['hello', 'hi', 'hey']):
            return "Hello! How can I assist you today?"
        elif any(word in command_lower for word in ['bye', 'goodbye']):
            return "Goodbye! Have a great day!"
        elif 'help' in command_lower:
            return "I can help you with various tasks. Try asking me questions or giving me commands!"
        elif '?' in command:
            return f"You asked: {command}. I'm currently running in fallback mode with limited capabilities."
        else:
            return f"I received your command: {command}. AI features are initializing..."
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def get_history(self, limit=10):
        """
        Get recent conversation history
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            list: Recent conversation history
        """
        return self.conversation_history[-limit:] if self.conversation_history else []
