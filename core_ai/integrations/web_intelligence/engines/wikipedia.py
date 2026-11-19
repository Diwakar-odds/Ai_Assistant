"""
Wikipedia OpenSearch API Connector.
Fast and authoritative for entities, concepts, historical events, and definitions.
"""

import logging
import urllib.parse
from typing import List
import requests

from .base import BaseSearchEngine
from ..models import SearchResult

logger = logging.getLogger(__name__)


class WikipediaEngine(BaseSearchEngine):
    """Wikipedia OpenSearch API Engine."""

    def __init__(self, timeout: float = 3.0):
        super().__init__(name="Wikipedia", timeout=timeout)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PulsarAI/1.0 (Desktop Assistant; https://github.com)"
        })

    @property
    def is_available(self) -> bool:
        return True

    def search(self, query: str, num_results: int = 3) -> List[SearchResult]:
        results: List[SearchResult] = []
        try:
            url = (
                f"https://en.wikipedia.org/w/api.php?"
                f"action=opensearch&search={urllib.parse.quote_plus(query)}"
                f"&limit={num_results}&format=json"
            )
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return results

            payload = resp.json()
            titles = payload[1] if len(payload) > 1 else []
            descriptions = payload[2] if len(payload) > 2 else []
            urls = payload[3] if len(payload) > 3 else []

            for idx, title in enumerate(titles):
                desc = descriptions[idx] if idx < len(descriptions) else ""
                u = urls[idx] if idx < len(urls) else ""
                if title and desc:
                    results.append(
                        SearchResult(
                            title=f"Wikipedia: {title}",
                            url=u,
                            snippet=desc,
                            source="Wikipedia",
                        )
                    )
        except Exception as exc:
            logger.debug(f"Wikipedia OpenSearch error: {exc}")

        return results
