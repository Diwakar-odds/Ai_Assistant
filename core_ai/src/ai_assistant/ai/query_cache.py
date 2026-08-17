"""
Query Cache Module (Alias / Wrapper for SemanticResponseCache)
Forwards to semantic_cache.py for unified embedding-based response caching.
"""

from ai_assistant.ai.semantic_cache import SemanticResponseCache

# Aliases for backward compatibility
QueryCache = SemanticResponseCache
SemanticCache = SemanticResponseCache

__all__ = ['QueryCache', 'SemanticCache', 'SemanticResponseCache']
