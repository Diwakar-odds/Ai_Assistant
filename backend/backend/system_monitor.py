# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")


import time
import psutil
from threading import Lock

# Global to track previous network counters for speed calculation
_last_net_io = None
_last_time = None
_lock = Lock()

def get_network_speed():
    global _last_net_io, _last_time
    
    with _lock:
        now = time.time()
        net_io = psutil.net_io_counters()
        
        if _last_net_io is None or _last_time is None:
            _last_net_io = net_io
            _last_time = now
            return 0
            
        # Calculate bytes per second
        time_delta = now - _last_time
        if time_delta <= 0:
            return 0
            
        bytes_sent = net_io.bytes_sent - _last_net_io.bytes_sent
        bytes_recv = net_io.bytes_recv - _last_net_io.bytes_recv
        
        total_bytes = bytes_sent + bytes_recv
        speed_bps = total_bytes / time_delta
        
        _last_net_io = net_io
        _last_time = now
        
        return speed_bps

def start_system_monitor(socketio):
    """
    Starts a background task that emits system stats via SocketIO.
    """
    def monitor_loop():
        print("📊 System monitor started")
        while True:
            try:
                # Get stats
                cpu = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                net_speed = get_network_speed()
                
                stats = {
                    'cpu_usage': cpu,
                    'memory_usage': memory,
                    'disk_usage': disk,
                    'network_speed': net_speed,
                    'timestamp': time.time()
                }
                
                # Emit to all connected clients
                socketio.emit('system_stats_update', stats)
                
            except Exception as e:
                logger.error(f"❌ Error in system monitor: {e}")
            
            socketio.sleep(2) # Non-blocking sleep for gevent/eventlet

    socketio.start_background_task(monitor_loop)
