"""
Pulsar Ambient AI Agent - Developer Telemetry Tracer
===================================================
Provides high-density, real-time structured telemetry for:
- Inbound requests (Terminal, Web App, Voice Hotkey, Desktop Companion)
- Intent Routing (Local LLM vs Cloud LLM vs Fast Rule Dispatch)
- Compute & Latency Metrics (Tokens, ms, status)
- Destination Dispatches (Frontend WS, Companion Mascot, Speech, OS Actions)
- Ambient Observer Notifications (Gmail, WhatsApp, Calendar alerts)
"""

import sys
import os
import time
import threading
from datetime import datetime
from typing import Optional, List, Any, Dict

# Ensure console supports UTF-8 on Windows
if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr is not None and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure console supports ANSI colors on Windows
if sys.platform == 'win32':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def safe_print(msg: str):
    """Prints message safely across all Windows console encodings (UTF-8, cp1252, etc)."""
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            sys.stdout.buffer.write((msg + "\n").encode('utf-8'))
            sys.stdout.buffer.flush()
        except Exception:
            clean_msg = msg.encode('ascii', errors='replace').decode('ascii')
            print(clean_msg)


class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    RED = '\033[91m'
    GRAY = '\033[90m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


class TelemetryTracer:
    """Thread-safe telemetry stream logger for developer transparency."""
    
    _lock = threading.Lock()
    
    @classmethod
    def _timestamp(cls) -> str:
        return datetime.now().strftime('%H:%M:%S')

    @classmethod
    def log_inbound(cls, source: str, query: str, context: Optional[Dict[str, Any]] = None):
        """Logs an inbound user command or request."""
        with cls._lock:
            ts = cls._timestamp()
            q_clean = query.strip().replace('\n', ' ')
            if len(q_clean) > 80:
                q_clean = q_clean[:77] + '...'
            safe_print(f"{Colors.GRAY}[{ts}]{Colors.RESET} {Colors.CYAN}{Colors.BOLD}📥 [INBOUND]{Colors.RESET}  Source: {Colors.WHITE}{source}{Colors.RESET} | Query: {Colors.CYAN}\"{q_clean}\"{Colors.RESET}")

    @classmethod
    def log_router(cls, intent: str, engine: str, details: Optional[str] = None):
        """Logs the routing decision made by the system."""
        with cls._lock:
            ts = cls._timestamp()
            det = f" | {details}" if details else ""
            safe_print(f"{Colors.GRAY}[{ts}]{Colors.RESET} {Colors.MAGENTA}{Colors.BOLD}🔀 [ROUTER]{Colors.RESET}   Intent: {Colors.WHITE}{intent}{Colors.RESET} | Target: {Colors.MAGENTA}{engine}{Colors.RESET}{det}")

    @classmethod
    def log_compute(cls, latency_ms: float, tokens: Optional[int] = None, tps: Optional[float] = None, memory_mb: Optional[float] = None, status: str = "OK"):
        """Logs the compute and latency metrics."""
        with cls._lock:
            ts = cls._timestamp()
            parts = [f"Latency: {Colors.BOLD}{latency_ms:.1f}ms{Colors.RESET}"]
            if tokens is not None:
                parts.append(f"Tokens: {tokens}")
            if tps is not None:
                parts.append(f"Speed: {tps:.1f} tps")
            if memory_mb is not None:
                parts.append(f"VRAM/Mem: {memory_mb:.1f} MB")
            parts.append(f"Status: {Colors.GREEN if 'OK' in status or '200' in status else Colors.RED}{status}{Colors.RESET}")
            stats_str = " | ".join(parts)
            safe_print(f"{Colors.GRAY}[{ts}]{Colors.RESET} {Colors.YELLOW}{Colors.BOLD}⚡ [COMPUTE]{Colors.RESET}  {stats_str}")

    @classmethod
    def log_dispatch(cls, destinations: List[str], response_snippet: Optional[str] = None):
        """Logs where the response / action is being dispatched."""
        with cls._lock:
            ts = cls._timestamp()
            dests = " -> ".join([f"{Colors.GREEN}[{d}]{Colors.RESET}" for d in destinations])
            safe_print(f"{Colors.GRAY}[{ts}]{Colors.RESET} {Colors.GREEN}{Colors.BOLD}📤 [DISPATCH]{Colors.RESET} -> {dests}")
            if response_snippet:
                snip = response_snippet.strip().replace('\n', ' ')
                if len(snip) > 100:
                    snip = snip[:97] + '...'
                safe_print(f"{Colors.GRAY}[{ts}]{Colors.RESET} {Colors.WHITE}{Colors.BOLD}💬 [PULSAR]{Colors.RESET}   \"{snip}\"")

    @classmethod
    def log_screen_action(cls, action: str, details: str, latency_ms: float):
        """Logs desktop screen perception and click/type execution."""
        with cls._lock:
            ts = cls._timestamp()
            safe_print(f"{Colors.GRAY}[{ts}]{Colors.RESET} {Colors.BLUE}{Colors.BOLD}👁️ [VISION]{Colors.RESET}   Action: {action} ({details}) | Latency: {latency_ms:.1f}ms")

    @classmethod
    def log_notification(cls, observer: str, title: str, priority: str = "normal"):
        """Logs an incoming ambient notification."""
        with cls._lock:
            ts = cls._timestamp()
            color = Colors.RED if priority.lower() == 'critical' else (Colors.YELLOW if priority.lower() == 'high' else Colors.BLUE)
            safe_print(f"{Colors.GRAY}[{ts}]{Colors.RESET} {Colors.YELLOW}{Colors.BOLD}🔔 [MONITOR]{Colors.RESET}  Observer: {Colors.WHITE}{observer}{Colors.RESET} | Priority: {color}[{priority.upper()}]{Colors.RESET} | \"{title}\"")


# Global singleton helper
telemetry = TelemetryTracer
