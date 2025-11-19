"""
Live Taskbar Analysis for YourDaddy Assistant
Real-time detection and analysis of taskbar applications and system state
"""

import sys
import os
sys.path.append('modules')

def analyze_current_taskbar():
    """Analyze what's currently visible on the taskbar"""
    try:
        import psutil
        import win32gui
        import win32process
        from datetime import datetime
        
        print(f"🔍 LIVE TASKBAR ANALYSIS - {datetime.now().strftime('%I:%M:%S %p')}")
        print("=" * 60)
        
        # Get visible windows (taskbar applications)
        windows = []
        def enum_window_callback(hwnd, windows_list):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if window_title and len(window_title) > 1:
                    try:
                        _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                        try:
                            process = psutil.Process(process_id)
                            process_name = process.name()
                            memory_mb = process.memory_info().rss / 1024 / 1024
                        except:
                            process_name = "Unknown"
                            memory_mb = 0
                        
                        windows_list.append({
                            'title': window_title,
                            'process': process_name,
                            'pid': process_id,
                            'memory_mb': round(memory_mb, 1)
                        })
                    except:
                        pass
            return True
        
        win32gui.EnumWindows(enum_window_callback, windows)
        
        # Filter for main applications (likely on taskbar)
        taskbar_apps = []
        for window in windows:
            title = window['title']
            process = window['process']
            
            # Filter system windows and focus on user applications
            if (not any(skip in title.lower() for skip in ['program manager', 'desktop window', 'task switching']) and
                process.lower() not in ['dwm.exe', 'winlogon.exe', 'csrss.exe', 'textinputhost.exe'] and
                not title.startswith('Microsoft Text')):
                taskbar_apps.append(window)
        
        print("📱 APPLICATIONS ON TASKBAR:")
        print("-" * 40)
        
        if taskbar_apps:
            for i, app in enumerate(taskbar_apps, 1):
                title_short = app['title'][:45] + "..." if len(app['title']) > 45 else app['title']
                print(f"{i:2d}. {title_short}")
                print(f"    Process: {app['process']} (PID: {app['pid']}) - {app['memory_mb']} MB")
                print()
        else:
            print("    No user applications detected")
        
        # System summary
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        print("💻 SYSTEM STATUS:")
        print("-" * 20)
        print(f"Memory: {memory.percent:.1f}% used ({memory.used // (1024**3):.1f}GB used of {memory.total // (1024**3):.1f}GB)")
        print(f"CPU: {cpu_percent:.1f}% usage")
        print(f"Active Applications: {len(taskbar_apps)}")
        print(f"Total Processes: {len(list(psutil.process_iter()))}")
        
        return {
            'taskbar_apps': taskbar_apps,
            'system_status': {
                'memory_percent': memory.percent,
                'cpu_percent': cpu_percent,
                'active_apps': len(taskbar_apps)
            }
        }
        
    except Exception as e:
        print(f"Error analyzing taskbar: {e}")
        return None

def check_specific_app(app_name):
    """Check if a specific application is running"""
    try:
        import psutil
        
        app_name_lower = app_name.lower()
        found_apps = []
        
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                proc_info = proc.info
                if (app_name_lower in proc_info['name'].lower() or 
                    (proc_info['exe'] and app_name_lower in proc_info['exe'].lower())):
                    found_apps.append({
                        'name': proc_info['name'],
                        'pid': proc_info['pid'],
                        'exe': proc_info['exe'] or 'Unknown'
                    })
            except:
                continue
        
        if found_apps:
            print(f"✅ Found '{app_name}' running:")
            for app in found_apps:
                print(f"   - {app['name']} (PID: {app['pid']})")
            return True
        else:
            print(f"❌ '{app_name}' is not currently running")
            return False
            
    except Exception as e:
        print(f"Error checking for app '{app_name}': {e}")
        return False

if __name__ == "__main__":
    # Live analysis
    result = analyze_current_taskbar()
    
    # Test specific app detection
    print("\n" + "="*60)
    print("🔍 TESTING SPECIFIC APP DETECTION:")
    print("-" * 30)
    
    test_apps = ['chrome', 'firefox', 'notepad', 'code', 'brave']
    for app in test_apps:
        check_specific_app(app)