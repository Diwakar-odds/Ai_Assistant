"""
Pulsar Core - Win32 Parent Process Watchdog

Monitors the parent process handle using native Win32 kernel primitives.
If the parent Host process dies, crashes, or is killed in Task Manager,
the Core immediately shuts down without leaving orphaned processes.
"""

import os
import sys
import time
import logging
import threading
from typing import Optional, Callable

logger = logging.getLogger("pulsar.core.watchdog")

SYNCHRONIZE = 0x00100000
INFINITE = 0xFFFFFFFF
WAIT_OBJECT_0 = 0x00000000


def _windows_watchdog_loop(parent_pid: int, on_exit: Optional[Callable[[], None]] = None):
    """
    Win32 implementation: opens parent process with SYNCHRONIZE access
    and blocks on WaitForSingleObject with ZERO CPU overhead.
    """
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32

    # Open handle with SYNCHRONIZE rights
    h_parent = kernel32.OpenProcess(SYNCHRONIZE, False, parent_pid)
    if not h_parent:
        err = kernel32.GetLastError()
        logger.error(f"[Watchdog] Failed to open parent process PID {parent_pid} (Error: {err}). Parent may be dead.")
        if on_exit:
            on_exit()
        else:
            os._exit(0)
        return

    logger.info(f"[Watchdog] Attached to parent process PID {parent_pid} (handle: {h_parent}). Monitoring...")

    try:
        # Blocks indefinitely until parent process signals termination
        res = kernel32.WaitForSingleObject(h_parent, INFINITE)
        if res == WAIT_OBJECT_0:
            logger.warning(f"[Watchdog] Parent process PID {parent_pid} terminated. Initiating immediate Core exit.")
        else:
            logger.warning(f"[Watchdog] WaitForSingleObject returned unexpected code {res}. Exiting Core.")
    finally:
        kernel32.CloseHandle(h_parent)

    if on_exit:
        try:
            on_exit()
        except Exception:
            pass
    os._exit(0)


def _generic_watchdog_loop(parent_pid: int, on_exit: Optional[Callable[[], None]] = None):
    """Fallback polling loop for non-Windows platforms or test environments."""
    logger.info(f"[Watchdog] Generic polling attached to parent PID {parent_pid}")
    while True:
        try:
            # os.kill(pid, 0) checks if process exists without sending a signal
            os.kill(parent_pid, 0)
        except OSError:
            logger.warning(f"[Watchdog] Parent process PID {parent_pid} not found. Exiting Core.")
            break
        time.sleep(0.5)

    if on_exit:
        try:
            on_exit()
        except Exception:
            pass
    os._exit(0)


def start_parent_watchdog(parent_pid: int, on_exit: Optional[Callable[[], None]] = None) -> Optional[threading.Thread]:
    """
    Starts a background daemon thread that monitors the parent PID.
    When the parent exits, the Core process terminates immediately via os._exit(0).
    """
    if not parent_pid or parent_pid <= 0:
        logger.info("[Watchdog] No parent PID provided (standalone/debug mode). Watchdog inactive.")
        return None

    target = _windows_watchdog_loop if sys.platform == "win32" else _generic_watchdog_loop
    thread = threading.Thread(
        target=target,
        args=(parent_pid, on_exit),
        name="PulsarParentWatchdog",
        daemon=True
    )
    thread.start()
    return thread
