"""
Google News RSS Engine
======================
Keyless, highly reliable news engine using official Google News RSS feed.
Ideal for breaking news, elections, sports scores, and recent global events
without falling victim to anti-bot blocks or JS requirements.
"""

import html
import logging
import re
from typing import List
import xml.etree.ElementTree as ET
import requests

from .base import BaseSearchEngine
from ..models import SearchResult

logger = logging.getLogger(__name__)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(text: str) -> str:
    if not text:
        return ""
    stripped = _TAG_RE.sub(" ", text)
    unescaped = html.unescape(stripped)
    return re.sub(r"\s+", " ", unescaped).strip()


class GoogleNewsEngine(BaseSearchEngine):
    """Fetches real-time news headlines and summaries via Google News RSS."""

    def __init__(self, region: str = "IN", lang: str = "en", timeout: float = 3.5):
        super().__init__(name="Google News", timeout=timeout)
        self.region = region.upper()
        self.lang = lang.lower()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    @property
    def is_available(self) -> bool:
        return True

    def search(self, query: str, num_results: int = 5, max_results: int = None, **kwargs) -> List[SearchResult]:
        limit = max_results if max_results is not None else num_results
        url = "https://news.google.com/rss/search"
        params = {
            "q": query,
            "hl": f"{self.lang}-{self.region}",
            "gl": self.region,
            "ceid": f"{self.region}:{self.lang}",
        }
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                logger.debug(f"Google News RSS returned status {resp.status_code}")
                return []

            root = ET.fromstring(resp.text)
            results: List[SearchResult] = []

            for item in root.iter("item"):
                title = _clean_text(item.findtext("title", ""))
                link = (item.findtext("link") or "").strip()
                source_name = _clean_text(item.findtext("source", "")) or "Google News"
                pub_date = item.findtext("pubDate", "")
                description = _clean_text(item.findtext("description", ""))

                if not title or not link:
                    continue

                snippet = description if description and description.lower() not in title.lower() else f"Reported by {source_name}: {title}"
                if pub_date:
                    snippet += f" ({pub_date})"

                results.append(
                    SearchResult(
                        title=title,
                        url=link,
                        snippet=snippet,
                        source=f"Google News ({source_name})",
                    )
                )

                if len(results) >= limit:
                    break

            return results
        except Exception as exc:
            logger.debug(f"Google News RSS search failed: {exc}")
            return []
