"""
Pulsar AI Assistant - Standalone Frozen Windows App Entrypoint
==============================================================
Dual-mode Paradigm B executable for PyInstaller `--onedir` distribution:
- `Pulsar.exe`                    -> Native PySide6 Host (Dashboard + 4D Wireframe Orb + System Tray)
- `Pulsar.exe --tray`             -> Native Host starting minimized in System Tray with 4D Orb active
- `Pulsar.exe --core-subprocess`  -> Headless AI & Audio Core (Flask + Socket.IO + WASAPI Mic + GGUF + Whisper + KittenTTS)

Strict Paradigm B Invariant:
- Host mode NEVER imports torch, llama_cpp, faster_whisper, sounddevice, or backend.
- Core mode NEVER imports PySide6 or QtWebEngine.
"""

import os
import sys
import multiprocessing
from pathlib import Path


def _setup_frozen_environment() -> Path:
    """Configures offline flags and resolves app directory beside Pulsar.exe."""
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).resolve().parent
        meipass = Path(getattr(sys, "_MEIPASS", app_dir))
    else:
        app_dir = Path(__file__).resolve().parent.parent
        meipass = app_dir

    os.environ.setdefault("PULSAR_ENV", "production")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-logging --log-level=3 --no-sandbox")

    # In PyInstaller console=False mode, detached launches have sys.stdout/stderr = None.
    # Redirect to os.devnull so Click/Flask/tqdm never crash on .write()/.flush().
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    models_dir = app_dir / "models"
    if models_dir.exists():
        os.environ["PULSAR_MODELS_DIR"] = str(models_dir)

    for p in (str(app_dir), str(meipass)):
        if p not in sys.path:
            sys.path.insert(0, p)

    return app_dir


def main():
    multiprocessing.freeze_support()
    app_dir = _setup_frozen_environment()

    # Mode 1: Headless Core Subprocess (spawned by Host's CoreSupervisor inside Win32 Job Object)
    if "--core-subprocess" in sys.argv:
        sys.argv = [a for a in sys.argv if a != "--core-subprocess"]
        meipass = Path(getattr(sys, "_MEIPASS", app_dir))
        for p in (str(meipass / "backend"), str(meipass / "core_ai"), str(app_dir / "backend"), str(app_dir / "core_ai")):
            if os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)
        from pulsar.core.__main__ import main as core_main
        core_main()
        return

    # Mode 2: Native Windows Desktop Host (PySide6)
    if sys.platform == "win32":
        try:
            import ctypes
            # Per-Monitor V2 DPI Awareness BEFORE any Qt import
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass
        try:
            import ctypes
            # Allow foreground activation if waking up an already-running Pulsar instance
            ctypes.windll.user32.AllowSetForegroundWindow(0xFFFFFFFF)
        except Exception:
            pass

    import argparse
    parser = argparse.ArgumentParser(description="Pulsar AI Assistant")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 5000)))
    parser.add_argument("--minimized", "--tray", dest="start_minimized", action="store_true")
    parser.add_argument("--open", dest="open_dashboard", action="store_true")
    parser.add_argument("--test-orb", action="store_true")
    args, _unknown = parser.parse_known_args()

    from pulsar.host.__main__ import run_host, run_standalone_orb_tray_test
    if args.test_orb:
        run_standalone_orb_tray_test(port=args.port)
    else:
        # In standalone desktop app mode, clicking Pulsar.exe opens Dashboard by default unless --tray passed
        run_host(port=args.port, start_dashboard=not args.start_minimized)


def _log_fatal_crash(exc: BaseException):
    """Writes uncaught frozen-mode tracebacks to %LOCALAPPDATA%\\Pulsar\\logs\\pulsar_crash.log."""
    import traceback
    import datetime
    tb_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    role = "core" if "--core-subprocess" in sys.argv else "host"
    try:
        local_app = os.environ.get("LOCALAPPDATA") or str(Path.home())
        log_dir = Path(local_app) / "Pulsar" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        crash_file = log_dir / "pulsar_crash.log"
        with crash_file.open("a", encoding="utf-8") as f:
            f.write(f"\n=== [{datetime.datetime.now().isoformat()}] FATAL CRASH ({role}, PID={os.getpid()}) ===\n")
            f.write(tb_text)
    except Exception:
        pass
    try:
        if sys.stderr is not None:
            sys.stderr.write(tb_text)
            sys.stderr.flush()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as _fatal_err:
        _log_fatal_crash(_fatal_err)
        sys.exit(1)
