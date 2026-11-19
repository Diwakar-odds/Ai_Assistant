"""
Pulsar Audio - Low-Overhead Microphone Stream (WASAPI Shared Mode)
==================================================================
Captures 16 kHz 16-bit mono audio in 20 ms frames (320 samples) via sounddevice.
Automatically selects the Windows WASAPI input device so
`sd.WasapiSettings(auto_convert=True)` works without PaErrorCode -9984.

Hard Invariants (Claude Paradigm B):
- Audio callback ONLY copies raw bytes, computes fast RMS, increments overrun
  counters, and pushes to a bounded queue.
- ZERO disk IO, ZERO logging, ZERO inference, ZERO network/socket calls in callback.
- Exposes overrun_count, queue_depth, and device_name for Core /health metrics.
"""

import sys
import queue
import logging
import threading
from typing import Optional, Tuple, Dict, Any
import numpy as np

logger = logging.getLogger("pulsar.audio.stream")

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 320  # 20 ms at 16 kHz (per Claude Blueprint Phase 4)
QUEUE_MAX_SIZE = 150  # ~3.0 seconds buffer


def _select_wasapi_input_device(sd) -> Tuple[Optional[int], str]:
    """
    Finds the best Windows WASAPI input device index so WasapiSettings(auto_convert=True)
    matches the device's host API (avoiding MME mismatch PaErrorCode -9984).
    """
    try:
        hostapis = sd.query_hostapis()
        wasapi_api_idx = None
        wasapi_default_in = -1
        for idx, api in enumerate(hostapis):
            if "wasapi" in str(api.get("name", "")).lower():
                wasapi_api_idx = idx
                wasapi_default_in = int(api.get("default_input_device", -1))
                break

        if wasapi_api_idx is None:
            return None, "Default Input"

        devices = sd.query_devices()
        if 0 <= wasapi_default_in < len(devices):
            dev = devices[wasapi_default_in]
            if dev.get("max_input_channels", 0) > 0:
                return wasapi_default_in, str(dev.get("name", f"WASAPI #{wasapi_default_in}"))

        # Fallback: first WASAPI microphone (preferring non-Stereo Mix)
        fallback_idx = None
        fallback_name = "WASAPI Input"
        for i, dev in enumerate(devices):
            if dev.get("hostapi") == wasapi_api_idx and dev.get("max_input_channels", 0) > 0:
                name = str(dev.get("name", ""))
                if "stereo mix" not in name.lower():
                    return i, name
                if fallback_idx is None:
                    fallback_idx = i
                    fallback_name = name
        return fallback_idx, fallback_name
    except Exception:
        return None, "Default Input"


class MicrophoneStream:
    """Thread-safe sounddevice WASAPI shared-mode audio input capture."""

    def __init__(self, sample_rate: int = SAMPLE_RATE, block_size: int = BLOCK_SIZE):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self._queue: queue.Queue = queue.Queue(maxsize=QUEUE_MAX_SIZE)
        self._stream = None
        self._is_running = False
        self._lock = threading.Lock()
        self._last_rms_level = 0.0
        self._overrun_count = 0
        self._stream_error_count = 0
        self._device_name = "Uninitialized"
        self._device_index: Optional[int] = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def latest_level(self) -> float:
        return self._last_rms_level

    @property
    def overrun_count(self) -> int:
        return self._overrun_count

    @property
    def queue_depth(self) -> int:
        return self._queue.qsize()

    @property
    def device_name(self) -> str:
        return self._device_name

    def get_metrics(self) -> Dict[str, Any]:
        """Returns live health metrics for Core GET /health."""
        return {
            "running": self._is_running,
            "device_name": self._device_name,
            "device_index": self._device_index,
            "sample_rate": self.sample_rate,
            "block_size": self.block_size,
            "overrun_count": self._overrun_count,
            "queue_depth": self._queue.qsize(),
            "queue_max": QUEUE_MAX_SIZE,
            "latest_rms": round(self._last_rms_level, 4),
            "stream_errors": self._stream_error_count,
        }

    def _audio_callback(self, indata, frames, time_info, status):
        """Ultra-lean callback: copies bytes, calculates RMS, pushes to ring queue."""
        if not self._is_running:
            return

        if status:
            if getattr(status, "input_overflow", False):
                self._overrun_count += 1
            else:
                self._stream_error_count += 1

        try:
            pcm = bytes(indata)
            arr = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
            rms = float(np.sqrt(np.mean(arr * arr))) / 32768.0
            level = min(1.0, max(0.0, rms * 6.5))
            self._last_rms_level = level

            if self._queue.full():
                self._overrun_count += 1
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass

            self._queue.put_nowait((pcm, level))
        except Exception:
            pass

    def start(self) -> bool:
        """Opens microphone stream in WASAPI shared mode with auto_convert=True."""
        with self._lock:
            if self._is_running:
                return True

            try:
                import sounddevice as sd

                # 1. Preferred path on Windows: explicit WASAPI device + auto_convert=True
                if sys.platform == "win32":
                    wasapi_idx, wasapi_name = _select_wasapi_input_device(sd)
                    if wasapi_idx is not None:
                        try:
                            extra = sd.WasapiSettings(auto_convert=True)
                            self._stream = sd.InputStream(
                                device=wasapi_idx,
                                samplerate=self.sample_rate,
                                channels=CHANNELS,
                                dtype="int16",
                                blocksize=self.block_size,
                                callback=self._audio_callback,
                                extra_settings=extra,
                            )
                            self._stream.start()
                            self._is_running = True
                            self._device_index = wasapi_idx
                            self._device_name = wasapi_name
                            logger.info(
                                f"[MicStream] WASAPI microphone opened: [{wasapi_idx}] {wasapi_name} "
                                f"at {self.sample_rate}Hz (block={self.block_size} / 20ms)"
                            )
                            return True
                        except Exception as wasapi_err:
                            logger.warning(f"[MicStream] WASAPI open note ({wasapi_err}); falling back to default device.")
                            self._stream = None

                # 2. Fallback path: system default input device without WASAPI-only extra_settings
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=CHANNELS,
                    dtype="int16",
                    blocksize=self.block_size,
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._is_running = True
                try:
                    def_in = sd.default.device[0]
                    dev_info = sd.query_devices(def_in)
                    self._device_index = int(def_in)
                    self._device_name = str(dev_info.get("name", "Default Input"))
                except Exception:
                    self._device_name = "Default System Input"
                logger.info(
                    f"[MicStream] Microphone opened: {self._device_name} "
                    f"at {self.sample_rate}Hz (block={self.block_size})"
                )
                return True
            except Exception as e:
                logger.error(f"[MicStream] Failed to open microphone stream: {e}")
                self._is_running = False
                return False

    def read_frame(self, timeout: float = 0.1) -> Optional[Tuple[bytes, float]]:
        """Retrieves next (pcm_bytes, rms_level) tuple from queue."""
        if not self._is_running:
            return None
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        """Stops the audio stream and releases hardware handle immediately."""
        with self._lock:
            self._is_running = False
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    logger.debug(f"[MicStream] Stream close note: {e}")
                finally:
                    self._stream = None

            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break

            self._last_rms_level = 0.0
            logger.info("[MicStream] Microphone stream stopped and hardware handle released.")
