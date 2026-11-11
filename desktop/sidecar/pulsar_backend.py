#!/usr/bin/env python3
"""
Pulsar AI - Backend Sidecar Launcher
===================================
Launches modern_web_backend.py with full monorepo path resolution
and UTF-8 environment settings.
"""

import sys
import os
from pathlib import Path
import runpy

# Ensure UTF-8 output on Windows
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

# Resolve base project directory
sidecar_dir = Path(__file__).resolve().parent
project_root = sidecar_dir.parent.parent

# Inject monorepo paths
paths_to_add = [
    str(project_root),
    str(project_root / "backend"),
    str(project_root / "core_ai" / "src"),
    str(project_root / "core_ai" / "src" / "ai_assistant"),
    str(project_root / "shared"),
]

for p in paths_to_add:
    if p not in sys.path:
        sys.path.insert(0, p)

if __name__ == "__main__":
    backend_script = project_root / "backend" / "modern_web_backend.py"
    print(f"[PULSAR-SIDECAR] Starting Pulsar AI Backend from: {backend_script}")
    try:
        runpy.run_path(str(backend_script), run_name="__main__")
    except KeyboardInterrupt:
        print("[PULSAR-SIDECAR] Shutting down cleanly.")
        sys.exit(0)
    except BaseException as e:
        print(f"[PULSAR-SIDECAR] Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
