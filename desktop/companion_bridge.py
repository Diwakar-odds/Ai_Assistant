#!/usr/bin/env python3
"""
Pulsar AI Assistant - Companion HTTP Bridge
============================================
Lightweight IPC connecting the floating desktop mascot to the backend Agent Brain.
Communicates via high-speed HTTP REST with automatic retry and local fallback.
"""

import os
import sys
import time
import requests
from typing import Dict, Any, List, Optional


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

    def send_command(self, command: str, include_screen: bool = False) -> Dict[str, Any]:
        """Sends user command to Agent Brain on backend"""
        try:
            resp = self.session.post(
                f"{self.base_url}/api/agent/command",
                json={"command": command, "include_screen": include_screen},
                timeout=25.0
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

    def _local_fallback(self, command: str, include_screen: bool) -> Dict[str, Any]:
        """Executes directly in-process if Flask backend is not yet booted"""
        try:
            from agent_brain import get_agent_brain
            brain = get_agent_brain()
            return brain.process_command(command, include_screen=include_screen)
        except Exception as e:
            return {
                "success": False,
                "response": f"Backend is starting up. Please try again in a moment. ({e})",
                "tts": "Assistant backend is starting up."
            }

