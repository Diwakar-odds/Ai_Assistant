"""
Pulsar AI Assistant - Phase 3 Automated Test Suite
=================================================
Validates the Native Host components:
1. Win32 Job Object: creation, limit configuration, process assignment, and kernel kill-on-close.
2. Core Supervisor: crypto token generation, URL construction, and status management.
3. Tray Icon: high-DPI QPainter vector icon generation.
4. Host Mutex: single-instance enforcement.
"""

import os
import sys
import time
import subprocess
import pytest
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pulsar.host.job_object import Win32JobObject
from pulsar.host.core_supervisor import CoreSupervisor
from pulsar.host.tray_app import create_tray_orb_icon
from pulsar.host.__main__ import acquire_host_mutex


def test_job_object_kernel_kill_on_close():
    """
    Spawns a long-running child process and assigns it to a Win32 Job Object.
    When the Job Object is closed, the OS kernel must kill the child immediately.
    """
    if sys.platform != "win32":
        pytest.skip("Win32 Job Object is Windows-specific")

    # Spawn long-sleeping child process
    child_cmd = [sys.executable, "-c", "import time; time.sleep(60)"]
    proc = subprocess.Popen(child_cmd)
    child_pid = proc.pid

    try:
        # Create Job Object and assign process
        job = Win32JobObject()
        assert job.handle is not None
        assigned = job.assign_process(child_pid)
        assert assigned is True

        # Process should be alive right now
        assert proc.poll() is None

        # Close the Job Object handle
        job.close()
        assert job.handle is None

        # OS kernel must terminate the process within 2 seconds
        terminated = False
        start_t = time.time()
        while time.time() - start_t < 3.0:
            if proc.poll() is not None:
                terminated = True
                break
            time.sleep(0.2)

        assert terminated is True, f"Child PID {child_pid} was not killed by OS kernel after Job Object close!"

    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=1)


def test_core_supervisor_token_and_config():
    """Verify Supervisor generates secure tokens and configures URLs."""
    sup = CoreSupervisor(port=5088)
    assert len(sup.token) == 32  # 16 bytes hex = 32 chars
    assert sup.base_url == "http://127.0.0.1:5088"
    assert sup.status == "stopped"


def test_tray_icon_generation():
    """Verify PySide6 creates a valid high-DPI vector orb icon."""
    from PySide6.QtWidgets import QApplication
    _app = QApplication.instance() or QApplication(sys.argv)

    icon = create_tray_orb_icon(size=64)
    assert icon is not None
    assert not icon.isNull()
    pix = icon.pixmap(64, 64)
    assert pix.width() == 64
    assert pix.height() == 64


def test_host_mutex_single_instance():
    """Verify Host single-instance mutex works on Windows."""
    if sys.platform != "win32":
        pytest.skip("Win32 Mutex is Windows-specific")

    test_mutex_name = f"Local\\Pulsar.Host.UnitTest.{os.getpid()}"
    # First acquisition with unique test mutex should succeed
    first = acquire_host_mutex(name=test_mutex_name)
    assert first is True

    # Second acquisition with same mutex name should detect duplicate
    second = acquire_host_mutex(name=test_mutex_name)
    assert second is False


def test_host_zero_ai_or_audio_imports():
    """Claude Hard Rule: Host must NEVER import torch, llama_cpp, whisper, pyaudio, sounddevice, or backend."""
    code = (
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, r'" + str(REPO_ROOT) + "')\n"
        "import pulsar.host.__main__\n"
        "import pulsar.host.console_ui\n"
        "import pulsar.host.orb_window\n"
        "import pulsar.host.tray_app\n"
        "import pulsar.host.dashboard_window\n"
        "import pulsar.host.core_supervisor\n"
        "forbidden = ['torch', 'llama_cpp', 'faster_whisper', 'pyaudio', 'sounddevice', 'backend.modern_web_backend']\n"
        "loaded = [m for m in forbidden if m in sys.modules]\n"
        "if loaded:\n"
        "    print(f'FORBIDDEN:{loaded}')\n"
        "    sys.exit(1)\n"
    )
    res = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Host imported forbidden modules: {res.stdout} {res.stderr}"


def test_tray_context_menu_survives_gc():
    """Verify PulsarTrayIcon retains its QMenu reference across Python garbage collection."""
    import gc
    from PySide6.QtWidgets import QApplication
    from pulsar.host.tray_app import PulsarTrayIcon

    _app = QApplication.instance() or QApplication(sys.argv)
    tray = PulsarTrayIcon()
    gc.collect()
    assert tray._menu is not None
    assert tray.contextMenu() is not None
    assert len(tray.contextMenu().actions()) >= 4


def test_orb_window_renders_vivid_pixels_and_reconciles():
    """Verify OrbWindow draws non-zero alpha pixels and obeys reconcile() hide/show."""
    from PySide6.QtWidgets import QApplication
    from pulsar.host.orb_window import OrbWindow

    app = QApplication.instance() or QApplication(sys.argv)
    orb = OrbWindow(port=5099)
    orb.set_orb_state("listening", 0.5)
    orb.set_reconciled_visible(True, delay_ms=0)
    app.processEvents()
    assert orb.isVisible() is True

    img = orb.grab().toImage()
    assert img.width() > 0 and img.height() > 0
    max_alpha = max(
        img.pixelColor(x, y).alpha()
        for y in range(0, img.height(), 4)
        for x in range(0, img.width(), 4)
    )
    assert max_alpha >= 180, f"Orb too faint (max_alpha={max_alpha})"

    orb.set_reconciled_visible(False)
    app.processEvents()
    assert orb.isVisible() is False
    orb.close()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
