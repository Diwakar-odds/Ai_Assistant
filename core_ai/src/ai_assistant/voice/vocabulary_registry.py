"""
Vocabulary, Custom Dictionary & Deterministic Grammar Registry
============================================================
Central registry for:
1. User-custom vocabulary (names, profiles, technical terms, apps, Hinglish slang).
2. STT Whisper Vocabulary Biasing (initial_prompt keywords).
3. STT Transcript Normalization (phonetic mishearing correction).
4. TTS Phonetic & Devanagari Mapping for EdgeTTS / KittenTTS.
5. Deterministic First-Person Feminine Grammar Enforcement.
6. Anti-Servant / Tone Guardrail Filter.

Storage: `data/user_preferences/user_dictionary.json`
Thread-safe, sub-millisecond in-memory cache with atomic file writes.
"""

import json
import logging
import re
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

_DEFAULT_WORDS = {
    "diwakar": {"devanagari": "दिवाकर", "spoken": "Diwakar", "category": "user_name"},
    "rancho": {"devanagari": "रांचो", "spoken": "Rancho", "category": "profile"},
    "vs code": {"devanagari": "वीएस कोड", "spoken": "VS Code", "category": "app"},
    "vscode": {"devanagari": "वीएस कोड", "spoken": "VS Code", "category": "app"},
    "pulsar": {"devanagari": "पल्सर", "spoken": "Pulsar", "category": "assistant"},
    "fastapi": {"devanagari": "फास्ट एपीआई", "spoken": "FastAPI", "category": "tech"},
    "pycharm": {"devanagari": "पाईचार्म", "spoken": "PyCharm", "category": "app"},
    "spotify": {"devanagari": "स्पॉटिफ़ाई", "spoken": "Spotify", "category": "app"},
    "github": {"devanagari": "गिटहब", "spoken": "GitHub", "category": "tech"},
    "gguf": {"devanagari": "जीजीयूएफ", "spoken": "GGUF", "category": "tech"},
}

_DEFAULT_STT_CORRECTIONS = {
    "divakar": "diwakar",
    "dewakar": "diwakar",
    "deewakar": "diwakar",
    "ranjo": "rancho",
    "pulser": "pulsar",
    "palsar": "pulsar",
    "paulsar": "pulsar",
    "fashapi": "fastapi",
    "vescode": "vs code",
}

_DEFAULT_COMMAND_ALIASES = {
    "गाना": "music",
    "खोलो": "open",
    "चालू करो": "start",
    "बंद करो": "close",
    "स्क्रीन देखो": "screen",
}

# Deterministic feminine grammar fixes (Devanagari using script-aware boundaries, excluding punctuation like ।)
_DEV_LETTER = r"[a-zA-Z0-9\u0904-\u0963\u0966-\u097F]"
_DEV_B_LEFT = rf"(?<!{_DEV_LETTER})"
_DEV_B_RIGHT = rf"(?!{_DEV_LETTER})"

_FEMININE_DEVANAGARI_RULES = [
    (re.compile(rf"{_DEV_B_LEFT}करू[ंँ]?गा{_DEV_B_RIGHT}"), "करूँगी"),
    (re.compile(rf"{_DEV_B_LEFT}बताऊ[ंँ]?गा{_DEV_B_RIGHT}"), "बताऊँगी"),
    (re.compile(rf"{_DEV_B_LEFT}देखू[ंँ]?गा{_DEV_B_RIGHT}"), "देखूँगी"),
    (re.compile(rf"{_DEV_B_LEFT}सकू[ंँ]?गा{_DEV_B_RIGHT}"), "सकूँगी"),
    (re.compile(rf"{_DEV_B_LEFT}करता\s+हूँ{_DEV_B_RIGHT}"), "करती हूँ"),
    (re.compile(rf"{_DEV_B_LEFT}बताता\s+हूँ{_DEV_B_RIGHT}"), "बताती हूँ"),
    (re.compile(rf"{_DEV_B_LEFT}देखता\s+हूँ{_DEV_B_RIGHT}"), "देखती हूँ"),
    (re.compile(rf"{_DEV_B_LEFT}सोचता\s+हूँ{_DEV_B_RIGHT}"), "सोचती हूँ"),
    (re.compile(rf"{_DEV_B_LEFT}सकता\s+हूँ{_DEV_B_RIGHT}"), "सकती हूँ"),
    (re.compile(rf"{_DEV_B_LEFT}रहता\s+हूँ{_DEV_B_RIGHT}"), "रहती हूँ"),
    (re.compile(rf"{_DEV_B_LEFT}तैयार\s+रहूँगा{_DEV_B_RIGHT}"), "तैयार रहूँगी"),
    (re.compile(rf"{_DEV_B_LEFT}बेरोज़?गार\s+हूँ{_DEV_B_RIGHT}"), "काम पर हूँ"),
]

# Deterministic feminine grammar fixes (Roman Hinglish)
_FEMININE_HINGLISH_RULES = [
    (re.compile(r"\bkarunga\b", re.IGNORECASE), "karungi"),
    (re.compile(r"\bbataunga\b", re.IGNORECASE), "bataungi"),
    (re.compile(r"\bdekhunga\b", re.IGNORECASE), "dekhungi"),
    (re.compile(r"\bsakunga\b", re.IGNORECASE), "sakungi"),
    (re.compile(r"\bkarta\s+hoon\b", re.IGNORECASE), "karti hoon"),
    (re.compile(r"\bbatata\s+hoon\b", re.IGNORECASE), "batati hoon"),
    (re.compile(r"\bdekhta\s+hoon\b", re.IGNORECASE), "dekhti hoon"),
    (re.compile(r"\bsochta\s+hoon\b", re.IGNORECASE), "sochti hoon"),
    (re.compile(r"\bsakta\s+hoon\b", re.IGNORECASE), "sakti hoon"),
]

# Anti-servant filter rules
_ANTI_SERVANT_RULES = [
    (re.compile(r"(?:[—\-]\s*)?आदेश\s+दें\s*[।.!]?", re.UNICODE), "बताओ क्या करना है।"),
    (re.compile(r"\bआपकी\s+क्या\s+सेवा\s+करूँ\??", re.UNICODE), "बताओ आज किस काम पर काम करें?"),
    (re.compile(r"\bसेवा\s+में\s+हाज़िर\b", re.UNICODE), "तैयार हूँ"),
    (re.compile(r"\bमालिक\b", re.UNICODE), "दोस्त"),
    (re.compile(r"\bआपके\s+कमांड\s+का\s+इंतज़ार\s+था\b", re.UNICODE), "बताओ क्या प्लान है"),
]


class VocabularyRegistry:
    """Thread-safe user dictionary and grammar normalization registry."""

    _instance: Optional["VocabularyRegistry"] = None
    _lock = threading.RLock()

    def __init__(self, data_path: Optional[Path] = None):
        self._data_path = data_path or self._resolve_default_path()
        self._words: Dict[str, Dict[str, str]] = {}
        self._stt_corrections: Dict[str, str] = {}
        self._command_aliases: Dict[str, str] = {}
        self._strict_grammar = True
        self._filter_servant = True
        self._load()

    @staticmethod
    def _resolve_default_path() -> Path:
        try:
            from ai_assistant.core.database_config import DATA_DIR
            target = Path(DATA_DIR) / "user_preferences" / "user_dictionary.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            return target
        except Exception:
            return Path("data/user_preferences/user_dictionary.json")

    def _load(self) -> None:
        with self._lock:
            if not self._data_path.exists():
                # Populate default structure
                self._words = dict(_DEFAULT_WORDS)
                self._stt_corrections = dict(_DEFAULT_STT_CORRECTIONS)
                self._command_aliases = dict(_DEFAULT_COMMAND_ALIASES)
                self._strict_grammar = True
                self._filter_servant = True
                self._save_to_disk()
                return

            try:
                data = json.loads(self._data_path.read_text(encoding="utf-8"))
                self._words = dict(_DEFAULT_WORDS)
                self._words.update(data.get("words", {}))
                self._stt_corrections = dict(_DEFAULT_STT_CORRECTIONS)
                self._stt_corrections.update(data.get("sttCorrections", {}))
                self._command_aliases = dict(_DEFAULT_COMMAND_ALIASES)
                self._command_aliases.update(data.get("commandAliases", {}))
                self._strict_grammar = bool(data.get("strictGrammar", True))
                self._filter_servant = bool(data.get("filterServantPhrases", True))
            except Exception as exc:
                logger.warning(f"Error loading user_dictionary.json ({exc}), using defaults")
                self._words = dict(_DEFAULT_WORDS)
                self._stt_corrections = dict(_DEFAULT_STT_CORRECTIONS)
                self._command_aliases = dict(_DEFAULT_COMMAND_ALIASES)

    def _save_to_disk(self) -> None:
        try:
            self._data_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "words": self._words,
                "sttCorrections": self._stt_corrections,
                "commandAliases": self._command_aliases,
                "strictGrammar": self._strict_grammar,
                "filterServantPhrases": self._filter_servant,
            }
            tmp = self._data_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self._data_path)
        except Exception as exc:
            logger.error(f"Failed to persist user_dictionary.json: {exc}")

    def reload(self) -> None:
        """Force reload from disk (e.g. after external change)."""
        self._load()

    # ── STT Helpers ──────────────────────────────────────────────────────────

    def get_whisper_prompt_keywords(self, limit: int = 24) -> str:
        """Return a comma-separated string of user vocabulary words to bias Whisper."""
        with self._lock:
            tokens: List[str] = []
            for k, meta in self._words.items():
                spoken = meta.get("spoken") or k
                dev = meta.get("devanagari") or ""
                if spoken and spoken not in tokens:
                    tokens.append(spoken)
                if dev and dev not in tokens:
                    tokens.append(dev)
            return ", ".join(tokens[:limit])

    def normalize_stt_transcript(self, raw_text: str) -> str:
        """
        Fast in-memory phonetic correction of common Whisper mishearings.
        Takes <0.05ms for typical sentences.
        """
        if not raw_text:
            return ""
        with self._lock:
            corrections = self._stt_corrections
        if not corrections:
            return raw_text

        def _sub(m: re.Match) -> str:
            word = m.group(0)
            low = word.lower()
            if low in corrections:
                target = corrections[low]
                return target if word.islower() else target.title()
            return word

        return re.sub(r"[a-zA-Z0-9_\u0900-\u097F]+", _sub, raw_text)

    # ── TTS & Grammar Normalization ──────────────────────────────────────────

    def apply_tts_phonetics(self, text: str) -> str:
        """
        Replace custom user words with their configured Devanagari or spoken spelling.
        """
        if not text:
            return ""
        with self._lock:
            items = list(self._words.items())

        out = text
        for token, meta in items:
            dev = meta.get("devanagari")
            if dev:
                pattern = re.compile(rf"\b{re.escape(token)}\b", re.IGNORECASE)
                out = pattern.sub(dev, out)
        return out

    def enforce_grammar_and_tone(self, text: str) -> str:
        """
        Deterministic post-processing:
        1. Correct masculine first-person verbs to feminine ('karunga' -> 'karungi').
        2. Filter servile phrases ('आदेश दें' -> natural phrasing).
        Zero latency (~0.05ms).
        """
        if not text:
            return ""

        out = text
        with self._lock:
            strict_g = self._strict_grammar
            filter_s = self._filter_servant

        if strict_g:
            for pat, repl in _FEMININE_DEVANAGARI_RULES:
                out = pat.sub(repl, out)
            for pat, repl in _FEMININE_HINGLISH_RULES:
                out = pat.sub(repl, out)

        if filter_s:
            for pat, repl in _ANTI_SERVANT_RULES:
                out = pat.sub(repl, out)

        return out

    # ── CRUD for Settings & API ──────────────────────────────────────────────

    def get_dictionary_data(self) -> Dict[str, Any]:
        """Return current dictionary data for UI / REST endpoints."""
        with self._lock:
            return {
                "words": dict(self._words),
                "sttCorrections": dict(self._stt_corrections),
                "commandAliases": dict(self._command_aliases),
                "strictGrammar": self._strict_grammar,
                "filterServantPhrases": self._filter_servant,
            }

    def update_dictionary_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update dictionary data, persist to disk, and return updated state."""
        with self._lock:
            merge = data.get("merge", True)
            if "words" in data and isinstance(data["words"], dict):
                if merge:
                    self._words.update(data["words"])
                else:
                    self._words = data["words"]
            if "sttCorrections" in data and isinstance(data["sttCorrections"], dict):
                if merge:
                    self._stt_corrections.update(data["sttCorrections"])
                else:
                    self._stt_corrections = data["sttCorrections"]
            if "commandAliases" in data and isinstance(data["commandAliases"], dict):
                if merge:
                    self._command_aliases.update(data["commandAliases"])
                else:
                    self._command_aliases = data["commandAliases"]
            if "strictGrammar" in data:
                self._strict_grammar = bool(data["strictGrammar"])
            if "filterServantPhrases" in data:
                self._filter_servant = bool(data["filterServantPhrases"])
            self._save_to_disk()
            return self.get_dictionary_data()

    def add_word(self, word: str, devanagari: str, spoken: str = "", category: str = "custom") -> None:
        """Add or update a single word entry."""
        w_low = word.strip().lower()
        if not w_low:
            return
        with self._lock:
            self._words[w_low] = {
                "devanagari": devanagari.strip(),
                "spoken": (spoken or word).strip(),
                "category": category.strip(),
            }
            self._save_to_disk()

    def remove_word(self, word: str) -> bool:
        """Remove a word entry."""
        w_low = word.strip().lower()
        with self._lock:
            if w_low in self._words:
                del self._words[w_low]
                self._save_to_disk()
                return True
        return False


_global_registry: Optional[VocabularyRegistry] = None
_init_lock = threading.Lock()


def get_vocabulary_registry() -> VocabularyRegistry:
    """Get the global VocabularyRegistry singleton."""
    global _global_registry
    if _global_registry is None:
        with _init_lock:
            if _global_registry is None:
                _global_registry = VocabularyRegistry()
    return _global_registry
