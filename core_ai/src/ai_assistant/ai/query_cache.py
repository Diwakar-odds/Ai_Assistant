"""
TF-IDF Query Similarity Cache
Smart response caching using semantic similarity

Features:
- TF-IDF vectorization of queries
- Cosine similarity matching
- Response caching with TTL
- Cache invalidation on concept drift
- Cost savings by reducing LLM calls
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import Counter
import math

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ scikit-learn not available - using fallback similarity")


class QuerySimilarityCache:
    """
    Smart query caching using TF-IDF similarity
    """
    
    def __init__(self, db_path: str = "data/caches/query_cache.db", 
                 similarity_threshold: float = 0.85,
                 cache_ttl_hours: int = 24):
        self.db_path = db_path
        self.similarity_threshold = similarity_threshold
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            self.fitted = False
        
        self._init_database()
        self._load_cache()
    
    def _init_database(self):
        """Initialize cache database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_cache (
                    query_hash TEXT PRIMARY KEY,
                    query_text TEXT NOT NULL,
                    response TEXT NOT NULL,
                    query_embedding TEXT,
                    hit_count INTEGER DEFAULT 0,
                    cost_saved REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    last_used TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_queries INTEGER DEFAULT 0,
                    cache_hits INTEGER DEFAULT 0,
                    cache_misses INTEGER DEFAULT 0,
                    cost_saved REAL DEFAULT 0.0,
                    last_updated TEXT NOT NULL
                )
            """)
            
            # Initialize stats if not exists
            cursor = conn.execute("SELECT COUNT(*) FROM cache_stats")
            if cursor.fetchone()[0] == 0:
                conn.execute("""
                    INSERT INTO cache_stats (total_queries, cache_hits, cache_misses, cost_saved, last_updated)
                    VALUES (0, 0, 0, 0.0, ?)
                """, (datetime.now().isoformat(),))
    
    def _load_cache(self):
        """Load existing cache entries"""
        self.cache = {}
        self.queries = []
        self.embeddings = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT query_hash, query_text, response, query_embedding, expires_at
                FROM query_cache
                WHERE expires_at > ?
            """, (datetime.now().isoformat(),))
            
            for row in cursor.fetchall():
                query_hash, query_text, response, embedding_json, expires_at = row
                self.cache[query_hash] = {
                    'query': query_text,
                    'response': response,
                    'expires_at': datetime.fromisoformat(expires_at)
                }
                self.queries.append(query_text)
                
                if embedding_json:
                    self.embeddings.append(json.loads(embedding_json))
        
        # Fit vectorizer on existing queries
        if SKLEARN_AVAILABLE and len(self.queries) > 0:
            try:
                self.vectorizer.fit(self.queries)
                self.fitted = True
            except:
                self.fitted = False
    
    def _compute_hash(self, query: str) -> str:
        """Compute hash for query"""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _compute_similarity_sklearn(self, query: str) -> Optional[Tuple[str, float]]:
        """Compute similarity using sklearn"""
        if not self.fitted or len(self.queries) == 0:
            return None
        
        try:
            # Transform new query
            query_vec = self.vectorizer.transform([query])
            
            # Transform all cached queries
            cache_vecs = self.vectorizer.transform(self.queries)
            
            # Compute similarities
            similarities = cosine_similarity(query_vec, cache_vecs)[0]
            
            # Find best match
            max_idx = similarities.argmax()
            max_sim = similarities[max_idx]
            
            if max_sim >= self.similarity_threshold:
                best_query = self.queries[max_idx]
                query_hash = self._compute_hash(best_query)
                return query_hash, max_sim
        except:
            return None
        
        return None
    
    def _compute_similarity_fallback(self, query: str) -> Optional[Tuple[str, float]]:
        """Fallback similarity using word overlap"""
        query_words = set(query.lower().split())
        
        best_match = None
        best_score = 0.0
        
        for cached_query in self.queries:
            cached_words = set(cached_query.lower().split())
            
            # Jaccard similarity
            intersection = len(query_words & cached_words)
            union = len(query_words | cached_words)
            
            if union > 0:
                score = intersection / union
                
                if score > best_score and score >= self.similarity_threshold:
                    best_score = score
                    best_match = cached_query
        
        if best_match:
            return self._compute_hash(best_match), best_score
        
        return None
    
    def get(self, query: str) -> Optional[Dict]:
        """
        Get cached response for query
        
        Returns:
            dict with 'response', 'similarity', 'from_cache': True if found
            None if not found
        """
        # Exact match first
        query_hash = self._compute_hash(query)
        
        if query_hash in self.cache:
            entry = self.cache[query_hash]
            if entry['expires_at'] > datetime.now():
                self._record_hit(query_hash)
                return {
                    'response': entry['response'],
                    'similarity': 1.0,
                    'from_cache': True
                }
        
        # Similarity search
        if SKLEARN_AVAILABLE:
            match = self._compute_similarity_sklearn(query)
        else:
            match = self._compute_similarity_fallback(query)
        
        if match:
            match_hash, similarity = match
            if match_hash in self.cache:
                entry = self.cache[match_hash]
                if entry['expires_at'] > datetime.now():
                    self._record_hit(match_hash)
                    return {
                        'response': entry['response'],
                        'similarity': similarity,
                        'from_cache': True
                    }
        
        # Cache miss
        self._record_miss()
        return None
    
    def set(self, query: str, response: str, cost_saved: float = 0.0):
        """Cache a query-response pair"""
        query_hash = self._compute_hash(query)
        now = datetime.now()
        expires_at = now + self.cache_ttl
        
        # Compute embedding for similarity search
        embedding_json = None
        if SKLEARN_AVAILABLE and self.fitted:
            try:
                embedding = self.vectorizer.transform([query]).toarray()[0]
                embedding_json = json.dumps(embedding.tolist())
            except:
                pass
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO query_cache
                (query_hash, query_text, response, query_embedding, hit_count, cost_saved, created_at, last_used, expires_at)
                VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)
            """, (
                query_hash,
                query,
                response,
                embedding_json,
                cost_saved,
                now.isoformat(),
                now.isoformat(),
                expires_at.isoformat()
            ))
        
        # Update in-memory cache
        self.cache[query_hash] = {
            'query': query,
            'response': response,
            'expires_at': expires_at
        }
        
        # Update queries list
        if query not in self.queries:
            self.queries.append(query)
            
            # Refit vectorizer periodically
            if SKLEARN_AVAILABLE and len(self.queries) % 10 == 0:
                try:
                    self.vectorizer.fit(self.queries)
                    self.fitted = True
                except:
                    pass
    
    def _record_hit(self, query_hash: str):
        """Record cache hit"""
        with sqlite3.connect(self.db_path) as conn:
            # Update entry
            conn.execute("""
                UPDATE query_cache
                SET hit_count = hit_count + 1,
                    last_used = ?
                WHERE query_hash = ?
            """, (datetime.now().isoformat(), query_hash))
            
            # Update stats
            conn.execute("""
                UPDATE cache_stats
                SET total_queries = total_queries + 1,
                    cache_hits = cache_hits + 1,
                    last_updated = ?
            """, (datetime.now().isoformat(),))
    
    def _record_miss(self):
        """Record cache miss"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE cache_stats
                SET total_queries = total_queries + 1,
                    cache_misses = cache_misses + 1,
                    last_updated = ?
            """, (datetime.now().isoformat(),))
    
    def clear_expired(self):
        """Remove expired cache entries"""
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM query_cache
                WHERE expires_at < ?
            """, (now.isoformat(),))
        
        # Reload cache
        self._load_cache()
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT total_queries, cache_hits, cache_misses, cost_saved
                FROM cache_stats
                ORDER BY id DESC LIMIT 1
            """)
            
            row = cursor.fetchone()
            if row:
                total, hits, misses, cost = row
                hit_rate = hits / total if total > 0 else 0.0
                
                return {
                    'total_queries': total,
                    'cache_hits': hits,
                    'cache_misses': misses,
                    'hit_rate': hit_rate,
                    'cost_saved': cost,
                    'cache_size': len(self.cache)
                }
        
        return {
            'total_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'hit_rate': 0.0,
            'cost_saved': 0.0,
            'cache_size': 0
        }
    
    def invalidate_similar(self, query: str, threshold: float = 0.9):
        """Invalidate cache entries similar to query (for concept drift)"""
        to_remove = []
        
        for cached_query in self.queries:
            if SKLEARN_AVAILABLE and self.fitted:
                try:
                    query_vec = self.vectorizer.transform([query])
                    cached_vec = self.vectorizer.transform([cached_query])
                    sim = cosine_similarity(query_vec, cached_vec)[0][0]
                    
                    if sim >= threshold:
                        to_remove.append(self._compute_hash(cached_query))
                except:
                    pass
        
        if to_remove:
            with sqlite3.connect(self.db_path) as conn:
                for query_hash in to_remove:
                    conn.execute("DELETE FROM query_cache WHERE query_hash = ?", (query_hash,))
            
            self._load_cache()


def example_usage():
    """Demonstrate query caching"""
    cache = QuerySimilarityCache(similarity_threshold=0.85)
    
    # First query - cache miss
    result = cache.get("What is machine learning?")
    if result is None:
        print("Cache miss - querying LLM...")
        response = "Machine learning is a branch of AI..."
        cache.set("What is machine learning?", response, cost_saved=0.002)
        print(f"Response: {response}")
    else:
        print(f"Cache hit! Similarity: {result['similarity']:.2f}")
        print(f"Response: {result['response']}")
    
    # Similar query - should hit cache
    result = cache.get("What's machine learning?")
    if result:
        print(f"\nCache hit on similar query! Similarity: {result['similarity']:.2f}")
        print(f"Response: {result['response']}")
    
    # Different query - cache miss
    result = cache.get("How do I train a neural network?")
    if result is None:
        print("\nCache miss - different query")
    
    # Get stats
    stats = cache.get_stats()
    print(f"\nCache Statistics:")
    print(f"  Total queries: {stats['total_queries']}")
    print(f"  Cache hits: {stats['cache_hits']}")
    print(f"  Hit rate: {stats['hit_rate']:.1%}")
    print(f"  Cache size: {stats['cache_size']}")


if __name__ == "__main__":
    example_usage()
