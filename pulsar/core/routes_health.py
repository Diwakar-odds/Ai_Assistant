"""
Pulsar Core - Health, Lifecycle, and Orb Routes

Provides:
- GET  /health   -> Reports core readiness, component matrix, uptime, and PID.
- POST /shutdown -> Authenticated graceful shutdown endpoint.
- GET  /orb      -> Serves static/orb.html for the PySide6 WebEngine overlay.
"""

import os
import time
import logging
import threading
from typing import Dict, Any, Optional
from flask import Blueprint, jsonify, request, send_file, Response, current_app

logger = logging.getLogger("pulsar.core.health")

health_bp = Blueprint("pulsar_health", __name__)

_START_TIME = time.time()
_AUTH_TOKEN: Optional[str] = None
_COMPONENTS: Dict[str, str] = {
    "server": "ready",
    "llm": "warming",
    "stt": "warming",
    "tts": "warming",
    "audio_worker": "warming",
}
_LOCK = threading.Lock()


def configure_security_token(token: Optional[str]):
    """Sets the per-launch security token for this Core instance."""
    global _AUTH_TOKEN
    with _LOCK:
        _AUTH_TOKEN = token.strip() if token else None
    if _AUTH_TOKEN:
        logger.info(f"[Security] Per-launch token configured (length: {len(_AUTH_TOKEN)})")
    else:
        logger.warning("[Security] Running without authentication token (dev mode)")


def set_component_status(component: str, status: str):
    """Updates health status for a specific engine component."""
    with _LOCK:
        _COMPONENTS[component] = status
        logger.info(f"[Health] Component '{component}' -> '{status}'")


def get_overall_status() -> str:
    """Calculates overall readiness from component statuses."""
    with _LOCK:
        statuses = list(_COMPONENTS.values())
        if any(s == "error" for s in statuses):
            return "error"
        if any(s == "warming" for s in statuses):
            return "warming"
        return "ready"


def _extract_token_from_request() -> Optional[str]:
    """Extracts auth token from headers, query params, or JSON body."""
    # 1. Header
    auth_header = request.headers.get("X-Pulsar-Token")
    if auth_header:
        return auth_header.strip()

    # 2. Bearer token in Authorization header
    bearer = request.headers.get("Authorization", "")
    if bearer.startswith("Bearer "):
        return bearer[7:].strip()

    # 3. Query string
    query_token = request.args.get("token")
    if query_token:
        return query_token.strip()

    # 4. JSON body
    if request.is_json:
        try:
            body = request.get_json(silent=True)
            if body and isinstance(body, dict) and "token" in body:
                return str(body["token"]).strip()
        except Exception:
            pass

    return None


@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for Host supervisor.
    Validates token if provided, reports component status.
    """
    overall = get_overall_status()
    req_token = _extract_token_from_request()
    
    with _LOCK:
        token_match = True
        if _AUTH_TOKEN:
            token_match = (req_token == _AUTH_TOKEN) if req_token else False

        components_copy = dict(_COMPONENTS)

    audio_metrics = {}
    try:
        from pulsar.audio.worker import get_audio_worker_metrics
        audio_metrics = get_audio_worker_metrics()
    except Exception:
        pass

    payload = {
        "status": overall,
        "pid": os.getpid(),
        "uptime_sec": round(time.time() - _START_TIME, 2),
        "components": components_copy,
        "audio_metrics": audio_metrics,
        "token_valid": token_match if req_token else None,
    }
    return jsonify(payload), 200


@health_bp.route("/api/orb/state", methods=["GET"])
def api_get_orb_state():
    """Returns current 4D Orb state and audio RMS level."""
    from pulsar.core.orb_state import get_orb_state
    return jsonify(get_orb_state()), 200


@health_bp.route("/shutdown", methods=["POST"])
def shutdown_core():
    """
    Authenticated shutdown endpoint.
    Terminates the Core process after sending HTTP response.
    """
    global _AUTH_TOKEN
    client_token = _extract_token_from_request()

    with _LOCK:
        expected = _AUTH_TOKEN

    if expected:
        if not client_token:
            return jsonify({
                "error": "Unauthorized",
                "message": "Missing shutdown authentication token (X-Pulsar-Token header required)"
            }), 401

        if client_token != expected:
            return jsonify({
                "error": "Forbidden",
                "message": "Invalid authentication token"
            }), 403

    # Stop Audio Worker to release microphone handle immediately
    try:
        from pulsar.audio.worker import stop_core_audio_worker
        stop_core_audio_worker()
    except Exception:
        pass

    logger.warning("[Shutdown] Authenticated shutdown request received. Terminating Core process in 300ms...")

    def _delayed_exit():
        time.sleep(0.3)
        logger.info("[Shutdown] Core terminating now.")
        os._exit(0)

    # In unit tests (TESTING=True), skip hard os._exit(0) to avoid killing test runner
    if not current_app.config.get("TESTING"):
        threading.Thread(target=_delayed_exit, name="DelayedShutdown", daemon=True).start()
    else:
        logger.info("[Shutdown] Running under TESTING=True; simulated exit without os._exit.")

    return jsonify({
        "status": "shutting_down",
        "pid": os.getpid(),
        "message": "Pulsar Core is shutting down cleanly"
    }), 200


@health_bp.route("/orb", methods=["GET"])
def serve_orb_html():
    """Serves static/orb.html for PySide6 WebEngine overlay."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    orb_path = os.path.join(static_dir, "orb.html")

    if not os.path.exists(orb_path):
        return Response("orb.html not found", status=404, mimetype="text/plain")

    response = send_file(orb_path, mimetype="text/html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
