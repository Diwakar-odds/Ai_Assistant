"""
Action Chain & Executive Orchestration REST API (`/api/chains/*`, `/api/executive/stop`).
Unifies ExecutiveBrain, ChainOfActionsManager, TaskChainOrchestrator, and
PersistentProgressTracker behind a single canonical DTO and live WebSocket bridge.
"""

from __future__ import annotations

import inspect
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

from .common import (
    get_socketio,
    jwt_required,
    logger,
    run_async,
    sanitize_command,
    validate_input,
)

chain_bp = Blueprint("chain", __name__)

try:
    from ai_assistant.core.chain_of_actions_manager import ChainOfActionsManager, get_chain_manager
    from ai_assistant.core.progress_tracker import get_progress_tracker
    MULTI_AGENT_AVAILABLE = True
except ImportError as e:
    MULTI_AGENT_AVAILABLE = False
    logger.warning(f"Chain/Orchestration system not available in chain_routes: {e}")

_optimizer_lock = threading.Lock()
_chain_optimizer = None
_progress_lock = threading.Lock()
_progress_subscribed = False


def _get_chain_optimizer():
    global _chain_optimizer
    with _optimizer_lock:
        if _chain_optimizer is None:
            try:
                from ai_assistant.core.chain_optimizer import ChainOptimizer
                _chain_optimizer = ChainOptimizer()
            except Exception as exc:
                logger.warning(f"ChainOptimizer unavailable: {exc}")
                return None
        return _chain_optimizer


def _emit_chain_ws(chain_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    try:
        try:
            from websockets import broadcast_chain_progress
        except ImportError:
            from backend.websockets import broadcast_chain_progress
        broadcast_chain_progress(chain_id, event_type, payload)
    except Exception as exc:
        logger.debug(f"Chain WS emit skipped ({event_type}): {exc}")


def _map_status_to_ws_event(status_str: str, default: str = "chain.step_completed") -> str:
    s = (status_str or "").lower()
    mapping = {
        "pending": "chain.planned",
        "planning": "chain.planned",
        "created": "chain.planned",
        "executing": "chain.step_completed",
        "running": "chain.step_completed",
        "verifying": "chain.verification_completed",
        "paused": "chain.paused",
        "waiting_confirmation": "chain.paused",
        "completed": "chain.completed",
        "failed": "chain.step_failed",
        "cancelled": "chain.cancelled",
    }
    return mapping.get(s, default)


def _broadcast_chain_progress(progress: Any) -> None:
    """Progress callback bridged from ChainOfActionsManager / ExecutiveBrain to Socket.IO."""
    try:
        payload = progress.to_dict() if hasattr(progress, "to_dict") else (dict(progress) if isinstance(progress, dict) else {"progress": progress})
        chain_id = str(payload.get("chain_id") or payload.get("id") or "")
        status_str = str(payload.get("status") or "").lower()
        event_type = str(payload.get("event") or payload.get("event_type") or "")
        if not event_type:
            cur_idx = payload.get("current_action_index", 0)
            if status_str == "executing" and cur_idx in (0, None):
                event_type = "chain.started"
            else:
                event_type = _map_status_to_ws_event(status_str)

        snapshot = resolve_chain_snapshot(chain_id) if chain_id else None
        if snapshot:
            enriched = {**snapshot, **payload, "chain_id": chain_id, "id": chain_id}
        else:
            enriched = payload
        _emit_chain_ws(chain_id, event_type, enriched)
    except Exception as e:
        logger.error(f"WebSocket chain progress broadcast error: {e}")


def ensure_chain_progress_subscribed() -> None:
    """Idempotently subscribe `_broadcast_chain_progress` to chain managers/brains."""
    global _progress_subscribed
    with _progress_lock:
        if _progress_subscribed:
            return
        subscribed_any = False
        if MULTI_AGENT_AVAILABLE:
            try:
                mgr = get_chain_manager()
                if hasattr(mgr, "subscribe_progress"):
                    mgr.subscribe_progress(_broadcast_chain_progress)
                    subscribed_any = True
                elif hasattr(mgr, "subscribe_events"):
                    mgr.subscribe_events(_broadcast_chain_progress)
                    subscribed_any = True
            except Exception as exc:
                logger.debug(f"Could not subscribe ChainOfActionsManager progress: {exc}")

        try:
            from ai_assistant.core.command_brain import get_executive_brain
            brain = get_executive_brain()
            for attr in ("subscribe_progress", "subscribe_events", "set_progress_callback"):
                fn = getattr(brain, attr, None)
                if callable(fn):
                    fn(_broadcast_chain_progress)
                    subscribed_any = True
                    break
        except Exception as exc:
            logger.debug(f"Could not subscribe ExecutiveBrain progress: {exc}")

        if subscribed_any:
            _progress_subscribed = True


def _coerce_lower_status(raw: Any, default: str = "pending") -> str:
    if raw is None:
        return default
    if hasattr(raw, "value"):
        val = str(raw.value).lower()
    else:
        val = str(raw).lower()
    if "." in val:
        val = val.split(".")[-1]
    if val in ("running", "in_progress"):
        return "executing"
    if val in ("created", "decomposed"):
        return "pending"
    return val or default


def _normalize_action_item(act: Any, idx: int = 0) -> Dict[str, Any]:
    if hasattr(act, "to_dict"):
        d = act.to_dict()
    elif isinstance(act, dict):
        d = dict(act)
    else:
        d = {
            "id": getattr(act, "id", getattr(act, "step_id", f"action_{idx + 1}")),
            "type": getattr(act, "type", getattr(act, "intent", getattr(act, "action_type", "custom"))),
            "description": getattr(act, "description", getattr(act, "original_text", str(act))),
            "status": getattr(act, "status", "pending"),
            "agent_id": getattr(act, "agent_id", None),
            "result": getattr(act, "result", None),
            "error": getattr(act, "error", None),
        }
    atype = d.get("type") or d.get("intent") or "custom"
    if hasattr(atype, "value"):
        atype = atype.value
    raw_status = _coerce_lower_status(d.get("status"), "pending")
    return {
        "id": str(d.get("id") or d.get("step_id") or f"action_{idx + 1}"),
        "type": str(atype),
        "description": str(d.get("description") or d.get("original_text") or ""),
        "agent_id": d.get("agent_id"),
        "status": raw_status,
        "progress": float(d.get("progress", 100.0 if raw_status == "completed" else 0.0) or 0.0),
        "dependencies": list(d.get("dependencies") or []),
        "result": d.get("result") or d.get("result_json"),
        "error": d.get("error"),
        "verified": bool(d.get("verified", False)),
        "verification_result": d.get("verification_result") or d.get("verification"),
    }


def _normalize_chain_dto(obj: Any) -> Optional[Dict[str, Any]]:
    if obj is None:
        return None
    if hasattr(obj, "to_dict"):
        raw = obj.to_dict()
    elif isinstance(obj, dict):
        raw = dict(obj)
    else:
        raw = {
            "chain_id": getattr(obj, "chain_id", getattr(obj, "id", None)),
            "command": getattr(obj, "command", ""),
            "source": getattr(obj, "source", "api"),
            "status": getattr(obj, "status", "executing" if getattr(obj, "is_running", False) else "completed"),
            "progress_percentage": getattr(obj, "progress_percentage", 0.0),
            "current_action_index": getattr(obj, "current_action_index", 0),
            "app_context": getattr(obj, "app_context", None),
            "actions": getattr(obj, "actions", getattr(obj, "steps", [])),
            "created_at": getattr(obj, "created_at", None),
            "started_at": getattr(obj, "started_at", None),
            "completed_at": getattr(obj, "completed_at", None),
            "final_output": getattr(obj, "final_output", None),
            "errors": getattr(obj, "errors", []),
        }
        if hasattr(obj, "orchestrator") and obj.orchestrator is not None:
            orch = obj.orchestrator
            raw.setdefault("total_actions", getattr(orch, "total_steps", len(raw.get("actions") or [])))
            raw.setdefault("actions_completed", getattr(orch, "steps_completed", 0))
            if hasattr(orch, "steps") and not raw["actions"]:
                raw["actions"] = getattr(orch, "steps") or []

    cid = str(raw.get("chain_id") or raw.get("id") or "")
    raw_actions = raw.get("actions") or raw.get("steps") or []
    actions = [_normalize_action_item(a, idx) for idx, a in enumerate(raw_actions)]
    total = int(raw.get("total_actions") if raw.get("total_actions") is not None else len(actions))
    completed = int(
        raw.get("actions_completed")
        if raw.get("actions_completed") is not None
        else sum(1 for a in actions if a["status"] == "completed")
    )
    failed = int(
        raw.get("actions_failed")
        if raw.get("actions_failed") is not None
        else sum(1 for a in actions if a["status"] == "failed")
    )
    status = _coerce_lower_status(raw.get("status"), "pending")
    progress = raw.get("progress_percentage")
    if progress is None:
        progress = raw.get("progress")
    if progress is None:
        if status == "completed":
            progress = 100.0
        elif total > 0:
            progress = round((completed / total) * 100.0, 1)
        else:
            progress = 0.0

    cur_idx = int(raw.get("current_action_index") or 0)
    current_action = raw.get("current_action")
    current_agent = raw.get("current_agent")
    if not current_action and actions:
        running = next((a for a in actions if a["status"] in ("executing", "running")), None)
        pick = running or (actions[cur_idx] if 0 <= cur_idx < len(actions) else actions[-1])
        current_action = pick.get("description")
        current_agent = current_agent or pick.get("agent_id")

    created_at = raw.get("created_at")
    started_at = raw.get("started_at")
    completed_at = raw.get("completed_at")
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()
    if hasattr(started_at, "isoformat"):
        started_at = started_at.isoformat()
    if hasattr(completed_at, "isoformat"):
        completed_at = completed_at.isoformat()

    return {
        "chain_id": cid,
        "id": cid,
        "command": str(raw.get("command") or ""),
        "source": str(raw.get("source") or "api"),
        "status": status,
        "progress_percentage": float(progress),
        "current_action_index": cur_idx,
        "total_actions": total,
        "actions_completed": completed,
        "actions_failed": failed,
        "app_context": raw.get("app_context"),
        "current_action": current_action,
        "current_agent": current_agent,
        "requires_confirmation": bool(raw.get("requires_confirmation", status == "waiting_confirmation")),
        "actions": actions,
        "steps": actions,
        "created_at": created_at,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": raw.get("duration_seconds", raw.get("duration")),
        "final_output": raw.get("final_output") or raw.get("results_json"),
        "errors": list(raw.get("errors") or ([raw["error"]] if raw.get("error") else [])),
    }


def resolve_chain_snapshot(chain_id: str) -> Optional[Dict[str, Any]]:
    """Unified chain lookup across ChainOfActionsManager, ExecutiveBrain, and ProgressTracker."""
    if not chain_id:
        return None
    if MULTI_AGENT_AVAILABLE:
        try:
            mgr = get_chain_manager()
            ch = mgr.get_chain(chain_id)
            if ch is not None:
                return _normalize_chain_dto(ch)
        except Exception:
            pass

    try:
        from ai_assistant.core.command_brain import get_executive_brain
        brain = get_executive_brain()
        active_map = getattr(brain, "_active_chains", {}) or {}
        if chain_id in active_map:
            return _normalize_chain_dto(active_map[chain_id])
        completed_map = getattr(brain, "_completed_chains", {}) or {}
        if chain_id in completed_map:
            return _normalize_chain_dto(completed_map[chain_id])
    except Exception:
        pass

    if MULTI_AGENT_AVAILABLE:
        try:
            tracker = get_progress_tracker()
            details = tracker.get_chain_details(chain_id) if hasattr(tracker, "get_chain_details") else None
            if details:
                return _normalize_chain_dto(details)
        except Exception:
            pass

    return None


def list_active_chains_dto() -> List[Dict[str, Any]]:
    """Collect deduplicated active chains across ChainOfActionsManager and ExecutiveBrain."""
    merged: Dict[str, Dict[str, Any]] = {}
    if MULTI_AGENT_AVAILABLE:
        try:
            mgr = get_chain_manager()
            for cid, ch in (getattr(mgr, "active_chains", {}) or {}).items():
                dto = _normalize_chain_dto(ch)
                if dto:
                    merged[cid] = dto
        except Exception:
            pass

    try:
        from ai_assistant.core.command_brain import get_executive_brain
        brain = get_executive_brain()
        for cid, ch in (getattr(brain, "_active_chains", {}) or {}).items():
            if cid not in merged:
                dto = _normalize_chain_dto(ch)
                if dto:
                    merged[cid] = dto
    except Exception:
        pass

    return list(merged.values())


def _check_chain_safety_gate(command: str, confirmed: bool = False) -> Optional[Dict[str, Any]]:
    """Verify settings_manager permissions and Tier-3 confirmation for risky chains."""
    lower = (command or "").lower()
    if any(w in lower for w in ("shutdown", "shut down", "restart computer", "reboot", "sleep pc", "lock pc")):
        try:
            from settings_manager import is_system_control_allowed
            if not is_system_control_allowed():
                return {
                    "blocked": True,
                    "success": False,
                    "error": "System control commands are disabled by your Security -> Permissions settings.",
                }
        except Exception:
            pass

    if confirmed:
        return None

    is_tier3 = any(
        kw in lower
        for kw in (
            "send whatsapp", "whatsapp message", "send email", "email to",
            "send message", "message bhejo", "shutdown", "shut down",
            "restart computer", "reboot", "delete file", "delete all",
            "remove file", "format drive", "end call",
        )
    )
    if is_tier3:
        try:
            try:
                from agent_brain import get_agent_brain
            except ImportError:
                from backend.agent_brain import get_agent_brain
            brain = get_agent_brain()
            gated = brain._create_pending_confirmation(
                command,
                "action_chain",
                "execute_chain",
                {"command": command, "confirmed": True},
                {"summary": f"execute chain: {command[:120]}"},
            )
            return {"gated": True, **gated}
        except Exception:
            action_id = f"act_{int(time.time() * 1000)}"
            return {
                "gated": True,
                "success": True,
                "requires_confirmation": True,
                "action_id": action_id,
                "response": f"Please confirm before running chain: {command[:120]}",
                "card": {
                    "type": "confirmation",
                    "action_id": action_id,
                    "title": "⚠️ Confirmation Required",
                    "body": command[:120],
                    "actions": ["Confirm", "Cancel"],
                },
            }
    return None


def _launch_manager_chain_thread(chain_id: str) -> None:
    """Execute a ChainOfActionsManager chain in a guarded background thread."""
    ensure_chain_progress_subscribed()

    def run_execute():
        try:
            mgr = get_chain_manager()
            run_async(mgr.execute_chain(chain_id))
            snap = resolve_chain_snapshot(chain_id)
            if snap:
                ev = _map_status_to_ws_event(snap.get("status", "completed"), "chain.completed")
                _emit_chain_ws(chain_id, ev, snap)
        except Exception as exc:
            logger.error(f"Background chain execution failed ({chain_id}): {exc}", exc_info=True)
            _emit_chain_ws(chain_id, "chain.completed", {
                "chain_id": chain_id,
                "id": chain_id,
                "status": "failed",
                "error": str(exc),
            })

    thread = threading.Thread(target=run_execute, daemon=True)
    thread.start()


def _cancel_chain_everywhere(chain_id: str) -> tuple[bool, Optional[Dict[str, Any]]]:
    """Cancel a chain cleanly across ChainOfActionsManager, ExecutiveBrain, and ProgressTracker."""
    found = False
    if MULTI_AGENT_AVAILABLE:
        try:
            from ai_assistant.core.action_chain_models import ChainStatus
            mgr = get_chain_manager()
            if chain_id in mgr.active_chains:
                found = True
                if hasattr(mgr, "cancel_chain"):
                    mgr.cancel_chain(chain_id)
                else:
                    ch = mgr.active_chains.pop(chain_id)
                    ch.status = ChainStatus.CANCELLED
                    ch.completed_at = datetime.now()
                    mgr.completed_chains[chain_id] = ch
                try:
                    get_progress_tracker().save_chain_result(
                        chain_id, ChainStatus.CANCELLED.value, {"cancelled": True}, "Cancelled by user"
                    )
                except Exception:
                    pass
        except Exception as exc:
            logger.warning(f"Manager cancel failed for {chain_id}: {exc}")

    try:
        from ai_assistant.core.command_brain import get_executive_brain
        brain = get_executive_brain()
        active_map = getattr(brain, "_active_chains", {}) or {}
        if chain_id in active_map:
            found = True
            if hasattr(brain, "cancel_chain"):
                brain.cancel_chain(chain_id)
            else:
                mc = active_map.get(chain_id)
                if mc and getattr(mc, "orchestrator", None):
                    mc.orchestrator.emergency_stop()
                if mc is not None:
                    mc.is_running = False
                    if hasattr(mc, "status"):
                        try:
                            from ai_assistant.core.action_chain_models import ChainStatus
                            mc.status = ChainStatus.CANCELLED
                        except Exception:
                            mc.status = "cancelled"
    except Exception as exc:
        logger.warning(f"ExecutiveBrain cancel failed for {chain_id}: {exc}")

    if not found:
        snap = resolve_chain_snapshot(chain_id)
        if snap and snap.get("status") == "cancelled":
            return True, snap
        return False, None

    snap = resolve_chain_snapshot(chain_id) or {"chain_id": chain_id, "id": chain_id, "status": "cancelled"}
    snap["status"] = "cancelled"
    _emit_chain_ws(chain_id, "chain.cancelled", snap)
    return True, snap


# =============================================================================
# REST Routes
# =============================================================================

@chain_bp.route("/api/chains/create", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def create_chain():
    """Create (and optionally execute) an action chain from natural language command."""
    if request.method == "OPTIONS":
        return ("", 204)
    if not MULTI_AGENT_AVAILABLE:
        return jsonify({"success": False, "error": "Multi-Agent / Chain system not available"}), 503

    data = request.get_json(silent=True) or {}
    raw_command = data.get("command", "")
    is_valid, err = validate_input({"command": raw_command}, "command", "command")
    if not is_valid:
        return jsonify({"success": False, "error": err}), 400

    command = sanitize_command(raw_command)
    if not command:
        return jsonify({"success": False, "error": "Command is required"}), 400

    source = str(data.get("source") or "api")
    auto_execute = bool(data.get("auto_execute", True))
    wait = bool(data.get("wait", False))
    confirmed = bool(data.get("confirmed", False))

    gate = _check_chain_safety_gate(command, confirmed=confirmed)
    if gate:
        if gate.get("blocked"):
            return jsonify(gate), 403
        return jsonify(gate), 200

    try:
        ensure_chain_progress_subscribed()

        if not auto_execute:
            mgr = get_chain_manager()
            chain = run_async(mgr.create_chain(command, source=source))
            dto = _normalize_chain_dto(chain) or {"chain_id": chain.chain_id, "id": chain.chain_id}
            _emit_chain_ws(dto["chain_id"], "chain.planned", dto)
            return jsonify({
                "success": True,
                "message": "Action chain created",
                "action_taken": "created",
                "chain": dto,
                **dto,
            }), 200

        if wait:
            from ai_assistant.integrations.orchestrator_integration import process_with_orchestrator
            sig = inspect.signature(process_with_orchestrator)
            kwargs: Dict[str, Any] = {}
            if "wait" in sig.parameters:
                kwargs["wait"] = True
            if "timeout" in sig.parameters:
                kwargs["timeout"] = float(data.get("timeout", 30.0) or 30.0)
            if "provider" in sig.parameters and data.get("provider"):
                kwargs["provider"] = data.get("provider")
            if "model" in sig.parameters and data.get("model"):
                kwargs["model"] = data.get("model")
            if "offline_mode" in sig.parameters and "offline_mode" in data:
                kwargs["offline_mode"] = bool(data.get("offline_mode"))

            orch_res = process_with_orchestrator(command, dict(data.get("context") or {}), **kwargs)
            cid = orch_res.get("chain_id")
            snap = resolve_chain_snapshot(cid) if cid else None
            payload = {**(snap or {}), **orch_res}
            if cid and cid not in payload:
                payload["chain_id"] = cid
            payload.setdefault("id", cid)
            payload.setdefault("command", command)
            ok = bool(orch_res.get("success", False))
            return jsonify(payload), (200 if ok else 500)

        from ai_assistant.core.command_brain import get_executive_brain
        brain = get_executive_brain()
        brain_sig = inspect.signature(brain.receive_command)
        extra_kw: Dict[str, Any] = {}
        if "context" in brain_sig.parameters and data.get("context"):
            extra_kw["context"] = data.get("context")
        brain_response = brain.receive_command(command, source=source, **extra_kw)

        cid = getattr(brain_response, "chain_id", None)
        snap = resolve_chain_snapshot(cid) if cid else None
        if not getattr(brain_response, "success", True):
            return jsonify({
                "success": False,
                "status": "error",
                "error": getattr(brain_response, "message", "Failed to start chain"),
                "message": getattr(brain_response, "message", "Failed to start chain"),
                "chain_id": cid,
                "id": cid,
                "command": command,
                "action_taken": getattr(brain_response, "action_taken", "error"),
            }), 400

        if snap:
            _emit_chain_ws(cid, "chain.started", snap)
        return jsonify({
            "success": True,
            "status": (snap or {}).get("status", "executing"),
            "message": getattr(brain_response, "message", "Chain started"),
            "chain_id": cid,
            "id": cid,
            "command": command,
            "action_taken": getattr(brain_response, "action_taken", "started"),
            "chain": snap or {"chain_id": cid, "id": cid, "command": command},
            **(snap or {}),
        }), 200
    except Exception as e:
        logger.error(f"Error creating chain: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@chain_bp.route("/api/chains", methods=["GET", "OPTIONS"])
@chain_bp.route("/api/chains/active", methods=["GET", "OPTIONS"])
@jwt_required(optional=True)
def get_active_chains():
    """List currently active chains across ExecutiveBrain and ChainOfActionsManager."""
    if request.method == "OPTIONS":
        return ("", 204)
    if not MULTI_AGENT_AVAILABLE:
        return jsonify({"success": False, "error": "Multi-Agent System not available", "chains": []}), 503
    try:
        ensure_chain_progress_subscribed()
        chains = list_active_chains_dto()
        include_completed = str(request.args.get("include_completed", "")).lower() in ("1", "true", "yes")
        if include_completed:
            seen = {c["chain_id"] for c in chains}
            for item in get_progress_tracker().get_recent_chains(limit=10) or []:
                dto = _normalize_chain_dto(item)
                if dto and dto["chain_id"] not in seen:
                    chains.append(dto)
        return jsonify({
            "success": True,
            "chains": chains,
            "total": len(chains),
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        logger.error(f"Error listing active chains: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e), "chains": []}), 500


@chain_bp.route("/api/chains/<chain_id>/execute", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def execute_chain(chain_id: str):
    """Execute a created chain."""
    if request.method == "OPTIONS":
        return ("", 204)
    if not MULTI_AGENT_AVAILABLE:
        return jsonify({"success": False, "error": "Multi-Agent System not available"}), 503

    try:
        mgr = get_chain_manager()
        chain = mgr.get_chain(chain_id)
        if chain is None:
            snap = resolve_chain_snapshot(chain_id)
            if not snap:
                return jsonify({"success": False, "error": "Chain not found"}), 404
            return jsonify({
                "success": True,
                "status": snap.get("status", "executing"),
                "chain_id": chain_id,
                "id": chain_id,
                "message": "Chain is managed by ExecutiveBrain",
                **snap,
            })

        data = request.get_json(silent=True) or {}
        wait = bool(data.get("wait", False))
        ensure_chain_progress_subscribed()
        _emit_chain_ws(chain_id, "chain.started", _normalize_chain_dto(chain) or {"chain_id": chain_id, "status": "executing"})

        if wait:
            run_async(mgr.execute_chain(chain_id))
            snap = resolve_chain_snapshot(chain_id) or {"chain_id": chain_id, "status": "completed"}
            return jsonify({"success": snap.get("status") != "failed", **snap})

        _launch_manager_chain_thread(chain_id)
        return jsonify({
            "success": True,
            "status": "executing",
            "chain_id": chain_id,
            "id": chain_id,
            "message": "Chain execution started",
        })
    except Exception as e:
        logger.error(f"Error executing chain '{chain_id}': {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@chain_bp.route("/api/chains/<chain_id>/pause", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def pause_chain(chain_id: str):
    """Pause a running action chain."""
    if request.method == "OPTIONS":
        return ("", 204)
    if not MULTI_AGENT_AVAILABLE:
        return jsonify({"success": False, "error": "Multi-Agent System not available"}), 503

    try:
        found = False
        mgr = get_chain_manager()
        if chain_id in mgr.active_chains:
            found = True
            if hasattr(mgr, "pause_chain"):
                mgr.pause_chain(chain_id)
            else:
                from ai_assistant.core.action_chain_models import ChainStatus
                paused_val = getattr(ChainStatus, "PAUSED", ChainStatus.WAITING_CONFIRMATION)
                mgr.active_chains[chain_id].status = paused_val

        try:
            from ai_assistant.core.command_brain import get_executive_brain
            brain = get_executive_brain()
            active_map = getattr(brain, "_active_chains", {}) or {}
            if chain_id in active_map:
                found = True
                if hasattr(brain, "pause_chain"):
                    brain.pause_chain(chain_id)
                else:
                    mc = active_map[chain_id]
                    if getattr(mc, "orchestrator", None):
                        mc.orchestrator.pause()
        except Exception as exc:
            logger.debug(f"ExecutiveBrain pause note: {exc}")

        if not found:
            return jsonify({"success": False, "error": "Chain not found or not active"}), 404

        snap = resolve_chain_snapshot(chain_id) or {"chain_id": chain_id, "id": chain_id, "status": "paused"}
        snap["status"] = "paused"
        _emit_chain_ws(chain_id, "chain.paused", snap)
        return jsonify({"success": True, **snap})
    except Exception as e:
        logger.error(f"Error pausing chain '{chain_id}': {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@chain_bp.route("/api/chains/<chain_id>/cancel", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def cancel_chain(chain_id: str):
    """Cancel a running or queued chain cleanly across all stores."""
    if request.method == "OPTIONS":
        return ("", 204)
    if not MULTI_AGENT_AVAILABLE:
        return jsonify({"success": False, "error": "Multi-Agent System not available"}), 503

    try:
        found, snap = _cancel_chain_everywhere(chain_id)
        if not found:
            return jsonify({"success": False, "error": "Chain not found or already completed"}), 404
        return jsonify({"success": True, "status": "cancelled", "chain_id": chain_id, "id": chain_id, **(snap or {})})
    except Exception as e:
        logger.error(f"Error cancelling chain '{chain_id}': {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@chain_bp.route("/api/chains/optimize", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def optimize_chain():
    """Optimize a chain plan based on historical execution."""
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    plan = data.get("plan", [])

    optimizer = _get_chain_optimizer()
    if optimizer is None:
        return jsonify({"success": False, "error": "ChainOptimizer not available"}), 503

    try:
        optimized_plan = optimizer.optimize_plan(plan)
        success_rate = optimizer.predict_success_rate(optimized_plan)
        return jsonify({
            "success": True,
            "status": "success",
            "optimized_plan": optimized_plan,
            "predicted_success_rate": success_rate,
        })
    except Exception as e:
        logger.error(f"Error optimizing chain: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@chain_bp.route("/api/chains/<chain_id>/resume", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def resume_chain(chain_id: str):
    """Resume a paused/waiting chain with optional user input/confirmation, or cancel."""
    if request.method == "OPTIONS":
        return ("", 204)
    if not MULTI_AGENT_AVAILABLE:
        return jsonify({"success": False, "error": "Multi-Agent System not available"}), 503

    data = request.get_json(silent=True) or {}
    user_input = data.get("input") if "input" in data else data.get("user_input")
    action = str(data.get("action") or "proceed").lower()

    try:
        if action == "cancel":
            found, snap = _cancel_chain_everywhere(chain_id)
            if not found:
                return jsonify({"success": False, "error": "Chain not found or already completed"}), 404
            return jsonify({"success": True, "status": "cancelled", "message": "Chain cancelled by user", "chain_id": chain_id, **(snap or {})})

        found = False
        mgr = get_chain_manager()
        ch = mgr.active_chains.get(chain_id)
        if ch is not None:
            found = True
            if hasattr(mgr, "resume_chain"):
                sig = inspect.signature(mgr.resume_chain)
                kw = {}
                if "user_input" in sig.parameters:
                    kw["user_input"] = user_input
                if "confirmed" in sig.parameters:
                    kw["confirmed"] = bool(data.get("confirmed", True))
                res = mgr.resume_chain(chain_id, **kw)
                if inspect.isawaitable(res):
                    run_async(res)
            else:
                from ai_assistant.core.action_chain_models import ChainStatus
                ch.status = ChainStatus.EXECUTING
                if user_input is not None and isinstance(getattr(ch, "context", None), dict):
                    ch.context["user_input"] = user_input

        try:
            from ai_assistant.core.command_brain import get_executive_brain
            brain = get_executive_brain()
            active_map = getattr(brain, "_active_chains", {}) or {}
            if chain_id in active_map:
                found = True
                if hasattr(brain, "resume_chain"):
                    brain.resume_chain(chain_id)
                else:
                    mc = active_map[chain_id]
                    if getattr(mc, "orchestrator", None):
                        mc.orchestrator.resume()
        except Exception as exc:
            logger.debug(f"ExecutiveBrain resume note: {exc}")

        if not found:
            return jsonify({"success": False, "error": "Chain not found or already completed"}), 404

        snap = resolve_chain_snapshot(chain_id) or {"chain_id": chain_id, "id": chain_id, "status": "executing"}
        snap["status"] = "executing"
        _emit_chain_ws(chain_id, "chain.resumed", snap)
        return jsonify({
            "success": True,
            "status": "executing",
            "chain_id": chain_id,
            "id": chain_id,
            "message": "Chain resumed successfully",
            **snap,
        })
    except Exception as e:
        logger.error(f"Error resuming chain '{chain_id}': {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@chain_bp.route("/api/chains/<chain_id>", methods=["GET", "OPTIONS"])
@jwt_required(optional=True)
def get_chain_status(chain_id: str):
    """Get unified status of an action chain from active stores or history DB."""
    if request.method == "OPTIONS":
        return ("", 204)
    if not MULTI_AGENT_AVAILABLE:
        return jsonify({"success": False, "error": "Multi-Agent System not available"}), 503

    try:
        dto = resolve_chain_snapshot(chain_id)
        if not dto:
            return jsonify({"success": False, "error": "Chain not found"}), 404
        return jsonify({"success": True, **dto})
    except Exception as e:
        logger.error(f"Error getting chain status '{chain_id}': {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@chain_bp.route("/api/chains/history", methods=["GET", "OPTIONS"])
@jwt_required(optional=True)
def get_chain_history():
    """Get execution history of action chains."""
    if request.method == "OPTIONS":
        return ("", 204)
    if not MULTI_AGENT_AVAILABLE:
        return jsonify({"success": False, "error": "Multi-Agent System not available", "chains": []}), 503

    try:
        limit = request.args.get("limit", default=20, type=int) or 20
        tracker = get_progress_tracker()
        if hasattr(tracker, "list_chains"):
            raw_history = tracker.list_chains(limit=limit)
        else:
            raw_history = tracker.get_recent_chains(limit=limit)

        chains: List[Dict[str, Any]] = []
        seen = set()
        for item in raw_history or []:
            dto = _normalize_chain_dto(item)
            if dto and dto["chain_id"] not in seen:
                seen.add(dto["chain_id"])
                chains.append(dto)

        # Include in-memory completed chains not yet persisted
        try:
            mgr = get_chain_manager()
            for cid, ch in reversed(list((getattr(mgr, "completed_chains", {}) or {}).items())):
                if cid not in seen:
                    dto = _normalize_chain_dto(ch)
                    if dto:
                        seen.add(cid)
                        chains.append(dto)
        except Exception:
            pass

        return jsonify({
            "success": True,
            "chains": chains[:limit],
            "history": chains[:limit],
            "total": len(chains[:limit]),
        })
    except Exception as e:
        logger.error(f"Error fetching chain history: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e), "chains": []}), 500


@chain_bp.route("/api/executive/stop", methods=["GET", "POST", "OPTIONS"])
@chain_bp.route("/api/emergency/stop", methods=["GET", "POST", "OPTIONS"])
def executive_emergency_stop():
    """Global Emergency Stop endpoint for UI and frontend controls."""
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        from ai_assistant.core.emergency_stop import trigger_emergency_stop
        data = request.get_json(silent=True) or {}
        reason = data.get("reason", "Triggered from Web UI / REST")
        active_before = list_active_chains_dto()
        res = trigger_emergency_stop(reason=reason)
        for ch in active_before:
            cid = ch.get("chain_id")
            if cid:
                _emit_chain_ws(cid, "chain.cancelled", {**ch, "status": "cancelled", "reason": reason})
        sio = get_socketio()
        if sio:
            try:
                sio.emit("emergency_stop_confirmed", {"success": True, "result": res, "reason": reason}, namespace="/")
            except Exception:
                pass
        return jsonify({"success": True, "message": "Emergency stop executed", "result": res})
    except Exception as e:
        logger.error(f"Executive stop endpoint error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
