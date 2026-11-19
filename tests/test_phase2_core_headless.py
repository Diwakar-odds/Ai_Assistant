"""
Pulsar AI Assistant - Phase 2 Automated Test Suite
=================================================
Validates the Headless Core (python -m pulsar.core):
1. Test GET /health reports status, components, PID, and uptime.
2. Test Origin validation middleware (blocks evil.com, allows localhost).
3. Test POST /shutdown security:
   - Rejected without token (401)
   - Rejected with invalid token (403)
   - Accepted with valid token (200)
4. Test GET /orb serves the 4D WebGL orb HTML.
5. Test OrbStateManager state transitions and rate-limiting.
6. Test Parent Watchdog: Core child process terminates automatically when parent process dies.
"""

import os
import sys
import time
import json
import socket
import subprocess
import requests
import psutil
import pytest
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Force headless environment
os.environ["PULSAR_DISABLE_COMPANION"] = "1"

from pulsar.core.server import setup_core_app, app
from pulsar.core.routes_health import configure_security_token, set_component_status, get_overall_status
from pulsar.core.orb_state import get_orb_state_manager, set_orb_state, get_orb_state


def get_free_port():
    """Finds a free ephemeral port for subprocess testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# =============================================================================
# 1. FLASK CLIENT UNIT & SECURITY TESTS
# =============================================================================

@pytest.fixture(scope="module")
def test_client():
    """Initializes the Flask test client with a test security token."""
    test_token = "pulsar-test-secret-nonce-12345"
    setup_core_app(token=test_token)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client, test_token


def test_health_endpoint(test_client):
    """Verify GET /health returns required JSON structure."""
    client, token = test_client
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()

    assert "status" in data
    assert "components" in data
    assert "pid" in data
    assert "uptime_sec" in data
    assert data["pid"] == os.getpid()
    assert isinstance(data["components"], dict)
    assert "server" in data["components"]


def test_health_with_token_validation(test_client):
    """Verify GET /health correctly checks token match if provided."""
    client, token = test_client
    # With correct token
    res_correct = client.get("/health", headers={"X-Pulsar-Token": token})
    assert res_correct.get_json().get("token_valid") is True

    # With wrong token
    res_wrong = client.get("/health", headers={"X-Pulsar-Token": "bad-token"})
    assert res_wrong.get_json().get("token_valid") is False


def test_orb_page_served(test_client):
    """Verify GET /orb returns the WebGL canvas orb HTML."""
    client, _ = test_client
    response = client.get("/orb")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    html = response.get_data(as_text=True)
    assert "orbCanvas" in html
    assert "setOrbState" in html


def test_origin_security_guard(test_client):
    """Verify malicious Origin headers are rejected with 403 Forbidden."""
    client, _ = test_client

    # Malicious origin on protected route (/shutdown)
    res_evil_shutdown = client.post("/shutdown", headers={"Origin": "http://evil-hackers.com"})
    assert res_evil_shutdown.status_code == 403

    # Valid origin on /shutdown (proceeds to token validation)
    res_valid_origin = client.post("/shutdown", headers={"Origin": "http://localhost:5000"})
    assert res_valid_origin.status_code != 403 or "Unauthorized" in res_valid_origin.get_data(as_text=True)


def test_shutdown_without_token_rejected(test_client):
    """Verify POST /shutdown without token returns 401 Unauthorized."""
    client, _ = test_client
    response = client.post("/shutdown")
    assert response.status_code == 401
    data = response.get_json()
    assert "Unauthorized" in data.get("error", "")


def test_shutdown_with_invalid_token_rejected(test_client):
    """Verify POST /shutdown with invalid token returns 403 Forbidden."""
    client, _ = test_client
    response = client.post("/shutdown", headers={"X-Pulsar-Token": "completely-wrong-token"})
    assert response.status_code == 403
    data = response.get_json()
    assert "Forbidden" in data.get("error", "")


def test_shutdown_with_valid_token_accepted(test_client):
    """Verify POST /shutdown with valid token returns 200 shutting_down."""
    client, token = test_client
    response = client.post("/shutdown", headers={"X-Pulsar-Token": token})
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("status") == "shutting_down"


def test_orb_state_manager():
    """Verify OrbStateManager handles state transitions and levels."""
    mgr = get_orb_state_manager()
    res = mgr.update_state(state="listening", level=0.85, force=True)
    assert res["state"] == "listening"
    assert res["level"] == 0.85

    snap = mgr.get_state()
    assert snap["state"] == "listening"
    assert snap["level"] == 0.85

    # Test invalid state is rejected gracefully
    mgr.update_state(state="invalid_state_xyz")
    assert mgr.get_state()["state"] == "listening"

    # Reset back to idle
    mgr.update_state(state="idle", level=0.0, force=True)
    assert mgr.get_state()["state"] == "idle"


# =============================================================================
# 2. SUBPROCESS INTEGRATION & WATCHDOG LIFECYCLE TESTS
# =============================================================================

def test_subprocess_core_launch_and_shutdown():
    """
    Spawns 'python -m pulsar.core' in a real subprocess, queries /health,
    then cleanly shuts it down via authenticated POST /shutdown.
    """
    python_exe = sys.executable
    port = get_free_port()
    token = f"live-test-token-{int(time.time())}"

    cmd = [
        python_exe,
        "-m",
        "pulsar.core",
        "--port",
        str(port),
        "--token",
        token,
        "--no-prewarm",
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PULSAR_DISABLE_COMPANION": "1"}
    )

    try:
        base_url = f"http://127.0.0.1:{port}"
        started = False
        data = None
        for _ in range(40):
            time.sleep(0.3)
            if proc.poll() is not None:
                stdout, stderr = proc.communicate(timeout=2)
                pytest.fail(
                    f"Core process exited prematurely with code {proc.returncode}.\n"
                    f"STDOUT: {stdout.decode('utf-8', errors='ignore')}\n"
                    f"STDERR: {stderr.decode('utf-8', errors='ignore')}"
                )

            try:
                r = requests.get(f"{base_url}/health", timeout=1)
                if r.status_code == 200:
                    data = r.json()
                    started = True
                    break
            except (requests.ConnectionError, requests.Timeout):
                continue

        assert started, f"Core server did not start on {base_url} within 12s"

        # Verify reported PID belongs to our process tree (shim or child)
        proc_tree_pids = {proc.pid}
        try:
            for child in psutil.Process(proc.pid).children(recursive=True):
                proc_tree_pids.add(child.pid)
        except Exception:
            pass
        assert data["pid"] in proc_tree_pids

        # Check /orb endpoint
        orb_res = requests.get(f"{base_url}/orb", timeout=2)
        assert orb_res.status_code == 200
        assert "orbCanvas" in orb_res.text

        # Test authenticated shutdown
        shutdown_res = requests.post(
            f"{base_url}/shutdown",
            headers={"X-Pulsar-Token": token},
            timeout=2
        )
        assert shutdown_res.status_code == 200
        assert shutdown_res.json()["status"] == "shutting_down"

        # Wait for process to exit cleanly within 5 seconds
        exit_code = proc.wait(timeout=5)
        assert exit_code == 0

    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=2)


def test_parent_watchdog_kills_core_on_parent_death():
    """
    Launches a temporary parent process that spawns the Core with --parent-pid.
    When the parent process terminates, the Core's watchdog must detect handle
    signaling and terminate itself immediately within 3.5s.
    """
    python_exe = sys.executable
    port = get_free_port()
    token = "watchdog-test-token"

    # Start a dummy parent process that stays alive until we kill it
    parent_script = "import time; time.sleep(60)"
    parent_proc = subprocess.Popen([python_exe, "-c", parent_script])
    time.sleep(0.3)

    # In Windows venv, track the underlying real python process if any
    try:
        children = psutil.Process(parent_proc.pid).children()
        real_parent_pid = children[0].pid if children else parent_proc.pid
    except Exception:
        real_parent_pid = parent_proc.pid

    # Launch Core linked to this real_parent_pid
    core_cmd = [
        python_exe,
        "-m",
        "pulsar.core",
        "--port",
        str(port),
        "--token",
        token,
        "--parent-pid",
        str(real_parent_pid),
        "--no-prewarm",
    ]

    core_proc = subprocess.Popen(
        core_cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PULSAR_DISABLE_COMPANION": "1"}
    )

    try:
        # 1. Verify Core is alive while parent is alive
        base_url = f"http://127.0.0.1:{port}"
        core_healthy = False
        core_server_pid = None
        for _ in range(40):
            time.sleep(0.3)
            try:
                r = requests.get(f"{base_url}/health", timeout=1)
                if r.status_code == 200:
                    core_healthy = True
                    core_server_pid = r.json().get("pid")
                    break
            except Exception:
                continue

        assert core_healthy, "Core failed to start while parent was alive"

        # 2. Kill the parent process to simulate Host crash or Task Manager termination
        parent_proc.kill()
        try:
            psutil.Process(real_parent_pid).kill()
        except Exception:
            pass

        # 3. Watchdog should trigger and terminate Core within 4.0 seconds!
        core_exited = False
        start_wait = time.time()
        while time.time() - start_wait < 4.0:
            if core_proc.poll() is not None:
                core_exited = True
                break
            if core_server_pid and not psutil.pid_exists(core_server_pid):
                core_exited = True
                break
            time.sleep(0.3)

        assert core_exited, f"Parent watchdog failed: Core PID {core_server_pid} still running after parent PID {real_parent_pid} died!"

    finally:
        if parent_proc.poll() is None:
            parent_proc.kill()
        if core_proc.poll() is None:
            core_proc.kill()
            core_proc.wait(timeout=2)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
