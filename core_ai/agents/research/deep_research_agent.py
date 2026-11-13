import asyncio
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


class DeepResearchAgent(BaseAgent):
    """Performs topic query expansion, concurrent multi-source scraping, and synthesis."""

    def __init__(self, agent_id: str = "deep-research-001", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config or {})
        self.name = "Deep Research Agent"
        self.category = "research"
        self.description = "Performs deep topic analysis, parallel search, and LLM synthesis."
        self.capabilities = [
            "deep_research",
            "social_synthesis",
            "multi_source_scrape",
        ]
        self.ai_manager = None

    async def can_handle(self, task: Task) -> bool:
        keywords = [
            "deep research", "synthesize", "comprehensive analysis",
            "market research", "in-depth", "multi-source",
        ]
        return any(kw in (task.description or "").lower() for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        try:
            topic = str(task.params.get("query") or task.description or "").strip()
            if not topic:
                return TaskResult(success=False, error="No research topic provided.")

            queries = self._generate_search_queries(topic)
            raw_data = await self._parallel_search_and_scrape(queries)
            synthesis, used_llm = await self._synthesize_results(topic, raw_data)

            output_file = self._resolve_output_path(
                task,
                default_filename=f"deep_research_{task.task_id[:8]}.md",
            )
            from pathlib import Path

            await asyncio.to_thread(
                Path(output_file).write_text, synthesis, encoding="utf-8"
            )

            return TaskResult(
                success=True,
                output_path=output_file,
                artifacts=[output_file],
                data={
                    "synthesis": synthesis,
                    "summary": synthesis[:600],
                    "output": synthesis,
                    "text": synthesis,
                    "raw_data_count": len(raw_data),
                    "sources": [item.get("url") for item in raw_data if item.get("url")],
                    "message": f"Deep research completed across {len(raw_data)} source(s).",
                },
                metadata={"used_llm": used_llm, "queries": queries},
            )
        except Exception as exc:
            logger.error("[%s] DeepResearch execution failed: %s", self.agent_id, exc, exc_info=True)
            return TaskResult(success=False, error=str(exc))

    @staticmethod
    def _generate_search_queries(prompt: str) -> List[str]:
        clean = (
            prompt.lower()
            .replace("deep research", "")
            .replace("synthesize", "")
            .replace("comprehensive analysis", "")
            .strip()
        ) or prompt.strip()
        return [
            f"{clean} latest developments",
            f"{clean} overview guide",
            f"{clean} analysis trends",
        ]

    def _search_urls_sync(self, query: str) -> List[Dict[str, str]]:
        # 1. googlesearch-python if available
        try:
            from googlesearch import search as g_search
            items = []
            for res in g_search(query, num_results=2, advanced=True):
                items.append(
                    {
                        "url": getattr(res, "url", str(res)),
                        "title": getattr(res, "title", "") or "",
                        "snippet": getattr(res, "description", "") or "",
                    }
                )
            if items:
                return items
        except Exception:
            pass

        # 2. DuckDuckGo HTML fallback
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
            resp = requests.get(url, headers=_HEADERS, timeout=8)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            items = []
            for item in soup.select(".result"):
                a = item.select_one("a.result__a")
                if not a:
                    continue
                href = a.get("href") or ""
                if href.startswith("http"):
                    sn = item.select_one(".result__snippet")
                    items.append(
                        {
                            "url": href,
                            "title": a.get_text(" ", strip=True),
                            "snippet": sn.get_text(" ", strip=True) if sn else "",
                        }
                    )
                if len(items) >= 2:
                    break
            return items
        except Exception as exc:
            logger.debug("Search query %r failed: %s", query, exc)
            return []

    def _scrape_text_sync(self, url: str) -> str:
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return ""
            response = requests.get(url, headers=_HEADERS, timeout=6)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                for tag in soup(["script", "style", "noscript"]):
                    tag.decompose()
                return " ".join(soup.stripped_strings)
            return ""
        except Exception:
            return ""

    async def _parallel_search_and_scrape(self, queries: List[str]) -> List[Dict[str, Any]]:
        search_batches = await asyncio.gather(
            *(asyncio.to_thread(self._search_urls_sync, q) for q in queries),
            return_exceptions=True,
        )

        candidates: List[Dict[str, str]] = []
        visited = set()
        for batch in search_batches:
            if isinstance(batch, Exception):
                continue
            for item in batch:
                url = item.get("url", "")
                if url and url not in visited:
                    visited.add(url)
                    candidates.append(item)

        scrape_texts = await asyncio.gather(
            *(asyncio.to_thread(self._scrape_text_sync, item["url"]) for item in candidates),
            return_exceptions=True,
        )

        all_results: List[Dict[str, Any]] = []
        for item, content in zip(candidates, scrape_texts):
            body = "" if isinstance(content, Exception) else str(content or "")
            if not body:
                body = item.get("snippet", "")
            all_results.append(
                {
                    "url": item["url"],
                    "title": item.get("title", ""),
                    "content": body[:1200],
                }
            )
        return all_results

    async def _synthesize_results(self, original_prompt: str, raw_data: List[Dict[str, Any]]) -> tuple[str, bool]:
        context_lines = [f"Topic: {original_prompt}\n\nSources:"]
        for idx, item in enumerate(raw_data, start=1):
            context_lines.append(
                f"Source {idx} ({item.get('title') or item.get('url', 'unknown')} - {item.get('url', '')}):\n"
                f"{item.get('content', '')}\n"
            )
        context = "\n".join(context_lines)

        prompt = (
            "You are an elite research analyst. Synthesize the scraped sources into a concise, "
            "factual Markdown report addressing the topic below.\n"
            f'Topic: "{original_prompt}"\n\n'
            "Include:\n- Executive Summary\n- Key Findings\n- Sources (URLs)\n\n"
            f"Scraped Data:\n{context}"
        )

        # Support injected self.ai_manager or UnifiedChatInterface via self.chat_llm
        if self.ai_manager is not None and self.llm is None:
            self.llm = self.ai_manager

        llm_response = await self.chat_llm(
            prompt,
            system_message="You are an elite research analyst producing concise structured Markdown reports.",
            max_tokens=1500,
            temperature=0.3,
        )
        if llm_response:
            return llm_response, True

        # Deterministic structured fallback when offline or LLM unavailable
        findings = []
        sources = []
        for idx, item in enumerate(raw_data, start=1):
            title = item.get("title") or f"Source {idx}"
            url = item.get("url", "")
            snippet = (item.get("content") or "").strip()[:300]
            if snippet:
                findings.append(f"- **{title}**: {snippet}")
            if url:
                sources.append(f"- [{title}]({url})")

        fallback_md = (
            f"# Deep Research Report: {original_prompt}\n\n"
            f"## Executive Summary\n"
            f"Collected {len(raw_data)} source(s) for `{original_prompt}`.\n\n"
            f"## Key Findings\n"
            + ("\n".join(findings) if findings else "- No live web sources retrieved (offline or search limited).")
            + "\n\n## Sources\n"
            + ("\n".join(sources) if sources else "- None")
        )
        return fallback_md, False
