import sys; sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8');
import os
import sys
import subprocess
import atexit
import time

def main():
    """
    Wrapper script to run the modern_web_backend and frontend from the root directory.
    """
    # Force UTF-8 encoding for Windows terminals to display emojis correctly
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_script = os.path.join(root_dir, 'backend', 'modern_web_backend.py')
    frontend_dir = os.path.join(root_dir, 'frontend', 'web-app')
    
    if not os.path.exists(backend_script):
        print(f"Error: Could not find backend script at {backend_script}")
        sys.exit(1)
        
    frontend_process = None
    
    if os.path.exists(frontend_dir):
        print(f"[WEB] Launching React Frontend (npm run dev)...")
        # Start frontend in the background
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"], 
            cwd=frontend_dir,
            shell=True
        )
        
        # Give frontend a second to initialize logs before backend logs take over
        time.sleep(2)
        
        # Cleanup function to kill frontend when backend is stopped
        def cleanup():
            if frontend_process and frontend_process.poll() is None:
                print("\n🛑 Shutting down Frontend...")
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(frontend_process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
        atexit.register(cleanup)
        
    print(f"⚙️ Launching modern_web_backend...")
    
    try:
        # Launch the actual backend script with forced UTF-8 encoding
        env = os.environ.copy()
        result = subprocess.run([sys.executable, backend_script] + sys.argv[1:], env=env)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
        sys.exit(0)

if __name__ == '__main__':
    main()
