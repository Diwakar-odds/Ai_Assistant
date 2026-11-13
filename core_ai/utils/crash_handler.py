"""
Pulsar AI Assistant - Enterprise Crash Recovery & Unhandled Exception Handler
=============================================================================
Catches unhandled exceptions across main and background threads, logs full
system diagnostics to the canonical logs directory, and displays a user-friendly
Win32 native alert if running in packaged desktop GUI mode without console.
"""

import sys
import os
import time
import traceback
import platform
import threading
import tempfile
from pathlib import Path
from typing import Optional


_CRASH_HANDLER_INSTALLED = False
_ORIGINAL_EXCEPTHOOK = sys.excepthook
_ORIGINAL_THREADING_EXCEPTHOOK = getattr(threading, "excepthook", None)


def _resolve_crash_log_file() -> Path:
    """Resolve the target path for crash.log safely."""
    try:
        from core_ai.config.paths import LOGS_DIR
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        return LOGS_DIR / "crash.log"
    except Exception:
        # Fallback to LocalAppData or Temp
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            fallback = Path(local_app_data) / "PulsarAI" / "logs"
            try:
                fallback.mkdir(parents=True, exist_ok=True)
                return fallback / "crash.log"
            except Exception:
                pass
        return Path(tempfile.gettempdir()) / "pulsar_crash.log"


def _format_crash_report(exc_type, exc_value, exc_traceback) -> str:
    """Generate detailed diagnostic crash report."""
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_str = "".join(tb_lines)

    frozen = bool(getattr(sys, "frozen", False))
    env_mode = os.environ.get("PULSAR_ENV", "development" if not frozen else "production")

    report = [
        "=" * 72,
        f"PULSAR AI ASSISTANT - CRASH REPORT",
        f"Timestamp:   {now}",
        f"Exception:   {exc_type.__name__}: {exc_value}",
        f"Frozen (.exe): {frozen}",
        f"Environment: {env_mode}",
        f"Python:      {platform.python_version()} ({platform.architecture()[0]})",
        f"Platform:    {platform.platform()}",
        f"Executable:  {sys.executable}",
        "=" * 72,
        "TRACEBACK:",
        tb_str.strip(),
        "=" * 72,
        "\n",
    ]
    return "\n".join(report)


def _show_crash_dialog(crash_log_path: Path, exc_name: str, exc_msg: str):
    """Show native Win32 MessageBox on Windows if running in GUI mode."""
    if sys.platform == "win32":
        try:
            import ctypes
            title = "Pulsar AI Assistant - Unexpected Error"
            msg = (
                f"Pulsar AI Assistant encountered an unexpected error:\n\n"
                f"{exc_name}: {exc_msg}\n\n"
                f"A diagnostic crash report has been saved to:\n"
                f"{crash_log_path}\n\n"
                f"Please share this file with support to resolve the issue."
            )
            # MB_ICONERROR (0x10) | MB_OK (0x00) | MB_SYSTEMMODAL (0x1000)
            ctypes.windll.user32.MessageBoxW(0, msg, title, 0x10 | 0x1000)
        except Exception:
            pass


def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    """Central unhandled exception dispatcher."""
    # Don't intercept clean user exits (Ctrl+C or sys.exit)
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        if _ORIGINAL_EXCEPTHOOK:
            _ORIGINAL_EXCEPTHOOK(exc_type, exc_value, exc_traceback)
        return

    crash_log_file = _resolve_crash_log_file()
    report = _format_crash_report(exc_type, exc_value, exc_traceback)

    # Write report to disk
    try:
        with open(crash_log_file, "a", encoding="utf-8") as f:
            f.write(report)
    except Exception:
        pass

    # Print to stderr if available
    try:
        sys.stderr.write(report)
        sys.stderr.flush()
    except Exception:
        pass

    # Display GUI alert if frozen or no visible console
    is_gui = bool(getattr(sys, "frozen", False)) or (sys.stderr is None)
    if is_gui:
        _show_crash_dialog(crash_log_file, exc_type.__name__, str(exc_value))


def handle_thread_exception(args):
    """Threading exception handler for Python 3.8+."""
    handle_unhandled_exception(args.exc_type, args.exc_value, args.exc_traceback)


def install_crash_handler():
    """Install the global crash hook for both main thread and worker threads."""
    global _CRASH_HANDLER_INSTALLED
    if _CRASH_HANDLER_INSTALLED:
        return

    sys.excepthook = handle_unhandled_exception
    if hasattr(threading, "excepthook"):
        threading.excepthook = handle_thread_exception

    _CRASH_HANDLER_INSTALLED = True


__all__ = [
    "install_crash_handler",
    "handle_unhandled_exception",
]
