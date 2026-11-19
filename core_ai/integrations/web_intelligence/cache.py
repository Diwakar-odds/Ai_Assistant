"""
Thread-safe Tiered TTL Cache for Web Intelligence.
Ensures repetitive queries across Chat, Voice, and Agents hit local memory instantly.
"""

import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from .models import SearchResult


class TieredTTLCache:
    """In-memory cache with category-based Time-To-Live expiration."""

    # Default TTL configuration (seconds)
    DEFAULT_TTLS = {
        "financial": 300,        # 5 minutes (gold, silver, stocks, crypto)
        "sports": 300,           # 5 minutes (live scores)
        "weather": 900,          # 15 minutes
        "news": 1800,            # 30 minutes
        "general": 21600,        # 6 hours
        "deep_research": 43200,  # 12 hours
    }

    def __init__(self, max_entries: int = 1000):
        self._cache: Dict[str, Tuple[List[SearchResult], float, str]] = {}
        self._lock = threading.RLock()
        self._max_entries = max_entries

    def _determine_category(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["gold", "silver", "petrol", "diesel", "stock", "nifty", "sensex", "crypto", "bitcoin", "dollar", "rupee", "price", "rate", "bhav"]):
            return "financial"
        if any(w in q for w in ["weather", "mausam", "temperature", "forecast", "rain", "barish"]):
            return "weather"
        if any(w in q for w in ["score", "match", "ipl", "cricket", "football", "who won"]):
            return "sports"
        if any(w in q for w in ["news", "headline", "breaking", "khabar", "latest"]):
            return "news"
        return "general"

    def _normalize_key(self, query: str) -> str:
        return " ".join(query.strip().lower().split())

    def get(self, query: str) -> Optional[List[SearchResult]]:
        """Retrieve unexpired cached search results."""
        key = self._normalize_key(query)
        now = time.time()
        with self._lock:
            if key in self._cache:
                results, expires_at, _ = self._cache[key]
                if now < expires_at:
                    return results
                else:
                    # Expired
                    del self._cache[key]
        return None

    def set(self, query: str, results: List[SearchResult], category: Optional[str] = None):
        """Store search results with category-appropriate TTL."""
        if not results:
            return

        key = self._normalize_key(query)
        cat = category or self._determine_category(query)
        ttl = self.DEFAULT_TTLS.get(cat, self.DEFAULT_TTLS["general"])
        expires_at = time.time() + ttl

        with self._lock:
            # Simple LRU eviction if full
            if len(self._cache) >= self._max_entries:
                # Remove 20% oldest entries
                items = sorted(self._cache.items(), key=lambda item: item[1][1])
                for k, _ in items[: int(self._max_entries * 0.2)]:
                    self._cache.pop(k, None)

            self._cache[key] = (results, expires_at, cat)

    def clear(self):
        """Purge all cache entries."""
        with self._lock:
            self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Return cache health metrics."""
        now = time.time()
        with self._lock:
            valid_entries = sum(1 for _, exp, _ in self._cache.values() if exp > now)
            return {
                "total_cached": len(self._cache),
                "active_valid_entries": valid_entries,
            }
