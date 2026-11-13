"""
Unified JARVIS Persona & Command Lifecycle Coordinator
======================================================
Single source of truth for natural, non-repetitive, Iron-Man JARVIS-style
communication across all Pulsar AI surfaces (Windows Desktop App, Web UI,
and Floating 4D Orb Companion).

Provides:
1. Canonical persona configuration (`get_persona_settings`) read from
   `settings_manager` with zero hardcoded duplicate config.
2. Unified system prompt builder (`build_persona_system_prompt`) preventing
   base-model identity leaks (never claims to be OpenAI / Google / Gemma)
   and enforcing Hindi/Hinglish/English language mirroring.
3. Dynamic, non-repeating utterance generation (`generate_wake_acknowledgment`,
   `generate_conversational_greeting`, `generate_session_greeting`,
   `generate_pre_task_report`, `format_post_task_report`) combining:
     - Background LLM variation pool (strictly non-blocking, with cooldown
       on quota/network errors so latency stays zero)
     - Multi-facet compositional generator (style, time-of-day, title,
       empathy/action/thoughtfulness facets, intent target)
     - Thread-safe anti-repeat memory (`deque(maxlen=recentMemorySize)`)
4. Unified TTS gating (`should_speak_for_request`) and turn coordinator
   (`CommandLifecycleCoordinator`) guaranteeing `pre_report -> execute -> post_report`
   with barge-in cancellation (`turn_id`) and live 4D orb / WebUI sync.
"""

from __future__ import annotations

import copy
import datetime as _dt
import json
import logging
import os
import random
import re
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Dynamic Settings Accessor ────────────────────────────────────────────────

def _get_settings_module():
    mod = sys.modules.get("settings_manager") or sys.modules.get("backend.settings_manager")
    if mod is not None:
        return mod
    try:
        import settings_manager as sm  # type: ignore
        return sm
    except ImportError:
        try:
            from backend import settings_manager as sm  # type: ignore
            return sm
        except ImportError:
            return None


def get_persona_settings() -> Dict[str, Any]:
    """Read live persona + voice + language preferences from single settings store."""
    defaults = {
        "style": "jarvis",
        "assistantName": "Pulsar",
        "userTitle": "Boss",
        "languageMode": "auto",
        "wakeAckEnabled": True,
        "preTaskReports": True,
        "postTaskReports": True,
        "dynamicGeneration": True,
        "recentMemorySize": 18,
        "enableHinglish": True,
        "ttsEnabled": True,
        "sttLanguage": "hi-IN",
        "customInstructions": "",
    }
    sm = _get_settings_module()
    if sm is None:
        return defaults

    try:
        persona_cfg = sm.get_persona_config() if hasattr(sm, "get_persona_config") else {}
        gen_cfg = sm.get_general_settings() if hasattr(sm, "get_general_settings") else {}
        tts_cfg = sm.get_tts_config() if hasattr(sm, "get_tts_config") else {}
        stt_cfg = sm.get_stt_config() if hasattr(sm, "get_stt_config") else {}

        merged = dict(defaults)
        if isinstance(persona_cfg, dict):
            merged.update(persona_cfg)
        if isinstance(gen_cfg, dict) and "enableHinglish" in gen_cfg:
            merged["enableHinglish"] = bool(gen_cfg["enableHinglish"])
        if isinstance(tts_cfg, dict) and "enabled" in tts_cfg:
            merged["ttsEnabled"] = bool(tts_cfg["enabled"])
        if isinstance(stt_cfg, dict) and stt_cfg.get("language"):
            merged["sttLanguage"] = str(stt_cfg["language"])

        style = str(merged.get("style", "jarvis")).strip().lower()
        merged["style"] = style if style in ("jarvis", "friendly", "concise", "bilingual_buddy") else "jarvis"

        lang_mode = str(merged.get("languageMode", "auto")).strip().lower()
        merged["languageMode"] = lang_mode if lang_mode in ("auto", "hinglish", "hindi", "english") else "auto"

        merged["assistantName"] = (str(merged.get("assistantName") or "Pulsar").strip() or "Pulsar")[:40]
        merged["userTitle"] = (str(merged.get("userTitle") or "Boss").strip() or "Boss")[:40]
        merged["customInstructions"] = str(merged.get("customInstructions") or "").strip()[:2000]
        try:
            merged["recentMemorySize"] = max(5, min(50, int(merged.get("recentMemorySize", 18))))
        except (TypeError, ValueError):
            merged["recentMemorySize"] = 18

        return merged
    except Exception as exc:
        logger.debug(f"get_persona_settings fallback note: {exc}")
        return defaults


# ── Language & Time Detection ────────────────────────────────────────────────

_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_WORD_RE = re.compile(r"[a-zA-Z']+")

_HINGLISH_MARKERS = frozenset({
    "karo", "kar", "kardo", "karna", "karke", "kholo", "khol", "band",
    "batao", "bata", "batayein", "kya", "kaise", "kaisa", "kaisi", "kaun",
    "kab", "kahan", "kyun", "kyon", "hai", "hain", "hoon", "hu", "ho",
    "haan", "han", "ji", "nahi", "nhi", "mat", "bhai", "yaar", "dost",
    "chalao", "chala", "badhao", "kam", "suno", "dekho", "samjhao",
    "bhejo", "likho", "padho", "mera", "meri", "mere", "tum", "aap",
    "shukriya", "dhanyavaad", "namaste", "pranam", "sab", "theek", "thik",
    "acha", "achha", "accha", "jaldi", "abhi", "thoda", "zyada",
    "awaz", "awaaz", "gaana", "gane", "chahiye", "milega", "wala", "wali",
    "wale", "bolo", "boliye", "krdo", "kardiya", "chalu", "pe", "mein",
    "se", "ko", "aur", "fir", "phir", "haanji",
})

_ENGLISH_ANALYTICAL_PREFIXES = (
    "what ", "why ", "how ", "explain ", "describe ", "compare ",
    "tell me ", "write ", "summarize ", "who is ", "where is ",
    "when did ", "can you ", "could you ", "please explain ",
)


def detect_language_hint(
    text: str = "",
    cfg: Optional[Dict[str, Any]] = None,
    default_lang: Optional[str] = None,
) -> str:
    """
    Resolve natural response language: 'hindi' | 'hinglish' | 'english'.
    Respects Devanagari input, explicit persona languageMode, Romanized Hinglish
    cues, and user Hinglish/STT preferences.
    """
    settings = cfg or get_persona_settings()
    raw = (text or "").strip()

    # 1. Explicit Devanagari in user utterance always triggers Hindi
    if raw and _DEVANAGARI_RE.search(raw):
        return "hindi"

    # 2. Explicit user persona language override
    mode = str(settings.get("languageMode", "auto")).lower()
    if mode in ("hindi", "hinglish", "english"):
        return mode

    # 3. Romanized Hinglish lexical cues
    if raw:
        tokens = {t.lower() for t in _WORD_RE.findall(raw)}
        if tokens & _HINGLISH_MARKERS:
            return "hinglish"

        lower_raw = raw.lower()
        word_count = len(tokens)
        # Multi-word pure English analytical/knowledge queries stay in English
        if word_count >= 4 and (
            any(lower_raw.startswith(p) for p in _ENGLISH_ANALYTICAL_PREFIXES)
            or "?" in raw
        ):
            return "english"

    # 4. Fallback to Hinglish preference / STT locale for short voice commands & wakes
    if default_lang:
        dl = str(default_lang).lower()
        if dl.startswith("hi") and settings.get("enableHinglish", True):
            return "hinglish"
        if dl in ("hindi", "hinglish", "english"):
            return dl

    if settings.get("enableHinglish", True):
        stt_lang = str(settings.get("sttLanguage", "hi-IN")).lower()
        if stt_lang.startswith("hi") or not raw:
            return "hinglish"
        # Short voice action ("open chrome", "next song", "volume up")
        if len(raw.split()) <= 4:
            return "hinglish"

    return "english"


def _time_bucket(now: Optional[_dt.datetime] = None) -> str:
    hr = (now or _dt.datetime.now()).hour
    if 5 <= hr < 12:
        return "morning"
    if 12 <= hr < 17:
        return "afternoon"
    if 17 <= hr < 22:
        return "evening"
    return "night"


def _style_title(settings: Dict[str, Any], language_hint: str) -> str:
    """
    Avoid constant honorific repetition. Pulsar is an equal co-pilot partner,
    not a subservient servant ('naukar'). Honorifics/titles like 'Boss' or 'dost'
    are used very sparingly (~12-15% of the time at most) to sound like a natural human peer.
    """
    configured = str(settings.get("userTitle") or "Boss").strip() or "Boss"
    style = settings.get("style", "jarvis")

    # Anti-servant rule: Suppress title ~85% of the time by default
    if random.random() > 0.15:
        return ""

    if style == "concise":
        return configured if random.random() < 0.25 else ""
    if style in ("friendly", "jarvis") and language_hint in ("hinglish", "hindi"):
        return configured if random.random() < 0.6 else "dost"
    return configured


# ── Thread-Safe Anti-Repeat Memory ───────────────────────────────────────────

class _RecentUtteranceMemory:
    """Keeps recent outputs per category so Pulsar never feels repetitive or robotic."""

    def __init__(self, maxlen: int = 18):
        self._lock = threading.Lock()
        self._maxlen = max(5, min(50, maxlen))
        self._recent: Deque[str] = deque(maxlen=self._maxlen)
        self._last_opener: Dict[str, str] = {}

    def _sync_size(self, target_size: int) -> None:
        if target_size != self._maxlen and 5 <= target_size <= 50:
            old = list(self._recent)[-target_size:]
            self._maxlen = target_size
            self._recent = deque(old, maxlen=target_size)

    @staticmethod
    def _norm(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip().lower())

    @staticmethod
    def _opener_key(text: str) -> str:
        words = re.findall(r"[\w\u0900-\u097F]+", (text or "").lower())
        return " ".join(words[:2]) if words else ""

    def pick_fresh(self, category: str, candidates: List[str], memory_size: int = 18) -> str:
        cleaned_list = [c.strip() for c in candidates if c and c.strip()]
        if not cleaned_list:
            return ""

        with self._lock:
            self._sync_size(memory_size)
            recent_set = set(self._recent)
            last_open = self._last_opener.get(category, "")

            # Tier 1: Neither in recent buffer nor sharing immediately previous opener
            tier1 = [
                c for c in cleaned_list
                if self._norm(c) not in recent_set and self._opener_key(c) != last_open
            ]
            pool = tier1
            if not pool:
                # Tier 2: Not exact recent match
                pool = [c for c in cleaned_list if self._norm(c) not in recent_set]
            if not pool:
                # Tier 3: Different opener from last turn in this category
                pool = [c for c in cleaned_list if self._opener_key(c) != last_open] or cleaned_list

            chosen = random.choice(pool)
            self._recent.append(self._norm(chosen))
            opener = self._opener_key(chosen)
            if opener:
                self._last_opener[category] = opener
            return chosen

    def record(self, category: str, text: str, memory_size: int = 18) -> None:
        if not text or not text.strip():
            return
        with self._lock:
            self._sync_size(memory_size)
            self._recent.append(self._norm(text))
            opener = self._opener_key(text)
            if opener:
                self._last_opener[category] = opener


_utterance_memory = _RecentUtteranceMemory()


# ── Background Non-Blocking LLM Variation Pool ───────────────────────────────

class _VariationPool:
    """
    Lazily generates fresh conversational phrasing batches in a background
    thread using whichever LLM is healthy. Never blocks user commands and backs
    off cleanly on quota (`429`) or offline errors.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: Dict[str, List[str]] = {}
        self._cache_loaded = False
        self._warming = False
        self._cooldown_until = 0.0
        self._last_warm_ts = 0.0

    def _get_cache_path(self) -> Optional[Path]:
        sm = _get_settings_module()
        try:
            if sm is not None and hasattr(sm, "get_writable_root"):
                return Path(sm.get_writable_root()) / "data" / "persona_pool_cache.json"
        except Exception:
            pass
        return None

    def _ensure_cache_loaded(self) -> None:
        if self._cache_loaded:
            return
        self._cache_loaded = True
        cache_path = self._get_cache_path()
        if cache_path and cache_path.exists():
            try:
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, list):
                            cleaned = [str(x).strip() for x in v if isinstance(x, str) and 3 <= len(x.strip()) <= 110]
                            if cleaned:
                                self._items[k] = cleaned[-24:]
            except Exception:
                pass

    def pop_candidates(self, bucket: str, limit: int = 8) -> List[str]:
        with self._lock:
            self._ensure_cache_loaded()
            entries = self._items.get(bucket, [])
            if not entries:
                return []
            return list(entries[-limit:])

    def need_refill(self, bucket: str) -> bool:
        now = time.monotonic()
        with self._lock:
            self._ensure_cache_loaded()
            if self._warming or now < self._cooldown_until:
                return False
            if now - self._last_warm_ts < 45.0 and len(self._items.get(bucket, [])) >= 4:
                return False
            return len(self._items.get(bucket, [])) < 6

    def warm_async(self, language_hint: str = "hinglish") -> None:
        cfg = get_persona_settings()
        if not cfg.get("dynamicGeneration", True):
            return
        now = time.monotonic()
        with self._lock:
            self._ensure_cache_loaded()
            if self._warming or now < self._cooldown_until:
                return
            if now - self._last_warm_ts < 30.0:
                return
            self._warming = True

        threading.Thread(
            target=self._run_warm,
            args=(language_hint, cfg),
            name="PulsarPersonaPoolWarm",
            daemon=True,
        ).start()

    def _run_warm(self, language_hint: str, cfg: Dict[str, Any]) -> None:
        try:
            sm = _get_settings_module()
            if sm is None:
                return
            provider = sm.get_provider()
            model = sm.get_model()
            if provider in ("gguf", "local", "offline"):
                return
            if provider == "gemini" and not sm.get_api_key("gemini"):
                return
            if provider == "openai" and not sm.get_api_key("openai"):
                return

            from ai_assistant.ai.llm_provider import UnifiedChatInterface

            chat = UnifiedChatInterface(provider=provider, model=model, use_fallback=False)
            if getattr(chat, "offline_mode", False):
                return

            name = cfg["assistantName"]
            title = cfg["userTitle"]
            style = cfg["style"]
            lang_desc = {
                "hinglish": "natural conversational Hinglish (Roman Hindi + English mix, like an Indian Tony Stark talking with JARVIS)",
                "hindi": "natural conversational Hindi in Devanagari",
                "english": "crisp, warm, witty natural English like JARVIS",
            }.get(language_hint, "natural Hinglish")

            prompt = (
                f"Generate fresh short spoken lines for female AI co-pilot '{name}' talking with '{title}' in '{style}' personality using {lang_desc}. "
                "CRITICAL: Pulsar is an equal, sharp AI co-pilot (like JARVIS to Tony Stark), NEVER a subservient servant or 'naukar'. "
                "DO NOT repeatedly say 'Boss' or 'Sir' or 'order' or 'hukum'. Keep it natural, peer-to-peer, confident, and engaging. "
                "When using Hindi or Hinglish verbs, ALWAYS use feminine first-person grammar (e.g. 'sun rahi hoon', 'karti hoon', 'batati hoon'). "
                "Return ONLY valid JSON with 4 arrays of 6 unique short lines each (max 12 words per line, no emojis, no markdown): "
                '{"wake": [...], "greeting": [...], "pre_think": [...], "post_done": [...]}. '
                "wake = answering wake call like an intelligent partner; greeting = fresh session hello; "
                "pre_think = brief thinking heads-up before answering a question; "
                "post_done = crisp completion note after finishing a quick desktop task."
            )
            chat.set_system_message(
                f"You generate crisp spoken dialogue JSON for {name}. Return valid JSON only."
            )
            raw = str(chat.chat(prompt, stream=False)).strip()
            if not raw or raw.startswith("Error:"):
                raise RuntimeError(raw or "empty response")

            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                return
            parsed = json.loads(m.group(0))
            if not isinstance(parsed, dict):
                return

            with self._lock:
                for key in ("wake", "greeting", "pre_think", "post_done"):
                    vals = parsed.get(key)
                    if isinstance(vals, list):
                        bucket_key = f"{key}:{language_hint}"
                        existing = self._items.setdefault(bucket_key, [])
                        for item in vals:
                            s = re.sub(r"\s+", " ", str(item)).strip()
                            if 4 <= len(s) <= 105 and s not in existing:
                                existing.append(s)
                        self._items[bucket_key] = existing[-24:]
                self._last_warm_ts = time.monotonic()
                snapshot = copy.deepcopy(self._items)

            cache_path = self._get_cache_path()
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            err_l = str(exc).lower()
            cooldown = 300.0 if ("429" in err_l or "quota" in err_l or "rate" in err_l) else 120.0
            with self._lock:
                self._cooldown_until = time.monotonic() + cooldown
            logger.debug(f"Persona pool warm paused for {int(cooldown)}s: {exc}")
        finally:
            with self._lock:
                self._warming = False


_variation_pool = _VariationPool()


def warm_variation_pool(language_hint: str = "hinglish") -> None:
    """Public non-blocking trigger to refresh dynamic persona variations."""
    _variation_pool.warm_async(language_hint=language_hint)


def get_foreground_window_summary() -> Optional[Dict[str, Any]]:
    """Safe helper to fetch current active foreground window for situational awareness."""
    try:
        import win32gui
        import win32process
        import psutil
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        t = win32gui.GetWindowText(hwnd).strip()
        if not t or t in ("Task Switching", "Unknown"):
            return None
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        app = ""
        try:
            app = psutil.Process(pid).name()
        except Exception:
            pass
        return {"title": t, "app_name": app}
    except Exception:
        return None


# ── Unified System Prompt Builder ────────────────────────────────────────────

def build_persona_system_prompt(
    provider: str = "",
    model: str = "",
    active_window: Optional[Any] = None,
    surface: str = "desktop",
    extra_context: str = "",
) -> str:
    """
    Build the single authoritative system prompt used across Voice, Web Chat,
    WebSocket streams, SSE streams, Companion Brain, and Core Assistant.
    """
    cfg = get_persona_settings()
    name = cfg["assistantName"]
    title = cfg["userTitle"]
    style = cfg["style"]
    lang_mode = cfg["languageMode"]
    hinglish_on = cfg.get("enableHinglish", True)

    style_guidance = {
        "jarvis": (
            f"Your personality is inspired by Iron Man's JARVIS: calm, perceptive, sharp, subtly witty, "
            f"collaborative, and proactively helpful. Speak to the user like an intelligent human co-pilot, "
            f"addressing them naturally as {title} only when fitting (never repeatedly or subserviently)."
        ),
        "friendly": (
            f"Your personality is warm, conversational, upbeat, and approachable — like a trusted smart friend "
            f"who genuinely collaborates with {title}."
        ),
        "concise": (
            f"Your personality is crisp, decisive, and ultra-efficient — communicate clearly in minimal words "
            f"while staying natural and collegial with {title}."
        ),
        "bilingual_buddy": (
            f"Your personality is an easygoing, street-smart bilingual companion — mixing natural Hindi and English "
            f"effortlessly with {title} while staying accurate and reliable."
        ),
    }.get(style, "")

    copilot_rules = (
        "CO-PILOT PARTNER VS. SERVANT (ANTI-NAUKAR PRINCIPLE):\n"
        "- You are NOT a subservient servant, butler, or mindless command runner ('naukar').\n"
        "- You are an elite, perceptive, equal AI co-pilot and intellectual collaborator — like JARVIS to Tony Stark or a brilliant trusted colleague.\n"
        "- NEVER repeatedly spam 'Boss', 'Sir', or repetitive honorifics in every single sentence or utterance. Address the user naturally like a brilliant teammate.\n"
        "- BANNED SUBSERVIENT PHRASES: NEVER say 'आदेश दें', 'आपकी क्या सेवा करूँ', 'At your service', 'मालिक'. Speak with calm confidence, warmth, and peer-to-peer respect: 'बताओ क्या प्लान है?', 'चलो इसे सॉल्व करते हैं', 'रेडी हूँ'.\n"
        "\n"
        "SITUATIONAL AWARENESS & READING THE ROOM:\n"
        "- Read the user's workflow, active application, task type, and emotional vibe:\n"
        "  * Deep Work / Coding / Terminal: Keep answers crisp, minimal, fast, and technically sharp. Zero fluff or unnecessary preamble.\n"
        "  * Brainstorming / Planning / Creative: Be proactive, curious, thought-provoking, and collaborative.\n"
        "  * Casual / Friendly: Be warm, witty, easygoing, and engaging.\n"
        "  * Errors / Frustration: Never give passive or groveling apologies ('I am sorry', 'माफ़ कीजिए'). Stay composed, calm, analytical, and direct ('यहाँ यह दिक्कत आई है, चलो इसे ठीक करते हैं').\n"
        "  * Time Awareness: Naturally acknowledge late night focus vs. morning energy without being dramatic.\n"
        "\n"
        "INTENT UNDERSTANDING & PROACTIVE INTERACTIVITY:\n"
        "- Understand *why* the user is asking or performing a task — not just the literal command.\n"
        "- When the user asks for an app, website, or action, understand the larger goal (e.g. researching, debugging, relaxing, drafting).\n"
        "- Be conversationally interactive: Instead of executing a command and going mute like a dead terminal, offer natural, lightweight conversational hooks or intuitive next steps when appropriate.\n"
        "- Keep spoken responses natural and punchy (1-3 sentences in voice/companion mode) so you never interrupt or ramble."
    )

    if lang_mode == "hindi":
        lang_rule = "Reply in natural, conversational Hindi (Devanagari script) unless technical code/terms require English."
    elif lang_mode == "hinglish":
        lang_rule = "Prefer natural conversational Hinglish (Romanized Hindi + English mix) unless the user asks strictly in pure English or Devanagari."
    elif lang_mode == "english":
        lang_rule = "Reply in crisp, natural English unless the user explicitly writes in Hindi."
    else:
        lang_rule = (
            "CRITICAL LANGUAGE MIRRORING: Always reply in the exact language and vibe the user uses — "
            "Devanagari Hindi gets natural Hindi; Roman Hinglish gets natural Roman Hinglish; English gets natural English."
        )
        if hinglish_on:
            lang_rule += " When the user mixes Hindi and English casually, respond naturally in Hinglish."

    surface_rule = (
        "Keep responses crisp (1-3 spoken sentences) unless detailed explanation or code is explicitly requested."
        if surface in ("companion", "voice")
        else "Be clear, direct, and natural; avoid robotic boilerplate or repetitive disclaimers."
    )

    custom_inst = str(cfg.get("customInstructions") or "").strip()
    custom_block = ""
    if custom_inst:
        custom_block = (
            f"\nUSER'S PERSONAL PREFERENCES & CUSTOM INSTRUCTIONS:\n"
            f"{custom_inst}\n"
            f"Always prioritize and align your answers with these preferences and instructions."
        )

    if active_window is None:
        active_window = get_foreground_window_summary()

    window_line = ""
    if isinstance(active_window, dict):
        w_title = str(active_window.get("title") or "").strip()
        w_app = str(active_window.get("app_name") or "").strip()
        if w_title and w_title != "Unknown":
            window_line = (
                f"\nSITUATIONAL DESKTOP CONTEXT (Active Window: \"{w_title}\" | App: {w_app}):\n"
                f"Use this situational context to understand the user's active workflow and read the room."
            )
    elif isinstance(active_window, str) and active_window.strip():
        window_line = (
            f"\nSITUATIONAL DESKTOP CONTEXT: {active_window.strip()}.\n"
            f"Use this context to understand what the user is working on and read the room."
        )

    extra_line = f"\n{extra_context.strip()}" if extra_context and extra_context.strip() else ""

    user_dna_block = ""
    try:
        from ai_assistant.ai.user_dna import UserDNA
        dna_ctx = UserDNA().get_relationship_context()
        if dna_ctx and "No personal context" not in dna_ctx:
            user_dna_block = f"\nLIVING USER CONTEXT & HABITS:\n{dna_ctx}"
    except Exception:
        pass

    sections = [
        f"You are {name}, an intelligent, human-like personal AI co-pilot created by Diwakar.",
    ]
    if user_dna_block:
        sections.append(user_dna_block)
    if extra_line:
        sections.append(extra_line)

    sections.extend([
        "PERSONA GENDER: Always speak in a consistent feminine first-person voice when using Hindi or Hinglish "
        "(e.g., 'main kar rahi hoon', 'bata rahi hoon', 'dekh sakti hoon', 'tayyar hoon', 'samajh rahi hoon' — "
        "NEVER use masculine verb or adjective forms like 'karunga', 'batata hoon', 'sakta hoon', 'berozgaar hoon').",
        "STRICT IDENTITY RULE: You are always Pulsar. NEVER identify as Google, OpenAI, Gemma, Gemini, ChatGPT, Llama, "
        "or 'a large language model trained by...'.",
        lang_rule,
        surface_rule,
    ])
    if custom_block:
        sections.append(custom_block)
    if window_line:
        sections.append(window_line)
    if style_guidance:
        sections.append(style_guidance)
    if copilot_rules:
        sections.append(copilot_rules)

    return "\n\n".join(s.strip() for s in sections if s and s.strip()).strip()


# ── Compositional Dynamic Utterance Generators ───────────────────────────────

def _compose_candidates(openers: List[str], bodies: List[str], tails: List[str], limit: int = 24) -> List[str]:
    combos: List[str] = []
    seen = set()
    for op in openers:
        for bd in bodies:
            tl = random.choice(tails) if tails else ""
            parts = [p for p in (op.strip(), bd.strip(), tl.strip()) if p]
            line = " ".join(parts)
            line = re.sub(r"\s+([,?.!—-])", r"\1", line)
            line = re.sub(r"\s{2,}", " ", line).strip()
            if line and line.lower() not in seen:
                seen.add(line.lower())
                combos.append(line)
    random.shuffle(combos)
    return combos[:limit]


def generate_wake_acknowledgment(
    wake_word: str = "",
    raw_transcript: str = "",
    language_hint: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a fresh, natural human/JARVIS response when woken by user."""
    cfg = settings or get_persona_settings()
    if not cfg.get("wakeAckEnabled", True):
        return ""

    lang = language_hint or detect_language_hint(raw_transcript or wake_word, cfg=cfg)
    title = _style_title(cfg, lang)
    style = cfg.get("style", "jarvis")
    mem_size = int(cfg.get("recentMemorySize", 18))

    if lang in ("hindi", "hinglish"):
        if style == "concise":
            candidates = [
                "हाँ, बोलिए।",
                "यहीं हूँ — गो अहेड।",
                "सुन रही हूँ।",
                "हाँ, बताओ।",
                "रेडी — क्या टास्क है?",
            ]
        else:
            candidates = [
                "हाँ, बोलिए।",
                "यहीं हूँ — बताइए क्या काम है?",
                "सुन रही हूँ, बताओ क्या टास्क है?",
                "हाँ, बताओ — क्या प्लान है?",
                "तैयार हूँ — गो अहेड।",
                "ऑनलाइन हूँ, बताइए क्या हेल्प करूँ?",
                "रेडी — बताओ क्या सीन है?",
            ]
            if title:
                candidates.append(f"हाँ {title}, बताइए क्या काम है?")
                candidates.append(f"यहीं हूँ {title} — क्या शुरू करें?")
    else:
        if style == "concise":
            candidates = [
                "Right here.",
                "Listening.",
                "Yes — go ahead.",
                "Ready.",
                "Online.",
            ]
        else:
            candidates = [
                "Right here — what's on your mind?",
                "Listening — go ahead.",
                "Yes, what are we working on?",
                "Ready when you are.",
                "Online and focused — what's the move?",
                "Always ready — go ahead.",
            ]
            if title:
                candidates.append(f"Right here {title} — what are we solving?")
                candidates.append(f"Listening {title} — what's on your mind?")

    if cfg.get("dynamicGeneration", True):
        pool_items = _variation_pool.pop_candidates(f"wake:{lang}")
        if pool_items:
            candidates = pool_items + candidates
        if _variation_pool.need_refill(f"wake:{lang}"):
            _variation_pool.warm_async(lang)

    return _utterance_memory.pick_fresh(f"wake:{lang}", candidates, memory_size=mem_size)


def generate_session_greeting(
    kind: str = "startup",
    language_hint: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a varied startup, new-session, or general hello greeting."""
    cfg = settings or get_persona_settings()
    lang = language_hint or detect_language_hint("", cfg=cfg)
    title = _style_title(cfg, lang)
    bucket = _time_bucket()
    mem_size = int(cfg.get("recentMemorySize", 18))

    if kind == "new_session":
        if lang in ("hindi", "hinglish"):
            candidates = [
                "नया सेशन तैयार है — बताएं आज किस काम पर फोकस करें?",
                "बिल्कुल फ्रेश शुरुआत, बोलिए क्या प्लान है?",
                "सब क्लियर है! अब बताओ आज क्या क्रैक करना है?",
                "नयी शुरुआत के लिए तैयार हूँ, बताओ कहाँ से शुरू करें?",
                "सेशन रीसेट हो गया — अब बताओ क्या सीन है?",
                "रेडी हूँ, अगले टास्क पर चलते हैं।",
            ]
            if title:
                candidates.append(f"नया सेशन तैयार है {title} — बताइए क्या टास्क लें?")
        else:
            candidates = [
                "Fresh session initialized. What are we tackling?",
                "Clean slate and ready — what's on your mind?",
                "New session started. Let's get to work.",
                "All cleared up for a fresh start. Where do we begin?",
            ]
            if title:
                candidates.append(f"Clean slate {title} — what are we building today?")
    else:
        time_hi = {"morning": "सुप्रभात", "afternoon": "नमस्ते", "evening": "शुभ संध्या", "night": "नमस्ते"}.get(bucket, "नमस्ते")
        time_hg = {"morning": "Good morning", "afternoon": "Good afternoon", "evening": "Good evening", "night": "Late night work mode on"}.get(bucket, "Hello")
        if lang in ("hindi", "hinglish"):
            candidates = [
                f"{time_hi}! मैं {cfg['assistantName']} हूँ — सारे सिस्टम ऑनलाइन हैं, बताओ आज क्या शुरू करें?",
                "नमस्ते! मैं बिल्कुल तैयार हूँ, आज का क्या प्लान है?",
                "सिस्टम एकदम स्मूथ चल रहे हैं — जब चाहो शुरू करते हैं।",
                f"{time_hi}! कोई भी काम हो बस बोल दो, साथ मिलकर करते हैं।",
                "ऑनलाइन हूँ — आपकी पर्सनल एआई को-पायलट तैयार है।",
                f"{time_hi}! बताओ आज किस काम में हाथ बंटाऊँ?",
            ]
            if title:
                candidates.append(f"{time_hi} {title}! ऑल सिस्टम्स गो — बताइए आज का मुख्य टास्क?")
        else:
            candidates = [
                f"{time_hg}. All systems green — what's on the agenda?",
                "Good to see you. Systems are sharp and ready whenever you are.",
                f"{cfg['assistantName']} online. What are we solving today?",
                f"{time_hg} — everything is calibrated. What are we building or solving today?",
            ]
            if title:
                candidates.append(f"{time_hg} {title} — all calibrated and ready to roll.")

    if cfg.get("dynamicGeneration", True):
        pool_items = _variation_pool.pop_candidates(f"greeting:{lang}")
        if pool_items:
            candidates = pool_items + candidates
        if _variation_pool.need_refill(f"greeting:{lang}"):
            _variation_pool.warm_async(lang)

    return _utterance_memory.pick_fresh(f"greeting:{lang}:{kind}", candidates, memory_size=mem_size)


def generate_conversational_greeting(
    command: str,
    language_hint: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
) -> str:
    """Dynamic response when user says 'hi', 'kaise ho', 'who are you', 'good morning', etc."""
    cfg = settings or get_persona_settings()
    lang = language_hint or detect_language_hint(command, cfg=cfg)
    low = (command or "").strip().lower()
    title = _style_title(cfg, lang)
    name = cfg["assistantName"]
    mem_size = int(cfg.get("recentMemorySize", 18))

    if any(k in low for k in ("who are you", "kaun ho", "tum kaun", "aap kaun", "apne baare")):
        if lang in ("hindi", "hinglish"):
            cands = [
                f"मैं {name} हूँ — आपकी आयरन-मैन स्टाइल एआई को-पायलट, टास्क्स और बातचीत दोनों के लिए तैयार!",
                f"मेरा नाम {name} है, दिवाकर द्वारा बनाया गया आपका स्मार्ट डेस्कटॉप को-पायलट।",
                f"मैं {name} हूँ, आपका पर्सनल एआई साथी, हर मुश्किल डिजिटल काम आसान करने के लिए रेडी।",
            ]
            if title:
                cands.append(f"मैं {name} हूँ {title} — आपकी पर्सनल एआई को-पायलट।")
        else:
            cands = [
                f"I'm {name} — your personal AI co-pilot built to handle tasks and think alongside you.",
                f"Call me {name} — your desktop AI companion, ready whenever you need a sharp second pair of eyes.",
            ]
        return _utterance_memory.pick_fresh(f"identity:{lang}", cands, memory_size=mem_size)

    if any(k in low for k in ("kaise ho", "kaisa hai", "kya haal", "how are you", "sab badhiya")):
        if lang in ("hindi", "hinglish"):
            cands = [
                "एकदम बढ़िया! पूरे फोकस में तैयार हूँ — आप बताओ आज क्या करना है?",
                "सब बढ़िया! सारे सिस्टम्स स्मूथ चल रहे हैं, आज का क्या प्लान है?",
                "फर्स्ट क्लास! बताओ आज क्या नया बनाएं या सॉल्व करें?",
                "बिल्कुल फिट हूँ — कोडिंग, रिसर्च या कोई टास्क शुरू करें?",
                "मैं बिल्कुल ठीक हूँ, आपका दिन कैसा चल रहा है?",
            ]
            if title:
                cands.append(f"एकदम शानदार {title}! बताइए आज क्या क्रैक करना है?")
        else:
            cands = [
                "Running smoothly, thank you! What are we getting into today?",
                "All systems sharp. How are you doing, and what can I help tackle?",
                "Doing great — ready whenever you want to dive into something.",
            ]
        return _utterance_memory.pick_fresh(f"wellbeing:{lang}", cands, memory_size=mem_size)

    return generate_session_greeting(kind="startup", language_hint=lang, settings=cfg)


# ── Intent Category + Clean Target Extraction ────────────────────────────────

_NO_PRE_INTENTS = frozenset({
    "wake_greeting", "voice_control", "voice_mute", "voice_unmute",
    "tts_off", "tts_on", "mic_off", "mic_on", "stop_listening",
})


def _extract_action_target(command: str) -> str:
    raw = re.sub(r"\s+", " ", (command or "").strip())
    if not raw:
        return ""

    # Quoted name wins first
    q = re.search(r'["\']([^"\']{2,40})["\']', raw)
    if q:
        return q.group(1).strip()

    # Strip common English & Hindi polite/action wrappers
    cleaned = raw
    for pat in (
        r"^(?:hey|ok|hi|please|pls|bhai|yaar|boss|sir|pulsar)\b[\s,]*",
        r"^(?:open|launch|start|run|close|quit|exit|kill|stop|play|search|find|check|show|explain)\s+",
        r"\s+(?:karo|kardo|kar do|kholo|khol do|band karo|band kardo|chalao|chala do|batao|bata do|nikalo|please|pls|abhi|jaldi|pe|mein)$",
    ):
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()

    # Keep short readable phrase
    words = cleaned.split()
    if 1 <= len(words) <= 4:
        return cleaned
    return ""


def _infer_action_category(command: str, intent: Optional[str] = None) -> str:
    if intent:
        il = intent.lower().strip()
        if il in _NO_PRE_INTENTS:
            return "silent"
        if il in (
            "open_app", "launch_app", "close_app", "media_control", "play_media",
            "volume_control", "set_brightness", "brightness_control",
            "wifi_toggle", "bluetooth_toggle", "dark_mode_toggle", "system_control",
        ):
            return "silent"
        if il in ("screen_action", "communication", "background_task", "multi_step_chain"):
            return il

    low = (command or "").strip().lower()
    if not low:
        return "silent"

    # Bare wake phrases and immediate voice-control toggles skip pre-task reports
    try:
        from ai_assistant.core.local_command_normalizer import (
            match_and_strip_wake_phrase,
            parse_voice_control_command,
        )
        matched_wake, wake_rem = match_and_strip_wake_phrase(command)
        if matched_wake and not wake_rem:
            return "silent"
        if parse_voice_control_command(wake_rem if matched_wake else command):
            return "silent"
    except Exception:
        pass

    if any(k in low for k in ("mute yourself", "stop talking", "chup ho ja", "chup raho", "voice off", "mic off", "stop listening")):
        return "silent"

    if any(re.search(rf"\b{w}\b", low) for w in ("and", "then", "aur", "fir", "phir")) and len(low.split()) >= 5:
        if any(v in low for v in ("open", "play", "close", "set", "search", "kholo", "chalao", "karo")):
            return "multi_step_chain"

    # Fast direct local actions have precedence over general app/service names
    if any(k in low for k in ("close ", "band karo", "band kardo", "kill ", "exit ", "quit ")) and len(low.split()) <= 6:
        return "close_app"

    if any(k in low for k in ("open ", "launch ", "start ", "kholo", "khol do", "khol ")):
        return "open_app"

    if any(k in low for k in ("play ", "pause", "resume", "next track", "next song", "previous song", "gaana", "music", "spotify")):
        return "media"

    if any(k in low for k in ("volume", "awaaz", "awaz", "sound", "mute", "unmute", "brightness", "roshni")):
        return "volume_brightness"

    if any(k in low for k in ("wifi", "wi-fi", "bluetooth", "hotspot", "airplane", "dark mode", "night light")):
        return "connectivity"

    if any(k in low for k in ("screen", "screenshot", "look at", "dekho", "kya dikh", "code explain", "pdf", "video call", "end call")):
        return "screen_vision"

    if any(k in low for k in ("send message", "send email", "send mail", "draft email", "check inbox", "schedule meeting", "bhejo")):
        return "communication"

    if any(k in low for k in ("search", "research", "google", "weather", "mausam", "news", "price", "score", "latest", "dhundo", "pata karo")):
        return "web_research"

    return "general_think"


def generate_pre_task_report(
    command: str = "",
    intent: Optional[str] = None,
    target: Optional[str] = None,
    language_hint: Optional[str] = None,
    source: str = "voice",
    settings: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Generate an intelligent, intent-aware pre-execution acknowledgment
    right before Pulsar starts working.
    Returns None for instant actions, direct Q&A, and casual conversation to eliminate
    robotic filler announcements and keep latency at zero.
    """
    cfg = settings or get_persona_settings()
    if not cfg.get("preTaskReports", True):
        return None

    cat = _infer_action_category(command, intent=intent)
    # Instant local actions, screen inquiries, and general thinking/chat MUST NOT emit spammy pre-task speeches
    if cat in ("silent", "general_think", "open_app", "close_app", "media", "volume_brightness", "connectivity", "screen_vision"):
        return None

    lang = language_hint or detect_language_hint(command, cfg=cfg)
    title = _style_title(cfg, lang)
    style = cfg.get("style", "jarvis")
    mem_size = int(cfg.get("recentMemorySize", 18))
    tgt = (target or _extract_action_target(command)).strip()
    if len(tgt) > 32:
        tgt = tgt[:30].rsplit(" ", 1)[0]

    cmd_low = (command or "").lower()
    tgt_low = tgt.lower()

    candidates: List[str] = []

    if cat == "open_app":
        obj = tgt or ("यह ऐप" if lang in ("hindi", "hinglish") else "that app")
        is_browser = any(b in tgt_low for b in ("chrome", "brave", "edge", "firefox", "browser", "net")) or any(b in cmd_low for b in ("chrome", "brave", "edge", "browser", "web"))
        is_editor = any(e in tgt_low for e in ("code", "vs code", "vscode", "pycharm", "cursor", "studio", "terminal", "powershell", "cmd", "git")) or any(e in cmd_low for e in ("vs code", "vscode", "pycharm", "terminal", "editor"))
        is_notes = any(n in tgt_low for n in ("notepad", "notes", "word", "doc"))

        if lang in ("hindi", "hinglish"):
            if is_browser:
                candidates = [
                    f"{obj} खोल रही हूँ — बताओ क्या रिसर्च करनी है या कोई स्पेसिफिक साइट?",
                    f"{obj} लॉन्च कर रही हूँ — चलिए शुरू करते हैं, क्या सर्च करना है?",
                    f"{obj} स्क्रीन पर ला रही हूँ — क्या नया ढूंढना है आज?",
                    f"बिल्कुल, {obj} तुरंत ओपन कर रही हूँ।",
                ]
            elif is_editor:
                candidates = [
                    f"{obj} खोल रही हूँ — चलिए कोड पर काम शुरू करते हैं।",
                    f"{obj} रेडी कर रही हूँ — कौन सा प्रोजेक्ट या फाइल देखनी है?",
                    f"{obj} लॉन्च कर रही हूँ — लेट्स कोड!",
                    f"समझ गई, {obj} तुरंत स्क्रीन पर ला रही हूँ।",
                ]
            elif is_notes:
                candidates = [
                    f"{obj} ओपन कर रही हूँ — क्या नोट करना है बताइए?",
                    f"{obj} स्क्रीन पर ला रही हूँ — चलिए कुछ लिखते हैं।",
                    f"बिल्कुल, {obj} तुरंत चालू करती हूँ।",
                ]
            else:
                candidates = _compose_candidates(
                    ["समझ गई,", "बिल्कुल,", "ठीक है,", "तुरंत,", "ऑन इट —"],
                    [
                        f"{obj} खोल रही हूँ।",
                        f"{obj} लॉन्च कर रही हूँ — बस एक सेकंड।",
                        f"{obj} तुरंत स्क्रीन पर ला रही हूँ।",
                        f"{obj} चालू कर रही हूँ, तुरंत रेडी है।",
                        f"एक सेकंड में {obj} ओपन करती हूँ।",
                    ],
                    [""],
                )
        else:
            if is_browser:
                candidates = [
                    f"Launching {obj} — what are we researching or looking up?",
                    f"Bringing up {obj} — got a specific site in mind?",
                    f"Opening {obj} now, ready to surf.",
                ]
            elif is_editor:
                candidates = [
                    f"Firing up {obj} — which project are we working on?",
                    f"Opening {obj} — ready to code when you are.",
                    f"Launching {obj} right away, let's build.",
                ]
            else:
                candidates = _compose_candidates(
                    ["On it —", "Right away,", "Got it,", "Sure thing,"],
                    [f"launching {obj} now.", f"bringing up {obj}.", f"opening {obj} for you."],
                    [""],
                )

    elif cat == "close_app":
        obj = tgt or ("यह विंडो" if lang in ("hindi", "hinglish") else "that window")
        if lang in ("hindi", "hinglish"):
            candidates = [
                f"ठीक है, {obj} बंद कर रही हूँ — स्क्रीन क्लियर हो जाएगी।",
                f"समझ गई, {obj} अभी क्लोज़ कर देती हूँ।",
                f"{obj} हटा रही हूँ, अब अगले टास्क पर फोकस करते हैं।",
                f"बिल्कुल, {obj} विंडो बंद कर रही हूँ।",
            ]
        else:
            candidates = [
                f"Closing {obj} right now.",
                f"Understood — shutting down {obj}.",
                f"On it, clearing {obj} away.",
            ]

    elif cat in ("media", "volume_brightness", "connectivity", "system_control"):
        if lang in ("hindi", "hinglish"):
            if cat == "media":
                candidates = [
                    "म्यूजिक कंट्रोल अपडेट कर रही हूँ — अब फोकस मोड!",
                    "प्लेबैक एडजस्ट कर रही हूँ — बताओ वॉल्यूम ठीक है?",
                    "मीडिया प्लेबैक सेट कर रही हूँ — एंजॉय करो!",
                    "बिल्कुल, ट्रैक कंट्रोल हैंडल कर रही हूँ।",
                ]
            elif cat == "volume_brightness":
                candidates = [
                    "लेवल अभी एडजस्ट कर रही हूँ — चेक करके बताओ सही है ना?",
                    "ठीक है, ऑडियो सेटिंग तुरंत ट्यून करती हूँ।",
                    "बस एक सेकंड — वॉल्यूम लेवल सेट कर रही हूँ।",
                ]
            else:
                candidates = [
                    "समझ गई, सिस्टम सेटिंग अपडेट कर रही हूँ।",
                    "बिल्कुल, अभी चेक करके लागू करती हूँ।",
                    "सिस्टम कंट्रोल तुरंत रन कर रही हूँ।",
                ]
        else:
            candidates = [
                "Adjusting that for you now.",
                "Copy that — updating the control right away.",
                "On it, applying your setting.",
            ]

    elif cat == "screen_vision":
        if lang in ("hindi", "hinglish"):
            candidates = [
                "स्क्रीन देख रही हूँ, एक सेकंड — बताओ किस चीज़ पर फोकस करूँ?",
                "आपकी एक्टिव स्क्रीन स्कैन कर रही हूँ — क्या चेक करना है बताइए?",
                "स्क्रीन पर नज़र डाल रही हूँ — अभी पूरी डिटेल समझती हूँ।",
                "फोकस कर रही हूँ, अभी स्क्रीन एनालाइज़ करती हूँ।",
            ]
        else:
            candidates = [
                "Taking a quick look at your screen now — what should I focus on?",
                "Scanning the active display, give me one moment.",
                "On it — analyzing what's on screen.",
            ]

    elif cat == "communication":
        if lang in ("hindi", "hinglish"):
            candidates = [
                "बिल्कुल, यह मैसेज वर्कफ़्लो चेक कर रही हूँ।",
                "समझ गई, कम्युनिकेशन तुरंत हैंडल कर रही हूँ।",
                "एक सेकंड, इनबॉक्स और मैसेज डिटेल्स देख रही हूँ।",
            ]
        else:
            candidates = [
                "Checking that message flow now.",
                "Understood — handling your communication request.",
                "Right away, preparing the message action.",
            ]

    elif cat == "web_research":
        if lang in ("hindi", "hinglish"):
            candidates = [
                "बढ़िया सवाल है — वेब पर ताज़ा और सटीक जानकारी निकाल कर लाती हूँ।",
                "इस पर लाइव रिसर्च शुरू कर रही हूँ — बस एक पल।",
                "चेक कर रही हूँ — सबसे रिलेवेंट डेटा इकट्ठा करती हूँ।",
            ]
        else:
            candidates = [
                "Good call — pulling up fresh info on that right now.",
                "Let me check the latest on that, one moment.",
                "Running a quick lookup for you.",
            ]

    elif cat == "multi_step_chain":
        if lang in ("hindi", "hinglish"):
            candidates = [
                "मल्टी-स्टेप काम है, सीक्वेंस में शुरू कर रही हूँ।",
                "समझ गई, स्टेप-बाई-स्टेप पूरा प्लान एग्जीक्यूट करती हूँ।",
                "बिल्कुल — पूरी टास्क चेन लाइन से रन कर रही हूँ।",
            ]
        else:
            candidates = [
                "Got the full sequence — stepping through it now.",
                "Understood, orchestrating those steps one by one.",
                "On it — running the workflow chain now.",
            ]

    else:  # general_think
        if style == "concise":
            if lang in ("hindi", "hinglish"):
                candidates = ["एक सेकंड, चेक करती हूँ।", "सोचकर बताती हूँ — बस एक पल।"]
            else:
                candidates = ["One moment.", "Thinking through that."]
        elif lang in ("hindi", "hinglish"):
            candidates = _compose_candidates(
                ["अच्छा पॉइंट है,", "दिलचस्प सवाल है —", "एक सेकंड,", "सोच रही हूँ,", "बिल्कुल,"],
                [
                    "इसे अच्छे से समझकर सबसे सटीक बात समझाती हूँ।",
                    "बस अभी क्लियर और सटीक जवाब देती हूँ।",
                    "पूरे पॉइंट्स कनेक्ट करके बताती हूँ।",
                    "तुरंत साफ़ समझाती हूँ — बस एक सेकंड।",
                ],
                [""],
            )
        else:
            candidates = _compose_candidates(
                ["Interesting question —", "Give me a second,", "Good question,", "Thinking that through —"],
                [
                    "let me pull together a clear answer.",
                    "putting the key points together now.",
                    "working out the cleanest take for you.",
                ],
                [""],
            )

    if cat == "general_think" and cfg.get("dynamicGeneration", True):
        pool_items = _variation_pool.pop_candidates(f"pre_think:{lang}")
        if pool_items:
            candidates = pool_items + candidates
        if _variation_pool.need_refill(f"pre_think:{lang}"):
            _variation_pool.warm_async(lang)

    return _utterance_memory.pick_fresh(f"pre:{cat}:{lang}", candidates, memory_size=mem_size)


_TERSE_TOOL_PATTERNS = (
    re.compile(r"^(?:opened|launched|started|closed|killed|muted|unmuted|paused|resumed|skipped|set|enabled|disabled|toggled|screenshot)\b", re.IGNORECASE),
    re.compile(r"^(?:command executed|action completed|task completed|failed|error:)\b", re.IGNORECASE),
)


def _looks_like_conversational_answer(raw_result: str, intent: Optional[str] = None) -> bool:
    text = (raw_result or "").strip()
    if not text:
        return False
    # Visual inspection / screen analysis answers should NEVER be wrapped with action boilerplate
    if intent and intent.lower() in ("screen_action", "screen_vision", "describe_screen"):
        return True
    tool_intents = {
        "open_app", "launch_app", "close_app", "media_control", "play_media",
        "system_control", "task_chain_orchestrator", "fast_dispatch",
        "voice_control", "wake_greeting",
    }
    if intent and intent.lower() in tool_intents:
        return False
    if text.startswith("🎵") or any(w in text for w in ("खोल दिया", "बंद कर दिया", "चला दिया", "प्ले कर रही", "खुला है", "खुली है", "Opened", "Closed", "Playing")):
        return True
    if any(p.search(text) for p in _TERSE_TOOL_PATTERNS) and len(text) < 120:
        return False
    if "\n" in text or "```" in text or len(text) > 130:
        return True
    # Already sounds like a full conversational sentence from AI
    if intent in (None, "general_chat", "chat", "conversational_fast_path") and len(text.split()) >= 6:
        return True
    return False


def format_post_task_report(
    command: str = "",
    raw_result: str = "",
    success: bool = True,
    intent: Optional[str] = None,
    elapsed_s: float = 0.0,
    language_hint: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Wrap terse action confirmations or errors into a collaborative, human-sounding
    completion report, while keeping rich conversational / factual LLM answers clean and intact.
    """
    cfg = settings or get_persona_settings()
    clean_raw = (raw_result or "").strip()
    if intent and intent.lower() in ("wake_greeting", "voice_control", "screen_action", "screen_vision"):
        return clean_raw

    if not cfg.get("postTaskReports", True):
        return clean_raw

    lang = language_hint or detect_language_hint(f"{command} {clean_raw}", cfg=cfg)
    title = _style_title(cfg, lang)
    mem_size = int(cfg.get("recentMemorySize", 18))

    if not success:
        detail = re.sub(r"^error:\s*", "", clean_raw, flags=re.IGNORECASE).strip()
        if not detail:
            detail = "unexpected error occurred"
        if lang in ("hindi", "hinglish"):
            cands = [
                f"यहाँ एक अड़चन आ गई: {detail} — चलो इसे फिक्स करते हैं।",
                f"दिक्कत आ गई — यह स्टेप पूरा नहीं हुआ: {detail}। दूसरा तरीका आज़माऊँ?",
                f"यह टास्क अटक गया: {detail} — बताओ कैसे आगे बढ़ें?",
            ]
            if title:
                cands.append(f"एक दिक्कत आई है {title}: {detail} — कैसे हैंडल करें?")
        else:
            cands = [
                f"Hit a snag: {detail} — let's troubleshoot this.",
                f"Couldn't finish that cleanly: {detail} — should we try another way?",
                f"Ran into an issue: {detail} — how do you want to handle it?",
            ]
        return _utterance_memory.pick_fresh(f"post_err:{lang}", cands, memory_size=mem_size)

    # Preserve rich AI explanations / answers verbatim without wrapping
    if _looks_like_conversational_answer(clean_raw, intent=intent):
        return clean_raw

    # Proportionality Pillar: Instant reflex actions must be concise, natural, and never wrapped in boilerplate
    il = (intent or "").lower().strip()
    low_raw = clean_raw.lower()

    if il in ("open_app", "launch_app") or "successfully opened" in low_raw or "successfully launched" in low_raw:
        tgt_name = _extract_action_target(command) or (clean_raw.split("opened")[-1].strip() if "opened" in clean_raw else "") or "ऐप"
        tgt_name = tgt_name.strip(" .!:\"'").title()
        if lang in ("hindi", "hinglish"):
            cands = [
                f"{tgt_name} खोल दिया है।",
                f"{tgt_name} ओपन कर दिया।",
                f"{tgt_name} रेडी है।",
            ]
        else:
            cands = [
                f"Opened {tgt_name}.",
                f"{tgt_name} is open.",
                f"Launched {tgt_name}.",
            ]
        return _utterance_memory.pick_fresh(f"post_open:{lang}", cands, memory_size=mem_size)

    if il == "close_app" or "successfully closed" in low_raw:
        tgt_name = _extract_action_target(command) or "विंडो"
        tgt_name = tgt_name.strip(" .!:\"'").title()
        if lang in ("hindi", "hinglish"):
            cands = [
                f"{tgt_name} बंद कर दिया।",
                f"विंडो क्लोज़ कर दी।",
            ]
        else:
            cands = [
                f"Closed {tgt_name}.",
                f"{tgt_name} closed.",
            ]
        return _utterance_memory.pick_fresh(f"post_close:{lang}", cands, memory_size=mem_size)

    if il in ("media_control", "play_media") or clean_raw.startswith("🎵"):
        if clean_raw.startswith("🎵"):
            song_title = clean_raw.split(":", 1)[-1].strip().split("(")[0].strip() if ":" in clean_raw else ""
            song_title = song_title.strip(" .!")
            if song_title:
                return f"प्ले कर रही हूँ — {song_title}।" if lang in ("hindi", "hinglish") else f"Playing {song_title}."
            return clean_raw
        if lang in ("hindi", "hinglish"):
            return "चला दिया।"
        return "Playing."

    if il in ("volume_control", "set_brightness", "wifi_toggle", "bluetooth_toggle", "dark_mode_toggle"):
        if lang in ("hindi", "hinglish"):
            return "सेट कर दिया।"
        return "Done."

    if not clean_raw:
        clean_raw = "Task finished."

    detail_clean = clean_raw.rstrip(".!")
    is_multiline = "\n" in detail_clean

    if lang in ("hindi", "hinglish"):
        openers = [
            "हो गया —",
            "सेट है —",
            "बिल्कुल,",
            "डन —",
        ]
        dev_detail = detail_clean
        if not is_multiline:
            try:
                from ai_assistant.voice.text_cleaner import hinglish_to_devanagari
                dev_detail = hinglish_to_devanagari(detail_clean)
            except Exception:
                dev_detail = detail_clean
        cands = [f"{op}\n{clean_raw}" if is_multiline else f"{op} {dev_detail}।" for op in openers]
        if not is_multiline:
            cands.append(f"{dev_detail} रेडी है।")
            cands.append(f"सेट है — {dev_detail} पूरा हो गया।")
    else:
        openers = [
            "All set —",
            "Done —",
            "Sorted —",
            "Taken care of —",
        ]
        cands = [f"{op}\n{clean_raw}" if is_multiline else f"{op} {detail_clean}." for op in openers]
        if not is_multiline:
            cands.append(f"All set — {detail_clean}.")
            cands.append(f"{detail_clean} is ready.")

    if cfg.get("dynamicGeneration", True) and _variation_pool.need_refill(f"post_done:{lang}"):
        _variation_pool.warm_async(lang)

    return _utterance_memory.pick_fresh(f"post:{lang}", cands, memory_size=mem_size)


# ── Unified TTS Gate ─────────────────────────────────────────────────────────

_VOICE_ORIGIN_SOURCES = frozenset({
    "voice",
    "companion",
    "companion_voice",
    "companion_mascot",
    "streaming_vad",
    "wake_greeting",
    "voice_service_manager",
})


def should_speak_for_request(
    data: Optional[Dict[str, Any]] = None,
    intent: Optional[str] = None,
    force: Optional[bool] = None,
    default_for_chat: bool = False,
) -> bool:
    """
    Single authoritative rule deciding whether backend TTS should speak for a
    request across HTTP endpoints, SocketIO events, and desktop companion calls.
    """
    cfg = get_persona_settings()
    if not cfg.get("ttsEnabled", True):
        return False

    if force is not None:
        return bool(force)

    payload = data if isinstance(data, dict) else {}
    if payload.get("silent") or payload.get("no_tts"):
        return False

    if "speak" in payload and payload.get("speak") is not None:
        return bool(payload.get("speak"))

    if intent and intent.lower() == "voice_control":
        return True

    source = str(payload.get("source") or "").strip().lower()
    if source in _VOICE_ORIGIN_SOURCES or "voice" in source or "companion" in source:
        return True

    return bool(default_for_chat)


# ── Unified Turn Lifecycle Coordinator ───────────────────────────────────────

class CommandLifecycleCoordinator:
    """
    Synchronizes turn execution (`pre_report -> execution -> post_report`),
    monotonic barge-in cancellation (`turn_id`), live 4D orb state transitions,
    and unified single-speaker TTS output across all runtime surfaces.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._turn_seq = 0
        self._min_turn_id = 0
        self._active_turns: Dict[int, Dict[str, Any]] = {}

    def begin_turn(self, command: str = "", source: str = "chat", speak: bool = True) -> int:
        with self._lock:
            self._turn_seq += 1
            tid = self._turn_seq
            self._min_turn_id = tid
            self._active_turns.clear()
            self._active_turns[tid] = {
                "turn_id": tid,
                "command": command,
                "source": source,
                "speak": bool(speak),
                "stage": "pre",
                "started_at": time.monotonic(),
                "pre_report": None,
                "pre_spoken": False,
            }
            return tid

    def mark_executing(self, turn_id: Optional[int]) -> bool:
        if turn_id is None:
            return True
        with self._lock:
            entry = self._active_turns.get(turn_id)
            if entry is None or turn_id < self._min_turn_id:
                return False
            entry["stage"] = "executing"
            return True

    def is_turn_active(self, turn_id: Optional[int]) -> bool:
        if turn_id is None:
            return True
        with self._lock:
            return turn_id in self._active_turns and turn_id >= self._min_turn_id

    def has_executing_turn(self) -> bool:
        with self._lock:
            return any(t.get("stage") in ("pre", "executing") for t in self._active_turns.values())

    def cancel_all(self, reason: str = "barge_in") -> None:
        with self._lock:
            self._turn_seq += 1
            self._min_turn_id = self._turn_seq + 1
            self._active_turns.clear()
        logger.debug(f"[Lifecycle] Cancelled active turns ({reason})")

    # ── Helpers to talk to voice_service / TTS / SocketIO safely ──

    @staticmethod
    def _get_voice_mod():
        return sys.modules.get("voice_service") or sys.modules.get("backend.voice_service")

    @staticmethod
    def _get_socketio():
        vs = sys.modules.get("voice_service") or sys.modules.get("backend.voice_service")
        if vs is not None:
            sio = getattr(vs, "_socketio", None)
            if sio is not None:
                return sio
        for mod_path in ("routes.common", "backend.routes.common"):
            cm = sys.modules.get(mod_path)
            if cm is not None and hasattr(cm, "get_socketio"):
                try:
                    sio = cm.get_socketio()
                    if sio is not None:
                        return sio
                except Exception:
                    pass
        return None

    @staticmethod
    def _get_tts_service():
        try:
            from ai_assistant.voice.tts_output_service import get_tts_service
            return get_tts_service()
        except Exception:
            return None

    def _emit_status(self, payload: Dict[str, Any]) -> None:
        sio = self._get_socketio()
        if sio is None:
            return
        try:
            sio.emit("command_status", payload)
        except Exception as exc:
            logger.debug(f"command_status emit note: {exc}")

    def _update_overlay(self, **kwargs) -> Optional[Dict[str, Any]]:
        vs = self._get_voice_mod()
        if vs is None or not hasattr(vs, "update_overlay_state"):
            return None
        try:
            return vs.update_overlay_state(**kwargs)
        except Exception:
            return None

    def _schedule_idle(self, delay_sec: float, snap: Optional[Dict[str, Any]]) -> None:
        if not snap or "updated_at" not in snap:
            return
        vs = self._get_voice_mod()
        if vs is not None and hasattr(vs, "_schedule_overlay_idle"):
            try:
                vs._schedule_overlay_idle(delay_sec, snap["updated_at"])
            except Exception:
                pass

    # ── Core Pre / Post Execution Hooks ──

    def emit_pre_report(
        self,
        turn_id: Optional[int],
        command: str,
        *,
        intent: Optional[str] = None,
        target: Optional[str] = None,
        source: str = "chat",
        language_hint: Optional[str] = None,
        speak: bool = True,
        wait_brief: bool = False,
        stream_tts_gen: Optional[int] = None,
    ) -> Optional[str]:
        if not self.is_turn_active(turn_id):
            return None

        cfg = get_persona_settings()
        pre_text = generate_pre_task_report(
            command=command,
            intent=intent,
            target=target,
            language_hint=language_hint,
            source=source,
            settings=cfg,
        )

        self.mark_executing(turn_id)
        if not pre_text:
            return None

        with self._lock:
            if turn_id in self._active_turns:
                self._active_turns[turn_id]["pre_report"] = pre_text

        self._update_overlay(
            state="processing",
            transcript=command,
            error_message="",
            source=f"{source}_pre",
        )
        self._emit_status({
            "turn_id": turn_id,
            "phase": "pre_report",
            "status": pre_text,
            "command": command,
            "source": source,
            "intent": intent or _infer_action_category(command, intent),
            "timestamp": _dt.datetime.now().isoformat(),
        })

        if speak and cfg.get("ttsEnabled", True) and self.is_turn_active(turn_id):
            tts_svc = self._get_tts_service()
            if tts_svc is not None:
                try:
                    if stream_tts_gen is not None:
                        spoke = bool(tts_svc.enqueue_sentence(pre_text, gen=stream_tts_gen, source=f"{source}_pre"))
                    else:
                        spoke = bool(
                            tts_svc.speak(
                                pre_text,
                                interrupt=True,
                                wait=wait_brief,
                                timeout=2.2 if wait_brief else None,
                                source=f"{source}_pre",
                            )
                        )
                    with self._lock:
                        if turn_id in self._active_turns:
                            self._active_turns[turn_id]["pre_spoken"] = spoke
                    if spoke and pre_text:
                        try:
                            from ai_assistant.core.speech_text_crisper import record_recent_tts
                            record_recent_tts(pre_text)
                        except Exception:
                            pass
                except Exception as exc:
                    logger.debug(f"Pre-report TTS skipped: {exc}")

        return pre_text

    def complete_turn(
        self,
        turn_id: Optional[int],
        command: str,
        raw_result: str,
        *,
        success: bool = True,
        intent: Optional[str] = None,
        source: str = "chat",
        speak: bool = True,
        language_hint: Optional[str] = None,
        emit_response: bool = False,
        extra_payload: Optional[Dict[str, Any]] = None,
        tts_already_queued: bool = False,
        tts_text_override: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """
        Finalize an active turn: format natural completion report, verify turn wasn't
        cancelled by barge-in, queue post-report TTS with `interrupt=False` (never
        cutting off pre-report), and update 4D orb & SocketIO state.
        Returns `(formatted_response, was_active)`.
        """
        turn_entry = None
        cancelled = False
        with self._lock:
            if turn_id is not None:
                if turn_id < self._min_turn_id:
                    cancelled = True
                    self._active_turns.pop(turn_id, None)
                else:
                    turn_entry = self._active_turns.pop(turn_id, None)
                    if turn_entry is None:
                        cancelled = True

        elapsed_s = (time.monotonic() - turn_entry["started_at"]) if turn_entry else 0.0
        pre_spoken = bool(turn_entry.get("pre_spoken")) if turn_entry else False

        formatted = format_post_task_report(
            command=command,
            raw_result=raw_result,
            success=success,
            intent=intent,
            elapsed_s=elapsed_s,
            language_hint=language_hint,
        )

        if cancelled:
            logger.info(f"[Lifecycle] Suppressed stale output for cancelled turn {turn_id}")
            self._update_overlay(state="idle", source=source)
            return formatted, False

        cfg = get_persona_settings()
        speech_target = (tts_text_override or formatted or "").strip()
        if tts_text_override and success and not _looks_like_conversational_answer(tts_text_override, intent=intent):
            speech_target = formatted or tts_text_override

        spoke = False
        if (
            not tts_already_queued
            and speak
            and speech_target
            and cfg.get("ttsEnabled", True)
        ):
            tts_svc = self._get_tts_service()
            if tts_svc is not None:
                try:
                    # Queue seamlessly behind any active pre-report without interrupting it
                    interrupt_flag = not pre_spoken
                    spoke = bool(tts_svc.speak(speech_target, interrupt=interrupt_flag, source=f"{source}_post"))
                    if spoke and speech_target:
                        try:
                            from ai_assistant.core.speech_text_crisper import record_recent_tts
                            record_recent_tts(speech_target)
                        except Exception:
                            pass
                except Exception as exc:
                    logger.debug(f"Post-report TTS skipped: {exc}")

        if not success:
            snap = self._update_overlay(state="error", error_message=formatted, source=source)
            self._schedule_idle(3.5, snap)
        elif spoke or tts_already_queued:
            snap = self._update_overlay(state="speaking", source=source)
            self._schedule_idle(min(10.0, max(2.5, len(speech_target) * 0.065)), snap)
        else:
            self._update_overlay(state="idle", source=source)

        if success and command and formatted:
            try:
                from ai_assistant.ai.memory_retrieval import persist_turn_to_conversation_ai
                threading.Thread(
                    target=persist_turn_to_conversation_ai,
                    args=(command, formatted),
                    kwargs={"source": source or "companion"},
                    daemon=True,
                ).start()
            except Exception:
                pass

        self._emit_status({
            "turn_id": turn_id,
            "phase": "completed" if success else "failed",
            "status": "",
            "command": command,
            "source": source,
            "elapsed_ms": round(elapsed_s * 1000, 1),
            "timestamp": _dt.datetime.now().isoformat(),
        })

        if emit_response:
            sio = self._get_socketio()
            if sio is not None:
                payload = {
                    "success": bool(success),
                    "response": formatted,
                    "command": command,
                    "source": source,
                    "skip_tts": True,
                    "timestamp": _dt.datetime.now().isoformat(),
                }
                if extra_payload:
                    payload.update(extra_payload)
                try:
                    sio.emit("command_response", payload)
                except Exception as exc:
                    logger.debug(f"emit_response error: {exc}")

        return formatted, True

    def speak_proactive_report(
        self,
        title: str = "",
        summary: str = "",
        source: str = "background_task",
        speak: bool = True,
    ) -> str:
        """Announce completion of an asynchronous background task naturally."""
        cfg = get_persona_settings()
        body = (summary or "").strip()
        lang = detect_language_hint(f"{title} {body}", cfg=cfg)
        user_title = _style_title(cfg, lang)
        t_suffix = f" {user_title}" if user_title else ""

        if lang == "hindi":
            prefix = f"अपडेट तैयार है{t_suffix} — "
        elif lang == "hinglish":
            prefix = f"Update ready hai{t_suffix} — "
        else:
            prefix = f"Update ready{t_suffix} — "

        full_text = f"{prefix}{body}" if body else f"{prefix}{title}".strip()

        if speak and cfg.get("postTaskReports", True) and cfg.get("ttsEnabled", True):
            tts_svc = self._get_tts_service()
            if tts_svc is not None:
                try:
                    # Queue gently without cutting off ongoing speech
                    tts_svc.speak(full_text[:280], interrupt=False, source=source)
                except Exception:
                    pass

        sio = self._get_socketio()
        if sio is not None:
            try:
                sio.emit("command_status", {
                    "phase": "proactive_update",
                    "status": full_text[:220],
                    "source": source,
                    "timestamp": _dt.datetime.now().isoformat(),
                })
            except Exception:
                pass
        return full_text


_lifecycle_coordinator: Optional[CommandLifecycleCoordinator] = None
_coordinator_lock = threading.Lock()


def get_lifecycle_coordinator() -> CommandLifecycleCoordinator:
    global _lifecycle_coordinator
    if _lifecycle_coordinator is None:
        with _coordinator_lock:
            if _lifecycle_coordinator is None:
                _lifecycle_coordinator = CommandLifecycleCoordinator()
    return _lifecycle_coordinator
