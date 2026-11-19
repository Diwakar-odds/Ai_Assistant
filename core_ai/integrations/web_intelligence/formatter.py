"""
Context Formatter for Web Grounding.
Produces structured [LIVE WEB CONTEXT] prompt blocks designed to enforce
strict grounding for both cloud LLMs and local quantized GGUF models.
"""

from datetime import datetime
from typing import List
from .models import SearchResult


class ContextFormatter:
    """Formats raw search results into an authoritative LLM grounding block."""

    @staticmethod
    def format_grounding_block(query: str, results: List[SearchResult]) -> str:
        """
        Creates an explicit grounding block with instructions to prevent hallucination.
        """
        if not results:
            return ""

        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"[LIVE WEB SEARCH CONTEXT — Retrieved at {timestamp_str}]",
            "CRITICAL INSTRUCTIONS FOR AI ASSISTANT:",
            "1. The information below was retrieved live from the internet moments ago.",
            "2. You MUST use this real-time data to answer the user's factual questions (e.g. current prices, rates, weather, sports scores, news).",
            "3. If this live context contradicts your pre-trained model cutoff or internal memory, ALWAYS trust and cite this live data.",
            "4. Answer naturally, concisely, and cite source titles or URLs when relevant.",
            f"User Query: \"{query}\"\n",
            "VERIFIED WEB RESULTS:"
        ]

        for idx, res in enumerate(results, 1):
            lines.append(f"[{idx}] {res.title}")
            lines.append(f"    Source: {res.source} | URL: {res.url}")
            lines.append(f"    Snippet: {res.snippet}")

        lines.append("[END LIVE WEB SEARCH CONTEXT]\n")

        return "\n".join(lines)

    @staticmethod
    def format_offline_degradation_block() -> str:
        """Note injected when the system is offline or web search fails."""
        return (
            "[SYSTEM NOTICE: Real-time web search is currently unavailable (offline mode). "
            "Please answer using your best pre-trained knowledge, and explicitly inform the user "
            "that live data could not be verified.]"
        )
