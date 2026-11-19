"""
Pulsar Core - Orb State Manager

Manages the 4D Orb state machine and broadcasts real-time state updates
over Socket.IO at up to 30 Hz to the PySide6 WebEngine host window or web frontend.
"""

import time
import logging
import threading
from typing import Optional, Dict, Any

logger = logging.getLogger("pulsar.core.orb_state")

VALID_STATES = {"idle", "listening", "thinking", "speaking", "offline", "error"}


class OrbStateManager:
    """Thread-safe rate-limited orb state broadcaster."""

    def __init__(self, min_emit_interval_sec: float = 1.0 / 30.0):
        self._lock = threading.Lock()
        self._socketio = None
        self._min_emit_interval = min_emit_interval_sec
        self._last_emit_time = 0.0

        self._state = "idle"
        self._level = 0.0
        self._details: Dict[str, Any] = {}
        self._last_emitted_state = ""
        self._last_emitted_level = -1.0

    def set_socketio(self, socketio_instance):
        """Attaches the Flask-SocketIO instance for live broadcasting."""
        with self._lock:
            self._socketio = socketio_instance
        logger.info("[OrbState] SocketIO attached to OrbStateManager")

    def update_state(
        self,
        state: Optional[str] = None,
        level: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Updates the orb state and broadcasts to Socket.IO clients.
        State changes emit immediately. Audio level changes are throttled to 30 Hz.
        """
        with self._lock:
            now = time.time()
            state_changed = False

            if state is not None and state != self._state:
                if state in VALID_STATES:
                    self._state = state
                    state_changed = True
                else:
                    logger.warning(f"[OrbState] Unknown state '{state}'. Valid: {VALID_STATES}")

            if level is not None:
                # Clamp between 0.0 and 1.0
                self._level = max(0.0, min(1.0, float(level)))

            if details is not None:
                self._details = details

            payload = {
                "state": self._state,
                "level": round(self._level, 3),
                "timestamp": now,
                "details": self._details,
            }

            # State transitions emit immediately without throttle
            time_elapsed = now - self._last_emit_time
            level_diff = abs(self._level - self._last_emitted_level)
            should_emit = force or state_changed or (time_elapsed >= self._min_emit_interval and level_diff >= 0.015)

            if should_emit and self._socketio is not None:
                try:
                    self._socketio.emit("orb_state", payload)
                    self._last_emit_time = now
                    self._last_emitted_state = self._state
                    self._last_emitted_level = self._level
                except Exception as e:
                    logger.debug(f"[OrbState] SocketIO emit error: {e}")

            return payload

    def get_state(self) -> Dict[str, Any]:
        """Returns snapshot of current state."""
        with self._lock:
            return {
                "state": self._state,
                "level": round(self._level, 3),
                "timestamp": time.time(),
                "details": dict(self._details),
            }


_GLOBAL_ORB_MANAGER: Optional[OrbStateManager] = None
_GLOBAL_LOCK = threading.Lock()


def get_orb_state_manager() -> OrbStateManager:
    """Singleton getter for OrbStateManager."""
    global _GLOBAL_ORB_MANAGER
    with _GLOBAL_LOCK:
        if _GLOBAL_ORB_MANAGER is None:
            _GLOBAL_ORB_MANAGER = OrbStateManager()
        return _GLOBAL_ORB_MANAGER


def set_orb_state(
    state: Optional[str] = None,
    level: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Convenience helper to set orb state globally."""
    return get_orb_state_manager().update_state(state=state, level=level, details=details, force=force)


def get_orb_state() -> Dict[str, Any]:
    """Convenience helper to read orb state globally."""
    return get_orb_state_manager().get_state()
