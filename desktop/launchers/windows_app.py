#!/usr/bin/env python3
"""
AI Assistant - Windows Desktop Application
===========================================
Wraps the modern web backend in a lightweight native Windows desktop window.
"""

import sys
import os
import threading
import time
import logging
import urllib.request
import urllib.error
from pathlib import Path

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


class WindowsDesktopApp:
    """Main Windows Desktop Application Controller"""
    
    def __init__(self, port: int = 5000):
        self.port = port
        self.backend_thread = None
        self.server_running = False
        
    def start_backend(self):
        """Start the backend in background thread"""
        try:
            logger.info("🚀 Launching AI Assistant Backend...")
            import modern_web_backend
            if hasattr(modern_web_backend, 'socketio') and hasattr(modern_web_backend, 'app'):
                modern_web_backend.socketio.run(
                    modern_web_backend.app,
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
            except (urllib.error.URLError, ConnectionRefusedError, OSError):
                time.sleep(0.5)
        
        logger.error("❌ Backend server failed to start within timeout.")
        return False

    def launch(self):
        """Launch the desktop app window"""
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
            logger.info("🖥️ Opening Native Desktop Window...")
            window = webview.create_window(
                title='Pulsar AI Assistant',
                url=app_url,
                width=1440,
                height=900,
                resizable=True,
                fullscreen=False,
                min_size=(960, 640),
                background_color='#0f172a',
                text_select=True
            )
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

