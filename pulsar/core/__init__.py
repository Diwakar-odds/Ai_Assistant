"""
Pulsar Headless Core Package (python -m pulsar.core)

Invariants:
- Zero GUI imports (no win32gui, no pystray, no pywebview, no tkinter).
- Strictly binds to 127.0.0.1 (loopback only).
- Authenticated via per-launch security token.
- Single owner of AI inference engines (Llama, Whisper, KittenTTS, etc.).
- Monitored by Win32 parent process watchdog.
"""

__all__ = ["server", "watchdog", "orb_state"]
