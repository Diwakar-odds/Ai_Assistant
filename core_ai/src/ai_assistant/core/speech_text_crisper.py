"""
Deterministic Speech Text Crisper & Hallucination/Echo Filter
Zero-LLM, sub-millisecond lexical and acoustic post-STT sanitization pipeline.

Capabilities:
1. Whisper Audio & Subtitle Hallucination Rejection ([Music], [Applause], "Thanks for watching", etc.)
2. Repetitive Loop & Stutter Collapsing ("open open chrome" -> "open chrome")
3. Self-Echo Leakage Filter (matches against recent AI TTS output buffer within 3.5s)
4. Background Noise / Consonant Soup / Syllable Repetition Rejection ("na na na na na na")
5. Hesitation Filler Pruning (leading/trailing "um", "uh", "ah", "hmm", "मतलब", "तो वो")
6. Antigravity-style Text Crisping (sentence casing, punctuation normalization, trailing conjunction trimming)
"""

import re
import time
import threading
from collections import deque
from typing import Dict, Any, Optional, List, Tuple

# Thread-safe recent TTS output ring buffer for self-echo detection
_RECENT_TTS_BUFFER: deque = deque(maxlen=8)
_TTS_BUFFER_LOCK = threading.Lock()


def record_recent_tts(text: str, timestamp: Optional[float] = None) -> None:
    """
    Record an utterance spoken by the AI assistant into the recent TTS buffer.
    Used for sub-millisecond acoustic self-echo rejection.
    """
    if not text or not str(text).strip():
        return
    clean = str(text).strip()
    ts = timestamp if timestamp is not None else time.time()
    with _TTS_BUFFER_LOCK:
        _RECENT_TTS_BUFFER.append({
            "text": clean,
            "tokens": set(re.findall(r'[\w\u0900-\u097F]+', clean.lower())),
            "timestamp": ts,
        })


def get_recent_tts_records(max_age_seconds: float = 4.0) -> List[Dict[str, Any]]:
    """Return all TTS records spoken within `max_age_seconds`."""
    now = time.time()
    with _TTS_BUFFER_LOCK:
        return [r for r in _RECENT_TTS_BUFFER if now - r["timestamp"] <= max_age_seconds]


# Known Whisper subtitle and training corpus hallucination tokens
_WHISPER_HALLUCINATION_TAG_PATTERNS = [
    r'\[\s*(?:music|applause|laughter|cheering|screaming|chatter|whispering|cough|throat|sigh|giggle|groan|groans|crying)\s*\]',
    r'\(\s*(?:music|applause|laughter|cheering|screaming)\s*\)',
    r'\*\s*(?:music|applause|laughter|cheering)\s*\*+',
    r'[♪♫🎵🎶]+',
    r'\[\s*(?:संगीत|ताली|हँसी)\s*\]',
]
_COMPILED_TAG_RE = re.compile("|".join(_WHISPER_HALLUCINATION_TAG_PATTERNS), re.IGNORECASE)

_WHISPER_HALLUCINATION_SUBSTRINGS = frozenset([
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "subscribe to my channel",
    "like and subscribe",
    "subtitles by",
    "translated by",
    "all rights reserved",
    "copyright",
    "amara.org",
    "mbc news",
    "mbc 뉴스",
    "viewers like you",
    "for more videos",
    "watch next",
    "notification bell",
])

_VALID_VOWEL_LESS_LATIN_WORDS = frozenset({
    "rhythm", "rhythms", "crypt", "crypts", "lynx", "myth", "myths", "psych",
    "sync", "syncs", "gym", "gyms", "by", "my", "why", "dry", "fly", "sky",
    "spy", "try", "fry", "cry", "shy", "ply",
})

# Hesitation filler prefixes to prune from speech input
_LEADING_FILLERS_RE = re.compile(
    r'^(?:(?:um|uh|ah|er|hmm|hmmm|like|you\s+know|matlab|toh\s+wo|are\s+yaar|arey\s+yaar|suno\s+na|suno|सुनो|मतलब|अरे\s+यार)[\s,.:;!?\-]+)+',
    re.IGNORECASE | re.UNICODE,
)

# Trailing conversational fillers to prune
_TRAILING_FILLERS_RE = re.compile(
    r'[\s,.:;!?\-]+(?:(?:um|uh|ah|er|hmm|hmmm|you\s+know|matlab|na|yaar|bhai|bhaiya|boss|plz|please|pls)[\s,.:;!?\-]*)+$',
    re.IGNORECASE | re.UNICODE,
)

# Dangling conjunctions at the tail
_DANGLING_CONJUNCTION_TAIL_RE = re.compile(
    r'[\s,.:;!?\-]+(?:and|aur|और|or|warna|otherwise|then|next|phir|fir)[\s,.:;!?\-]*$',
    re.IGNORECASE | re.UNICODE,
)


def is_hallucination_or_garbage(text: str) -> Tuple[bool, str]:
    """
    Deterministically detect if `text` is a Whisper hallucination, background audio
    artifact, keyboard mashing, or non-speech syllable loop.

    Returns:
        (is_garbage: bool, reason: str)
    """
    if not text or not text.strip():
        return True, "empty_text"

    trimmed = text.strip()

    # 1. Non-alphanumeric noise (e.g. "...", "???", "--", ".,.,")
    alpha_tokens = re.findall(r'[\w\u0900-\u097F]+', trimmed)
    if not alpha_tokens:
        return True, "pure_punctuation_or_symbols"

    # 2. Check for explicit Whisper subtitle hallucination tags
    if _COMPILED_TAG_RE.search(trimmed):
        # If the text is ONLY the hallucination tag (or tag + dots), discard
        residual = _COMPILED_TAG_RE.sub("", trimmed).strip(" \t\r\n.,;:!?-_")
        if not residual:
            return True, "whisper_music_or_sound_tag"

    # 3. Check for Whisper subtitle watermark phrases
    lower_text = trimmed.lower()
    for sub in _WHISPER_HALLUCINATION_SUBSTRINGS:
        if sub in lower_text:
            return True, f"whisper_subtitle_watermark:{sub}"

    # 4. Syllable and Word Repetition Loop Detector (e.g. "na na na na na", "ha ha ha ha", "dum dum dum")
    tokens = [t.lower() for t in alpha_tokens]
    if len(tokens) >= 3:
        # Dominant single token repetition ratio
        max_freq = max(tokens.count(t) for t in set(tokens))
        ratio = max_freq / len(tokens)
        if ratio >= 0.60:
            return True, f"repetition_loop_dominant_token:{ratio:.2f}"

        # 2-gram phrase loops (e.g. "baby baby baby baby", "you know you know you know")
        if len(tokens) >= 4:
            bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]
            max_bg_freq = max(bigrams.count(b) for b in set(bigrams))
            if max_bg_freq >= 3:
                return True, f"repetition_loop_bigram:{max_bg_freq}"

    # 5. Length vs Token Count (gibberish keyboard mash or phoneme run without vowels)
    for tok in tokens:
        if len(tok) >= 5 and re.fullmatch(r'[a-z]+', tok):
            # Check vowel presence in Latin words (excluding valid vowel-less words like rhythm, sync)
            if not any(v in tok for v in "aeiou") and tok not in _VALID_VOWEL_LESS_LATIN_WORDS:
                return True, f"consonant_soup_no_vowels:{tok}"
            # Check for unpronounceable consonant clusters (6+ consonants in a row, e.g. "asdfghjkl", "zxcvbnm")
            if re.search(r'[bcdfghjklmnpqrstvwxz]{6,}', tok):
                return True, f"consonant_mash_cluster:{tok}"

    # 6. Ultra-short non-command residue (e.g. single consonant or isolated meaningless vowel "h", "k", "अ")
    if len(tokens) == 1 and len(tokens[0]) == 1:
        single = tokens[0]
        # Allow numbers ("1", "2") and known 1-letter valid words ("a", "i")
        if not single.isdigit() and single not in ("a", "i"):
            return True, f"single_character_noise:{single}"

    return False, ""


def is_recent_tts_echo(
    transcript: str,
    max_age_seconds: float = 3.5,
    similarity_threshold: float = 0.70,
) -> Tuple[bool, float, str]:
    """
    Check if `transcript` is residual microphone acoustic leakage from speech
    the AI assistant recently spoke via TTS.

    Returns:
        (is_echo: bool, overlap_score: float, matched_tts_text: str)
    """
    if not transcript or not transcript.strip():
        return False, 0.0, ""

    # Never treat an explicit user stop/pause command as echo!
    try:
        from ai_assistant.core.local_command_normalizer import is_barge_in_stop_command
        if is_barge_in_stop_command(transcript):
            return False, 0.0, ""
    except Exception:
        pass

    recent_records = get_recent_tts_records(max_age_seconds=max_age_seconds)
    if not recent_records:
        return False, 0.0, ""

    trans_tokens = [t.lower() for t in re.findall(r'[\w\u0900-\u097F]+', transcript)]
    if not trans_tokens:
        return False, 0.0, ""

    trans_set = set(trans_tokens)
    clean_trans = " ".join(trans_tokens)

    for rec in recent_records:
        rec_tokens = rec.get("tokens", set())
        rec_text = " ".join(re.findall(r'[\w\u0900-\u097F]+', rec.get("text", "").lower()))
        if not rec_tokens:
            continue

        # 1. Exact sub-phrase containment (e.g. AI said "ready hoon Boss", mic heard "ready hoon")
        if len(trans_tokens) >= 2 and clean_trans in rec_text:
            return True, 1.0, rec.get("text", "")

        # 2. Token overlap ratio (Jaccard on transcript tokens)
        intersection = trans_set.intersection(rec_tokens)
        overlap = len(intersection) / len(trans_set)
        if overlap >= similarity_threshold and len(trans_tokens) <= 6:
            return True, overlap, rec.get("text", "")

    return False, 0.0, ""


def crisp_speech_transcript(raw_text: str) -> str:
    """
    Apply deterministic Antigravity-style text crisping to raw transcribed speech:
    1. Collapse repeated tags & sound artifacts
    2. Remove consecutive duplicate words / stutters ("main main" -> "main", "open open" -> "open")
    3. Prune leading/trailing speech hesitation markers ("um", "uh", "matlab")
    4. Strip dangling conjunctions at ends ("... and", "... aur")
    5. Clean duplicate punctuation & normalize whitespace
    6. Ensure clean initial capitalization
    """
    if not raw_text or not raw_text.strip():
        return ""

    text = raw_text.strip()

    # 1. Strip sound tags like [Music], [Applause], (music), ♪
    text = _COMPILED_TAG_RE.sub(" ", text)

    # 2. Collapse consecutive duplicate words (stutter reduction)
    # Unicode and Devanagari safe word boundary collapse: "word word" -> "word"
    # Matches words repeated 2+ times: e.g. "open open open" -> "open", "मैं मैं" -> "मैं"
    text = re.sub(
        r'(?i)(?:^|(?<=\s))([\w\u0900-\u097F]+)(?:\s+\1)+(?=\s|$|[.,!?;:])',
        r'\1',
        text,
        flags=re.UNICODE,
    )

    # 3. Prune leading fillers ("um", "uh", "matlab", "suno na" before real command)
    text = _LEADING_FILLERS_RE.sub("", text)

    # 4. Iteratively prune trailing fillers & trailing conjunctions (handles nested e.g. "... please and")
    for _ in range(3):
        prev = text
        text = _DANGLING_CONJUNCTION_TAIL_RE.sub("", text)
        text = _TRAILING_FILLERS_RE.sub("", text)
        if text == prev:
            break

    # 6. Normalize punctuation runs (e.g. "???" -> "?", "..." -> ".")
    text = re.sub(r'([.?!,])\1+', r'\1', text)
    # Strip leading commas / punctuation
    text = text.strip(" \t\r\n,;:-")

    # 7. Normalize spaces
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return ""

    # 8. Clean initial capitalization (if first letter is ASCII)
    if text and text[0].isascii() and text[0].islower():
        text = text[0].upper() + text[1:]

    return text


def filter_and_crisp_speech_transcript(
    raw_transcript: str,
    require_wake_word: bool = False,
    check_echo: bool = True,
    max_echo_age: float = 3.5,
) -> Dict[str, Any]:
    """
    Unified entry point for incoming voice speech transcripts.
    Executes in <0.5ms with ZERO AI / LLM calls.

    Returns:
        {
            "valid": bool,
            "crisped_text": str,
            "matched_wake": Optional[str],
            "is_wake_only": bool,
            "rejection_reason": str,
        }
    """
    if not raw_transcript or not raw_transcript.strip():
        return {
            "valid": False,
            "crisped_text": "",
            "matched_wake": None,
            "is_wake_only": False,
            "rejection_reason": "empty_input",
        }

    # Step 1: Detect Whisper Hallucination / Noise artifacts
    is_garbage, garbage_reason = is_hallucination_or_garbage(raw_transcript)
    if is_garbage:
        return {
            "valid": False,
            "crisped_text": "",
            "matched_wake": None,
            "is_wake_only": False,
            "rejection_reason": f"hallucination_or_noise:{garbage_reason}",
        }

    # Step 2: Check Recent AI TTS Self-Echo Leakage
    if check_echo:
        is_echo, score, matched_tts = is_recent_tts_echo(raw_transcript, max_age_seconds=max_echo_age)
        if is_echo:
            return {
                "valid": False,
                "crisped_text": "",
                "matched_wake": None,
                "is_wake_only": False,
                "rejection_reason": f"recent_tts_self_echo:{score:.2f}:{matched_tts[:30]}",
            }

    # Step 3: Match and strip wake word
    from ai_assistant.core.local_command_normalizer import match_and_strip_wake_phrase
    matched_wake, clean_command = match_and_strip_wake_phrase(raw_transcript)

    if require_wake_word and not matched_wake:
        return {
            "valid": False,
            "crisped_text": "",
            "matched_wake": None,
            "is_wake_only": False,
            "rejection_reason": "wake_word_required",
        }

    # Step 3b: If wake word matched with a residual command, verify residual is not AI self-echo
    if check_echo and clean_command.strip():
        is_echo_c, score_c, matched_c = is_recent_tts_echo(clean_command, max_age_seconds=max_echo_age)
        if is_echo_c:
            return {
                "valid": False,
                "crisped_text": "",
                "matched_wake": matched_wake,
                "is_wake_only": False,
                "rejection_reason": f"recent_tts_self_echo:{score_c:.2f}:{matched_c[:30]}",
            }

    # Step 4: If wake word was detected and user only said wake word ("Hey Pulsar")
    if matched_wake and not clean_command.strip():
        return {
            "valid": True,
            "crisped_text": "",
            "matched_wake": matched_wake,
            "is_wake_only": True,
            "rejection_reason": "",
        }

    # Step 5: Apply Antigravity-style Text Crisping
    target_text = clean_command.strip() if clean_command.strip() else raw_transcript.strip()
    crisped = crisp_speech_transcript(target_text)

    # Step 6: Post-crisp validity check
    if not crisped:
        if matched_wake:
            return {
                "valid": True,
                "crisped_text": "",
                "matched_wake": matched_wake,
                "is_wake_only": True,
                "rejection_reason": "",
            }
        return {
            "valid": False,
            "crisped_text": "",
            "matched_wake": matched_wake,
            "is_wake_only": False,
            "rejection_reason": "empty_after_crisping",
        }

    return {
        "valid": True,
        "crisped_text": crisped,
        "matched_wake": matched_wake,
        "is_wake_only": False,
        "rejection_reason": "",
    }
