"""
Multi-Agent REST API Blueprint (`/api/agents/*`).
Exposes agent discovery, lifecycle loading, task dispatch/execution,
capability mapping, and task status/cancellation with WebSocket telemetry
and Tier-3 safety gating.
"""

from __future__ import annotations

import inspect
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

from .common import (
    api_logger,
    get_jwt_identity,
    jwt_required,
    limiter,
    logger,
    run_async,
    sanitize_command,
    validate_input,
)

agent_bp = Blueprint("agents", __name__)

_init_lock = threading.RLock()
_registry_singleton = None
_coordinator_singleton = None
_events_subscribed = False

_tasks_lock = threading.RLock()
_agent_tasks: Dict[str, Dict[str, Any]] = {}
_cancel_events: Dict[str, threading.Event] = {}


def _emit_agent_event(event_type: str, data: Dict[str, Any]) -> None:
    """Safely broadcast `agent.*` or `agents_snapshot` via websockets."""
    try:
        try:
            from websockets import broadcast_agent_event
        except ImportError:
            from backend.websockets import broadcast_agent_event
        broadcast_agent_event(event_type, data)
    except Exception as exc:
        logger.debug(f"Agent WebSocket emit skipped ({event_type}): {exc}")


def _coerce_status_str(raw_status: Any) -> str:
    if hasattr(raw_status, "value"):
        val = str(raw_status.value).lower()
    else:
        val = str(raw_status or "idle").lower()
    if val in ("working", "busy", "running"):
        return "busy"
    if val in ("offline", "unloaded"):
        return "offline"
    if val in ("error", "failed"):
        return "error"
    return "idle"


def _on_coordinator_event(event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
    """Bridge MultiAgentCoordinator lifecycle callbacks onto WebSocket + local task table."""
    data = dict(payload or {})
    task_id = data.get("task_id")
    if task_id:
        with _tasks_lock:
            existing = _agent_tasks.get(task_id)
            if existing:
                if event_type == "agent.task_started":
                    existing["status"] = "running"
                elif event_type == "agent.task_completed":
                    existing["status"] = "completed"
                    existing["completed_at"] = datetime.now().isoformat()
                elif event_type == "agent.task_failed":
                    existing["status"] = "failed"
                    existing["completed_at"] = datetime.now().isoformat()
                    if data.get("error"):
                        existing["error"] = data["error"]
    _emit_agent_event(event_type, data)
    if event_type in ("agent.status_changed", "agent.task_started", "agent.task_completed", "agent.task_failed"):
        try:
            _emit_agent_event("agents_snapshot", get_agents_snapshot_payload())
        except Exception:
            pass


def get_agent_registry_and_coordinator():
    """Lazily initialize & cache AgentRegistry and MultiAgentCoordinator."""
    global _registry_singleton, _coordinator_singleton, _events_subscribed
    with _init_lock:
        if _registry_singleton is None:
            try:
                from ai_assistant.agents.registry import get_global_registry
                _registry_singleton = get_global_registry()
            except Exception:
                from ai_assistant.agents.registry import AgentRegistry
                from ai_assistant.agents.loader import AgentLoader

                reg = AgentRegistry()
                if hasattr(AgentLoader, "load_all_agents"):
                    AgentLoader.load_all_agents(registry=reg, eager=False)
                else:
                    AgentLoader.register_agent_definitions(reg)
                _registry_singleton = reg

        if _coordinator_singleton is None:
            try:
                from ai_assistant.core.multi_agent_coordinator import get_multi_agent_coordinator
                _coordinator_singleton = get_multi_agent_coordinator(_registry_singleton)
            except Exception:
                from ai_assistant.core.multi_agent_coordinator import MultiAgentCoordinator
                _coordinator_singleton = MultiAgentCoordinator(_registry_singleton)

        if not _events_subscribed and _coordinator_singleton is not None:
            subscribe_fn = getattr(_coordinator_singleton, "subscribe_events", None)
            if callable(subscribe_fn):
                try:
                    subscribe_fn(_on_coordinator_event)
                    _events_subscribed = True
                except Exception as exc:
                    logger.debug(f"Could not subscribe coordinator events: {exc}")

        return _registry_singleton, _coordinator_singleton


def _synthesize_agents_dto(registry: Any) -> List[Dict[str, Any]]:
    """Convert registry state to unified Agent DTO list, even on pre-Phase2 registries."""
    if registry is None:
        return []
    if hasattr(registry, "list_agents_dto"):
        try:
            items = registry.list_agents_dto()
            if isinstance(items, list):
                return items
        except Exception as exc:
            logger.debug(f"registry.list_agents_dto failed, synthesizing fallback: {exc}")

    dtos: List[Dict[str, Any]] = []
    definitions = getattr(registry, "_agent_definitions", {}) or {}
    loaded_map = getattr(registry, "_agents", {}) or {}
    seen = set()

    for aid, info in definitions.items():
        seen.add(aid)
        inst = loaded_map.get(aid)
        meta = info.get("metadata") if isinstance(info, dict) else {}
        if not isinstance(meta, dict):
            meta = {}
        raw_status = getattr(inst, "status", "idle") if inst is not None else "idle"
        dtos.append({
            "id": aid,
            "name": getattr(inst, "name", None) or meta.get("name") or aid,
            "category": getattr(inst, "category", None) or meta.get("category") or "general",
            "description": getattr(inst, "description", None) or meta.get("description") or "",
            "capabilities": list(getattr(inst, "capabilities", None) or meta.get("capabilities") or []),
            "status": _coerce_status_str(raw_status),
            "loaded": inst is not None,
            "active_tasks": 1 if getattr(inst, "current_task", None) else int(getattr(inst, "active_tasks", 0) or 0),
            "completed_tasks": int(getattr(inst, "completed_tasks", 0) or 0),
            "failed_tasks": int(getattr(inst, "failed_tasks", 0) or 0),
        })

    for aid, inst in loaded_map.items():
        if aid in seen:
            continue
        dtos.append({
            "id": aid,
            "name": getattr(inst, "name", aid),
            "category": getattr(inst, "category", "general"),
            "description": getattr(inst, "description", ""),
            "capabilities": list(getattr(inst, "capabilities", []) or []),
            "status": _coerce_status_str(getattr(inst, "status", "idle")),
            "loaded": True,
            "active_tasks": 1 if getattr(inst, "current_task", None) else int(getattr(inst, "active_tasks", 0) or 0),
            "completed_tasks": int(getattr(inst, "completed_tasks", 0) or 0),
            "failed_tasks": int(getattr(inst, "failed_tasks", 0) or 0),
        })

    return dtos


def get_agents_snapshot_payload() -> Dict[str, Any]:
    """Return full agent roster snapshot DTO shared by REST and WebSockets."""
    registry, _ = get_agent_registry_and_coordinator()
    agents = _synthesize_agents_dto(registry)
    return {
        "success": True,
        "agents": agents,
        "total": len(agents),
        "active_count": sum(1 for a in agents if a.get("loaded")),
        "busy_count": sum(1 for a in agents if a.get("status") == "busy"),
        "timestamp": datetime.now().isoformat(),
    }


def _find_agent_dto(registry: Any, agent_id: str) -> Optional[Dict[str, Any]]:
    if registry is not None and hasattr(registry, "get_agent_dto"):
        try:
            dto = registry.get_agent_dto(agent_id)
            if dto:
                return dto
        except Exception:
            pass
    for item in _synthesize_agents_dto(registry):
        if item.get("id") == agent_id:
            return item
    return None


def _agent_exists(registry: Any, agent_id: str) -> bool:
    if registry is None:
        return False
    defs = getattr(registry, "_agent_definitions", {}) or {}
    loaded = getattr(registry, "_agents", {}) or {}
    return agent_id in defs or agent_id in loaded or _find_agent_dto(registry, agent_id) is not None


def _check_agent_safety_gate(
    command_text: str,
    agent_id: Optional[str],
    params: Dict[str, Any],
    confirmed: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Enforce settings_manager permissions and Tier-3 confirmation gating for
    high-consequence multi-agent actions unless already explicitly confirmed.
    """
    lower = (command_text or "").lower()
    aid = (agent_id or "").lower()

    # Respect user permission toggles
    if aid in ("file-001", "file_01") or any(w in lower for w in ("shutdown", "restart", "reboot", "sleep pc", "lock pc")):
        try:
            from settings_manager import is_system_control_allowed
            if any(w in lower for w in ("shutdown", "restart", "reboot", "sleep pc", "lock pc")) and not is_system_control_allowed():
                return {
                    "blocked": True,
                    "success": False,
                    "error": "System control commands are disabled by your Security -> Permissions settings.",
                }
        except Exception:
            pass

    if confirmed:
        return None

    is_comm_send = (
        aid in ("comm-001", "communication_01", "communication-001")
        and any(w in lower for w in ("send", "whatsapp", "email", "mail", "bhejo", "message", "reply", "tweet", "post"))
    )
    is_destructive_file = (
        any(w in lower for w in ("delete ", "remove ", "wipe ", "erase ", "rm ", "format "))
        and not bool(params.get("dry_run"))
    )
    is_power_control = any(w in lower for w in ("shutdown", "shut down", "restart computer", "reboot", "format drive"))
    is_db_write = (
        aid in ("database-001", "database_01")
        and any(w in lower for w in ("drop ", "truncate ", "delete from ", "alter table ", "update ", "insert into "))
    )

    if is_comm_send or is_destructive_file or is_power_control or is_db_write:
        summary = f"run agent task ({agent_id or 'auto'}): {command_text[:120]}"
        try:
            try:
                from agent_brain import get_agent_brain
            except ImportError:
                from backend.agent_brain import get_agent_brain
            brain = get_agent_brain()
            gated = brain._create_pending_confirmation(
                command_text,
                "multi_agent_task",
                "execute_agent",
                {
                    "command": command_text,
                    "agent_id": agent_id,
                    "params": params,
                    "confirmed": True,
                },
                {"summary": summary},
            )
            return {"gated": True, **gated}
        except Exception:
            action_id = f"act_{int(time.time() * 1000)}"
            return {
                "gated": True,
                "success": True,
                "requires_confirmation": True,
                "action_id": action_id,
                "response": f"Confirmation required to {summary}.",
                "tts": f"Please confirm before I {summary}.",
                "card": {
                    "type": "confirmation",
                    "action_id": action_id,
                    "title": "⚠️ Confirmation Required",
                    "body": summary,
                    "actions": ["Confirm", "Cancel"],
                },
            }
    return None


def _build_task_obj(
    task_id: str,
    description: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
    agent_id: Optional[str] = None,
    capability: Optional[str] = None,
):
    from ai_assistant.agents.models import Task

    sig = inspect.signature(Task)
    kwargs: Dict[str, Any] = {
        "task_id": task_id,
        "description": description,
        "params": params,
    }
    optional_fields = {
        "target_agent_id": agent_id,
        "required_capabilities": [capability] if capability else [],
        "context": context,
    }
    for key, val in optional_fields.items():
        if key in sig.parameters and val is not None:
            kwargs[key] = val
    return Task(**kwargs)


def _normalize_task_result(result: Any, task_id: str, agent_id: Optional[str]) -> Dict[str, Any]:
    if result is None:
        return {
            "success": False,
            "task_id": task_id,
            "agent_id": agent_id,
            "error": "No result returned by agent",
            "data": {},
            "artifacts": [],
            "output_path": None,
            "execution_time": 0.0,
        }
    if isinstance(result, dict):
        data = result.get("data") if isinstance(result.get("data"), dict) else result
        return {
            "success": bool(result.get("success", True)),
            "task_id": task_id,
            "agent_id": result.get("agent_id") or agent_id,
            "agent_name": result.get("agent_name"),
            "data": data,
            "output": result.get("output") or (data.get("output") if isinstance(data, dict) else None) or (data.get("summary") if isinstance(data, dict) else None) or (data.get("text") if isinstance(data, dict) else None),
            "output_path": result.get("output_path"),
            "artifacts": result.get("artifacts") or [],
            "error": result.get("error"),
            "execution_time": float(result.get("execution_time") or 0.0),
        }

    data = getattr(result, "data", {}) or {}
    if not isinstance(data, dict):
        data = {"raw": data}
    output_text = (
        data.get("output")
        or data.get("summary")
        or data.get("text")
        or data.get("response")
        or data.get("message")
        or data.get("result")
        or getattr(result, "output_path", None)
    )
    resolved_agent_id = getattr(result, "agent_id", None) or agent_id
    return {
        "success": bool(getattr(result, "success", False)),
        "task_id": task_id,
        "agent_id": resolved_agent_id,
        "agent_name": getattr(result, "agent_name", None),
        "data": data,
        "output": str(output_text) if output_text is not None else "",
        "output_path": getattr(result, "output_path", None),
        "artifacts": list(getattr(result, "artifacts", []) or []),
        "error": getattr(result, "error", None),
        "execution_time": float(getattr(result, "execution_time", 0.0) or 0.0),
    }


def _execute_coordinator_sync(
    registry: Any,
    coordinator: Any,
    task_id: str,
    description: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
    agent_id: Optional[str] = None,
    capability: Optional[str] = None,
) -> Dict[str, Any]:
    """Run an agent or coordinated task synchronously using the best available coordinator method."""
    cancel_evt = _cancel_events.get(task_id)
    if cancel_evt and cancel_evt.is_set():
        return {
            "success": False,
            "task_id": task_id,
            "agent_id": agent_id,
            "error": "Task cancelled before execution",
            "data": {},
            "artifacts": [],
            "output_path": None,
            "execution_time": 0.0,
        }

    task_obj = _build_task_obj(task_id, description, params, context, agent_id=agent_id, capability=capability)

    async def _runner():
        if agent_id:
            if hasattr(coordinator, "execute_agent"):
                return await coordinator.execute_agent(agent_id, task_obj)
            if hasattr(coordinator, "execute_step"):
                return await coordinator.execute_step(
                    description,
                    params=params,
                    preferred_agent_id=agent_id,
                    capability=capability,
                    chain_context=context,
                )
            agent = registry.get_agent(agent_id)
            if agent is None:
                raise ValueError(f"Agent '{agent_id}' could not be loaded")
            return await agent.execute(task_obj)

        if hasattr(coordinator, "execute_step"):
            return await coordinator.execute_step(
                description,
                params=params,
                preferred_agent_id=agent_id,
                capability=capability,
                chain_context=context,
            )
        if hasattr(coordinator, "coordinate_task"):
            return await coordinator.coordinate_task(task_obj)
        raise RuntimeError("MultiAgentCoordinator exposes neither execute_step nor coordinate_task")

    raw_result = run_async(_runner())
    return _normalize_task_result(raw_result, task_id, agent_id)


def _run_and_record_task(
    task_id: str,
    registry: Any,
    coordinator: Any,
    description: str,
    params: Dict[str, Any],
    context: Dict[str, Any],
    agent_id: Optional[str],
    capability: Optional[str],
) -> Dict[str, Any]:
    started_at = datetime.now().isoformat()
    with _tasks_lock:
        record = _agent_tasks.setdefault(task_id, {})
        record.update({
            "task_id": task_id,
            "agent_id": agent_id,
            "description": description,
            "status": "running",
            "started_at": started_at,
        })

    _emit_agent_event("agent.task_started", {
        "task_id": task_id,
        "agent_id": agent_id,
        "description": description,
        "status": "running",
    })

    try:
        normalized = _execute_coordinator_sync(
            registry, coordinator, task_id, description, params, context,
            agent_id=agent_id, capability=capability,
        )
        cancel_evt = _cancel_events.get(task_id)
        is_cancelled = bool(cancel_evt and cancel_evt.is_set())
        final_status = "cancelled" if is_cancelled else ("completed" if normalized.get("success") else "failed")

        with _tasks_lock:
            record = _agent_tasks[task_id]
            record.update({
                "agent_id": normalized.get("agent_id") or agent_id,
                "agent_name": normalized.get("agent_name"),
                "status": final_status,
                "success": bool(normalized.get("success")) and not is_cancelled,
                "result": normalized.get("data"),
                "output": normalized.get("output"),
                "output_path": normalized.get("output_path"),
                "artifacts": normalized.get("artifacts", []),
                "error": normalized.get("error"),
                "execution_time": normalized.get("execution_time", 0.0),
                "completed_at": datetime.now().isoformat(),
            })
            snapshot = dict(record)

        ev_name = "agent.task_completed" if snapshot["status"] == "completed" else "agent.task_failed"
        _emit_agent_event(ev_name, snapshot)
        _emit_agent_event("agents_snapshot", get_agents_snapshot_payload())
        return snapshot
    except Exception as exc:
        logger.error(f"Agent task {task_id} failed: {exc}", exc_info=True)
        with _tasks_lock:
            record = _agent_tasks[task_id]
            record.update({
                "status": "failed",
                "success": False,
                "error": str(exc),
                "completed_at": datetime.now().isoformat(),
            })
            snapshot = dict(record)
        _emit_agent_event("agent.task_failed", snapshot)
        _emit_agent_event("agents_snapshot", get_agents_snapshot_payload())
        return snapshot


# =============================================================================
# REST Endpoints
# =============================================================================

@agent_bp.route("/api/agents", methods=["GET", "OPTIONS"])
@jwt_required(optional=True)
def api_list_agents():
    """List all registered specialized agents with live status and task metrics."""
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        return jsonify(get_agents_snapshot_payload())
    except Exception as exc:
        logger.error(f"Failed to list agents: {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc), "agents": []}), 500


@agent_bp.route("/api/agents/capabilities", methods=["GET", "OPTIONS"])
@jwt_required(optional=True)
def api_agent_capabilities():
    """Return capability-to-agent discovery map."""
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        registry, _ = get_agent_registry_and_coordinator()
        if hasattr(registry, "get_capabilities_map"):
            cap_map = registry.get_capabilities_map()
        else:
            cap_map = {}
            for item in _synthesize_agents_dto(registry):
                for cap in item.get("capabilities", []):
                    cap_map.setdefault(cap, []).append(item["id"])
        return jsonify({
            "success": True,
            "capabilities": cap_map,
            "total_capabilities": len(cap_map),
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as exc:
        logger.error(f"Failed to get agent capabilities: {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc), "capabilities": {}}), 500


@agent_bp.route("/api/agents/<agent_id>", methods=["GET", "OPTIONS"])
@jwt_required(optional=True)
def api_get_agent_detail(agent_id: str):
    """Return details, metrics, and recent tasks for one agent."""
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        registry, _ = get_agent_registry_and_coordinator()
        dto = _find_agent_dto(registry, agent_id)
        if not dto:
            return jsonify({"success": False, "error": f"Agent '{agent_id}' not found"}), 404

        with _tasks_lock:
            recent = [
                dict(t) for t in reversed(list(_agent_tasks.values()))
                if t.get("agent_id") == agent_id
            ][:20]

        return jsonify({
            "success": True,
            "agent": dto,
            "recent_tasks": recent,
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as exc:
        logger.error(f"Failed to inspect agent '{agent_id}': {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@agent_bp.route("/api/agents/<agent_id>/load", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def api_load_agent(agent_id: str):
    """Explicitly trigger lazy loading / instantiation of an agent."""
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        registry, _ = get_agent_registry_and_coordinator()
        if not _agent_exists(registry, agent_id):
            return jsonify({"success": False, "error": f"Agent '{agent_id}' not found"}), 404

        inst = registry.get_agent(agent_id)
        if inst is None:
            return jsonify({"success": False, "error": f"Agent '{agent_id}' failed to load"}), 500

        dto = _find_agent_dto(registry, agent_id)
        _emit_agent_event("agent.status_changed", {
            "agent_id": agent_id,
            "status": (dto or {}).get("status", "idle"),
            "loaded": True,
        })
        _emit_agent_event("agents_snapshot", get_agents_snapshot_payload())
        return jsonify({"success": True, "agent": dto})
    except Exception as exc:
        logger.error(f"Failed to load agent '{agent_id}': {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


def _handle_agent_dispatch_request(forced_agent_id: Optional[str] = None):
    data = request.get_json(silent=True) or {}
    raw_cmd = data.get("command") or data.get("description") or data.get("task") or ""
    if not isinstance(raw_cmd, str) or not raw_cmd.strip():
        return jsonify({"success": False, "error": "command or description is required"}), 400

    valid, err = validate_input({"command": raw_cmd}, "command", "command")
    if not valid:
        return jsonify({"success": False, "error": err}), 400

    command_text = sanitize_command(raw_cmd)
    agent_id = forced_agent_id or data.get("agent_id")
    capability = data.get("capability")
    params = dict(data.get("params") or {})
    context = dict(data.get("context") or {})
    confirmed = bool(data.get("confirmed", False))
    run_async_mode = bool(data.get("async", False))

    if data.get("provider"):
        context["provider"] = data.get("provider")
        params.setdefault("provider", data.get("provider"))
    if data.get("model"):
        context["model"] = data.get("model")
        params.setdefault("model", data.get("model"))
    if "offline_mode" in data:
        context["offline_mode"] = bool(data.get("offline_mode"))
        params.setdefault("offline_mode", bool(data.get("offline_mode")))

    registry, coordinator = get_agent_registry_and_coordinator()
    if agent_id and not _agent_exists(registry, agent_id):
        return jsonify({"success": False, "error": f"Agent '{agent_id}' not found"}), 404

    gate = _check_agent_safety_gate(command_text, agent_id, params, confirmed=confirmed)
    if gate:
        if gate.get("blocked"):
            return jsonify(gate), 403
        return jsonify(gate), 200

    task_id = f"task_{uuid.uuid4().hex[:12]}"
    created_at = datetime.now().isoformat()
    with _tasks_lock:
        _cancel_events[task_id] = threading.Event()
        _agent_tasks[task_id] = {
            "task_id": task_id,
            "agent_id": agent_id,
            "description": command_text,
            "capability": capability,
            "params": params,
            "status": "pending",
            "created_at": created_at,
            "user": get_jwt_identity() or "anonymous",
        }

    api_logger.info(f"Agent task queued: {task_id} (agent={agent_id or 'auto'}, async={run_async_mode})")

    if run_async_mode:
        t = threading.Thread(
            target=_run_and_record_task,
            args=(task_id, registry, coordinator, command_text, params, context, agent_id, capability),
            daemon=True,
        )
        t.start()
        return jsonify({
            "success": True,
            "task_id": task_id,
            "agent_id": agent_id,
            "status": "running",
            "async": True,
            "message": "Agent task started",
            "created_at": created_at,
        }), 202

    snapshot = _run_and_record_task(
        task_id, registry, coordinator, command_text, params, context, agent_id, capability
    )
    status_code = 200 if snapshot.get("success") else 500
    response_body = {
        **snapshot,
        "result": {
            "success": snapshot.get("success", False),
            "data": snapshot.get("result") or {},
            "output": snapshot.get("output"),
            "output_path": snapshot.get("output_path"),
            "artifacts": snapshot.get("artifacts", []),
            "error": snapshot.get("error"),
        },
        "response": snapshot.get("output") or (snapshot.get("error") or ""),
    }
    return jsonify(response_body), status_code


@agent_bp.route("/api/agents/dispatch", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_dispatch_agent():
    """Auto-route or dispatch a task through MultiAgentCoordinator."""
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        return _handle_agent_dispatch_request(forced_agent_id=None)
    except Exception as exc:
        logger.error(f"Agent dispatch error: {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@agent_bp.route("/api/agents/<agent_id>/execute", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_execute_specific_agent(agent_id: str):
    """Execute a task directly on the specified agent."""
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        return _handle_agent_dispatch_request(forced_agent_id=agent_id)
    except Exception as exc:
        logger.error(f"Agent '{agent_id}' execute error: {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@agent_bp.route("/api/agents/tasks", methods=["GET", "OPTIONS"])
@jwt_required(optional=True)
def api_list_agent_tasks():
    """List active and recent agent tasks."""
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        agent_filter = request.args.get("agent_id")
        status_filter = request.args.get("status")
        limit = request.args.get("limit", default=50, type=int) or 50

        merged: Dict[str, Dict[str, Any]] = {}
        try:
            _, coordinator = get_agent_registry_and_coordinator()
            if hasattr(coordinator, "list_tasks"):
                for item in coordinator.list_tasks() or []:
                    tid = item.get("task_id")
                    if tid:
                        merged[tid] = dict(item)
        except Exception:
            pass

        with _tasks_lock:
            for tid, rec in _agent_tasks.items():
                merged[tid] = dict(rec)

        tasks = list(merged.values())
        tasks.sort(key=lambda t: t.get("created_at") or t.get("started_at") or "", reverse=True)
        if agent_filter:
            tasks = [t for t in tasks if t.get("agent_id") == agent_filter]
        if status_filter:
            tasks = [t for t in tasks if str(t.get("status", "")).lower() == status_filter.lower()]
        tasks = tasks[:limit]

        return jsonify({
            "success": True,
            "tasks": tasks,
            "total": len(tasks),
            "active_count": sum(1 for t in tasks if t.get("status") in ("pending", "running", "busy")),
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as exc:
        logger.error(f"Failed to list agent tasks: {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc), "tasks": []}), 500


@agent_bp.route("/api/agents/tasks/<task_id>", methods=["GET", "OPTIONS"])
@jwt_required(optional=True)
def api_get_agent_task(task_id: str):
    """Return status & result for a single agent task."""
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        with _tasks_lock:
            rec = _agent_tasks.get(task_id)
            if rec:
                return jsonify({"success": True, "task": dict(rec)})

        try:
            _, coordinator = get_agent_registry_and_coordinator()
            if hasattr(coordinator, "get_task"):
                coord_rec = coordinator.get_task(task_id)
                if coord_rec:
                    return jsonify({"success": True, "task": coord_rec})
        except Exception:
            pass

        return jsonify({"success": False, "error": f"Task '{task_id}' not found"}), 404
    except Exception as exc:
        logger.error(f"Failed to get agent task '{task_id}': {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@agent_bp.route("/api/agents/tasks/<task_id>/cancel", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def api_cancel_agent_task(task_id: str):
    """Cancel a queued or running agent task."""
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        found = False
        snapshot = None
        with _tasks_lock:
            evt = _cancel_events.get(task_id)
            if evt is not None:
                evt.set()
            if task_id in _agent_tasks:
                found = True
                _agent_tasks[task_id]["status"] = "cancelled"
                _agent_tasks[task_id]["success"] = False
                _agent_tasks[task_id]["error"] = "Cancelled by user"
                _agent_tasks[task_id]["completed_at"] = datetime.now().isoformat()
                snapshot = dict(_agent_tasks[task_id])

        try:
            _, coordinator = get_agent_registry_and_coordinator()
            if hasattr(coordinator, "cancel_task") and coordinator.cancel_task(task_id):
                found = True
        except Exception:
            pass

        if not found:
            return jsonify({"success": False, "error": f"Task '{task_id}' not found"}), 404

        payload = snapshot or {"task_id": task_id, "status": "cancelled", "success": False}
        _emit_agent_event("agent.task_failed", payload)
        _emit_agent_event("agents_snapshot", get_agents_snapshot_payload())
        return jsonify({"success": True, "task": payload, "status": "cancelled"})
    except Exception as exc:
        logger.error(f"Failed to cancel agent task '{task_id}': {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


# =============================================================================
# WORKFLOW MEMORY & DYNAMIC SWARM SYNTHESIZER APIS
# =============================================================================

@agent_bp.route("/api/agents/workflows", methods=["GET", "OPTIONS"])
@jwt_required(optional=True)
def api_list_workflow_recipes():
    """List all saved macro workflow recipes learned by the swarm."""
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        from ai_assistant.core.workflow_memory import get_workflow_memory
        recipes = get_workflow_memory().list_all_recipes()
        return jsonify({"success": True, "recipes": recipes, "count": len(recipes)})
    except Exception as exc:
        logger.error(f"Failed to list workflow recipes: {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@agent_bp.route("/api/agents/workflows/synthesize", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def api_synthesize_workflow():
    """
    Synthesize an execution DAG for an unlisted/novel user goal via SwarmPlanner.
    Returns the wave breakdown, agent assignments, and reasoning.
    """
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        data = request.get_json(silent=True) or {}
        goal = (data.get("goal") or data.get("command") or data.get("task") or "").strip()
        if not goal:
            return jsonify({"success": False, "error": "Field 'goal' is required"}), 400

        from ai_assistant.core.swarm_planner import SwarmPlanner
        registry, coordinator = get_agent_registry_and_coordinator()
        planner = SwarmPlanner(registry=registry, llm_provider=getattr(coordinator, "llm", None))
        
        plan = run_async(planner.plan_workflow(goal))
        return jsonify({
            "success": True,
            "workflow": plan.to_dict() if plan else None,
            "cached": False,
        })
    except Exception as exc:
        logger.error(f"Failed to synthesize workflow: {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@agent_bp.route("/api/agents/workflows/clear", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def api_clear_workflow_memory():
    """Clear all cached workflow recipes."""
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        from ai_assistant.core.workflow_memory import get_workflow_memory
        get_workflow_memory().clear_memory()
        return jsonify({"success": True, "message": "Workflow memory cleared successfully"})
    except Exception as exc:
        logger.error(f"Failed to clear workflow memory: {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500
