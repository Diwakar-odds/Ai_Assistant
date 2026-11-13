"""
AI Package (core_ai.ai)
Contains conversational AI, LLM providers, memory systems, NLP,
personality engines, and analytics.
"""

import logging

try:
    from core_ai.utils.logging_config import get_logger
    logger = get_logger(__name__, log_category="app")
except Exception:
    try:
        from ai_assistant.utils.logging_config import get_logger
        logger = get_logger(__name__, log_category="app")
    except Exception:
        logger = logging.getLogger(__name__)

__version__ = "2.0.0"

# Import domain sub-packages
from . import llm
from . import learning
from . import nlp
from . import memory as memory_pkg
from . import personality
from . import analytics

# Re-export key flat modules for 100% backward compatibility
from .conversational_ai import (
    AdvancedConversationalAI,
    ConversationState,
    MoodType,
    ConversationContext,
    TokenCounter,
)
# Alias for convenience
ConversationalAI = AdvancedConversationalAI

from .llm_provider import LLMProvider
from .memory import ConnectionPool, get_db_connection

# Advanced Learning Systems (lazy loading)
_feedback_engine = None
_intent_classifier = None
_prompt_optimizer = None
_multimodal_engine = None

def get_feedback_engine():
    """Get or create feedback learning engine (RLHF-inspired)"""
    global _feedback_engine
    if _feedback_engine is None:
        try:
            from .advanced_feedback_learning import AdaptiveLearningEngine
            _feedback_engine = AdaptiveLearningEngine()
        except ImportError as e:
            logger.warning(f"Could not load feedback engine: {e}")
            return None
    return _feedback_engine

def get_intent_classifier():
    """Get or create intent classifier with NER"""
    global _intent_classifier
    if _intent_classifier is None:
        try:
            from .intent_classification import IntentClassifier
            _intent_classifier = IntentClassifier()
        except ImportError as e:
            logger.warning(f"Could not load intent classifier: {e}")
            return None
    return _intent_classifier

def get_prompt_optimizer():
    """Get or create adaptive prompt optimizer"""
    global _prompt_optimizer
    if _prompt_optimizer is None:
        try:
            from .adaptive_prompts import PromptOptimizer
            _prompt_optimizer = PromptOptimizer()
        except ImportError as e:
            logger.warning(f"Could not load prompt optimizer: {e}")
            return None
    return _prompt_optimizer

def get_multimodal_engine():
    """Get or create multimodal learning engine"""
    global _multimodal_engine
    if _multimodal_engine is None:
        try:
            from .multimodal_learning import MultiModalLearningEngine
            _multimodal_engine = MultiModalLearningEngine()
        except ImportError as e:
            logger.warning(f"Could not load multimodal engine: {e}")
            return None
    return _multimodal_engine

__all__ = [
    "llm",
    "learning",
    "nlp",
    "personality",
    "analytics",
    "AdvancedConversationalAI",
    "ConversationalAI",
    "ConversationState",
    "MoodType",
    "ConversationContext",
    "TokenCounter",
    "LLMProvider",
    "ConnectionPool",
    "get_db_connection",
    "get_feedback_engine",
    "get_intent_classifier",
    "get_prompt_optimizer",
    "get_multimodal_engine",
]
