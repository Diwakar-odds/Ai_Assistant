"""
AI Personality Sub-package
Provides adaptive personality, emotional intelligence, context-aware responses, and intelligent responder.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .personality_engine import PersonalityEngine
    from .emotional_intelligence import EmotionalIntelligence
    from .intelligent_responder import IntelligentResponder, get_responder, generate_intelligent_response
    from .context_aware_response import ContextAwareResponseGenerator
    from .adaptive_prompts import PromptTemplate, PromptExperiment, PromptOptimizer
    from .adaptive_voice import AdaptiveVoiceRecognition

def __getattr__(name):
    if name == "PersonalityEngine":
        from . import personality_engine
        return getattr(personality_engine, name)
    elif name == "EmotionalIntelligence":
        from . import emotional_intelligence
        return getattr(emotional_intelligence, name)
    elif name in ("IntelligentResponder", "get_responder", "generate_intelligent_response"):
        from . import intelligent_responder
        return getattr(intelligent_responder, name)
    elif name == "ContextAwareResponseGenerator":
        from . import context_aware_response
        return getattr(context_aware_response, name)
    elif name in ("PromptTemplate", "PromptExperiment", "PromptOptimizer"):
        from . import adaptive_prompts
        return getattr(adaptive_prompts, name)
    elif name == "AdaptiveVoiceRecognition":
        from . import adaptive_voice
        return getattr(adaptive_voice, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "PersonalityEngine",
    "EmotionalIntelligence",
    "IntelligentResponder",
    "get_responder",
    "generate_intelligent_response",
    "ContextAwareResponseGenerator",
    "PromptTemplate",
    "PromptExperiment",
    "PromptOptimizer",
    "AdaptiveVoiceRecognition",
]

