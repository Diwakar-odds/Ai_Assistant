"""
AI Memory Sub-package
Provides SQLite/vector persistence, historical RAG, user DNA profiling, and semantic retrieval.
"""

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .user_dna import UserDNA
    from .memory_retrieval import MemoryRetrieval, get_memory_retriever, retrieve_unified_historical_context
    from .smart_memory_retrieval import SmartMemoryRetrieval
    from .historical_rag import HistoricalRAG
    from .memory import ConnectionPool, get_db_connection, get_encrypted_db, save_knowledge

def __getattr__(name):
    if name == "UserDNA":
        from . import user_dna
        return getattr(user_dna, name)
    elif name in ("MemoryRetrieval", "get_memory_retriever", "retrieve_unified_historical_context"):
        from . import memory_retrieval
        return getattr(memory_retrieval, name)
    elif name == "SmartMemoryRetrieval":
        from . import smart_memory_retrieval
        return getattr(smart_memory_retrieval, name)
    elif name == "HistoricalRAG":
        from . import historical_rag
        return getattr(historical_rag, name)
    
    try:
        mem = importlib.import_module(".memory", __name__)
        if hasattr(mem, name):
            val = getattr(mem, name)
            globals()[name] = val
            return val
    except Exception:
        pass
        
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "UserDNA",
    "MemoryRetrieval",
    "get_memory_retriever",
    "retrieve_unified_historical_context",
    "SmartMemoryRetrieval",
    "HistoricalRAG",
    "ConnectionPool",
    "get_db_connection",
    "get_encrypted_db",
    "save_knowledge",
]
