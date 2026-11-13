"""
Pulsar AI Assistant - Web Backend & UI Launcher
===============================================
Unified Single-Process Launcher.

Usage:
    python web.py           (Production mode: runs backend + pre-built UI on http://localhost:5000)
    python web.py --dev     (Dev mode: starts Vite dev server alongside backend)

Guarantees 1 Process, 1 PID, and 1 Port (5000) with zero orphaned subprocesses.
"""
import sys
import os
import atexit
import time

if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr is not None and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

_backend_app = None

def _get_backend_module():
    global _backend_app
    if _backend_app is None:
        root_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.join(root_dir, 'backend')
        for p in (root_dir, backend_dir, os.path.join(root_dir, 'core_ai', 'src')):
            if p not in sys.path:
                sys.path.insert(0, p)
        if os.path.exists(backend_dir):
            os.chdir(backend_dir)
        from backend import modern_web_backend as backend_app
        _backend_app = backend_app
    return _backend_app

def start_server(host="127.0.0.1", port=5000, **kwargs):
    """Programmatic entry point to start the Pulsar server."""
    backend_app = _get_backend_module()
    return backend_app.start_server(host=host, port=port, **kwargs)

def __getattr__(name):
    """
    Transparently proxy any attributes (e.g. app, socketio, assistant)
    to backend.modern_web_backend so `import web; web.app` works seamlessly.
    """
    backend_app = _get_backend_module()
    return getattr(backend_app, name)

def main():
    """
    Unified Single-Process Launcher for Pulsar AI Assistant.
    Guarantees 1 Process, 1 PID, and 1 Port (5000) with zero orphaned subprocesses.
    Serves both WebUI and Backend in-process directly on http://localhost:5000.
    """
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    os.environ['PYTHONUNBUFFERED'] = '1'
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    # Allow companion orb by default; disable only if explicitly requested via --no-companion or --headless
    if '--no-companion' in sys.argv or '--headless' in sys.argv:
        os.environ['PULSAR_DISABLE_COMPANION'] = '1'
    else:
        os.environ.pop('PULSAR_DISABLE_COMPANION', None)

    def cleanup_companion():
        try:
            from routes.system_routes import stop_companion_process
            stop_companion_process()
        except Exception:
            pass
    atexit.register(cleanup_companion)

    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, 'backend')
    
    for p in (root_dir, backend_dir, os.path.join(root_dir, 'core_ai', 'src')):
        if p not in sys.path:
            sys.path.insert(0, p)
            
    # Optional dev frontend flag (--dev or --dev-frontend)
    dev_mode = '--dev' in sys.argv or '--dev-frontend' in sys.argv
    if dev_mode:
        import subprocess
        frontend_dir = os.path.join(root_dir, 'frontend', 'web-app')
        if os.path.exists(frontend_dir):
            frontend_process = subprocess.Popen(
                ["npm", "run", "dev"], 
                cwd=frontend_dir,
                shell=True
            )
            def cleanup():
                if frontend_process and frontend_process.poll() is None:
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(frontend_process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            atexit.register(cleanup)

    os.chdir(backend_dir)
    try:
        backend_app = _get_backend_module()
        backend_app.start_server(host="127.0.0.1", port=5000)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
        sys.exit(0)

if __name__ == '__main__':
    main()
