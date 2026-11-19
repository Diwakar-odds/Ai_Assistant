"""
Pulsar Native Host Package (PySide6)
Paradigm B: Native Host Process

Invariants:
- Zero heavy AI / torch / whisper / llama imports in Host.
- Owns all native GUI: System Tray (QSystemTrayIcon), Dashboard (QWebEngineView), 4D Orb Window.
- Manages Core child process via Win32 Job Object (KILL_ON_JOB_CLOSE).
- Single-instance guaranteed via Win32 Mutex 'Local\\Pulsar.Host.v1'.
"""

__all__ = ["job_object", "core_supervisor", "tray_app", "orb_window", "dashboard_window"]
