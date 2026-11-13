#!/usr/bin/env python3
"""
Pulsar AI Assistant - Notification Monitor Service
===================================================
Autonomous background service monitoring:
- Gmail inbox for important incoming emails
- Google Calendar for upcoming meetings & deadlines
- WhatsApp Desktop unread message alerts
- Custom priority filtering rules
Pushes structured notification objects to the companion mascot robot.
"""

import sys
import os
import time
import re
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root / "core_ai" / "src"))

from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

try:
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class NotificationMonitor:
    """Background notification poller and priority aggregator"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(NotificationMonitor, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        logger.info("📡 Initializing Notification Monitor Service...")
        self.pending_notifications: List[Dict[str, Any]] = []
        self.seen_notification_keys = set()
        self.is_running = False

        # State tracking
        self.last_unread_email_count = None
        self.last_whatsapp_badge = ""
        self.importance_keywords = ["urgent", "important", "interview", "offer", "deadline", "meeting", "alert"]

    def start(self):
        """Starts background polling loops"""
        if self.is_running:
            return
        self.is_running = True

        threading.Thread(target=self._email_monitor_loop, daemon=True).start()
        threading.Thread(target=self._calendar_monitor_loop, daemon=True).start()
        threading.Thread(target=self._window_monitor_loop, daemon=True).start()
        logger.info("✅ Notification Monitor threads running")

    def stop(self):
        self.is_running = False

    # -------------------------------------------------------------
    # 1. Email Polling (Gmail)
    # -------------------------------------------------------------
    def _email_monitor_loop(self):
        """Checks Gmail inbox periodically"""
        # Brief initial sleep so server finishes booting
        time.sleep(10)
        while self.is_running:
            try:
                from ai_assistant.integrations.email_handler import GmailManager
                gm = GmailManager()
                unread_str = gm.get_unread_count()
                # Parse numeric unread count
                nums = re.findall(r"\d+", str(unread_str))
                unread_count = int(nums[0]) if nums else 0

                if self.last_unread_email_count is not None and unread_count > self.last_unread_email_count:
                    diff = unread_count - self.last_unread_email_count
                    summary = gm.get_inbox_summary(max_emails=min(3, diff))
                    
                    priority = "normal"
                    if any(k in summary.lower() for k in self.importance_keywords):
                        priority = "high"

                    self.push_notification({
                        "type": "email",
                        "title": f"📧 {diff} New Email{'s' if diff > 1 else ''}",
                        "body": summary[:120],
                        "priority": priority,
                        "actions": ["Show", "Dismiss"]
                    })

                self.last_unread_email_count = unread_count
            except Exception as e:
                logger.debug(f"Email monitor pass notice: {e}")

            time.sleep(60)

    # -------------------------------------------------------------
    # 2. Calendar Reminders (Google Calendar)
    # -------------------------------------------------------------
    def _calendar_monitor_loop(self):
        """Checks Calendar for upcoming events starting soon"""
        time.sleep(15)
        while self.is_running:
            try:
                from ai_assistant.integrations.google_calendar import CalendarManager
                cal = CalendarManager()
                events_str = cal.get_upcoming_events(days_ahead=1)
                
                # Check for events today
                if events_str and "No upcoming events" not in events_str:
                    lines = [line.strip() for line in events_str.split("\n") if line.strip()]
                    for line in lines[:2]:
                        event_key = f"cal_{line[:30]}"
                        if event_key not in self.seen_notification_keys:
                            self.seen_notification_keys.add(event_key)
                            self.push_notification({
                                "type": "calendar",
                                "title": "📅 Calendar Reminder",
                                "body": line[:100],
                                "priority": "high",
                                "actions": ["Acknowledge", "Dismiss"]
                            })
            except Exception as e:
                logger.debug(f"Calendar monitor pass notice: {e}")

            time.sleep(300)

    # -------------------------------------------------------------
    # 3. WhatsApp / Messaging Window Badges
    # -------------------------------------------------------------
    def _window_monitor_loop(self):
        """Checks for unread message indicators in window titles"""
        time.sleep(5)
        while self.is_running:
            if WIN32_AVAILABLE:
                try:
                    found_titles = []
                    def _enum_cb(hwnd, param):
                        if win32gui.IsWindowVisible(hwnd):
                            t = win32gui.GetWindowText(hwnd)
                            if t and "whatsapp" in t.lower() and "(" in t:
                                param.append(t)
                        return True

                    win32gui.EnumWindows(_enum_cb, found_titles)

                    for title in found_titles:
                        if title != self.last_whatsapp_badge:
                            self.last_whatsapp_badge = title
                            self.push_notification({
                                "type": "whatsapp",
                                "title": "💬 WhatsApp Message",
                                "body": f"New message arrived: {title}",
                                "priority": "normal",
                                "actions": ["Show", "Reply", "Dismiss"]
                            })
                except Exception as e:
                    logger.debug(f"Window monitor pass notice: {e}")

            time.sleep(8)

    # -------------------------------------------------------------
    # 4. Notification Queue Management
    # -------------------------------------------------------------
    def push_notification(self, notif: Dict[str, Any]):
        """Pushes a notification into the pending queue"""
        with self._lock:
            notif["id"] = f"notif_{int(time.time() * 1000)}"
            notif["timestamp"] = time.time()
            if "priority" not in notif:
                notif["priority"] = "normal"
            if "actions" not in notif:
                notif["actions"] = ["Show", "Dismiss"]

            # Deduplicate by type and body
            for existing in self.pending_notifications:
                if existing.get("type") == notif.get("type") and existing.get("body") == notif.get("body"):
                    return

            logger.info(f"🔔 Notification queued: {notif.get('title')}")
            self.pending_notifications.append(notif)
            try:
                from telemetry_tracer import telemetry
                telemetry.log_notification(notif.get("type", "monitor"), notif.get("title", ""), notif.get("priority", "normal"))
            except Exception:
                pass

            # Limit queue size
            if len(self.pending_notifications) > 20:
                self.pending_notifications.pop(0)

    def get_pending(self) -> List[Dict[str, Any]]:
        """Returns and clears all pending notifications sorted by priority"""
        with self._lock:
            # Sort by priority weight descending
            weights = {"critical": 4, "high": 3, "normal": 2, "low": 1}
            self.pending_notifications.sort(key=lambda n: weights.get(n.get("priority", "normal"), 1), reverse=True)
            items = list(self.pending_notifications)
            self.pending_notifications.clear()
            return items

    def peek_pending(self) -> List[Dict[str, Any]]:
        """Returns pending notifications without clearing"""
        with self._lock:
            return list(self.pending_notifications)


_global_monitor = None

def get_notification_monitor() -> NotificationMonitor:
    """Singleton getter for NotificationMonitor"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = NotificationMonitor()
    return _global_monitor

