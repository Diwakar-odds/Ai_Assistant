"""
Semantic Vector Intent Router for Web Intelligence Subsystem.
Uses SentenceTransformer ('all-MiniLM-L6-v2') embeddings and cosine similarity
against high-density multilingual prototype clusters.
Completely replaces brittle regex and hardcoded keyword matching.
"""

import logging
import time
from typing import Dict, List, Tuple, Optional
import numpy as np

from .models import WebQueryMode
from core_ai.ai.shared_embedder import (
    encode_text,
    encode_batch,
    cosine_similarity,
    is_embedder_available,
)

logger = logging.getLogger(__name__)


class SemanticVectorRouter:
    """
    Classifies user queries into WebQueryModes using dense vector representations
    and cluster centroid / kNN cosine similarity.
    """

    # Semantic prototypes across English, Hindi, and Hinglish
    _PROTOTYPES: Dict[WebQueryMode, List[str]] = {
        WebQueryMode.BROWSER_ACTION: [
            "open google and search for python tutorials",
            "search this on chrome browser",
            "open youtube and search for songs",
            "launch web browser to find documentation",
            "google pe search karo aur dikhao",
            "chrome browser me open karo",
            "youtube par video search karo",
            "browser me khol ke dikhao",
            "search on google chrome",
            "browse to this website on edge",
        ],
        WebQueryMode.BACKGROUND_GROUNDING: [
            # Commodities & Finance
            "what is the price of gold and silver today",
            "current petrol and diesel rate in delhi",
            "bitcoin and crypto live market price",
            "stock market nifty sensex current level",
            "today gold bhav and silver price in india",
            "aaj sone ka bhav kitna hai",
            "petrol ka kya rate hai aaj",
            "share market aaj kitna upar ya niche hai",
            "dollar to rupee current exchange rate",
            # Sports & Live Scores
            "live cricket score and match schedule",
            "who won the match yesterday",
            "last india cricket match against which team",
            "ipl points table and upcoming matches",
            "kal ka cricket match kaun jeeta",
            "india ka agla match kab aur kiske sath hai",
            "football world cup live tournament score",
            # Weather & Environment
            "current weather and temperature outside",
            "will it rain today in mumbai",
            "aaj ka mausam kaisa rahega aur barish hogi kya",
            "aqi air pollution index right now",
            # News & Recency
            "latest breaking news and current affairs",
            "recent events happening today",
            "who is the current prime minister of uk",
            "current president of united states",
            "aaj ki taaza khabar aur breaking news",
            "kya naya hua aaj desh aur duniya me",
            "who is the current ceo of openai",
            # Developer, Software Versions & Release Dates
            "when was python 3.13 released and release date",
            "latest release features and changelog of bun node next.js",
            "release date and schedule of python 3.14",
            "is python 3.13 free threaded gil available",
            "what is the latest version of react or angular",
            "current status of github actions outage and uptime",
            "official documentation for library api endpoints",
        ],
        WebQueryMode.DEEP_RESEARCH: [
            "deep research on system architecture and design",
            "comprehensive performance benchmark comparison between runtime engines",
            "in depth analysis of memory leak and race conditions",
            "detailed architectural tradeoffs and benchmarks",
            "comprehensive technical study of database engines",
            "thorough investigation of latency bottlenecks and profiling",
            "deep dive into kubernetes cilium ebpf networking",
            "synthesize comprehensive multi source analysis on this topic",
            "conduct deep research on uvloop vs standard asyncio",
        ],
        WebQueryMode.DIRECT_CHAT: [
            # Coding & Technical
            "write a python function to reverse a linked list",
            "help me debug this javascript error",
            "explain how neural networks work in simple terms",
            "write a sql query to join two tables",
            "python code likh kar dikhao",
            "is code me kya bug hai samjhao",
            # Creative Writing & Reasoning
            "write an essay on climate change",
            "compose a poem about the sunrise",
            "tell me a funny story or joke",
            "koi acchi kahani ya chutkula sunao",
            "kavita likho dosti ke upar",
            # Conversational Greetings & Identity
            "hello how are you doing today",
            "who are you and what can you do",
            "good morning hope you have a nice day",
            "tum kaun ho aur kya kar sakte ho",
            "kya haal chaal hai",
            "thank you so much for your help",
        ],
    }

    # Direct local system commands (volume, apps, power)
    _SYSTEM_PROTOTYPES: List[str] = [
        "increase or decrease system volume",
        "mute audio or turn volume up",
        "close this application or window",
        "open notepad or open calculator",
        "shut down or restart the computer",
        "lock the screen or sleep",
        "awaaz badhao ya mute karo",
        "calculator kholo ya notepad kholo",
        "screen lock karo ya shutdown karo",
    ]

    # Temporal local clock queries (handled by OS clock instantly, no search needed)
    _TEMPORAL_PROTOTYPES: List[str] = [
        "what is today's date",
        "what is the current time right now",
        "what day of the week is it today",
        "aaj date kya hai",
        "aaj konsi tarikh hai",
        "aaj kya din hai aur time kya hua",
        "current system clock date and time",
    ]

    def __init__(self):
        self._is_initialized = False
        self._cluster_embeddings: Dict[str, np.ndarray] = {}
        self._cluster_centroids: Dict[str, np.ndarray] = {}

    def _ensure_embeddings(self) -> bool:
        """Lazily pre-computes and caches prototype embeddings on first access."""
        if self._is_initialized:
            return True

        if not is_embedder_available():
            logger.warning("Shared embedder unavailable for SemanticVectorRouter.")
            return False

        try:
            t0 = time.time()
            all_clusters = {
                WebQueryMode.BROWSER_ACTION.value: self._PROTOTYPES[WebQueryMode.BROWSER_ACTION],
                WebQueryMode.BACKGROUND_GROUNDING.value: self._PROTOTYPES[WebQueryMode.BACKGROUND_GROUNDING],
                WebQueryMode.DIRECT_CHAT.value: self._PROTOTYPES[WebQueryMode.DIRECT_CHAT],
                "system_command": self._SYSTEM_PROTOTYPES,
                "temporal_clock": self._TEMPORAL_PROTOTYPES,
            }

            for key, texts in all_clusters.items():
                vecs = encode_batch(texts, normalize=True)
                if vecs is not None and len(vecs) > 0:
                    self._cluster_embeddings[key] = vecs
                    # Centroid: mean vector normalized
                    mean_vec = np.mean(vecs, axis=0)
                    norm = np.linalg.norm(mean_vec)
                    self._cluster_centroids[key] = (mean_vec / max(norm, 1e-12)).astype(np.float32)

            self._is_initialized = True
            elapsed = (time.time() - t0) * 1000
            logger.info(f"✅ SemanticVectorRouter initialized ({elapsed:.1f}ms, {len(self._cluster_embeddings)} clusters).")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize SemanticVectorRouter embeddings: {e}")
            return False

    def route(self, query: str) -> Tuple[WebQueryMode, float, str]:
        """
        Routes user query using dense vector cosine similarity.
        Returns:
            (mode: WebQueryMode, confidence: float, search_query: str)
        """
        clean_query = (query or "").strip()
        if not clean_query:
            return WebQueryMode.DIRECT_CHAT, 1.0, ""

        if not self._ensure_embeddings():
            # Fallback to direct chat if embedder failed
            return WebQueryMode.DIRECT_CHAT, 0.5, clean_query

        # 1. Encode incoming user query
        query_vec = encode_text(clean_query, normalize=True)
        if query_vec is None:
            return WebQueryMode.DIRECT_CHAT, 0.5, clean_query

        # 2. Check Temporal Clock first (Highest precedence for zero-latency system date/time)
        temp_vecs = self._cluster_embeddings.get("temporal_clock")
        if temp_vecs is not None:
            temp_sims = cosine_similarity(query_vec, temp_vecs)
            max_temp = float(np.max(temp_sims))
            if max_temp >= 0.72:
                logger.debug(f"SemanticVectorRouter: Temporal clock matched ({max_temp:.2f})")
                return WebQueryMode.DIRECT_CHAT, max_temp, clean_query

        # 3. Check System Command (volume, app open/close)
        sys_vecs = self._cluster_embeddings.get("system_command")
        if sys_vecs is not None:
            sys_sims = cosine_similarity(query_vec, sys_vecs)
            max_sys = float(np.max(sys_sims))
            if max_sys >= 0.72:
                logger.debug(f"SemanticVectorRouter: Local system command matched ({max_sys:.2f})")
                return WebQueryMode.DIRECT_CHAT, max_sys, clean_query

        # 4. Score core clusters (kNN top-3 average + max similarity)
        scores: Dict[str, float] = {}
        for key in [
            WebQueryMode.BROWSER_ACTION.value,
            WebQueryMode.BACKGROUND_GROUNDING.value,
            WebQueryMode.DEEP_RESEARCH.value,
            WebQueryMode.DIRECT_CHAT.value,
        ]:
            vecs = self._cluster_embeddings.get(key)
            if vecs is not None:
                sims = cosine_similarity(query_vec, vecs)
                # Take top-2 average similarity for robustness
                top2_avg = float(np.mean(np.sort(sims)[-2:]))
                max_sim = float(np.max(sims))
                # Weighted blend: 60% top similarity + 40% cluster cohesion
                scores[key] = (0.6 * max_sim) + (0.4 * top2_avg)

        # 5. Determine winning cluster
        best_mode_str = max(scores, key=scores.get)
        best_score = scores[best_mode_str]

        logger.debug(f"SemanticVectorRouter scores for '{clean_query[:30]}...': {scores}")

        # Deep Research has high priority when explicit research/benchmarking is requested
        if best_mode_str == WebQueryMode.DEEP_RESEARCH.value and best_score >= 0.52:
            return WebQueryMode.DEEP_RESEARCH, best_score, clean_query

        # Thresholding for BACKGROUND_GROUNDING (must exceed confidence threshold)
        if best_mode_str == WebQueryMode.BACKGROUND_GROUNDING.value:
            if best_score >= 0.52:
                return WebQueryMode.BACKGROUND_GROUNDING, best_score, clean_query
            else:
                return WebQueryMode.DIRECT_CHAT, best_score, clean_query

        if best_mode_str == WebQueryMode.BROWSER_ACTION.value:
            if best_score >= 0.65:
                return WebQueryMode.BROWSER_ACTION, best_score, clean_query

        return WebQueryMode.DIRECT_CHAT, best_score, clean_query
