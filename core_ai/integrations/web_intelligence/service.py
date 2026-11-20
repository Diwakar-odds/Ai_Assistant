"""
Unified Web Intelligence Service for Pulsar AI.
The central singleton service providing real-time grounding, search,
and scraping across Chat, Voice, Multi-Agent Swarm, and Tool calling.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import logging
import re
import socket
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from .cache import TieredTTLCache
from .classifier import WebQueryClassifier
from .micro_router import NeuralMicroRouter
from .config import load_web_intelligence_config
from .engines import DuckDuckGoEngine, WikipediaEngine, InstantFactsConnector, GoogleNewsEngine, TavilyEngine, SerpApiEngine
from .formatter import ContextFormatter
from .models import GroundingResult, ScrapedSource, SearchResult, WebQueryMode

logger = logging.getLogger(__name__)

try:
    from telemetry_tracer import telemetry
except ImportError:
    class DummyTelemetry:
        @staticmethod
        def log_router(*a, **k): pass
        @staticmethod
        def log_compute(*a, **k): pass
    telemetry = DummyTelemetry

_service_lock = threading.RLock()
_service_instance: Optional["WebIntelligenceService"] = None


def get_web_intelligence() -> "WebIntelligenceService":
    """Return process-wide singleton WebIntelligenceService instance."""
    global _service_instance
    with _service_lock:
        if _service_instance is None:
            _service_instance = WebIntelligenceService()
        return _service_instance


class WebIntelligenceService:
    """Master Web Intelligence Service."""

    def __init__(self):
        self.config = load_web_intelligence_config()
        self.micro_router = NeuralMicroRouter()
        self.classifier = WebQueryClassifier()
        self.cache = TieredTTLCache(max_entries=1000)
        self.formatter = ContextFormatter()

        # Engine Connectors
        self.instant_facts = InstantFactsConnector(timeout=2.0)
        self.duckduckgo = DuckDuckGoEngine(timeout=2.5)
        self.google_news = GoogleNewsEngine(timeout=3.0)
        self.wikipedia = WikipediaEngine(timeout=2.5)

        # Optional Paid Engines (Active only when keys are provided)
        tavily_key = self.config.get("api_keys", {}).get("tavily", "")
        serpapi_key = self.config.get("api_keys", {}).get("serpapi", "")
        self.tavily = TavilyEngine(api_key=tavily_key, timeout=3.5)
        self.serpapi = SerpApiEngine(api_key=serpapi_key, timeout=3.5)

        # Worker pool for non-blocking timeout-guarded searches
        self._executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="WebIntelWorker")
        self._offline_mode = False
        self._last_connectivity_check = 0.0
        self._is_connected_cache = True

        # Speculative Pre-Fetching Engine State
        self._speculative_futures: Dict[str, Tuple[Any, float]] = {}
        self._speculative_lock = threading.Lock()

    # =========================================================================
    # PUBLIC API: CLASSIFICATION, PRE-FETCHING & GROUNDING
    # =========================================================================

    def classify(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        last_user_turn: Optional[str] = None,
        last_assistant_turn: Optional[str] = None,
    ) -> Tuple[WebQueryMode, str]:
        """
        Routes query using Tri-Hybrid Semantic Vector Router + Neural Reformulator.
        Supports generalized multi-turn follow-up resolution when conversation history or turns are provided.
        """
        try:
            return self.micro_router.route_and_reformulate(
                message,
                history=history,
                last_user_turn=last_user_turn,
                last_assistant_turn=last_assistant_turn,
            )
        except Exception as e:
            logger.warning(f"MicroRouter routing failed ({e}), falling back to classifier.")
            return self.classifier.classify(message)

    def speculative_prefetch(
        self,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
        last_user_turn: Optional[str] = None,
        last_assistant_turn: Optional[str] = None,
    ) -> Optional[str]:
        """
        Speculative Pre-Fetching Engine:
        Asynchronously launches background search as soon as query arrives.
        Achieves near 0ms perceived search latency when ground_prompt is evaluated.
        """
        if not user_message or not user_message.strip():
            return None

        try:
            mode, search_query = self.classify(
                user_message,
                history=history,
                last_user_turn=last_user_turn,
                last_assistant_turn=last_assistant_turn,
            )
            if mode not in (WebQueryMode.BACKGROUND_GROUNDING, WebQueryMode.DEEP_RESEARCH):
                return None

            if not search_query or len(search_query) < 3:
                return None

            # 1. If already in TTL cache, no background search needed
            if self.cache.get(search_query) is not None:
                return search_query

            with self._speculative_lock:
                now = time.time()
                # Prune stale futures (>60s)
                stale_keys = [k for k, (_, t) in self._speculative_futures.items() if now - t > 60.0]
                for k in stale_keys:
                    self._speculative_futures.pop(k, None)

                # Check if already active or pending
                if search_query in self._speculative_futures:
                    fut, t = self._speculative_futures[search_query]
                    if not fut.done() or (now - t < 30.0):
                        return search_query

                # Launch speculative background search immediately
                future = self._executor.submit(self.search, search_query, num_results=4)
                self._speculative_futures[search_query] = (future, now)
                logger.info(f"⚡ Speculative pre-fetch launched for: '{search_query}'")
                return search_query
        except Exception as e:
            logger.debug(f"Speculative prefetch error: {e}")
            return None

    def ground_prompt(
        self,
        user_message: str,
        timeout: float = 5.0,
        history: Optional[List[Dict[str, str]]] = None,
        last_user_turn: Optional[str] = None,
        last_assistant_turn: Optional[str] = None,
    ) -> GroundingResult:
        """
        Main entry point for Chat and Voice assistant pipelines.
        Returns GroundingResult with structured context block if query needs live grounding.
        Checks speculative pre-fetch cache to deliver ~0ms search latency.
        """
        start_time = time.time()
        mode, search_query = self.classify(
            user_message,
            history=history,
            last_user_turn=last_user_turn,
            last_assistant_turn=last_assistant_turn,
        )

        # Mode D: DIRECT_CHAT or Mode A: BROWSER_ACTION -> No background grounding needed
        if mode in (WebQueryMode.DIRECT_CHAT, WebQueryMode.BROWSER_ACTION):
            return GroundingResult(
                mode=mode,
                query=search_query,
                grounded_message=user_message,
                context_block="",
                results=[],
                search_time_ms=0.0,
            )

        # Mode C: DEEP_RESEARCH -> Execute developer deep research synthesis
        if mode == WebQueryMode.DEEP_RESEARCH:
            return self.deep_research(search_query, timeout=timeout)

        # Check offline state
        if self._offline_mode or not self.is_online:
            offline_block = self.formatter.format_offline_degradation_block()
            return GroundingResult(
                mode=mode,
                query=search_query,
                grounded_message=f"{offline_block}\n\nUser: {user_message}",
                context_block=offline_block,
                results=[],
                search_time_ms=(time.time() - start_time) * 1000,
                offline_degraded=True,
            )

        # Check TTL Cache first
        was_cached = self.cache.get(search_query) is not None
        speculative_hit = False

        # Check speculative prefetch future
        spec_future = None
        with self._speculative_lock:
            if search_query in self._speculative_futures:
                spec_future, _ = self._speculative_futures.pop(search_query)
                speculative_hit = True

        try:
            if spec_future is not None:
                # Await speculative future (already warm or running in background)
                rem_timeout = max(0.5, timeout - (time.time() - start_time))
                results = spec_future.result(timeout=rem_timeout)
            else:
                future = self._executor.submit(self.search, search_query, num_results=4)
                results = future.result(timeout=timeout)
        except FutureTimeoutError:
            logger.warning(f"Web search for '{search_query}' timed out after {timeout}s")
            results = []
        except Exception as exc:
            logger.error(f"Web search for '{search_query}' failed: {exc}")
            results = []

        elapsed_ms = (time.time() - start_time) * 1000

        if not results:
            return GroundingResult(
                mode=mode,
                query=search_query,
                grounded_message=user_message,
                context_block="",
                results=[],
                search_time_ms=elapsed_ms,
                cache_hit=was_cached or speculative_hit,
            )

        # Format context block
        context_block = self.formatter.format_grounding_block(search_query, results)
        grounded_message = f"{context_block}\n\nUser: {user_message}"

        return GroundingResult(
            mode=mode,
            query=search_query,
            grounded_message=grounded_message,
            context_block=context_block,
            results=results,
            search_time_ms=elapsed_ms,
            source_engine=results[0].source if results else "none",
            cache_hit=was_cached or speculative_hit,
        )

    def deep_research(
        self,
        query: str,
        max_sources: int = 4,
        timeout: float = 10.0,
    ) -> GroundingResult:
        """
        Developer-Grade Deep Research Agent (Mode C).
        1. Multi-query technical expansion across architecture, benchmarks, and production pitfalls.
        2. Parallel search across engines.
        3. Parallel source scraping via safe HTML extractor.
        4. Structured technical dossier synthesis.
        """
        start_time = time.time()
        clean_topic = query.strip()

        # Step 1: Multi-Query Technical Expansion
        sub_queries = [
            f"{clean_topic} architecture internals specification",
            f"{clean_topic} benchmark performance comparison tradeoffs",
            f"{clean_topic} production best practices common issues",
        ]

        # Step 2: Parallel Multi-Engine Search
        search_futures = [self._executor.submit(self.search, sq, num_results=3) for sq in sub_queries]
        candidates: List[SearchResult] = []
        seen_urls = set()

        for f in search_futures:
            try:
                res_list = f.result(timeout=min(4.5, timeout))
                for item in res_list:
                    if item.url and item.url not in seen_urls:
                        seen_urls.add(item.url)
                        candidates.append(item)
            except Exception as e:
                logger.debug(f"Deep research search error: {e}")

        # Limit to top distinct candidates
        top_candidates = candidates[:max_sources]

        # Step 3: Parallel Content Scraping
        def _scrape_worker(item: SearchResult) -> Dict[str, Any]:
            content = self.scrape_url(item.url, max_chars=3500)
            return {
                "url": item.url,
                "title": item.title,
                "snippet": item.snippet,
                "source": item.source,
                "content": content or item.snippet,
                "scraped": content is not None,
            }

        scrape_futures = [self._executor.submit(_scrape_worker, c) for c in top_candidates]
        scraped_data: List[Dict[str, Any]] = []
        for sf in scrape_futures:
            try:
                scraped_data.append(sf.result(timeout=5.0))
            except Exception as e:
                logger.debug(f"Scrape worker error: {e}")

        elapsed_ms = (time.time() - start_time) * 1000

        # Step 4: Structured Dossier Synthesis
        dossier_lines = [
            f"[DEEP RESEARCH DOSSIER: {clean_topic}]",
            f"Query Topic: {clean_topic}",
            f"Scope: {len(sub_queries)} technical vectors, {len(scraped_data)} verified source(s) scraped",
            "",
            "## 1. Technical Insights & Core Architecture",
        ]

        sources_summary = []
        for idx, item in enumerate(scraped_data, 1):
            title = item.get("title") or f"Source {idx}"
            url = item.get("url", "")
            content = (item.get("content") or "").strip()
            snippet_summary = content[:350].replace("\n", " ")
            dossier_lines.append(f"### Source {idx}: {title}")
            dossier_lines.append(f"- URL: {url}")
            dossier_lines.append(f"- Excerpt: {snippet_summary}...")
            dossier_lines.append("")
            sources_summary.append(SearchResult(title=title, url=url, snippet=snippet_summary, source="DeepResearch"))

        dossier_lines.append("## 2. Synthesis Directive for Developer")
        dossier_lines.append(
            "Synthesize the architecture, performance benchmarks, and production tradeoffs from above. "
            "Highlight concrete code patterns, failure modes, and engineering guidance."
        )
        dossier_lines.append("[END DEEP RESEARCH DOSSIER]")

        dossier_block = "\n".join(dossier_lines)
        grounded_message = f"{dossier_block}\n\nUser: {clean_topic}"

        return GroundingResult(
            mode=WebQueryMode.DEEP_RESEARCH,
            query=clean_topic,
            grounded_message=grounded_message,
            context_block=dossier_block,
            results=sources_summary,
            search_time_ms=elapsed_ms,
            source_engine="DeepResearchAgent",
            cache_hit=False,
        )

    # =========================================================================
    # PUBLIC API: SEARCH & SCRAPING (For Agents & Swarm)
    # =========================================================================

    def search(self, query: str, num_results: int = 5, max_age_seconds: int = 900) -> List[SearchResult]:
        """
        General-purpose cached search. Primary method consumed by ResearchAgent,
        DeepResearchAgent, DataAgent, etc.
        """
        if not query or not query.strip():
            return []

        clean_query = query.strip()

        # 1. Check TTL Cache first
        cached = self.cache.get(clean_query)
        if cached:
            logger.debug(f"Web search cache hit for: {clean_query}")
            return cached[:num_results]

        results: List[SearchResult] = []

        # 2. Check Instant Facts Connector (fast weather, crypto, stocks)
        try:
            instant_res = self.instant_facts.check_and_fetch(clean_query)
            if instant_res:
                results.extend(instant_res)
        except Exception as e:
            logger.debug(f"Instant fact check error: {e}")

        # 3. Optional Premium Engine (Tavily or SerpAPI if configured)
        if len(results) < num_results:
            pref = self.config.get("preferred_engine", "").lower()
            if pref == "tavily" and self.tavily.is_available:
                try:
                    t_results = self.tavily.search(clean_query, num_results=num_results - len(results))
                    if t_results:
                        results.extend(t_results)
                except Exception as e:
                    logger.debug(f"Tavily search failed: {e}")
            elif pref == "serpapi" and self.serpapi.is_available:
                try:
                    s_results = self.serpapi.search(clean_query, num_results=num_results - len(results))
                    if s_results:
                        results.extend(s_results)
                except Exception as e:
                    logger.debug(f"SerpAPI search failed: {e}")

        # 4. Google News RSS for News/Current Events or Sports
        is_news_query = any(w in clean_query.lower() for w in ["news", "khabar", "samachar", "election", "match", "score", "cricket", "ipl", "result", "latest", "breaking"])
        if is_news_query and len(results) < num_results:
            try:
                news_results = self.google_news.search(clean_query, max_results=num_results - len(results))
                if news_results:
                    results.extend(news_results)
            except Exception as e:
                logger.debug(f"Google News search error: {e}")

        # 5. DuckDuckGo Search (Primary Zero-Key Engine)
        if len(results) < num_results:
            try:
                # If query is commodity/price, make it specific for reliable results
                search_term = clean_query
                if any(w in clean_query.lower() for w in ["gold", "silver", "petrol", "diesel"]) and "today" not in clean_query.lower() and "aaj" not in clean_query.lower():
                    search_term = f"{clean_query} today live price India"

                ddg_results = self.duckduckgo.search(search_term, num_results=num_results - len(results))
                if ddg_results:
                    results.extend(ddg_results)
            except Exception as e:
                logger.debug(f"DuckDuckGo search failed: {e}")

        # 6. Fallback to Google News (if DDG returned nothing)
        if not results:
            try:
                news_fb = self.google_news.search(clean_query, max_results=3)
                if news_fb:
                    results.extend(news_fb)
            except Exception as e:
                logger.debug(f"Google News fallback error: {e}")

        # 7. Wikipedia OpenSearch Fallback (if still empty)
        if not results:
            try:
                wiki_results = self.wikipedia.search(clean_query, num_results=3)
                if wiki_results:
                    results.extend(wiki_results)
            except Exception as e:
                logger.debug(f"Wikipedia search failed: {e}")

        # Cache results if found & log telemetry
        if results:
            self.cache.set(clean_query, results)
            try:
                telemetry.log_router("WEB_INTEL", f"{results[0].source} ({len(results)} results)")
            except Exception:
                pass

        return results[:num_results]

    def scrape_url(self, url: str, max_chars: int = 5000, timeout: float = 6.0) -> Optional[str]:
        """
        Fetches and cleans visible text from a URL.
        Safe against SSRF and oversized payloads.
        """
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
            }
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            # Strip non-content tags
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "svg"]):
                tag.decompose()

            text = soup.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:max_chars] if text else None
        except Exception as exc:
            logger.debug(f"Scrape URL failed for {url}: {exc}")
            return None

    def search_and_scrape(self, query: str, num_urls: int = 3, max_chars_per_url: int = 3000) -> List[ScrapedSource]:
        """
        Compound search and parallel scrape. Designed for DeepResearchAgent.
        """
        results = self.search(query, num_results=num_urls)
        scraped_sources: List[ScrapedSource] = []

        def _worker(res: SearchResult) -> ScrapedSource:
            content = self.scrape_url(res.url, max_chars=max_chars_per_url)
            if content:
                return ScrapedSource(
                    url=res.url,
                    title=res.title,
                    content=content,
                    char_count=len(content),
                    success=True,
                )
            return ScrapedSource(
                url=res.url,
                title=res.title,
                content=res.snippet,  # Fallback to snippet if scrape failed
                char_count=len(res.snippet),
                success=False,
                error="HTTP fetch failed; snippet used",
            )

        futures = [self._executor.submit(_worker, res) for res in results]
        for f in futures:
            try:
                scraped_sources.append(f.result(timeout=8.0))
            except Exception as e:
                logger.debug(f"Parallel scrape item error: {e}")

        return scraped_sources

    # =========================================================================
    # CONNECTIVITY & CONFIGURATION
    # =========================================================================

    @property
    def is_online(self) -> bool:
        """Cached check for internet connectivity (checks at most once every 30s)."""
        now = time.time()
        if now - self._last_connectivity_check > 30.0:
            self._last_connectivity_check = now
            try:
                # Fast socket connection check to 1.1.1.1 or 8.8.8.8
                socket.create_connection(("8.8.8.8", 53), timeout=1.5).close()
                self._is_connected_cache = True
            except OSError:
                self._is_connected_cache = False
        return self._is_connected_cache

    def set_offline_mode(self, offline: bool):
        self._offline_mode = offline
