"""
System Monitor Module
Collects real-time hardware metrics (CPU, RAM, Disk, Network) with caching and smoothing.
Extracted from assistant.py for modularity.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class SystemMonitor:
    """Monitors system performance metrics with caching."""
    
    def __init__(self, cache_ttl_seconds: float = 2.0):
        self.cache_ttl = cache_ttl_seconds
        self.stats_cache: Dict[str, Any] = {}
        self.cache_timestamp = 0.0
        
        self.last_network_stats = None
        self.last_network_time = None
        self.network_speed_history = []

    def get_real_time_stats(self) -> Dict[str, Any]:
        """Get system statistics with rolling cache to avoid psutil thrashing."""
        now = time.time()
        if now - self.cache_timestamp < self.cache_ttl and self.stats_cache:
            return self.stats_cache
            
        if not PSUTIL_AVAILABLE:
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage": 0,
                "memory_usage": 0,
                "disk_usage": 0,
                "network_mbps": 0,
                "active_tasks": 0,
                "temperature": "N/A"
            }
            
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            # Network speed calculation
            net_mbps = 0.0
            net_io = psutil.net_io_counters()
            current_bytes = net_io.bytes_recv + net_io.bytes_sent
            
            if self.last_network_stats is not None and self.last_network_time is not None:
                elapsed = now - self.last_network_time
                if elapsed > 0.1:
                    bytes_diff = current_bytes - self.last_network_stats
                    net_mbps = round((bytes_diff * 8) / (elapsed * 1024 * 1024), 2)
                    self.network_speed_history.append(net_mbps)
                    if len(self.network_speed_history) > 5:
                        self.network_speed_history.pop(0)
                    net_mbps = round(sum(self.network_speed_history) / len(self.network_speed_history), 2)
                    
            self.last_network_stats = current_bytes
            self.last_network_time = now
            
            stats = {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage": cpu,
                "memory_usage": mem,
                "disk_usage": disk,
                "network_mbps": net_mbps,
                "active_tasks": len(psutil.pids()),
                "temperature": "N/A"
            }
            
            self.stats_cache = stats
            self.cache_timestamp = now
            return stats
            
        except Exception as e:
            logger.debug(f"Error fetching system stats: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage": 0,
                "memory_usage": 0,
                "disk_usage": 0,
                "network_mbps": 0,
                "active_tasks": 0,
                "temperature": "N/A"
            }
