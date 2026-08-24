# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

# System Monitoring and Management Module
"""
System monitoring, process management, and PC maintenance functions
for the Pulsar AI Assistant.
"""

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False
    logger.warning("WARNING: psutil not found. System monitoring features will be disabled.")

import platform
import tempfile
import shutil
import os
import time

def get_system_status() -> str:
    """
    Gets comprehensive system status including CPU, RAM, disk, and network info.
    """
    if not PSUTIL_AVAILABLE or psutil is None:
        return "❌ System monitoring requires 'psutil' package."

    print("--- 'Hands' (get_system_status) activated ---")
    try:
        # CPU Information
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        
        # Memory Information
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk Information
        disk_usage = psutil.disk_usage('/')
        
        # Network Information
        network_stats = psutil.net_io_counters()
        
        # Battery Information (if available)
        battery_info = ""
        try:
            battery = psutil.sensors_battery()
            if battery:
                battery_info = f"\\n🔋 Battery: {battery.percent:.1f}% ({'Charging' if battery.power_plugged else 'Not Charging'})"
        except:
            pass
        
        status_report = f"""📊 SYSTEM STATUS REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🖥️  CPU: {cpu_percent}% usage | {cpu_count} cores | {cpu_freq.current:.0f} MHz
🧠 RAM: {memory.percent}% used ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)
💾 Disk: {disk_usage.percent}% used ({disk_usage.used // (1024**3):.1f}GB / {disk_usage.total // (1024**3):.1f}GB)
🌐 Network: ↑{network_stats.bytes_sent // (1024**2):.1f}MB sent | ↓{network_stats.bytes_recv // (1024**2):.1f}MB received{battery_info}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return status_report
        
    except Exception as e:
        return f"Error getting system status: {e}"

def get_running_processes(limit: int = 10) -> str:
    """
    Gets information about currently running processes.
    :param limit: Number of top processes to show (by CPU usage)
    """
    print(f"--- 'Hands' (get_running_processes) activated. Limit: {limit} ---")
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                proc_info = proc.info
                processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by CPU usage
        processes = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:limit]
        
        process_report = "📋 TOP RUNNING PROCESSES\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
        for proc in processes:
            name = proc['name'][:25].ljust(25)
            cpu = f"{proc['cpu_percent'] or 0:.1f}%".rjust(6)
            mem = f"{proc['memory_percent'] or 0:.1f}%".rjust(6)
            pid = str(proc['pid']).rjust(6)
            process_report += f"🔹 {name} | CPU: {cpu} | RAM: {mem} | PID: {pid}\\n"
        
        return process_report
        
    except Exception as e:
        return f"Error getting running processes: {e}"

def cleanup_temp_files() -> str:
    """
    Cleans up temporary files and system cache.
    """
    print("--- 'Hands' (cleanup_temp_files) activated ---")
    try:
        temp_dir = tempfile.gettempdir()
        cleaned_size = 0
        cleaned_count = 0
        
        # Clean temp files older than 1 day
        current_time = time.time()
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # Check if file is older than 1 day
                    if current_time - os.path.getmtime(file_path) > 86400:  # 24 hours
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        cleaned_size += file_size
                        cleaned_count += 1
                except (OSError, PermissionError):
                    continue  # Skip files we can't access
        
        cleaned_size_mb = cleaned_size / (1024 * 1024)
        return f"🧹 Cleanup complete! Removed {cleaned_count} temporary files, freed {cleaned_size_mb:.1f} MB of disk space."
        
    except Exception as e:
        return f"Error during cleanup: {e}"

def get_network_info() -> str:
    """
    Gets detailed network information including active connections.
    """
    print("--- 'Hands' (get_network_info) activated ---")
    try:
        # Network interfaces
        interfaces = psutil.net_if_addrs()
        network_stats = psutil.net_io_counters(pernic=True)
        
        network_report = "🌐 NETWORK INFORMATION\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
        
        for interface_name, interface_addrs in interfaces.items():
            if interface_name in network_stats:
                stats = network_stats[interface_name]
                network_report += f"📡 {interface_name}:\\n"
                
                for addr in interface_addrs:
                    if addr.family.name == 'AF_INET':  # IPv4
                        network_report += f"   📍 IPv4: {addr.address}\\n"
                
                network_report += f"   📊 Sent: {stats.bytes_sent // (1024**2):.1f}MB | Received: {stats.bytes_recv // (1024**2):.1f}MB\\n\\n"
        
        return network_report
        
    except Exception as e:
        return f"Error getting network info: {e}"

def monitor_system_alerts() -> str:
    """
    Monitors system for potential issues and alerts.
    """
    print("--- 'Hands' (monitor_system_alerts) activated ---")
    try:
        alerts = []
        
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 80:
            alerts.append(f"⚠️ HIGH CPU USAGE: {cpu_percent}%")
        
        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 80:
            alerts.append(f"⚠️ HIGH MEMORY USAGE: {memory.percent}%")
        
        # Check disk usage
        disk_usage = psutil.disk_usage('/')
        if disk_usage.percent > 85:
            alerts.append(f"⚠️ LOW DISK SPACE: {disk_usage.percent}% used")
        
        # Check battery (if available)
        try:
            battery = psutil.sensors_battery()
            if battery and not battery.power_plugged and battery.percent < 20:
                alerts.append(f"🔋 LOW BATTERY: {battery.percent}%")
        except:
            pass
        
        if alerts:
            return "🚨 SYSTEM ALERTS:\\n" + "\\n".join(alerts)
        else:
            return "✅ All systems running normally. No alerts detected."
            
    except Exception as e:
        return f"Error monitoring system alerts: {e}"

def get_system_info() -> str:
    """
    Gets detailed system information including OS, hardware, and Python environment.
    """
    print("--- 'Hands' (get_system_info) activated ---")
    try:
        uname = platform.uname()
        boot_time = psutil.boot_time()
        boot_datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot_time))
        
        system_info = f"""💻 SYSTEM INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🖥️  System: {uname.system} {uname.release}
🏷️  Node: {uname.node}
⚙️  Machine: {uname.machine}
🔧 Processor: {uname.processor or platform.processor()}
🐍 Python: {platform.python_version()}
🚀 Boot Time: {boot_datetime}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return system_info
        
    except Exception as e:
        return f"Error getting system info: {e}"

def get_battery_status() -> str:
    """
    Gets detailed battery status if available.
    """
    print("--- 'Hands' (get_battery_status) activated ---")
    try:
        battery = psutil.sensors_battery()
        if not battery:
            return "🔌 This system doesn't have a battery or battery info is not available."
        
        percent = battery.percent
        plugged = battery.power_plugged
        seconds_left = battery.secsleft
        
        status = f"🔋 BATTERY STATUS\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
        status += f"⚡ Charge Level: {percent}%\\n"
        status += f"🔌 Power Adapter: {'Connected' if plugged else 'Disconnected'}\\n"
        
        if seconds_left != psutil.POWER_TIME_UNLIMITED and not plugged:
            hours, remainder = divmod(seconds_left, 3600)
            minutes = remainder // 60
            status += f"⏱️  Time Remaining: {int(hours)}h {int(minutes)}m\\n"
        
        # Status indicator
        if percent > 80:
            status += "Status: Excellent 🟢"
        elif percent > 50:
            status += "Status: Good 🟡"
        elif percent > 20:
            status += "Status: Low 🟠"
        else:
            status += "Status: Critical 🔴"
        
        return status
        
    except Exception as e:
        return f"Error getting battery status: {e}"