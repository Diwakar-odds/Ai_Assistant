#!/usr/bin/env python3
"""
Offline Mode Detection and Management
Detects internet connectivity and switches between online and offline modes.
Manages caching and fallback strategies.
"""

import os
import socket
import json
import logging
import time
import threading
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class OfflineModeManager:
    """Manages offline/online mode detection and switching."""
    
    def __init__(self, 
                 check_interval: int = 30,
                 offline_cache_dir: str = "offline_cache",
                 enable_auto_detection: bool = True):
        """
        Initialize offline mode manager.
        
        Args:
            check_interval: How often to check connectivity (seconds)
            offline_cache_dir: Directory for caching offline data
            enable_auto_detection: Whether to auto-detect connectivity
        """
        self.check_interval = check_interval
        self.offline_cache_dir = Path(offline_cache_dir)
        self.offline_cache_dir.mkdir(exist_ok=True)
        
        self.is_online = True
        self.is_offline_mode = False  # User-forced offline mode
        self.check_running = False
        self.check_thread = None
        self.enable_auto_detection = enable_auto_detection
        
        # Callbacks for mode changes
        self.on_mode_change_callbacks: list[Callable] = []
        self.last_status_check = datetime.now()
        
        # Initial check
        self._check_connectivity()
        
        # Start background connectivity check if enabled
        if enable_auto_detection:
            self.start_connectivity_check()
    
    def _check_connectivity(self, timeout: int = 3) -> bool:
        """
        Check if device has internet connectivity.
        
        Args:
            timeout: Timeout for connection check (seconds)
        
        Returns:
            True if connected, False otherwise
        """
        try:
            # Try multiple DNS servers (Google, Cloudflare)
            hosts = [
                ("8.8.8.8", 53),      # Google DNS
                ("1.1.1.1", 53),      # Cloudflare DNS
                ("208.67.222.222", 53)  # OpenDNS
            ]
            
            for host, port in hosts:
                try:
                    socket.create_connection((host, port), timeout=timeout)
                    self.is_online = True
                    self.last_status_check = datetime.now()
                    return True
                except (socket.timeout, socket.error):
                    continue
            
            self.is_online = False
            self.last_status_check = datetime.now()
            return False
        
        except Exception as e:
            logger.debug(f"Connectivity check error: {e}")
            self.is_online = False
            return False
    
    def start_connectivity_check(self):
        """Start background connectivity check thread."""
        if self.check_running:
            return
        
        self.check_running = True
        self.check_thread = threading.Thread(
            target=self._connectivity_check_loop,
            daemon=True
        )
        self.check_thread.start()
        logger.info("Connectivity monitoring started")
    
    def stop_connectivity_check(self):
        """Stop background connectivity check thread."""
        self.check_running = False
        if self.check_thread:
            self.check_thread.join(timeout=5)
        logger.info("Connectivity monitoring stopped")
    
    def _connectivity_check_loop(self):
        """Background thread for periodic connectivity checks."""
        while self.check_running:
            try:
                previous_state = self.is_online
                self._check_connectivity()
                
                # Call callbacks if state changed
                if previous_state != self.is_online:
                    self._trigger_mode_change_callbacks()
                
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Connectivity check loop error: {e}")
                time.sleep(self.check_interval)
    
    def set_offline_mode(self, force_offline: bool):
        """
        Force offline mode regardless of connectivity.
        
        Args:
            force_offline: True to force offline mode
        """
        previous_mode = self.is_offline_mode
        self.is_offline_mode = force_offline
        
        if previous_mode != force_offline:
            self._trigger_mode_change_callbacks()
            logger.info(f"Offline mode set to: {force_offline}")
    
    def is_connected(self) -> bool:
        """Check if device should be in online mode."""
        if self.is_offline_mode:
            return False
        return self.is_online
    
    def should_use_offline(self) -> bool:
        """Check if offline mode should be used."""
        return not self.is_connected()
    
    def add_mode_change_callback(self, callback: Callable[[bool], None]):
        """
        Add callback for mode changes.
        
        Args:
            callback: Function called with (is_online: bool) when mode changes
        """
        self.on_mode_change_callbacks.append(callback)
    
    def _trigger_mode_change_callbacks(self):
        """Trigger all registered mode change callbacks."""
        is_online = self.is_connected()
        for callback in self.on_mode_change_callbacks:
            try:
                callback(is_online)
            except Exception as e:
                logger.error(f"Error in mode change callback: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current offline/online status."""
        return {
            "is_online": self.is_online,
            "is_offline_mode": self.is_offline_mode,
            "should_use_offline": self.should_use_offline(),
            "last_check": self.last_status_check.isoformat(),
            "mode": "offline" if self.should_use_offline() else "online"
        }
    
    def cache_response(self, key: str, data: Dict[str, Any], ttl_hours: int = 24):
        """
        Cache a response for offline use.
        
        Args:
            key: Cache key (e.g., "weather_london", "news_tech")
            data: Data to cache
            ttl_hours: Time to live in hours
        """
        try:
            cache_file = self.offline_cache_dir / f"{key}.json"
            cache_data = {
                "data": data,
                "timestamp": datetime.now().isoformat(),
                "ttl_hours": ttl_hours,
                "expires_at": (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.debug(f"Cached response for key: {key}")
        except Exception as e:
            logger.error(f"Failed to cache response: {e}")
    
    def get_cached_response(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response if available and not expired.
        
        Args:
            key: Cache key
        
        Returns:
            Cached data or None if not found or expired
        """
        try:
            cache_file = self.offline_cache_dir / f"{key}.json"
            
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check if expired
            expires_at = datetime.fromisoformat(cache_data["expires_at"])
            if datetime.now() > expires_at:
                logger.debug(f"Cache expired for key: {key}")
                cache_file.unlink()  # Delete expired cache
                return None
            
            return cache_data["data"]
        except Exception as e:
            logger.debug(f"Failed to retrieve cached response: {e}")
            return None
    
    def clear_cache(self, older_than_hours: Optional[int] = None):
        """
        Clear cache files.
        
        Args:
            older_than_hours: Only clear files older than X hours. None = clear all.
        """
        try:
            cutoff_time = (
                datetime.now() - timedelta(hours=older_than_hours) 
                if older_than_hours else None
            )
            
            for cache_file in self.offline_cache_dir.glob("*.json"):
                if cutoff_time:
                    file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if file_time > cutoff_time:
                        continue
                
                cache_file.unlink()
            
            logger.info(f"Cache cleared (older than {older_than_hours} hours)" if older_than_hours else "Cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached data."""
        try:
            cache_files = list(self.offline_cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            cached_items = {}
            for cache_file in cache_files:
                try:
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                    cached_items[cache_file.stem] = {
                        "timestamp": data.get("timestamp"),
                        "expires_at": data.get("expires_at"),
                        "size_bytes": cache_file.stat().st_size
                    }
                except:
                    pass
            
            return {
                "cache_dir": str(self.offline_cache_dir),
                "total_items": len(cached_items),
                "total_size_bytes": total_size,
                "items": cached_items
            }
        except Exception as e:
            logger.error(f"Failed to get cache info: {e}")
            return {}


# Global instance
_offline_manager = None


def get_offline_manager(
    check_interval: int = 30,
    offline_cache_dir: str = "offline_cache",
    enable_auto_detection: bool = True
) -> OfflineModeManager:
    """
    Get or create the global offline mode manager instance.
    
    Args:
        check_interval: How often to check connectivity
        offline_cache_dir: Directory for caching
        enable_auto_detection: Whether to auto-detect connectivity
    
    Returns:
        OfflineModeManager instance
    """
    global _offline_manager
    
    if _offline_manager is None:
        _offline_manager = OfflineModeManager(
            check_interval=check_interval,
            offline_cache_dir=offline_cache_dir,
            enable_auto_detection=enable_auto_detection
        )
    
    return _offline_manager
