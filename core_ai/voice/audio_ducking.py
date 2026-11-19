"""
Pulsar AI Assistant - Production Audio Ducking Service
=====================================================
Automatically ducks Windows master output and background media volume by ~65%
whenever the user starts speaking or when the assistant speaks.
Smoothly restores the original master volume when speech or TTS playback finishes.

Thread-safe, reference-counted (safe for overlapping mic + TTS turns), and
resilient across Windows COM threads.
"""

import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_DUCK_LOCK = threading.RLock()
_ORIGINAL_VOLUME: Optional[float] = None
_DUCK_COUNT: int = 0
_IS_DUCKED: bool = False


def duck_audio(attenuation_factor: float = 0.35) -> bool:
    """
    Duck master output volume to reduce background audio interference during speech/TTS.
    Uses reference counting so overlapping user speech and TTS stay ducked continuously.
    Returns True if master volume is currently ducked.
    """
    global _ORIGINAL_VOLUME, _DUCK_COUNT, _IS_DUCKED
    with _DUCK_LOCK:
        _DUCK_COUNT += 1
        if _IS_DUCKED:
            # Already ducked, just incremented refcount
            return True

        try:
            import comtypes
            comtypes.CoInitialize()
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from comtypes import CLSCTX_ALL

                devices = AudioUtilities.GetSpeakers()
                if not devices:
                    return False
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = interface.QueryInterface(IAudioEndpointVolume)
                current_vol = volume.GetMasterVolumeLevelScalar()

                if current_vol > 0.05:
                    _ORIGINAL_VOLUME = current_vol
                    target_vol = max(0.08, current_vol * attenuation_factor)
                    volume.SetMasterVolumeLevelScalar(target_vol, None)
                    _IS_DUCKED = True
                    logger.debug(f"[AudioDucker] Ducked master volume from {current_vol:.2f} -> {target_vol:.2f} (refcount={_DUCK_COUNT})")
                    return True
            finally:
                comtypes.CoUninitialize()
        except Exception as e:
            logger.debug(f"[AudioDucker] Ducking unavailable or failed: {e}")
            return False
    return False


def unduck_audio(force: bool = False) -> bool:
    """
    Decrement duck refcount and restore master volume back to pre-duck level
    when all active speech/TTS sources have finished (or immediately if force=True).
    Returns True if volume was restored to original level.
    """
    global _ORIGINAL_VOLUME, _DUCK_COUNT, _IS_DUCKED
    with _DUCK_LOCK:
        if force:
            _DUCK_COUNT = 0
        else:
            _DUCK_COUNT = max(0, _DUCK_COUNT - 1)

        if _DUCK_COUNT > 0:
            # Still held by another voice/TTS source
            return False

        if not _IS_DUCKED or _ORIGINAL_VOLUME is None:
            _IS_DUCKED = False
            _DUCK_COUNT = 0
            return False

        try:
            import comtypes
            comtypes.CoInitialize()
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from comtypes import CLSCTX_ALL

                devices = AudioUtilities.GetSpeakers()
                if not devices:
                    return False
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = interface.QueryInterface(IAudioEndpointVolume)

                volume.SetMasterVolumeLevelScalar(_ORIGINAL_VOLUME, None)
                logger.debug(f"[AudioDucker] Restored master volume to {_ORIGINAL_VOLUME:.2f}")
                _IS_DUCKED = False
                _ORIGINAL_VOLUME = None
                _DUCK_COUNT = 0
                return True
            finally:
                comtypes.CoUninitialize()
        except Exception as e:
            logger.debug(f"[AudioDucker] Unduck failed: {e}")
            _IS_DUCKED = False
            _ORIGINAL_VOLUME = None
            _DUCK_COUNT = 0
            return False
    return False


def is_audio_ducked() -> bool:
    """Check if audio is currently ducked."""
    with _DUCK_LOCK:
        return _IS_DUCKED
