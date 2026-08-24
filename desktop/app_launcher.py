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

def open_dashboard():
    # Wait for the backend to bind to port 5000
    if wait_for_server():
        # Server is up, create window
        print("Launching Native Windows GUI...")
        window = webview.create_window(
            title="Pulsar AI Assistant",
            url="http://127.0.0.1:5000",
            width=1280,
            height=800,
            min_size=(800, 600),
            text_select=True,
            frameless=False,
        )
        # Use private_mode=True to avoid WebView2 cache locking issues when multiple instances crash
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
