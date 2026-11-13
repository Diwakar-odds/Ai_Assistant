"""
AI LLM Sub-package
Provides Large Language Model orchestration, routing, caching, and local/offline inference.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_provider import LLMProvider, OpenAIProvider, GeminiProvider
    from .offline_llm_provider import OfflineLLMProvider, get_offline_llm
    from .gguf_model_manager import GGUFModelManager, get_gguf_manager
    from .local_model_manager import LocalModelManager
    from .model_router import ModelTier, ModelConfig, QueryAnalysis, get_model_router
    from .streaming_handler import StreamProvider, StreamChunk, StreamingResponseHandler
    from .semantic_cache import SemanticResponseCache, get_response_cache
    from .query_cache import QuerySimilarityCache
    from .llm_bandit import LLMBandit
    from .network_aware_llm import OnlineLLMConfig, get_optimal_llm_config

def __getattr__(name):
    # Lazy imports to minimize startup time
    if name in ("LLMProvider", "OpenAIProvider", "GeminiProvider"):
        from . import llm_provider
        return getattr(llm_provider, name)
    elif name in ("OfflineLLMProvider", "get_offline_llm"):
        from . import offline_llm_provider
        return getattr(offline_llm_provider, name)
    elif name in ("GGUFModelManager", "get_gguf_manager"):
        from . import gguf_model_manager
        return getattr(gguf_model_manager, name)
    elif name == "LocalModelManager":
        from . import local_model_manager
        return getattr(local_model_manager, name)
    elif name in ("ModelTier", "ModelConfig", "QueryAnalysis", "get_model_router"):
        from . import model_router
        return getattr(model_router, name)
    elif name in ("StreamProvider", "StreamChunk", "StreamingResponseHandler"):
        from . import streaming_handler
        return getattr(streaming_handler, name)
    elif name in ("SemanticResponseCache", "get_response_cache"):
        from . import semantic_cache
        return getattr(semantic_cache, name)
    elif name == "QuerySimilarityCache":
        from . import query_cache
        return getattr(query_cache, name)
    elif name == "LLMBandit":
        from . import llm_bandit
        return getattr(llm_bandit, name)
    elif name in ("OnlineLLMConfig", "get_optimal_llm_config"):
        from . import network_aware_llm
        return getattr(network_aware_llm, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "LLMProvider",
    "OfflineLLMProvider",
    "GGUFModelManager",
    "LocalModelManager",
    "ModelTier",
    "ModelConfig",
    "QueryAnalysis",
    "get_model_router",
    "StreamProvider",
    "StreamChunk",
    "StreamingResponseHandler",
    "SemanticResponseCache",
    "get_response_cache",
    "QuerySimilarityCache",
    "LLMBandit",
    "OnlineLLMConfig",
    "get_optimal_llm_config",
]

