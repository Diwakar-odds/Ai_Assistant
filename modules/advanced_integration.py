"""
Advanced System Integration for YourDaddy Assistant

This module provides deep system integration capabilities including:
- System-wide hooks and event monitoring
- Advanced OS integration (Windows, macOS, Linux)
- Cross-platform compatibility layer
- Hardware access and control
- System service management
- Performance optimization
- Security and permissions management
"""

import os
import sys
import platform
import subprocess
import threading
import time
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import psutil
if platform.system() == "Windows":
    import winreg
else:
    winreg = None
import signal
import socket
from pathlib import Path

class SystemType(Enum):
    """Supported system types"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"

class HookType(Enum):
    """Types of system hooks"""
    FILE_SYSTEM = "filesystem"
    PROCESS = "process"
    NETWORK = "network"
    USB_DEVICE = "usb_device"
    POWER = "power"
    WINDOW = "window"
    KEYBOARD = "keyboard"
    MOUSE = "mouse"

@dataclass
class SystemEvent:
    """Represents a system event"""
    event_id: str
    hook_type: HookType
    timestamp: datetime
    data: Dict[str, Any]
    source: str
    processed: bool = False

@dataclass
class IntegrationCapability:
    """Represents a system integration capability"""
    name: str
    supported_platforms: List[SystemType]
    requires_admin: bool
    description: str
    implementation: Optional[Callable] = None

class PlatformAdapter:
    """Cross-platform compatibility adapter"""
    
    def __init__(self):
        self.system_type = self._detect_system()
        self.capabilities = self._initialize_capabilities()
    
    def _detect_system(self) -> SystemType:
        """Detect the current operating system"""
        system = platform.system().lower()
        if system == "windows":
            return SystemType.WINDOWS
        elif system == "darwin":
            return SystemType.MACOS
        elif system == "linux":
            return SystemType.LINUX
        else:
            return SystemType.UNKNOWN
    
    def _initialize_capabilities(self) -> Dict[str, IntegrationCapability]:
        """Initialize platform-specific capabilities"""
        capabilities = {}
        
        # File system monitoring
        capabilities["fs_monitor"] = IntegrationCapability(
            name="File System Monitor",
            supported_platforms=[SystemType.WINDOWS, SystemType.MACOS, SystemType.LINUX],
            requires_admin=False,
            description="Monitor file system changes in real-time",
            implementation=self._setup_fs_monitor
        )
        
        # Process monitoring
        capabilities["process_monitor"] = IntegrationCapability(
            name="Process Monitor",
            supported_platforms=[SystemType.WINDOWS, SystemType.MACOS, SystemType.LINUX],
            requires_admin=True,
            description="Monitor process creation and termination",
            implementation=self._setup_process_monitor
        )
        
        # Registry access (Windows only)
        if self.system_type == SystemType.WINDOWS:
            capabilities["registry_access"] = IntegrationCapability(
                name="Registry Access",
                supported_platforms=[SystemType.WINDOWS],
                requires_admin=True,
                description="Read/write Windows registry",
                implementation=self._setup_registry_access
            )
        
        # System services
        capabilities["service_control"] = IntegrationCapability(
            name="Service Control",
            supported_platforms=[SystemType.WINDOWS, SystemType.LINUX],
            requires_admin=True,
            description="Control system services",
            implementation=self._setup_service_control
        )
        
        # Hardware monitoring
        capabilities["hardware_monitor"] = IntegrationCapability(
            name="Hardware Monitor",
            supported_platforms=[SystemType.WINDOWS, SystemType.MACOS, SystemType.LINUX],
            requires_admin=False,
            description="Monitor CPU, memory, disk, network usage",
            implementation=self._setup_hardware_monitor
        )
        
        # Window management
        capabilities["window_manager"] = IntegrationCapability(
            name="Window Manager",
            supported_platforms=[SystemType.WINDOWS, SystemType.LINUX],
            requires_admin=False,
            description="Advanced window control and monitoring",
            implementation=self._setup_window_manager
        )
        
        return capabilities
    
    def is_capability_supported(self, capability_name: str) -> bool:
        """Check if a capability is supported on current platform"""
        if capability_name not in self.capabilities:
            return False
        
        capability = self.capabilities[capability_name]
        return self.system_type in capability.supported_platforms
    
    def requires_admin(self, capability_name: str) -> bool:
        """Check if a capability requires admin privileges"""
        if capability_name not in self.capabilities:
            return False
        
        return self.capabilities[capability_name].requires_admin
    
    def get_supported_capabilities(self) -> List[str]:
        """Get list of supported capabilities for current platform"""
        supported = []
        for name, capability in self.capabilities.items():
            if self.system_type in capability.supported_platforms:
                supported.append(name)
        return supported
    
    def _setup_fs_monitor(self):
        """Setup file system monitoring"""
        try:
            if self.system_type == SystemType.WINDOWS:
                import win32file
                import win32con
                return self._windows_fs_monitor
            elif self.system_type == SystemType.LINUX:
                import inotify
                return self._linux_fs_monitor
            elif self.system_type == SystemType.MACOS:
                return self._macos_fs_monitor
        except ImportError:
            return None
    
    def _setup_process_monitor(self):
        """Setup process monitoring"""
        if self.system_type == SystemType.WINDOWS:
            return self._windows_process_monitor
        elif self.system_type in [SystemType.LINUX, SystemType.MACOS]:
            return self._unix_process_monitor
    
    def _setup_registry_access(self):
        """Setup Windows registry access"""
        if self.system_type == SystemType.WINDOWS:
            return WindowsRegistryManager()
        return None
    
    def _setup_service_control(self):
        """Setup system service control"""
        if self.system_type == SystemType.WINDOWS:
            return WindowsServiceManager()
        elif self.system_type == SystemType.LINUX:
            return LinuxServiceManager()
        return None
    
    def _setup_hardware_monitor(self):
        """Setup hardware monitoring"""
        return HardwareMonitor()
    
    def _setup_window_manager(self):
        """Setup window management"""
        if self.system_type == SystemType.WINDOWS:
            return WindowsWindowManager()
        elif self.system_type == SystemType.LINUX:
            return LinuxWindowManager()
        return None

class SystemHookManager:
    """Manages system-wide hooks and events"""
    
    def __init__(self, db_path: str = "system_hooks.db"):
        self.db_path = db_path
        self.adapter = PlatformAdapter()
        self.hooks = {}
        self.event_handlers = {}
        self.monitoring_threads = {}
        self.is_monitoring = False
        
        self.init_database()
    
    def init_database(self):
        """Initialize hooks database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_events (
                event_id TEXT PRIMARY KEY,
                hook_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                source TEXT NOT NULL,
                processed INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hook_configs (
                hook_name TEXT PRIMARY KEY,
                hook_type TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_hook(self, hook_name: str, hook_type: HookType, config: Dict[str, Any] = None):
        """Register a new system hook"""
        if not self.adapter.is_capability_supported(hook_type.value):
            raise ValueError(f"Hook type {hook_type.value} not supported on {self.adapter.system_type.value}")
        
        self.hooks[hook_name] = {
            "type": hook_type,
            "config": config or {},
            "active": False
        }
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO hook_configs (hook_name, hook_type, config)
            VALUES (?, ?, ?)
        ''', (hook_name, hook_type.value, json.dumps(config or {})))
        conn.commit()
        conn.close()
    
    def start_hook(self, hook_name: str):
        """Start monitoring for a specific hook"""
        if hook_name not in self.hooks:
            raise ValueError(f"Hook {hook_name} not registered")
        
        hook = self.hooks[hook_name]
        hook_type = hook["type"]
        
        if hook_type == HookType.FILE_SYSTEM:
            self._start_filesystem_hook(hook_name, hook["config"])
        elif hook_type == HookType.PROCESS:
            self._start_process_hook(hook_name, hook["config"])
        elif hook_type == HookType.NETWORK:
            self._start_network_hook(hook_name, hook["config"])
        elif hook_type == HookType.POWER:
            self._start_power_hook(hook_name, hook["config"])
        
        hook["active"] = True
    
    def stop_hook(self, hook_name: str):
        """Stop monitoring for a specific hook"""
        if hook_name in self.monitoring_threads:
            # Signal thread to stop
            self.monitoring_threads[hook_name]["stop"] = True
            self.hooks[hook_name]["active"] = False
    
    def register_event_handler(self, hook_type: HookType, handler: Callable[[SystemEvent], None]):
        """Register an event handler for a hook type"""
        if hook_type not in self.event_handlers:
            self.event_handlers[hook_type] = []
        self.event_handlers[hook_type].append(handler)
    
    def _emit_event(self, hook_type: HookType, data: Dict[str, Any], source: str):
        """Emit a system event"""
        event = SystemEvent(
            event_id=f"{hook_type.value}_{int(time.time() * 1000)}",
            hook_type=hook_type,
            timestamp=datetime.now(),
            data=data,
            source=source
        )
        
        # Store in database
        self._store_event(event)
        
        # Call registered handlers
        if hook_type in self.event_handlers:
            for handler in self.event_handlers[hook_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in event handler: {e}")
    
    def _store_event(self, event: SystemEvent):
        """Store event in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_events (event_id, hook_type, data, source)
            VALUES (?, ?, ?, ?)
        ''', (event.event_id, event.hook_type.value, json.dumps(event.data), event.source))
        conn.commit()
        conn.close()
    
    def _start_filesystem_hook(self, hook_name: str, config: Dict[str, Any]):
        """Start filesystem monitoring hook"""
        watch_paths = config.get("paths", [os.getcwd()])
        
        def monitor_filesystem():
            thread_data = {"stop": False}
            self.monitoring_threads[hook_name] = thread_data
            
            # Simple polling-based implementation for cross-platform compatibility
            last_check = {}
            
            while not thread_data["stop"]:
                for path in watch_paths:
                    try:
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                filepath = os.path.join(root, file)
                                try:
                                    stat = os.stat(filepath)
                                    mtime = stat.st_mtime
                                    
                                    if filepath not in last_check or last_check[filepath] != mtime:
                                        if filepath in last_check:
                                            # File was modified
                                            self._emit_event(HookType.FILE_SYSTEM, {
                                                "action": "modified",
                                                "path": filepath,
                                                "size": stat.st_size,
                                                "mtime": mtime
                                            }, hook_name)
                                        last_check[filepath] = mtime
                                except (OSError, IOError):
                                    continue
                    except (OSError, IOError):
                        continue
                
                time.sleep(config.get("interval", 1))
        
        thread = threading.Thread(target=monitor_filesystem, daemon=True)
        thread.start()
    
    def _start_process_hook(self, hook_name: str, config: Dict[str, Any]):
        """Start process monitoring hook"""
        def monitor_processes():
            thread_data = {"stop": False}
            self.monitoring_threads[hook_name] = thread_data
            
            last_processes = set(p.pid for p in psutil.process_iter())
            
            while not thread_data["stop"]:
                try:
                    current_processes = set(p.pid for p in psutil.process_iter())
                    
                    # New processes
                    new_processes = current_processes - last_processes
                    for pid in new_processes:
                        try:
                            process = psutil.Process(pid)
                            self._emit_event(HookType.PROCESS, {
                                "action": "created",
                                "pid": pid,
                                "name": process.name(),
                                "cmdline": process.cmdline(),
                                "username": process.username()
                            }, hook_name)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    # Terminated processes
                    terminated_processes = last_processes - current_processes
                    for pid in terminated_processes:
                        self._emit_event(HookType.PROCESS, {
                            "action": "terminated",
                            "pid": pid
                        }, hook_name)
                    
                    last_processes = current_processes
                    
                except Exception as e:
                    print(f"Process monitoring error: {e}")
                
                time.sleep(config.get("interval", 2))
        
        thread = threading.Thread(target=monitor_processes, daemon=True)
        thread.start()
    
    def _start_network_hook(self, hook_name: str, config: Dict[str, Any]):
        """Start network monitoring hook"""
        def monitor_network():
            thread_data = {"stop": False}
            self.monitoring_threads[hook_name] = thread_data
            
            last_connections = set()
            
            while not thread_data["stop"]:
                try:
                    current_connections = set()
                    for conn in psutil.net_connections():
                        if conn.status == psutil.CONN_ESTABLISHED:
                            current_connections.add((conn.laddr, conn.raddr, conn.pid))
                    
                    # New connections
                    new_connections = current_connections - last_connections
                    for laddr, raddr, pid in new_connections:
                        try:
                            process_name = psutil.Process(pid).name() if pid else "unknown"
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            process_name = "unknown"
                        
                        self._emit_event(HookType.NETWORK, {
                            "action": "connection_established",
                            "local_addr": laddr,
                            "remote_addr": raddr,
                            "pid": pid,
                            "process": process_name
                        }, hook_name)
                    
                    last_connections = current_connections
                    
                except Exception as e:
                    print(f"Network monitoring error: {e}")
                
                time.sleep(config.get("interval", 5))
        
        thread = threading.Thread(target=monitor_network, daemon=True)
        thread.start()
    
    def _start_power_hook(self, hook_name: str, config: Dict[str, Any]):
        """Start power monitoring hook"""
        def monitor_power():
            thread_data = {"stop": False}
            self.monitoring_threads[hook_name] = thread_data
            
            last_battery = None
            last_power_plugged = None
            
            while not thread_data["stop"]:
                try:
                    battery = psutil.sensors_battery()
                    if battery:
                        current_battery = battery.percent
                        current_power_plugged = battery.power_plugged
                        
                        if last_battery is not None:
                            if abs(current_battery - last_battery) > 5:  # 5% change
                                self._emit_event(HookType.POWER, {
                                    "action": "battery_change",
                                    "percent": current_battery,
                                    "power_plugged": current_power_plugged,
                                    "time_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
                                }, hook_name)
                        
                        if last_power_plugged is not None and current_power_plugged != last_power_plugged:
                            self._emit_event(HookType.POWER, {
                                "action": "power_status_change",
                                "power_plugged": current_power_plugged,
                                "percent": current_battery
                            }, hook_name)
                        
                        last_battery = current_battery
                        last_power_plugged = current_power_plugged
                
                except Exception as e:
                    print(f"Power monitoring error: {e}")
                
                time.sleep(config.get("interval", 10))
        
        thread = threading.Thread(target=monitor_power, daemon=True)
        thread.start()
    
    def get_recent_events(self, hook_type: HookType = None, limit: int = 100) -> List[SystemEvent]:
        """Get recent system events"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if hook_type:
            cursor.execute('''
                SELECT event_id, hook_type, timestamp, data, source, processed
                FROM system_events
                WHERE hook_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (hook_type.value, limit))
        else:
            cursor.execute('''
                SELECT event_id, hook_type, timestamp, data, source, processed
                FROM system_events
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
        
        events = []
        for row in cursor.fetchall():
            events.append(SystemEvent(
                event_id=row[0],
                hook_type=HookType(row[1]),
                timestamp=datetime.fromisoformat(row[2]),
                data=json.loads(row[3]),
                source=row[4],
                processed=bool(row[5])
            ))
        
        conn.close()
        return events

class HardwareMonitor:
    """Advanced hardware monitoring and control"""
    
    def __init__(self):
        self.monitoring = False
        self.callbacks = {}
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        info = {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "cpu": {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "usage_percent": psutil.cpu_percent(interval=1),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
                "percentage": psutil.virtual_memory().percent
            },
            "disk": [],
            "network": {
                "interfaces": {},
                "stats": psutil.net_io_counters()._asdict()
            }
        }
        
        # Disk information
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                info["disk"].append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percentage": (usage.used / usage.total) * 100
                })
            except PermissionError:
                continue
        
        # Network interfaces
        for interface, addrs in psutil.net_if_addrs().items():
            info["network"]["interfaces"][interface] = [addr._asdict() for addr in addrs]
        
        return info
    
    def get_running_processes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get information about running processes"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        return processes[:limit]
    
    def monitor_performance(self, callback: Callable[[Dict[str, Any]], None], interval: int = 5):
        """Start performance monitoring"""
        def monitor():
            while self.monitoring:
                stats = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory": psutil.virtual_memory()._asdict(),
                    "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else None,
                    "network_io": psutil.net_io_counters()._asdict()
                }
                
                callback(stats)
                time.sleep(interval)
        
        self.monitoring = True
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring = False

class WindowsRegistryManager:
    """Windows Registry management"""
    
    def __init__(self):
        if platform.system() != "Windows":
            raise RuntimeError("Registry manager only available on Windows")
    
    def read_value(self, hkey: str, subkey: str, value_name: str):
        """Read a value from Windows registry"""
        try:
            hkey_map = {
                "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
                "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
                "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
                "HKEY_USERS": winreg.HKEY_USERS,
                "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG
            }
            
            with winreg.OpenKey(hkey_map[hkey], subkey) as key:
                value, regtype = winreg.QueryValueEx(key, value_name)
                return value
        except Exception as e:
            raise ValueError(f"Failed to read registry value: {e}")
    
    def write_value(self, hkey: str, subkey: str, value_name: str, value: Any, value_type: str = "REG_SZ"):
        """Write a value to Windows registry"""
        try:
            hkey_map = {
                "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
                "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
                "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
                "HKEY_USERS": winreg.HKEY_USERS,
                "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG
            }
            
            type_map = {
                "REG_SZ": winreg.REG_SZ,
                "REG_DWORD": winreg.REG_DWORD,
                "REG_BINARY": winreg.REG_BINARY,
                "REG_MULTI_SZ": winreg.REG_MULTI_SZ
            }
            
            with winreg.OpenKey(hkey_map[hkey], subkey, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, value_name, 0, type_map[value_type], value)
        except Exception as e:
            raise ValueError(f"Failed to write registry value: {e}")

class AdvancedIntegrationManager:
    """Main manager for advanced system integration"""
    
    def __init__(self, db_path: str = "advanced_integration.db"):
        self.db_path = db_path
        self.platform_adapter = PlatformAdapter()
        self.hook_manager = SystemHookManager(f"{db_path}_hooks.db")
        self.hardware_monitor = HardwareMonitor()
        self.capabilities = {}
        
        self.init_database()
        self.initialize_capabilities()
    
    def init_database(self):
        """Initialize integration database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS integration_status (
                capability TEXT PRIMARY KEY,
                enabled INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                config TEXT,
                error_count INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cpu_percent REAL,
                memory_percent REAL,
                disk_usage TEXT,
                network_stats TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def initialize_capabilities(self):
        """Initialize available system integration capabilities"""
        supported = self.platform_adapter.get_supported_capabilities()
        
        for capability in supported:
            self.capabilities[capability] = {
                "enabled": False,
                "instance": None,
                "last_error": None
            }
    
    def enable_capability(self, capability_name: str, config: Dict[str, Any] = None) -> bool:
        """Enable a system integration capability"""
        if capability_name not in self.capabilities:
            return False
        
        if not self.platform_adapter.is_capability_supported(capability_name):
            return False
        
        try:
            # Check admin requirements
            if self.platform_adapter.requires_admin(capability_name) and not self._is_admin():
                raise PermissionError(f"Administrator privileges required for {capability_name}")
            
            # Initialize capability
            capability_def = self.platform_adapter.capabilities[capability_name]
            if capability_def.implementation:
                instance = capability_def.implementation()
                self.capabilities[capability_name]["instance"] = instance
                self.capabilities[capability_name]["enabled"] = True
                
                # Update database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO integration_status 
                    (capability, enabled, last_used, config)
                    VALUES (?, 1, CURRENT_TIMESTAMP, ?)
                ''', (capability_name, json.dumps(config or {})))
                conn.commit()
                conn.close()
                
                return True
            
        except Exception as e:
            self.capabilities[capability_name]["last_error"] = str(e)
            return False
        
        return False
    
    def disable_capability(self, capability_name: str):
        """Disable a system integration capability"""
        if capability_name in self.capabilities:
            self.capabilities[capability_name]["enabled"] = False
            self.capabilities[capability_name]["instance"] = None
            
            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE integration_status SET enabled = 0 WHERE capability = ?
            ''', (capability_name,))
            conn.commit()
            conn.close()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "platform": self.platform_adapter.system_type.value,
            "capabilities": {},
            "hardware": self.hardware_monitor.get_system_info(),
            "processes": self.hardware_monitor.get_running_processes(20),
            "hooks": {
                "active": len([h for h in self.hook_manager.hooks.values() if h["active"]]),
                "total": len(self.hook_manager.hooks)
            },
            "recent_events": len(self.hook_manager.get_recent_events(limit=10))
        }
        
        for name, capability in self.capabilities.items():
            status["capabilities"][name] = {
                "enabled": capability["enabled"],
                "supported": self.platform_adapter.is_capability_supported(name),
                "requires_admin": self.platform_adapter.requires_admin(name),
                "last_error": capability["last_error"]
            }
        
        return status
    
    def setup_system_hooks(self):
        """Setup basic system monitoring hooks"""
        # File system monitoring
        self.hook_manager.register_hook("fs_monitor", HookType.FILE_SYSTEM, {
            "paths": [os.path.expanduser("~"), "C:\\Windows\\System32" if platform.system() == "Windows" else "/var/log"],
            "interval": 2
        })
        
        # Process monitoring
        self.hook_manager.register_hook("process_monitor", HookType.PROCESS, {
            "interval": 3
        })
        
        # Network monitoring
        self.hook_manager.register_hook("network_monitor", HookType.NETWORK, {
            "interval": 5
        })
        
        # Power monitoring (if battery present)
        if psutil.sensors_battery():
            self.hook_manager.register_hook("power_monitor", HookType.POWER, {
                "interval": 30
            })
    
    def start_monitoring(self):
        """Start system monitoring"""
        for hook_name in self.hook_manager.hooks:
            try:
                self.hook_manager.start_hook(hook_name)
            except Exception as e:
                print(f"Failed to start hook {hook_name}: {e}")
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        for hook_name in self.hook_manager.hooks:
            self.hook_manager.stop_hook(hook_name)
        
        self.hardware_monitor.stop_monitoring()
    
    def _is_admin(self) -> bool:
        """Check if running with administrator privileges"""
        try:
            if platform.system() == "Windows":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin()
            else:
                return os.geteuid() == 0
        except Exception:
            return False
    
    def get_integration_insights(self) -> Dict[str, Any]:
        """Generate insights from system integration"""
        insights = {
            "system_health": "good",
            "performance_trends": {},
            "security_recommendations": [],
            "optimization_suggestions": []
        }
        
        # Analyze recent events
        recent_events = self.hook_manager.get_recent_events(limit=100)
        
        # Count event types
        event_counts = {}
        for event in recent_events:
            event_type = event.hook_type.value
            if event_type not in event_counts:
                event_counts[event_type] = 0
            event_counts[event_type] += 1
        
        insights["event_summary"] = event_counts
        
        # System performance analysis
        hardware_info = self.hardware_monitor.get_system_info()
        cpu_usage = hardware_info["cpu"]["usage_percent"]
        memory_usage = hardware_info["memory"]["percentage"]
        
        if cpu_usage > 80:
            insights["optimization_suggestions"].append("High CPU usage detected - consider closing unnecessary applications")
        
        if memory_usage > 85:
            insights["optimization_suggestions"].append("High memory usage detected - system may benefit from additional RAM")
        
        # Security recommendations
        if len([p for p in self.hardware_monitor.get_running_processes() if "unknown" in p.get("username", "")]) > 5:
            insights["security_recommendations"].append("Multiple processes running with unknown users - review system security")
        
        return insights

def main():
    """Example usage of Advanced System Integration"""
    integration_manager = AdvancedIntegrationManager()
    
    # Get system status
    status = integration_manager.get_system_status()
    print("System Status:", json.dumps(status, indent=2))
    
    # Setup and start monitoring
    integration_manager.setup_system_hooks()
    integration_manager.start_monitoring()
    
    print("System integration started. Monitoring system events...")
    
    # Monitor for a short time
    time.sleep(10)
    
    # Get insights
    insights = integration_manager.get_integration_insights()
    print("Integration Insights:", json.dumps(insights, indent=2))
    
    # Stop monitoring
    integration_manager.stop_monitoring()

if __name__ == "__main__":
    main()