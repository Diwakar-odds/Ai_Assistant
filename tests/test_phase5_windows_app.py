"""
Pulsar AI Assistant - Phase 5 Production Windows 11 App Test Suite
==================================================================
Verifies native Windows 11 desktop application packaging, AppUserModelID,
Start Menu registration, pythonw.exe windowless safety, and production Tray menu.
"""

import os
import sys
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_native_exe_and_multi_res_ico():
    """Verify compiled Pulsar.exe (PE64) and multi-res pulsar_app.ico exist."""
    exe = REPO_ROOT / "Pulsar.exe"
    ico = REPO_ROOT / "assets" / "pulsar_app.ico"

    assert exe.exists(), "Pulsar.exe missing — run scripts/build_windows_app.py"
    assert exe.stat().st_size > 20_000
    assert exe.read_bytes()[:2] == b"MZ", "Pulsar.exe is not a valid Windows PE executable"

    assert ico.exists(), "assets/pulsar_app.ico missing"
    from PIL import Image
    im = Image.open(ico)
    sizes = im.info.get("sizes", set())
    for expected in ((16, 16), (32, 32), (48, 48), (256, 256)):
        assert expected in sizes, f"Missing icon size {expected} in pulsar_app.ico"


def test_start_menu_shortcut_has_app_user_model_id():
    """Verify Start Menu .lnk is stamped with System.AppUserModel.ID for clean Taskbar pinning."""
    if sys.platform != "win32":
        pytest.skip("Windows-only shortcut test")

    import pythoncom
    from win32com.propsys import propsys, pscon
    from pulsar.host.windows_integration import PULSAR_APP_ID, PULSAR_DISPLAY_NAME

    lnk = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{PULSAR_DISPLAY_NAME}.lnk"
    assert lnk.exists(), f"Start Menu shortcut missing: {lnk}"

    pythoncom.CoInitialize()
    try:
        store = propsys.SHGetPropertyStoreFromParsingName(str(lnk))
        val = store.GetValue(pscon.PKEY_AppUserModel_ID).GetValue()
        assert val == PULSAR_APP_ID, f"Expected AppUserModelID '{PULSAR_APP_ID}', got '{val}'"
    finally:
        pythoncom.CoUninitialize()


def test_window_taskbar_identity_binding_and_production_tray_menu():
    """Verify AppUserModelID + SHGetPropertyStoreForWindow + full production Tray menu."""
    if sys.platform != "win32":
        pytest.skip("Windows-only taskbar test")

    from PySide6.QtWidgets import QApplication
    from pulsar.host.windows_integration import set_process_app_user_model_id, configure_window_taskbar_identity
    from pulsar.host.dashboard_window import DashboardWindow
    from pulsar.host.tray_app import PulsarTrayIcon

    assert set_process_app_user_model_id() is True

    app = QApplication.instance() or QApplication(sys.argv)
    dash = DashboardWindow(port=5099)
    hwnd = int(dash.winId())
    assert configure_window_taskbar_identity(hwnd) is True
    dash.allow_real_close()
    dash.close()

    tray = PulsarTrayIcon()
    labels = [a.text() for a in tray.contextMenu().actions() if not a.isSeparator()]
    for required in (
        "Open Pulsar Dashboard",
        "Open in Web Browser",
        "Toggle 4D Orb",
        "Always Show Orb",
        "Start with Windows",
        "Restart Core Engine",
        "Open Logs Folder",
        "Quit Pulsar",
    ):
        assert required in labels, f"Missing production tray action: {required}"


def test_pythonw_windowless_none_stdout_safety(monkeypatch):
    """Verify Host console UI & logging never crash when sys.stdout is None (pythonw.exe)."""
    from pulsar.host.console_ui import render_host_developer_console, start_host_repl
    from pulsar.logging_setup import configure_process_logging

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stdin", None)

    log_path = configure_process_logging("host_test")
    assert log_path.parent.exists()
    render_host_developer_console(port=5099)  # Must silently no-op without raising
    start_host_repl(port=5099)                # Must silently no-op without raising


if __name__ == "__main__":
    pytest.main(["-v", __file__])
