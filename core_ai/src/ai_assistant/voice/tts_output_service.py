"""
Unified Production Desktop TTS Output Service (Windows Native)
=================================================================

Single-speaker audio pipeline for Pulsar AI Assistant:
  - Primary (Online): EdgeTTS neural voices decoded in-memory via PyAV -> 24 kHz mono float32 PCM
  - Fallback / Local (Offline): KittenTTS mini-0.8 (8 voices) via ONNX + Indic Devanagari->Hinglish transliteration
  - Last Resort (Offline OS): Windows SAPI5 (pyttsx3 + COM CoInitialize)
  - Pipelined Sentence Streaming: SynthesisWorker -> bounded PlaybackQueue -> sounddevice.OutputStream
  - Instant Barge-In: monotonic turn_id cancellation mid-frame + queue flush
  - Acoustic Echo Protection: per-block EchoGuard.note_output() + throttled RMS telemetry
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import queue
import re
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__, log_category="app")
except Exception:
    logger = logging.getLogger(__name__)

from ai_assistant.voice.text_cleaner import (
    clean_text_for_tts,
    devanagari_to_hinglish,
    prepare_text_for_kitten_tts,
)

for _mod_alias in (
    "ai_assistant.voice.tts_output_service",
    "core_ai.src.ai_assistant.voice.tts_output_service",
):
    sys.modules.setdefault(_mod_alias, sys.modules[__name__])

TARGET_SAMPLE_RATE = 24000
BLOCK_SAMPLES = 1024  # ~42.7 ms at 24 kHz
EDGE_CIRCUIT_COOLDOWN_SEC = 45.0
SESSION_TIMBRE_LOCK_IDLE_SEC = 180.0

KITTEN_MINI_VOICES = (
    "Bella",
    "Jasper",
    "Luna",
    "Bruno",
    "Rosie",
    "Hugo",
    "Kiki",
    "Leo",
)

_MALE_EDGE_HINTS = (
    "guy",
    "davis",
    "ryan",
    "prabhat",
    "christopher",
    "eric",
    "madhur",
    "andrew",
    "brian",
    "jasper",
    "bruno",
    "hugo",
    "leo",
    "david",
    "mark",
    "ravi",
    "hemant",
)


def is_male_voice_hint(configured_voice: Optional[str]) -> bool:
    """Return True only when a configured voice explicitly selects a male speaker."""
    if not configured_voice:
        return False
    v_low = str(configured_voice).strip().lower()
    if any(hint in v_low for hint in _MALE_EDGE_HINTS):
        return True
    return bool(re.search(r"\bmale\b", v_low))


def configure_sapi5_voice(engine: Any, configured_voice: Optional[str] = None) -> Optional[str]:
    """Select a female Windows SAPI5 voice by default (avoiding male David fallback)."""
    if configured_voice is None:
        try:
            from settings_manager import get_tts_voice_id
            configured_voice = get_tts_voice_id()
        except Exception:
            configured_voice = None

    want_male = is_male_voice_hint(configured_voice)
    try:
        voices = list(engine.getProperty("voices") or [])
    except Exception:
        return None
    if not voices:
        return None

    chosen = None
    if want_male:
        male_prefs = ("ravi", "hemant", "david", "mark", "george", "male")
        for pref in male_prefs:
            for v in voices:
                desc = f"{getattr(v, 'name', '')} {getattr(v, 'id', '')}".lower()
                if pref == "male":
                    if re.search(r"\bmale\b", desc):
                        chosen = v
                        break
                elif pref in desc:
                    chosen = v
                    break
            if chosen is not None:
                break
    else:
        female_prefs = ("heera", "kalpana", "zira", "hazel", "susan", "eva", "aria", "female")
        for pref in female_prefs:
            for v in voices:
                desc = f"{getattr(v, 'name', '')} {getattr(v, 'id', '')}".lower()
                if pref in desc:
                    chosen = v
                    break
            if chosen is not None:
                break
        if chosen is None:
            for v in voices:
                desc = f"{getattr(v, 'name', '')} {getattr(v, 'id', '')}".lower()
                if not any(m in desc for m in ("david", "mark", "george", "richard", "hemant", "ravi")):
                    chosen = v
                    break

    if chosen is not None:
        try:
            engine.setProperty("voice", chosen.id)
            return str(chosen.id)
        except Exception:
            pass
    return None

_ESPEAK_ENV_LOCK = threading.Lock()
_ESPEAK_ENV_CONFIGURED = False

_KITTEN_MODEL_LOCK = threading.Lock()
_KITTEN_MODEL_INSTANCE: Any = None


def ensure_espeak_environment() -> Tuple[Optional[str], Optional[str]]:
    """Configure PHONEMIZER_ESPEAK_LIBRARY and ESPEAK_DATA_PATH without hardcoded C:\\ paths."""
    global _ESPEAK_ENV_CONFIGURED
    with _ESPEAK_ENV_LOCK:
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
        lib_candidates: List[Path] = []
        data_candidates: List[Path] = []

        try:
            import espeakng_loader

            lp = espeakng_loader.get_library_path()
            dp = espeakng_loader.get_data_path()
            if lp:
                lib_candidates.append(Path(lp))
            if dp:
                data_candidates.append(Path(dp))
        except Exception:
            pass

        meipass = getattr(sys, "_MEIPASS", None)
        exe_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else None
        for root in [Path(meipass) if meipass else None, exe_dir / "_internal" if exe_dir else None, exe_dir]:
            if root is not None:
                lib_candidates.append(root / "espeakng_loader" / "espeak-ng.dll")
                data_candidates.append(root / "espeakng_loader" / "espeak-ng-data")

        # Legacy system install fallback
        lib_candidates.append(Path(r"C:\Program Files\eSpeak NG\libespeak-ng.dll"))
        data_candidates.append(Path(r"C:\Program Files\eSpeak NG\espeak-ng-data"))

        chosen_lib = next((str(p) for p in lib_candidates if p and p.exists()), None)
        chosen_data = next((str(p) for p in data_candidates if p and p.exists()), None)

        if chosen_lib and not _ESPEAK_ENV_CONFIGURED:
            os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = chosen_lib
            try:
                from phonemizer.backend.espeak.wrapper import EspeakWrapper
                EspeakWrapper.set_library(chosen_lib)
            except Exception:
                pass
        if chosen_data and not _ESPEAK_ENV_CONFIGURED:
            os.environ["ESPEAK_DATA_PATH"] = chosen_data
            try:
                from phonemizer.backend.espeak.wrapper import EspeakWrapper
                if hasattr(EspeakWrapper, "set_data_path"):
                    EspeakWrapper.set_data_path(chosen_data)
            except Exception:
                pass

        _ESPEAK_ENV_CONFIGURED = True
        return chosen_lib, chosen_data


def resolve_kitten_mini_dir() -> Optional[Path]:
    """Locate the local offline KittenTTS mini-0.8 directory across AppData, PyInstaller, and dev tree."""
    rel = Path("models") / "tts" / "kitten-tts-mini-0.8"
    candidates: List[Optional[Path]] = []

    try:
        from settings_manager import resolve_local_model_path
        resolved = resolve_local_model_path(str(rel))
        candidates.append(resolved)
    except Exception:
        pass

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / rel)
    if getattr(sys, "frozen", False):
        exe_parent = Path(sys.executable).resolve().parent
        candidates.append(exe_parent / "_internal" / rel)
        candidates.append(exe_parent / rel)

    # Repo root: core_ai/src/ai_assistant/voice/tts_output_service.py -> parents[4]
    try:
        repo_root = Path(__file__).resolve().parents[4]
        candidates.append(repo_root / rel)
    except Exception:
        pass
    candidates.append(Path.cwd() / rel)

    for cand in candidates:
        if cand and cand.is_dir() and (cand / "kitten_tts_mini_v0_8.onnx").is_file() and (cand / "voices.npz").is_file():
            return cand
    return None


def load_kitten_mini_model():
    """Load the thread-safe KittenTTS mini-0.8 model offline from local weights."""
    global _KITTEN_MODEL_INSTANCE
    if _KITTEN_MODEL_INSTANCE is not None:
        return _KITTEN_MODEL_INSTANCE

    with _KITTEN_MODEL_LOCK:
        if _KITTEN_MODEL_INSTANCE is not None:
            return _KITTEN_MODEL_INSTANCE

        ensure_espeak_environment()
        model_dir = resolve_kitten_mini_dir()

        if model_dir is not None:
            config_path = model_dir / "config.json"
            cfg: Dict[str, Any] = {}
            if config_path.is_file():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                except Exception as cfg_err:
                    logger.warning(f"[TTS] Could not read KittenTTS config.json: {cfg_err}")

            onnx_file = model_dir / str(cfg.get("model_file") or "kitten_tts_mini_v0_8.onnx")
            voices_file = model_dir / str(cfg.get("voices") or "voices.npz")
            speed_priors = cfg.get("speed_priors") if isinstance(cfg.get("speed_priors"), dict) else {}
            voice_aliases = cfg.get("voice_aliases") if isinstance(cfg.get("voice_aliases"), dict) else {}

            if onnx_file.is_file() and voices_file.is_file():
                from kittentts.onnx_model import KittenTTS_1_Onnx

                _KITTEN_MODEL_INSTANCE = KittenTTS_1_Onnx(
                    model_path=str(onnx_file),
                    voices_path=str(voices_file),
                    speed_priors=speed_priors,
                    voice_aliases=voice_aliases,
                )
                logger.info(f"[TTS] Loaded KittenTTS mini-0.8 strictly offline from {model_dir}")
                return _KITTEN_MODEL_INSTANCE

        # Fallback to standard HuggingFace loader only if local folder wasn't found
        from kittentts import KittenTTS

        _KITTEN_MODEL_INSTANCE = KittenTTS("KittenML/kitten-tts-mini-0.8")
        logger.info("[TTS] Loaded KittenTTS mini-0.8 via package loader")
        return _KITTEN_MODEL_INSTANCE


def resolve_kitten_voice(configured_voice: Optional[str]) -> str:
    """Resolve any UI/config voice identifier into one of the 8 KittenTTS mini-0.8 voices."""
    if not configured_voice:
        return "Bella"
    v = str(configured_voice).strip()
    if v.lower().startswith("kitten:"):
        candidate = v.split(":", 1)[1].strip()
        for k in KITTEN_MINI_VOICES:
            if k.lower() == candidate.lower():
                return k
    for k in KITTEN_MINI_VOICES:
        if k.lower() == v.lower():
            return k
    v_lower = v.lower()
    if any(hint in v_lower for hint in _MALE_EDGE_HINTS):
        return "Jasper"
    return "Bella"


_HINGLISH_EDGE_MARKERS = re.compile(
    r"\b(?:haan|haa|han|ji|jee|theek|thik|sun|raha|rahaa|rahi|rahee|hoon|hun|"
    r"kya|kaise|kaisa|karo|kardo|karna|kholo|khol|band|batao|batayein|boliye|"
    r"suniye|samajh|abhi|yahin|bilkul|zaroor|namaste|shukriya)\b",
    re.IGNORECASE,
)


def resolve_edge_voice(text: str, configured_voice: Optional[str]) -> str:
    """Pick the best EdgeTTS voice (auto-switching to hi-IN for Devanagari or Hinglish text)."""
    has_devanagari = bool(re.search(r"[\u0900-\u097F]", text or ""))
    has_hinglish = bool(_HINGLISH_EDGE_MARKERS.search(text or ""))
    v = str(configured_voice or "").strip()
    want_male = is_male_voice_hint(v)

    if has_devanagari or has_hinglish:
        if v.startswith("hi-IN-"):
            return v
        return "hi-IN-MadhurNeural" if want_male else "hi-IN-SwaraNeural"

    if "Neural" in v:
        return v
    if want_male:
        return "en-IN-PrabhatNeural"
    return "en-US-AriaNeural"


def decode_audio_bytes_to_pcm24k(audio_bytes: bytes, format_hint: Optional[str] = None) -> np.ndarray:
    """Decode in-memory MP3/WAV/OGG audio bytes to 24 kHz mono float32 PCM using PyAV."""
    if not audio_bytes:
        return np.zeros(0, dtype=np.float32)

    import av

    bio = io.BytesIO(audio_bytes)
    open_kwargs: Dict[str, Any] = {}
    if format_hint:
        open_kwargs["format"] = format_hint

    chunks: List[np.ndarray] = []
    container = av.open(bio, **open_kwargs)
    try:
        resampler = av.audio.resampler.AudioResampler(
            format="flt",
            layout="mono",
            rate=TARGET_SAMPLE_RATE,
        )
        for frame in container.decode(audio=0):
            for rframe in resampler.resample(frame):
                arr = np.asarray(rframe.to_ndarray(), dtype=np.float32).reshape(-1)
                if arr.size > 0:
                    chunks.append(arr)
        for rframe in resampler.resample(None):
            arr = np.asarray(rframe.to_ndarray(), dtype=np.float32).reshape(-1)
            if arr.size > 0:
                chunks.append(arr)
    finally:
        try:
            container.close()
        except Exception:
            pass

    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks).astype(np.float32, copy=False)


def pcm_to_wav_bytes(pcm: np.ndarray, sample_rate: int = TARGET_SAMPLE_RATE) -> bytes:
    """Encode float32 PCM (-1..1) as 16-bit mono WAV bytes in memory."""
    import wave

    clipped = np.clip(np.asarray(pcm, dtype=np.float32).reshape(-1), -1.0, 1.0)
    int16_data = (clipped * 32767.0).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int16_data.tobytes())
    return buf.getvalue()


# Boundary regex for streaming sentence chunking:
# - Hindi danda '।' or double-danda '॥' (always ends a sentence)
# - Newlines
# - '.', '!', '?' followed by whitespace (or end of buffer ONLY when final=True)
#   Avoids splitting numbers like "3.14" or "v0.8" mid-token.
_RE_SENTENCE_SPLIT = re.compile(
    r"(?:।+|॥+|\r?\n+|(?<!\d)[.!?]+(?=\s)|(?<=[^\d\s])[.!?]+$)"
)
_RE_CLAUSE_SPLIT = re.compile(r"[,;—–]\s+")


def split_speakable_chunks(buffer: str, final: bool = False) -> Tuple[List[str], str]:
    """
    Split streaming LLM output buffer cleanly on Hindi/English sentence boundaries
    while preserving any trailing incomplete phrase in remaining_buffer.
    """
    if not buffer:
        return [], ""

    work = buffer
    chunks: List[str] = []

    while work:
        matched_end: Optional[int] = None

        for m in _RE_SENTENCE_SPLIT.finditer(work):
            end_pos = m.end()
            # If the match ended at EOS on `.!?` (no trailing whitespace yet), hold back
            # unless this is the final flush so we don't split abbreviations/decimals mid-stream.
            if end_pos == len(work) and not final and work[m.start():m.end()] not in ("।", "॥") and "\n" not in work[m.start():m.end()]:
                continue
            matched_end = end_pos
            break

        if matched_end is not None:
            piece = work[:matched_end].strip()
            work = work[matched_end:].lstrip()
            if piece:
                chunks.append(piece)
            continue

        # Clause split only when accumulated clause is quite long (keeps short Hindi/Hinglish fluent)
        if len(work) >= 75 and len(work.split()) >= 11:
            clause_match = None
            for cm in _RE_CLAUSE_SPLIT.finditer(work):
                prefix = work[:cm.end()].strip()
                if len(prefix.split()) >= 8 or len(prefix) >= 55:
                    clause_match = cm
                    break
            if clause_match is not None:
                piece = work[:clause_match.end()].strip()
                work = work[clause_match.end():].lstrip()
                if piece:
                    chunks.append(piece)
                continue

        # Hard safety wrap for ultra-long unpunctuated runs
        if len(work) >= 160:
            cut = work.rfind(" ", 80, 160)
            if cut > 0:
                piece = work[:cut].strip()
                work = work[cut:].lstrip()
                if piece:
                    chunks.append(piece)
                continue

        break

    if final and work.strip():
        chunks.append(work.strip())
        work = ""

    return chunks, work


@dataclass
class _SynthJob:
    gen: int
    text: str
    source: str
    voice_override: Optional[str] = None
    engine_override: Optional[str] = None
    speed_override: Optional[float] = None
    volume_override: Optional[float] = None


@dataclass
class _PlayItem:
    gen: int
    source: str
    engine_used: str
    pcm: Optional[np.ndarray] = None
    sapi_fallback_text: Optional[str] = None
    speed: float = 1.0
    volume: float = 0.9
    configured_voice: Optional[str] = None


def _load_tts_prefs() -> Dict[str, Any]:
    defaults = {
        "enabled": True,
        "engine": "edge_tts",
        "voice_id": "hi-IN-SwaraNeural",
        "speed": 1.0,
        "volume": 0.9,
    }
    try:
        from settings_manager import get_tts_config
        cfg = get_tts_config()
        if isinstance(cfg, dict):
            defaults.update(cfg)
    except Exception:
        pass
    return defaults


class TTSOutputService:
    """
    Single-speaker desktop TTS output coordinator with streaming queue,
    instant barge-in cancellation, offline KittenTTS fallback, and EchoGuard sync.
    """

    def __init__(
        self,
        edge_cooldown_sec: float = EDGE_CIRCUIT_COOLDOWN_SEC,
        session_lock_idle_sec: float = SESSION_TIMBRE_LOCK_IDLE_SEC,
        audio_writer: Optional[Callable[[np.ndarray, int], None]] = None,
    ):
        self._lock = threading.RLock()
        self._next_gen: int = 0
        self._min_valid_gen: int = 1
        self._active_stream_gen: Optional[int] = None

        self._synth_queue: queue.Queue[Optional[_SynthJob]] = queue.Queue()
        self._play_queue: queue.Queue[Optional[_PlayItem]] = queue.Queue(maxsize=4)

        self._abort_event = threading.Event()
        self._shutdown = False
        self._idle_event = threading.Event()
        self._idle_event.set()

        self._is_speaking = False
        self._active_engine = "none"
        self._pending_synth_count = 0
        self._pending_play_count = 0

        self._edge_cooldown_sec = float(edge_cooldown_sec)
        self._session_lock_idle_sec = float(session_lock_idle_sec)
        self._edge_breaker_until: float = 0.0
        self._edge_consecutive_errors: int = 0
        self._turn_engine_pins: Dict[int, str] = {}
        self._session_fallback_active: bool = False
        self._session_fallback_last_activity: float = 0.0
        self._last_prefs_sig: Optional[Tuple[str, str]] = None

        self._audio_writer = audio_writer
        self._state_callback: Optional[Callable[[bool, float, str], None]] = None
        self._last_telemetry_emit: float = 0.0

        self._synth_thread = threading.Thread(
            target=self._synth_worker_loop, name="PulsarTTSSynthWorker", daemon=True
        )
        self._play_thread = threading.Thread(
            target=self._play_worker_loop, name="PulsarTTSPlayWorker", daemon=True
        )
        self._synth_thread.start()
        self._play_thread.start()
        threading.Thread(
            target=self._prewarm_default_engine,
            name="PulsarTTSPrewarm",
            daemon=True,
        ).start()

    def _prewarm_default_engine(self) -> None:
        try:
            prefs = _load_tts_prefs()
            eng = str(prefs.get("engine") or "").strip().lower()
            vid = str(prefs.get("voice_id") or "").strip().lower()
            if (
                eng == "kittentts"
                or vid == "kittentts"
                or vid.startswith("kitten:")
                or resolve_kitten_mini_dir() is not None
            ):
                load_kitten_mini_model()
        except Exception as exc:
            logger.debug(f"[TTS] KittenTTS prewarm skipped: {exc}")

    # ── Public API ────────────────────────────────────────────────────────

    def set_state_callback(self, callback: Optional[Callable[[bool, float, str], None]]) -> None:
        """Register callback(speaking: bool, audio_level_0_100: float, source: str)."""
        with self._lock:
            self._state_callback = callback

    def is_speaking(self) -> bool:
        with self._lock:
            return self._is_speaking or self._pending_synth_count > 0 or self._pending_play_count > 0

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            breaker_rem = max(0.0, self._edge_breaker_until - now)
            q_synth = max(self._pending_synth_count, self._synth_queue.qsize())
            q_play = max(self._pending_play_count, self._play_queue.qsize())
            return {
                "speaking": self._is_speaking or self._pending_synth_count > 0 or self._pending_play_count > 0,
                "active_playback": self._is_speaking,
                "active_engine": self._active_engine,
                "queued_synth": q_synth,
                "queued_play": q_play,
                "edge_circuit_open": breaker_rem > 0.0,
                "edge_cooldown_remaining_s": round(breaker_rem, 1),
                "session_timbre_locked_engine": "kittentts" if self._session_fallback_active else None,
                "kitten_offline_ready": resolve_kitten_mini_dir() is not None,
                "sample_rate": TARGET_SAMPLE_RATE,
            }

    def begin_stream(self, interrupt: bool = True, source: str = "assistant") -> int:
        """Start a streaming speech turn and return its generation token."""
        with self._lock:
            self._next_gen += 1
            gen = self._next_gen
            self._active_stream_gen = gen
            if interrupt:
                self._min_valid_gen = gen
                self._flush_queues_locked()
                self._abort_event.set()
            else:
                self._abort_event.clear()
            return gen

    def enqueue_sentence(
        self,
        text: str,
        gen: Optional[int] = None,
        source: str = "assistant",
        voice: Optional[str] = None,
        engine: Optional[str] = None,
    ) -> Optional[int]:
        """Queue one speakable sentence without interrupting earlier sentences of the same turn."""
        cleaned = clean_text_for_tts(text)
        if not cleaned:
            return None

        prefs = _load_tts_prefs()
        if not prefs.get("enabled", True) and not engine and not voice:
            return None

        with self._lock:
            target_gen = gen if gen is not None else self._active_stream_gen
            if target_gen is None or target_gen < self._min_valid_gen:
                return None
            if target_gen == self._min_valid_gen:
                self._abort_event.clear()
            self._idle_event.clear()
            self._pending_synth_count += 1
            self._synth_queue.put(
                _SynthJob(
                    gen=target_gen,
                    text=cleaned,
                    source=source,
                    voice_override=voice,
                    engine_override=engine,
                )
            )
            return target_gen

    def finish_stream(self, gen: Optional[int] = None, wait: bool = False, timeout: Optional[float] = None) -> bool:
        """Mark streaming turn complete; optionally wait for queued sentences to finish playing."""
        with self._lock:
            if gen is None or self._active_stream_gen == gen:
                self._active_stream_gen = None
        if wait:
            return self.wait_until_idle(timeout=timeout)
        return True

    def speak(
        self,
        text: str,
        *,
        interrupt: bool = True,
        wait: bool = False,
        timeout: Optional[float] = None,
        source: str = "assistant",
        voice: Optional[str] = None,
        engine: Optional[str] = None,
        speed: Optional[float] = None,
        volume: Optional[float] = None,
    ) -> bool:
        """Speak complete text (auto-split into clean sentences for fast first-audio latency)."""
        cleaned = clean_text_for_tts(text)
        if not cleaned:
            return False

        prefs = _load_tts_prefs()
        if not prefs.get("enabled", True) and not engine and not voice:
            return False

        sentences, rem = split_speakable_chunks(cleaned, final=True)
        if rem:
            sentences.append(rem)
        if not sentences:
            sentences = [cleaned]

        with self._lock:
            self._next_gen += 1
            gen = self._next_gen
            self._active_stream_gen = None
            if interrupt:
                self._min_valid_gen = gen
                self._flush_queues_locked()
                self._abort_event.set()
            else:
                self._abort_event.clear()

            # Allow newly submitted gen to clear abort before workers pick it up
            self._abort_event.clear()
            self._idle_event.clear()
            for sent in sentences:
                self._pending_synth_count += 1
                self._synth_queue.put(
                    _SynthJob(
                        gen=gen,
                        text=sent,
                        source=source,
                        voice_override=voice,
                        engine_override=engine,
                        speed_override=speed,
                        volume_override=volume,
                    )
                )

        if wait:
            return self.wait_until_idle(timeout=timeout)
        return True

    def stop(self, reason: str = "barge_in") -> None:
        """Immediately stop ongoing playback and flush all pending sentences."""
        was_active = False
        with self._lock:
            was_active = self._is_speaking or self._pending_synth_count > 0 or self._pending_play_count > 0
            self._next_gen += 1
            self._min_valid_gen = self._next_gen + 1
            self._active_stream_gen = None
            self._abort_event.set()
            self._flush_queues_locked()
            self._is_speaking = False
            self._pending_synth_count = 0
            self._pending_play_count = 0
            self._idle_event.set()

        self._reset_echo_guard()
        self._set_legacy_tts_flag(False)
        if was_active:
            logger.info(f"[TTS] Interrupted playback ({reason})")
            self._emit_state(False, 0.0, "backend_tts", force=True)

    def wait_until_idle(self, timeout: Optional[float] = None) -> bool:
        return self._idle_event.wait(timeout=timeout)

    def reset_edge_circuit_breaker(self) -> None:
        with self._lock:
            self._edge_breaker_until = 0.0
            self._edge_consecutive_errors = 0
            self._session_fallback_active = False
            self._session_fallback_last_activity = 0.0
            self._turn_engine_pins.clear()

    # ── Synthesis & Playback Workers ──────────────────────────────────────

    def _flush_queues_locked(self) -> None:
        while not self._synth_queue.empty():
            try:
                self._synth_queue.get_nowait()
                self._pending_synth_count = max(0, self._pending_synth_count - 1)
            except queue.Empty:
                break
        while not self._play_queue.empty():
            try:
                self._play_queue.get_nowait()
                self._pending_play_count = max(0, self._pending_play_count - 1)
            except queue.Empty:
                break

    def _is_gen_valid(self, gen: int) -> bool:
        with self._lock:
            return (not self._shutdown) and gen >= self._min_valid_gen

    def _synth_worker_loop(self) -> None:
        while not self._shutdown:
            try:
                job = self._synth_queue.get(timeout=0.25)
            except queue.Empty:
                continue

            if job is None:
                break

            try:
                if not self._is_gen_valid(job.gen):
                    continue

                item = self._synthesize_job(job)
                if item is None or not self._is_gen_valid(job.gen):
                    continue

                with self._lock:
                    if not self._is_gen_valid(job.gen):
                        continue
                    self._pending_play_count += 1

                # Bounded enqueue with periodic validity check so stop() never stalls
                placed = False
                while not self._shutdown and self._is_gen_valid(job.gen):
                    try:
                        self._play_queue.put(item, timeout=0.05)
                        placed = True
                        break
                    except queue.Full:
                        continue

                if not placed:
                    with self._lock:
                        self._pending_play_count = max(0, self._pending_play_count - 1)
            except Exception as e:
                logger.error(f"[TTS] Synth worker error: {e}")
            finally:
                became_idle = False
                with self._lock:
                    self._pending_synth_count = max(0, self._pending_synth_count - 1)
                    if (
                        self._pending_synth_count == 0
                        and self._pending_play_count == 0
                        and not self._is_speaking
                        and self._active_stream_gen is None
                    ):
                        self._idle_event.set()
                        became_idle = True
                if became_idle:
                    self._set_legacy_tts_flag(False)
                    self._emit_state(False, 0.0, "backend_tts", force=True)

    def _synthesize_job(self, job: _SynthJob) -> Optional[_PlayItem]:
        prefs = _load_tts_prefs()
        prefs_sig = (
            str(prefs.get("engine") or "").strip().lower(),
            str(prefs.get("voice_id") or "").strip().lower(),
        )
        voice_id = str(job.voice_override or prefs.get("voice_id") or "hi-IN-SwaraNeural").strip()
        if job.engine_override:
            engine = str(job.engine_override).strip().lower()
        elif job.voice_override:
            vid_low = voice_id.lower()
            if vid_low == "kittentts" or vid_low.startswith("kitten:"):
                engine = "kittentts"
            elif "neural" in vid_low:
                engine = "edge_tts"
            elif vid_low in ("pyttsx3", "sapi5") or vid_low.startswith("sapi"):
                engine = "pyttsx3"
            else:
                engine = str(prefs.get("engine") or "edge_tts").strip().lower()
        else:
            engine = str(prefs.get("engine") or "edge_tts").strip().lower()
        try:
            speed = float(job.speed_override if job.speed_override is not None else prefs.get("speed", 1.0))
        except (TypeError, ValueError):
            speed = 1.0
        try:
            volume = float(job.volume_override if job.volume_override is not None else prefs.get("volume", 0.9))
        except (TypeError, ValueError):
            volume = 0.9
        speed = max(0.5, min(2.0, speed))
        volume = max(0.0, min(1.5, volume))

        force_kitten = (
            engine == "kittentts"
            or voice_id.lower() == "kittentts"
            or voice_id.lower().startswith("kitten:")
        )

        allow_edge = (not force_kitten) and (engine != "pyttsx3")
        with self._lock:
            now = time.monotonic()
            # Reset sticky session lock automatically if user switched TTS engine/voice in settings
            if self._last_prefs_sig is not None and prefs_sig != self._last_prefs_sig:
                self._session_fallback_active = False
                self._session_fallback_last_activity = 0.0
                self._edge_breaker_until = 0.0
                self._edge_consecutive_errors = 0
                self._turn_engine_pins.clear()
            self._last_prefs_sig = prefs_sig

            # Prune stale turn pins
            if len(self._turn_engine_pins) > 32:
                cutoff = self._min_valid_gen - 16
                self._turn_engine_pins = {g: e for g, e in self._turn_engine_pins.items() if g >= cutoff}

            turn_pin = self._turn_engine_pins.get(job.gen)
            if turn_pin == "kittentts":
                # Keep all sentences within a single turn in the exact same timbre
                allow_edge = False
            elif allow_edge and self._session_fallback_active and job.engine_override != "edge_tts":
                # Keep the active conversation session locked to KittenTTS until long idle or settings reset
                if (now - self._session_fallback_last_activity) < self._session_lock_idle_sec:
                    self._session_fallback_last_activity = now
                    allow_edge = False
                else:
                    self._session_fallback_active = False
                    self._session_fallback_last_activity = 0.0

        # 1. Online EdgeTTS (primary when configured and session is not locked to fallback)
        if allow_edge:
            with self._lock:
                breaker_open = time.monotonic() < self._edge_breaker_until
                if breaker_open:
                    self._turn_engine_pins[job.gen] = "kittentts"
                    self._session_fallback_active = True
                    self._session_fallback_last_activity = time.monotonic()
            if not breaker_open:
                pcm = self._try_edge_tts_pcm(job.text, voice_id, speed, job.gen)
                if pcm is not None and pcm.size > 0:
                    with self._lock:
                        self._turn_engine_pins.setdefault(job.gen, "edge_tts")
                        self._session_fallback_last_activity = time.monotonic()
                    return _PlayItem(
                        gen=job.gen,
                        source=job.source,
                        engine_used="edge_tts",
                        pcm=self._prepare_pcm(pcm, volume),
                        speed=speed,
                        volume=volume,
                        configured_voice=voice_id,
                    )
                with self._lock:
                    self._turn_engine_pins[job.gen] = "kittentts"
                    self._session_fallback_active = True
                    self._session_fallback_last_activity = time.monotonic()

        if not self._is_gen_valid(job.gen):
            return None

        # 2. Offline neural engine: KittenTTS mini-0.8 (local/fallback)
        if engine != "pyttsx3":
            pcm = self._try_kitten_tts_pcm(job.text, voice_id, speed)
            if pcm is not None and pcm.size > 0:
                with self._lock:
                    self._turn_engine_pins.setdefault(job.gen, "kittentts")
                    if self._session_fallback_active:
                        self._session_fallback_last_activity = time.monotonic()
                return _PlayItem(
                    gen=job.gen,
                    source=job.source,
                    engine_used="kittentts",
                    pcm=self._prepare_pcm(pcm, volume),
                    speed=speed,
                    volume=volume,
                    configured_voice=voice_id,
                )

        if not self._is_gen_valid(job.gen):
            return None

        # 3. Last-resort OS fallback: Windows SAPI5 (pyttsx3, Female by default)
        pcm = self._try_sapi5_to_pcm(job.text, speed, volume, configured_voice=voice_id)
        if pcm is not None and pcm.size > 0:
            return _PlayItem(
                gen=job.gen,
                source=job.source,
                engine_used="pyttsx3",
                pcm=self._prepare_pcm(pcm, 1.0),
                speed=speed,
                volume=volume,
                configured_voice=voice_id,
            )

        return _PlayItem(
            gen=job.gen,
            source=job.source,
            engine_used="pyttsx3_direct",
            pcm=None,
            sapi_fallback_text=job.text,
            speed=speed,
            volume=volume,
            configured_voice=voice_id,
        )

    def _try_edge_tts_pcm(self, text: str, configured_voice: str, speed: float, gen: int) -> Optional[np.ndarray]:
        try:
            import edge_tts
        except ImportError:
            return None

        target_voice = resolve_edge_voice(text, configured_voice)
        pct = int(round((speed - 1.0) * 100.0))
        rate_str = f"{pct:+d}%"

        async def _fetch_bytes() -> bytes:
            comm = edge_tts.Communicate(text, target_voice, rate=rate_str)
            buf = bytearray()
            async for chunk in comm.stream():
                if not self._is_gen_valid(gen):
                    break
                if chunk.get("type") == "audio":
                    data = chunk.get("data")
                    if data:
                        buf.extend(data)
            return bytes(buf)

        try:
            async def _fetch_timed() -> bytes:
                return await asyncio.wait_for(_fetch_bytes(), timeout=4.0)

            try:
                asyncio.get_running_loop()
                loop_running = True
            except RuntimeError:
                loop_running = False

            if loop_running:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    audio_bytes = pool.submit(lambda: asyncio.run(_fetch_timed())).result(timeout=5.0)
            else:
                audio_bytes = asyncio.run(_fetch_timed())

            if not self._is_gen_valid(gen):
                return None
            if not audio_bytes:
                raise RuntimeError("EdgeTTS returned empty audio stream")

            pcm = decode_audio_bytes_to_pcm24k(audio_bytes, format_hint="mp3")
            if pcm.size == 0:
                raise RuntimeError("PyAV decoded 0 frames from EdgeTTS stream")

            with self._lock:
                self._edge_breaker_until = 0.0
                self._edge_consecutive_errors = 0
            return pcm
        except Exception as err:
            with self._lock:
                self._edge_consecutive_errors += 1
                self._edge_breaker_until = time.monotonic() + self._edge_cooldown_sec
            logger.warning(
                f"[TTS] EdgeTTS unavailable ({type(err).__name__}: {err}) — switching to KittenTTS mini-0.8 for {self._edge_cooldown_sec:.0f}s"
            )
            return None

    def _try_kitten_tts_pcm(self, text: str, configured_voice: str, speed: float) -> Optional[np.ndarray]:
        try:
            cleaned = prepare_text_for_kitten_tts(text)
            if not cleaned:
                return None

            model = load_kitten_mini_model()
            voice_alias = resolve_kitten_voice(configured_voice)
            raw = model.generate(cleaned, voice=voice_alias, speed=speed, clean_text=True)
            pcm = np.asarray(raw, dtype=np.float32).reshape(-1)
            return pcm if pcm.size > 0 else None
        except Exception as err:
            logger.error(f"[TTS] KittenTTS synthesis failed: {err}")
            return None

    def _try_sapi5_to_pcm(
        self,
        text: str,
        speed: float,
        volume: float,
        configured_voice: Optional[str] = None,
    ) -> Optional[np.ndarray]:
        """Synthesize via Windows SAPI5 into a temporary WAV and load as 24 kHz float32 PCM."""
        coinit_done = False
        tmp_path: Optional[str] = None
        try:
            try:
                import pythoncom
                pythoncom.CoInitialize()
                coinit_done = True
            except Exception:
                pass

            import pyttsx3

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                tmp_path = tf.name

            engine = pyttsx3.init()
            configure_sapi5_voice(engine, configured_voice=configured_voice)
            engine.setProperty("rate", int(round(175 * speed)))
            engine.setProperty("volume", max(0.0, min(1.0, volume)))
            engine.save_to_file(text, tmp_path)
            engine.runAndWait()
            try:
                engine.stop()
            except Exception:
                pass

            if tmp_path and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 44:
                with open(tmp_path, "rb") as f:
                    wav_bytes = f.read()
                pcm = decode_audio_bytes_to_pcm24k(wav_bytes, format_hint="wav")
                if pcm.size > 0:
                    return pcm
        except Exception as err:
            logger.debug(f"[TTS] SAPI5 WAV capture failed: {err}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            if coinit_done:
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
        return None

    @staticmethod
    def _prepare_pcm(pcm: np.ndarray, volume: float) -> np.ndarray:
        arr = np.asarray(pcm, dtype=np.float32).reshape(-1)
        if arr.size == 0:
            return arr
        # Prevent hard clipping on boosted waveforms, apply volume
        peak = float(np.max(np.abs(arr)))
        if peak > 1.0:
            arr = arr / peak
        arr = np.clip(arr * float(volume), -1.0, 1.0).astype(np.float32, copy=False)

        # Gentle 5 ms fade-in / fade-out to avoid inter-sentence clicks
        fade = min(120, arr.size // 4)
        if fade > 4:
            ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            arr = arr.copy()
            arr[:fade] *= ramp
            arr[-fade:] *= ramp[::-1]
        return arr

    # ── Playback Worker ───────────────────────────────────────────────────

    def _play_worker_loop(self) -> None:
        sd_stream = None
        last_item_end = time.monotonic()

        def _close_stream():
            nonlocal sd_stream
            if sd_stream is not None:
                try:
                    sd_stream.stop()
                except Exception:
                    pass
                try:
                    sd_stream.close()
                except Exception:
                    pass
                sd_stream = None

        while not self._shutdown:
            item: Optional[_PlayItem] = None
            try:
                item = self._play_queue.get(timeout=0.08)
            except queue.Empty:
                if sd_stream is not None and (time.monotonic() - last_item_end) > 1.2:
                    _close_stream()
                with self._lock:
                    if self._is_speaking and self._pending_synth_count == 0 and self._pending_play_count == 0:
                        self._is_speaking = False
                        self._active_engine = "none"
                        self._idle_event.set()
                        should_emit_idle = True
                    else:
                        should_emit_idle = False
                if should_emit_idle:
                    self._reset_echo_guard()
                    self._emit_state(False, 0.0, "backend_tts")
                continue

            if item is None:
                break

            try:
                if not self._is_gen_valid(item.gen):
                    _close_stream()
                    continue

                with self._lock:
                    self._is_speaking = True
                    self._active_engine = item.engine_used
                    self._idle_event.clear()

                self._set_legacy_tts_flag(True)
                self._emit_state(True, 35.0, f"backend_tts:{item.engine_used}", force=True)

                if item.pcm is not None and item.pcm.size > 0:
                    if self._audio_writer is not None:
                        self._play_via_custom_writer(item)
                    else:
                        sd_stream = self._play_via_sounddevice(item, sd_stream)
                elif item.sapi_fallback_text:
                    _close_stream()
                    self._play_sapi_direct(
                        item.sapi_fallback_text,
                        item.speed,
                        item.volume,
                        item.gen,
                        configured_voice=item.configured_voice,
                    )

                last_item_end = time.monotonic()
            except Exception as err:
                logger.error(f"[TTS] Playback worker error: {err}")
                _close_stream()
            finally:
                should_close_stream = False
                with self._lock:
                    self._pending_play_count = max(0, self._pending_play_count - 1)
                    if not self._is_gen_valid(item.gen) or self._abort_event.is_set():
                        should_close_stream = True

                    # Check immediately if there's nothing else pending
                    nothing_pending = (
                        self._play_queue.empty()
                        and self._pending_play_count == 0
                        and self._pending_synth_count == 0
                        and self._active_stream_gen is None
                    )
                    if nothing_pending:
                        self._is_speaking = False
                        self._active_engine = "none"
                        self._idle_event.set()
                        should_close_stream = True
                    elif self._abort_event.is_set() and self._play_queue.empty():
                        self._is_speaking = False
                        self._active_engine = "none"
                        self._idle_event.set()
                        should_close_stream = True

                if should_close_stream:
                    _close_stream()
                if nothing_pending:
                    self._reset_echo_guard()
                    self._set_legacy_tts_flag(False)
                    self._emit_state(False, 0.0, "backend_tts", force=True)

        _close_stream()

    def _play_via_custom_writer(self, item: _PlayItem) -> None:
        pcm = item.pcm
        if pcm is None:
            return
        for start in range(0, pcm.size, BLOCK_SAMPLES):
            if not self._is_gen_valid(item.gen) or self._abort_event.is_set():
                return
            block = pcm[start : start + BLOCK_SAMPLES]
            rms = float(np.sqrt(np.mean(block * block))) if block.size > 0 else 0.0
            orb_level = min(100.0, max(8.0, rms * 320.0)) if rms > 0.004 else 8.0
            self._note_echo_guard(block, rms)
            self._emit_state(True, orb_level, f"backend_tts:{item.engine_used}")
            self._audio_writer(block, TARGET_SAMPLE_RATE)

    def _play_via_sounddevice(self, item: _PlayItem, sd_stream: Any) -> Any:
        pcm = item.pcm
        if pcm is None:
            return sd_stream

        import sounddevice as sd

        def _is_stream_usable(stream_obj: Any) -> bool:
            if stream_obj is None:
                return False
            if getattr(stream_obj, "closed", False) or getattr(stream_obj, "stopped", False):
                return False
            return bool(getattr(stream_obj, "active", True))

        if sd_stream is not None and not _is_stream_usable(sd_stream):
            try:
                sd_stream.close()
            except Exception:
                pass
            sd_stream = None

        if sd_stream is None:
            try:
                sd_stream = sd.OutputStream(
                    samplerate=TARGET_SAMPLE_RATE,
                    channels=1,
                    dtype="float32",
                    blocksize=BLOCK_SAMPLES,
                )
                sd_stream.start()
            except Exception as open_err:
                logger.warning(f"[TTS] Could not open PortAudio OutputStream: {open_err}")
                return None

        for start in range(0, pcm.size, BLOCK_SAMPLES):
            if not self._is_gen_valid(item.gen) or self._abort_event.is_set():
                # Fade-out trailing tiny buffer on interrupt to prevent speaker click
                fade_len = min(64, pcm.size - start)
                if fade_len > 4 and _is_stream_usable(sd_stream):
                    fade_tail = pcm[start : start + fade_len].copy() * np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
                    try:
                        sd_stream.write(fade_tail.reshape(-1, 1))
                    except Exception:
                        pass
                try:
                    sd_stream.abort()
                except Exception:
                    pass
                try:
                    sd_stream.close()
                except Exception:
                    pass
                return None

            block = pcm[start : start + BLOCK_SAMPLES]
            rms = float(np.sqrt(np.mean(block * block))) if block.size > 0 else 0.0
            orb_level = min(100.0, max(8.0, rms * 320.0)) if rms > 0.004 else 8.0
            self._note_echo_guard(block, rms)
            self._emit_state(True, orb_level, f"backend_tts:{item.engine_used}")
            try:
                if not _is_stream_usable(sd_stream):
                    raise RuntimeError("PortAudio OutputStream stopped/closed")
                sd_stream.write(block.reshape(-1, 1))
            except Exception as write_err:
                # Recover cleanly from stopped/stale PortAudio stream (-9983)
                try:
                    if sd_stream is not None:
                        sd_stream.close()
                except Exception:
                    pass
                sd_stream = None
                try:
                    sd_stream = sd.OutputStream(
                        samplerate=TARGET_SAMPLE_RATE,
                        channels=1,
                        dtype="float32",
                        blocksize=BLOCK_SAMPLES,
                    )
                    sd_stream.start()
                    sd_stream.write(block.reshape(-1, 1))
                except Exception as rec_err:
                    logger.warning(f"[TTS] PortAudio stream recovery failed ({write_err} -> {rec_err})")
                    try:
                        if sd_stream is not None:
                            sd_stream.close()
                    except Exception:
                        pass
                    return None

        return sd_stream

    def _play_sapi_direct(
        self,
        text: str,
        speed: float,
        volume: float,
        gen: int,
        configured_voice: Optional[str] = None,
    ) -> None:
        if not self._is_gen_valid(gen):
            return
        coinit_done = False
        try:
            try:
                import pythoncom
                pythoncom.CoInitialize()
                coinit_done = True
            except Exception:
                pass
            import pyttsx3

            engine = pyttsx3.init()
            configure_sapi5_voice(engine, configured_voice=configured_voice)
            engine.setProperty("rate", int(round(175 * speed)))
            engine.setProperty("volume", max(0.0, min(1.0, volume)))
            self._emit_state(True, 45.0, "backend_tts:pyttsx3", force=True)
            engine.say(text)
            engine.runAndWait()
        except Exception as err:
            logger.error(f"[TTS] SAPI5 direct playback failed: {err}")
        finally:
            if coinit_done:
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

    # ── EchoGuard & Overlay State Helpers ─────────────────────────────────

    @staticmethod
    def _note_echo_guard(block: np.ndarray, rms: float) -> None:
        try:
            from ai_assistant.voice.echo_guard import get_echo_guard
            get_echo_guard().note_output(block, TARGET_SAMPLE_RATE, level=rms)
        except Exception:
            pass

    @staticmethod
    def _reset_echo_guard() -> None:
        try:
            from ai_assistant.voice.echo_guard import reset_echo_guard
            reset_echo_guard()
        except Exception:
            pass

    @staticmethod
    def _set_legacy_tts_flag(active: bool) -> None:
        for mod_name in ("voice_service", "backend.voice_service"):
            mod = sys.modules.get(mod_name)
            if mod is not None and hasattr(mod, "set_tts_active"):
                try:
                    mod.set_tts_active(active)
                except Exception:
                    pass
                break

    def _emit_state(self, speaking: bool, level: float, source: str, force: bool = False) -> None:
        cb = self._state_callback
        if cb is None:
            return
        now = time.monotonic()
        if not force and speaking and (now - self._last_telemetry_emit) < 0.06:
            return
        self._last_telemetry_emit = now
        try:
            cb(bool(speaking), float(level), str(source))
        except Exception:
            pass


_tts_service_lock = threading.Lock()
_tts_service_instance: Optional[TTSOutputService] = None


def get_tts_service() -> TTSOutputService:
    """Return the global singleton desktop TTS output service."""
    global _tts_service_instance
    if _tts_service_instance is None:
        with _tts_service_lock:
            if _tts_service_instance is None:
                _tts_service_instance = TTSOutputService()
    return _tts_service_instance
