"""
Tavily Search Engine Connector.
High-precision search optimized for AI agents and RAG.
Active only if user provides TAVILY_API_KEY in settings or environment.
"""

import logging
from typing import List
import requests

from .base import BaseSearchEngine
from ..models import SearchResult

logger = logging.getLogger(__name__)


class TavilyEngine(BaseSearchEngine):
    """Tavily AI Search Engine Connector."""

    def __init__(self, api_key: str = "", timeout: float = 3.5):
        super().__init__(name="Tavily", timeout=timeout)
        self.api_key = api_key.strip()
        self.session = requests.Session()

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        if not self.is_available:
            return []

        results: List[SearchResult] = []
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": "basic",
                "include_answer": True,
                "max_results": num_results,
            }
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            if resp.status_code != 200:
                logger.debug(f"Tavily returned HTTP {resp.status_code}")
                return results

            data = resp.json()

            # Include direct answer if available
            if data.get("answer"):
                results.append(
                    SearchResult(
                        title="Tavily AI Direct Answer",
                        url="https://tavily.com",
                        snippet=data["answer"],
                        source="Tavily AI",
                    )
                )

            for item in data.get("results", []):
                results.append(
                    SearchResult(
                        title=item.get("title", "Web Result"),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        source="Tavily",
                        relevance_score=float(item.get("score", 1.0)),
                    )
                )
                if len(results) >= num_results:
                    break

        except Exception as exc:
            logger.debug(f"Tavily search error: {exc}")

        return results
