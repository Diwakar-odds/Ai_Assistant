"""
Pulsar Headless Core CLI Entrypoint (python -m pulsar.core)

Usage:
    python -m pulsar.core --port 5000 --token <SECRET_TOKEN> --parent-pid <PID>
"""

import os
import sys
import argparse
import logging

# Ensure repo root is on sys.path
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


def main():
    parser = argparse.ArgumentParser(description="Pulsar AI Assistant - Headless Core Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (strictly loopback 127.0.0.1)")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 5000)), help="Port to bind (default: 5000)")
    parser.add_argument("--token", type=str, default=os.getenv("PULSAR_AUTH_TOKEN"), help="Per-launch authentication token")
    parser.add_argument("--parent-pid", type=int, default=int(os.getenv("PULSAR_PARENT_PID", 0)) or None, help="Parent Host PID for watchdog")
    parser.add_argument("--no-prewarm", action="store_true", help="Skip heavy background pre-warming (for rapid testing)")

    args = parser.parse_args()

    # Configure per-process rotating logging in %LOCALAPPDATA%\Pulsar\logs
    from pulsar.logging_setup import configure_process_logging
    configure_process_logging("core", console_level=logging.INFO)

    # Force strictly 127.0.0.1 loopback
    if args.host not in ("127.0.0.1", "localhost"):
        logging.warning(f"Rejecting non-loopback host '{args.host}'. Enforcing 127.0.0.1.")
        args.host = "127.0.0.1"

    from pulsar.core.server import run_core
    run_core(
        host=args.host,
        port=args.port,
        token=args.token,
        parent_pid=args.parent_pid,
        prewarm=not args.no_prewarm,
    )


if __name__ == "__main__":
    main()
