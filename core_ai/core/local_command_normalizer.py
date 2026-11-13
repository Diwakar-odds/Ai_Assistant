"""
Unified Local Command Normalizer, Wake-Word Matcher & Voice Control Engine
========================================================================
Single shared module imported across backend, core_ai, and desktop companion to
avoid regex/keyword/Devanagari duplication.

Responsibilities:
1. Ensure project-local ffmpeg binary directory (`<root>/bin`) is on PATH.
2. Unicode-safe punctuation stripping (preserving Devanagari combining marks Mn/Mc).
3. Word/token-boundary checks immune to substring bugs ("and" inside "command").
4. Longest-phrase-first Devanagari/Hindi/Hinglish normalization to canonical tokens.
5. Shared wake-word phrase merging & stripping across WebUI/Backend/Companion.
6. Voice-mode settings control (switch AI provider/model, wake word, continuous
   listening, TTS, desktop overlay, STT language, UI view navigation).
"""

from __future__ import annotations

import logging
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_DIR = _PROJECT_ROOT / "backend"


def ensure_project_ffmpeg_in_path(project_root: Optional[Path] = None) -> Optional[Path]:
    """Idempotently prepend `<project_root>/bin` to PATH if ffmpeg binaries exist there."""
    root = Path(project_root) if project_root else _PROJECT_ROOT
    bin_dir = root / "bin"
    if bin_dir.is_dir():
        bin_str = str(bin_dir)
        current_parts = os.environ.get("PATH", "").split(os.pathsep) if os.environ.get("PATH") else []
        if bin_str not in current_parts:
            os.environ["PATH"] = f"{bin_str}{os.pathsep}{os.environ.get('PATH', '')}" if os.environ.get("PATH") else bin_str
        return bin_dir
    return None


def _import_settings_manager():
    """Import backend.settings_manager cleanly regardless of cwd/sys.path."""
    try:
        import settings_manager  # type: ignore
        return settings_manager
    except ImportError:
        backend_str = str(_BACKEND_DIR)
        if _BACKEND_DIR.is_dir() and backend_str not in sys.path:
            sys.path.insert(0, backend_str)
        try:
            import settings_manager  # type: ignore
            return settings_manager
        except ImportError:
            try:
                from backend import settings_manager  # type: ignore
                return settings_manager
            except ImportError:
                return None


# =============================================================================
# UNICODE-SAFE PUNCTUATION STRIPPING & WORD BOUNDARY HELPERS
# =============================================================================

def strip_punctuation_unicode(text: str) -> str:
    """
    Replace punctuation, symbols, separators, and control characters with spaces
    while preserving all Unicode letters, digits, AND combining marks (Mn/Mc)
    used by Devanagari matras/halant/anusvara.
    """
    if not text:
        return ""
    cleaned = "".join(
        " " if unicodedata.category(ch)[0] in ("P", "S", "Z", "C") else ch
        for ch in text
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def word_boundary_contains(text: str, phrase: str) -> bool:
    """
    Return True if `phrase` appears as whole token(s) in `text`.
    Immune to partial word matches ('and' in 'command'/'android') and Devanagari
    combining-mark boundary pitfalls in Python's `re`.
    """
    if not text or not phrase:
        return False
    norm_text = strip_punctuation_unicode(text).lower()
    norm_phrase = strip_punctuation_unicode(phrase).lower()
    if not norm_text or not norm_phrase:
        return False
    return f" {norm_phrase} " in f" {norm_text} "


def contains_any_sequential_keyword(text: str, keywords: Sequence[str]) -> bool:
    """Check if any keyword/phrase appears at whole-word boundaries or symbolic connectors exist."""
    if not text or not keywords:
        return False
    raw_lower = text.lower()
    for kw in keywords:
        kw_s = str(kw).strip().lower()
        if kw_s in ('&&', '||', '->', '=>', ';'):
            if kw_s in raw_lower:
                return True
    norm_text = strip_punctuation_unicode(text).lower()
    if not norm_text:
        return False
    padded = f" {norm_text} "
    for kw in keywords:
        kw_clean = strip_punctuation_unicode(str(kw)).lower().strip()
        if kw_clean and f" {kw_clean} " in padded:
            return True
    return False


# =============================================================================
# WHISPER NOISE & HALLUCINATION FILTERING
# =============================================================================

_NOISE_TOKENS = frozenset({
    # Hindi single vowel/syllable/fragment tokens commonly produced on breath/ambient noise
    "आई", "आ", "ओ", "ऊ", "ए", "ऐ", "इ", "ई", "अ", "हूँ", "था", "थी", "है", "हैं", "हाँ",
    "ना", "तो", "भी", "से", "को", "का", "की", "के", "में", "पर", "ने", "या", "व़र",
    # English single filler/syllable/article tokens
    "um", "umm", "uh", "ah", "oh", "eh", "er", "hmm", "hmmm", "yeah", "yep", "nope",
    "the", "a", "an", "is", "it", "in", "on", "at", "to", "so", "or", "and", "you",
    "i", "me", "my", "we", "he", "she",
})

_WHISPER_HALLUCINATIONS = frozenset({
    "thank you", "thank you.", "thanks for watching", "thanks for watching.",
    "subtitles by", "subtitles by the amara.org community", "amara.org",
    "you", "bye", "bye bye",
})


def is_noise_fragment(text: str) -> bool:
    """
    Returns True if the transcribed text is a single-token vocalization, breathing sound,
    or common Whisper hallucination artifact that should not trigger an AI turn.
    """
    raw = (text or "").strip()
    if not raw:
        return True
    low = raw.lower().rstrip(".!?,")
    if low in _WHISPER_HALLUCINATIONS:
        return True
    tokens = [t for t in re.split(r"[\s\.,!?;:\"\'\-—]+", raw) if t]
    if not tokens:
        return True
    if len(tokens) == 1:
        tok = tokens[0]
        tok_low = tok.lower()
        if tok in _NOISE_TOKENS or tok_low in _NOISE_TOKENS:
            return True
        if len(tok) <= 1:
            return True
    return False


# =============================================================================
# HINGLISH / DEVANAGARI NORMALIZATION
# =============================================================================

# Canonical token map — applied longest-phrase-first on space-padded text so
# multi-word phrases ("युटुब म्यूजिक", "ओपन करो") are never split prematurely.
_DEVANAGARI_AND_HINGLISH_PHRASES: Dict[str, str] = {
    # --- Multi-word App Actions (Longest first) ---
    "वाट्सब प्वलो": "open whatsapp",
    "वाटसब प्वलो": "open whatsapp",
    "वाट्सप प्वलो": "open whatsapp",
    "व्हाट्सएप प्वलो": "open whatsapp",
    "वाट्सब खोलो": "open whatsapp",
    "वाट्सप खोलो": "open whatsapp",
    "व्हाट्सब खोलो": "open whatsapp",
    "वाटसब खोलो": "open whatsapp",
    "व्हाट्सएप खोलो": "open whatsapp",
    "व्हाट्सऐप खोलो": "open whatsapp",
    "युटुब खोलो": "open youtube",
    "यूट्यूब खोलो": "open youtube",
    "क्रोम खोलो": "open chrome",

    # --- Apps & Web Apps ---
    "युटुब म्यूजिक": "youtube music",
    "यूट्यूब म्यूजिक": "youtube music",
    "यूट्यूब म्यूज़िक": "youtube music",
    "युट्यूब म्यूजिक": "youtube music",
    "यूटुब म्यूजिक": "youtube music",
    "युटुब म्युजिक": "youtube music",
    "यूट्यूब म्युजिक": "youtube music",
    "युटुब": "youtube",
    "यूट्यूब": "youtube",
    "युट्यूब": "youtube",
    "यूटुब": "youtube",
    "व्हाट्सएप": "whatsapp",
    "व्हाट्सऐप": "whatsapp",
    "वॉट्सऐप": "whatsapp",
    "वॉट्सएप": "whatsapp",
    "वाट्सएप": "whatsapp",
    "वाट्सऐप": "whatsapp",
    "वाट्सब": "whatsapp",
    "वाटसब": "whatsapp",
    "व्हाट्सब": "whatsapp",
    "वाट्सप": "whatsapp",
    "वाटसप": "whatsapp",
    "व्हाट्सप": "whatsapp",
    "वट्सएप": "whatsapp",
    "वॉटसएप": "whatsapp",
    "whtsap": "whatsapp",
    "whtsp": "whatsapp",
    "whatsap": "whatsapp",
    "whatspp": "whatsapp",
    "whtsapp": "whatsapp",
    "स्पॉटिफाई": "spotify",
    "स्पॉटीफाई": "spotify",
    "स्पोटीफाई": "spotify",
    "गूगल क्रोम": "google chrome",
    "क्रोम": "chrome",
    "गूगल मैप्स": "google maps",
    "मैप्स": "google maps",
    "गूगल ड्राइव": "google drive",
    "गूगल डॉक्स": "google docs",
    "जीमेल": "gmail",
    "गूगल": "google",
    "कैलकुलेटर": "calculator",
    "केलकुलेटर": "calculator",
    "नोटपैड": "notepad",
    "टेलीग्राम": "telegram",
    "डिस्कॉर्ड": "discord",
    "वीएलसी": "vlc",
    "वीएस कोड": "vscode",
    "विजुअल स्टूडियो कोड": "vscode",
    "फ़ाइल एक्सप्लोरर": "explorer",
    "फाइल एक्सप्लोरर": "explorer",
    "एक्सप्लोरर": "explorer",
    "ब्राउज़र": "browser",
    "ब्राउजर": "browser",
    "माइक्रोसॉफ्ट एज": "edge",
    "इंस्टाग्राम": "instagram",
    "फेसबुक": "facebook",
    "नेटफ्लिक्स": "netflix",
    "प्राइम वीडियो": "prime video",
    "कमांड प्रॉम्प्ट": "cmd",
    "सीएमडी": "cmd",
    "टर्मिनल": "terminal",
    "पावरशेल": "powershell",
    "टास्क मैनेजर": "task manager",
    "स्पॉटिफ़ाई": "spotify",

    # --- Actions / Verbs ---
    "ओपन कर दो": "open",
    "ओपन करो": "open",
    "ओपन कीजिए": "open",
    "ओपन": "open",
    "खोल दीजिए": "kholo",
    "खोल दो": "kholo",
    "खोल दे": "kholo",
    "खोलिए": "kholo",
    "खोलिये": "kholo",
    "खोलना": "kholo",
    "खोलो": "kholo",
    "खोलो ना": "kholo",
    "खोल": "kholo",
    "प्वलो": "kholo",
    "पोलो": "kholo",
    "कलो": "kholo",
    "लॉन्च करो": "launch",
    "लॉन्च": "launch",
    "स्टार्ट करो": "start",
    "स्टार्ट": "start",
    "क्लोज़ कर दो": "close",
    "क्लोज़ करो": "close",
    "क्लोज कर दो": "close",
    "क्लोज करो": "close",
    "क्लोज": "close",
    "बंद कर दो": "band karo",
    "बंद करो": "band karo",
    "बंद कर": "band karo",
    "बंद": "band",
    "चालू कर दो": "chalu karo",
    "चालू करो": "chalu karo",
    "चालू कर": "chalu karo",
    "चालू": "chalu",
    "चला दो": "chalao",
    "चलाओ": "chalao",
    "प्ले कर दो": "play karo",
    "प्ले करो": "play karo",
    "प्ले": "play",
    "बजा दो": "bajao",
    "बजाओ": "bajao",
    "बजा": "bajao",
    "लगा दो": "lagao",
    "लगाओ": "lagao",
    "सर्च करो": "search",
    "खोजो": "search",
    "ढूंढो": "search",
    "सर्च": "search",
    "दिखाओ": "show",
    "बताओ": "show",
    "स्विच कर दो": "switch",
    "स्विच करो": "switch",
    "स्विच": "switch",
    "बदल दो": "switch",
    "बदलो": "switch",
    "शिफ्ट करो": "switch",
    "शिफ्ट": "switch",

    # --- Media / Playback / Volume ---
    "ले नेख सों": "next song",
    "ले नेक्स सों": "next song",
    "ले नेख सोंग": "next song",
    "ले नेक्स सोंग": "next song",
    "नेख सों": "next song",
    "नेक्स सोंग": "next song",
    "नेक्स सांग": "next song",
    "नेक्स्ट सोंग": "next song",
    "नेक्स्ट सांग": "next song",
    "नेक्स्ट सॉन्ग": "next song",
    "नेक्स्ट गाना": "next song",
    "नेक्स्ट ट्रैक": "next song",
    "प्ले नेक्स्ट सांग": "play next song",
    "प्ले नेक्स्ट सॉन्ग": "play next song",
    "प्ले नेक्स्ट गाना": "play next song",
    "प्ले नेक्स्ट": "play next song",
    "प्ले नेक्स": "play next song",
    "प्ले नेख": "play next song",
    "ले नेख": "next song",
    "ले नेक्स": "next song",
    "अगला गाना": "next song",
    "अगला सोंग": "next song",
    "अगला सांग": "next song",
    "गाना बदलो": "next song",
    "प्रीवियस सॉन्ग": "previous song",
    "प्रीवियस सोंग": "previous song",
    "प्रीवियस सांग": "previous song",
    "पिछला गाना": "previous song",
    "पिछला सोंग": "previous song",
    "पिछला सांग": "previous song",
    "स्किप करो": "skip karo",
    "पॉज़ करो": "pause karo",
    "पॉज करो": "pause karo",
    "पाउज करो": "pause karo",
    "पाउस करो": "pause karo",
    "पॉज़ सोंग": "pause song",
    "पॉज सोंग": "pause song",
    "पाउज सोंग": "pause song",
    "पाउस सोंग": "pause song",
    "पॉज़ गाना": "pause song",
    "पॉज गाना": "pause song",
    "गाना रोको": "pause song",
    "गाना रोक दो": "pause song",
    "गाना बंद करो": "pause song",
    "म्यूजिक रोको": "pause song",
    "म्यूजिक बंद": "pause song",
    "गाना चालू करो": "gaana chalu karo",
    "गाना चलाओ": "gaana chalao",
    "गाना चला दो": "gaana chalao",
    "म्यूजिक चलाओ": "music chalao",
    "म्यूजिक चालू करो": "music chalu karo",
    "गाना": "gaana",
    "गीत": "gaana",
    "सॉन्ग": "song",
    "म्यूजिक": "music",
    "म्यूज़िक": "music",
    "वीडियो": "video",
    "वॉल्यूम": "volume",
    "वाल्यूम": "volume",
    "वोल्यूम": "volume",
    "आवाज़": "awaaz",
    "आवाज": "awaaz",
    "साउंड": "sound",
    "कम कर दो": "kam karo",
    "कम करो": "kam karo",
    "कम": "kam",
    "धीमा कर दो": "dhima karo",
    "धीमा करो": "dhima karo",
    "धीमी कर दो": "dhima karo",
    "धीमी करो": "dhima karo",
    "धीमा": "dhima",
    "धीमी": "dhima",
    "घटा दो": "kam karo",
    "घटाओ": "kam karo",
    "घटा": "kam",
    "बढ़ा दे": "badhao",
    "बढ़ा दीजिए": "badhao",
    "बढ़ा दो": "badhao",
    "बढ़ाओ": "badhao",
    "बढ़ा": "badhao",
    "तेज़ कर दो": "tez karo",
    "तेज़ करो": "tez karo",
    "तेज कर दो": "tez karo",
    "तेज करो": "tez karo",
    "तेज़": "tez",
    "तेज": "tez",
    "ज्यादा करो": "zyada karo",
    "अनम्यूट कर दो": "unmute",
    "अनम्यूट करो": "unmute",
    "अनम्यूट": "unmute",
    "म्यूट कर दो": "mute",
    "म्यूट करो": "mute",
    "म्यूट": "mute",

    # --- System & Settings ---
    "वाई-फाई": "wifi",
    "वाई फाई": "wifi",
    "वाइ फाई": "wifi",
    "वाई फाइ": "wifi",
    "वाइ फाइ": "wifi",
    "वाईफाई": "wifi",
    "वाइफाई": "wifi",
    "ब्लू टूथ": "bluetooth",
    "ब्लूटूथ": "bluetooth",
    "ब्लूटुथ": "bluetooth",
    "बैटरी": "battery",
    "ब्राइटनेस": "brightness",
    "चमक": "brightness",
    "रोशनी": "brightness",
    "डार्क मोड": "dark mode",
    "लाइट मोड": "light mode",
    "मोबाइल हॉटस्पॉट": "hotspot",
    "हॉटस्पॉट": "hotspot",
    "नाइट लाइट": "night light",
    "एयरप्लेन मोड": "airplane mode",
    "एयरप्लेन": "airplane",
    "फ्लाइट मोड": "airplane mode",
    "कंट्रोल पैनल": "control panel",
    "पर्सनलाइजेशन": "personalization",
    "डिस्प्ले": "display",
    "नेटवर्क": "network",
    "स्क्रीनशॉट": "screenshot",
    "screnshot": "screenshot",
    "scrnshot": "screenshot",
    "screen shot": "screenshot",
    "स्क्रीन": "screen",
    "सेटिंग्स": "settings",
    "सेटिंग": "settings",
    "शटडाउन": "shutdown",
    "रीस्टार्ट": "restart",
    "लॉक": "lock",
    "स्लीप": "sleep",
    "वेक वर्ड": "wake word",
    "वेकवर्ड": "wake word",
    "वेक मोड": "wake word",
    "लगातार सुनो": "continuous listening",
    "कंटीन्यूअस लिसनिंग": "continuous listening",
    "कंटीन्यूअस": "continuous listening",
    "ओवरले": "overlay",
    "ऑर्ब": "orb",
    "टीटीएस": "tts",
    "टी टी एस": "tts",
    "वॉइस आउटपुट": "voice output",
    "बोलना बंद": "tts off",
    "बोलना शुरू": "tts on",
    "बोलना चालू": "tts on",

    # --- AI Providers & Models ---
    "लोकल मॉडल": "local model",
    "ऑफलाइन मॉडल": "local model",
    "लोकल एआई": "local model",
    "ऑफलाइन एआई": "local model",
    "जीजीयूएफ": "gguf",
    "जी जी यू एफ": "gguf",
    "पल्सर मॉडल": "pulsar model",
    "पल्सर": "pulsar",
    "पलसर": "pulsar",
    "जेमिनी": "gemini",
    "जेमिनाई": "gemini",
    "जेमनी": "gemini",
    "ओपनएआई": "openai",
    "चैटजीपीटी": "chatgpt",
    "जीपीटी": "gpt",
    "ऑनलाइन मॉडल": "gemini",
    "ऑनलाइन एआई": "online ai",
    "ऑफलाइन": "offline",
    "लोकल": "local",
    "मॉडल": "model",
    "प्रोवाइडर": "provider",
    "हिंदी": "hindi",
    "अंग्रेजी": "english",
    "इंग्लिश": "english",

    # --- Common Grammar & Status Words ---
    "कौन सा": "kaun sa",
    "कौनसी": "kaun sa",
    "कौन से": "kaun se",
    "चल रहे हैं": "chal rahe",
    "खुले हैं": "khule hain",
    "ऑनलाइन": "online",
    "ऑन कर दो": "on karo",
    "ऑन करो": "on karo",
    "ऑफ कर दो": "off karo",
    "ऑफ करो": "off karo",
    "ऑफ़ कर दो": "off karo",
    "ऑफ़ करो": "off karo",
    "ऑफ़": "off",
    "ऑफ": "off",
    "ऑन": "on",
    "इसको": "isko",
    "इसे": "isko",
    "ये": "ye",
    "यह": "ye",
    "करो": "karo",
    "कर दो": "karo",
    "कर दे": "karo",
    "कीजिए": "karo",
    "पर": "par",
    "पे": "pe",
    "pr": "par",
    "में": "mein",
    "से": "se",
    "को": "ko",
    "और": "and",
    "फिर": "phir",
    "है": "hai",
    "हैं": "hain",
    "क्या": "kya",
    "डैशबोर्ड": "dashboard",
    "इंटीग्रेशन": "integrations",
    "कन्वर्सेशन": "conversations",
    "सिस्टम": "system",
    "चैट": "chat",
    "मैसेज": "message",
    "msh": "msg",
    "msz": "msg",
    "mssg": "msg",
    "मदद": "help",
    "हेल्प": "help",
    # --- Common transliterations, Hinglish variants & typos ---
    "yutube": "youtube",
    "ytube": "youtube",
    "utube": "youtube",
    "krke": "karke",
    "kar ke": "karke",
    "karkey": "karke",
    "bjao": "bajao",
    "bjado": "bajao",
    "bja do": "bajao",
    "krdo": "kardo",
    "kar do": "kardo",
    "dhundho": "dhundo",
    "dhund": "dhundo",
    "btao": "batao",
    "batado": "batao",
    "kholdo": "kholo",
    "khol do": "kholo",
    "khol ke": "kholo aur",
    "kholke": "kholo aur",
    "khol kar": "kholo aur",
    "khol kr": "kholo aur",
    "open krke": "open karke",
    "open karkey": "open karke",
    "bnd kro": "band karo",
    "bnd kar do": "band karo",
    "bnd krdo": "band karo",
    "band kro": "band karo",
    "bnd karo": "band karo",
    "bnd": "band",
    "kro": "karo",
    "bnd kar": "band kar",
}

_SORTED_PHRASE_KEYS = sorted(_DEVANAGARI_AND_HINGLISH_PHRASES.keys(), key=len, reverse=True)
_PHRASE_PATTERN = re.compile(
    r"(?<!\S)(" + "|".join(re.escape(k) for k in _SORTED_PHRASE_KEYS) + r")(?!\S)",
    flags=re.UNICODE,
)


def normalize_hinglish_devanagari(text: str) -> str:
    """
    Normalize mixed Devanagari/Hinglish/English command text into canonical tokens
    while preserving unknown words (e.g. custom app names, contact names) and
    never breaking Latin tokens.
    """
    if not text:
        return ""
    # Strip punctuation/symbols while keeping Unicode combining marks (matras/halant)
    cleaned = strip_punctuation_unicode(text).lower()
    if not cleaned:
        return ""
    normalized = _PHRASE_PATTERN.sub(
        lambda m: _DEVANAGARI_AND_HINGLISH_PHRASES.get(m.group(1), m.group(1)),
        cleaned,
    )
    return re.sub(r"\s+", " ", normalized).strip()


# =============================================================================
# SHARED WAKE PHRASES & STRIPPING
# =============================================================================

DEFAULT_WAKE_PHRASES: Tuple[str, ...] = (
    "hey pulsar",
    "ok pulsar",
    "hi pulsar",
    "he pulsar",
    "eh pulsar",
    "ey pulsar",
    "ay pulsar",
    "hay pulsar",
    "pulsar",
    "a pulsar",
    "hey pulser",
    "he pulser",
    "pulser",
    "hey pal sir",
    "hey pulse her",
    "hey assistant",
    "ok assistant",
    # Devanagari variants commonly produced by Whisper
    "असिस्टेंट",
    "हे असिस्टेंट",
    "ओके असिस्टेंट",
    "सुनो असिस्टेंट",
    "पल्सर",
    "पलसर",
    "हे पल्सर",
    "हे पलसर",
    "हेय पल्सर",
    "है पल्सर",
    "है पलसर",
    "ए पल्सर",
    "ये पल्सर",
    "ओके पल्सर",
    "ओके पलसर",
    "सुनो पल्सर",
    "सुनो पलसर",
    "जार्विस",
    "हे जार्विस",
    "ओके जार्विस",
)


def get_merged_wake_phrases(extra_phrases: Optional[Sequence[str]] = None) -> List[str]:
    """Return deduplicated lowercase wake phrases sorted longest-first."""
    phrases: List[str] = []
    if extra_phrases:
        phrases.extend(str(p).strip().lower() for p in extra_phrases if str(p).strip())

    sm = _import_settings_manager()
    if sm is not None:
        try:
            phrases.extend(str(p).strip().lower() for p in (sm.get_wake_words() or []) if str(p).strip())
        except Exception:
            pass

    phrases.extend(DEFAULT_WAKE_PHRASES)
    deduped = list(dict.fromkeys(p for p in phrases if p))
    deduped.sort(key=len, reverse=True)
    return deduped


_SHORT_VALID_SINGLE_COMMANDS = frozenset({
    "hi", "hey", "ok", "okay", "on", "off", "yes", "no", "stop", "mute",
    "unmute", "play", "pause", "next", "skip", "time", "date", "help",
    "open", "close", "quit", "exit", "wait", "back", "home",
    "हां", "हाँ", "नहीं", "ना", "चुप", "रुक", "रुको", "रोको", "बस",
    "खोलो", "बंद", "सुनो", "बताओ", "समय", "टाइम", "डेट", "हेल्प", "मदद",
})

_IMPOSSIBLE_DEVANAGARI_NUKTA_RE = re.compile(
    r"(?:^|[^\u0915\u0916\u0917\u091c\u0921\u0922\u092b\u092f\u0930\u0932\u0933])\u093c|\u093c{2,}"
)

_WAKE_NOISE_RESIDUE_TOKENS = frozenset({
    "a", "an", "the", "he", "she", "it", "uh", "um", "er", "ah", "oh", "eh", "ey", "ay", "hay",
    "ye", "yeh", "ya", "ha",
    "ए", "ये", "ओ", "हे", "अ", "उ",
})

BARGE_IN_STOP_PHRASES: Tuple[str, ...] = (
    # English
    "stop", "stop speaking", "stop talking", "stop it", "stop now",
    "shut up", "shutup", "quiet", "be quiet", "silence", "hush", "shhh", "shh", "shush",
    "cancel", "never mind", "nevermind", "mute yourself", "enough",
    "hold on", "wait",
    # Hinglish
    "chup", "chup ho", "chup ho ja", "chup ho jao", "chup raho", "chup rah",
    "chup kar", "chup karo", "chup kr",
    "bas", "bas kar", "bas karo", "bas ho gaya",
    "ruk", "ruk ja", "ruk jao", "ruko", "roko",
    "band kar", "band karo", "bolna band", "bolna band kar", "bolna band karo",
    "aawaz band", "aawaz band karo", "awaaz band", "awaaz band karo",
    "shant", "shant ho ja", "shant ho jao", "shaant", "shaant ho ja", "shaant ho jao",
    # Devanagari
    "चुप", "चुप हो", "चुप हो जा", "चुप हो जाओ", "चुप रहो", "चुप कर", "चुप करो",
    "बस", "बस कर", "बस करो",
    "रुक", "रुक जा", "रुक जाओ", "रुको", "रोको",
    "बंद कर", "बंद करो", "बोलना बंद", "बोलना बंद कर", "बोलना बंद करो",
    "आवाज बंद", "आवाज़ बंद", "आवाज बंद करो", "आवाज़ बंद करो",
    "शांत", "शांत हो जाओ", "स्टॉप", "चुपचाप",
)

_BARGE_IN_STOP_SET = frozenset(strip_punctuation_unicode(p).lower() for p in BARGE_IN_STOP_PHRASES)
_BARGE_IN_LEAD_PREFIXES = (
    "ok", "okay", "hey", "arey", "are", "ab", "abhi", "please", "plz", "yaar", "bhai", "zara", "oye", "abe",
    "ओके", "अरे", "अब", "अभी", "हे", "प्लीज", "यार", "भाई", "जरा", "ओए", "अबे",
)
_BARGE_IN_TRAIL_SUFFIXES = (
    "please", "plz", "yaar", "bhai", "bro", "man", "dude", "ab", "abhi", "na", "zara", "now", "boss",
    "already", "be", "bey", "re", "madarchod", "mc", "bc", "bhenchod", "bhosdike", "bsdk", "chutiya",
    "saale", "sale", "kamine", "harami", "gadhe", "idiot", "stupid",
    "प्लीज", "यार", "भाई", "अभी", "ना", "जरा", "मादरचोद", "साले", "अबे",
)
_UNAMBIGUOUS_SILENCE_HEADS = (
    "chup ho jao", "chup ho ja", "chup raho", "chup karo", "chup kar", "chup kr", "chup rah", "chup ho", "chup",
    "shut up", "shutup", "be quiet", "stop speaking", "stop talking", "stop it", "mute yourself",
    "bolna band karo", "bolna band kar", "bolna band",
    "awaaz band karo", "awaaz band kar", "aawaz band karo", "aawaz band kar",
    "shant ho jao", "shant ho ja", "shaant ho jao", "shaant ho ja", "shaant", "shant", "shhh", "shh", "shush",
    "चुप हो जाओ", "चुप हो जा", "चुप रहो", "चुप करो", "चुप कर", "चुप हो", "चुप", "चुपचाप",
    "बोलना बंद करो", "बोलना बंद कर", "बोलना बंद", "शांत हो जाओ", "शांत हो जा", "शांत",
)
_BARGE_IN_DISQUALIFIERS = frozenset({
    "spotify", "chrome", "notepad", "whatsapp", "youtube", "music", "song", "video",
    "gaana", "wifi", "bluetooth", "app", "download", "recording", "settings", "task",
    "what", "why", "how", "when", "where", "who", "open", "kholo", "play", "search",
})


def is_barge_in_stop_command(text: str) -> bool:
    """
    Return True for explicit user interruption / silence requests such as
    'chup ho jao', 'chup madarchod', 'bas karo', 'ruk jao', 'stop speaking', 'quiet', etc.
    Handles optional leading/trailing wake words and abusive/filler interjections safely
    without stealing normal commands like 'stop spotify'.
    """
    if not text or not text.strip():
        return False

    matched_wake, stripped = match_and_strip_wake_phrase(text)
    candidates = []
    if matched_wake:
        if stripped:
            candidates.append(stripped)
    else:
        candidates.append(text.strip())

    for cand in candidates:
        cleaned = strip_punctuation_unicode(cand).lower()
        if not cleaned:
            continue
        if cleaned in _BARGE_IN_STOP_SET:
            return True

        tokens = cleaned.split()
        # Trim one or more leading/trailing polite filler or expletive interjection tokens
        while len(tokens) > 1 and tokens[0] in _BARGE_IN_LEAD_PREFIXES:
            tokens = tokens[1:]
        while len(tokens) > 1 and tokens[-1] in _BARGE_IN_TRAIL_SUFFIXES:
            tokens = tokens[:-1]
        trimmed = " ".join(tokens)
        if trimmed in _BARGE_IN_STOP_SET:
            return True

        # Handle unambiguous silence cues followed by extra filler/profanity (e.g. "chup madarchod", "shut up idiot")
        if 1 < len(tokens) <= 6 and not (set(tokens) & _BARGE_IN_DISQUALIFIERS):
            for head in _UNAMBIGUOUS_SILENCE_HEADS:
                if trimmed == head or trimmed.startswith(head + " "):
                    return True

    return False


def _looks_like_clipped_wake_fragment(token: str) -> bool:
    tok = strip_punctuation_unicode(token or "").lower()
    if not tok:
        return False
    return ("पल्स" in tok) or ("पलस" in tok) or ("puls" in tok)


def match_and_strip_wake_phrase(
    transcript: str,
    extra_phrases: Optional[Sequence[str]] = None,
) -> Tuple[Optional[str], str]:
    """
    Match any configured/default wake phrase in `transcript` using Unicode-safe
    token boundaries, strip repeated leading/trailing wake words, and reject
    Whisper repetition hallucinations while returning `(matched_wake, remaining_command)`.
    """
    if not transcript or not transcript.strip():
        return None, ""

    phrases = get_merged_wake_phrases(extra_phrases)
    text_norm = strip_punctuation_unicode(transcript).lower()
    padded = f" {text_norm} "

    matched: Optional[str] = None
    for phrase in phrases:
        phrase_norm = strip_punctuation_unicode(phrase).lower()
        if phrase_norm and f" {phrase_norm} " in padded:
            matched = phrase
            break

    if not matched:
        return None, transcript.strip()

    wake_patterns = "|".join(re.escape(w) for w in phrases)
    lead_re = re.compile(
        rf"^\s*(?:{wake_patterns})(?:[\s,.:;!?।-]+|$)",
        flags=re.IGNORECASE | re.UNICODE,
    )
    trail_re = re.compile(
        rf"(?:[\s,.:;!?।-]+|^)(?:{wake_patterns})[\s,.:;!?।-]*$",
        flags=re.IGNORECASE | re.UNICODE,
    )

    cleaned = transcript.strip(" \t\r\n,.:;!?।-\"'")
    leading_strips = 0
    while cleaned:
        nxt, sub_count = lead_re.subn("", cleaned, count=1)
        if sub_count == 0:
            break
        cleaned = nxt.strip(" \t\r\n,.:;!?।-\"'")
        leading_strips += 1

    trailing_strips = 0
    while cleaned:
        nxt, sub_count = trail_re.subn("", cleaned, count=1)
        if sub_count == 0:
            break
        cleaned = nxt.strip(" \t\r\n,.:;!?।-\"'")
        trailing_strips += 1

    rem_tokens = [t for t in strip_punctuation_unicode(cleaned).lower().split() if t]

    # Reject Whisper noise repetition loops where wake only appears as a mid/tail artifact
    if leading_strips == 0:
        has_preceding_clipped_wake = any(_looks_like_clipped_wake_fragment(t) for t in rem_tokens[-2:])
        if trailing_strips >= 2 or (trailing_strips >= 1 and has_preceding_clipped_wake):
            return None, transcript.strip()

    # Discard 1-token filler/greeting residue (e.g. "He pulsar." / "Oh pulsar.") or multiple-wake artifacts
    total_strips = leading_strips + trailing_strips
    if len(rem_tokens) == 1 and total_strips >= 1:
        tok = rem_tokens[0]
        if tok in _WAKE_NOISE_RESIDUE_TOKENS and tok not in _SHORT_VALID_SINGLE_COMMANDS:
            return matched, ""

    if total_strips >= 2 and rem_tokens:
        while rem_tokens and _looks_like_clipped_wake_fragment(rem_tokens[0]):
            rem_tokens.pop(0)
        while rem_tokens and _looks_like_clipped_wake_fragment(rem_tokens[-1]):
            rem_tokens.pop()
        if not rem_tokens:
            return matched, ""
        if len(rem_tokens) == 1:
            tok = rem_tokens[0]
            if _IMPOSSIBLE_DEVANAGARI_NUKTA_RE.search(tok) or (
                len(tok) <= 3 and tok not in _SHORT_VALID_SINGLE_COMMANDS
            ):
                if leading_strips == 0:
                    return None, transcript.strip()
                return matched, ""
        # Re-clean if clipped wake fragments were stripped from the edges
        if leading_strips == 0 and any(_looks_like_clipped_wake_fragment(t) for t in strip_punctuation_unicode(cleaned).lower().split()):
            cleaned = " ".join(
                w for w in cleaned.split() if not _looks_like_clipped_wake_fragment(w)
            ).strip(" \t\r\n,.:;!?।-")

    return matched, cleaned.strip()


# =============================================================================
# VOICE CONTROL PARSER & EXECUTOR (SINGLE SETTINGS PATH)
# =============================================================================

_SWITCH_VERBS = (
    "switch", "change", "use", "shift", "set", "activate", "select",
    "enable", "laga", "lagao", "chalao", "badlo", "karo",
)


def _resolve_provider_and_model_from_fragment(fragment: str) -> Optional[Tuple[str, str]]:
    """Map a natural-language provider/model fragment to `(provider_id, model_id)`."""
    frag = fragment.lower().strip()
    if not frag:
        return None

    # Local GGUF / Pulsar local model
    if any(tok in frag for tok in ("local model", "offline model", "local ai", "offline ai", "gguf", "pulsar model")):
        return ("gguf", "pulsar-final-q4_k_m")
    if re.search(r"\b(?:local|offline)\b", frag):
        return ("gguf", "pulsar-final-q4_k_m")

    # OpenAI / GPT models
    if any(tok in frag for tok in ("openai", "gpt", "chatgpt")):
        if re.search(r"gpt[\s-]*4o[\s-]*mini", frag):
            return ("openai", "gpt-4o-mini")
        if re.search(r"gpt[\s-]*4o", frag):
            return ("openai", "gpt-4o")
        if re.search(r"gpt[\s-]*3\.?5", frag):
            return ("openai", "gpt-3.5-turbo")
        return ("openai", "gpt-4o-mini")

    # Gemini / Online AI
    if "gemini" in frag or "online ai" in frag or "online model" in frag:
        if "pro" in frag:
            return ("gemini", "gemini-2.5-pro")
        return ("gemini", "gemini-2.5-flash")

    return None


def parse_voice_control_command(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse natural English/Hindi/Hinglish voice/chat control commands that configure
    Pulsar's active AI provider, model, voice/system settings, or UI navigation.

    Returns a structured action dict or `None` if not a voice-control command.
    """
    if not text or not text.strip():
        return None

    # Strip leading wake phrase first so "Hey Pulsar switch to local model" works
    _, stripped_raw = match_and_strip_wake_phrase(text)
    target_text = stripped_raw or text.strip()
    norm = normalize_hinglish_devanagari(target_text)
    if not norm:
        return None

    # 1. Active model / provider status query
    if re.search(
        r"(?:\b(?:which|what|current|active|kaun\s*sa|kaunsa|konsa)\b.*?\b(?:ai\s+)?(?:model|provider)\b|"
        r"\b(?:model|provider)\b.*?\b(?:kya\s+hai|kaun\s+sa|status|active|running|chal\s+raha)\b)",
        norm,
    ):
        return {"action": "query_model_status", "raw": target_text}

    # 2. Switch AI provider / model
    # Extract destination side when phrasing is "<source> se <target>" or "from <source> to <target>"
    has_provider_cue = any(
        tok in norm
        for tok in (
            "gemini", "gguf", "local model", "offline model", "local mode", "offline mode",
            "local ai", "offline ai", "openai", "gpt", "chatgpt", "pulsar model",
            "online ai", "online model", "online mode", "model", "provider",
        )
    ) or (
        re.search(r"\b(switch|shift)\b", norm) is not None
        and re.search(r"\b(local|offline|online)\b", norm) is not None
    )
    if has_provider_cue:
        has_switch_intent = any(re.search(rf"\b{v}\b", norm) for v in _SWITCH_VERBS) or (
            re.search(r"\b(?:se|to)\b", norm) is not None
            and any(tok in norm for tok in ("model", "gguf", "gemini", "openai", "local", "offline", "online"))
        )
        # Do not hijack questions ("which model is gemini?") or website launches ("open gemini website")
        is_question = "?" in target_text and not re.search(r"\b(switch|change|use|activate|shift)\b", norm)
        is_website_open = (
            ("website" in norm or "open gemini" in norm)
            and not re.search(r"\b(model|provider|switch|shift|use|activate)\b", norm)
        )
        if has_switch_intent and not is_question and not is_website_open:
            dest_fragment = norm
            # "gemini se local model par switch karo" -> inspect portion between se and switch/par OR after se
            se_match = re.search(r"\bse\s+(.+)$", norm)
            to_match = re.search(r"\bto\s+(.+)$", norm)
            if se_match:
                dest_fragment = se_match.group(1)
            elif to_match:
                # Ignore "switch to local model from gemini" trailing "from ..."
                dest_fragment = re.split(r"\bfrom\b", to_match.group(1))[0].strip()

            resolved = _resolve_provider_and_model_from_fragment(dest_fragment)
            if not resolved and dest_fragment != norm:
                resolved = _resolve_provider_and_model_from_fragment(norm)

            if resolved:
                return {
                    "action": "switch_model",
                    "provider": resolved[0],
                    "model": resolved[1],
                    "raw": target_text,
                }

    # 3. Wake word enable / disable
    if "wake word" in norm or "always wake" in norm:
        if any(tok in norm for tok in ("off", "disable", "band", "stop", "deactivate")):
            return {"action": "toggle_wake_word", "enabled": False, "raw": target_text}
        if any(tok in norm for tok in ("on", "enable", "chalu", "start", "activate")):
            return {"action": "toggle_wake_word", "enabled": True, "raw": target_text}

    # 4. Continuous / hands-free listening toggle
    if any(tok in norm for tok in ("continuous listening", "always listening", "hands free", "always active")):
        if any(tok in norm for tok in ("off", "disable", "band", "stop", "deactivate")):
            return {"action": "toggle_continuous_listening", "enabled": False, "raw": target_text}
        if any(tok in norm for tok in ("on", "enable", "chalu", "start", "activate")):
            return {"action": "toggle_continuous_listening", "enabled": True, "raw": target_text}

    # 5a. Transient barge-in stop (interrupt current playback without disabling TTS setting)
    if is_barge_in_stop_command(text):
        return {"action": "stop_speaking", "raw": target_text}

    # 5b. TTS enable / disable (strictly exclude system audio volume mute & transient barge-in!)
    if any(tok in norm for tok in ("tts", "voice output", "voice response", "mute voice", "unmute voice")):
        if any(tok in norm for tok in ("off", "disable", "mute", "band")):
            return {"action": "toggle_tts", "enabled": False, "raw": target_text}
        if any(tok in norm for tok in ("on", "enable", "unmute", "chalu", "start", "resume")):
            return {"action": "toggle_tts", "enabled": True, "raw": target_text}

    # 6. Desktop 4D Orb overlay toggle
    if any(tok in norm for tok in ("desktop overlay", "floating orb", "4d orb", "overlay", "orb")):
        if any(tok in norm for tok in ("off", "hide", "disable", "band", "close", "remove", "hatao")):
            return {"action": "toggle_desktop_overlay", "enabled": False, "raw": target_text}
        if any(tok in norm for tok in ("on", "show", "enable", "chalu", "open", "start")):
            return {"action": "toggle_desktop_overlay", "enabled": True, "raw": target_text}

    # 6b. Screen share stealth / capture invisibility (Parakeet AI mode)
    if ("screen share" in norm or "stealth mode" in norm or "stealth" in norm) and not any(k in norm for k in ("screenshot", "screen shot", "screen padho", "screen check")):
        if any(tok in norm for tok in ("off", "disable", "band", "show", "visible", "deactivate", "hatao", "dikhao", "dikhaye")):
            return {"action": "toggle_screen_share_stealth", "enabled": False, "raw": target_text}
        if any(tok in norm for tok in ("on", "enable", "chalu", "hide", "invisible", "activate", "laga", "karo", "chupao", "chupa")):
            return {"action": "toggle_screen_share_stealth", "enabled": True, "raw": target_text}

    # 7. STT speech recognition language
    if any(tok in norm for tok in ("language", "stt", "speak in", "talk in", "hindi mein suno", "english mein suno")):
        if "hindi" in norm or "hinglish" in norm:
            return {"action": "set_stt_language", "language": "hi-IN", "raw": target_text}
        if "english" in norm:
            return {"action": "set_stt_language", "language": "en-US", "raw": target_text}

    # 8. WebUI panel navigation (scoped strictly to UI/dashboard views so Windows Settings still opens normally)
    ui_nav_map = [
        (("ai settings", "assistant settings", "app settings", "pulsar settings", "dashboard settings"), "settings"),
        (("ai learning", "learning view", "learning tab"), "ai-learning"),
        (("dashboard",), "dashboard"),
        (("conversations", "conversation history", "chat history"), "conversations"),
        (("integrations", "integration tab"), "integrations"),
        (("database view", "database tab"), "database"),
        (("systems view", "system monitor tab", "systems tab"), "systems"),
        (("apps view", "apps tab", "apps list"), "apps"),
        (("chat view", "chat tab", "chat screen"), "chat"),
        (("voice view", "voice tab", "voice settings"), "voice"),
    ]
    if any(verb in norm for verb in ("open", "kholo", "show", "go to", "switch to")):
        for triggers, view_name in ui_nav_map:
            if any(tr in norm for tr in triggers):
                return {"action": "navigate_view", "view": view_name, "raw": target_text}

    return None


_CONTEXTUAL_BARE_TOGGLE_RE = re.compile(
    r"^(?:(?:isko|ye|it|this|that)\s+)?(?:(?:turn|switch)\s+)?"
    r"(on|off|chalu|band|enable|disable)"
    r"(?:\s+(?:it|this|that))?"
    r"(?:\s+(?:karo|kardo|karde|kar|do|de|please|plz))?$",
    re.IGNORECASE,
)


def resolve_contextual_toggle_command(
    text: str,
    context_manager=None,
    max_age_sec: float = 120.0,
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Resolve bare follow-up toggle phrases like 'off कर दो', 'on कर दो',
    'बंद कर दो', or 'चालू कर दो' using the most recent hardware/theme toggle
    recorded in ContextManager within `max_age_sec`.
    """
    if not text or not text.strip():
        return None

    _, stripped = match_and_strip_wake_phrase(text)
    target = stripped or text.strip()
    norm = normalize_hinglish_devanagari(target)
    if not norm:
        return None

    match = _CONTEXTUAL_BARE_TOGGLE_RE.match(norm)
    if not match:
        return None

    ctx = context_manager
    if ctx is None:
        try:
            from ai_assistant.core.conversation_context import get_context_manager
            ctx = get_context_manager()
        except Exception:
            return None

    last_intent = ctx.get_var("last_toggle_intent")
    last_ts = ctx.get_var("last_toggle_ts")
    if last_intent not in ("wifi_toggle", "bluetooth_toggle", "dark_mode_toggle"):
        return None

    try:
        import time as _time
        if last_ts is None or (_time.time() - float(last_ts)) > max_age_sec:
            return None
    except (TypeError, ValueError):
        return None

    action_word = match.group(1).lower()
    enable = action_word in ("on", "chalu", "enable")
    return last_intent, {"enable": enable}


def execute_voice_control_command(
    parsed: Dict[str, Any],
    broadcast_fn: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Execute a parsed voice-control command through `settings_manager.update_settings_and_sync`
    (the single settings mutation pipeline) so UI, backend, companion, and settings.json stay aligned.
    """
    sm = _import_settings_manager()
    action = parsed.get("action")

    def _emit_extra(event: str, payload: Dict[str, Any]):
        if broadcast_fn:
            try:
                broadcast_fn(event, payload)
                return
            except Exception:
                pass
        try:
            try:
                from routes.common import get_socketio
            except ImportError:
                from backend.routes.common import get_socketio
            sio = get_socketio()
            if sio:
                sio.emit(event, payload)
        except Exception:
            pass

    if action == "query_model_status":
        provider = sm.get_provider() if sm else "unknown"
        model = sm.get_model() if sm else "unknown"
        mode = "Offline (Local)" if provider == "gguf" else "Online (Cloud)"
        msg = f"Abhi active model {model} ({provider} - {mode}) chal raha hai."
        return {
            "success": True,
            "response": msg,
            "tts": f"Currently active model is {model} on {provider}.",
            "provider_used": "local_voice_control",
            "model_used": model,
            "execution_meta": {
                "provider_requested": provider,
                "provider_used": "local_voice_control",
                "model_used": model,
                "fallback": False,
            },
        }

    if action == "switch_model":
        target_provider = parsed.get("provider", "gguf")
        target_model = parsed.get("model") or (sm.get_default_model_for_provider(target_provider) if sm else "")

        if sm is None:
            return {
                "success": False,
                "response": "Settings manager unavailable.",
                "tts": "Could not switch model because settings manager is unavailable.",
            }

        # Validate online API keys before switching
        if target_provider in ("gemini", "openai"):
            key = sm.get_api_key(target_provider)
            if not key:
                msg = (
                    f"{target_provider.capitalize()} ki API key configure nahi hai. "
                    f"Pehle Settings > Security mein API key add karein."
                )
                return {
                    "success": False,
                    "response": msg,
                    "tts": f"Cannot switch to {target_provider} because no API key is configured.",
                }

        # Validate local GGUF file before switching
        if target_provider == "gguf":
            ai_cfg = sm.get_ai_settings() or {}
            rel_path = (ai_cfg.get("localLlm") or {}).get("modelPath") or "models/pulsar-final-q4_k_m.gguf"
            model_path = (_PROJECT_ROOT / rel_path) if not Path(rel_path).is_absolute() else Path(rel_path)
            if not model_path.exists():
                msg = f"Local GGUF model file nahi mili: {model_path}"
                return {
                    "success": False,
                    "response": msg,
                    "tts": "Local GGUF model file was not found.",
                }

        res = sm.update_settings_and_sync(
            "ai",
            {
                "defaultProvider": target_provider,
                "defaultModel": target_model,
            },
            broadcast_fn=broadcast_fn,
        )
        if not res.get("success"):
            err = res.get("error", "Unknown error")
            return {
                "success": False,
                "response": f"Model switch nahi ho paya: {err}",
                "tts": "Failed to switch AI model.",
            }

        label = "Local GGUF" if target_provider == "gguf" else target_provider.capitalize()
        msg = f"Done! Ab {label} ({target_model}) active ho gaya hai."
        if target_provider == "gguf":
            import importlib.util
            if importlib.util.find_spec("llama_cpp") is None:
                msg += " (Local commands active hain; offline GGUF chat ke liye venv mein llama-cpp-python install karein.)"
        return {
            "success": True,
            "response": msg,
            "tts": f"Switched to {label}, {target_model}.",
            "provider": target_provider,
            "model": target_model,
            "execution_meta": {
                "provider_requested": target_provider,
                "provider_used": "local_voice_control",
                "model_used": target_model,
                "fallback": False,
            },
        }

    if action == "toggle_wake_word":
        enabled = bool(parsed.get("enabled", True))
        if sm:
            sm.update_settings_and_sync("voice", {"wakeWord": {"enabled": enabled}}, broadcast_fn=broadcast_fn)
        state_word = "ON" if enabled else "OFF"
        return {
            "success": True,
            "response": f"Wake word ab {state_word} kar diya gaya hai.",
            "tts": f"Wake word {'enabled' if enabled else 'disabled'}.",
            "execution_meta": {"provider_used": "local_voice_control"},
        }

    if action == "toggle_continuous_listening":
        enabled = bool(parsed.get("enabled", True))
        if sm:
            sm.update_settings_and_sync("voice", {"stt": {"continuous": enabled}}, broadcast_fn=broadcast_fn)
        state_word = "ON" if enabled else "OFF"
        return {
            "success": True,
            "response": f"Continuous listening ab {state_word} hai.",
            "tts": f"Continuous listening {'enabled' if enabled else 'disabled'}.",
            "execution_meta": {"provider_used": "local_voice_control"},
        }

    if action == "stop_speaking":
        try:
            from ai_assistant.core.jarvis_persona import get_lifecycle_coordinator
            get_lifecycle_coordinator().cancel_all(reason="voice_stop_command")
        except Exception:
            pass
        try:
            from ai_assistant.core.command_brain import get_executive_brain
            brain = get_executive_brain()
            if brain.is_busy():
                brain._cancel_all_active(reason="voice_stop_command", emit_notice=False)
        except Exception:
            pass
        try:
            from ai_assistant.voice.tts_output_service import get_tts_service
            get_tts_service().stop(reason="voice_stop_command")
        except Exception:
            pass
        return {
            "success": True,
            "response": "Okay, stopped speaking.",
            "tts": "",
            "execution_meta": {"provider_used": "local_voice_control"},
        }

    if action == "toggle_tts":
        enabled = bool(parsed.get("enabled", True))
        if sm:
            sm.update_settings_and_sync("voice", {"tts": {"enabled": enabled}}, broadcast_fn=broadcast_fn)
        state_word = "ON" if enabled else "OFF"
        return {
            "success": True,
            "response": f"Voice output (TTS) ab {state_word} hai.",
            "tts": "Voice output enabled." if enabled else "",
            "execution_meta": {"provider_used": "local_voice_control"},
        }

    if action == "toggle_desktop_overlay":
        enabled = bool(parsed.get("enabled", True))
        if sm:
            sm.update_settings_and_sync("system", {"desktopOverlay": enabled}, broadcast_fn=broadcast_fn)
        state_word = "ON" if enabled else "OFF"
        return {
            "success": True,
            "response": f"Desktop 4D orb overlay ab {state_word} hai.",
            "tts": f"Desktop overlay {'shown' if enabled else 'hidden'}.",
            "execution_meta": {"provider_used": "local_voice_control"},
        }

    if action == "toggle_screen_share_stealth":
        enabled = bool(parsed.get("enabled", True))
        if sm:
            sm.update_settings_and_sync("system", {"screenShareStealth": enabled}, broadcast_fn=broadcast_fn)
        state_word = "ON (Screen share mein invisible)" if enabled else "OFF (Screen share mein visible)"
        return {
            "success": True,
            "response": f"Screen share stealth mode ab {state_word} hai.",
            "tts": f"Screen share stealth mode {'enabled' if enabled else 'disabled'}.",
            "execution_meta": {"provider_used": "local_voice_control"},
        }

    if action == "set_stt_language":
        lang = parsed.get("language", "hi-IN")
        if sm:
            sm.update_settings_and_sync("voice", {"stt": {"language": lang}}, broadcast_fn=broadcast_fn)
        label = "Hindi (hi-IN)" if lang.startswith("hi") else "English (en-US)"
        return {
            "success": True,
            "response": f"Speech recognition language {label} par set ho gayi hai.",
            "tts": f"Voice language switched to {'Hindi' if lang.startswith('hi') else 'English'}.",
            "execution_meta": {"provider_used": "local_voice_control"},
        }

    if action == "navigate_view":
        view = parsed.get("view", "dashboard")
        _emit_extra("navigate_view", {"view": view})
        return {
            "success": True,
            "response": f"WebUI mein '{view}' section khol rahi hoon.",
            "tts": f"Opening {view} view.",
            "execution_meta": {"provider_used": "local_voice_control"},
        }

    return {"success": False, "response": f"Unsupported voice control action: {action}"}
