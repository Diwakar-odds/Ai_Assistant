"""
DuckDuckGo Search Engine Connector.
Requires ZERO API keys. Uses HTTP POST to DuckDuckGo HTML and Lite endpoints.
"""

import logging
import urllib.parse
from typing import List
import requests
from bs4 import BeautifulSoup

from .base import BaseSearchEngine
from ..models import SearchResult

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


class DuckDuckGoEngine(BaseSearchEngine):
    """Zero-key DuckDuckGo Search Engine using POST protocol."""

    def __init__(self, timeout: float = 3.0):
        super().__init__(name="DuckDuckGo", timeout=timeout)
        self.session = requests.Session()
        self.session.headers.update(_DEFAULT_HEADERS)

    @property
    def is_available(self) -> bool:
        return True

    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """Perform search using Lite endpoint (ultra-fast, ~1s) with HTML POST fallback."""
        results = self._search_lite_post(query, num_results)
        if not results:
            results = self._search_html_post(query, num_results)
        if not results:
            results = self._search_instant_answer(query, num_results)
        return results

    def _extract_real_url(self, href: str) -> str:
        """Unpack DuckDuckGo redirect link /l/?uddg=... to actual target URL."""
        if "duckduckgo.com/l/?uddg=" in href or "/l/?uddg=" in href:
            try:
                parsed = urllib.parse.urlparse(href)
                qs = urllib.parse.parse_qs(parsed.query)
                if "uddg" in qs and qs["uddg"]:
                    return qs["uddg"][0]
            except Exception:
                pass
        return href

    def _search_html_post(self, query: str, num_results: int) -> List[SearchResult]:
        """Scrape DuckDuckGo HTML endpoint via HTTP POST."""
        results: List[SearchResult] = []
        try:
            url = "https://html.duckduckgo.com/html/"
            data = {"q": query, "b": ""}
            resp = self.session.post(url, data=data, timeout=self.timeout)

            if resp.status_code != 200:
                logger.debug(f"DuckDuckGo HTML POST status: {resp.status_code}")
                return results

            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.select(".result"):
                a_tag = item.select_one("a.result__a")
                if not a_tag:
                    continue

                raw_href = a_tag.get("href", "")
                real_url = self._extract_real_url(raw_href)

                if not real_url.startswith("http"):
                    continue

                snippet_el = item.select_one(".result__snippet")
                snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
                title = a_tag.get_text(" ", strip=True)

                results.append(
                    SearchResult(
                        title=title,
                        url=real_url,
                        snippet=snippet,
                        source="DuckDuckGo",
                    )
                )
                if len(results) >= num_results:
                    break

        except Exception as exc:
            logger.debug(f"DuckDuckGo HTML POST scrape error: {exc}")

        return results

    def _search_lite_post(self, query: str, num_results: int) -> List[SearchResult]:
        """Fallback to DuckDuckGo Lite endpoint via POST."""
        results: List[SearchResult] = []
        try:
            url = "https://lite.duckduckgo.com/lite/"
            data = {"q": query}
            resp = self.session.post(url, data=data, timeout=self.timeout)

            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")
            # Lite layout uses table rows: tr td a.result-link
            for a_tag in soup.select("a.result-link")[:num_results]:
                href = self._extract_real_url(a_tag.get("href", ""))
                if not href.startswith("http"):
                    continue
                title = a_tag.get_text(" ", strip=True)
                
                # Snippet is in following row .result-snippet
                parent_tr = a_tag.find_parent("tr")
                snippet = ""
                if parent_tr:
                    next_tr = parent_tr.find_next_sibling("tr")
                    if next_tr:
                        snippet_td = next_tr.select_one(".result-snippet")
                        if snippet_td:
                            snippet = snippet_td.get_text(" ", strip=True)

                results.append(
                    SearchResult(
                        title=title,
                        url=href,
                        snippet=snippet,
                        source="DuckDuckGo Lite",
                    )
                )
        except Exception as exc:
            logger.debug(f"DuckDuckGo Lite scrape error: {exc}")

        return results

    def _search_instant_answer(self, query: str, num_results: int) -> List[SearchResult]:
        """Fallback to DuckDuckGo Instant Answer API."""
        results: List[SearchResult] = []
        try:
            params = {
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1,
            }
            resp = self.session.get(
                "https://api.duckduckgo.com/",
                params=params,
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                return results

            data = resp.json()
            if data.get("AbstractText"):
                results.append(
                    SearchResult(
                        title=data.get("Heading") or "Direct Fact",
                        url=data.get("AbstractURL") or "https://duckduckgo.com",
                        snippet=data["AbstractText"],
                        source="DuckDuckGo Instant Answer",
                    )
                )

            for topic in data.get("RelatedTopics", [])[: num_results - len(results)]:
                if isinstance(topic, dict) and topic.get("FirstURL") and topic.get("Text"):
                    results.append(
                        SearchResult(
                            title=topic.get("Text", "")[:60] + "...",
                            url=topic["FirstURL"],
                            snippet=topic["Text"],
                            source="DuckDuckGo",
                        )
                    )
        except Exception as exc:
            logger.debug(f"DuckDuckGo Instant Answer error: {exc}")

        return results
