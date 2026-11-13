import threading
import time
import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class SelfHealingEngine:
    """
    Monitors system health and gracefully degrades features if services fail.
    Implements automated fallback routines.
    """
    def __init__(self):
        self.health_status = {
            "llm_api": True,
            "tts_engine": True,
            "stt_engine": True,
            "database": True,
            "network": True
        }
        self.running = False
        self.thread = None
        self.callbacks = []
        self.check_interval = 60  # seconds

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.thread.start()
            logger.info("Self-Healing Engine started.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def register_callback(self, callback: Callable[[str, bool], None]):
        """Register a callback for status changes. func(service_name, is_healthy)"""
        self.callbacks.append(callback)

    def get_status(self) -> Dict[str, bool]:
        return self.health_status.copy()

    def _monitoring_loop(self):
        while self.running:
            self._check_network()
            self._check_database()
            # In a real scenario, we'd ping endpoints or check module availability
            time.sleep(self.check_interval)

    def _update_status(self, service: str, status: bool):
        if self.health_status.get(service) != status:
            self.health_status[service] = status
            logger.warning(f"Self-Healing: {service} status changed to {'healthy' if status else 'degraded'}")
            for cb in self.callbacks:
                try:
                    cb(service, status)
                except Exception as e:
                    logger.error(f"Error in health callback: {e}")

    def _check_network(self):
        try:
            import socket
            # Check connection to a reliable DNS server
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self._update_status("network", True)
        except OSError:
            self._update_status("network", False)
            self._update_status("llm_api", False) # LLM usually requires network

    def _check_database(self):
        try:
            from ai_assistant.core.database_config import get_db_path
            import sqlite3
            db_path = get_db_path('personal_knowledge')
            with sqlite3.connect(db_path) as conn:
                conn.execute("SELECT 1")
            self._update_status("database", True)
        except Exception:
            self._update_status("database", False)

    def report_failure(self, service: str):
        """Called by other modules when they catch an exception."""
        self._update_status(service, False)
        # Attempt immediate recovery routine if needed
        self._trigger_recovery(service)

    def _trigger_recovery(self, service: str):
        if service == "llm_api":
            logger.info("Self-Healing: Falling back to local offline model...")
            # Here we'd signal the orchestrator to switch to local LLM
        elif service == "database":
            logger.info("Self-Healing: Using in-memory fallback for context...")
