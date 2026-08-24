import sys
import os
import threading
import logging
import time
import warnings
from pathlib import Path

# Force UTF-8 encoding for console output (Fixes garbled emojis in some terminals like Git Bash)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Suppress pywinauto STA COM threading mode warning
warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto")

try:
    import webview
except ImportError:
    print("pywebview is required. Please 'pip install pywebview'")
    sys.exit(1)

# Ensure path is correct
def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).parent.parent.parent.parent
    return base_path / relative_path

project_root = get_resource_path("")
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def start_backend():
    print("Starting backend on port 5000 for Desktop App...")
    try:
        # LAZY IMPORT: Move heavy imports here so they don't block the UI window from opening!
        from ai_assistant.services.modern_web_backend import app, socketio, start_ai_background_thread
        
        # Fire off the background thread to load AI models while Flask starts serving the UI instantly
        start_ai_background_thread()
        
        try:
            from ai_assistant.services.backend.system_monitor import start_system_monitor
            start_system_monitor(socketio)
        except Exception as e:
            pass
            
        try:
            from ai_assistant.services.modern_web_backend import GOOGLE_SPEECH_WS_AVAILABLE, register_google_speech_handlers
            if GOOGLE_SPEECH_WS_AVAILABLE:
                register_google_speech_handlers(socketio)
        except Exception as e:
            pass
            
        try:
            import ai_assistant.services.voice_service as chat_handlers
            from ai_assistant.services.modern_web_backend import learning_router
            chat_handlers.set_socketio(socketio)
            chat_handlers.set_learning_router(learning_router)
        except Exception as e:
            print(f"âš ï¸ Could not register command handlers: {e}")

        # React app expects port 5000 based on its hardcoded fetches
        print("Now running socketio on port 5000...")
        socketio.run(app, host='127.0.0.1', port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
    except Exception as fatal_error:
        import traceback
        print("\n" + "="*50)
        print("âŒ FATAL BACKEND CRASH PREVENTED WEBVIEW FROM LOADING:")
        print("="*50)
        traceback.print_exc()
        print("="*50 + "\n")

def check_server_and_redirect(window):
    """Poll the Flask server until it's ready, then redirect the webview."""
    import urllib.request
    import time
    max_retries = 60 # 30 seconds timeout
    retries = 0
    while retries < max_retries:
        try:
            # Attempt to connect to the Flask server
            urllib.request.urlopen('http://127.0.0.1:5000/', timeout=1)
            # If successful, the server is up and ready!
            window.load_url('http://127.0.0.1:5000/')
            return
        except Exception:
            retries += 1
            time.sleep(0.5)
            
    # If we get here, the server failed to start in time
    error_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Error Loading Pulsar AI</title>
        <style>
            body { background: #16181D; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; font-family: sans-serif; }
        </style>
    </head>
    <body>
        <h2 style="color: #EF4444;">Server Timeout</h2>
        <p style="color: #9CA3AF;">The AI engine took too long to start or encountered an error.</p>
        <p style="color: #9CA3AF;">Please check the console logs for details.</p>
    </body>
    </html>
    """
    window.load_html(error_html)

def main():
    loading_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Loading Pulsar AI...</title>
        <style>
            body { background: #16181D; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; font-family: sans-serif; }
            .loader { border: 4px solid rgba(255,255,255,0.1); border-left-color: #3B82F6; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin-bottom: 20px; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .progress-text { margin-top: 15px; color: #60A5FA; font-size: 14px; font-weight: bold; }
        </style>
        <script>
            let dots = 0;
            setInterval(() => {
                dots = (dots + 1) % 4;
                document.getElementById('loading-text').innerText = 'Initializing System' + '.'.repeat(dots);
            }, 500);
        </script>
    </head>
    <body>
        <div class="loader"></div>
        <h2>Starting Web Server...</h2>
        <p style="color: #9CA3AF;">UI will appear instantly, AI modules will load in background.</p>
        <div class="progress-text" id="loading-text">Initializing System...</div>
    </body>
    </html>
    """

    # We now serve the frontend via Flask on port 5000
    print("Opening native window with loading screen...")
    window = webview.create_window('Pulsar AI Assistant', html=loading_html, width=1280, height=800, min_size=(800, 600))
    
    # Start the polling thread to redirect the window once the server is ready
    import threading
    threading.Thread(target=check_server_and_redirect, args=(window,), daemon=True).start()
    
    # Start the webview GUI loop FIRST, then run start_backend in a background thread.
    # This guarantees the window appears instantly (0 seconds) before heavy AI models block the GIL.
    webview.start(start_backend)

if __name__ == '__main__':
    main()

