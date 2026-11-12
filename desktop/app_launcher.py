#!/usr/bin/env python3
"""
PULSAR AI ASSISTANT - NATIVE WINDOWS DESKTOP APP
================================================
Native Windows Desktop Application powered by Microsoft Edge WebView2,
complete with System Tray integration, Floating 4D Glowing Orb,
Single-Instance Mutex, WebView2 pre-flight runtime validation, dynamic port
resolution, and full offline/online AI Chatbot features.
"""

import sys
import os
import time
import socket
import ctypes
import threading
import urllib.request
import urllib.error
import subprocess
import webbrowser
from pathlib import Path
import runpy
from typing import Optional

# Enforce UTF-8 globally to prevent Windows console encoding issues
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

# Suppress noisy Chromium / WebView2 background network spam
os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
    "--disable-features=OptimizationGuideModelDownloading,OptimizationHintsFetching,OptimizationTargetPrediction "
    "--disable-sync --disable-background-networking --disable-component-update --log-level=3"
)

APP_MUTEX_NAME = "Local\\Pulsar_AI_Desktop_App_Mutex"
WEBVIEW2_CLIENT_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
WEBVIEW2_DOWNLOAD_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_base_path() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)).resolve()
    return Path(__file__).resolve().parent.parent


project_root = get_base_path()

# Setup Python paths for the monorepo architecture
paths_to_add = [
    str(project_root),
    str(project_root / "backend"),
    str(project_root / "core_ai" / "src"),
    str(project_root / "core_ai" / "src" / "ai_assistant"),
    str(project_root / "shared"),
    str(project_root / "desktop"),
]
for p in paths_to_add:
    if p not in sys.path:
        sys.path.insert(0, p)


def _extract_companion_port(argv) -> int:
    for idx, arg in enumerate(argv):
        if arg == "--port" and idx + 1 < len(argv) and argv[idx + 1].isdigit():
            return int(argv[idx + 1])
        if arg == "--companion" and idx + 1 < len(argv) and argv[idx + 1].isdigit():
            return int(argv[idx + 1])
    for arg in argv:
        if arg.isdigit():
            return int(arg)
    for env_key in ("PULSAR_PORT", "PORT"):
        val = os.environ.get(env_key, "")
        if val.isdigit():
            return int(val)
    return 5000


def _show_windows_message(title: str, message: str, flags: int = 0x40) -> int:
    """Display native Win32 dialog without requiring tkinter."""
    if sys.platform == "win32":
        try:
            return ctypes.windll.user32.MessageBoxW(0, message, title, flags)
        except Exception:
            pass
    print(f"[{title}] {message}")
    return 1


def check_webview2_installed() -> bool:
    """Verify Microsoft Edge WebView2 Runtime is available on Windows."""
    if sys.platform != "win32":
        return True
    try:
        import winreg

        reg_checks = [
            (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_CLIENT_GUID}"),
            (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_CLIENT_GUID}"),
            (winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_CLIENT_GUID}"),
        ]
        for hive, subkey in reg_checks:
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    pv, _ = winreg.QueryValueEx(key, "pv")
                    if pv and str(pv).strip() and str(pv).strip() != "0.0.0.0":
                        return True
            except FileNotFoundError:
                continue
            except Exception:
                continue

        # Secondary filesystem check (per-machine Evergreen installation)
        for base_env in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
            root = os.environ.get(base_env)
            if root:
                wv_dir = Path(root) / "Microsoft" / "EdgeWebView" / "Application"
                if wv_dir.exists() and any(wv_dir.iterdir()):
                    return True
    except Exception:
        # Don't block startup if registry access itself errors unexpectedly
        return True
    return False


def _focus_existing_window() -> bool:
    """Bring already-running Pulsar AI Assistant window to the foreground."""
    if sys.platform != "win32":
        return False
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "Pulsar AI Assistant")
        if hwnd:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return True
    except Exception:
        pass
    return False


def acquire_single_instance_mutex():
    """Prevent multiple simultaneous instances of the desktop GUI window."""
    if sys.platform != "win32":
        return None
    try:
        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, True, APP_MUTEX_NAME)
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            if not _focus_existing_window():
                _show_windows_message(
                    "Pulsar AI Assistant",
                    "Pulsar AI Assistant is already running (check your Windows System Tray).",
                    0x40,
                )
            sys.exit(0)
        return mutex
    except Exception:
        return None


def is_server_online(port: int = 5000) -> bool:
    """Quick non-blocking check if Flask server is already online."""
    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=0.8)
        return req.status in (200, 302, 304)
    except Exception:
        try:
            req = urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=0.8)
            return req.status in (200, 302, 304)
        except Exception:
            return False


def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    """Check whether a local TCP port can be bound cleanly."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def resolve_app_port(preferred: int = 5000, max_scan: int = 50) -> tuple[int, bool]:
    """
    Resolve an available port for Pulsar backend.
    Returns (port, should_start_server). Reuses an already running Pulsar server if healthy.
    """
    env_port = os.environ.get("PORT", "").strip()
    if env_port.isdigit():
        preferred = int(env_port)

    if is_server_online(preferred):
        return preferred, False

    if is_port_free(preferred):
        return preferred, True

    for candidate in range(preferred + 1, preferred + max_scan + 1):
        if is_server_online(candidate):
            return candidate, False
        if is_port_free(candidate):
            return candidate, True

    # Last resort: ask OS for ephemeral free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1]), True


def start_backend_server(port: int = 5000):
    """Starts the Flask API Gateway in the background on the resolved port."""
    if is_server_online(port):
        print(f"[DESKTOP] Pulsar Backend is already running on port {port}.")
        return

    os.environ["PORT"] = str(port)
    os.environ["PULSAR_PORT"] = str(port)
    os.environ["PULSAR_DASHBOARD_URL"] = f"http://127.0.0.1:{port}"

    print(f"[DESKTOP] Starting Pulsar AI Backend Server on port {port}...")
    try:
        try:
            import modern_web_backend
            modern_web_backend.start_server(host="127.0.0.1", port=port)
            return
        except ImportError:
            pass

        backend_script = project_root / "backend" / "modern_web_backend.py"
        if backend_script.exists():
            runpy.run_path(str(backend_script), run_name="__main__")
        else:
            print(f"[DESKTOP] CRITICAL: Backend entrypoint not found at {backend_script}")
    except BaseException as e:
        print(f"[DESKTOP] Backend server stopped: {e}")


def wait_for_server(port: int = 5000, timeout: int = 60) -> bool:
    """Polls the Flask server until it is fully ready."""
    print(f"[DESKTOP] Waiting for AI Engine on port {port} to initialize...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_server_online(port):
            print("[DESKTOP] AI Engine is ready!")
            return True
        time.sleep(0.6)
    return False


def _spawn_companion(port: int):
    """Spawn the Win32 floating 4D orb overlay in both frozen and dev environments."""
    env = os.environ.copy()
    env["PULSAR_PORT"] = str(port)
    env["PULSAR_DASHBOARD_URL"] = f"http://127.0.0.1:{port}"
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    if is_frozen():
        subprocess.Popen(
            [sys.executable, "--companion", str(port)],
            cwd=str(Path(sys.executable).parent),
            env=env,
            creationflags=creationflags,
        )
    else:
        mascot_script = project_root / "desktop" / "companion_app.py"
        subprocess.Popen(
            [sys.executable, str(mascot_script), str(port)],
            cwd=str(project_root),
            env=env,
            creationflags=creationflags,
        )


def _notify_overlay_visibility(port: int, minimized: bool, source: str = "windows_app"):
    """Sync minimized/restored state with the single native Win32 4D orb overlay."""
    try:
        from companion_bridge import post_overlay_visibility
        post_overlay_visibility(port, minimized, source=source)
        return
    except Exception:
        pass

    def _send():
        try:
            import json
            url = f"http://127.0.0.1:{int(port)}/api/desktop/overlay/state"
            payload = json.dumps({"app_minimized": bool(minimized), "source": source}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=1.5):
                pass
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


class AppLauncherBridge:
    """IPC Bridge between JavaScript in WebView and Python Host."""

    def __init__(self, main_win, comp_win=None, port: int = 5000):
        self.main_win = main_win
        self.comp_win = comp_win
        self.port = port

    def restore_dashboard(self):
        try:
            _notify_overlay_visibility(self.port, False, source="windows_app")
            if self.main_win:
                self.main_win.restore()
                self.main_win.show()
        except Exception as e:
            print(f"[BRIDGE] Error restoring dashboard: {e}")

    def minimize_to_companion(self):
        try:
            if self.main_win:
                self.main_win.minimize()
            _notify_overlay_visibility(self.port, True, source="windows_app")
        except Exception as e:
            print(f"[BRIDGE] Error minimizing to companion: {e}")

    def dock_companion(self, docked: bool):
        return True

    def launch_ambient_mascot(self):
        """Spawns the unified native Win32 transparent 4D orb companion overlay."""
        try:
            _spawn_companion(self.port)
            return True
        except Exception as e:
            print(f"[BRIDGE] Failed to launch mascot: {e}")
            return False


class PulsarDesktopApp:
    def __init__(self):
        self.main_window = None
        self.comp_window = None
        self.tray_icon = None
        self.is_quitting = False
        self.port = 5000
        self._mutex_handle = None

    def setup_tray(self):
        """Initializes Windows System Tray notification area icon and menu."""
        try:
            import pystray
            from PIL import Image

            icon_candidates = [
                project_root / "assets" / "icon.ico",
                Path(sys.executable).parent / "icon.ico",
                Path(sys.executable).parent / "assets" / "icon.ico",
            ]
            icon_path = next((p for p in icon_candidates if p.exists()), None)
            if icon_path:
                tray_image = Image.open(icon_path)
            else:
                tray_image = Image.new("RGB", (64, 64), color=(0, 243, 255))

            def on_show_clicked(icon, item):
                _notify_overlay_visibility(self.port, False, source="windows_app")
                if self.main_window:
                    self.main_window.restore()
                    self.main_window.show()

            def on_hide_clicked(icon, item):
                if self.main_window:
                    self.main_window.hide()
                _notify_overlay_visibility(self.port, True, source="windows_app")

            def on_mascot_clicked(icon, item):
                try:
                    _spawn_companion(self.port)
                except Exception as e:
                    print(f"[TRAY] Error launching mascot: {e}")

            def on_toggle_stealth(icon, item):
                try:
                    from settings_manager import is_screen_share_stealth_enabled, update_settings_and_sync
                    cur = is_screen_share_stealth_enabled()
                    update_settings_and_sync("system", {"screenShareStealth": not cur})
                except Exception as e:
                    print(f"[TRAY] Error toggling screen share stealth: {e}")

            def on_quit_clicked(icon, item):
                self.is_quitting = True
                if self.tray_icon:
                    self.tray_icon.stop()
                if self.comp_window:
                    try:
                        self.comp_window.destroy()
                    except Exception:
                        pass
                if self.main_window:
                    try:
                        self.main_window.destroy()
                    except Exception:
                        pass
                os._exit(0)

            menu = pystray.Menu(
                pystray.MenuItem("🌌 Show Pulsar Dashboard", on_show_clicked, default=True),
                pystray.MenuItem("🙈 Minimize to Tray", on_hide_clicked),
                pystray.MenuItem("🔮 Floating Glowing Orb", on_mascot_clicked),
                pystray.MenuItem("🛡️ Screen Share Stealth", on_toggle_stealth),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("✕ Quit Pulsar AI", on_quit_clicked),
            )

            self.tray_icon = pystray.Icon("PulsarAssistant", tray_image, "Pulsar AI Assistant", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            print("[DESKTOP] System Tray initialized successfully.")
        except Exception as e:
            print(f"[DESKTOP] Note: System tray icon could not be loaded: {e}")

    def setup_global_hotkey(self):
        """Register global Windows hotkey to summon Pulsar to the foreground."""
        def toggle_window():
            if not self.main_window:
                return
            try:
                _notify_overlay_visibility(self.port, False, source="hotkey")
                self.main_window.restore()
                self.main_window.show()
            except Exception as e:
                print(f"[HOTKEY] Summon toggle error: {e}")

        def _hotkey_listener():
            try:
                import keyboard
            except ImportError:
                print("[HOTKEY] 'keyboard' package not installed, global hotkey unavailable.")
                return

            try:
                hotkey = "alt+space"
                try:
                    from settings_manager import get_general_settings
                    gen = get_general_settings()
                    if not gen.get("hotkeyEnabled", True):
                        print("[HOTKEY] Global summon hotkey is disabled in settings.")
                        return
                    configured = gen.get("hotkey", "Alt+Space")
                    if configured and configured.strip():
                        hotkey = configured.strip().lower()
                except Exception:
                    pass

                keyboard.add_hotkey(hotkey, toggle_window)
                print(f"[HOTKEY] Global desktop summon hotkey [{hotkey}] active.")
            except Exception as exc:
                print(f"[HOTKEY] Failed to register global hotkey: {exc}")

        threading.Thread(target=_hotkey_listener, daemon=True, name="PulsarGlobalHotkey").start()

    def run(self):
        # 0. Pre-flight OS checks (WebView2 & single instance)
        if not check_webview2_installed():
            choice = _show_windows_message(
                "Pulsar AI Assistant - Missing Runtime",
                "Microsoft Edge WebView2 Runtime is required to run Pulsar AI Assistant.\n\n"
                "Click Yes to open Microsoft's official WebView2 download page.",
                0x04 | 0x10,  # MB_YESNO | MB_ICONERROR
            )
            if choice == 6:  # IDYES
                webbrowser.open(WEBVIEW2_DOWNLOAD_URL)
            sys.exit(1)

        self._mutex_handle = acquire_single_instance_mutex()

        import webview

        # 1. Resolve port dynamically and start backend server if needed
        self.port, should_start_server = resolve_app_port(preferred=5000)
        os.environ["PORT"] = str(self.port)
        os.environ["PULSAR_PORT"] = str(self.port)
        os.environ["PULSAR_DASHBOARD_URL"] = f"http://127.0.0.1:{self.port}"

        if should_start_server:
            server_thread = threading.Thread(
                target=start_backend_server, args=(self.port,), daemon=True
            )
            server_thread.start()

        # 2. Poll until server is ready
        if not wait_for_server(port=self.port):
            _show_windows_message(
                "Pulsar AI Assistant - Startup Error",
                f"Pulsar AI Backend failed to respond on port {self.port}.\n"
                "Please check logs under %LOCALAPPDATA%\\PulsarAI\\logs for details.",
                0x10,
            )
            sys.exit(1)

        print(f"[DESKTOP] Launching Native Windows GUI Window on http://127.0.0.1:{self.port} ...")

        # 3. Create Main Dashboard Window
        self.main_window = webview.create_window(
            title="Pulsar AI Assistant",
            url=f"http://127.0.0.1:{self.port}",
            width=1440,
            height=900,
            min_size=(960, 640),
            text_select=True,
            frameless=False,
            background_color="#0f172a",
        )

        # 4. Reuse the single native Win32 4D Orb overlay synced via /api/desktop/overlay/state
        #    (Avoid creating a duplicate secondary pywebview /companion window.)
        bridge = AppLauncherBridge(self.main_window, None, port=self.port)
        sys._active_desktop_bridge = bridge
        self.main_window.js_api = bridge

        # Event hooks: keep unified minimized/restored visibility in sync
        def on_min():
            _notify_overlay_visibility(self.port, True, source="windows_app")

        def on_rest():
            _notify_overlay_visibility(self.port, False, source="windows_app")

        def on_close():
            if not self.is_quitting and self.tray_icon:
                # Minimize to tray while keeping the minimized 4D orb overlay active
                _notify_overlay_visibility(self.port, True, source="windows_app")
                return False
            _notify_overlay_visibility(self.port, False, source="windows_app")

        self.main_window.events.minimized += on_min
        self.main_window.events.restored += on_rest
        self.main_window.events.closed += on_close

        # 5. Start System Tray in background thread
        self.setup_tray()
        self.setup_global_hotkey()

        # 6. Start GUI loop in main thread
        webview.start(private_mode=False)

        print("[DESKTOP] Shutting down Pulsar Assistant...")
        if self.tray_icon:
            self.tray_icon.stop()
        os._exit(0)


def main():
    if "--companion" in sys.argv:
        port = _extract_companion_port(sys.argv[1:])
        os.environ["PULSAR_PORT"] = str(port)
        os.environ["PULSAR_DASHBOARD_URL"] = f"http://127.0.0.1:{port}"
        import companion_app
        companion_app.main(port=port)
        return

    app = PulsarDesktopApp()
    app.run()


if __name__ == "__main__":
    main()
