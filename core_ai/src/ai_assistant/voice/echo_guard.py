"""
Acoustic Echo Guard — Content-Based Echo Cancellation for Pulsar AI Assistant.

Instead of blanket-muting the microphone during TTS playback (the old
``set_tts_active`` timer), this module compares *what the speakers just played*
with *what the microphone just heard* in the frequency domain and subtracts it.

How it works
------------
1. **Band Energies:**  Every audio slice (mic or speaker) is reduced to 8 coarse
   frequency-band energies via FFT.  Coarse bands deliberately ignore pitch
   (which differs between people) and track *timbre* (which echo preserves).

2. **Projection & Subtraction:**  For each mic block, we find the recent
   speaker slice whose band-energy vector best explains (projects onto) the
   mic vector, then subtract it.  Pure echo cancels to near-zero residual; a
   different voice survives because its formants sit in bands where ours were
   weak.

3. **Self-Calibrating Gain:**  Whenever a block is confidently echo, the
   observed mic-to-speaker level ratio is folded into a running estimate.  The
   system learns the room's echo characteristics within a few seconds and
   re-calibrates when conditions change (volume, headphones, hand over mic).

Why this beats a timer
----------------------
- The microphone is NEVER blanket-muted — it stays open during playback.
- User can interrupt mid-sentence.
- Works regardless of TTS duration or room echo delay.
- Auto-calibrates to any room / speaker setup.

Adapted from Mark-LIV's core/echo.py (MIT) with improvements for Pulsar's
architecture (24 kHz TTS playback, 16 kHz mic capture, WebSocket audio flow).
"""

from __future__ import annotations

import time
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Log-spaced band edges across the speech range.  Coarse on purpose: fine bins
# would track pitch (which differs between speakers), we want *timbre* (which
# echo preserves).
_BAND_EDGES = (200, 400, 700, 1100, 1700, 2600, 3800, 5200, 7000)

_HISTORY_S = 1.5        # How far back an echo could plausibly arrive
_MIN_LEVEL = 0.06       # Below this the mic is room noise; nothing to decide

# Threshold placement — sits just above the worst echo the room has produced.
_MIN_USER = 0.15        # Never call anything below this a voice
_HEAD_Q = 97            # Percentile of observed echo the threshold must clear
_HEAD_MULT = 1.15       # ...with this much headroom above it

# When the echo floor is this high, content alone separates poorly.
_UNRELIABLE_FLOOR = 0.22
_BLOCKS_NORMAL = 5      # ~320 ms of sustained evidence
_BLOCKS_NOISY = 12      # ~770 ms when the room is hard

_FLOOR_WINDOW = 60      # Blocks kept to characterise the room's echo
_FLOOR_Q = 35           # Percentile taken as "typical echo here"
_WARMUP = 16            # Blocks (~1 s) before judging anyone
_RELEARN_RUN = 28       # A 'voice' lasting this long → room changed


# ---------------------------------------------------------------------------
# Band-energy fingerprint
# ---------------------------------------------------------------------------

def band_energies(pcm, sr: int) -> np.ndarray:
    """Compute energy per speech band — the fingerprint we compare.

    Left unnormalised: the decision below projects one vector onto another,
    and a projection needs real magnitudes.

    Parameters
    ----------
    pcm : array-like
        Audio samples (int16 or float32).
    sr : int
        Sample rate (e.g. 16000 for mic, 24000 for TTS).

    Returns
    -------
    np.ndarray
        Energy in each frequency band (len = len(_BAND_EDGES) - 1 = 8).
    """
    x = np.asarray(pcm, dtype=np.float32)
    if x.size < 64:
        return np.zeros(len(_BAND_EDGES) - 1, dtype=np.float32)

    # Remove DC offset
    x = x - x.mean()

    # FFT with Hanning window, padded to next power of two
    n = 1 << (int(x.size) - 1).bit_length()
    mag = np.abs(np.fft.rfft(x * np.hanning(x.size), n=n))
    freqs = np.fft.rfftfreq(n, 1.0 / sr)

    out = np.empty(len(_BAND_EDGES) - 1, dtype=np.float32)
    for i in range(len(_BAND_EDGES) - 1):
        mask = (freqs >= _BAND_EDGES[i]) & (freqs < _BAND_EDGES[i + 1])
        out[i] = float(mag[mask].sum())
    return out


# ---------------------------------------------------------------------------
# Echo Guard
# ---------------------------------------------------------------------------

class EchoGuard:
    """Classifies microphone blocks while the assistant is speaking.

    Usage
    -----
    - Call ``note_output(pcm, sr, level)`` from the TTS/playback path every
      time a chunk of audio is sent to the speakers.
    - Call ``is_user_speech(pcm, sr, level)`` from the microphone callback.
      Returns ``True`` only if the mic block contains a *different* voice.

    Both methods are cheap enough (one small FFT each) to sit in an audio
    thread.

    The guard never blanket-mutes the microphone.  Instead it subtracts the
    known speaker signal in the frequency domain and checks what's left.
    """

    def __init__(self) -> None:
        # Recent output history: (timestamp, band_energies, level)
        self._hist: list[tuple[float, np.ndarray, float]] = []

        # Learned echo gain (mic level per unit of output level)
        self._gain: float = 0.6
        self._seen: int = 0          # How many echo blocks the estimate has seen

        # Diagnostics
        self._last_sim: float = 0.0
        self._last_expected: float = 0.0

        # Room characterisation
        self._residuals: list[float] = []   # Recent ECHO residuals only
        self._floor: float = 0.10           # Typical echo residual; learned
        self._head: float = 0.13            # Near-worst echo residual; learned
        self._run: int = 0                  # Consecutive blocks called speech

        # Track whether we are actively playing audio
        self._is_playing: bool = False

        logger.info("[EchoGuard] Initialized — content-based echo cancellation active")

    # ── Properties / diagnostics ──────────────────────────────────────────

    @property
    def gain(self) -> float:
        """Learned mic-to-speaker level ratio."""
        return self._gain

    @property
    def calibrated(self) -> bool:
        """True once the estimate rests on enough real echo to be trusted."""
        return self._seen >= 8

    @property
    def floor(self) -> float:
        """Residual left by this room's echo.  Higher = harder to separate."""
        return self._floor

    @property
    def reliable(self) -> bool:
        """False when the acoustics are too poor to judge on content alone."""
        return self._floor < _UNRELIABLE_FLOOR

    @property
    def threshold(self) -> float:
        """The residual a block must clear to count as a voice."""
        return max(_MIN_USER, self._head * _HEAD_MULT)

    @property
    def required_blocks(self) -> int:
        """Consecutive positive blocks before an interruption is believed."""
        return _BLOCKS_NORMAL if self.reliable else _BLOCKS_NOISY

    @property
    def last_similarity(self) -> float:
        """1.0 = fully explained by our output, 0.0 = nothing to do with it."""
        return self._last_sim

    @property
    def is_playing(self) -> bool:
        """True if TTS output is currently being tracked."""
        return self._is_playing

    # ── Public control ────────────────────────────────────────────────────

    def reset(self) -> None:
        """Playback stopped — drop the output history, keep what was learned."""
        self._hist.clear()
        self._last_sim = 0.0
        self._is_playing = False
        logger.debug("[EchoGuard] Reset — playback stopped")

    def get_status(self) -> dict:
        """Return a status dict for the diagnostics API."""
        return {
            "calibrated": self.calibrated,
            "gain": round(self._gain, 3),
            "floor": round(self._floor, 3),
            "reliable": self.reliable,
            "threshold": round(self.threshold, 3),
            "is_playing": self._is_playing,
            "history_size": len(self._hist),
            "residuals_count": len(self._residuals),
            "seen_echo_blocks": self._seen,
        }

    # ── Entry point 1: Record what we are playing ─────────────────────────

    def note_output(
        self,
        pcm,
        sr: int,
        level: Optional[float] = None,
        when: Optional[float] = None,
    ) -> None:
        """Record a slice of what is being played, for later comparison.

        Parameters
        ----------
        pcm : array-like
            Raw audio samples sent to the speakers.
        sr : int
            Sample rate of the output (e.g. 24000 for KittenTTS).
        level : float, optional
            Pre-computed RMS level.  If None, computed from pcm.
        when : float, optional
            Monotonic timestamp.  If None, ``time.monotonic()`` is used.
        """
        try:
            t = time.monotonic() if when is None else when

            if level is None:
                x = np.asarray(pcm, dtype=np.float32)
                if x.size > 0:
                    level = float(np.sqrt(np.mean(x ** 2)))
                else:
                    level = 0.0

            self._hist.append((t, band_energies(pcm, sr), float(level)))
            self._is_playing = True

            # Prune old entries
            cutoff = t - _HISTORY_S
            if len(self._hist) > 8:
                self._hist = [h for h in self._hist if h[0] >= cutoff]
        except Exception:
            pass  # Never let bookkeeping disturb playback

    # ── Entry point 2: Classify microphone block ──────────────────────────

    def is_user_speech(
        self,
        pcm,
        sr: int,
        level: Optional[float] = None,
        when: Optional[float] = None,
    ) -> bool:
        """True if this microphone block is a different voice, not our echo.

        Parameters
        ----------
        pcm : array-like
            Raw audio samples from the microphone.
        sr : int
            Sample rate of the microphone (e.g. 16000).
        level : float, optional
            Pre-computed RMS level.  If None, computed from pcm.
        when : float, optional
            Monotonic timestamp.
        """
        try:
            if level is None:
                x = np.asarray(pcm, dtype=np.float32)
                if x.size > 0:
                    level = float(np.sqrt(np.mean(x ** 2)))
                else:
                    level = 0.0

            if level < _MIN_LEVEL:
                # Microphone hears nothing — record that for calibration
                if self._hist and max(h[2] for h in self._hist) > 0.15:
                    self._residuals.append(0.0)
                    if len(self._residuals) > _FLOOR_WINDOW:
                        del self._residuals[:-_FLOOR_WINDOW]
                    if len(self._residuals) >= _WARMUP:
                        self._floor = float(np.percentile(self._residuals, _FLOOR_Q))
                        self._head = float(np.percentile(self._residuals, _HEAD_Q))
                self._run = 0
                return False

            if not self._hist:
                # Nothing playing that we know of — anything audible is theirs
                return True

            t = time.monotonic() if when is None else when
            bands = band_energies(pcm, sr)
            total = float(bands.sum())
            if total <= 1e-9:
                return False

            # Find the recent output slice that best explains this block.
            # Subtract as much of it as fits.  What's left over is whatever
            # the mic heard that we did NOT play.
            best_res, best_level = 1.0, 0.0
            for ts, ref, ref_level in self._hist:
                if ts > t or t - ts > _HISTORY_S:
                    continue
                denom = float(np.dot(ref, ref))
                if denom < 1e-12:
                    continue
                # Projection coefficient: how much of 'ref' fits into 'bands'
                alpha = max(0.0, float(np.dot(bands, ref)) / denom)
                residual = np.maximum(bands - alpha * ref, 0.0)
                ratio = float(residual.sum()) / total
                if ratio < best_res:
                    best_res, best_level = ratio, ref_level

            self._last_sim = 1.0 - best_res

            # Nothing in the window explained it — that is not our sound
            if best_level <= 0.0:
                return True

            # --- Learning ---
            # While warming up, learn from EVERY block (so we don't misjudge
            # the first echo as a voice).  Once warm, learn only from blocks
            # BELOW the bar (so user speech doesn't lift the threshold).
            warming = len(self._residuals) < _WARMUP
            thr = self.threshold
            speech = (not warming) and best_res >= thr

            if speech:
                self._run += 1
                # A run this long is not someone interrupting — nobody talks
                # over an assistant for seconds on end.  The room changed
                # (volume, headphones unplugged), so characterise it again.
                if self._run > _RELEARN_RUN:
                    self._residuals.clear()
                    self._run = 0
                    return False
                return True

            self._run = 0
            self._residuals.append(best_res)
            if len(self._residuals) > _FLOOR_WINDOW:
                del self._residuals[:-_FLOOR_WINDOW]
            if len(self._residuals) >= _WARMUP:
                self._floor = float(np.percentile(self._residuals, _FLOOR_Q))
                self._head = float(np.percentile(self._residuals, _HEAD_Q))
            if warming:
                return False

            # Comfortably just us: also a safe moment to learn how loudly
            # this room returns our voice.
            if best_res <= self._floor * 1.15 and best_level > 0.05:
                obs = level / max(best_level, 1e-6)
                self._gain += (min(obs, 3.0) - self._gain) * 0.08
                self._seen = min(self._seen + 1, 999)
            return False

        except Exception as e:
            logger.debug(f"[EchoGuard] is_user_speech error (safe fallback): {e}")
            return False  # Any doubt: do not interrupt


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_echo_guard_instance: Optional[EchoGuard] = None


def get_echo_guard() -> EchoGuard:
    """Get or create the module-level EchoGuard singleton."""
    global _echo_guard_instance
    if _echo_guard_instance is None:
        _echo_guard_instance = EchoGuard()
    return _echo_guard_instance


def reset_echo_guard() -> None:
    """Reset the singleton (e.g. when playback stops)."""
    if _echo_guard_instance is not None:
        _echo_guard_instance.reset()
