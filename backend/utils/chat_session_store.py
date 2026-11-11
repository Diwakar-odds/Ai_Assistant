"""
Unified Backend Session & Activity Store for Pulsar AI
======================================================
Single source of truth for:
- Per-process backend boot detection (fresh active session on every backend restart)
- Archiving non-empty previous boot/manual sessions into persistent history
- Chronological chat transcript, voice commands, and rich activity timeline shared
  across Glowing Orb (desktop companion), WebUI chat/voice, HTTP REST, and Socket.IO.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_this_mod = sys.modules.get(__name__)
if _this_mod is not None:
    sys.modules.setdefault("utils.chat_session_store", _this_mod)
    sys.modules.setdefault("backend.utils.chat_session_store", _this_mod)

logger = logging.getLogger(__name__)

BOOT_ID = f"boot_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
MAX_HISTORY_SESSIONS = 50
MAX_MESSAGES_PER_SESSION = 500
MAX_ACTIVITIES_PER_SESSION = 500


def _resolve_default_storage_dir() -> Path:
    """Resolve writable session directory respecting PULSAR_DATA_DIR & frozen mode."""
    try:
        from settings_manager import get_writable_root

        base = Path(get_writable_root())
    except Exception:
        override = os.environ.get("PULSAR_DATA_DIR", "").strip()
        if override:
            base = Path(override).expanduser().resolve()
        elif getattr(sys, "frozen", False):
            appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~/.pulsar_ai"))
            base = Path(appdata) / "PulsarAI"
        else:
            base = Path(__file__).resolve().parent.parent.parent
    sessions_dir = base / "data" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


def _format_duration(start_ms: int, end_ms: int) -> str:
    diff_ms = max(0, int(end_ms) - int(start_ms))
    total_s = diff_ms // 1000
    hours = total_s // 3600
    minutes = (total_s % 3600) // 60
    seconds = total_s % 60
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    return f"{minutes}m {seconds}s"


def _format_clock_12h(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now()
    return d.strftime("%I:%M %p").lstrip("0") or d.strftime("%I:%M %p")


def _format_clock_hms(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now()
    return d.strftime("%I:%M:%S %p").lstrip("0") or d.strftime("%I:%M:%S %p")


def _has_meaningful_content(session: Optional[Dict[str, Any]]) -> bool:
    """Return True if a session has user interactions, voice commands, or non-trivial activity."""
    if not isinstance(session, dict):
        return False
    if session.get("voiceCommands"):
        return True
    for msg in session.get("messages") or []:
        if msg.get("type") == "user":
            return True
        if msg.get("source") not in (
            "webui_startup",
            "startup_greeting",
            "new_session",
            "webui_new_session",
            "backend_startup",
        ):
            return True
    for act in session.get("activities") or []:
        if act.get("kind") not in ("session", "startup"):
            return True
    return False


def _extract_meaningful_preview(
    messages: List[Dict[str, Any]],
    voice_commands: List[Dict[str, Any]],
    activities: List[Dict[str, Any]],
) -> str:
    for m in messages:
        if m.get("type") == "user" and str(m.get("text") or "").strip():
            return str(m["text"]).strip()[:150]
    for vc in voice_commands:
        if str(vc.get("command") or "").strip():
            return str(vc["command"]).strip()[:150]
    for m in messages:
        txt = str(m.get("text") or "").strip()
        if not txt:
            continue
        low = txt.lower()
        if (
            "at your service" in low
            or "all systems online" in low
            or "ready for a new session" in low
            or m.get("source") in ("webui_startup", "new_session", "webui_new_session")
        ):
            continue
        return txt[:150]
    for act in activities:
        if act.get("kind") not in ("session", "startup") and str(act.get("detail") or act.get("title") or "").strip():
            return str(act.get("detail") or act.get("title")).strip()[:150]
    if messages and str(messages[0].get("text") or "").strip():
        return str(messages[0]["text"]).strip()[:150]
    return "Interactive Session"


def _get_live_socketio():
    """Locate active SocketIO instance across voice_service or routes.common."""
    for mod_name in ("voice_service", "backend.voice_service"):
        mod = sys.modules.get(mod_name)
        if mod is not None:
            sio = getattr(mod, "_socketio", None)
            if sio is not None:
                return sio
    for mod_name in ("routes.common", "backend.routes.common"):
        mod = sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, "get_socketio"):
            try:
                sio = mod.get_socketio()
                if sio is not None:
                    return sio
            except Exception:
                pass
    return None


class ChatSessionStore:
    """Thread-safe persistent store for active session, history, and unified activity feed."""

    def __init__(self, storage_dir: Optional[Path] = None, boot_id: Optional[str] = None):
        self._lock = threading.RLock()
        self.storage_dir = Path(storage_dir) if storage_dir else _resolve_default_storage_dir()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.active_file = self.storage_dir / "active_session.json"
        self.history_file = self.storage_dir / "history.json"
        self.boot_id = boot_id or BOOT_ID

        self._history: List[Dict[str, Any]] = self._load_json(self.history_file, default=[])
        if not isinstance(self._history, list):
            self._history = []

        prev_active = self._load_json(self.active_file, default=None)
        if isinstance(prev_active, dict) and prev_active.get("id"):
            if prev_active.get("boot_id") != self.boot_id:
                if _has_meaningful_content(prev_active):
                    self._archive_session_locked(prev_active, save=False)
                self._active = self._create_blank_session_locked(
                    reason="backend_startup",
                    initial_activity_title="Backend session initialized",
                    initial_activity_detail=f"Fresh session started ({self.boot_id})",
                )
            else:
                self._active = self._normalize_session_dict(prev_active)
        else:
            self._active = self._create_blank_session_locked(
                reason="backend_startup",
                initial_activity_title="Backend session initialized",
                initial_activity_detail=f"Fresh session started ({self.boot_id})",
            )
        self._persist_locked()

    # ------------------------------------------------------------------
    # Low-level atomic JSON helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _load_json(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"[SessionStore] Failed reading {path}: {exc}")
            return default

    @staticmethod
    def _atomic_write_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f".tmp.{os.getpid()}.{threading.get_ident()}")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        except Exception as exc:
            logger.warning(f"[SessionStore] Failed writing {path}: {exc}")
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass

    def _persist_locked(self) -> None:
        self._atomic_write_json(self.active_file, self._active)
        self._atomic_write_json(self.history_file, self._history[:MAX_HISTORY_SESSIONS])

    def _next_unique_session_id_locked(self) -> str:
        used = {s.get("id") for s in self._history if isinstance(s, dict)}
        if getattr(self, "_active", None) and self._active.get("id"):
            used.add(self._active["id"])
        ts_ms = int(time.time() * 1000)
        candidate = f"session_{ts_ms}"
        while candidate in used:
            ts_ms += 1
            candidate = f"session_{ts_ms}"
        return candidate

    def _next_numeric_id_locked(self, session: Optional[Dict[str, Any]] = None) -> int:
        sess = session or self._active
        now_ms = int(time.time() * 1000)
        last_id = 0
        for m in sess.get("messages") or []:
            try:
                last_id = max(last_id, int(m.get("id") or 0))
            except Exception:
                pass
        return max(now_ms, last_id + 1)

    def _create_blank_session_locked(
        self,
        reason: str = "backend_startup",
        initial_activity_title: str = "Session started",
        initial_activity_detail: str = "",
        source: str = "system",
    ) -> Dict[str, Any]:
        now = datetime.now()
        session_id = self._next_unique_session_id_locked()
        try:
            start_ms = int(session_id.replace("session_", ""))
        except Exception:
            start_ms = int(time.time() * 1000)

        day_name = now.strftime("%A")
        date_str = now.strftime("%d %b %Y").lstrip("0")
        clock_hms = _format_clock_hms(now)

        init_act = {
            "seq": 1,
            "id": f"act_1_{uuid.uuid4().hex[:6]}",
            "kind": "session",
            "title": initial_activity_title,
            "detail": initial_activity_detail or f"Session {session_id} initialized",
            "source": source,
            "status": "info",
            "intent": None,
            "provider": None,
            "model": None,
            "time": clock_hms,
            "timestamp": now.isoformat(),
            "ts_ms": start_ms,
        }

        sess = {
            "id": session_id,
            "boot_id": self.boot_id,
            "reason": reason,
            "startTime": clock_hms,
            "startTimestamp": start_ms,
            "endTime": clock_hms,
            "endTimestamp": start_ms,
            "date": date_str,
            "day": day_name,
            "formattedDate": f"{day_name}, {date_str}",
            "duration": "0m 0s",
            "preview": "Interactive Session",
            "messageCount": 0,
            "userMessageCount": 0,
            "aiMessageCount": 0,
            "voiceCount": 0,
            "activityCount": 1,
            "messages": [],
            "voiceCommands": [],
            "activities": [init_act],
        }
        return sess

    def _recompute_summary_locked(self, session: Dict[str, Any]) -> None:
        msgs = session.get("messages") or []
        cmds = session.get("voiceCommands") or []
        acts = session.get("activities") or []

        start_ms = int(session.get("startTimestamp") or int(time.time() * 1000))
        end_ms = max(
            start_ms,
            int(session.get("endTimestamp") or start_ms),
            int((msgs[-1].get("ts_ms") if msgs else 0) or 0),
            int((acts[-1].get("ts_ms") if acts else 0) or 0),
        )
        session["endTimestamp"] = end_ms
        session["endTime"] = _format_clock_hms(datetime.fromtimestamp(end_ms / 1000.0))
        session["duration"] = _format_duration(start_ms, end_ms)
        session["messageCount"] = len(msgs)
        session["userMessageCount"] = sum(1 for m in msgs if m.get("type") == "user")
        session["aiMessageCount"] = sum(1 for m in msgs if m.get("type") == "ai")
        session["voiceCount"] = len(cmds)
        session["activityCount"] = len(acts)
        session["preview"] = _extract_meaningful_preview(msgs, cmds, acts)

    def _normalize_session_dict(self, session: Dict[str, Any]) -> Dict[str, Any]:
        sess = copy.deepcopy(session)
        sess.setdefault("messages", [])
        sess.setdefault("voiceCommands", [])
        sess.setdefault("activities", [])
        sess.setdefault("boot_id", self.boot_id)
        self._recompute_summary_locked(sess)
        return sess

    def _archive_session_locked(self, session: Dict[str, Any], save: bool = True) -> None:
        norm = self._normalize_session_dict(session)
        sid = norm.get("id")
        if not sid:
            return
        self._history = [s for s in self._history if s.get("id") != sid]
        self._history.insert(0, norm)
        self._history.sort(key=lambda s: int(s.get("startTimestamp") or 0), reverse=True)
        self._history = self._history[:MAX_HISTORY_SESSIONS]
        if save:
            self._persist_locked()

    # ------------------------------------------------------------------
    # SocketIO broadcast helper (best effort, never raises)
    # ------------------------------------------------------------------
    @staticmethod
    def _emit_socket(event_name: str, payload: Dict[str, Any]) -> None:
        sio = _get_live_socketio()
        if sio is None:
            return
        try:
            sio.emit(event_name, payload)
        except Exception as exc:
            logger.debug(f"[SessionStore] Socket emit {event_name} skipped: {exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_boot_id(self) -> str:
        return self.boot_id

    def next_message_id(self, prefix: str = "msg") -> str:
        return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"

    def get_current_session(self) -> Dict[str, Any]:
        with self._lock:
            self._recompute_summary_locked(self._active)
            return copy.deepcopy(self._active)

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._history[: max(1, int(limit))])

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        with self._lock:
            if self._active.get("id") == session_id:
                return copy.deepcopy(self._active)
            for item in self._history:
                if item.get("id") == session_id:
                    return copy.deepcopy(item)
            return None

    def get_current_activities(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            acts = self._active.get("activities") or []
            return copy.deepcopy(acts[-max(1, int(limit)) :])

    def start_new_session(
        self,
        reason: str = "manual",
        greeting_text: Optional[str] = None,
        source: str = "webui_new_session",
        emit_event: bool = True,
    ) -> Dict[str, Any]:
        with self._lock:
            if _has_meaningful_content(self._active):
                self._archive_session_locked(self._active, save=False)

            self._active = self._create_blank_session_locked(
                reason=reason,
                initial_activity_title="New session started",
                initial_activity_detail=f"Started via {source}",
                source=source,
            )

            if greeting_text and str(greeting_text).strip():
                self._append_message_locked(
                    role="ai",
                    text=str(greeting_text).strip(),
                    source=source,
                    is_voice=False,
                    message_id=f"greeting_{self._active['id']}",
                )

            self._recompute_summary_locked(self._active)
            self._persist_locked()
            snap = copy.deepcopy(self._active)

        if emit_event:
            self._emit_socket(
                "session_started",
                {
                    "boot_id": self.boot_id,
                    "session_id": snap["id"],
                    "session": snap,
                    "reason": reason,
                },
            )
        return snap

    def ensure_startup_greeting(
        self,
        greeting_text: Optional[str] = None,
        source: str = "webui_startup",
        emit_event: bool = True,
    ) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Record a startup greeting at most once for an empty active session."""
        with self._lock:
            existing_msgs = self._active.get("messages") or []
            if existing_msgs:
                for m in existing_msgs:
                    if m.get("source") in ("webui_startup", "startup_greeting", "new_session", "webui_new_session"):
                        return copy.deepcopy(m), False
                return copy.deepcopy(existing_msgs[0]), False

            clean_text = (greeting_text or "").strip()
            if not clean_text:
                return None, False

            msg_id = f"startup_{self._active['id']}"
            msg, created = self._append_message_locked(
                role="ai",
                text=clean_text,
                source=source,
                is_voice=False,
                message_id=msg_id,
            )
            act = self._append_activity_locked(
                kind="session",
                title="Startup greeting",
                detail=clean_text,
                source=source,
                status="success",
            )
            self._recompute_summary_locked(self._active)
            self._persist_locked()
            stats = self._summary_stats_locked()
            sid = self._active["id"]

        if created and emit_event:
            self._emit_socket(
                "session_event",
                {
                    "boot_id": self.boot_id,
                    "session_id": sid,
                    "message": msg,
                    "activity": act,
                    "stats": stats,
                },
            )
        return msg, created

    def delete_session(self, session_id: str) -> bool:
        if not session_id:
            return False
        with self._lock:
            if self._active.get("id") == session_id:
                self._active = self._create_blank_session_locked(
                    reason="deleted_active",
                    initial_activity_title="Session reset",
                    initial_activity_detail="Previous active session deleted",
                )
                self._persist_locked()
                return True
            before = len(self._history)
            self._history = [s for s in self._history if s.get("id") != session_id]
            changed = len(self._history) != before
            if changed:
                self._persist_locked()
            return changed

    def clear_history(self) -> int:
        with self._lock:
            count = len(self._history)
            self._history = []
            self._persist_locked()
            return count

    def _summary_stats_locked(self) -> Dict[str, Any]:
        return {
            "messageCount": self._active.get("messageCount", 0),
            "userMessageCount": self._active.get("userMessageCount", 0),
            "aiMessageCount": self._active.get("aiMessageCount", 0),
            "voiceCount": self._active.get("voiceCount", 0),
            "activityCount": self._active.get("activityCount", 0),
            "endTime": self._active.get("endTime"),
            "endTimestamp": self._active.get("endTimestamp"),
            "duration": self._active.get("duration"),
            "preview": self._active.get("preview"),
        }

    def _append_message_locked(
        self,
        role: str,
        text: str,
        *,
        source: str = "chat",
        is_voice: Optional[bool] = None,
        message_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        intent: Optional[str] = None,
        success: bool = True,
    ) -> Tuple[Dict[str, Any], bool]:
        norm_role = "user" if str(role).lower() == "user" else "ai"
        clean_text = str(text or "").strip()
        src = str(source or "chat")
        voice_flag = bool(is_voice) if is_voice is not None else (
            norm_role == "user"
            and any(tok in src.lower() for tok in ("voice", "companion", "whisper", "google"))
        )
        msg_uid = str(message_id).strip() if message_id else self.next_message_id(norm_role)

        msgs: List[Dict[str, Any]] = self._active.setdefault("messages", [])
        for existing in msgs:
            if existing.get("message_id") == msg_uid:
                if clean_text and clean_text != existing.get("text"):
                    existing["text"] = clean_text
                if provider:
                    existing["provider"] = provider
                if model:
                    existing["model"] = model
                if intent:
                    existing["intent"] = intent
                existing["success"] = bool(success)
                return copy.deepcopy(existing), False

        now = datetime.now()
        ts_ms = int(now.timestamp() * 1000)
        seq = (msgs[-1]["seq"] + 1) if msgs and isinstance(msgs[-1].get("seq"), int) else (len(msgs) + 1)
        num_id = self._next_numeric_id_locked()
        clock_12h = _format_clock_12h(now)

        msg = {
            "seq": seq,
            "id": num_id,
            "message_id": msg_uid,
            "type": norm_role,
            "text": clean_text,
            "time": clock_12h,
            "timestamp": now.isoformat(),
            "ts_ms": ts_ms,
            "source": src,
            "isVoice": voice_flag,
            "provider": provider,
            "model": model,
            "intent": intent,
            "success": bool(success),
        }
        msgs.append(msg)
        if len(msgs) > MAX_MESSAGES_PER_SESSION:
            del msgs[: len(msgs) - MAX_MESSAGES_PER_SESSION]

        if norm_role == "user" and voice_flag and clean_text:
            vcmds: List[Dict[str, Any]] = self._active.setdefault("voiceCommands", [])
            if not any(v.get("message_id") == msg_uid for v in vcmds):
                vcmds.append(
                    {
                        "id": num_id,
                        "message_id": msg_uid,
                        "command": clean_text,
                        "time": clock_12h,
                        "timestamp": now.isoformat(),
                        "ts_ms": ts_ms,
                        "source": src,
                    }
                )

        return copy.deepcopy(msg), True

    def _append_activity_locked(
        self,
        kind: str,
        title: str,
        detail: str = "",
        *,
        source: str = "system",
        status: str = "info",
        intent: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        activity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        acts: List[Dict[str, Any]] = self._active.setdefault("activities", [])
        act_uid = str(activity_id).strip() if activity_id else None
        if act_uid:
            for existing in acts:
                if existing.get("id") == act_uid:
                    if detail:
                        existing["detail"] = str(detail)[:400]
                    if status:
                        existing["status"] = str(status)
                    return copy.deepcopy(existing)

        now = datetime.now()
        ts_ms = int(now.timestamp() * 1000)
        seq = (acts[-1]["seq"] + 1) if acts and isinstance(acts[-1].get("seq"), int) else (len(acts) + 1)
        act = {
            "seq": seq,
            "id": act_uid or f"act_{seq}_{uuid.uuid4().hex[:6]}",
            "kind": str(kind or "info"),
            "title": str(title or kind or "Activity")[:160],
            "detail": str(detail or "")[:400],
            "source": str(source or "system"),
            "status": str(status or "info"),
            "intent": intent,
            "provider": provider,
            "model": model,
            "time": _format_clock_hms(now),
            "timestamp": now.isoformat(),
            "ts_ms": ts_ms,
        }
        acts.append(act)
        if len(acts) > MAX_ACTIVITIES_PER_SESSION:
            del acts[: len(acts) - MAX_ACTIVITIES_PER_SESSION]
        return copy.deepcopy(act)

    def record_message(
        self,
        role: str,
        text: str,
        *,
        source: str = "chat",
        is_voice: Optional[bool] = None,
        message_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        intent: Optional[str] = None,
        success: bool = True,
        also_record_activity: bool = True,
        activity_kind: Optional[str] = None,
        activity_title: Optional[str] = None,
        emit_event: bool = True,
        expected_session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        clean_text = str(text or "").strip()
        if not clean_text:
            return None

        with self._lock:
            if expected_session_id and self._active.get("id") != expected_session_id:
                logger.debug(
                    f"[SessionStore] Ignoring stale message write for session {expected_session_id} "
                    f"(active={self._active.get('id')})"
                )
                return None

            msg, created = self._append_message_locked(
                role=role,
                text=clean_text,
                source=source,
                is_voice=is_voice,
                message_id=message_id,
                provider=provider,
                model=model,
                intent=intent,
                success=success,
            )

            act = None
            if created and also_record_activity:
                if msg["type"] == "user":
                    is_orb = "companion" in str(source).lower()
                    inferred_kind = activity_kind or ("voice_input" if msg["isVoice"] else "text_input")
                    inferred_title = activity_title or (
                        "Glowing Orb voice command"
                        if is_orb
                        else ("Voice command received" if msg["isVoice"] else "Chat command sent")
                    )
                    inferred_status = "info"
                else:
                    inferred_kind = activity_kind or ("response" if success else "error")
                    inferred_title = activity_title or (
                        "Assistant replied" if success else "Command failed"
                    )
                    inferred_status = "success" if success else "error"

                act = self._append_activity_locked(
                    kind=inferred_kind,
                    title=inferred_title,
                    detail=clean_text,
                    source=msg["source"],
                    status=inferred_status,
                    intent=intent,
                    provider=provider,
                    model=model,
                )

            self._recompute_summary_locked(self._active)
            self._persist_locked()
            sid = self._active["id"]
            stats = self._summary_stats_locked()

        if emit_event:
            payload: Dict[str, Any] = {
                "boot_id": self.boot_id,
                "session_id": sid,
                "message": msg,
                "stats": stats,
            }
            if msg.get("isVoice") and msg["type"] == "user":
                payload["voice_command"] = {
                    "id": msg["id"],
                    "message_id": msg["message_id"],
                    "command": msg["text"],
                    "time": msg["time"],
                    "timestamp": msg["timestamp"],
                    "ts_ms": msg["ts_ms"],
                    "source": msg["source"],
                }
            if act is not None:
                payload["activity"] = act
            self._emit_socket("session_event", payload)

        return msg

    def record_activity(
        self,
        kind: str,
        title: str,
        detail: str = "",
        *,
        source: str = "system",
        status: str = "info",
        intent: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        activity_id: Optional[str] = None,
        emit_event: bool = True,
        expected_session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            if expected_session_id and self._active.get("id") != expected_session_id:
                logger.debug(
                    f"[SessionStore] Ignoring stale activity write for session {expected_session_id} "
                    f"(active={self._active.get('id')})"
                )
                return None
            act = self._append_activity_locked(
                kind=kind,
                title=title,
                detail=detail,
                source=source,
                status=status,
                intent=intent,
                provider=provider,
                model=model,
                activity_id=activity_id,
            )
            self._recompute_summary_locked(self._active)
            self._persist_locked()
            sid = self._active["id"]
            stats = self._summary_stats_locked()

        if emit_event:
            self._emit_socket(
                "session_event",
                {
                    "boot_id": self.boot_id,
                    "session_id": sid,
                    "activity": act,
                    "stats": stats,
                },
            )
        return act


_store_lock = threading.Lock()
_session_store: Optional[ChatSessionStore] = None


def get_session_store() -> ChatSessionStore:
    """Return process-wide singleton ChatSessionStore."""
    global _session_store
    if _session_store is None:
        with _store_lock:
            if _session_store is None:
                _session_store = ChatSessionStore()
    return _session_store


def reset_session_store_for_tests(
    storage_dir: Optional[Path] = None,
    boot_id: Optional[str] = None,
) -> ChatSessionStore:
    """Test helper to reset singleton against a fresh directory / boot_id."""
    global _session_store
    with _store_lock:
        _session_store = ChatSessionStore(storage_dir=storage_dir, boot_id=boot_id)
        return _session_store
