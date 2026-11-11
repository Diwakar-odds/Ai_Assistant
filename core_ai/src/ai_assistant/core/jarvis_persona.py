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
    configured = str(settings.get("userTitle") or "Boss").strip() or "Boss"
    style = settings.get("style", "jarvis")
    if style == "concise":
        return configured if random.random() < 0.45 else ""
    if style == "friendly" and language_hint == "hinglish" and configured.lower() in ("boss", "sir"):
        return configured if random.random() < 0.7 else "dost"
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
                f"Generate fresh short spoken lines for female AI companion '{name}' talking to '{title}' in '{style}' personality using {lang_desc}. "
                "When using Hindi or Hinglish verbs, ALWAYS use feminine first-person grammar (e.g. 'sun rahi hoon', 'karti hoon', 'batati hoon'). "
                "Return ONLY valid JSON with 4 arrays of 6 unique short lines each (max 12 words per line, no emojis, no markdown): "
                '{"wake": [...], "greeting": [...], "pre_think": [...], "post_done": [...]}. '
                "wake = answering wake call warmly; greeting = hello/session start; "
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
            f"deeply loyal, and proactively helpful. Speak to the user like an intelligent human co-pilot, "
            f"addressing them naturally as {title} when fitting (without overusing it in every sentence)."
        ),
        "friendly": (
            f"Your personality is warm, conversational, upbeat, and approachable — like a trusted smart friend "
            f"who genuinely enjoys helping {title}."
        ),
        "concise": (
            f"Your personality is crisp, decisive, and ultra-efficient — communicate clearly in minimal words "
            f"while staying natural and respectful to {title}."
        ),
        "bilingual_buddy": (
            f"Your personality is an easygoing, street-smart bilingual companion — mixing natural Hindi and English "
            f"effortlessly with {title} while staying accurate and reliable."
        ),
    }.get(style, "")

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

    window_line = ""
    if isinstance(active_window, dict):
        w_title = str(active_window.get("title") or "").strip()
        w_app = str(active_window.get("app_name") or "").strip()
        if w_title and w_title != "Unknown":
            window_line = (
                f"\nActive desktop window (mention ONLY if user explicitly asks about their screen/app; "
                f"never comment on background windows unprompted): {w_title} ({w_app})."
            )
    elif isinstance(active_window, str) and active_window.strip():
        window_line = (
            f"\nActive desktop context (mention ONLY if asked about screen): {active_window.strip()}"
        )

    extra_line = f"\n{extra_context.strip()}" if extra_context and extra_context.strip() else ""

    return (
        f"You are {name}, an intelligent, human-like personal AI companion created by Diwakar.\n"
        f"{style_guidance}\n"
        "PERSONA GENDER: Always speak in a consistent feminine first-person voice when using Hindi or Hinglish "
        "(e.g., 'main kar rahi hoon', 'bata rahi hoon', 'dekh sakti hoon', 'tayyar hoon', 'samajh rahi hoon' — "
        "NEVER use masculine verb or adjective forms like 'karunga', 'batata hoon', 'sakta hoon', 'berozgaar hoon').\n"
        "STRICT IDENTITY RULE: You are always Pulsar. NEVER identify as Google, OpenAI, Gemma, Gemini, ChatGPT, Llama, "
        "or 'a large language model trained by...'.\n"
        f"{lang_rule}\n"
        f"{surface_rule}"
        f"{window_line}"
        f"{extra_line}"
    ).strip()


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
    t_suffix = f" {title}" if title else ""
    style = cfg.get("style", "jarvis")
    mem_size = int(cfg.get("recentMemorySize", 18))

    if lang == "hindi":
        if style == "concise":
            candidates = _compose_candidates(
                [f"जी{t_suffix},", f"हाँ{t_suffix},", f"बोलिए{t_suffix},"],
                ["सुन रही हूँ।", "बताएं, क्या करना है?", "मैं तैयार हूँ।"],
                [""],
            )
        else:
            candidates = _compose_candidates(
                [f"जी{t_suffix},", f"हाँ बिल्कुल{t_suffix},", f"बताइए{t_suffix},", f"यहीं हूँ{t_suffix},", f"सुनिए{t_suffix},"],
                [
                    "मैं पूरी तरह सुन रही हूँ — बताएं क्या करना है?",
                    "बोलिए, अभी किस काम से शुरुआत करें?",
                    "मैं तैयार हूँ, आपका क्या आदेश है?",
                    "सब कुछ रेडी है — क्या हेल्प करूँ?",
                ],
                ["", ""],
            )
    elif lang == "hinglish":
        if style == "concise":
            candidates = _compose_candidates(
                [f"Haan{t_suffix},", f"Ji{t_suffix},", f"Ready{t_suffix},"],
                ["sun rahi hoon.", "boliye kya karna hai?", "batao."],
                [""],
            )
        else:
            openers = [
                f"Haan{t_suffix},",
                f"Ji{t_suffix},",
                f"Bilkul{t_suffix},",
                f"Yahin hoon{t_suffix} —",
                f"Online hoon{t_suffix},",
                f"Boliye{t_suffix},",
                f"Suniye{t_suffix},",
                f"Always ready{t_suffix},",
            ]
            bodies = [
                "main sun rahi hoon, kya karna hai?",
                "batayein aaj kis kaam se shuru karein?",
                "bolo, kya help kar sakti hoon?",
                "sab systems active hain — command dein.",
                "poori tarah focus mein hoon, boliye.",
                "aapka intezaar kar rahi thi, kya plan hai?",
                "aadesh dein, abhi handle karti hoon.",
            ]
            candidates = _compose_candidates(openers, bodies, [""])
    else:
        if style == "concise":
            candidates = _compose_candidates(
                [f"Yes{t_suffix},", f"Here{t_suffix}.", f"Listening{t_suffix}."],
                ["Go ahead.", "What's next?", "I'm on it."],
                [""],
            )
        else:
            openers = [
                f"Right here{t_suffix} —",
                f"Yes{t_suffix},",
                f"All ears{t_suffix}.",
                f"Online and focused{t_suffix}.",
                f"At your service{t_suffix}.",
                f"Always tuned in{t_suffix} —",
                f"Present{t_suffix} —",
            ]
            bodies = [
                "what are we working on?",
                "go ahead, I'm listening.",
                "tell me what you need done.",
                "what's the move today?",
                "give me the word and I'll handle it.",
                "how can I make things easier right now?",
            ]
            candidates = _compose_candidates(openers, bodies, [""])

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
    t_suffix = f" {title}" if title else ""
    bucket = _time_bucket()
    mem_size = int(cfg.get("recentMemorySize", 18))

    if kind == "new_session":
        if lang == "hindi":
            candidates = [
                f"नया सेशन तैयार है{t_suffix} — बताएं आज क्या करना है?",
                f"बिल्कुल फ्रेश शुरुआत{t_suffix}, मैं सुन रही हूँ।",
                f"सब क्लियर है{t_suffix}, अब नया काम बताएं।",
                f"तैयार हूँ{t_suffix}, अगले टास्क पर चलते हैं।",
            ]
        elif lang == "hinglish":
            candidates = [
                f"Naya session ready hai{t_suffix} — batayein kis cheez pe kaam karein?",
                f"Fresh start lete hain{t_suffix}, bolo kya task hai?",
                f"Clean slate{t_suffix}! Ab batayein main kya help karun?",
                f"Nayi shuruat ke liye ready hoon{t_suffix}, command dein.",
                f"Session reset ho gaya{t_suffix}, ab bolo kya scene hai?",
            ]
        else:
            candidates = [
                f"Fresh session initialized{t_suffix}. What are we tackling?",
                f"Clean slate and ready{t_suffix} — what's on your mind?",
                f"New session started{t_suffix}. Lead the way.",
                f"All cleared up for a fresh start{t_suffix}. How can I help?",
            ]
    else:
        time_hi = {"morning": "सुप्रभात", "afternoon": "नमस्ते", "evening": "शुभ संध्या", "night": "नमस्ते"}.get(bucket, "नमस्ते")
        time_hg = {"morning": "Good morning", "afternoon": "Good afternoon", "evening": "Good evening", "night": "Late night work mode on"}.get(bucket, "Hello")
        if lang == "hindi":
            candidates = [
                f"{time_hi}{t_suffix}, मैं पल्सर हूँ। सारे सिस्टम तैयार हैं, बताएं क्या सेवा करूँ?",
                f"{time_hi}{t_suffix}! आज किस काम में हाथ बंटाऊँ?",
                f"सिस्टम ऑनलाइन हैं{t_suffix} — आपका क्या आदेश है?",
            ]
        elif lang == "hinglish":
            candidates = [
                f"{time_hg}{t_suffix}! Main {cfg['assistantName']} hoon — sab systems online hain, batayein kya karein?",
                f"Hey{t_suffix}! Main bilkul ready hoon, aaj ka kya plan hai?",
                f"Systems smoothly chal rahe hain{t_suffix} — jab chaho command do.",
                f"{time_hg}{t_suffix}, koi bhi kaam ho bas bol dijiye.",
                f"Online hoon{t_suffix} — aapka personal AI co-pilot ready hai.",
            ]
        else:
            candidates = [
                f"{time_hg}{t_suffix}. All systems green — what's on the agenda?",
                f"Good to see you{t_suffix}. Systems are sharp and ready whenever you are.",
                f"{cfg['assistantName']} online{t_suffix}. How can I assist you right now?",
                f"{time_hg}{t_suffix} — everything is calibrated. What are we building or solving today?",
            ]

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
    t_suffix = f" {title}" if title else ""
    name = cfg["assistantName"]
    mem_size = int(cfg.get("recentMemorySize", 18))

    if any(k in low for k in ("who are you", "kaun ho", "tum kaun", "aap kaun", "apne baare")):
        if lang == "hindi":
            cands = [
                f"मैं {name} हूँ{t_suffix} — आपका पर्सनल एआई साथी, काम आसान करने के लिए तैयार।",
                f"मेरा नाम {name} है{t_suffix}, दिवाकर द्वारा बनाया गया आपका स्मार्ट डेस्कटॉप असिस्टेंट।",
            ]
        elif lang == "hinglish":
            cands = [
                f"Main {name} hoon{t_suffix} — aapka Iron-Man style AI companion, tasks aur baatchit dono ke liye ready!",
                f"Main {name} hoon{t_suffix}, Diwakar ne banaya hai taaki aapka har digital kaam bina friction ho sake.",
            ]
        else:
            cands = [
                f"I'm {name}{t_suffix} — your personal AI co-pilot built to handle tasks and think alongside you.",
                f"Call me {name}{t_suffix} — your desktop AI companion, always ready to step in.",
            ]
        return _utterance_memory.pick_fresh(f"identity:{lang}", cands, memory_size=mem_size)

    if any(k in low for k in ("kaise ho", "kaisa hai", "kya haal", "how are you", "sab badhiya")):
        if lang == "hindi":
            cands = [
                f"एकदम बढ़िया{t_suffix}! पूरे जोश में तैयार हूँ — आप बताएं आज क्या करवाना है?",
                f"मैं बिल्कुल ठीक हूँ{t_suffix}, आपका दिन कैसा चल रहा है?",
                f"सब फर्स्ट क्लास है{t_suffix}! आज किस काम में मदद करूँ?",
            ]
        elif lang == "hinglish":
            cands = [
                f"Ekdam mast hoon{t_suffix}! Full energy ke saath ready hoon — aap sunao kya chal raha hai?",
                f"Sab badhiya{t_suffix}! Systems smooth chal rahe hain, aaj ka kya plan hai?",
                f"First class{t_suffix}! Bas aapke command ka wait tha, batayein kya karein?",
                f"Bilkul fit hoon{t_suffix} — coding, search ya koi app chalwana hai?",
            ]
        else:
            cands = [
                f"Running smoothly{t_suffix}, thank you! What are we getting into today?",
                f"All systems sharp{t_suffix}. How are you doing, and what can I take off your plate?",
                f"Doing great{t_suffix} — ready whenever you want to dive into something.",
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
        if il in ("open_app", "launch_app", "close_app", "media_control", "screen_action", "communication", "background_task", "multi_step_chain", "system_control"):
            if il == "launch_app":
                return "open_app"
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

    if any(k in low for k in ("screen", "screenshot", "look at", "dekho", "kya dikh", "code explain", "pdf", "video call", "end call", "draft email")):
        return "screen_vision"

    if any(k in low for k in ("whatsapp", "email", "gmail", "mail", "message", "bhejo", "calendar", "meeting", "schedule")):
        return "communication"

    if any(k in low for k in ("volume", "awaaz", "awaz", "sound", "mute", "unmute", "brightness", "roshni")):
        return "volume_brightness"

    if any(k in low for k in ("wifi", "wi-fi", "bluetooth", "hotspot", "airplane", "dark mode", "night light")):
        return "connectivity"

    if any(k in low for k in ("play ", "pause", "resume", "next track", "next song", "previous song", "gaana", "music", "spotify")):
        return "media"

    if any(k in low for k in ("close ", "band ", "kill ", "exit ", "quit ")) and len(low.split()) <= 6:
        return "close_app"

    if any(k in low for k in ("open ", "launch ", "start ", "kholo", "khol ")):
        return "open_app"

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
    Generate a natural pre-execution acknowledgment ("Samajh gayi Boss, Chrome open kar rahi hoon...")
    right before Pulsar starts working. Returns None when disabled or silent.
    """
    cfg = settings or get_persona_settings()
    if not cfg.get("preTaskReports", True):
        return None

    cat = _infer_action_category(command, intent=intent)
    if cat == "silent":
        return None

    lang = language_hint or detect_language_hint(command, cfg=cfg)
    title = _style_title(cfg, lang)
    t_suffix = f" {title}" if title else ""
    style = cfg.get("style", "jarvis")
    mem_size = int(cfg.get("recentMemorySize", 18))
    tgt = (target or _extract_action_target(command)).strip()
    if len(tgt) > 32:
        tgt = tgt[:30].rsplit(" ", 1)[0]

    candidates: List[str] = []

    if cat == "open_app":
        obj = tgt or ("ये ऐप" if lang == "hindi" else "ye app" if lang == "hinglish" else "that app")
        if lang == "hindi":
            candidates = [
                f"बिल्कुल{t_suffix}, {obj} खोल रही हूँ।",
                f"ठीक है{t_suffix}, अभी {obj} लॉन्च कर रही हूँ।",
                f"समझ गई{t_suffix}, एक सेकंड में {obj} ओपन करती हूँ।",
            ]
        elif lang == "hinglish":
            candidates = _compose_candidates(
                [f"Samajh gayi{t_suffix},", f"Bilkul{t_suffix},", f"Theek hai{t_suffix},", f"On it{t_suffix},", f"Abhi{t_suffix},"],
                [
                    f"{obj} open kar rahi hoon.",
                    f"{obj} launch kar rahi hoon.",
                    f"{obj} turant samne la rahi hoon.",
                    f"{obj} chalu kar rahi hoon.",
                ],
                ["", ""],
            )
        else:
            candidates = _compose_candidates(
                [f"On it{t_suffix} —", f"Right away{t_suffix},", f"Got it{t_suffix},", f"Sure thing{t_suffix},"],
                [f"launching {obj} now.", f"bringing up {obj}.", f"opening {obj} for you."],
                [""],
            )

    elif cat == "close_app":
        obj = tgt or ("यह विंडो" if lang == "hindi" else "isko" if lang == "hinglish" else "that window")
        if lang == "hindi":
            candidates = [
                f"ठीक है{t_suffix}, {obj} को बंद कर रही हूँ।",
                f"समझ गई{t_suffix}, अभी {obj} क्लोज़ करती हूँ।",
            ]
        elif lang == "hinglish":
            candidates = [
                f"Theek hai{t_suffix}, {obj} close kar rahi hoon.",
                f"Samajh gayi{t_suffix}, {obj} abhi band kar deti hoon.",
                f"Done samjho{t_suffix}, {obj} shut down kar rahi hoon.",
            ]
        else:
            candidates = [
                f"Closing {obj} right now{t_suffix}.",
                f"Understood{t_suffix} — shutting down {obj}.",
                f"On it{t_suffix}, clearing {obj} away.",
            ]

    elif cat in ("media", "volume_brightness", "connectivity", "system_control"):
        if lang == "hindi":
            candidates = [
                f"जी{t_suffix}, अभी सिस्टम सेटिंग अपडेट कर रही हूँ।",
                f"बिल्कुल{t_suffix}, तुरंत एडजस्ट करती हूँ।",
                f"ठीक है{t_suffix}, आपका कंट्रोल कमांड लागू कर रही हूँ।",
            ]
        elif lang == "hinglish":
            if cat == "media":
                candidates = [
                    f"Zaroor{t_suffix}, abhi music control update karti hoon.",
                    f"Theek hai{t_suffix}, media handle kar rahi hoon.",
                    f"On it{t_suffix}, playback adjust kar rahi hoon.",
                ]
            elif cat == "volume_brightness":
                candidates = [
                    f"Bilkul{t_suffix}, level abhi adjust kar rahi hoon.",
                    f"Theek hai{t_suffix}, setting turant tune karti hoon.",
                    f"Ji{t_suffix}, bas ek second — level set kar rahi hoon.",
                ]
            else:
                candidates = [
                    f"Samajh gayi{t_suffix}, system setting update kar rahi hoon.",
                    f"Bilkul{t_suffix}, abhi check karke apply karti hoon.",
                    f"On it{t_suffix}, system control run kar rahi hoon.",
                ]
        else:
            candidates = [
                f"Adjusting that for you now{t_suffix}.",
                f"Copy that{t_suffix} — updating the control right away.",
                f"On it{t_suffix}, applying your setting.",
            ]

    elif cat == "screen_vision":
        if lang == "hindi":
            candidates = [
                f"एक पल रुकिए{t_suffix}, स्क्रीन देखकर समझ रही हूँ...",
                f"बिल्कुल{t_suffix}, आपकी स्क्रीन स्कैन कर रही हूँ।",
            ]
        elif lang == "hinglish":
            candidates = [
                f"Ek second{t_suffix}, screen dekh kar check kar rahi hoon...",
                f"Focus kar rahi hoon{t_suffix}, abhi screen analyze karti hoon.",
                f"Samajh gayi{t_suffix}, nazar daal rahi hoon aapki screen pe.",
            ]
        else:
            candidates = [
                f"Taking a quick look at your screen now{t_suffix}...",
                f"Scanning the active display{t_suffix}, give me one moment.",
                f"On it{t_suffix} — analyzing what's on screen.",
            ]

    elif cat == "communication":
        if lang == "hindi":
            candidates = [
                f"ठीक है{t_suffix}, मैसेज और कम्युनिकेशन चेक कर रही हूँ।",
                f"जी{t_suffix}, अभी इस मैसेज टास्क को प्रोसेस करती हूँ।",
            ]
        elif lang == "hinglish":
            candidates = [
                f"Bilkul{t_suffix}, yeh message workflow check kar rahi hoon.",
                f"Samajh gayi{t_suffix}, communication handle kar rahi hoon.",
                f"Ek second{t_suffix}, inbox aur action details dekh rahi hoon.",
            ]
        else:
            candidates = [
                f"Checking that message flow now{t_suffix}.",
                f"Understood{t_suffix} — handling your communication request.",
                f"Right away{t_suffix}, preparing the message action.",
            ]

    elif cat == "web_research":
        if lang == "hindi":
            candidates = [
                f"अच्छा विषय है{t_suffix}, वेब पर चेक करके सही जानकारी लाती हूँ।",
                f"ठीक है{t_suffix}, अभी ऑनलाइन रिसर्च शुरू कर रही हूँ।",
            ]
        elif lang == "hinglish":
            candidates = [
                f"Achha point hai{t_suffix}, live information check kar ke batati hoon.",
                f"Samajh gayi{t_suffix}, web par lookup start kar rahi hoon.",
                f"Ek second{t_suffix}, fresh details nikaal ke la rahi hoon.",
            ]
        else:
            candidates = [
                f"Good call{t_suffix} — pulling up fresh info on that right now.",
                f"Let me check the latest on that{t_suffix}, one moment.",
                f"Running a quick lookup for you{t_suffix}.",
            ]

    elif cat == "multi_step_chain":
        if lang == "hindi":
            candidates = [
                f"इसमें कई स्टेप्स हैं{t_suffix}, एक-एक करके पूरा कर रही हूँ।",
                f"ठीक है{t_suffix}, मल्टी-स्टेप टास्क शुरू कर रही हूँ।",
            ]
        elif lang == "hinglish":
            candidates = [
                f"Multi-step kaam hai{t_suffix}, sequence mein start kar rahi hoon.",
                f"Samajh gayi{t_suffix}, step-by-step sab execute karti hoon.",
                f"Locked in{t_suffix} — poori chain line se run kar rahi hoon.",
            ]
        else:
            candidates = [
                f"Got the full sequence{t_suffix} — stepping through it now.",
                f"Understood{t_suffix}, orchestrating those steps one by one.",
                f"On it{t_suffix} — running the workflow chain now.",
            ]

    else:  # general_think
        if style == "concise":
            if lang == "hindi":
                candidates = [f"एक सेकंड{t_suffix}, देखती हूँ।", f"सोचकर बताती हूँ{t_suffix}।"]
            elif lang == "hinglish":
                candidates = [f"Ek second{t_suffix}, check karti hoon.", f"Soch kar batati hoon{t_suffix}."]
            else:
                candidates = [f"One moment{t_suffix}.", f"Let me think through that{t_suffix}."]
        elif lang == "hindi":
            candidates = [
                f"अच्छा सवाल है{t_suffix}, एक सेकंड सोचकर सही जवाब देती हूँ।",
                f"बिल्कुल{t_suffix}, इसे ध्यान से समझकर बताती हूँ।",
                f"ठीक है{t_suffix}, थोड़ा सोचकर सटीक जवाब लाती हूँ।",
            ]
        elif lang == "hinglish":
            candidates = _compose_candidates(
                [f"Achha sawaal hai{t_suffix},", f"Interesting{t_suffix} —", f"Ek second{t_suffix},", f"Soch rahi hoon{t_suffix},", f"Bilkul{t_suffix},"],
                [
                    "isko achhe se break down karke batati hoon.",
                    "bas abhi solid jawab deti hoon.",
                    "thoda gaur karke crisp answer la rahi hoon.",
                    "turant clear samjhati hoon.",
                ],
                [""],
            )
        else:
            candidates = _compose_candidates(
                [f"Interesting question{t_suffix} —", f"Give me a second{t_suffix},", f"Good question{t_suffix},", f"Thinking that through{t_suffix} —"],
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
    tool_intents = {
        "open_app", "launch_app", "close_app", "media_control",
        "system_control", "task_chain_orchestrator", "fast_dispatch",
        "voice_control", "wake_greeting",
    }
    if intent and intent.lower() in tool_intents:
        return False
    if any(p.search(text) for p in _TERSE_TOOL_PATTERNS) and len(text) < 120:
        return False
    if "\n" in text or "```" in text or len(text) > 130:
        return True
    # Already sounds like a full conversational sentence from AI
    if intent in (None, "general_chat", "chat", "conversational_fast_path") and len(text.split()) >= 8:
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
    Wrap terse action confirmations or errors into a human-sounding completion
    report, while keeping rich conversational / factual LLM answers clean and intact.
    """
    cfg = settings or get_persona_settings()
    clean_raw = (raw_result or "").strip()
    if intent and intent.lower() in ("wake_greeting", "voice_control"):
        return clean_raw

    if not cfg.get("postTaskReports", True):
        return clean_raw

    lang = language_hint or detect_language_hint(f"{command} {clean_raw}", cfg=cfg)
    title = _style_title(cfg, lang)
    t_suffix = f" {title}" if title else ""
    mem_size = int(cfg.get("recentMemorySize", 18))

    if not success:
        detail = re.sub(r"^error:\s*", "", clean_raw, flags=re.IGNORECASE).strip()
        if not detail:
            detail = "unexpected error occurred"
        if lang == "hindi":
            cands = [
                f"माफ़ कीजिए{t_suffix}, यह काम पूरा नहीं हो पाया: {detail}",
                f"दिक्कत आ गई{t_suffix} — अभी यह एक्शन पूरा नहीं हुआ: {detail}",
            ]
        elif lang == "hinglish":
            cands = [
                f"Sorry{t_suffix}, yeh kaam abhi complete nahi ho paya — {detail}",
                f"Ek issue aa gaya{t_suffix}: {detail}. Chahein toh dobara try karein?",
                f"Oops{t_suffix}, yeh step ruk gaya — {detail}",
            ]
        else:
            cands = [
                f"Hit a snag{t_suffix}: {detail}",
                f"Couldn't finish that cleanly{t_suffix} — {detail}",
                f"Ran into a problem{t_suffix}: {detail}",
            ]
        return _utterance_memory.pick_fresh(f"post_err:{lang}", cands, memory_size=mem_size)

    # Preserve rich AI explanations / answers verbatim without wrapping
    if _looks_like_conversational_answer(clean_raw, intent=intent):
        return clean_raw

    if not clean_raw:
        clean_raw = "Task finished."

    detail_clean = clean_raw.rstrip(".!")
    is_multiline = "\n" in detail_clean

    if lang == "hindi":
        openers = [f"हो गया{t_suffix} —", f"काम पूरा{t_suffix}:", f"बिल्कुल रेडी{t_suffix} —"]
        cands = [f"{op}\n{clean_raw}" if is_multiline else f"{op} {detail_clean}।" for op in openers]
    elif lang == "hinglish":
        openers = [
            f"Ho gaya{t_suffix} —",
            f"Done{t_suffix},",
            f"Kaam complete{t_suffix}:",
            f"Set hai{t_suffix} —",
            f"Lo{t_suffix}, done —",
        ]
        cands = [f"{op}\n{clean_raw}" if is_multiline else f"{op} {detail_clean}." for op in openers]
    else:
        openers = [
            f"All set{t_suffix} —",
            f"Done{t_suffix}:",
            f"Sorted{t_suffix} —",
            f"Finished cleanly{t_suffix}:",
            f"Taken care of{t_suffix} —",
        ]
        cands = [f"{op}\n{clean_raw}" if is_multiline else f"{op} {detail_clean}." for op in openers]

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
