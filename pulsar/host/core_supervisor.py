"""
Pulsar Host - Core Process Supervisor

Orchestrates the headless Core subprocess:
- Generates crypto token per launch.
- Binds Core to Win32 Job Object (KILL_ON_JOB_CLOSE).
- Polls /health and verifies auth nonce.
- Automatically recovers and restarts Core on crash with exponential backoff.
- Orchestrates authenticated graceful shutdown.
"""

import os
import sys
import time
import secrets
import logging
import subprocess
import threading
from typing import Optional, Callable, Dict, Any
from pathlib import Path

import requests
import psutil

from pulsar.host.job_object import Win32JobObject

try:
    from PySide6.QtCore import QObject, Signal
    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False
    class QObject:
        pass
    class Signal:
        def __init__(self, *args): pass
        def emit(self, *args): pass
        def connect(self, *args): pass

logger = logging.getLogger("pulsar.host.supervisor")

# Repository root for working directory
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class SupervisorSignals(QObject):
    """Qt Signals to safely communicate from background supervisor thread to Qt UI thread."""
    core_ready = Signal()
    status_changed = Signal(str, dict)


class CoreSupervisor:
    """Manages the headless Core process lifecycle."""

    def __init__(
        self,
        port: int = 5000,
        host: str = "127.0.0.1",
        on_ready: Optional[Callable[[], None]] = None,
        on_status_change: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ):
        self.port = port
        self.host = host
        self.token = secrets.token_hex(16)
        self.base_url = f"http://{self.host}:{self.port}"

        self.signals = SupervisorSignals()
        self.on_ready = on_ready
        self.on_status_change = on_status_change

        self._job_object = Win32JobObject()
        self._proc: Optional[subprocess.Popen] = None
        self._core_server_pid: Optional[int] = None
        self._is_shutting_down = False

        self._status = "stopped"
        self._components: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None

    @property
    def status(self) -> str:
        with self._lock:
            return self._status

    @property
    def components(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._components)

    @property
    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self):
        """Starts the Core process and launches the background health monitor."""
        self._is_shutting_down = False
        self._spawn_core()
        self._monitor_thread = threading.Thread(
            target=self._supervision_loop,
            name="CoreSupervisorLoop",
            daemon=True,
        )
        self._monitor_thread.start()

    def _resolve_core_python(self) -> str:
        """Uses sibling python.exe (with CREATE_NO_WINDOW) when Host runs under pythonw.exe."""
        exe = Path(sys.executable)
        if exe.name.lower() == "pythonw.exe":
            sibling = exe.with_name("python.exe")
            if sibling.exists():
                return str(sibling)
        venv_py = REPO_ROOT / "venv" / "Scripts" / "python.exe"
        if venv_py.exists():
            return str(venv_py)
        return sys.executable

    def restart_core(self):
        """Gracefully restarts the Headless Core without closing the Host UI or System Tray."""
        logger.info("[Supervisor] Manual Core restart requested from Tray.")
        def _do_restart():
            try:
                requests.post(
                    f"{self.base_url}/shutdown",
                    headers={"X-Pulsar-Token": self.token},
                    timeout=1.5,
                )
            except Exception:
                pass
            if self._proc is not None:
                try:
                    self._proc.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    try:
                        self._proc.kill()
                    except Exception:
                        pass
        threading.Thread(target=_do_restart, name="CoreManualRestart", daemon=True).start()

    def _spawn_core(self):
        """Spawns the Core subprocess (supports both dev python and frozen PyInstaller Pulsar.exe)."""
        with self._lock:
            self._status = "starting"

        if getattr(sys, "frozen", False):
            work_dir = Path(sys.executable).resolve().parent
            cmd = [
                sys.executable,
                "--core-subprocess",
                "--host",
                self.host,
                "--port",
                str(self.port),
                "--token",
                self.token,
                "--parent-pid",
                str(os.getpid()),
            ]
        else:
            work_dir = REPO_ROOT
            cmd = [
                self._resolve_core_python(),
                "-m",
                "pulsar.core",
                "--host",
                self.host,
                "--port",
                str(self.port),
                "--token",
                self.token,
                "--parent-pid",
                str(os.getpid()),
            ]

        logger.info(f"[Supervisor] Launching Core: {' '.join(cmd)}")

        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        env["PULSAR_DISABLE_COMPANION"] = "1"

        # On Windows, hide console window and isolate process group so Ctrl+C in Host is handled cleanly
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        self._proc = subprocess.Popen(
            cmd,
            cwd=str(work_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            creationflags=creationflags,
        )

        logger.info(f"[Supervisor] Core process spawned with PID {self._proc.pid}")

        # Continuously drain stdout & stderr in background threads to avoid OS pipe deadlock
        def _drain_stream(stream, prefix):
            try:
                for line in iter(stream.readline, b""):
                    msg = line.decode("utf-8", errors="replace").strip()
                    if msg:
                        logger.debug(f"[{prefix}] {msg}")
            except Exception:
                pass
            finally:
                try:
                    stream.close()
                except Exception:
                    pass

        if self._proc.stdout:
            threading.Thread(target=_drain_stream, args=(self._proc.stdout, "CoreOut"), daemon=True).start()
        if self._proc.stderr:
            threading.Thread(target=_drain_stream, args=(self._proc.stderr, "CoreErr"), daemon=True).start()

        # Assign process (and child processes spawned by venv launcher) to Job Object
        time.sleep(0.2)
        self._job_object.assign_process(self._proc.pid)
        try:
            for child in psutil.Process(self._proc.pid).children(recursive=True):
                self._job_object.assign_process(child.pid)
        except Exception:
            pass

    def _supervision_loop(self):
        """Health checking and automatic crash recovery loop (max 5 tries with exponential backoff)."""
        backoff_sec = 1.0
        max_backoff = 10.0
        max_restarts = 5
        restart_count = 0
        was_ready = False

        while not self._is_shutting_down:
            # 1. Check if process terminated unexpectedly
            if self._proc is not None and self._proc.poll() is not None:
                if self._is_shutting_down:
                    break

                exit_code = self._proc.returncode
                restart_count += 1
                logger.error(
                    f"[Supervisor] Core process exited unexpectedly (code {exit_code}, attempt {restart_count}/{max_restarts})."
                )
                with self._lock:
                    self._status = "crashed"

                self.signals.status_changed.emit("crashed", {})
                if self.on_status_change:
                    self.on_status_change("crashed", {})

                if restart_count > max_restarts:
                    logger.error("[Supervisor] Max restart attempts (5) reached. Core marked as 'error'.")
                    with self._lock:
                        self._status = "error"
                    self.signals.status_changed.emit("error", {})
                    if self.on_status_change:
                        self.on_status_change("error", {})
                    break

                # Exponential backoff restart
                logger.info(f"[Supervisor] Re-spawning Core in {backoff_sec:.1f}s...")
                time.sleep(backoff_sec)
                backoff_sec = min(backoff_sec * 2.0, max_backoff)

                if not self._is_shutting_down:
                    was_ready = False
                    self._spawn_core()
                continue

            # 2. Poll /health endpoint and verify per-launch auth nonce
            try:
                resp = requests.get(
                    f"{self.base_url}/health",
                    headers={"X-Pulsar-Token": self.token},
                    timeout=1.5,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("token_valid") is False:
                        logger.warning("[Supervisor] Stranger process detected on port 5000 (token mismatch)!")
                        time.sleep(1.0)
                        continue

                    new_status = data.get("status", "warming")
                    self._core_server_pid = data.get("pid")

                    # Ensure Core PID is also assigned to Job Object
                    if self._core_server_pid:
                        self._job_object.assign_process(self._core_server_pid)

                    with self._lock:
                        status_changed = (self._status != new_status)
                        self._status = new_status
                        self._components = data.get("components", {})

                    if status_changed:
                        self.signals.status_changed.emit(new_status, self._components)
                        if self.on_status_change:
                            self.on_status_change(new_status, self._components)

                    if new_status == "ready" and not was_ready:
                        was_ready = True
                        backoff_sec = 1.0  # Reset backoff on success
                        restart_count = 0
                        logger.info("[Supervisor] Core reached 'ready' state!")
                        self.signals.core_ready.emit()
                        if self.on_ready:
                            try:
                                self.on_ready()
                            except Exception as e:
                                logger.error(f"[Supervisor] on_ready callback error: {e}")

            except (requests.ConnectionError, requests.Timeout):
                with self._lock:
                    if self._status not in ("starting", "crashed"):
                        self._status = "unreachable"

            time.sleep(1.0)

    def shutdown(self):
        """Clean idempotent shutdown of Core (POST /shutdown, 5s wait) and release of Job Object."""
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        logger.info("[Supervisor] Shutting down Core process...")

        # 1. Try graceful authenticated HTTP POST /shutdown
        try:
            requests.post(
                f"{self.base_url}/shutdown",
                headers={"X-Pulsar-Token": self.token},
                timeout=1.5,
            )
            logger.info("[Supervisor] POST /shutdown accepted by Core")
        except Exception:
            pass

        # 2. Wait up to 5.0s for graceful process exit (per Claude Blueprint)
        if self._proc is not None:
            try:
                self._proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                logger.warning("[Supervisor] Core did not exit within 5.0s; force killing...")
                try:
                    self._proc.kill()
                    self._proc.wait(timeout=1.0)
                except Exception:
                    pass

        # 3. Close Job Object handle (kernel cleans up any residual children)
        self._job_object.close()
        with self._lock:
            self._status = "stopped"
        logger.info("[Supervisor] Core supervisor shutdown complete.")
