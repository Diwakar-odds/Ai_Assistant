"""
UTF-8 stdout bootstrap (audit fix D1, part i).

The assistant's source files are UTF-8, but the Windows PowerShell console
defaults to cp1252. Emoji literals render as mojibake (…, ‘‹, etc.) even
when the bytes on disk are correct.

This module reconfigures sys.stdout / sys.stderr at import time so that
console output is rendered as UTF-8. Safe on non-Windows (it'll no-op there).
Safe to import multiple times.

Usage
-----
At the very top of main.py, before any other import that might print:

    try:
        from core_ai.src.ai_assistant.utils.utf8_bootstrap import configure_utf8_stdout
        configure_utf8_stdout()
    except Exception:
        pass

Or drop this file somewhere on sys.path and import directly. Path doesn't
matter — only the call matters, and the earlier the better.

What it does
------------
On Windows (PEP 528+, Python 3.7+):
  sys.stdout.reconfigure(encoding='utf-8', errors='replace')
  sys.stderr.reconfigure(encoding='utf-8', errors='replace')

On other platforms: no-op.

It also sets PYTHONIOENCODING for child processes that read from sys.stdin
or write to inherited file descriptors, which catches a class of issues
where the console is fine but a subprocess log isn't.
"""

from __future__ import annotations

import os
import sys


def configure_utf8_stdout() -> None:
    """Reconfigure stdout/stderr to UTF-8 on Windows. No-op elsewhere."""
    try:
        # Force the encoding for any child process that reads this env var.
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")

        if sys.platform != "win32":
            return

        for stream_name in ("stdout", "stderr"):
            stream = getattr(sys, stream_name, None)
            reconfigure = getattr(stream, "reconfigure", None)
            if callable(reconfigure):
                try:
                    reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    # Some embedded streams (pytest capture, IDE consoles) don't
                    # support reconfigure. That's fine — fall through.
                    pass
    except Exception:
        # Bootstrap must never crash the app.
        pass


# Auto-configure on import so a single import line in main.py is enough.
configure_utf8_stdout()
