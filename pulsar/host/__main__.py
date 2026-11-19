"""
Pulsar Native Host Main Entrypoint (python -m pulsar.host)
==========================================================
Claude Paradigm B Decoupled Architecture:
- Main Thread: Single PySide6 QApplication event loop.
- ZERO AI/audio imports (`torch`, `llama_cpp`, `faster_whisper`, `pyaudio`, `sounddevice`).
- Manages:
  1. Single-instance Win32 Named Mutex ('Local\\Pulsar.Host.v1') + QLocalServer IPC.
  2. PulsarTrayIcon (Windows 11 system tray with multi-DPI icon & persistent QMenu).
  3. DashboardWindow (PySide6 WebEngine React SPA, minimize-to-tray on [X]).
  4. OrbWindow (60 FPS click-through transparent 4D particle orb connected to Core Socket.IO).
  5. ONE `reconcile()` visibility state machine coordinating Dashboard & 4D Orb.
  6. CoreSupervisor (Win32 Job Object KILL_ON_JOB_CLOSE + CREATE_NO_WINDOW + max 5 retries).
  7. Pure-Python Master Developer Console v4.2.0 + interactive `pulsar> ` REPL.
"""

import os
import sys
import signal
import argparse
import logging
from pathlib import Path
from typing import Dict

# Ensure repo root is on sys.path (do NOT add backend/ or core_ai/ to Host!)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# High-DPI scaling & quiet Chromium configuration (must run before Qt imports)
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging --log-level=3 --no-sandbox"

logger = logging.getLogger("pulsar.host.main")

IPC_SERVER_NAME = "PulsarHostSingleInstanceV1"
_HOST_MUTEX_HANDLES: Dict[str, int] = {}


def get_current_desktop_info() -> tuple:
    """Returns (window_station_name, desktop_name) on Windows."""
    if sys.platform != "win32":
        return ("posix", "Default")
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hwinsta = user32.GetProcessWindowStation()
        hdesk = user32.GetThreadDesktop(kernel32.GetCurrentThreadId())
        buf_ws = ctypes.create_unicode_buffer(256)
        buf_dk = ctypes.create_unicode_buffer(256)
        needed = wintypes.DWORD()
        UOI_NAME = 2
        user32.GetUserObjectInformationW(hwinsta, UOI_NAME, buf_ws, 512, ctypes.byref(needed))
        user32.GetUserObjectInformationW(hdesk, UOI_NAME, buf_dk, 512, ctypes.byref(needed))
        return (buf_ws.value or "Unknown", buf_dk.value or "Unknown")
    except Exception:
        return ("Unknown", "Unknown")


def check_interactive_desktop() -> bool:
    """
    Claude Blueprint Failure #3 Guard:
    Detects when Host is launched inside a non-interactive / isolated sandbox desktop
    (e.g. `WinSta0\\exebox-...` inside an IDE agent terminal or Session 0 service)
    where Windows cannot display GUI windows, 4D Orb, or System Tray icons on the
    user's physical monitor (`WinSta0\\Default`).
    """
    if sys.platform != "win32":
        return True
    ws, desk = get_current_desktop_info()
    if ws.lower() == "winsta0" and desk.lower() == "default":
        return True

    sep = "=" * 84
    if sys.stdout is not None:
        print(f"\n{sep}", flush=True)
        print(f"  [BLOCKED] ISOLATED / HIDDEN WINDOWS DESKTOP DETECTED: {ws}\\{desk}", flush=True)
        print(f"{sep}", flush=True)
        print("  You launched `python web.py` from an IDE/Agent sandboxed terminal.", flush=True)
        print(f"  Windows isolates this terminal on hidden desktop '{ws}\\{desk}'.", flush=True)
        print("  GUI windows, 4D Glowing Orb, and System Tray icons created here are", flush=True)
        print("  INVISIBLE on your real desktop ('WinSta0\\Default')!", flush=True)
        print("", flush=True)
        print("  HOW TO LAUNCH PULSAR ON YOUR REAL DESKTOP (takes 2 seconds):", flush=True)
        print("    Option 1 (Easiest): Double-click  D:\\Projects\\Ai_Assistant\\Pulsar.exe", flush=True)
        print("    Option 2 (Terminal): Press Win + R -> type `powershell` -> Enter, then run:", flush=True)
        print("        cd D:\\Projects\\Ai_Assistant", flush=True)
        print("        .\\venv\\Scripts\\python.exe web.py", flush=True)
        print(f"{sep}\n", flush=True)
    logger.error(f"[Host] Refusing to start GUI on non-default desktop '{ws}\\{desk}'. Launch Pulsar.exe or use Windows PowerShell.")
    return False


def acquire_host_mutex(name: str = "Local\\Pulsar.Host.v1") -> bool:
    """Enforces single-instance of the Host process via Win32 Named Mutex."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h_mutex = kernel32.CreateMutexW(None, False, name)
        err = kernel32.GetLastError()
        if err == 183:  # ERROR_ALREADY_EXISTS
            if h_mutex:
                kernel32.CloseHandle(h_mutex)
            return False
        if h_mutex:
            # Persist handle so Windows holds the mutex for the full lifetime of Host
            _HOST_MUTEX_HANDLES[name] = h_mutex
        return True
    except Exception as e:
        logger.debug(f"[Host] Mutex check error: {e}")
        return True


def _signal_existing_host_to_show() -> bool:
    """Sends SHOW_DASHBOARD over QLocalSocket to the already-running Host instance."""
    try:
        from PySide6.QtNetwork import QLocalSocket
        sock = QLocalSocket()
        sock.connectToServer(IPC_SERVER_NAME)
        if sock.waitForConnected(800):
            sock.write(b"SHOW_DASHBOARD\n")
            sock.flush()
            sock.waitForBytesWritten(800)
            sock.disconnectFromServer()
            return True
    except Exception as e:
        logger.debug(f"[Host] Single-instance QLocalSocket signal error: {e}")
    return False


def run_standalone_orb_tray_test(port: int = 5000):
    """
    Phase 1 visual verification mode (`python web.py --test-orb`):
    Launches ONLY the 4D Glowing Orb + System Tray Icon with zero WebEngine and zero Core,
    cycling states (idle -> listening -> speaking -> thinking) every 3 seconds so you can
    instantly verify Orb transparency, click-through, topmost Z-order, and Tray icon.
    """
    if not check_interactive_desktop():
        sys.exit(2)

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from pulsar.host.orb_window import OrbWindow
    from pulsar.host.tray_app import PulsarTrayIcon, create_tray_orb_icon

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Pulsar Orb & Tray Test")
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(create_tray_orb_icon(64))

    orb = OrbWindow(port=port)
    states = ["idle", "listening", "speaking", "thinking"]
    idx = {"i": 0}

    def cycle():
        idx["i"] = (idx["i"] + 1) % len(states)
        st = states[idx["i"]]
        lvl = 0.65 if st in ("listening", "speaking") else 0.15
        orb.set_orb_state(st, lvl)
        print(f"[ORB TEST] State -> {st.upper()} (level={lvl}) | Pos=({orb.x()}, {orb.y()}) | Visible={orb.isVisible()}", flush=True)

    def quit_test():
        orb.hide_orb()
        tray.hide()
        app.quit()

    tray = PulsarTrayIcon(
        on_open_dashboard=lambda: print("[TRAY TEST] Tray left-click received!", flush=True),
        on_toggle_orb=orb.toggle_orb,
        on_exit=quit_test,
    )
    tray.update_core_status("Orb Test Mode")
    tray.show()
    orb.set_orb_state("idle", 0.25)
    orb.show_orb()

    print("\n" + "=" * 72, flush=True)
    print("  PULSAR PHASE-1 STANDALONE ORB + TRAY VISUAL TEST", flush=True)
    print("=" * 72, flush=True)
    print(f"  * 4D Orb:    Visible above taskbar at ({orb.x()}, {orb.y()}) [Size: {orb.width()}x{orb.height()}]", flush=True)
    print("  * Tray Icon: Active in Windows taskbar (check '^' Show hidden icons next to clock!)", flush=True)
    print("  * Click Test: Click through the Orb — clicks pass straight to windows behind it.", flush=True)
    print("  * Quit:       Press Ctrl+C here OR right-click Tray Icon -> 'Quit Pulsar'", flush=True)
    print("=" * 72 + "\n", flush=True)

    cycle_timer = QTimer()
    cycle_timer.timeout.connect(cycle)
    cycle_timer.start(3000)

    # Allow Ctrl+C to exit cleanly
    signal.signal(signal.SIGINT, lambda *_: quit_test())
    sig_timer = QTimer()
    sig_timer.timeout.connect(lambda: None)
    sig_timer.start(250)

    sys.exit(app.exec())


def run_host(port: int = 5000, start_dashboard: bool = False):
    """Initializes and runs the PySide6 Native Host (Paradigm B)."""
    from pulsar.logging_setup import configure_process_logging
    log_file = configure_process_logging("host", console_level=logging.INFO)

    logger.info("=== Starting Pulsar Native Host (PySide6 | Paradigm B) ===")

    # 0. Interactive Desktop Check (Claude Blueprint Failure #3)
    if not check_interactive_desktop():
        sys.exit(2)

    from pulsar.host.windows_integration import (
        set_process_app_user_model_id,
        allow_foreground_activation,
        get_app_icon_path,
        is_autostart_enabled,
        set_autostart_enabled,
        open_browser_dashboard,
        open_logs_folder,
    )

    # 1. Single Instance Check (Mutex + QLocalSocket wakeup of running Host)
    if not acquire_host_mutex():
        allow_foreground_activation()
        signaled = _signal_existing_host_to_show()
        if sys.stdout is not None:
            if signaled:
                print("[NOTICE] Pulsar is already running — brought existing Dashboard to front.")
            else:
                print("[NOTICE] Another instance of Pulsar Host is already running.")
        logger.warning("Another instance of Pulsar Host is already running. Exiting.")
        sys.exit(0)

    # 2. Stamp Windows 11 AppUserModelID BEFORE QApplication (enables clean Taskbar pinning!)
    set_process_app_user_model_id()

    # 3. Initialize Single Qt Application Event Loop
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication
    from PySide6.QtNetwork import QLocalServer

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Pulsar AI Assistant")
    # Prevent exit when Dashboard is closed to tray
    app.setQuitOnLastWindowClosed(False)

    from pulsar.host.core_supervisor import CoreSupervisor
    from pulsar.host.dashboard_window import DashboardWindow
    from pulsar.host.orb_window import OrbWindow
    from pulsar.host.tray_app import PulsarTrayIcon, create_tray_orb_icon

    ico_path = get_app_icon_path()
    app.setWindowIcon(QIcon(str(ico_path)) if ico_path.exists() else create_tray_orb_icon(64))

    # 3. Instantiate Pure-GUI Components (ZERO AI/Audio imports)
    dashboard = DashboardWindow(port=port)
    orb = OrbWindow(port=port)

    # State flags for single reconcile() visibility state machine
    always_show_orb = {"enabled": False}
    shown_tray_close_hint = {"done": False}
    quitting = {"active": False}

    # ------------------------------------------------------------------
    # ONE reconcile() function (Claude Blueprint Phase 3 + Browser Auto-Hide)
    # ------------------------------------------------------------------
    _EXCLUDED_TITLE_HINTS = (
        "visual studio code",
        "antigravity",
        "cursor",
        "launcher",
        "terminal",
        "command prompt",
        "powershell",
        "cmd.exe",
        "start.bat",
        "web.py",
    )

    def _detect_external_browser_dashboard_open() -> bool:
        """Detects if user opened http://localhost:5000 in Chrome/Edge/Brave/Firefox (un-minimized)."""
        if sys.platform != "win32":
            return False
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            dwmapi = getattr(ctypes.windll, "dwmapi", None)
            own_dash_hwnd = int(dashboard.winId()) if dashboard.isVisible() else 0
            own_orb_hwnd = int(orb.winId()) if orb.isVisible() else 0
            found = [False]
            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def _cb(hwnd, _lp):
                if hwnd in (own_dash_hwnd, own_orb_hwnd):
                    return True
                if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
                    return True
                cls_buf = ctypes.create_unicode_buffer(128)
                user32.GetClassNameW(hwnd, cls_buf, 128)
                cls_l = cls_buf.value.lower()
                if any(c in cls_l for c in ("console", "cascadia", "pseudoconsole", "terminal")):
                    return True
                tlen = user32.GetWindowTextLengthW(hwnd)
                if tlen <= 0:
                    return True
                tbuf = ctypes.create_unicode_buffer(tlen + 1)
                user32.GetWindowTextW(hwnd, tbuf, tlen + 1)
                tl = tbuf.value.strip().lower()
                if "pulsar ai assistant" not in tl:
                    return True
                if any(h in tl for h in _EXCLUDED_TITLE_HINTS):
                    return True
                if dwmapi is not None:
                    cloaked = ctypes.c_int(0)
                    if dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked)) == 0:
                        if cloaked.value != 0:
                            return True
                found[0] = True
                return False

            user32.EnumWindows(WNDENUMPROC(_cb), 0)
            return found[0]
        except Exception:
            return False

    def reconcile():
        """
        Single authoritative visibility rule:
        - When Native Dashboard OR Browser WebUI (localhost:5000) is visible & un-minimized -> Orb hides
          (unless 'Always Show Orb' is toggled ON in Tray menu).
        - Otherwise -> 136px crystal-clear 4D Wireframe Orb fades in smoothly above the taskbar.
        """
        if quitting["active"]:
            return
        native_dash_open = dashboard.isVisible() and not dashboard.isMinimized()
        browser_dash_open = False if native_dash_open else _detect_external_browser_dashboard_open()
        dash_open = native_dash_open or browser_dash_open
        orb_should_show = True if always_show_orb["enabled"] else (not dash_open)
        orb.set_reconciled_visible(orb_should_show)

    # Lightweight 1.0s watcher so opening/minimizing localhost:5000 in Chrome/Edge auto-hides/shows Orb
    browser_watch_timer = QTimer()
    browser_watch_timer.timeout.connect(reconcile)
    browser_watch_timer.start(1000)

    def on_closed_to_tray():
        """Show one-time 'still running in tray' notification on first [X] close."""
        if not shown_tray_close_hint["done"]:
            shown_tray_close_hint["done"] = True
            tray.showMessage(
                "Pulsar AI Assistant",
                "Pulsar is still running in the tray. 4D Orb is now active above the taskbar.",
                tray.icon(),
                3500,
            )

    dashboard.dashboard_opened.connect(reconcile)
    dashboard.dashboard_closed.connect(reconcile)
    dashboard.closed_to_tray.connect(on_closed_to_tray)

    # 4. Core Supervisor & Tray Icon Actions
    supervisor = CoreSupervisor(port=port)

    def open_or_restore_dashboard():
        dashboard.show_and_focus()
        reconcile()

    def toggle_orb_action():
        orb.toggle_orb()

    def set_always_show_orb(checked: bool):
        always_show_orb["enabled"] = bool(checked)
        reconcile()

    def toggle_autostart_action(checked: bool):
        ok = set_autostart_enabled(bool(checked))
        if ok:
            tray.showMessage(
                "Pulsar AI Assistant",
                "Pulsar will start automatically with Windows." if checked else "Windows auto-start disabled.",
                tray.icon(),
                2500,
            )

    def restart_core_action():
        tray.update_core_status("Restarting...")
        orb.set_orb_state("warming", 0.25)
        supervisor.restart_core()

    def full_exit_action(*_args):
        if quitting["active"]:
            return
        quitting["active"] = True
        logger.info("[Host] Quit requested. Shutting down Core & releasing Job Object...")
        try:
            ipc_server.close()
        except Exception:
            pass
        orb.stop_core_ipc()
        orb.hide_orb()
        dashboard.allow_real_close()
        dashboard.close()
        tray.hide()
        supervisor.shutdown()
        app.quit()

    tray = PulsarTrayIcon(
        on_open_dashboard=open_or_restore_dashboard,
        on_open_browser=lambda: open_browser_dashboard(port),
        on_toggle_orb=toggle_orb_action,
        on_toggle_always_show_orb=set_always_show_orb,
        on_toggle_autostart=toggle_autostart_action,
        autostart_initial=is_autostart_enabled(),
        on_restart_core=restart_core_action,
        on_open_logs=open_logs_folder,
        on_exit=full_exit_action,
    )

    # 5. QLocalServer for second-launch Dashboard focus
    QLocalServer.removeServer(IPC_SERVER_NAME)
    ipc_server = QLocalServer()
    if ipc_server.listen(IPC_SERVER_NAME):
        def _on_ipc_connection():
            conn = ipc_server.nextPendingConnection()
            if not conn:
                return
            if conn.waitForReadyRead(500):
                msg = bytes(conn.readAll()).decode("utf-8", errors="ignore").strip()
                if "SHOW_DASHBOARD" in msg:
                    logger.info("[Host] Second launch requested Dashboard focus.")
                    open_or_restore_dashboard()
            conn.disconnectFromServer()
        ipc_server.newConnection.connect(_on_ipc_connection)
    else:
        logger.debug(f"[Host] QLocalServer listen note: {ipc_server.errorString()}")

    # 6. Core Supervisor & Thread-Safe UI Signal Connections
    def on_core_ready():
        logger.info("[Host] Core is ready (Main UI Thread). Loading dashboard & connecting 30 Hz Orb IPC...")
        dashboard.load_dashboard(focus_if_visible=True)
        orb.set_orb_state("idle", 0.0)
        orb.start_core_ipc()
        tray.update_core_status("Ready")
        tray.showMessage(
            "Pulsar AI Assistant",
            "Pulsar Core is READY! Say 'Hey Pulsar' or click the Tray icon anytime.",
            tray.icon(),
            3500,
        )

        # Pure-Python Master Developer Console (ZERO AI/backend imports in Host!)
        try:
            from pulsar.host.console_ui import render_host_developer_console, start_host_repl
            render_host_developer_console(port=port, token=supervisor.token, log_path=str(log_file))
            start_host_repl(port=port)
        except Exception as e:
            logger.warning(f"[Host] Console UI notice: {e}")

    def on_status_change(status: str, components: dict):
        tray.update_core_status(status)
        if status in ("crashed", "error", "unreachable"):
            orb.set_orb_state("error", 0.35)
        elif status == "warming":
            orb.set_orb_state("warming", 0.12)
        elif status == "ready":
            orb.set_orb_state("idle", 0.05)

    supervisor.signals.core_ready.connect(on_core_ready)
    supervisor.signals.status_changed.connect(on_status_change)

    app.aboutToQuit.connect(supervisor.shutdown)
    # Handle Windows shutdown/logoff (WM_QUERYENDSESSION) cleanly so Pulsar never blocks reboot
    app.commitDataRequest.connect(full_exit_action)

    # 7. Clean Ctrl+C / SIGTERM handling inside Qt event loop
    def _handle_sigint(*_):
        logger.info("[Host] Ctrl+C received. Initiating clean shutdown...")
        QTimer.singleShot(0, full_exit_action)

    signal.signal(signal.SIGINT, _handle_sigint)
    try:
        signal.signal(signal.SIGTERM, _handle_sigint)
    except Exception:
        pass
    sig_pump = QTimer()
    sig_pump.timeout.connect(lambda: None)
    sig_pump.start(250)

    # 8. Show Tray, Spawn Core, Apply Single reconcile()
    tray.show()
    supervisor.start()

    if start_dashboard:
        dashboard.show_and_focus()
    else:
        logger.info("Host running in tray-only mode. 4D Orb active above taskbar.")

    # Reconcile initial visibility (if tray-only -> Orb appears immediately; if dashboard open -> Orb appears on minimize/close)
    reconcile()

    # Show startup balloon AFTER Qt event loop starts
    QTimer.singleShot(
        800,
        lambda: tray.showMessage(
            "Pulsar AI Assistant",
            "Pulsar started! Tray icon active (check '^' hidden icons if not pinned).",
            tray.icon(),
            3000,
        ),
    )

    logger.info(f"=== Pulsar Host UI initialized (PID: {os.getpid()} | Log: {log_file}) ===")
    sys.exit(app.exec())


def main():
    parser = argparse.ArgumentParser(description="Pulsar Native Host (PySide6)")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 5000)), help="Core port (default: 5000)")
    parser.add_argument("--open", dest="open_dashboard", action="store_true", help="Open native Dashboard window immediately on startup")
    parser.add_argument("--minimized", "--tray", dest="start_minimized", action="store_true", help="Start minimized in system tray with 4D Orb visible (default)")
    parser.add_argument("--test-orb", action="store_true", help="Run standalone Phase-1 4D Orb + Tray visual test")
    args = parser.parse_args()

    if args.test_orb:
        run_standalone_orb_tray_test(port=args.port)
    else:
        run_host(port=args.port, start_dashboard=bool(args.open_dashboard and not args.start_minimized))


if __name__ == "__main__":
    main()
