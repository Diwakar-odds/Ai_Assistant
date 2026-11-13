#!/usr/bin/env python3
"""
Pulsar AI Assistant - Companion Voice Subsystem
================================================
Always-on lightweight voice listener running in the companion process:
- Low-CPU energy-VAD + pre-roll ring buffer for zero-clipping wake detection
- Unicode-safe English & Hindi wake word matching ("hey pulsar", "pulsar", "पल्सर")
- Streaming live RMS audio level callbacks (0-100) for 4D Orb particle vibration
- Automatic pause during WebUI mic capture or TTS playback (zero echo/contention)
- Speech recognition via AdvancedSpeechRecognizer (Whisper) with Google STT fallback
"""

import collections
import inspect
import io
import os
import re
import sys
import threading
import time
import unicodedata
import wave
from pathlib import Path
from typing import Callable, List, Optional, Tuple

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import numpy as np

if getattr(sys, 'frozen', False):
    project_root = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)).resolve()
else:
    project_root = Path(__file__).resolve().parent.parent
for _sp in (
    str(project_root),
    str(project_root / "backend"),
    str(project_root / "core_ai" / "src"),
    str(project_root / "shared"),
    str(project_root / "desktop"),
):
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from ai_assistant.core.local_command_normalizer import (
    DEFAULT_WAKE_PHRASES,
    _IMPOSSIBLE_DEVANAGARI_NUKTA_RE,
    ensure_project_ffmpeg_in_path,
    get_merged_wake_phrases,
    is_barge_in_stop_command,
    is_noise_fragment,
    match_and_strip_wake_phrase,
)

ensure_project_ffmpeg_in_path(project_root)

from utils.logging_config import get_logger

logger = get_logger(__name__, log_category="app")


_REPETITION_HALLUCINATION_RE = re.compile(
    r"(?:^|\s)([\w\u0900-\u097F]+)(?:[,\s]+\1){3,}(?=$|\s|[.,!?;।])",
    re.IGNORECASE,
)


def filter_whisper_segments(
    segments,
    max_no_speech_prob: float = 0.60,
    min_avg_logprob: float = -1.10,
    max_compression_ratio: float = 2.20,
) -> str:
    """
    Filter out Whisper noise/repetition/nukta hallucinations using per-segment quality
    metrics (`no_speech_prob`, `avg_logprob`, `compression_ratio`) and script sanity.
    """
    kept: List[str] = []
    for seg in segments:
        txt = str(getattr(seg, "text", "") or "").strip()
        if not txt:
            continue
        if _IMPOSSIBLE_DEVANAGARI_NUKTA_RE.search(txt):
            continue
        if _REPETITION_HALLUCINATION_RE.search(txt):
            continue
        no_speech = getattr(seg, "no_speech_prob", None)
        if no_speech is not None and float(no_speech) > max_no_speech_prob:
            continue
        avg_lp = getattr(seg, "avg_logprob", None)
        if avg_lp is not None and float(avg_lp) < min_avg_logprob:
            continue
        comp_ratio = getattr(seg, "compression_ratio", None)
        if comp_ratio is not None and float(comp_ratio) > max_compression_ratio:
            continue
        kept.append(txt)
    return " ".join(kept).strip()


class CompanionVoiceListener:
    """Always-on voice capture and wake-word listener for the floating companion."""

    SAMPLE_RATE = 16000
    BLOCK_SIZE = 800  # 50 ms at 16 kHz

    def __init__(
        self,
        on_wake: Optional[Callable] = None,
        on_wake_ack: Optional[Callable[[Optional[str]], None]] = None,
        on_command: Optional[Callable[[str], None]] = None,
        on_partial: Optional[Callable[[str], None]] = None,
        on_audio_level: Optional[Callable[[float], None]] = None,
        on_wake_ignored: Optional[Callable[[], None]] = None,
        is_paused_fn: Optional[Callable[[], bool]] = None,
        is_capture_aborted_fn: Optional[Callable[[], bool]] = None,
        get_wake_phrases_fn: Optional[Callable[[], List[str]]] = None,
        is_tts_speaking_fn: Optional[Callable[[], bool]] = None,
        on_barge_in: Optional[Callable[[str], None]] = None,
    ):
        self.on_wake = on_wake
        self.on_wake_ack = on_wake_ack
        self.on_command = on_command
        self.on_partial = on_partial
        self.on_audio_level = on_audio_level
        self.on_wake_ignored = on_wake_ignored
        self.is_paused_fn = is_paused_fn
        self.is_capture_aborted_fn = is_capture_aborted_fn
        self.get_wake_phrases_fn = get_wake_phrases_fn
        self.is_tts_speaking_fn = is_tts_speaking_fn
        self.on_barge_in = on_barge_in

        self.is_running = False
        self.is_listening_for_command = False
        self._manual_listen_event = threading.Event()
        self._lock = threading.Lock()

        self._fast_whisper = None
        self._fw_lock = threading.Lock()
        self.speech_recognizer = None
        self._init_thread = threading.Thread(target=self._init_models, daemon=True)
        self._init_thread.start()

    def _get_live_stt_settings(self) -> Tuple[str, Optional[str], bool, float]:
        """Read canonical STT settings (`model`, `language`, `noise_reduction`, `sensitivity`)."""
        model_size = "small"
        lang_short: Optional[str] = "hi"
        noise_reduction = True
        sensitivity = 0.8
        try:
            from settings_manager import get_stt_config, get_stt_model
            cfg = get_stt_config() or {}
            model_size = str(get_stt_model() or "small").strip().lower() or "small"
            raw_lang = str(cfg.get("language") or "hi-IN").strip().lower()
            if raw_lang in ("", "auto"):
                lang_short = None
            elif "-" in raw_lang:
                lang_short = raw_lang.split("-", 1)[0] or None
            else:
                lang_short = raw_lang
            if "noise_reduction" in cfg:
                noise_reduction = bool(cfg.get("noise_reduction", True))
            if cfg.get("sensitivity") is not None:
                sensitivity = max(0.1, min(1.0, float(cfg.get("sensitivity", 0.8))))
        except Exception:
            pass
        return model_size, lang_short, noise_reduction, sensitivity

    def _vad_threshold(self, noise_floor: float, tts_now: bool, sensitivity: float = 0.8) -> float:
        """Compute adaptive RMS threshold honoring user STT sensitivity setting."""
        if tts_now:
            return max(0.022, noise_floor * 2.8)
        sens = max(0.1, min(1.0, float(sensitivity)))
        mult = max(1.45, min(2.6, 2.0 - (sens - 0.5) * 1.15))
        floor_min = max(0.0035, min(0.012, 0.007 - (sens - 0.5) * 0.006))
        return max(floor_min, noise_floor * mult)

    def _preprocess_pcm(self, pcm_f32: np.ndarray, noise_reduction: bool = True) -> np.ndarray:
        """Apply DC offset removal, >80 Hz high-pass filter, soft noise gate, and safe gain leveling."""
        if pcm_f32.size == 0 or not noise_reduction:
            return pcm_f32
        try:
            sig = pcm_f32 - float(np.mean(pcm_f32))
            if sig.size >= 320:
                spec = np.fft.rfft(sig)
                freqs = np.fft.rfftfreq(sig.size, d=1.0 / float(self.SAMPLE_RATE))
                hp_gain = np.clip((freqs - 55.0) / 45.0, 0.0, 1.0).astype(np.float32)
                sig = np.fft.irfft(spec * hp_gain, n=sig.size).astype(np.float32)

            hop = 320  # 20 ms at 16 kHz
            n_frames = sig.size // hop
            if n_frames >= 5:
                trimmed = sig[: n_frames * hop].reshape(n_frames, hop)
                frame_rms = np.sqrt(np.mean(trimmed * trimmed, axis=1) + 1e-12)
                noise_est = float(np.percentile(frame_rms, 20))
                speech_peak_rms = float(np.max(frame_rms))
                if noise_est > 1e-5 and speech_peak_rms > noise_est * 2.5:
                    soft_thr = noise_est * 1.45
                    gains = np.where(
                        frame_rms >= soft_thr,
                        1.0,
                        np.clip(0.30 + 0.70 * (frame_rms / max(soft_thr, 1e-6)), 0.30, 1.0),
                    ).astype(np.float32)
                    sample_gains = np.repeat(gains, hop)
                    if sig.size > sample_gains.size:
                        sample_gains = np.pad(sample_gains, (0, sig.size - sample_gains.size), mode="edge")
                    sig = sig * sample_gains

            peak = float(np.max(np.abs(sig))) if sig.size > 0 else 0.0
            if 0.015 < peak < 0.35:
                gain = min(4.0, 0.45 / peak)
                sig = np.clip(sig * gain, -1.0, 1.0).astype(np.float32, copy=False)
            return sig.astype(np.float32, copy=False)
        except Exception:
            return pcm_f32

    def _init_models(self):
        """Asynchronously warm up configured local faster-whisper model (zero ffmpeg)."""
        cfg_model, _, _, _ = self._get_live_stt_settings()
        candidates = tuple(dict.fromkeys([c for c in (cfg_model, "small", "base") if c]))
        try:
            from faster_whisper import WhisperModel

            for model_size in candidates:
                try:
                    self._fast_whisper = WhisperModel(
                        model_size,
                        device="cpu",
                        compute_type="int8",
                        local_files_only=True,
                    )
                    logger.info(f"Companion voice: faster-whisper ({model_size}, int8) loaded")
                    return
                except Exception as inner_e:
                    logger.debug(f"faster-whisper ({model_size}) unavailable offline: {inner_e}")
        except Exception as e:
            logger.debug(f"faster-whisper import unavailable: {e}")

        try:
            from ai_assistant.voice.advanced_speech_recognizer import AdvancedSpeechRecognizer

            self.speech_recognizer = AdvancedSpeechRecognizer()
            logger.info("Companion voice: AdvancedSpeechRecognizer loaded")
        except Exception as e:
            logger.warning(f"Could not load AdvancedSpeechRecognizer: {e}")

    def _get_wake_phrases(self) -> List[str]:
        """Return deduplicated wake phrases ordered longest-first."""
        extra: List[str] = []
        if self.get_wake_phrases_fn:
            try:
                extra.extend(self.get_wake_phrases_fn() or [])
            except Exception:
                pass
        return get_merged_wake_phrases(extra_phrases=extra)

    def _match_wake_phrase(self, transcript: str) -> Tuple[Optional[str], str]:
        """Match wake word anywhere in utterance and strip leading wake phrase."""
        extra: List[str] = []
        if self.get_wake_phrases_fn:
            try:
                extra.extend(self.get_wake_phrases_fn() or [])
            except Exception:
                pass
        return match_and_strip_wake_phrase(transcript, extra_phrases=extra)

    def _fire_on_wake(self, wake_word: Optional[str] = None):
        if not self.on_wake:
            return
        try:
            sig = inspect.signature(self.on_wake)
            if len(sig.parameters) >= 1:
                self.on_wake(wake_word)
            else:
                self.on_wake()
        except Exception:
            try:
                self.on_wake()
            except Exception:
                pass

    def _emit_level(self, rms: float, noise_floor: float):
        if not self.on_audio_level:
            return
        scaled = max(0.0, (rms - max(0.008, noise_floor * 1.15)) * 1150.0)
        level = float(min(100.0, max(0.0, scaled)))
        try:
            self.on_audio_level(level)
        except Exception:
            pass

    def start(self):
        """Start continuous background wake-word listener loop."""
        if self.is_running:
            return
        self.is_running = True
        threading.Thread(target=self._loop, daemon=True, name="CompanionVoiceLoop").start()
        logger.info("Companion Voice Listener started")

    def stop(self):
        self.is_running = False
        self._manual_listen_event.set()

    def trigger_manual_listen(self):
        """Trigger immediate command listening without waiting for wake word."""
        self._manual_listen_event.set()

    def _is_paused(self) -> bool:
        if not self.is_paused_fn:
            return False
        try:
            return bool(self.is_paused_fn())
        except Exception:
            return False

    def _is_capture_aborted(self) -> bool:
        fn = self.is_capture_aborted_fn
        if fn is None:
            return False
        try:
            return bool(fn())
        except Exception:
            return False

    def _is_tts_speaking(self) -> bool:
        if not self.is_tts_speaking_fn:
            return False
        try:
            return bool(self.is_tts_speaking_fn())
        except Exception:
            return False

    def _fire_on_barge_in(self, transcript: str = ""):
        if not self.on_barge_in:
            return
        try:
            sig = inspect.signature(self.on_barge_in)
            if len(sig.parameters) >= 1:
                self.on_barge_in(transcript)
            else:
                self.on_barge_in()
        except Exception:
            try:
                self.on_barge_in(transcript)
            except Exception:
                pass

    def _loop(self):
        """Energy-VAD passive wake & active TTS barge-in loop using sounddevice."""
        time.sleep(1.5)
        try:
            import sounddevice as sd
        except Exception as e:
            logger.warning(f"sounddevice unavailable for background wake listener: {e}")
            while self.is_running:
                time.sleep(0.5)
            return

        pre_roll = collections.deque(maxlen=12)  # ~600 ms pre-roll
        noise_floor = 0.0025

        while self.is_running:
            if self._is_paused():
                pre_roll.clear()
                time.sleep(0.12)
                continue

            if self._manual_listen_event.is_set():
                self._manual_listen_event.clear()
                self._capture_and_dispatch_command(sd, pre_roll=None, noise_floor=noise_floor)
                continue

            try:
                with sd.InputStream(
                    samplerate=self.SAMPLE_RATE,
                    channels=1,
                    dtype="float32",
                    blocksize=self.BLOCK_SIZE,
                ) as stream:
                    speech_frames: List[np.ndarray] = []
                    speaking = False
                    silent_blocks = 0
                    active_speech_blocks = 0
                    tts_during_utterance = False

                    while self.is_running:
                        if self._is_paused():
                            pre_roll.clear()
                            speech_frames.clear()
                            speaking = False
                            active_speech_blocks = 0
                            tts_during_utterance = False
                            break

                        if self._manual_listen_event.is_set():
                            self._manual_listen_event.clear()
                            stream.stop()
                            stream.close()
                            self._capture_and_dispatch_command(sd, pre_roll=None, noise_floor=noise_floor)
                            break

                        block, _overflow = stream.read(self.BLOCK_SIZE)
                        mono = block[:, 0].copy()
                        rms = float(np.sqrt(np.mean(mono * mono)))
                        tts_now = self._is_tts_speaking()
                        _, _, _, stt_sens = self._get_live_stt_settings()
                        threshold = self._vad_threshold(noise_floor, tts_now=tts_now, sensitivity=stt_sens)

                        if not speaking:
                            pre_roll.append(mono)
                            # Do not let speaker TTS output corrupt ambient room noise_floor
                            if not tts_now:
                                if rms < noise_floor:
                                    noise_floor = max(0.004, 0.90 * noise_floor + 0.10 * rms)
                                else:
                                    noise_floor = min(0.014, 0.97 * noise_floor + 0.03 * min(rms, 0.020))
                            if rms > threshold:
                                speaking = True
                                silent_blocks = 0
                                active_speech_blocks = 1
                                tts_during_utterance = tts_now
                                speech_frames = list(pre_roll)
                        else:
                            speech_frames.append(mono)
                            tts_during_utterance = tts_during_utterance or tts_now
                            if rms > threshold * 0.80:
                                silent_blocks = 0
                                active_speech_blocks += 1
                            else:
                                silent_blocks += 1

                            duration_s = len(speech_frames) * (self.BLOCK_SIZE / self.SAMPLE_RATE)
                            silence_limit = 5 if tts_during_utterance else 7
                            max_dur = 2.5 if tts_during_utterance else 4.0
                            if silent_blocks >= silence_limit or duration_s >= max_dur:
                                stream.stop()
                                stream.close()
                                # Require >=3 active blocks (~150ms speech) to avoid single key/desk clicks
                                if duration_s >= 0.25 and active_speech_blocks >= 3:
                                    pcm = np.concatenate(speech_frames)
                                    if tts_during_utterance:
                                        self._process_barge_in_candidate(sd, pcm, noise_floor)
                                    else:
                                        self._process_wake_candidate(sd, pcm, noise_floor)
                                speech_frames.clear()
                                pre_roll.clear()
                                speaking = False
                                active_speech_blocks = 0
                                tts_during_utterance = False
                                break
            except Exception as e:
                logger.debug(f"Background mic listener cycle interrupted: {e}")
                time.sleep(0.8)

    def _process_barge_in_candidate(self, sd_module, pcm: np.ndarray, noise_floor: float):
        """
        Process microphone speech heard during active TTS playback.
        Only interrupts for explicit stop phrases ('chup ho jao', 'stop', 'bas karo')
        or multi-word wake phrases ('hey pulsar ...'); ignores speaker echo.
        """
        transcript = self._transcribe_pcm(pcm)
        if not transcript:
            return

        if is_barge_in_stop_command(transcript):
            logger.info(f"Voice barge-in stop detected during speech: '{transcript}'")
            self._fire_on_barge_in(transcript)
            return

        matched_wake, inline_cmd = self._match_wake_phrase(transcript)
        # During TTS playback, require a multi-word wake phrase (e.g. 'hey pulsar', not bare 'pulsar')
        # so Pulsar speaking its own name over speakers never self-interrupts.
        if not matched_wake or " " not in matched_wake.strip():
            return

        logger.info(f"Voice barge-in wake '{matched_wake}' detected during speech: '{transcript}'")
        self._fire_on_barge_in(transcript)
        time.sleep(0.15)

        if inline_cmd:
            if is_barge_in_stop_command(inline_cmd):
                return
            if is_noise_fragment(inline_cmd):
                logger.info(f"Dropped inline wake noise fragment: '{inline_cmd}'")
                return
            if self.on_command:
                self.on_command(inline_cmd)
            return

        self._fire_on_wake(matched_wake)
        self._capture_and_dispatch_command(
            sd_module,
            pre_roll=None,
            noise_floor=noise_floor,
            timeout_s=8.5,
            announce_wake=False,
        )

    def _process_wake_candidate(self, sd_module, pcm: np.ndarray, noise_floor: float):
        """Transcribe wake-word candidate quietly while keeping overlay idle unless matched."""
        if self._is_paused():
            return
        transcript = self._transcribe_pcm(pcm)
        if not transcript:
            return
        logger.debug(f"[CompanionVoice] Candidate heard: '{transcript}'")
        if self._is_paused():
            return

        if self._is_tts_speaking():
            if is_barge_in_stop_command(transcript):
                logger.info(f"Voice barge-in stop detected: '{transcript}'")
                self._fire_on_barge_in(transcript)
            return

        matched_wake, inline_cmd = self._match_wake_phrase(transcript)
        if not matched_wake:
            return

        logger.info(f"Wake word '{matched_wake}' detected in: '{transcript}'")
        self._fire_on_wake(matched_wake)

        if inline_cmd:
            if is_barge_in_stop_command(inline_cmd):
                self._fire_on_barge_in(inline_cmd)
                if self.on_wake_ignored:
                    self.on_wake_ignored()
                return
            if is_noise_fragment(inline_cmd):
                logger.info(f"Dropped inline wake noise fragment: '{inline_cmd}'")
                if self.on_wake_ignored:
                    self.on_wake_ignored()
                return
            logger.info(f"Executing inline wake command: '{inline_cmd}'")
            if self.on_command:
                self.on_command(inline_cmd)
            return

        # Wake word only: fire non-blocking acknowledgment in background so mic opens immediately
        if self.on_wake_ack:
            try:
                threading.Thread(
                    target=self.on_wake_ack,
                    args=(matched_wake,),
                    daemon=True,
                ).start()
            except Exception as e:
                logger.debug(f"Wake acknowledgment thread note: {e}")

        self._capture_and_dispatch_command(
            sd_module,
            pre_roll=None,
            noise_floor=noise_floor,
            timeout_s=6.0,
            announce_wake=False,
        )

    def _capture_and_dispatch_command(
        self,
        sd_module,
        pre_roll: Optional[collections.deque] = None,
        noise_floor: float = 0.010,
        timeout_s: float = 8.5,
        announce_wake: bool = True,
    ):
        with self._lock:
            if self.is_listening_for_command:
                return
            self.is_listening_for_command = True

        try:
            if announce_wake:
                self._fire_on_wake(None)
            if self.on_partial:
                try:
                    self.on_partial("Listening...")
                except Exception:
                    pass

            pcm = self._record_with_levels(sd_module, timeout_s=timeout_s, noise_floor=noise_floor)
            if self.on_audio_level:
                self.on_audio_level(0.0)

            if pcm is None or len(pcm) == 0:
                if self.on_wake_ignored:
                    self.on_wake_ignored()
                return

            if self.on_partial:
                try:
                    self.on_partial("Transcribing...")
                except Exception:
                    pass

            cmd = self._transcribe_pcm(pcm, strict=False)
            if cmd and cmd.strip():
                if is_barge_in_stop_command(cmd):
                    self._fire_on_barge_in(cmd)
                    if self.on_wake_ignored:
                        self.on_wake_ignored()
                    return
                matched_wake, cleaned = self._match_wake_phrase(cmd)
                if matched_wake and not cleaned:
                    logger.info("Wake phrase repeated without follow-up command; ignoring.")
                    if self.on_wake_ignored:
                        self.on_wake_ignored()
                    return
                final_cmd = cleaned if matched_wake else cmd.strip()
                if is_noise_fragment(final_cmd):
                    logger.info(f"Companion dropped noise/hallucination fragment: '{final_cmd}'")
                    if self.on_wake_ignored:
                        self.on_wake_ignored()
                    return
                logger.info(f"Companion captured command: '{final_cmd}'")
                if self.on_command:
                    self.on_command(final_cmd)
            else:
                if self.on_wake_ignored:
                    self.on_wake_ignored()
        finally:
            self.is_listening_for_command = False
            if self.on_audio_level:
                try:
                    self.on_audio_level(0.0)
                except Exception:
                    pass

    def _record_with_levels(
        self,
        sd_module,
        timeout_s: float = 6.0,
        noise_floor: float = 0.010,
        max_utterance_s: float = 14.0,
    ) -> Optional[np.ndarray]:
        """Record active voice command while streaming live RMS amplitude (0-100)."""
        # Allow brief trailing wake-ack audio tail without stalling mic start
        tts_wait_deadline = time.time() + 0.45
        while self.is_running and self._is_tts_speaking() and time.time() < tts_wait_deadline:
            if self._is_capture_aborted():
                return None
            time.sleep(0.04)

        frames: List[np.ndarray] = []
        speech_blocks = 0
        silent_blocks = 0
        speech_start_idx: Optional[int] = None
        speech_start_time: Optional[float] = None
        start_time = time.time()
        aborted = False
        _, _, _, stt_sens = self._get_live_stt_settings()

        try:
            with sd_module.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=self.BLOCK_SIZE,
            ) as stream:
                while self.is_running:
                    now = time.time()
                    if speech_blocks < 2 and (now - start_time) >= timeout_s:
                        break
                    if speech_start_time is not None and (now - speech_start_time) >= max_utterance_s:
                        break
                    if self._is_capture_aborted():
                        aborted = True
                        break

                    block, _overflow = stream.read(self.BLOCK_SIZE)
                    mono = block[:, 0].copy()
                    frames.append(mono)

                    rms = float(np.sqrt(np.mean(mono * mono)))
                    self._emit_level(rms, noise_floor)
                    threshold = self._vad_threshold(noise_floor, tts_now=False, sensitivity=stt_sens)

                    if rms > threshold:
                        if speech_start_idx is None:
                            speech_start_idx = len(frames) - 1
                        speech_blocks += 1
                        if speech_blocks >= 2 and speech_start_time is None:
                            speech_start_time = time.time()
                        silent_blocks = 0
                    elif speech_blocks >= 2:
                        silent_blocks += 1
                        # ~800ms trailing silence ends command utterance cleanly without clipping
                        if silent_blocks >= 8:
                            break
        except Exception as e:
            logger.error(f"Active command recording error: {e}")
            return None

        if aborted and speech_blocks < 2:
            logger.info("Companion post-wake capture aborted before speech started.")
            return None
        if speech_blocks < 2 or not frames:
            logger.info("Companion post-wake capture timed out with no speech detected.")
            return None

        if speech_start_idx is not None and speech_start_idx > 6:
            frames = frames[speech_start_idx - 6 :]
        return np.concatenate(frames)

    def _pcm_to_wav_bytes(self, pcm: np.ndarray) -> bytes:
        pcm_clamped = np.clip(pcm, -1.0, 1.0)
        int16_data = (pcm_clamped * 32767.0).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(int16_data.tobytes())
        return buf.getvalue()

    def _transcribe_pcm(self, pcm: np.ndarray, strict: bool = True) -> Optional[str]:
        """Transcribe float32 PCM buffer using quality-filtered faster-whisper, AdvancedSpeechRecognizer, then Google STT."""
        pcm_f32 = np.asarray(pcm, dtype=np.float32).reshape(-1)
        if pcm_f32.size < int(self.SAMPLE_RATE * 0.25):
            return None
        peak = float(np.max(np.abs(pcm_f32)))
        rms = float(np.sqrt(np.mean(pcm_f32 * pcm_f32)))
        if peak < 0.006 or rms < 0.0012:
            return None

        _, lang_short, noise_reduction, _ = self._get_live_stt_settings()
        proc_pcm = self._preprocess_pcm(pcm_f32, noise_reduction=noise_reduction)

        no_speech_thr = 0.60 if strict else 0.78
        log_prob_thr = -1.05 if strict else -1.55
        min_seg_lp = -1.10 if strict else -1.55
        if lang_short == "en":
            init_prompt = (
                "Hey Pulsar, OK Pulsar. Open WhatsApp, Chrome, YouTube Music, VS Code, "
                "take a screenshot, what should I do?"
            )
        else:
            init_prompt = (
                "Hey Pulsar, OK Pulsar, नमस्ते! WhatsApp, YouTube Music, Chrome, "
                "VS Code खोलो, स्क्रीनशॉट लो, बताओ क्या करना है?"
            )

        try:
            from ai_assistant.voice.vocabulary_registry import get_vocabulary_registry
            kw = get_vocabulary_registry().get_whisper_prompt_keywords()
            if kw:
                init_prompt = f"{init_prompt} ({kw})"
        except Exception:
            pass

        if self._fast_whisper is not None:
            try:
                with self._fw_lock:
                    text = ""
                    try:
                        segments, _info = self._fast_whisper.transcribe(
                            proc_pcm,
                            beam_size=1,
                            language=lang_short,
                            initial_prompt=init_prompt,
                            vad_filter=True,
                            vad_parameters=dict(min_silence_duration_ms=200, min_speech_duration_ms=80),
                            condition_on_previous_text=False,
                            without_timestamps=True,
                            no_speech_threshold=no_speech_thr,
                            log_prob_threshold=log_prob_thr,
                            compression_ratio_threshold=2.2,
                        )
                        text = filter_whisper_segments(
                            segments,
                            max_no_speech_prob=no_speech_thr,
                            min_avg_logprob=min_seg_lp,
                        )
                    except Exception as e:
                        logger.debug(f"Fast-whisper transcribe error: {e}")
                        text = ""
                if text:
                    try:
                        from ai_assistant.voice.vocabulary_registry import get_vocabulary_registry
                        text = get_vocabulary_registry().normalize_stt_transcript(text)
                    except Exception:
                        pass
                    return text
            except Exception as e:
                logger.debug(f"faster-whisper wake transcribe note: {e}")

        if self.speech_recognizer:
            try:
                asr_lang = "en-IN" if lang_short == "en" else "hinglish"
                text, _conf, _model = self.speech_recognizer.recognize(
                    {"raw": proc_pcm, "sampling_rate": self.SAMPLE_RATE},
                    language=asr_lang,
                )
                if text and text.strip():
                    cleaned = text.strip()
                    try:
                        from ai_assistant.voice.vocabulary_registry import get_vocabulary_registry
                        cleaned = get_vocabulary_registry().normalize_stt_transcript(cleaned)
                    except Exception:
                        pass
                    return cleaned
            except Exception as e:
                logger.debug(f"Local Whisper failed, trying Google STT: {e}")

        try:
            import speech_recognition as sr

            r = sr.Recognizer()
            int16_bytes = (np.clip(proc_pcm, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
            audio = sr.AudioData(int16_bytes, self.SAMPLE_RATE, 2)
            google_langs = ("en-IN", "hi-IN", None) if lang_short == "en" else ("hi-IN", "en-IN", None)
            for lang in google_langs:
                try:
                    text = r.recognize_google(audio, language=lang) if lang else r.recognize_google(audio)
                    if text and text.strip():
                        cleaned = text.strip()
                        try:
                            from ai_assistant.voice.vocabulary_registry import get_vocabulary_registry
                            cleaned = get_vocabulary_registry().normalize_stt_transcript(cleaned)
                        except Exception:
                            pass
                        return cleaned
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Google STT fallback failed: {e}")

        return None
