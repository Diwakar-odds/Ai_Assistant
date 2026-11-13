"""
Backend Services & Background Monitors Package
=============================================
Consolidates all background web services, agents bridge, voice streaming,
system telemetry, settings management, and automated monitors.
"""

import sys
import os
import importlib

services_dir = os.path.dirname(os.path.abspath(__file__))
if services_dir not in sys.path:
    sys.path.insert(0, services_dir)

_SERVICE_MODULES = {
    "agent_brain",
    "voice_service",
    "settings_manager",
    "system_monitor",
    "telemetry_dashboard",
    "telemetry_tracer",
    "notification_monitor",
    "insights_engine",
    "startup_sequence",
    "learning_api",
    "learning_dashboard_api",
    "learning_integration",
    "app_integration_api",
    "user_preferences",
}

def __getattr__(name: str):
    if name in _SERVICE_MODULES:
        try:
            mod = importlib.import_module(f".{name}", package=__name__)
            globals()[name] = mod
            return mod
        except Exception as e:
            raise AttributeError(f"Could not load service {name}: {e}") from e
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __dir__():
    return sorted(list(globals().keys()) + list(_SERVICE_MODULES))

__all__ = sorted(list(_SERVICE_MODULES))
