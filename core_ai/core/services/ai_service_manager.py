"""
AI Service Manager

Manages AI-related services including multimodal AI, conversational AI, and LLM chat.
Extracted from ModernAssistant for better modularity.
"""

import logging

logger = logging.getLogger(__name__)

class AIServiceManager:
    """Manages AI services with lazy initialization"""
    
    def __init__(self):
        """Initialize AI service manager"""
        self._multimodal_ai = None
        self._conversational_ai = None
        self._llm_chat = None
        self._initialized = {
            'multimodal': False,
            'conversational': False,
            'llm': False
        }
    
    @property
    def multimodal_ai(self):
        """Get multimodal AI service (lazy loaded)"""
        if not self._initialized['multimodal']:
            try:
                from ai_assistant.integrations.multimodal_integration import get_multimodal_ai
                self._multimodal_ai = get_multimodal_ai()
                self._initialized['multimodal'] = True
                logger.info("Multimodal AI initialized")
            except Exception as e:
                logger.warning(f"Multimodal AI initialization failed: {e}")
        return self._multimodal_ai
    
    @property
    def conversational_ai(self):
        """Get conversational AI service (lazy loaded)"""
        if not self._initialized['conversational']:
            try:
                from ai_assistant.integrations.conversational_ai import get_conversational_ai
                self._conversational_ai = get_conversational_ai()
                self._initialized['conversational'] = True
                logger.info("Conversational AI initialized")
            except Exception as e:
                logger.warning(f"Conversational AI initialization failed: {e}")
        return self._conversational_ai
    
    @property
    def llm_chat(self):
        """Get LLM chat service (lazy loaded)"""
        if not self._initialized['llm']:
            try:
                from ai_assistant.modules.gemini_chat import GeminiChat
                self._llm_chat = GeminiChat()
                self._initialized['llm'] = True
                logger.info("LLM chat initialized")
            except Exception as e:
                logger.warning(f"LLM chat initialization failed: {e}")
        return self._llm_chat
    
    def get_status(self):
        """Get initialization status of all AI services"""
        return {
            'multimodal': 'ready' if self._initialized['multimodal'] and self._multimodal_ai else 'not_started',
            'conversational': 'ready' if self._initialized['conversational'] and self._conversational_ai else 'not_started',
            'llm': 'ready' if self._initialized['llm'] and self._llm_chat else 'not_started'
        }
