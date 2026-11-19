"""
Pulsar AI Assistant - Per-Process Rotating Logging Setup
========================================================
Configures clean per-process rotating log files in:
    %LOCALAPPDATA%\\Pulsar\\logs\\pulsar_<role>.log

Zero GUI and zero AI imports — safe for Host, Core, and Audio Worker processes.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_log_dir() -> Path:
    """Returns %LOCALAPPDATA%/Pulsar/logs on Windows (or repo logs/ fallback)."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        log_dir = Path(local_app_data) / "Pulsar" / "logs"
    else:
        log_dir = Path(__file__).resolve().parent.parent / "logs" / "pulsar"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        log_dir = Path(__file__).resolve().parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def configure_process_logging(role: str, console_level: int = logging.INFO, file_level: int = logging.DEBUG) -> Path:
    """
    Configures root logging with a RotatingFileHandler (5 MB x 3 backups)
    and a clean StreamHandler for the console.
    """
    log_dir = get_log_dir()
    log_file = log_dir / f"pulsar_{role}.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(min(console_level, file_level))

    # Avoid duplicating handlers if called more than once
    has_file = any(
        isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "").endswith(f"pulsar_{role}.log")
        for h in root_logger.handlers
    )
    has_console = any(
        type(h) is logging.StreamHandler
        for h in root_logger.handlers
    )

    fmt_file = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | [PID:%(process)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fmt_console = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    if not has_file:
        try:
            fh = RotatingFileHandler(
                str(log_file),
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            fh.setLevel(file_level)
            fh.setFormatter(fmt_file)
            root_logger.addHandler(fh)
        except Exception:
            pass

    if not has_console and sys.stdout is not None:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(console_level)
        ch.setFormatter(fmt_console)
        root_logger.addHandler(ch)

    return log_file
