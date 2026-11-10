import sys
import os
import time
import threading
import urllib.request
from pathlib import Path
import runpy
import webview

def get_base_path():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    else:
        return Path(__file__).resolve().parent.parent

def start_backend_server():
    base_path = get_base_path()
    
    # Setup exact Python paths for the Monorepo architecture
    sys.path.insert(0, str(base_path / "backend"))
    sys.path.insert(0, str(base_path / "core_ai" / "src"))
    sys.path.insert(0, str(base_path / "core_ai" / "src" / "ai_assistant"))
    sys.path.insert(0, str(base_path / "shared"))
    sys.path.insert(0, str(base_path))
    
    print("Starting Pulsar AI Backend...")
    backend_script = base_path / "backend" / "modern_web_backend.py"
    try:
        runpy.run_path(str(backend_script), run_name="__main__")
    except BaseException as e:
        print(f"CRITICAL: Backend crashed: {e}")

def wait_for_server():
    """Polls the Flask server until it is ready."""
    print("Waiting for AI Engine to initialize...")
    max_retries = 30
    for i in range(max_retries):
        try:
            urllib.request.urlopen("http://127.0.0.1:5000", timeout=1)
            print("Server is ready!")
            return True
        except Exception:
            time.sleep(1)
    return False

class AppLauncherBridge:
    def __init__(self, main_win, comp_win):
        self.main_win = main_win
        self.comp_win = comp_win

    def restore_dashboard(self):
        try:
            if self.comp_win:
                self.comp_win.hide()
            if self.main_win:
                self.main_win.restore()
                self.main_win.show()
        except Exception:
            pass

    def minimize_to_companion(self):
        try:
            if self.main_win:
                self.main_win.minimize()
            if self.comp_win:
                self.comp_win.restore()
                self.comp_win.show()
        except Exception:
            pass

    def dock_companion(self, docked: bool):
        try:
            if not self.comp_win or not webview.screens:
                return
            screen = webview.screens[0]
            if docked:
                self.comp_win.move(screen.width - 60, screen.height - 340 - 60)
            else:
                self.comp_win.move(screen.width - 280 - 30, screen.height - 340 - 60)
        except Exception:
            pass

    def prepare_screenshot(self):
        try:
            if self.comp_win:
                self.comp_win.hide()
                def _restore():
                    time.sleep(1.2)
                    if self.comp_win:
                        self.comp_win.show()
                threading.Thread(target=_restore, daemon=True).start()
        except Exception:
            pass

def open_dashboard():
    # Wait for the backend to bind to port 5000
    if wait_for_server():
        print("Launching Native Windows GUI with Floating Companion...")
        bridge_holder = [None]
        
        main_window = webview.create_window(
            title="Pulsar AI Assistant",
            url="http://127.0.0.1:5000",
            width=1440,
            height=900,
            min_size=(960, 640),
            text_select=True,
            frameless=False,
        )

        comp_w = 280
        comp_h = 340
        comp_x = None
        comp_y = None
        if webview.screens:
            screen = webview.screens[0]
            comp_x = screen.width - comp_w - 30
            comp_y = screen.height - comp_h - 60

        comp_window = webview.create_window(
            title="Pulsar Companion Mascot",
            url="http://127.0.0.1:5000/companion",
            width=comp_w,
            height=comp_h,
            x=comp_x,
            y=comp_y,
            frameless=True,
            on_top=True,
            transparent=True,
            hidden=True,
            resizable=False,
            easy_drag=True
        )

        bridge = AppLauncherBridge(main_window, comp_window)
        bridge_holder[0] = bridge
        sys._active_desktop_bridge = bridge
        main_window.js_api = bridge
        comp_window.js_api = bridge

        def on_min():
            if comp_window:
                comp_window.restore()
                comp_window.show()

        def on_rest():
            if comp_window:
                comp_window.hide()

        def on_close():
            if comp_window:
                try:
                    comp_window.destroy()
                except Exception:
                    pass

        main_window.events.minimized += on_min
        main_window.events.restored += on_rest
        main_window.events.closed += on_close

        webview.start(private_mode=True)
    else:
        print("Failed to connect to the backend server. It may have crashed.")
        sys.exit(1)

if __name__ == "__main__":
    # Start the backend server in a background thread
    server_thread = threading.Thread(target=start_backend_server, daemon=True)
    server_thread.start()
    
    # We must run the GUI in the main thread.
    open_dashboard()
    
    print("Shutting down Pulsar Assistant...")
    sys.exit(0)
