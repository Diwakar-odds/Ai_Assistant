#!/usr/bin/env python3
"""
AI Assistant - Windows Desktop Application
===========================================
Wraps the modern web backend in a lightweight native Windows desktop window
with an intelligent floating companion mascot overlay on minimize.
"""

import sys
import os
import threading
import time
import logging
import urllib.request
import urllib.error
from pathlib import Path

# Suppress noisy Chromium / WebView2 background network spam (GCM, updater)
os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = (
    '--disable-features=OptimizationGuideModelDownloading,OptimizationHintsFetching,OptimizationTargetPrediction '
    '--disable-sync --disable-background-networking --disable-component-update --log-level=3'
)

# Setup correct project paths (Handles both standalone Python and PyInstaller frozen .exe)
if getattr(sys, 'frozen', False):
    # PyInstaller bundle
    bundle_dir = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    exe_dir = Path(sys.executable).parent
    project_root = bundle_dir
    log_file = exe_dir / 'desktop_app.log'
else:
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    exe_dir = project_root
    log_file = project_root / 'desktop_app.log'

backend_dir = project_root / 'backend'
core_ai_src = project_root / 'core_ai' / 'src'
shared_dir = project_root / 'shared'

for path_entry in [str(project_root), str(backend_dir), str(core_ai_src), str(shared_dir), str(exe_dir)]:
    if path_entry not in sys.path:
        sys.path.insert(0, path_entry)

# Setup logging to both console (if available) and file
handlers = [logging.FileHandler(str(log_file), encoding='utf-8')]
if sys.stdout is not None:
    handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=handlers
)
logger = logging.getLogger(__name__)

try:
    import webview
    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False
    logger.warning("pywebview is not installed. Will fallback to default web browser.")


def _post_overlay_visibility(port: int, minimized: bool):
    """Notify backend overlay coordinator when the native desktop window minimizes or restores."""
    try:
        from companion_bridge import post_overlay_visibility
        post_overlay_visibility(port, minimized, source="windows_app")
        return
    except Exception:
        pass

    def _send():
        try:
            import json
            url = f"http://127.0.0.1:{port}/api/desktop/overlay/state"
            payload = json.dumps({"app_minimized": bool(minimized), "source": "windows_app"}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=1.5):
                pass
        except Exception as e:
            logger.debug(f"Overlay visibility sync note: {e}")

    threading.Thread(target=_send, daemon=True).start()


class CompanionBridge:
    """Native Python bridge for the Floating Companion mascot and Dashboard"""

    def __init__(self, app):
        self.app = app

    def restore_dashboard(self):
        """Restore full main dashboard and hide minimized overlay"""
        logger.info("Restoring full dashboard window...")
        try:
            _post_overlay_visibility(self.app.port, False)
            if self.app.companion_window:
                self.app.companion_window.hide()
            if self.app.main_window:
                self.app.main_window.restore()
                self.app.main_window.show()
        except Exception as e:
            logger.error(f"Error restoring dashboard: {e}")

    def minimize_to_companion(self):
        """Minimize main dashboard and enable transparent taskbar-adjacent 4D orb overlay"""
        logger.info("Minimizing dashboard -> Enabling Minimized 4D Orb Overlay...")
        try:
            if self.app.main_window:
                self.app.main_window.minimize()
            _post_overlay_visibility(self.app.port, True)
        except Exception as e:
            logger.error(f"Error minimizing to companion: {e}")

    def dock_companion(self, docked: bool):
        """Move companion into docked / peeking position at screen edge"""
        try:
            if not self.app.companion_window or not webview.screens:
                return
            screen = webview.screens[0]
            w = 280
            h = 340
            if docked:
                # Dock to right edge (peeking)
                self.app.companion_window.move(screen.width - 60, screen.height - h - 60)
            else:
                # Restore full float position
                self.app.companion_window.move(screen.width - w - 30, screen.height - h - 60)
        except Exception as e:
            logger.error(f"Error docking companion: {e}")

    def prepare_screenshot(self):
        """Temporarily hide companion window so it doesn't obstruct screenshot"""
        try:
            if self.app.companion_window:
                self.app.companion_window.hide()
                def _restore():
                    time.sleep(1.2)
                    if self.app.companion_window:
                        self.app.companion_window.show()
                threading.Thread(target=_restore, daemon=True).start()
        except Exception as e:
            logger.error(f"Error in prepare_screenshot: {e}")


class WindowsDesktopApp:
    """Main Windows Desktop Application Controller with Floating Companion Mascot"""

    def __init__(self, port: int = 5000):
        self.port = port
        self.backend_thread = None
        self.server_running = False
        self.main_window = None
        self.companion_window = None
        self.bridge = CompanionBridge(self)
        sys._active_desktop_bridge = self.bridge

    def start_backend(self):
        """Start the backend in background thread"""
        try:
            logger.info("🚀 Launching AI Assistant Backend...")
            backend_mod = None
            try:
                import web
                if hasattr(web, 'start_server'):
                    backend_mod = web
            except ImportError:
                pass
            if backend_mod is None:
                import modern_web_backend
                backend_mod = modern_web_backend

            if hasattr(backend_mod, 'start_server'):
                backend_mod.start_server(host='127.0.0.1', port=self.port)
            elif hasattr(backend_mod, 'socketio') and hasattr(backend_mod, 'app'):
                backend_mod.socketio.run(
                    backend_mod.app,
                    host='127.0.0.1',
                    port=self.port,
                    debug=False,
                    allow_unsafe_werkzeug=True
                )
        except Exception as e:
            logger.error(f"❌ Backend error: {e}")
            import traceback
            traceback.print_exc()

    def wait_for_server(self, timeout: int = 45) -> bool:
        """Wait for the Flask backend to be ready"""
        start_time = time.time()
        url = f'http://127.0.0.1:{self.port}'
        logger.info(f"⏳ Waiting for backend at {url}...")

        while time.time() - start_time < timeout:
            try:
                with urllib.request.urlopen(url, timeout=1) as response:
                    if response.status in (200, 302, 304):
                        logger.info("✅ Backend server is live!")
                        self.server_running = True
                        return True
            except urllib.error.HTTPError as he:
                logger.info(f"✅ Backend server responded with HTTP {he.code}!")
                self.server_running = True
                return True
            except (urllib.error.URLError, ConnectionRefusedError, OSError):
                time.sleep(0.5)

        logger.error("❌ Backend server failed to start within timeout.")
        return False

    def launch(self):
        """Launch the desktop app window and companion mascot"""
        logger.info("=" * 60)
        logger.info("🤖 Pulsar AI Assistant - Windows Desktop App")
        logger.info("=" * 60)

        # 1. Start backend thread
        self.backend_thread = threading.Thread(target=self.start_backend, daemon=True)
        self.backend_thread.start()

        # 2. Wait for backend to be ready
        if not self.wait_for_server():
            logger.error("Could not connect to backend. Please check logs.")
            return

        # 3. Open desktop window
        app_url = f'http://127.0.0.1:{self.port}'

        if WEBVIEW_AVAILABLE:
            logger.info("🖥️ Opening Native Desktop Dashboard...")
            self.main_window = webview.create_window(
                title='Pulsar AI Assistant',
                url=app_url,
                width=1440,
                height=900,
                resizable=True,
                fullscreen=False,
                min_size=(960, 640),
                background_color='#0f172a',
                text_select=True,
                js_api=self.bridge
            )

            # Event hooks: Sync minimize/restore with transparent click-through 4D Orb overlay
            def on_main_minimized():
                logger.info("Main window minimized -> Notifying 4D Orb Desktop Overlay")
                _post_overlay_visibility(self.port, True)

            def on_main_restored():
                logger.info("Main window restored -> Hiding 4D Orb Desktop Overlay")
                _post_overlay_visibility(self.port, False)

            def on_main_closed():
                logger.info("Main dashboard closed -> Keeping minimized 4D Orb Desktop Overlay active")
                _post_overlay_visibility(self.port, True)
                if self.companion_window:
                    try:
                        self.companion_window.destroy()
                    except Exception:
                        pass

            self.main_window.events.minimized += on_main_minimized
            self.main_window.events.restored += on_main_restored
            self.main_window.events.closed += on_main_closed

            webview.start(debug=False, http_server=False)
        else:
            import webbrowser
            logger.info(f"🌐 Opening default browser at {app_url}...")
            webbrowser.open(app_url)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass


def main():
    app = WindowsDesktopApp(port=5000)
    app.launch()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutdown requested.")
        sys.exit(0)
