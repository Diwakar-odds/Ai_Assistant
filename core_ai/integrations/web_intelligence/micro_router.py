"""
Neural Micro-Router and Generalized Query Reformulator.
Extracts intent, resolves multi-turn follow-up queries across coding, systems, and developer domains,
and strips conversational Hinglish/English noise to produce high-precision search queries.
No brittle hardcoded dictionaries.
"""

from dataclasses import dataclass
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .models import WebQueryMode
from .semantic_router import SemanticVectorRouter
from .grammar import get_search_router_grammar

logger = logging.getLogger(__name__)

# Common conversational stop-phrases in Hindi / Hinglish / English that pollute search engines
_CONVERSATIONAL_STOP_WORDS = [
    r"\b(?:bhai|yaar|dost|bro|sir|please|plz)\b",
    r"\b(?:batao|bata|bataiye|dikhao|dikhaye|chahiye|janana\s+hai)\b",
    r"\b(?:kya\s+hai|kya\s+chal\s+raha\s+hai|kaise\s+karein|karein\s+kaise)\b",
    r"\b(?:hoga\s+kya|rahega\s+kya|aaj\s+ka\s+din)\b",
    r"\b(?:kiske\s+sa?th\s+tha|kiske\s+sa?th\s+hai|kab\s+tha|kab\s+hai)\b",
    r"\b(?:can\s+you\s+tell\s+me|tell\s+me|what\s+is\s+the|explain\s+to\s+me)\b",
    r"\b(?:mujhe\s+ye\s+batao|mujhe\s+batao|kripya\s+batao)\b",
]
_COMPILED_STOPS = [re.compile(p, re.IGNORECASE) for p in _CONVERSATIONAL_STOP_WORDS]

# Elliptical / Follow-up triggers in Hinglish and English
_FOLLOWUP_STARTERS = re.compile(
    r"^\s*(?:aur|and|what\s+about|how\s+about|what\s+if|usme|iska|iske|iski|unka|unke|unki|also|then|to|phir|fir|lekin|par|bhi)\b",
    re.IGNORECASE
)

_TARGET_SWAP_PATTERNS = [
    # "aur python me?", "and for golang?", "what about rust?"
    re.compile(r"^(?:aur|and|what\s+about|how\s+about)\s+(?:in|for|me|mein|pe|par)?\s*([a-zA-Z0-9_\.\-\+\#]+)\s*(?:me|mein|pe|par)?\??$", re.IGNORECASE),
    # "python me?", "golang ka?", "windows pe?"
    re.compile(r"^([a-zA-Z0-9_\.\-\+\#]+)\s+(?:me|mein|pe|par|ka|ke|ki|for|in)\??$", re.IGNORECASE),
]

_ASPECT_PATTERNS = [
    # "how to fix it?", "error kaise solve karein?"
    (re.compile(r"(?:how\s+to\s+fix|error\s+solve|kaise\s+theek\s+kare|fix\s+kaise\s+kare|solution\s+kya\s+hai)", re.IGNORECASE), "how to fix"),
    # "syntax kya hai?", "syntax example?"
    (re.compile(r"(?:syntax\s+kya\s+hai|syntax\s+example|code\s+example|kaise\s+likhe)", re.IGNORECASE), "syntax code example"),
    # "benchmark kaisa hai?", "performance comparison?"
    (re.compile(r"(?:benchmark|performance|speed|kitna\s+fast\s+hai|comparison)", re.IGNORECASE), "performance benchmark comparison"),
    # "internals / architecture"
    (re.compile(r"(?:internals|architecture|under\s+the\s+hood|kaise\s+kaam\s+karta\s+hai|working)", re.IGNORECASE), "architecture internals"),
    # "production deploy / best practices"
    (re.compile(r"(?:production|deploy|best\s+practices|scale|scaling)", re.IGNORECASE), "production best practices deployment"),
]


class FollowUpContextResolver:
    """
    Generalized Multi-Turn Context Resolver.
    Resolves elliptical developer follow-ups into complete standalone queries.
    """

    @classmethod
    def is_followup(cls, query: str) -> bool:
        """Determines if query is an elliptical or contextual follow-up."""
        q = (query or "").strip().lower()
        if not q:
            return False

        # Standalone action commands with imperative verbs are not follow-ups
        first_token = q.split()[0] if q.split() else ""
        if first_token in ("install", "setup", "download", "clone", "create", "write", "build", "run", "open", "close", "start", "stop"):
            return False

        # 1. Starts with connector
        if _FOLLOWUP_STARTERS.search(q):
            return True

        # 2. Target swap pattern (e.g. "in python?", "windows pe?")
        for pat in _TARGET_SWAP_PATTERNS:
            if pat.match(q):
                return True

        # 3. Pronoun / demonstrative reference
        if re.search(r"\b(?:it|this|that|these|those|yeh|woh|isme|usme|iska|iski)\b", q):
            return True

        # 4. Short fragment queries lacking an explicit subject
        words = q.split()
        if len(words) <= 5:
            if any(w in q for w in ["why", "kaise", "kyun", "kab", "kahan", "error", "issue", "fix", "difference", "vs"]):
                return True
            # Preposition or Postposition fragment: "docker ke andar?", "in docker?", "windows pe?", "on windows?"
            if re.search(r"\b(?:ke\s+andar|ke\s+sath|ke\s+baad|in|on|at|inside|under|with|for|me|mein|pe|par)\b", q):
                return True

        return False

    @classmethod
    def extract_focal_subject(cls, previous_turn: str) -> str:
        """Extracts the central technical subject / topic from the previous turn."""
        if not previous_turn:
            return ""

        text = previous_turn.strip()

        # Remove question framing and leading articles
        clean = re.sub(
            r"^(?:what\s+is\s+the|what\s+is|what\s+are\s+the|what\s+are|how\s+to|how\s+do\s+i|can\s+you\s+explain|explain|tell\s+me\s+about|kya\s+hota\s+hai|kaise\s+karein)\s+",
            "",
            text,
            flags=re.IGNORECASE
        )
        clean = re.sub(r"^(?:the|a|an)\s+", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"[?!.,;]+$", "", clean).strip()

        # Remove conversational filler words
        for pat in _COMPILED_STOPS:
            clean = pat.sub(" ", clean)

        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    @classmethod
    def resolve(
        cls,
        current_query: str,
        last_user_turn: Optional[str] = None,
        last_assistant_turn: Optional[str] = None
    ) -> str:
        """
        Synthesizes a complete standalone query by fusing focal context from prior turns.
        """
        raw = (current_query or "").strip()
        if not raw:
            return ""

        if not cls.is_followup(raw) or (not last_user_turn and not last_assistant_turn):
            return raw

        prior_context = cls.extract_focal_subject(last_user_turn or "")
        if not prior_context and last_assistant_turn:
            # Fallback: extract first line / title from assistant turn
            first_line = last_assistant_turn.strip().split("\n")[0]
            prior_context = cls.extract_focal_subject(first_line)[:80]

        if not prior_context:
            return raw

        q_clean = raw.strip()

        # Case A: Target Swap (e.g. Previous="Memory limit in Node.js v20", Current="aur Python me?")
        for pat in _TARGET_SWAP_PATTERNS:
            m = pat.match(q_clean)
            if m:
                new_target = m.group(1).strip()
                # Check if prior_context ends with "in <entity> [ver]" or "for <entity>"
                m_sub = re.search(r"^(.*?)\s+(?:in|for|on)\s+([a-zA-Z0-9_\.\-\+\#\s]+)$", prior_context, re.IGNORECASE)
                if m_sub:
                    base_predicate = m_sub.group(1).strip()
                    return f"{base_predicate} in {new_target}"

                # Otherwise replace last word/platform token
                words = prior_context.split()
                if len(words) >= 2:
                    base_predicate = " ".join(words[:-1])
                    return f"{base_predicate} in {new_target}"
                return f"{prior_context} in {new_target}"

        # Case B: Aspect / How-to / Fix / Benchmark follow-up
        for pat, aspect_prefix in _ASPECT_PATTERNS:
            if pat.search(q_clean):
                return f"{aspect_prefix} for {prior_context}"

        # Case C: Environmental / Platform constraint addition ("windows pe?", "docker ke andar?")
        # Postposition (Hindi): "<target> ke andar/pe/par/me/mein"
        post_match = re.search(r"^([a-zA-Z0-9_\-\.\s]+?)\s+(?:ke\s+andar|ke\s+sath|me|mein|pe|par)\??$", q_clean, re.IGNORECASE)
        if post_match:
            env_target = post_match.group(1).strip()
            return f"{prior_context} on {env_target}"

        # Preposition (English): "in/on/inside <target>"
        prep_match = re.search(r"\b(?:in|on|under|inside|for|with)\s+([a-zA-Z0-9_\-\.\s]+?)(?:\?|$)", q_clean, re.IGNORECASE)
        if prep_match:
            env_target = prep_match.group(1).strip()
            return f"{prior_context} on {env_target}"

        # Case D: Generic connector ("aur?", "and then?", "what about performance?")
        cleaned_current = _FOLLOWUP_STARTERS.sub("", q_clean).strip()
        if cleaned_current:
            return f"{prior_context} {cleaned_current}"
        
        return prior_context


class NeuralMicroRouter:
    """
    Generalized Micro-Router with Semantic Vector Classification,
    Follow-up Resolution, and Noise Stripping.
    """

    def __init__(self):
        self.semantic_router = SemanticVectorRouter()
        self.context_resolver = FollowUpContextResolver()

    def route_and_reformulate(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
        last_user_turn: Optional[str] = None,
        last_assistant_turn: Optional[str] = None
    ) -> Tuple[WebQueryMode, str]:
        """
        Determines the execution mode and produces an optimized search query.
        Returns:
            (mode: WebQueryMode, search_query: str)
        """
        raw_query = (query or "").strip()
        if not raw_query:
            return WebQueryMode.DIRECT_CHAT, ""

        # Step 0: Context-Aware Follow-Up Resolution (if conversation history exists)
        resolved_query = raw_query
        if last_user_turn or last_assistant_turn or (history and len(history) >= 1):
            if not last_user_turn and history:
                for msg in reversed(history):
                    if msg.get("role") == "user":
                        last_user_turn = msg.get("content")
                        break
                    elif msg.get("role") == "assistant" and not last_assistant_turn:
                        last_assistant_turn = msg.get("content")

            resolved_query = self.context_resolver.resolve(
                raw_query,
                last_user_turn=last_user_turn,
                last_assistant_turn=last_assistant_turn
            )
            if resolved_query != raw_query:
                logger.info(f"🔄 Follow-up query resolved: '{raw_query}' → '{resolved_query}'")

        # Step 1: Semantic Vector Routing (<5ms)
        mode, confidence, _ = self.semantic_router.route(resolved_query)

        # Quick exits: direct local tasks or explicit browser actions
        if mode in (WebQueryMode.DIRECT_CHAT, WebQueryMode.BROWSER_ACTION):
            return mode, resolved_query

        # Step 2: Generalized Query Reformulation for Web Grounding / Deep Research
        clean_search_query = self._reformulate_query(resolved_query)

        # Mode C: Deep research when comprehensive analysis is detected
        if mode == WebQueryMode.DEEP_RESEARCH:
            return WebQueryMode.DEEP_RESEARCH, clean_search_query

        return WebQueryMode.BACKGROUND_GROUNDING, clean_search_query

    def _reformulate_query(self, raw_query: str) -> str:
        """
        Generalized noise stripping for developer and technical queries.
        Preserves programming terms, versions, CLI flags, error codes, and parameters.
        """
        q = raw_query.strip()

        # Remove conversational filler stop patterns
        cleaned = q
        for pattern in _COMPILED_STOPS:
            cleaned = pattern.sub(" ", cleaned)

        # Canonical normalization for high-frequency multilingual commodities
        if re.search(r"\b(?:sone|sona)\s+ka\s+(?:bhav|rate|daam)\b", cleaned, re.IGNORECASE):
            cleaned = re.sub(r"\b(?:sone|sona)\s+ka\s+(?:bhav|rate|daam)\b", "gold price", cleaned, flags=re.IGNORECASE)
        elif re.search(r"\bchandi\s+ka\s+(?:bhav|rate|daam)\b", cleaned, re.IGNORECASE):
            cleaned = re.sub(r"\bchandi\s+ka\s+(?:bhav|rate|daam)\b", "silver price", cleaned, flags=re.IGNORECASE)

        # Clean multiple spaces and strip punctuation at boundaries
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = re.sub(r"^[?!.,;:\s]+|[?!.,;:\s]+$", "", cleaned)

        return cleaned if len(cleaned) >= 3 else q
