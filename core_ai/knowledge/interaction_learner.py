"""
Asynchronous Situational & Life Interaction Learner
===================================================
Non-blocking background daemon that runs after every conversation turn to:
1. Persist completed turns into `conversation_ai.db` + FTS5 long-term memory.
2. Extract episodic life facts (people, exams, schedules, commitments, preferences).
3. Connect user habits with active desktop context (e.g. music preferences while coding).
4. Update `UserDNA` and `PersonalKnowledgeGraph` without adding any latency to voice/chat turns.
"""

import json
import logging
import re
import threading
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Fast heuristic triggers to decide if a turn contains personal life facts or preferences
_PERSONAL_FACT_PATTERNS = [
    re.compile(r"\b(?:my|mera|meri|mere)\s+(?:name|brother|sister|friend|boss|colleague|project|exam|college|work|schedule|bhai|dost|naam)\b", re.IGNORECASE),
    re.compile(r"\b(?:i\s+like|i\s+prefer|i\s+love|i\s+hate|mujhe\s+pasand|mujhe\s+accha|don't\s+like)\b", re.IGNORECASE),
    re.compile(r"\b(?:exam|interview|deadline|meeting|flight|trip|viva|test|event|pariksha)\s+(?:on|at|tomorrow|today|kal|friday|monday|tuesday|wednesday|thursday|saturday|sunday)\b", re.IGNORECASE),
    re.compile(r"\b(?:call\s+me|address\s+me|mujhe\s+bulao|naam\s+se\s+bulao)\b", re.IGNORECASE),
    re.compile(r"\b(?:always\s+use|default\s+to|profile\s+use\s+karo)\b", re.IGNORECASE),
]


def _extract_and_persist_facts(user_text: str, assistant_response: str, active_window: Optional[Dict[str, Any]] = None) -> None:
    """Internal worker executed in a background daemon thread."""
    try:
        from ai_assistant.ai.memory_retrieval import persist_turn_to_conversation_ai
        persist_turn_to_conversation_ai(user_text, assistant_response, source="interaction_learner")
    except Exception as exc:
        logger.debug(f"[Learner] Turn persistence note: {exc}")

    # Check if text contains personal life context
    has_personal_intent = any(pat.search(user_text) for pat in _PERSONAL_FACT_PATTERNS)
    if not has_personal_intent:
        return

    try:
        from ai_assistant.ai.user_dna import UserDNA
        from ai_assistant.knowledge.personal_knowledge_graph import get_knowledge_graph

        dna = UserDNA()
        pkg = get_knowledge_graph()

        low = user_text.lower()

        # 1. Preferred user name / title override
        name_m = re.search(r"\b(?:my\s+name\s+is|call\s+me|mera\s+naam)\s+([a-zA-Z\u0900-\u097F]{2,20})\b", low)
        if name_m:
            chosen = name_m.group(1).title()
            dna.update_trait("user_name", chosen, confidence=1.0)
            logger.info(f"[Learner] Updated user name in DNA: {chosen}")

        # 2. Upcoming event / deadline / exam detection (English & Hindi/Hinglish)
        event_type = None
        event_time = None

        m_direct = (
            re.search(r"\b(exam|interview|deadline|meeting|viva|test)\s+(?:is\s+)?(?:on|at|around)\s+([a-zA-Z\u0900-\u097F]+)", low)
            or re.search(r"\b(exam|interview|deadline|meeting|viva|test)\s+([a-zA-Z\u0900-\u097F]+)\s+(?:ko|hai|mein)", low)
        )
        if m_direct:
            event_type = m_direct.group(1).title()
            event_time = m_direct.group(2).title()
        else:
            m_time_first = re.search(r"\b(kal|parso|aaj|tomorrow|tonight)\s+(?:mera\s+)?(exam|interview|deadline|meeting|viva|test)", low)
            if m_time_first:
                event_time = m_time_first.group(1).title()
                event_type = m_time_first.group(2).title()

        if event_type and event_time:
            dna.update_trait(f"upcoming_{event_type.lower()}", f"{event_type} ({event_time})", confidence=0.95)
            try:
                pkg.add_fact("User", "has_upcoming", f"{event_type} ({event_time})", source="chat")
            except Exception:
                pass
            logger.info(f"[Learner] Recorded upcoming event: {event_type} ({event_time})")

        # 3. Contextual habit: what user does while in specific apps
        if active_window and isinstance(active_window, dict):
            app = str(active_window.get("app_name") or "").lower()
            if "code" in app or "studio" in app:
                if any(m in low for m in ("music", "song", "gaana", "spotify", "track")):
                    dna.update_trait("coding_habit", "Prefers listening to music/songs while coding", confidence=0.85)
                    logger.info("[Learner] Recorded coding habit: music while coding")

    except Exception as exc:
        logger.debug(f"[Learner] Fact extraction background note: {exc}")


def record_turn_and_learn_async(
    user_text: str,
    assistant_response: str,
    *,
    source: str = "voice",
    active_window: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Fire-and-forget background trigger to learn habits and persist memory.
    Adds EXACTLY 0ms latency to the user conversation loop.
    """
    u = str(user_text or "").strip()
    a = str(assistant_response or "").strip()
    if not u or not a:
        return

    # Detached daemon thread
    worker = threading.Thread(
        target=_extract_and_persist_facts,
        args=(u, a, active_window),
        name="PulsarInteractionLearner",
        daemon=True,
    )
    worker.start()
