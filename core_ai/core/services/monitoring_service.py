"""
Monitoring Service

Handles system monitoring, statistics collection, and real-time metrics.
Extracted from ModernAssistant for better modularity.
"""

import logging
import time

logger = logging.getLogger(__name__)

# Try to import psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - system monitoring limited")

class MonitoringService:
    """System monitoring and statistics service"""
    
    def __init__(self, socketio=None):
        """
        Initialize monitoring service
        
        Args:
            socketio: SocketIO instance for real-time updates
        """
        self.socketio = socketio
        self.stats_cache = {}
        self.cache_timestamp = 0
        self.cache_duration = 2  # Cache for 2 seconds
    
    def get_real_time_system_stats(self):
        """
        Get real-time system statistics
        
        Returns:
            dict: System statistics
        """
        # Check cache
        current_time = time.time()
        if (current_time - self.cache_timestamp) < self.cache_duration:
            return self.stats_cache
        
        try:
            if not PSUTIL_AVAILABLE:
                return {
                    "error": "System monitoring not available",
                    "cpu_usage": 0,
                    "memory_usage": 0
                }
            
            stats = {
                "cpu_usage": round(psutil.cpu_percent(interval=0.1), 1),
                "memory_usage": round(psutil.virtual_memory().percent, 1),
                "disk_usage": round(psutil.disk_usage('/').percent, 1) if hasattr(psutil, 'disk_usage') else 0,
                "timestamp": current_time
            }
            
            # Try to get network stats
            try:
                net_io = psutil.net_io_counters()
                stats["network"] = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv
                }
            except:
                pass
            
            # Cache the results
            self.stats_cache = stats
            self.cache_timestamp = current_time
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {
                "error": str(e),
                "cpu_usage": 0,
                "memory_usage": 0
            }
    
    def start_monitoring(self, interval=5):
        """
        Start background system monitoring
        
        Args:
            interval: Update interval in seconds
        """
        import threading
        
        def monitor():
            while True:
                try:
                    stats = self.get_real_time_system_stats()
                    if self.socketio:
                        self.socketio.emit('system_stats', stats)
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                    time.sleep(interval)
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        logger.info("System monitoring started")
    
    def get_process_info(self):
        """
        Get current process information
        
        Returns:
            dict: Process information
        """
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
        
        try:
            process = psutil.Process()
            return {
                "pid": process.pid,
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "cpu_percent": process.cpu_percent(interval=0.1),
                "num_threads": process.num_threads()
            }
        except Exception as e:
            logger.error(f"Error getting process info: {e}")
            return {"error": str(e)}
