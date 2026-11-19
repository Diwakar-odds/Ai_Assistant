"""
SerpAPI Search Engine Connector.
Provides official Google search results. Active only if SERPAPI_API_KEY is configured.
"""

import logging
from typing import List
import requests

from .base import BaseSearchEngine
from ..models import SearchResult

logger = logging.getLogger(__name__)


class SerpApiEngine(BaseSearchEngine):
    """SerpAPI Google Search Connector."""

    def __init__(self, api_key: str = "", timeout: float = 3.5):
        super().__init__(name="SerpAPI", timeout=timeout)
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
            url = "https://serpapi.com/search"
            params = {
                "api_key": self.api_key,
                "q": query,
                "engine": "google",
                "num": num_results,
            }
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                logger.debug(f"SerpAPI returned HTTP {resp.status_code}")
                return results

            data = resp.json()

            # Direct answer box
            if "answer_box" in data and data["answer_box"].get("answer"):
                results.append(
                    SearchResult(
                        title="Google Quick Answer",
                        url=data["answer_box"].get("link", "https://google.com"),
                        snippet=data["answer_box"]["answer"],
                        source="Google via SerpAPI",
                    )
                )

            for item in data.get("organic_results", []):
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source="Google via SerpAPI",
                    )
                )
                if len(results) >= num_results:
                    break

        except Exception as exc:
            logger.debug(f"SerpAPI search error: {exc}")

        return results
