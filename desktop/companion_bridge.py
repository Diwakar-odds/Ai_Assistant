#!/usr/bin/env python3
"""
Pulsar AI Assistant - Companion HTTP Bridge
============================================
Lightweight IPC connecting the floating desktop mascot to the backend Agent Brain.
Communicates via high-speed HTTP REST with automatic retry and local fallback.
"""

import os
import sys
import json
import time
import threading
import urllib.request
import requests
from typing import Dict, Any, List, Optional


def post_overlay_visibility(port: int, minimized: bool, source: str = "windows_app") -> None:
    """Unified background POST to sync desktop overlay visibility when native windows minimize/restore."""
    def _send():
        try:
            url = f"http://127.0.0.1:{int(port)}/api/desktop/overlay/state"
            payload = json.dumps({
                "app_minimized": bool(minimized),
                "source": source,
            }).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=1.5):
                pass
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


class CompanionBridgeClient:
    """Client for companion to communicate with Flask backend Agent Brain"""

    def __init__(self, port: int = 5000):
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"
        self.session = requests.Session()
        self.is_connected = False
        self._check_connection()

    def _check_connection(self) -> bool:
        try:
            r = self.session.get(f"{self.base_url}/api/status", timeout=1.0)
            self.is_connected = (r.status_code == 200)
            return self.is_connected
        except Exception:
            self.is_connected = False
            return False

    def send_command(self, command: str, include_screen: bool = False, source: str = "companion_voice") -> Dict[str, Any]:
        """Sends user command to Agent Brain on backend"""
        try:
            resp = self.session.post(
                f"{self.base_url}/api/agent/command",
                json={"command": command, "include_screen": include_screen, "source": source},
                timeout=60.0
            )
            if resp.status_code == 200:
                self.is_connected = True
                return resp.json()
            else:
                return {
                    "success": False,
                    "response": f"Server responded with status {resp.status_code}",
                    "tts": "Server error."
                }
        except requests.exceptions.ReadTimeout:
            # Backend accepted the command and is still streaming/speaking; never fall back locally or mark error
            self.is_connected = True
            return {
                "success": True,
                "response": "",
                "tts": "",
                "_timed_out": True,
                "_local_fallback": False,
            }
        except requests.exceptions.ConnectionError:
            self.is_connected = False
            # Local in-process fallback if backend is not running
            return self._local_fallback(command, include_screen)
        except Exception as e:
            return {
                "success": False,
                "response": f"Bridge request error: {str(e)}",
                "tts": "Communication error."
            }

    def get_overlay_state(self) -> Optional[Dict[str, Any]]:
        """Fetch live 4D orb overlay state and settings toggle from backend."""
        try:
            resp = self.session.get(f"{self.base_url}/api/desktop/overlay/state", timeout=1.5)
            if resp.status_code == 200:
                self.is_connected = True
                data = resp.json()
                return data.get("overlay") if isinstance(data, dict) else None
        except Exception:
            pass
        return None

    def update_overlay_state(
        self,
        state: Optional[str] = None,
        audio_level: Optional[float] = None,
        app_minimized: Optional[bool] = None,
        transcript: Optional[str] = None,
        error_message: Optional[str] = None,
        source: str = "companion",
    ) -> Optional[Dict[str, Any]]:
        """Push live orb state or voice amplitude to backend overlay coordinator."""
        payload: Dict[str, Any] = {"source": source}
        if state is not None:
            payload["state"] = state
        if audio_level is not None:
            payload["audio_level"] = float(audio_level)
        if app_minimized is not None:
            payload["app_minimized"] = bool(app_minimized)
        if transcript is not None:
            payload["transcript"] = transcript
        if error_message is not None:
            payload["error_message"] = error_message

        try:
            resp = self.session.post(
                f"{self.base_url}/api/desktop/overlay/state",
                json=payload,
                timeout=1.2,
            )
            if resp.status_code == 200:
                self.is_connected = True
                data = resp.json()
                return data.get("overlay") if isinstance(data, dict) else None
        except Exception:
            pass
        return None

    def get_wake_words(self) -> List[str]:
        """Load configured wake-word phrases from backend settings."""
        try:
            resp = self.session.get(f"{self.base_url}/api/settings/all", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                phrases = (((data.get("settings") or {}).get("voice") or {}).get("wakeWord") or {}).get("phrases")
                if isinstance(phrases, list):
                    return [str(p).strip().lower() for p in phrases if str(p).strip()]
        except Exception:
            pass
        try:
            from ai_assistant.core.local_command_normalizer import DEFAULT_WAKE_PHRASES
            return list(DEFAULT_WAKE_PHRASES)
        except Exception:
            return ["hey pulsar", "pulsar", "ok pulsar", "hey assistant"]

    def poll_notifications(self) -> List[Dict[str, Any]]:
        """Polls backend for pending notifications (Email, WhatsApp, Calendar)"""
        try:
            resp = self.session.get(f"{self.base_url}/api/agent/notifications", timeout=1.5)
            if resp.status_code == 200:
                self.is_connected = True
                return resp.json().get("notifications", [])
            return []
        except Exception:
            return []

    def confirm_action(self, action_id: str, confirmed: bool) -> Dict[str, Any]:
        """Confirms or cancels a Tier 3 action"""
        try:
            resp = self.session.post(
                f"{self.base_url}/api/agent/confirm",
                json={"action_id": action_id, "confirmed": confirmed},
                timeout=10.0
            )
            return resp.json() if resp.status_code == 200 else {"success": False}
        except Exception as e:
            return {"success": False, "response": str(e)}

    def get_tts_status(self) -> Optional[Dict[str, Any]]:
        """Query backend single-speaker TTS and EchoGuard status."""
        try:
            resp = self.session.get(f"{self.base_url}/api/voice/status", timeout=1.5)
            if resp.status_code == 200:
                self.is_connected = True
                return resp.json()
        except Exception:
            pass
        return None

    def speak(self, text: str, interrupt: bool = True, wait: bool = False, source: str = "companion") -> bool:
        """Ask the unified backend TTSOutputService to speak text over system speakers."""
        clean = (text or "").strip()
        if not clean:
            return False
        try:
            resp = self.session.post(
                f"{self.base_url}/api/voice/speak",
                json={"text": clean, "interrupt": interrupt, "wait": wait, "source": source},
                timeout=15.0 if wait else 3.0,
            )
            if resp.status_code == 200:
                self.is_connected = True
                data = resp.json()
                return bool(data.get("success", False))
        except Exception:
            pass
        return False

    def request_wake_ack(
        self,
        wake_word: str = "",
        raw_transcript: str = "",
        kind: str = "wake",
        speak: bool = True,
        wait: bool = True,
        source: str = "companion_wake",
    ) -> Dict[str, Any]:
        """Request a dynamic, non-repeating wake/session acknowledgment from unified backend persona."""
        try:
            resp = self.session.post(
                f"{self.base_url}/api/voice/wake-ack",
                json={
                    "wake_word": wake_word,
                    "raw_transcript": raw_transcript,
                    "kind": kind,
                    "speak": bool(speak),
                    "wait": bool(wait),
                    "source": source,
                },
                timeout=16.0 if wait else 3.0,
            )
            if resp.status_code == 200:
                self.is_connected = True
                data = resp.json()
                if isinstance(data, dict):
                    return data
            elif resp.status_code < 500:
                # Reachable HTTP response without fallback collision
                return {"success": False, "text": "", "spoken": False, "_local_fallback": False}
        except requests.exceptions.ReadTimeout:
            # Backend accepted the request and is likely still finishing playback; NEVER overlap with local fallback
            self.is_connected = True
            return {"success": True, "text": "", "queued": True, "spoken": True, "_local_fallback": False}
        except requests.exceptions.ConnectionError:
            self.is_connected = False
        except Exception:
            self.is_connected = False

        # Offline in-process persona fallback ONLY when backend is unreachable
        text = ""
        try:
            from ai_assistant.core.jarvis_persona import generate_wake_acknowledgment
            text = generate_wake_acknowledgment(wake_word=wake_word, raw_transcript=raw_transcript)
        except Exception:
            text = ""
        return {"success": bool(text), "text": text, "spoken": False, "_local_fallback": True}

    def stop_speaking(self, reason: str = "companion_barge_in") -> bool:
        """Immediately stop ongoing backend TTS playback (barge-in)."""
        try:
            resp = self.session.post(
                f"{self.base_url}/api/voice/stop",
                json={"reason": reason},
                timeout=1.5,
            )
            if resp.status_code == 200:
                self.is_connected = True
                return True
        except Exception:
            pass
        return False

    def _local_fallback(self, command: str, include_screen: bool) -> Dict[str, Any]:
        """Executes directly in-process if Flask backend is not yet booted."""
        try:
            pre_report = None
            try:
                from ai_assistant.core.jarvis_persona import generate_pre_task_report
                pre_report = generate_pre_task_report(command, source="companion_voice")
            except Exception:
                pre_report = None

            from agent_brain import get_agent_brain
            brain = get_agent_brain()
            res = brain.process_command(command, include_screen=include_screen, source="companion_voice")
            if isinstance(res, dict):
                out = dict(res)
                raw_resp = str(out.get("response", ""))
                try:
                    from ai_assistant.core.jarvis_persona import format_post_task_report
                    formatted = format_post_task_report(
                        command=command,
                        raw_result=raw_resp,
                        success=bool(out.get("success", True)),
                        intent=out.get("intent"),
                    )
                    out["response"] = formatted
                    if out.get("intent") not in ("wake_greeting", "voice_control"):
                        out["tts"] = formatted
                except Exception:
                    pass
                if pre_report and out.get("intent") not in ("wake_greeting", "voice_control"):
                    out["pre_report"] = pre_report
                out["_local_fallback"] = True
                return out
            return {"success": True, "response": str(res), "pre_report": pre_report, "_local_fallback": True}
        except Exception as e:
            return {
                "success": False,
                "response": f"Backend is starting up. Please try again in a moment. ({e})",
                "tts": "Assistant backend is starting up.",
                "_local_fallback": True,
            }

