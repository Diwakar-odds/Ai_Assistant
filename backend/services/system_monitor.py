import threading
import time
import psutil
from flask_socketio import SocketIO

def start_system_monitor(socketio: SocketIO):
    """
    Start a background thread that monitors system stats (CPU, RAM) 
    and emits them over websockets.
    """
    def monitor_loop():
        while True:
            try:
                # Calculate CPU and Memory usage
                cpu_percent = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                
                stats = {
                    "cpu": cpu_percent,
                    "ram": mem.percent,
                    "ram_used_gb": round(mem.used / (1024**3), 2),
                    "ram_total_gb": round(mem.total / (1024**3), 2)
                }
                
                # Emit to clients
                socketio.emit('system_stats', stats, namespace='/')
                
                # Wait before next update
                time.sleep(2)
            except Exception as e:
                print(f"Error in system monitor: {e}")
                time.sleep(5)
                
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()
