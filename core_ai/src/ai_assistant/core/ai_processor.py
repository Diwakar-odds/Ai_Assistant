"""
AI Processor Module
Handles LLM Providers, Multimodal AI, Conversational AI, and Multilingual processing.
Extracted from assistant.py for modularity.
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AIProcessor:
    """Manages AI model orchestration, NLP, and vision features."""
    
    def __init__(self, enable_multimodal: bool = True, enable_conversational: bool = True, enable_multilingual: bool = True):
        self.enable_multimodal = enable_multimodal
        self.enable_conversational = enable_conversational
        self.enable_multilingual = enable_multilingual
        
        self._multimodal_ai = None
        self._conversational_ai = None
        self._multilingual = None
        self._llm_chat = None
        
        self._init_status = {
            'multimodal_ai': 'not_started',
            'conversational_ai': 'not_started',
            'multilingual': 'not_started',
            'llm_chat': 'not_started',
        }

    @property
    def multimodal_ai(self):
        """Lazy load MultiModal AI"""
        if self._multimodal_ai is None and self.enable_multimodal:
            try:
                from ai_assistant.multimodal import MultiModalAI
                self._multimodal_ai = MultiModalAI()
                self._init_status['multimodal_ai'] = 'ready'
                logger.info("✅ MultiModal AI initialized")
            except Exception as e:
                logger.warning(f"MultiModal AI init failed: {e}")
                self._init_status['multimodal_ai'] = 'failed'
        return self._multimodal_ai

    @property
    def conversational_ai(self):
        """Lazy load Conversational AI"""
        if self._conversational_ai is None and self.enable_conversational:
            try:
                from ai_assistant.ai.conversational_ai import AdvancedConversationalAI
                self._conversational_ai = AdvancedConversationalAI()
                self._init_status['conversational_ai'] = 'ready'
                logger.info("✅ Conversational AI initialized")
            except Exception as e:
                logger.warning(f"Conversational AI init failed: {e}")
                self._init_status['conversational_ai'] = 'failed'
        return self._conversational_ai

    @property
    def multilingual(self):
        """Lazy load Multilingual Support"""
        if self._multilingual is None and self.enable_multilingual:
            try:
                from ai_assistant.multilingual import MultilingualSupport
                self._multilingual = MultilingualSupport()
                self._init_status['multilingual'] = 'ready'
                logger.info("✅ Multilingual support initialized")
            except Exception as e:
                logger.warning(f"Multilingual init failed: {e}")
                self._init_status['multilingual'] = 'failed'
        return self._multilingual

    @property
    def llm_chat(self):
        """Lazy load LLM Chat provider"""
        if self._llm_chat is None:
            try:
                from ai_assistant.ai.llm_provider import get_llm_provider
                self._llm_chat = get_llm_provider()
                self._init_status['llm_chat'] = 'ready'
            except Exception as e:
                logger.debug(f"LLM Chat provider init note: {e}")
                self._init_status['llm_chat'] = 'failed'
        return self._llm_chat

    def get_init_status(self) -> Dict[str, str]:
        """Return the initialization status of AI components"""
        return self._init_status.copy()

    def analyze_screen(self, prompt: str = "Describe what you see on the screen") -> str:
        """Analyze screenshot using MultiModal AI"""
        if not self.multimodal_ai:
            return "MultiModal AI is not available. Check your API keys and configuration."
        try:
            return self.multimodal_ai.analyze_screen(prompt)
        except Exception as e:
            logger.error(f"Screen analysis error: {e}")
            return f"Failed to analyze screen: {e}"

    def answer_visual_question(self, question: str, image_path: Optional[str] = None) -> str:
        """Answer a visual question about an image or the screen"""
        if not self.multimodal_ai:
            return "MultiModal AI is not available."
        try:
            return self.multimodal_ai.answer_visual_question(question, image_path)
        except Exception as e:
            logger.error(f"Visual Q&A error: {e}")
            return f"Failed to answer visual question: {e}"
