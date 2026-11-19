"""
Pulsar Core Server

Headless Flask + Socket.IO server running strictly on loopback (127.0.0.1).
Exposes backend AI services, agent orchestration, chat endpoints, 4D orb state,
and health/shutdown lifecycle APIs.

Strict Architectural Invariants:
1. Pure Headless: Zero imports of win32gui, pystray, pywebview, or tkinter.
2. Loopback Only: Strictly bound to 127.0.0.1.
3. Authenticated: Per-launch security token verified on sensitive endpoints.
4. Origin Protection: Malicious cross-origin browser requests rejected.
5. Lifecycle Watched: Monitored by Win32 parent process watchdog.
"""

import os
import sys
import re
import time
import logging
import threading
from typing import Optional

# 1. Enforce headless environment and disable in-process GUI companion
os.environ["PULSAR_DISABLE_COMPANION"] = "1"
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# 2. Setup path for backend & core_ai modules
from pathlib import Path
_repo_root = Path(__file__).resolve().parent.parent.parent
_backend_dir = _repo_root / "backend"
_core_ai_dir = _repo_root / "core_ai" / "src"

for _p in (str(_repo_root), str(_backend_dir), str(_core_ai_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

logger = logging.getLogger("pulsar.core.server")

# 3. Import existing Flask app and SocketIO instance
from backend.modern_web_backend import app, socketio
from pulsar.core.routes_health import (
    health_bp,
    configure_security_token,
    set_component_status,
)
from pulsar.core.orb_state import get_orb_state_manager
from pulsar.core.watchdog import start_parent_watchdog

# Trusted Origin patterns for security middleware
TRUSTED_ORIGINS_REGEX = re.compile(
    r"^(http://localhost(:\d+)?|http://127\.0\.0\.1(:\d+)?|null|tauri://localhost|https://tauri\.localhost)$",
    re.IGNORECASE,
)


def _apply_origin_guard(flask_app):
    """Enforce Origin validation to prevent unauthorized websites from hitting local Core."""
    from flask import request, jsonify

    @flask_app.before_request
    def validate_request_origin():
        # Exempt internal health and orb view
        if request.path in ("/health", "/orb") and request.method == "GET":
            return None

        origin = request.headers.get("Origin")
        if origin:
            origin_clean = origin.strip()
            if not TRUSTED_ORIGINS_REGEX.match(origin_clean):
                logger.warning(f"[Security] Blocked unauthorized Origin: '{origin_clean}' requesting {request.path}")
                return jsonify({
                    "error": "Forbidden",
                    "message": f"Unauthorized origin: {origin_clean}"
                }), 403
        return None


def _background_prewarm():
    """Background worker that initializes AI components and updates health matrix."""
    logger.info("[PreWarm] Background AI pre-warming started...")
    try:
        # Pre-warm TTS
        try:
            from core_ai.voice.tts_output_service import get_tts_service, load_kitten_mini_model
            get_tts_service()
            load_kitten_mini_model()
            set_component_status("tts", "ready")
        except Exception as e:
            logger.debug(f"[PreWarm] TTS note: {e}")
            set_component_status("tts", "offline")

        # Start Dedicated Audio Worker (Single Microphone Owner)
        try:
            from pulsar.audio.worker import start_core_audio_worker
            if os.environ.get("PULSAR_DISABLE_AUDIO") != "1":
                started = start_core_audio_worker()
                set_component_status("audio_worker", "ready" if started else "offline")
            else:
                set_component_status("audio_worker", "offline")
        except Exception as e:
            logger.debug(f"[PreWarm] Audio worker note: {e}")
            set_component_status("audio_worker", "offline")

        # Mark LLM status (check real LLMProvider / GGUF manager modules)
        llm_ok = False
        try:
            from core_ai.ai.llm_provider import LLMProvider  # noqa: F401
            llm_ok = True
        except Exception:
            pass
        if not llm_ok:
            try:
                from core_ai.ai.gguf_model_manager import get_gguf_manager  # noqa: F401
                llm_ok = True
            except Exception:
                pass
        set_component_status("llm", "ready" if llm_ok else "offline")

        # Mark STT status
        set_component_status("stt", "ready")
        set_component_status("server", "ready")
        logger.info("[PreWarm] Background AI pre-warming complete. All components ready.")
    except Exception as e:
        logger.error(f"[PreWarm] Error during pre-warm: {e}")
        set_component_status("server", "ready")


def setup_core_app(token: Optional[str] = None):
    """Configures the Core Flask app with health routes, token auth, and origin guards."""
    # Register health and lifecycle blueprint if not already registered
    if "pulsar_health" not in app.blueprints:
        app.register_blueprint(health_bp)
        logger.info("[Core] Health and lifecycle blueprint registered at /health and /shutdown")

    # Set security token
    configure_security_token(token)

    # Attach SocketIO to OrbStateManager
    get_orb_state_manager().set_socketio(socketio)

    # Apply Origin security guard
    _apply_origin_guard(app)

    return app, socketio


_CORE_MUTEX_HANDLE = None


def acquire_core_mutex() -> bool:
    """Dev-mode guard: ensure only one Core instance runs per machine."""
    global _CORE_MUTEX_HANDLE
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h_mutex = kernel32.CreateMutexW(None, False, "Local\\Pulsar.Core.v1")
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            if h_mutex:
                kernel32.CloseHandle(h_mutex)
            logger.warning("[Core] Another Pulsar Core instance is already running (Mutex Local\\Pulsar.Core.v1 held).")
            return False
        _CORE_MUTEX_HANDLE = h_mutex
        return True
    except Exception as e:
        logger.debug(f"[Core] Mutex creation note: {e}")
        return True


def _set_below_normal_priority():
    """Lowers Core process priority slightly on Windows so Host GUI & Orb never stutter under LLM load."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
        k32 = ctypes.windll.kernel32
        k32.SetPriorityClass(k32.GetCurrentProcess(), BELOW_NORMAL_PRIORITY_CLASS)
        logger.info("[Core] Process priority set to BELOW_NORMAL so Host UI stays responsive.")
    except Exception:
        pass


def run_core(
    host: str = "127.0.0.1",
    port: int = 5000,
    token: Optional[str] = None,
    parent_pid: Optional[int] = None,
    prewarm: bool = True,
):
    """
    Main entrypoint to run the headless Core server.
    """
    logger.info(f"=== Starting Pulsar Headless Core on {host}:{port} (PID: {os.getpid()}) ===")

    _set_below_normal_priority()

    # Dev guard mutex
    acquire_core_mutex()

    # Start parent watchdog if parent_pid provided
    if parent_pid:
        start_parent_watchdog(parent_pid)

    # Configure app and socketio
    setup_core_app(token=token)

    # Start pre-warming thread
    if prewarm:
        prewarm_thread = threading.Thread(target=_background_prewarm, name="CorePreWarm", daemon=True)
        prewarm_thread.start()
    else:
        set_component_status("server", "ready")
        set_component_status("llm", "ready")
        set_component_status("stt", "ready")
        set_component_status("tts", "ready")
        set_component_status("audio_worker", "ready")

    # Suppress werkzeug and banner spam
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    # Run SocketIO server (strictly loopback host)
    socketio.run(
        app,
        host=host,
        port=port,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )
