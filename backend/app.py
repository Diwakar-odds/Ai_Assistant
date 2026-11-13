"""
Pulsar AI Assistant - Flask Web Application Server
Entry point for the Web API Server (backend/app.py).
"""
import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from .modern_web_backend import app, socketio, start_server

main = start_server

__all__ = ["app", "socketio", "start_server", "main"]

if __name__ == "__main__":
    main()
