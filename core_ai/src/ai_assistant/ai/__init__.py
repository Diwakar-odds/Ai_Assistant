"""
AI and machine learning modules for the assistant.

This package contains conversational AI, LLM providers, memory systems,
and other AI-related functionality including advanced learning systems.
"""

__version__ = "1.1.0"

from .conversational_ai import *
from .llm_provider import *
from .memory import *

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
            print(f"Warning: Could not load feedback engine: {e}")
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
            print(f"Warning: Could not load intent classifier: {e}")
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
            print(f"Warning: Could not load prompt optimizer: {e}")
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
            print(f"Warning: Could not load multimodal engine: {e}")
            return None
    return _multimodal_engine

# Export learning functions
__all__ = [
    'get_feedback_engine',
    'get_intent_classifier', 
    'get_prompt_optimizer',
    'get_multimodal_engine'
]