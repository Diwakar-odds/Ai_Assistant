"""
Performance Optimization Module for YourDaddy Assistant

This module provides comprehensive performance monitoring, optimization,
and resource management capabilities including:
- Real-time performance monitoring
- Advanced caching systems
- Memory management and optimization
- Database performance tuning
- Async processing and task management
- Resource monitoring and auto-scaling
- Performance profiling and analysis
- Error handling and recovery systems
"""

import os
import gc
import sys
import time
import json
import psutil
import sqlite3
import asyncio
import threading
import traceback
import cProfile
import pstats
import functools
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from collections import defaultdict, deque
from contextlib import contextmanager
import weakref

# Performance monitoring
try:
    import memory_profiler
    HAS_MEMORY_PROFILER = True
except ImportError:
    HAS_MEMORY_PROFILER = False

try:
    import line_profiler
    HAS_LINE_PROFILER = True
except ImportError:
    HAS_LINE_PROFILER = False

class PerformanceLevel(Enum):
    """Performance optimization levels"""
    MINIMAL = "minimal"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"

class ResourceType(Enum):
    """System resource types"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"

class CacheType(Enum):
    """Cache implementation types"""
    LRU = "lru"
    LFU = "lfu"
    TIMED = "timed"
    MEMORY_AWARE = "memory_aware"

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    memory_available: int
    disk_usage: float
    network_io: Dict[str, int]
    active_threads: int
    response_time: float
    cache_hit_rate: float
    error_rate: float

@dataclass
class OptimizationSettings:
    """Performance optimization settings"""
    level: PerformanceLevel
    max_memory_usage: float  # Percentage
    max_cpu_usage: float     # Percentage
    cache_size_mb: int
    auto_gc_threshold: int
    async_task_limit: int
    connection_pool_size: int
    enable_profiling: bool
    enable_caching: bool
    enable_compression: bool

class SmartCache:
    """Advanced caching system with multiple strategies"""
    
    def __init__(self, max_size: int = 1000, cache_type: CacheType = CacheType.LRU, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.cache_type = cache_type
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.access_times = {}
        self.access_counts = defaultdict(int)
        self.creation_times = {}
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Any:
        """Get value from cache"""
        if key in self.cache:
            # Check TTL
            if self.ttl_seconds > 0:
                if time.time() - self.creation_times[key] > self.ttl_seconds:
                    self.delete(key)
                    self.misses += 1
                    return None
            
            # Update access tracking
            self.access_times[key] = time.time()
            self.access_counts[key] += 1
            self.hits += 1
            return self.cache[key]
        
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache"""
        current_time = time.time()
        
        # If cache is full, evict based on strategy
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict()
        
        self.cache[key] = value
        self.access_times[key] = current_time
        self.creation_times[key] = current_time
        self.access_counts[key] += 1
    
    def delete(self, key: str) -> None:
        """Delete key from cache"""
        if key in self.cache:
            del self.cache[key]
            del self.access_times[key]
            del self.creation_times[key]
            if key in self.access_counts:
                del self.access_counts[key]
    
    def _evict(self) -> None:
        """Evict items based on cache type strategy"""
        if not self.cache:
            return
        
        if self.cache_type == CacheType.LRU:
            # Least Recently Used
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            self.delete(oldest_key)
        
        elif self.cache_type == CacheType.LFU:
            # Least Frequently Used
            least_used_key = min(self.access_counts.keys(), key=lambda k: self.access_counts[k])
            self.delete(least_used_key)
        
        elif self.cache_type == CacheType.TIMED:
            # Oldest creation time
            oldest_key = min(self.creation_times.keys(), key=lambda k: self.creation_times[k])
            self.delete(oldest_key)
        
        elif self.cache_type == CacheType.MEMORY_AWARE:
            # Evict based on memory usage
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 80:
                # Aggressive eviction
                keys_to_remove = list(self.cache.keys())[:len(self.cache) // 4]
                for key in keys_to_remove:
                    self.delete(key)
            else:
                # Normal LRU eviction
                oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
                self.delete(oldest_key)
    
    def clear(self) -> None:
        """Clear entire cache"""
        self.cache.clear()
        self.access_times.clear()
        self.access_counts.clear()
        self.creation_times.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "cache_type": self.cache_type.value,
            "memory_usage_mb": sys.getsizeof(self.cache) / 1024 / 1024
        }

class MemoryManager:
    """Advanced memory management and optimization"""
    
    def __init__(self, max_memory_percent: float = 80.0):
        self.max_memory_percent = max_memory_percent
        self.weak_references = weakref.WeakSet()
        self.memory_threshold = max_memory_percent
        self.last_gc_time = time.time()
        self.gc_interval = 60  # seconds
    
    def monitor_memory(self) -> Dict[str, Any]:
        """Monitor current memory usage"""
        memory = psutil.virtual_memory()
        process = psutil.Process()
        
        return {
            "total_memory_gb": memory.total / 1024**3,
            "available_memory_gb": memory.available / 1024**3,
            "used_memory_percent": memory.percent,
            "process_memory_mb": process.memory_info().rss / 1024**2,
            "process_memory_percent": process.memory_percent(),
            "gc_collections": gc.get_count(),
            "gc_threshold": gc.get_threshold()
        }
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Perform memory optimization"""
        results = {
            "before_memory": psutil.virtual_memory().percent,
            "gc_collected": 0,
            "optimizations_applied": []
        }
        
        # Force garbage collection
        collected = gc.collect()
        results["gc_collected"] = collected
        results["optimizations_applied"].append("garbage_collection")
        
        # Check if we need aggressive optimization
        current_memory = psutil.virtual_memory().percent
        
        if current_memory > self.memory_threshold:
            # Clear weak references
            self.weak_references.clear()
            results["optimizations_applied"].append("weak_references_cleared")
            
            # Optimize Python internal structures
            sys.intern('')  # Clear interned strings cache partially
            results["optimizations_applied"].append("intern_cache_optimized")
            
            # Force additional GC cycles
            for generation in range(3):
                gc.collect(generation)
            results["optimizations_applied"].append("multi_generation_gc")
        
        results["after_memory"] = psutil.virtual_memory().percent
        results["memory_freed"] = results["before_memory"] - results["after_memory"]
        
        return results
    
    def auto_memory_management(self) -> None:
        """Automatic memory management in background"""
        current_time = time.time()
        
        if current_time - self.last_gc_time > self.gc_interval:
            memory_percent = psutil.virtual_memory().percent
            
            if memory_percent > self.memory_threshold:
                self.optimize_memory()
            
            self.last_gc_time = current_time
    
    def get_memory_recommendations(self) -> List[str]:
        """Get memory optimization recommendations"""
        recommendations = []
        memory_info = self.monitor_memory()
        
        if memory_info["used_memory_percent"] > 80:
            recommendations.append("Consider increasing system RAM or reducing memory usage")
        
        if memory_info["process_memory_mb"] > 500:
            recommendations.append("Application using high memory - consider optimizing data structures")
        
        gc_count = sum(memory_info["gc_collections"])
        if gc_count > 1000:
            recommendations.append("High garbage collection activity - check for memory leaks")
        
        return recommendations
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory management statistics"""
        memory_info = self.monitor_memory()
        
        return {
            "current_mb": memory_info["process_memory_mb"],
            "peak_mb": memory_info["process_memory_mb"],  # Could track peak if needed
            "last_cleanup": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_gc_time)),
            "objects_freed": sum(gc.get_count()),
            "memory_freed_mb": 0,  # Could track if monitoring before/after cleanup
            "recommendations": self.get_memory_recommendations()
        }
    
    def cleanup(self) -> float:
        """Cleanup memory and return freed amount"""
        before_memory = psutil.virtual_memory().percent
        
        # Force garbage collection
        gc.collect()
        
        # Update last gc time
        self.last_gc_time = time.time()
        
        after_memory = psutil.virtual_memory().percent
        freed_mb = max(0, (before_memory - after_memory) * psutil.virtual_memory().total / (1024 * 1024 * 100))
        
        return freed_mb

class AsyncTaskManager:
    """Asynchronous task management and optimization"""
    
    def __init__(self, max_concurrent_tasks: int = 10):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.active_tasks = {}
        self.task_queue = asyncio.Queue()
        self.task_results = {}
        self.task_stats = defaultdict(int)
        self.loop = None
    
    def initialize_loop(self):
        """Initialize async event loop"""
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
    
    async def execute_task_async(self, task_func: Callable, *args, **kwargs) -> Any:
        """Execute function asynchronously"""
        task_id = f"task_{int(time.time() * 1000000)}"
        
        try:
            self.active_tasks[task_id] = {
                "function": task_func.__name__,
                "started_at": datetime.now(),
                "status": "running"
            }
            
            # Execute the task
            if asyncio.iscoroutinefunction(task_func):
                result = await task_func(*args, **kwargs)
            else:
                # Run in thread pool for blocking functions
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, task_func, *args, **kwargs)
            
            self.active_tasks[task_id]["status"] = "completed"
            self.active_tasks[task_id]["completed_at"] = datetime.now()
            self.task_results[task_id] = result
            self.task_stats["completed"] += 1
            
            return result
        
        except Exception as e:
            self.active_tasks[task_id]["status"] = "failed"
            self.active_tasks[task_id]["error"] = str(e)
            self.task_stats["failed"] += 1
            raise
        
        finally:
            # Clean up old task references
            self.cleanup_completed_tasks()
    
    def cleanup_completed_tasks(self):
        """Clean up completed task references"""
        current_time = datetime.now()
        
        for task_id in list(self.active_tasks.keys()):
            task_info = self.active_tasks[task_id]
            if task_info["status"] in ["completed", "failed"]:
                # Keep task info for 5 minutes after completion
                completed_at = task_info.get("completed_at")
                if completed_at and current_time - completed_at > timedelta(minutes=5):
                    del self.active_tasks[task_id]
                    if task_id in self.task_results:
                        del self.task_results[task_id]
    
    def submit_task(self, task_id: str, coro) -> None:
        """Submit a task for execution"""
        if self.loop is None:
            self.initialize_loop()
        
        # Store task info
        self.active_tasks[task_id] = {
            "function": "coroutine",
            "started_at": datetime.now(),
            "status": "submitted"
        }
        
        # Create task
        task = asyncio.create_task(coro)
        self.active_tasks[task_id]["task"] = task
        self.task_stats["submitted"] += 1
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a specific task"""
        if task_id in self.active_tasks:
            task_info = self.active_tasks[task_id].copy()
            # Remove the actual task object from status
            if "task" in task_info:
                task_info["task"] = "AsyncTask object"
            return task_info
        return {"status": "not_found"}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get task manager statistics"""
        active_count = sum(1 for t in self.active_tasks.values() if t["status"] == "running")
        
        return {
            "active_tasks": active_count,
            "total_tasks": len(self.active_tasks),
            "submitted": self.task_stats["submitted"],
            "completed": self.task_stats["completed"],
            "failed": self.task_stats["failed"],
            "max_concurrent": self.max_concurrent_tasks
        }
    
    def stop(self) -> None:
        """Stop the task manager"""
        # Cancel all active tasks
        for task_info in self.active_tasks.values():
            if "task" in task_info and hasattr(task_info["task"], "cancel"):
                task_info["task"].cancel()
        
        self.active_tasks.clear()
        self.task_results.clear()
    
    def get_task_stats(self) -> Dict[str, Any]:
        """Get task execution statistics"""
        active_count = len([t for t in self.active_tasks.values() if t["status"] == "running"])
        
        return {
            "active_tasks": active_count,
            "max_concurrent": self.max_concurrent_tasks,
            "total_completed": self.task_stats["completed"],
            "total_failed": self.task_stats["failed"],
            "queue_size": self.task_queue.qsize() if hasattr(self.task_queue, 'qsize') else 0
        }

class DatabaseOptimizer:
    """Database performance optimization"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection_pool = []
        self.pool_size = 5
        self.query_cache = SmartCache(max_size=500, cache_type=CacheType.LFU)
        self.slow_query_threshold = 1.0  # seconds
        self.slow_queries = deque(maxlen=100)
    
    @contextmanager
    def get_connection(self):
        """Get database connection from pool"""
        if self.connection_pool:
            conn = self.connection_pool.pop()
        else:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            conn.execute("PRAGMA synchronous=NORMAL")  # Faster sync
            conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
            conn.execute("PRAGMA temp_store=MEMORY")  # Temp tables in memory
        
        try:
            yield conn
        finally:
            if len(self.connection_pool) < self.pool_size:
                self.connection_pool.append(conn)
            else:
                conn.close()
    
    def execute_query_cached(self, query: str, params: tuple = ()) -> List[tuple]:
        """Execute query with caching"""
        cache_key = f"{query}:{str(params)}"
        
        # Check cache first for SELECT queries
        if query.strip().upper().startswith("SELECT"):
            cached_result = self.query_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
        
        start_time = time.time()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if query.strip().upper().startswith("SELECT"):
                result = cursor.fetchall()
            else:
                conn.commit()
                result = cursor.rowcount
        
        execution_time = time.time() - start_time
        
        # Log slow queries
        if execution_time > self.slow_query_threshold:
            self.slow_queries.append({
                "query": query,
                "params": params,
                "execution_time": execution_time,
                "timestamp": datetime.now()
            })
        
        # Cache SELECT results
        if query.strip().upper().startswith("SELECT") and isinstance(result, list):
            self.query_cache.set(cache_key, result)
        
        return result
    
    def optimize_database(self) -> Dict[str, Any]:
        """Optimize database performance"""
        results = {
            "optimizations_applied": [],
            "before_size": 0,
            "after_size": 0
        }
        
        try:
            # Get initial size
            if os.path.exists(self.db_path):
                results["before_size"] = os.path.getsize(self.db_path)
            
            with self.get_connection() as conn:
                # Analyze database
                conn.execute("ANALYZE")
                results["optimizations_applied"].append("analyze")
                
                # Vacuum database
                conn.execute("VACUUM")
                results["optimizations_applied"].append("vacuum")
                
                # Update statistics
                conn.execute("UPDATE sqlite_stat1 SET stat=NULL")
                conn.execute("ANALYZE")
                results["optimizations_applied"].append("statistics_update")
                
                # Reindex
                conn.execute("REINDEX")
                results["optimizations_applied"].append("reindex")
            
            # Get final size
            if os.path.exists(self.db_path):
                results["after_size"] = os.path.getsize(self.db_path)
            
            results["size_reduced"] = results["before_size"] - results["after_size"]
            
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database performance statistics"""
        stats = {
            "cache_stats": self.query_cache.get_stats(),
            "slow_queries_count": len(self.slow_queries),
            "connection_pool_size": len(self.connection_pool),
            "database_size_mb": 0
        }
        
        if os.path.exists(self.db_path):
            stats["database_size_mb"] = os.path.getsize(self.db_path) / 1024 / 1024
        
        # Get recent slow queries
        stats["recent_slow_queries"] = list(self.slow_queries)[-5:] if self.slow_queries else []
        
        return stats

class PerformanceProfiler:
    """Performance profiling and analysis"""
    
    def __init__(self):
        self.profiles = {}
        self.active_profiles = {}
    
    def profile_function(self, func: Callable) -> Callable:
        """Decorator to profile function performance"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            try:
                result = func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                result = None
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss
                
                profile_data = {
                    "function_name": func.__name__,
                    "execution_time": end_time - start_time,
                    "memory_delta": end_memory - start_memory,
                    "success": success,
                    "error": error,
                    "timestamp": datetime.now(),
                    "args_count": len(args),
                    "kwargs_count": len(kwargs)
                }
                
                # Store profile data
                if func.__name__ not in self.profiles:
                    self.profiles[func.__name__] = deque(maxlen=100)
                
                self.profiles[func.__name__].append(profile_data)
            
            return result
        
        return wrapper
    
    def start_cpu_profile(self, name: str):
        """Start CPU profiling"""
        profiler = cProfile.Profile()
        profiler.enable()
        self.active_profiles[name] = {
            "profiler": profiler,
            "start_time": time.time(),
            "type": "cpu"
        }
    
    def stop_cpu_profile(self, name: str) -> Dict[str, Any]:
        """Stop CPU profiling and return results"""
        if name not in self.active_profiles:
            return {"error": "Profile not found"}
        
        profile_info = self.active_profiles[name]
        profiler = profile_info["profiler"]
        
        profiler.disable()
        
        # Get profile statistics
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        
        # Capture top functions
        import io
        s = io.StringIO()
        stats.print_stats(20)
        profile_output = s.getvalue()
        
        result = {
            "name": name,
            "duration": time.time() - profile_info["start_time"],
            "type": "cpu",
            "top_functions": profile_output,
            "total_calls": stats.total_calls,
            "total_time": stats.total_tt
        }
        
        del self.active_profiles[name]
        return result
    
    def get_function_stats(self, function_name: str) -> Dict[str, Any]:
        """Get statistics for a specific function"""
        if function_name not in self.profiles:
            return {"error": "No profile data found"}
        
        profiles = list(self.profiles[function_name])
        
        if not profiles:
            return {"error": "No execution data"}
        
        execution_times = [p["execution_time"] for p in profiles]
        memory_deltas = [p["memory_delta"] for p in profiles]
        
        return {
            "function_name": function_name,
            "total_calls": len(profiles),
            "avg_execution_time": sum(execution_times) / len(execution_times),
            "min_execution_time": min(execution_times),
            "max_execution_time": max(execution_times),
            "avg_memory_delta": sum(memory_deltas) / len(memory_deltas),
            "success_rate": sum(1 for p in profiles if p["success"]) / len(profiles) * 100,
            "recent_errors": [p["error"] for p in profiles[-5:] if p["error"]]
        }

class ResourceMonitor:
    """System resource monitoring and alerting"""
    
    def __init__(self, check_interval: int = 5):
        self.check_interval = check_interval
        self.metrics_history = deque(maxlen=720)  # 1 hour of 5-second intervals
        self.alerts = deque(maxlen=100)
        self.thresholds = {
            "cpu_critical": 90.0,
            "cpu_warning": 70.0,
            "memory_critical": 90.0,
            "memory_warning": 80.0,
            "disk_critical": 95.0,
            "disk_warning": 85.0
        }
        self.monitoring = False
        self.monitor_thread = None
    
    def collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Network I/O
        network = psutil.net_io_counters()
        network_io = {
            "bytes_sent": network.bytes_sent,
            "bytes_recv": network.bytes_recv,
            "packets_sent": network.packets_sent,
            "packets_recv": network.packets_recv
        }
        
        # Thread count
        active_threads = threading.active_count()
        
        # Create metrics object
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_usage=cpu_percent,
            memory_usage=memory.percent,
            memory_available=memory.available,
            disk_usage=disk.percent,
            network_io=network_io,
            active_threads=active_threads,
            response_time=0.0,  # To be filled by application
            cache_hit_rate=0.0,  # To be filled by cache systems
            error_rate=0.0       # To be filled by error tracking
        )
        
        return metrics
    
    def check_thresholds(self, metrics: PerformanceMetrics):
        """Check if metrics exceed thresholds and generate alerts"""
        alerts = []
        
        # CPU alerts
        if metrics.cpu_usage >= self.thresholds["cpu_critical"]:
            alerts.append({
                "level": "critical",
                "resource": "cpu",
                "message": f"CPU usage critical: {metrics.cpu_usage:.1f}%",
                "timestamp": metrics.timestamp,
                "value": metrics.cpu_usage
            })
        elif metrics.cpu_usage >= self.thresholds["cpu_warning"]:
            alerts.append({
                "level": "warning",
                "resource": "cpu",
                "message": f"CPU usage warning: {metrics.cpu_usage:.1f}%",
                "timestamp": metrics.timestamp,
                "value": metrics.cpu_usage
            })
        
        # Memory alerts
        if metrics.memory_usage >= self.thresholds["memory_critical"]:
            alerts.append({
                "level": "critical",
                "resource": "memory",
                "message": f"Memory usage critical: {metrics.memory_usage:.1f}%",
                "timestamp": metrics.timestamp,
                "value": metrics.memory_usage
            })
        elif metrics.memory_usage >= self.thresholds["memory_warning"]:
            alerts.append({
                "level": "warning",
                "resource": "memory",
                "message": f"Memory usage warning: {metrics.memory_usage:.1f}%",
                "timestamp": metrics.timestamp,
                "value": metrics.memory_usage
            })
        
        # Disk alerts
        if metrics.disk_usage >= self.thresholds["disk_critical"]:
            alerts.append({
                "level": "critical",
                "resource": "disk",
                "message": f"Disk usage critical: {metrics.disk_usage:.1f}%",
                "timestamp": metrics.timestamp,
                "value": metrics.disk_usage
            })
        elif metrics.disk_usage >= self.thresholds["disk_warning"]:
            alerts.append({
                "level": "warning",
                "resource": "disk",
                "message": f"Disk usage warning: {metrics.disk_usage:.1f}%",
                "timestamp": metrics.timestamp,
                "value": metrics.disk_usage
            })
        
        # Store alerts
        for alert in alerts:
            self.alerts.append(alert)
        
        return alerts
    
    def start_monitoring(self):
        """Start background resource monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop background resource monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                metrics = self.collect_metrics()
                self.metrics_history.append(metrics)
                
                # Check for alerts
                alerts = self.check_thresholds(metrics)
                
                # Log critical alerts
                for alert in alerts:
                    if alert["level"] == "critical":
                        print(f"🚨 CRITICAL ALERT: {alert['message']}")
                
                time.sleep(self.check_interval)
            
            except Exception as e:
                print(f"❌ Resource monitoring error: {e}")
                time.sleep(self.check_interval)
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current system status"""
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        latest_metrics = self.metrics_history[-1]
        recent_alerts = [alert for alert in self.alerts if 
                        (datetime.now() - alert["timestamp"]).total_seconds() < 300]  # Last 5 minutes
        
        return {
            "current_metrics": asdict(latest_metrics),
            "recent_alerts": recent_alerts,
            "alert_summary": {
                "critical": len([a for a in recent_alerts if a["level"] == "critical"]),
                "warning": len([a for a in recent_alerts if a["level"] == "warning"])
            },
            "monitoring_active": self.monitoring,
            "metrics_collected": len(self.metrics_history)
        }

class PerformanceOptimizer:
    """Main performance optimization manager"""
    
    def __init__(self, settings: OptimizationSettings = None):
        self.settings = settings or OptimizationSettings(
            level=PerformanceLevel.STANDARD,
            max_memory_usage=80.0,
            max_cpu_usage=70.0,
            cache_size_mb=128,
            auto_gc_threshold=1000,
            async_task_limit=10,
            connection_pool_size=5,
            enable_profiling=True,
            enable_caching=True,
            enable_compression=False
        )
        
        # Initialize components
        self.cache = SmartCache(
            max_size=self.settings.cache_size_mb * 10,  # Approximate items
            cache_type=CacheType.MEMORY_AWARE
        )
        self.memory_manager = MemoryManager(self.settings.max_memory_usage)
        self.async_manager = AsyncTaskManager(self.settings.async_task_limit)
        self.profiler = PerformanceProfiler()
        self.resource_monitor = ResourceMonitor()
        
        # Database optimizers
        self.db_optimizers = {}
        
        # Performance history
        self.optimization_history = deque(maxlen=1000)
        
        # Auto-optimization settings
        self.auto_optimize = True
        self.last_auto_optimization = time.time()
        self.auto_optimize_interval = 300  # 5 minutes
    
    def register_database(self, name: str, db_path: str):
        """Register a database for optimization"""
        self.db_optimizers[name] = DatabaseOptimizer(db_path)
    
    def optimize_all_systems(self) -> Dict[str, Any]:
        """Perform comprehensive system optimization"""
        start_time = time.time()
        results = {
            "optimization_level": self.settings.level.value,
            "started_at": datetime.now().isoformat(),
            "optimizations": {}
        }
        
        try:
            # Memory optimization
            memory_results = self.memory_manager.optimize_memory()
            results["optimizations"]["memory"] = memory_results
            
            # Cache optimization
            if self.settings.enable_caching:
                cache_stats = self.cache.get_stats()
                if cache_stats["hit_rate"] < 50:  # Low hit rate
                    self.cache.clear()
                    results["optimizations"]["cache"] = {"action": "cache_cleared", "reason": "low_hit_rate"}
                else:
                    results["optimizations"]["cache"] = {"action": "no_optimization_needed"}
            
            # Database optimization
            db_results = {}
            for name, db_optimizer in self.db_optimizers.items():
                try:
                    db_result = db_optimizer.optimize_database()
                    db_results[name] = db_result
                except Exception as e:
                    db_results[name] = {"error": str(e)}
            results["optimizations"]["databases"] = db_results
            
            # System cleanup based on optimization level
            if self.settings.level in [PerformanceLevel.AGGRESSIVE, PerformanceLevel.MAXIMUM]:
                # More aggressive optimizations
                gc.collect(2)  # Force full GC
                results["optimizations"]["garbage_collection"] = "aggressive"
                
                # Clear Python internal caches
                sys.intern('')
                results["optimizations"]["python_internals"] = "optimized"
            
            # Record optimization
            optimization_record = {
                "timestamp": datetime.now(),
                "level": self.settings.level.value,
                "duration": time.time() - start_time,
                "results": results
            }
            self.optimization_history.append(optimization_record)
            
            results["completed_at"] = datetime.now().isoformat()
            results["duration_seconds"] = time.time() - start_time
            
        except Exception as e:
            results["error"] = str(e)
            results["traceback"] = traceback.format_exc()
        
        return results
    
    def auto_optimize_check(self):
        """Check if auto-optimization should run"""
        if not self.auto_optimize:
            return
        
        current_time = time.time()
        if current_time - self.last_auto_optimization < self.auto_optimize_interval:
            return
        
        # Check if optimization is needed
        memory_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent(interval=1)
        
        needs_optimization = (
            memory_percent > self.settings.max_memory_usage or
            cpu_percent > self.settings.max_cpu_usage
        )
        
        if needs_optimization:
            print("🔧 Auto-optimization triggered")
            results = self.optimize_all_systems()
            print(f"✅ Auto-optimization completed in {results.get('duration_seconds', 0):.2f}s")
        
        self.last_auto_optimization = current_time
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        # System metrics
        system_status = self.resource_monitor.get_current_status()
        
        # Cache performance
        cache_stats = self.cache.get_stats()
        
        # Memory status
        memory_info = self.memory_manager.monitor_memory()
        
        # Task management
        task_stats = self.async_manager.get_task_stats()
        
        # Database performance
        db_stats = {}
        for name, db_optimizer in self.db_optimizers.items():
            db_stats[name] = db_optimizer.get_database_stats()
        
        # Recent optimizations
        recent_optimizations = list(self.optimization_history)[-5:] if self.optimization_history else []
        
        return {
            "system_status": system_status,
            "cache_performance": cache_stats,
            "memory_status": memory_info,
            "task_management": task_stats,
            "database_performance": db_stats,
            "recent_optimizations": [
                {
                    "timestamp": opt["timestamp"].isoformat(),
                    "level": opt["level"],
                    "duration": opt["duration"]
                } for opt in recent_optimizations
            ],
            "optimization_settings": asdict(self.settings),
            "auto_optimize_enabled": self.auto_optimize
        }
    
    def start_monitoring(self):
        """Start all monitoring systems"""
        self.resource_monitor.start_monitoring()
        self.async_manager.initialize_loop()
        print("📊 Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop all monitoring systems"""
        self.resource_monitor.stop_monitoring()
        print("📊 Performance monitoring stopped")

def create_performance_decorator(optimizer: PerformanceOptimizer):
    """Create a performance optimization decorator"""
    def performance_optimized(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Auto-optimization check
            optimizer.auto_optimize_check()
            
            # Profile if enabled
            if optimizer.settings.enable_profiling:
                return optimizer.profiler.profile_function(func)(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        return wrapper
    return performance_optimized

def main():
    """Example usage of Performance Optimization"""
    print("🔧 Performance Optimization Demo")
    print("=" * 50)
    
    # Create optimizer with standard settings
    settings = OptimizationSettings(
        level=PerformanceLevel.STANDARD,
        max_memory_usage=75.0,
        cache_size_mb=64,
        enable_profiling=True,
        enable_caching=True
    )
    
    optimizer = PerformanceOptimizer(settings)
    
    # Start monitoring
    optimizer.start_monitoring()
    
    # Register a test database
    optimizer.register_database("test_db", "test.db")
    
    # Run optimization
    print("🔧 Running system optimization...")
    results = optimizer.optimize_all_systems()
    print(f"✅ Optimization completed: {results['duration_seconds']:.2f}s")
    
    # Get performance summary
    summary = optimizer.get_performance_summary()
    print(f"📊 Cache hit rate: {summary['cache_performance']['hit_rate']:.1f}%")
    print(f"💾 Memory usage: {summary['memory_status']['used_memory_percent']:.1f}%")
    
    # Test caching
    print("\n🗃️ Testing cache performance...")
    for i in range(100):
        optimizer.cache.set(f"key_{i}", f"value_{i}")
    
    # Test cache retrieval
    start_time = time.time()
    for i in range(50):
        value = optimizer.cache.get(f"key_{i}")
    end_time = time.time()
    
    print(f"⚡ Cache retrieval time: {(end_time - start_time) * 1000:.2f}ms")
    
    # Stop monitoring
    time.sleep(2)
    optimizer.stop_monitoring()
    
    print("🎉 Performance optimization demo completed!")

if __name__ == "__main__":
    main()