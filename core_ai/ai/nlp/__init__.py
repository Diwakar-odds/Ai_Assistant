"""
AI NLP Sub-package
Provides intent classification, command parsing, semantic vector embeddings, and intent routing.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .intent_router import IntentRouter, IntentResult, IntentDefinition
    from .intent_classification import IntentClassifier, Intent, Entity
    from .multi_step_parser import MultiStepCommandParser, TaskStep, parse_multi_step_command
    from .shared_embedder import get_shared_embedder, is_embedder_available, encode_text
    from .domain_embeddings import DomainAdaptedEmbeddings, DomainAdapter, DomainExample
    from .command_predictor import CommandSuccessPredictor
    from .command_sequences import CommandMarkovChain
    from .smart_command_prediction import SmartCommandPredictor

def __getattr__(name):
    if name in ("IntentRouter", "IntentResult", "IntentDefinition"):
        from . import intent_router
        return getattr(intent_router, name)
    elif name in ("IntentClassifier", "Intent", "Entity"):
        from . import intent_classification
        return getattr(intent_classification, name)
    elif name in ("MultiStepCommandParser", "TaskStep", "parse_multi_step_command"):
        from . import multi_step_parser
        return getattr(multi_step_parser, name)
    elif name in ("get_shared_embedder", "is_embedder_available", "encode_text"):
        from . import shared_embedder
        return getattr(shared_embedder, name)
    elif name in ("DomainAdaptedEmbeddings", "DomainAdapter", "DomainExample"):
        from . import domain_embeddings
        return getattr(domain_embeddings, name)
    elif name == "CommandSuccessPredictor":
        from . import command_predictor
        return getattr(command_predictor, name)
    elif name == "CommandMarkovChain":
        from . import command_sequences
        return getattr(command_sequences, name)
    elif name == "SmartCommandPredictor":
        from . import smart_command_prediction
        return getattr(smart_command_prediction, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "IntentRouter",
    "IntentResult",
    "IntentDefinition",
    "IntentClassifier",
    "Intent",
    "Entity",
    "MultiStepCommandParser",
    "TaskStep",
    "parse_multi_step_command",
    "get_shared_embedder",
    "is_embedder_available",
    "encode_text",
    "DomainAdaptedEmbeddings",
    "DomainAdapter",
    "DomainExample",
    "CommandSuccessPredictor",
    "CommandMarkovChain",
    "SmartCommandPredictor",
]

