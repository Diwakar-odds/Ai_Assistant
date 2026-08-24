# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Semantic Response Cache System
Caches AI responses using semantic similarity matching

Features:
- Semantic search for similar queries (not exact match)
- DiskCache for persistence
- Automatic cache invalidation
- Response variations to avoid repetition
- Hit rate tracking
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
import logging
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

logger = logging.getLogger(__name__)

try:
    from diskcache import Cache
    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False
    logger.warning("diskcache not available - using in-memory cache")

# Defer sentence-transformers import to avoid slow startup (93s TensorFlow load)
# Will import on first use in _ensure_embedder_loaded()
try:
    import importlib.util
    EMBEDDINGS_AVAILABLE = importlib.util.find_spec("sentence_transformers") is not None
    if not EMBEDDINGS_AVAILABLE:
        logger.warning("sentence-transformers not available - using exact match only")
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not available - using exact match only")


class SemanticResponseCache:
    """Intelligent response caching with semantic similarity"""
    
    def __init__(self, 
                 cache_dir: str = "data/response_cache",
                 similarity_threshold: float = 0.85,
                 max_cache_size_gb: int = 2,
                 ttl_hours: int = 24):
        """
        Initialize semantic cache
        
        Args:
            cache_dir: Directory for cache storage
            similarity_threshold: Minimum similarity score (0-1) to consider a hit
            max_cache_size_gb: Maximum cache size in GB
            ttl_hours: Cache entry time-to-live in hours
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_hours * 3600
        
        # Initialize disk cache
        if DISKCACHE_AVAILABLE:
            self.cache = Cache(
                str(self.cache_dir),
                size_limit=max_cache_size_gb * 1024**3  # Convert GB to bytes
            )
        else:
            # Fallback to in-memory dict
            self.cache = {}
        
        # Initialize embeddings model (completely lazy - load on first use)
        self.embedder = None
        self._embedder_loading = False
        self._embedder_attempted = False  # Track if we've tried to load
        
        if EMBEDDINGS_AVAILABLE:
            logger.info("⚡ Semantic cache initialized (embeddings will load on first query)")
        else:
            logger.info("⚡ Semantic cache initialized in exact-match mode (sentence-transformers not available)")
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'total_queries': 0
        }
        
        # Load stats if exists
        self._load_stats()
    
    def _ensure_embedder_loaded(self):
        """Lazy load embedder on first use"""
        if self.embedder is not None or self._embedder_attempted or not EMBEDDINGS_AVAILABLE:
            return
        
        self._embedder_attempted = True
        
        # Import sentence_transformers here to avoid slow startup
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.warning("Failed to import sentence_transformers")
            return
        
        # Check if model is cached locally
        cache_dir = Path.home() / '.cache/huggingface/sentence-transformers/sentence-transformers_all-MiniLM-L6-v2'
        model_exists_locally = cache_dir.exists()
        
        if model_exists_locally:
            try:
                logger.info("🔄 Loading embeddings model from local cache...")
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
                logger.info("✅ Embeddings model loaded")
            except Exception as e:
                logger.warning(f"Failed to load embeddings model: {e}")
                self.embedder = None
        else:
            logger.info("⚠️ Embeddings model not cached. Download recommended.")
            logger.info("   python -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')\"")
    
    def _load_stats(self):
        """Load cache statistics"""
        stats_file = self.cache_dir / 'cache_stats.json'
        if stats_file.exists():
            try:
                with open(stats_file, 'r') as f:
                    self.stats = json.load(f)
            except:
                pass
    
    def _save_stats(self):
        """Save cache statistics"""
        stats_file = self.cache_dir / 'cache_stats.json'
        try:
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except:
            pass
    
    def _load_embedder_if_needed(self):
        """Lazy load embedder on first use (background download if needed)"""
        if self.embedder is not None or self._embedder_loading:
            return
        
        if not EMBEDDINGS_AVAILABLE:
            return
        
        self._embedder_loading = True
        try:
            import threading
            
            def _download_model():
                try:
                    from sentence_transformers import SentenceTransformer
                    self.embedder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
                    logger.info("✅ Embeddings model loaded successfully (background download)")
                    self._embedder_loading = False
                except Exception as e:
                    logger.error(f"Failed to download embeddings model: {e}")
                    self._embedder_loading = False
            
            # Download in background thread to avoid blocking
            thread = threading.Thread(target=_download_model, daemon=True, name="EmbedderDownloader")
            thread.start()
            logger.info("🔄 Downloading embeddings model in background...")
            
        except Exception as e:
            logger.error(f"Failed to start embedder download: {e}")
            self._embedder_loading = False
    
    def _get_embedding(self, text: str):
        """Get embedding for text"""
        # Lazy load embedder on first use
        self._load_embedder_if_needed()
        
        if self.embedder:
            try:
                return self.embedder.encode(text, convert_to_numpy=True)
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                return None
        return None
    
    def _compute_similarity(self, query_embedding, cached_embedding) -> float:
        """Compute cosine similarity between embeddings"""
        try:
            dot_product = np.dot(query_embedding, cached_embedding)
            norm_product = np.linalg.norm(query_embedding) * np.linalg.norm(cached_embedding)
            return float(dot_product / norm_product)
        except:
            return 0.0
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def get(self, query: str, context: Dict[str, Any] = None) -> Optional[str]:
        """
        Get cached response for query
        
        Args:
            query: User query
            context: Optional context for filtering
            
        Returns:
            Cached response if found, None otherwise
        """
        self.stats['total_queries'] += 1
        
        # Try exact match first (fast path)
        exact_key = self._get_cache_key(query.lower().strip())
        
        if DISKCACHE_AVAILABLE:
            cached = self.cache.get(exact_key)
        else:
            cached = self.cache.get(exact_key)
        
        if cached:
            # Check if expired
            timestamp = cached.get('timestamp', 0)
            if datetime.now().timestamp() - timestamp < self.ttl_seconds:
                self.stats['hits'] += 1
                self._save_stats()
                logger.info(f"✅ Cache HIT (exact): {query[:50]}...")
                return self._vary_response(cached['response'])
        
        # Try semantic search if embeddings available
        if self.embedder:
            query_embedding = self._get_embedding(query)
            if query_embedding is not None:
                match = self._find_similar(query_embedding, context)
                if match:
                    self.stats['hits'] += 1
                    self._save_stats()
                    logger.info(f"✅ Cache HIT (semantic): {query[:50]}...")
                    return self._vary_response(match['response'])
        
        # Cache miss
        self.stats['misses'] += 1
        self._save_stats()
        logger.debug(f"❌ Cache MISS: {query[:50]}...")
        return None
    
    def _find_similar(self, query_embedding: np.ndarray, 
                     context: Dict[str, Any] = None) -> Optional[Dict]:
        """Find semantically similar cached entry"""
        best_match = None
        best_similarity = 0.0
        
        # Scan cache for similar queries
        if DISKCACHE_AVAILABLE:
            for key in self.cache.iterkeys():
                try:
                    cached = self.cache.get(key)
                    if cached and 'embedding' in cached:
                        cached_embedding = np.array(cached['embedding'])
                        similarity = self._compute_similarity(query_embedding, cached_embedding)
                        
                        if similarity > best_similarity and similarity >= self.similarity_threshold:
                            # Check if not expired
                            timestamp = cached.get('timestamp', 0)
                            if datetime.now().timestamp() - timestamp < self.ttl_seconds:
                                best_similarity = similarity
                                best_match = cached
                except:
                    continue
        
        return best_match
    
    def set(self, query: str, response: str, context: Dict[str, Any] = None,
            metadata: Dict[str, Any] = None):
        """
        Cache a response
        
        Args:
            query: User query
            response: AI response
            context: Optional context
            metadata: Optional metadata (model used, latency, etc.)
        """
        key = self._get_cache_key(query.lower().strip())
        
        # Get embedding
        embedding = self._get_embedding(query)
        
        cache_entry = {
            'query': query,
            'response': response,
            'timestamp': datetime.now().timestamp(),
            'context': context or {},
            'metadata': metadata or {},
            'embedding': embedding.tolist() if embedding is not None else None,
            'hit_count': 0
        }
        
        if DISKCACHE_AVAILABLE:
            self.cache.set(key, cache_entry, expire=self.ttl_seconds)
        else:
            self.cache[key] = cache_entry
        
        logger.debug(f"💾 Cached response for: {query[:50]}...")
    
    def _vary_response(self, response: str) -> str:
        """
        Add slight variations to cached responses to feel more natural
        
        Returns the response with optional variations
        """
        # For now, return as-is
        # Future: Add response variations like different greetings, etc.
        return response
    
    def invalidate(self, query: str = None):
        """
        Invalidate cache entry or entire cache
        
        Args:
            query: Specific query to invalidate, or None to clear all
        """
        if query:
            key = self._get_cache_key(query.lower().strip())
            if DISKCACHE_AVAILABLE:
                self.cache.delete(key)
            else:
                self.cache.pop(key, None)
            logger.info(f"🗑️ Invalidated cache for: {query[:50]}...")
        else:
            if DISKCACHE_AVAILABLE:
                self.cache.clear()
            else:
                self.cache.clear()
            logger.info("🗑️ Cache cleared completely")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = (self.stats['hits'] / max(self.stats['total_queries'], 1)) * 100
        
        stats = {
            **self.stats,
            'hit_rate_percent': round(hit_rate, 2),
            'cache_size_entries': len(self.cache) if DISKCACHE_AVAILABLE else len(self.cache),
        }
        
        if DISKCACHE_AVAILABLE:
            stats['cache_size_mb'] = round(self.cache.volume() / 1024**2, 2)
        
        return stats
    
    def optimize(self):
        """Optimize cache by removing old/unused entries"""
        if DISKCACHE_AVAILABLE:
            # DiskCache handles this automatically
            self.cache.cull()
            logger.info("✅ Cache optimized")


# Global cache instance
_response_cache = None

def get_response_cache() -> SemanticResponseCache:
    """Get global response cache instance"""
    global _response_cache
    if _response_cache is None:
        _response_cache = SemanticResponseCache()
    return _response_cache


# Convenience functions
def cache_response(query: str, response: str, **kwargs):
    """Cache a response"""
    cache = get_response_cache()
    cache.set(query, response, **kwargs)


def get_cached_response(query: str, **kwargs) -> Optional[str]:
    """Get cached response"""
    cache = get_response_cache()
    return cache.get(query, **kwargs)


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    cache = get_response_cache()
    return cache.get_stats()


if __name__ == "__main__":
    # Test the cache
    logger.debug("Testing Semantic Response Cache...\n")
    
    cache = SemanticResponseCache()
    
    # Test 1: Exact match
    logger.debug("Test 1: Exact match")
    cache.set("What is the weather?", "It's sunny and 72°F")
    result = cache.get("What is the weather?")
    print(f"Result: {result}\n")
    
    # Test 2: Semantic match
    logger.debug("Test 2: Semantic match")
    result = cache.get("How's the weather today?")
    print(f"Result: {result}\n")
    
    # Test 3: Cache miss
    logger.debug("Test 3: Cache miss")
    result = cache.get("Tell me a joke")
    print(f"Result: {result}\n")
    
# Alias for backward compatibility
SemanticCache = SemanticResponseCache

