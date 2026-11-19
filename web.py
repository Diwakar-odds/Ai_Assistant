"""
Pulsar AI Assistant - Master Unified Launcher
=============================================
Paradigm B: Decoupled 2-Process Architecture (Native Host + Headless Core)

Architecture Invariants (Claude Blueprint):
1. One Launch Command: `python web.py` starts the entire system.
2. One Lifecycle: Win32 Job Object (KILL_ON_JOB_CLOSE) + Parent Watchdog = zero orphans.
3. One Port: Port 5000 bound strictly to loopback (127.0.0.1) with per-launch auth token.
4. One Microphone Owner: Core Audio Worker owns WASAPI mic exclusively. Host NEVER touches mic or AI models.
5. Native Host: PySide6 System Tray + 4D Glowing Orb + Dashboard + Single `reconcile()` handoff.

Usage:
    python web.py             (Starts Tray Icon, 4D Orb, Dashboard, and Headless Core)
    python web.py --tray      (Starts minimized in System Tray with 4D Orb immediately visible)
    python web.py --test-orb  (Phase-1 standalone visual test: ONLY 4D Orb + Tray Icon)
    python web.py --core-only (Runs Headless Core server only, without GUI)
"""

import sys
import os
import argparse
from pathlib import Path

# 1. Auto-wrap with project virtual environment if launched via global python
#    (accepts both venv\Scripts\python.exe and venv\Scripts\pythonw.exe cleanly!)
_root_dir = Path(__file__).resolve().parent
_venv_python = _root_dir / "venv" / "Scripts" / "python.exe"
_venv_pythonw = _root_dir / "venv" / "Scripts" / "pythonw.exe"

if _venv_python.exists():
    def _is_same_exe(a: str, b: Path) -> bool:
        if not b.exists():
            return False
        try:
            return os.path.samefile(a, str(b))
        except Exception:
            return os.path.normpath(a).lower() == os.path.normpath(str(b)).lower()

    _in_venv = _is_same_exe(sys.executable, _venv_python) or _is_same_exe(sys.executable, _venv_pythonw)
    if not _in_venv and os.environ.get("_PULSAR_VENV_WRAPPED") != "1":
        os.environ["_PULSAR_VENV_WRAPPED"] = "1"
        import subprocess
        _target = _venv_pythonw if (sys.executable.lower().endswith("pythonw.exe") and _venv_pythonw.exists()) else _venv_python
        sys.exit(subprocess.call([str(_target)] + sys.argv))

# 2. Enforce Per-Monitor V2 DPI Awareness BEFORE any GUI library is imported (Claude Failure #4)
if sys.platform == "win32":
    try:
        import ctypes
        DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
        ctypes.windll.user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

# 3. Configure console UTF-8 encoding
if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Keep Host sys.path clean: ONLY add repo root (never eagerly expose backend/core_ai to Host)
if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))


def __getattr__(name):
    """Backward compatibility: proxy attributes like app, socketio to backend."""
    for _p in (str(_root_dir / "backend"), str(_root_dir / "core_ai")):
        if _p not in sys.path:
            sys.path.insert(0, _p)
    from backend.modern_web_backend import app, socketio
    if name == "app":
        return app
    elif name == "socketio":
        return socketio
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def main():
    parser = argparse.ArgumentParser(description="Pulsar AI Assistant - Master Launcher")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 5000)), help="Port (default: 5000)")
    parser.add_argument("--minimized", "--tray", dest="start_minimized", action="store_true", help="Start minimized in system tray with 4D Orb visible")
    parser.add_argument("--open", dest="open_dashboard", action="store_true", help="Open dashboard window immediately")
    parser.add_argument("--test-orb", action="store_true", help="Standalone Phase-1 visual test of 4D Orb + System Tray")
    parser.add_argument("--core-only", action="store_true", help="Run Headless Core only without GUI")
    parser.add_argument("--no-prewarm", action="store_true", help="Skip heavy pre-warming on startup")

    args = parser.parse_args()

    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONUNBUFFERED"] = "1"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging --log-level=3 --no-sandbox"

    if args.test_orb:
        from pulsar.host.__main__ import run_standalone_orb_tray_test
        run_standalone_orb_tray_test(port=args.port)
    elif args.core_only:
        for _p in (str(_root_dir / "backend"), str(_root_dir / "core_ai")):
            if _p not in sys.path:
                sys.path.insert(0, _p)
        from pulsar.core.server import run_core
        run_core(host="127.0.0.1", port=args.port, prewarm=not args.no_prewarm)
    else:
        from pulsar.host.__main__ import run_host
        run_host(port=args.port, start_dashboard=bool(args.open_dashboard and not args.start_minimized))


if __name__ == "__main__":
    main()
