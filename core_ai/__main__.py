"""
Pulsar AI Assistant - CLI & Core Package Entry Point
===================================================
Enables running the assistant directly via:
    python -m core_ai
    python -m core_ai --web
    python -m core_ai --desktop
    python -m core_ai --status
"""

import sys
import os
import argparse
from pathlib import Path

# Ensure paths
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
for p in (PROJECT_ROOT, PROJECT_ROOT / "backend", PACKAGE_DIR, PROJECT_ROOT / "desktop"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from core_ai.config.paths import APP_NAME, IS_PRODUCTION, DATA_DIR, CONFIG_DIR, LOGS_DIR
from core_ai.utils.crash_handler import install_crash_handler

install_crash_handler()


def main():
    parser = argparse.ArgumentParser(
        prog="core_ai",
        description=f"{APP_NAME} - Enterprise AI Assistant Engine",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start the Flask Web API backend server (port 5000)",
    )
    parser.add_argument(
        "--desktop",
        action="store_true",
        help="Launch the native Windows desktop companion window",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Display storage paths, environment mode, and database diagnostics",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Specify port for web server (default: 5000)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{APP_NAME} 4.0.0",
    )

    args = parser.parse_args()

    if args.status:
        print(f"==================================================")
        print(f" {APP_NAME} System Diagnostics & Storage Report")
        print(f"==================================================")
        print(f" Environment: {'Production' if IS_PRODUCTION else 'Development'}")
        print(f" Project Root: {PROJECT_ROOT}")
        print(f" Config Dir:   {CONFIG_DIR}")
        print(f" Data Dir:     {DATA_DIR}")
        print(f" Logs Dir:     {LOGS_DIR}")
        print(f" Python:       {sys.version.split()[0]} ({sys.platform})")
        print(f"==================================================")
        return 0

    if args.web:
        import web
        return web.start_server(port=args.port)

    if args.desktop:
        from desktop.app_launcher import main as desktop_main
        return desktop_main()

    # Default action: Print status and help
    parser.print_help()
    print("\n[INFO] Current Active Paths:")
    print(f"  - Config: {CONFIG_DIR}")
    print(f"  - Data:   {DATA_DIR}")
    print(f"  - Logs:   {LOGS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
