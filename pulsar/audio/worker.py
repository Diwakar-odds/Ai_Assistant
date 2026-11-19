"""
Pulsar Audio Worker - Dedicated Audio & Wake Word Subsystem

The SINGLE OWNER of the microphone in the entire architecture:
- 16 kHz shared-mode WASAPI capture via sounddevice.
- Continuous real-time RMS audio level streaming to 4D Orb (30 Hz throttle).
- Offline speech detection & wake word recognition ("Hey Pulsar", "Pulsar").
- Direct integration with STT (Faster-Whisper), Agent Brain, and Neural TTS.
"""

import io
import os
import sys
import wave
import time
import logging
import threading
from typing import Optional, List, Callable
from collections import deque
import numpy as np

# Ensure repository root is on sys.path
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
for _p in (str(REPO_ROOT), str(REPO_ROOT / "backend"), str(REPO_ROOT / "core_ai")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from pulsar.audio.mic_stream import MicrophoneStream
from pulsar.core.orb_state import set_orb_state, get_orb_state

logger = logging.getLogger("pulsar.audio.worker")

SAMPLE_RATE = 16000
ENERGY_THRESHOLD = 0.045  # Normalized RMS speech threshold
SILENCE_DURATION_SEC = 0.85
MAX_COMMAND_DURATION_SEC = 12.0


class AudioWorker:
    """Dedicated background audio worker and wake word listener."""

    def __init__(
        self,
        wake_words: Optional[List[str]] = None,
        on_wake: Optional[Callable[[str], None]] = None,
        on_command: Optional[Callable[[str], None]] = None,
    ):
        self.mic = MicrophoneStream(sample_rate=SAMPLE_RATE)
        self.wake_words = wake_words or ["hey pulsar", "pulsar", "ok pulsar", "hey assistant"]
        self.on_wake = on_wake
        self.on_command = on_command

        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Pre-roll ring buffer (~0.8s = 40 blocks of 320 samples / 20ms at 16kHz)
        self._preroll_buffer = deque(maxlen=40)
        self._tts_speaking = False
        self._tts_ended_at = 0.0

        # STT instance (lazy loaded)
        self._stt_recognizer = None

    def get_metrics(self) -> dict:
        """Exposes audio stream metrics (overruns, queue depth, device) for Core /health."""
        m = self.mic.get_metrics()
        m["worker_running"] = self._is_running
        m["process_pid"] = os.getpid()
        m["tts_echo_gated"] = self._is_echo_gated()
        return m

    def _is_echo_gated(self) -> bool:
        """Returns True while TTS is speaking or within 450ms echo cooldown."""
        if self._tts_speaking:
            return True
        if (time.time() - self._tts_ended_at) < 0.45:
            return True
        return False

    def _get_stt(self):
        """Lazy load STT engine."""
        if self._stt_recognizer is None:
            try:
                from core_ai.voice.advanced_speech_recognizer import AdvancedSpeechRecognizer
                self._stt_recognizer = AdvancedSpeechRecognizer()
                logger.info("[AudioWorker] AdvancedSpeechRecognizer (Faster-Whisper) loaded")
            except Exception as e:
                logger.warning(f"[AudioWorker] STT load note: {e}")
        return self._stt_recognizer

    def start(self) -> bool:
        """Starts the microphone and background processing loop."""
        with self._lock:
            if self._is_running:
                return True

            if not self.mic.start():
                logger.error("[AudioWorker] Could not open microphone.")
                return False

            self._is_running = True
            self._thread = threading.Thread(
                target=self._processing_loop,
                name="PulsarAudioWorkerLoop",
                daemon=True,
            )
            self._thread.start()
            logger.info("[AudioWorker] Dedicated Audio Worker started.")
            return True

    def stop(self):
        """Stops the audio worker and releases microphone hardware."""
        with self._lock:
            self._is_running = False
            self.mic.stop()
            set_orb_state(state="idle", level=0.0, force=True)
            logger.info("[AudioWorker] Audio Worker stopped.")

    def _processing_loop(self):
        """Main audio processing and wake detection loop with echo gate & unplug recovery."""
        # Elevate thread priority to ABOVE_NORMAL on Windows so audio never drops under LLM load
        if sys.platform == "win32":
            try:
                import ctypes
                k32 = ctypes.windll.kernel32
                THREAD_PRIORITY_ABOVE_NORMAL = 1
                k32.SetThreadPriority(k32.GetCurrentThread(), THREAD_PRIORITY_ABOVE_NORMAL)
            except Exception:
                pass

        logger.info("[AudioWorker] Listening for wake words: %s", self.wake_words)

        in_speech = False
        speech_frames = []
        speech_start_time = 0.0
        silence_start_time = 0.0
        last_level_emit = 0.0
        last_frame_time = time.time()

        while self._is_running:
            frame_data = self.mic.read_frame(timeout=0.1)
            now = time.time()
            if not frame_data:
                # Device unplug / stream stall recovery
                if (now - last_frame_time) >= 4.0 and self._is_running:
                    logger.warning("[AudioWorker] No audio frames for 4s (device unplugged?). Retrying mic...")
                    self.mic.stop()
                    time.sleep(1.0)
                    if self._is_running:
                        self.mic.start()
                    last_frame_time = time.time()
                continue

            last_frame_time = now
            pcm, level = frame_data

            # 1. Stream live RMS level to 4D Orb at 30 Hz throttle
            if now - last_level_emit >= (1.0 / 30.0):
                set_orb_state(level=level)
                last_level_emit = now

            # 2. Echo gate while TTS is playing (raises threshold 3.5x to avoid self-trigger)
            eff_threshold = (ENERGY_THRESHOLD * 3.5) if self._is_echo_gated() else ENERGY_THRESHOLD
            is_voiced = level >= eff_threshold

            if not in_speech:
                self._preroll_buffer.append(pcm)
                if is_voiced and not self._is_echo_gated():
                    # User started speaking!
                    in_speech = True
                    speech_start_time = now
                    silence_start_time = 0.0
                    speech_frames = list(self._preroll_buffer)
                    speech_frames.append(pcm)
            else:
                speech_frames.append(pcm)

                # Track silence
                if not is_voiced:
                    if silence_start_time == 0.0:
                        silence_start_time = now
                    elif now - silence_start_time >= SILENCE_DURATION_SEC:
                        # End of speech detected! Process buffered audio.
                        in_speech = False
                        self._process_utterance(speech_frames)
                        speech_frames = []
                else:
                    silence_start_time = 0.0

                # Max duration safety cutoff
                if now - speech_start_time >= MAX_COMMAND_DURATION_SEC:
                    in_speech = False
                    self._process_utterance(speech_frames)
                    speech_frames = []

    def _process_utterance(self, frames: List[bytes]):
        """Transcribes buffered utterance and routes wake word or command."""
        if not frames or len(frames) < 8:
            return

        total_bytes = b"".join(frames)
        duration_sec = len(total_bytes) / (SAMPLE_RATE * 2)
        if duration_sec < 0.4:
            return  # Too short to be a valid command

        logger.debug(f"[AudioWorker] Processing utterance: {duration_sec:.2f}s ({len(total_bytes)} bytes)")

        # Create in-memory 16kHz WAV
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(total_bytes)
        wav_bytes = wav_io.getvalue()

        # Transcribe with STT
        stt = self._get_stt()
        text = ""
        if stt:
            try:
                res = stt.transcribe_audio_data(wav_bytes)
                if isinstance(res, dict):
                    text = res.get("text", "").strip()
                elif isinstance(res, str):
                    text = res.strip()
            except Exception as e:
                logger.debug(f"[AudioWorker] STT error: {e}")

        if not text:
            return

        logger.info(f"[AudioWorker] Transcribed speech: '{text}'")
        text_lower = text.lower()

        # Check for wake words
        wake_matched = None
        for ww in self.wake_words:
            if ww in text_lower:
                wake_matched = ww
                break

        if wake_matched:
            logger.info(f"[AudioWorker] 🎯 Wake word '{wake_matched}' detected in '{text}'!")
            set_orb_state(state="listening", force=True)

            if self.on_wake:
                try:
                    self.on_wake(wake_matched)
                except Exception:
                    pass

            # Extract command portion after wake word
            try:
                from core_ai.core.local_command_normalizer import match_and_strip_wake_phrase
                cmd_text, _ = match_and_strip_wake_phrase(text)
            except Exception:
                cmd_text = text_lower.replace(wake_matched, "").strip()

            if cmd_text and len(cmd_text) >= 2:
                # Immediate command present!
                logger.info(f"[AudioWorker] Executing command: '{cmd_text}'")
                self._dispatch_command(cmd_text)
            else:
                # Wake word alone: speak acknowledgment greeting
                self._speak_wake_ack()

    def _speak_wake_ack(self):
        """Speaks acknowledgment greeting when wake word is called without command."""
        greeting = "Haan Ji Boss, batayein?"
        try:
            from core_ai.core.jarvis_persona import generate_wake_acknowledgment
            ack = generate_wake_acknowledgment(wake_word="hey pulsar")
            if ack:
                greeting = ack
        except Exception:
            pass

        set_orb_state(state="speaking", force=True)
        self._tts_speaking = True
        try:
            from core_ai.voice.tts_output_service import get_tts_service
            get_tts_service().speak(greeting, source="wake_ack")
        except Exception:
            pass
        finally:
            self._tts_speaking = False
            self._tts_ended_at = time.time()
        set_orb_state(state="idle", force=True)

    def _dispatch_command(self, command_text: str):
        """Sends command to Core Agent Brain and plays voice response."""
        set_orb_state(state="thinking", force=True)

        reply_text = ""
        try:
            from backend.routes.system_routes import execute_companion_voice_command
            res = execute_companion_voice_command({"command": command_text, "source": "AUDIO_WORKER"})
            if isinstance(res, dict):
                reply_text = res.get("tts") or res.get("response") or ""
        except Exception as e:
            logger.warning(f"[AudioWorker] Command dispatch note: {e}")

        if reply_text:
            logger.info(f"[AudioWorker] Speaking response: '{reply_text[:60]}...'")
            set_orb_state(state="speaking", force=True)
            self._tts_speaking = True
            try:
                from core_ai.voice.tts_output_service import get_tts_service
                get_tts_service().speak(reply_text, source="audio_worker_reply")
            except Exception:
                pass
            finally:
                self._tts_speaking = False
                self._tts_ended_at = time.time()

        set_orb_state(state="idle", force=True)


_GLOBAL_AUDIO_WORKER: Optional[AudioWorker] = None
_WORKER_LOCK = threading.Lock()


def get_audio_worker() -> AudioWorker:
    """Singleton getter for AudioWorker."""
    global _GLOBAL_AUDIO_WORKER
    with _WORKER_LOCK:
        if _GLOBAL_AUDIO_WORKER is None:
            _GLOBAL_AUDIO_WORKER = AudioWorker()
        return _GLOBAL_AUDIO_WORKER


def start_core_audio_worker() -> bool:
    """Convenience helper to start audio worker inside Core server."""
    return get_audio_worker().start()


def stop_core_audio_worker():
    """Convenience helper to stop audio worker inside Core server."""
    worker = get_audio_worker()
    worker.stop()


def get_audio_worker_metrics() -> dict:
    """Returns live audio worker metrics (overruns, queue depth, device) for /health."""
    with _WORKER_LOCK:
        if _GLOBAL_AUDIO_WORKER is None:
            return {"running": False, "overrun_count": 0, "queue_depth": 0}
        return _GLOBAL_AUDIO_WORKER.get_metrics()
