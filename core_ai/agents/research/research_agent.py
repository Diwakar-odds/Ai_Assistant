import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import urllib.parse

from bs4 import BeautifulSoup
import requests

from ..base_agent import BaseAgent
from ..models import Task, TaskResult

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


class ResearchAgent(BaseAgent):
    """Handles web research, Wikipedia lookups, and URL scraping without blocking the event loop."""

    def __init__(self, agent_id: str = "research-001", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config or {})
        self.name = "Research Agent"
        self.category = "research"
        self.description = "Performs web searches, Wikipedia lookups, scraping, and info gathering."
        self.capabilities = [
            "web_search",
            "wikipedia_summary",
            "scrape_url",
            "research_topic",
        ]

    async def can_handle(self, task: Task) -> bool:
        keywords = [
            "search", "find", "lookup", "research", "scrape",
            "wikipedia", "google", "investigate", "facts",
        ]
        return any(kw in (task.description or "").lower() for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        try:
            desc = (task.description or "").lower()
            if "wikipedia" in desc or "wiki" in desc:
                return await self._search_wikipedia(task)
            if "scrape" in desc or "extract" in desc or task.params.get("url"):
                return await self._scrape_url(task)
            return await self._web_search(task)
        except Exception as exc:
            logger.error("[%s] Research execution failed: %s", self.agent_id, exc, exc_info=True)
            return TaskResult(success=False, error=str(exc))

    def _duckduckgo_search_sync(self, query: str, num_results: int) -> List[Dict[str, str]]:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results: List[Dict[str, str]] = []
        for item in soup.select(".result"):
            a = item.select_one("a.result__a")
            if not a:
                continue
            href = a.get("href") or ""
            if not href.startswith("http"):
                continue
            snippet_el = item.select_one(".result__snippet")
            results.append(
                {
                    "title": a.get_text(" ", strip=True),
                    "url": href,
                    "description": snippet_el.get_text(" ", strip=True) if snippet_el else "",
                }
            )
            if len(results) >= num_results:
                break
        return results

    def _wikipedia_opensearch_sync(self, query: str, num_results: int) -> List[Dict[str, str]]:
        url = (
            "https://en.wikipedia.org/w/api.php?"
            f"action=opensearch&search={urllib.parse.quote_plus(query)}&limit={num_results}&format=json"
        )
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        titles = payload[1] if len(payload) > 1 else []
        descs = payload[2] if len(payload) > 2 else []
        urls = payload[3] if len(payload) > 3 else []
        results: List[Dict[str, str]] = []
        for idx, title in enumerate(titles):
            results.append(
                {
                    "title": title,
                    "url": urls[idx] if idx < len(urls) else "",
                    "description": descs[idx] if idx < len(descs) else "",
                }
            )
        return results

    async def _web_search(self, task: Task) -> TaskResult:
        query = str(task.params.get("query") or task.description or "").strip()
        num_results = int(task.params.get("num_results", 5))
        if not query:
            return TaskResult(success=False, error="No search query provided.")

        def _search_sync() -> List[Dict[str, str]]:
            # 1. Optional googlesearch-python if installed
            try:
                from googlesearch import search as g_search
                items: List[Dict[str, str]] = []
                for res in g_search(query, num_results=num_results, advanced=True):
                    items.append(
                        {
                            "title": getattr(res, "title", "") or "",
                            "url": getattr(res, "url", str(res)),
                            "description": getattr(res, "description", "") or "",
                        }
                    )
                if items:
                    return items
            except Exception:
                pass

            # 2. DuckDuckGo HTML fallback (zero extra deps)
            try:
                items = self._duckduckgo_search_sync(query, num_results)
                if items:
                    return items
            except Exception as exc:
                logger.debug("DuckDuckGo search failed: %s", exc)

            # 3. Wikipedia OpenSearch fallback
            return self._wikipedia_opensearch_sync(query, num_results)

        try:
            results = await asyncio.to_thread(_search_sync)
        except Exception as exc:
            return TaskResult(success=False, error=f"Search failed: {exc}")

        output_path = self._resolve_output_path(task, f"search_{task.task_id[:8]}.json")
        await asyncio.to_thread(
            lambda: open(output_path, "w", encoding="utf-8").write(
                json.dumps({"query": query, "results": results}, indent=2, ensure_ascii=False)
            )
        )

        summary_lines = [f"Found {len(results)} result(s) for '{query}':"]
        for r in results[:5]:
            summary_lines.append(f"- {r.get('title') or r.get('url')}: {r.get('description', '')[:120]}")
        summary = "\n".join(summary_lines)

        return TaskResult(
            success=True,
            output_path=output_path,
            artifacts=[output_path],
            data={
                "results": results,
                "summary": summary,
                "output": summary,
                "message": f"Found {len(results)} search result(s).",
                "output_path": output_path,
            },
        )

    async def _search_wikipedia(self, task: Task) -> TaskResult:
        raw_query = str(task.params.get("query") or task.description or "")
        query = raw_query.replace("wikipedia", "").replace("Wikipedia", "").strip()
        sentences = int(task.params.get("sentences", 3))
        if not query:
            return TaskResult(success=False, error="No Wikipedia topic provided.")

        def _wiki_sync() -> Dict[str, Any]:
            try:
                import wikipedia  # type: ignore
                summary = wikipedia.summary(query, sentences=sentences)
                page = wikipedia.page(query, auto_suggest=False)
                return {"title": page.title, "summary": summary, "url": page.url}
            except ImportError:
                pass

            # Wikipedia REST v1 + OpenSearch API fallback (uses requests)
            slug = urllib.parse.quote(query.replace(" ", "_"))
            rest_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
            resp = requests.get(rest_url, headers=_HEADERS, timeout=10)
            if resp.status_code == 404:
                hits = self._wikipedia_opensearch_sync(query, 1)
                if not hits:
                    raise ValueError(f"Wikipedia page not found for '{query}'")
                best_title = hits[0]["title"]
                rest_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(best_title.replace(' ', '_'))}"
                resp = requests.get(rest_url, headers=_HEADERS, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            extract = str(data.get("extract") or "")
            if sentences > 0 and extract:
                parts = [s.strip() for s in extract.split(". ") if s.strip()]
                extract = ". ".join(parts[:sentences]) + ("." if parts else "")
            page_url = (
                ((data.get("content_urls") or {}).get("desktop") or {}).get("page")
                or f"https://en.wikipedia.org/wiki/{slug}"
            )
            return {
                "title": data.get("title", query),
                "summary": extract,
                "url": page_url,
            }

        try:
            wiki_data = await asyncio.to_thread(_wiki_sync)
        except Exception as exc:
            return TaskResult(success=False, error=f"Wikipedia lookup failed: {exc}")

        return TaskResult(
            success=True,
            data={
                **wiki_data,
                "output": wiki_data["summary"],
                "text": wiki_data["summary"],
                "message": f"Wikipedia summary retrieved for '{wiki_data['title']}'.",
            },
        )

    async def _scrape_url(self, task: Task) -> TaskResult:
        url = str(task.params.get("url") or "").strip()
        if not url:
            return TaskResult(success=False, error="No URL provided for scraping")
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return TaskResult(success=False, error=f"Unsupported URL scheme: {parsed.scheme}")

        def _scrape_sync() -> Dict[str, Any]:
            response = requests.get(url, headers=_HEADERS, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            title = soup.title.get_text(strip=True) if soup.title else ""
            paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
            text = "\n".join(paragraphs[:15])
            return {"url": url, "title": title, "text_content": paragraphs[:10], "text": text}

        try:
            scraped = await asyncio.to_thread(_scrape_sync)
        except Exception as exc:
            return TaskResult(success=False, error=f"Scraping failed: {exc}")

        return TaskResult(
            success=True,
            data={
                **scraped,
                "summary": scraped["text"][:500],
                "output": scraped["text"],
                "message": f"Scraped {len(scraped['text_content'])} paragraph(s) from {url}.",
            },
        )
