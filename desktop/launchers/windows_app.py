#!/usr/bin/env python3
"""
AI Assistant - Windows Desktop Application
===========================================
Wraps the web backend in a native Windows desktop application using pywebview.
"""

import sys
import os
import threading
import time
import logging
import webview
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add project root to path
# Add project root to path (src directory)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class WindowsApp:
    """Main Windows Desktop Application"""
    
    def __init__(self):
        self.backend_thread = None
        self.flask_app = None
        self.socketio = None
        self.server_running = False
        self.port = 5000
        
    def start_backend(self):
        """Start the Flask backend in a separate thread"""
        try:
            logger.info("Starting Flask backend server...")
            
            # Import and run the backend
            import runpy
            
            # This will start the Flask server
            runpy.run_module('ai_assistant.services.modern_web_backend', run_name='__main__')
            
        except Exception as e:
            logger.error(f"Failed to start backend: {e}")
            import traceback
            traceback.print_exc()
    
    def wait_for_server(self, timeout=30):
        """Wait for the Flask server to be ready"""
        import urllib.request
        import urllib.error
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{self.port}', timeout=1)
                logger.info("Backend server is ready!")
                self.server_running = True
                return True
            except (urllib.error.URLError, ConnectionRefusedError, OSError):
                time.sleep(0.5)
        
        logger.error("Backend server failed to start in time")
        return False
    
    def create_window(self):
        """Create the desktop window"""
        logger.info("Creating desktop window...")
        
        # Create the main window
        window = webview.create_window(
            title='AI Assistant',
            url=f'http://127.0.0.1:{self.port}',
            width=1400,
            height=900,
            resizable=True,
            fullscreen=False,
            min_size=(800, 600),
            background_color='#1a1a1a',
            text_select=True
        )
        
        return window
    
    def run(self):
        """Run the Windows desktop application"""
        logger.info("="*60)
        logger.info("AI Assistant - Windows Desktop App")
        logger.info("="*60)
        
        # Start backend in separate thread
        logger.info("Launching backend server...")
        self.backend_thread = threading.Thread(target=self.start_backend, daemon=True)
        self.backend_thread.start()
        
        # Wait for server to be ready
        if not self.wait_for_server():
            logger.error("Failed to start the application. Exiting...")
            return
        
        # Create and start the desktop window
        window = self.create_window()
        
        # Start the GUI (blocking call)
        logger.info("Opening desktop window...")
        webview.start(debug=False, http_server=False)
        
        logger.info("Application closed.")


def main():
    """Main entry point"""
    app = WindowsApp()
    app.run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nShutdown requested...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
