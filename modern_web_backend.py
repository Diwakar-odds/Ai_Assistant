import sys
import os
import subprocess
import atexit
import time

if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr is not None and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def main():
    """
    Wrapper script to run the modern_web_backend and frontend from the root directory.
    Cleanly separates Vite logs from the unified Python Developer Telemetry Console.
    """
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_script = os.path.join(root_dir, 'backend', 'modern_web_backend.py')
    frontend_dir = os.path.join(root_dir, 'frontend', 'web-app')
    logs_dir = os.path.join(root_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    if not os.path.exists(backend_script):
        print(f"Error: Could not find backend script at {backend_script}")
        sys.exit(1)
        
    frontend_process = None
    vite_log_file = None
    
    if os.path.exists(frontend_dir):
        # Redirect Vite output cleanly to file to prevent console interleaving
        vite_log_path = os.path.join(logs_dir, 'vite_frontend.log')
        vite_log_file = open(vite_log_path, 'w', encoding='utf-8')
        
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"], 
            cwd=frontend_dir,
            shell=True,
            stdout=vite_log_file,
            stderr=subprocess.STDOUT
        )
        
        # Mark frontend status for Developer Matrix
        os.environ['VITE_STATUS'] = 'RUNNING'
        os.environ['VITE_FRONTEND_URL'] = 'http://localhost:5173'
        
        def cleanup():
            try:
                if vite_log_file and not vite_log_file.closed:
                    vite_log_file.close()
            except Exception:
                pass
            if frontend_process and frontend_process.poll() is None:
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(frontend_process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
        atexit.register(cleanup)
        
    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        env['PYTHONUNBUFFERED'] = '1'
        env['HF_HUB_OFFLINE'] = '1'
        env['TRANSFORMERS_OFFLINE'] = '1'
        backend_dir = os.path.dirname(backend_script)
        result = subprocess.run([sys.executable, backend_script] + sys.argv[1:], env=env, cwd=backend_dir)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
        sys.exit(0)

if __name__ == '__main__':
    main()
