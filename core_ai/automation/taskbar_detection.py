# Setup centralized logging
try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__, log_category="app")
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Taskbar and Running Applications Detection Module
"""
This module provides capabilities to detect and analyze the Windows taskbar,
including running applications, taskbar icons, and system tray information.
"""

import os
import psutil
import time
from typing import Dict, List, Tuple, Optional, Any
from PIL import Image, ImageGrab
import json
from datetime import datetime

try:
    import win32gui
    import win32con
    import win32process
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logger.warning("Warning: win32gui not available. Some taskbar detection features will be limited.")

import ctypes
from ctypes import wintypes

try:
    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi
    DWMWA_CLOAKED = 14
    GW_OWNER = 4
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    
    class RECT(ctypes.Structure):
        _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                    ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
                    
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    CTYPES_DWM_AVAILABLE = True
except Exception as e:
    CTYPES_DWM_AVAILABLE = False
    logger.debug(f"ctypes DWM setup skipped: {e}")

# Import multimodal capabilities for visual analysis
try:
    from ai_assistant.vision.multimodal import MultiModalAI
    MULTIMODAL_AVAILABLE = True
except ImportError:
    MULTIMODAL_AVAILABLE = False
    logger.warning("Warning: Multimodal AI not available for visual taskbar analysis.")

class TaskbarDetector:
    """Detects and analyzes Windows taskbar and running applications."""
    
    def __init__(self):
        self.multimodal = None
        if MULTIMODAL_AVAILABLE:
            try:
                self.multimodal = MultiModalAI()
            except Exception as e:
                logger.warning(f"Warning: Could not initialize MultiModalAI: {e}")
    
    def get_running_applications(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get detailed information about all running applications.
        
        Returns:
            Dictionary with application information including PIDs, names, and window titles
        """
        logger.info("🔍 Detecting running applications...")
        
        applications = {
            "processes": [],
            "windows": [],
            "summary": {}
        }
        
        # Get process information
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent', 'create_time']):
            try:
                proc_info = proc.info
                proc_info['memory_mb'] = proc_info['memory_info'].rss / 1024 / 1024
                proc_info['running_time'] = time.time() - proc_info['create_time']
                del proc_info['memory_info']  # Remove the original object
                applications["processes"].append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Get window information if win32gui is available
        if WIN32_AVAILABLE:
            applications["windows"] = self._get_window_information()
        
        # Create summary
        applications["summary"] = {
            "total_processes": len(applications["processes"]),
            "total_windows": len(applications["windows"]),
            "timestamp": datetime.now().isoformat()
        }
        
        return applications
    
    def _get_window_information(self) -> List[Dict[str, Any]]:
        """
        Get information about all genuine desktop and taskbar application windows,
        strictly filtering out background daemons, system tray processes, cloaked UWP apps,
        tooltips, and system shell helpers.
        """
        windows = []
        if not CTYPES_DWM_AVAILABLE:
            return windows

        def process_hwnd(hwnd):
            if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
                return
                
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return
                
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.strip()
            if not title:
                return
                
            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls_buf, 256)
            cls_name = cls_buf.value
            if cls_name in ('Progman', 'WorkerW', 'Shell_TrayWnd', 'Shell_SecondaryTrayWnd',
                            'ApplicationFrameInputSinkWindow', 'Windows.UI.Core.CoreWindow', 
                            'DV2ControlHost', 'TopLevelWindowForOverflowXamlIsland'):
                return

            # Check cloaked
            cloaked = wintypes.DWORD(0)
            res = dwmapi.DwmGetWindowAttribute(hwnd, ctypes.c_uint(DWMWA_CLOAKED), ctypes.byref(cloaked), ctypes.sizeof(cloaked))
            if res == 0 and cloaked.value != 0:
                return
                
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if (ex_style & WS_EX_TOOLWINDOW) and not (ex_style & WS_EX_APPWINDOW):
                return
                
            owner = user32.GetWindow(hwnd, GW_OWNER)
            if owner != 0 and not (ex_style & WS_EX_APPWINDOW):
                return
                
            rect = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            is_min = user32.IsIconic(hwnd)
            if not is_min and (w <= 2 or h <= 2):
                return
                
            title_lower = title.lower()
            if title_lower in ('program manager', 'default ime', 'msctfime ui', 'windows input experience', 
                               'popuphost', 'nvidia geforce overlay', 'settings', 'battery meter', 'network flyout'):
                return
                
            pid = wintypes.DWORD(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            try:
                pname = psutil.Process(pid.value).name()
            except:
                pname = 'unknown'
                
            friendly = self._FRIENDLY_APP_NAMES.get(pname.lower())
            if not friendly:
                stem = pname[:-4] if pname.lower().endswith(".exe") else pname
                friendly = stem.replace("_", " ").title() if stem and stem.lower() != "unknown" else title
                
            windows.append({
                'hwnd': hwnd,
                'app': friendly,
                'process_name': pname,
                'title': title,
                'pid': pid.value,
                'position': {
                    'left': rect.left,
                    'top': rect.top,
                    'right': rect.right,
                    'bottom': rect.bottom,
                    'width': w,
                    'height': h
                },
                'is_minimized': bool(is_min),
                'is_maximized': bool(user32.IsZoomed(hwnd) if hasattr(user32, 'IsZoomed') else False),
            })

        def callback(hwnd, lparam):
            try:
                process_hwnd(hwnd)
            except Exception:
                pass
            return True

        cb = WNDENUMPROC(callback)
        hdesk = None
        try:
            hdesk = user32.OpenDesktopW('Default', 0, False, 0x0100)
            if hdesk:
                user32.EnumDesktopWindows(hdesk, cb, 0)
            else:
                user32.EnumWindows(cb, 0)
        except Exception as e:
            logger.debug(f"Enum windows desktop error: {e}")
            try:
                user32.EnumWindows(cb, 0)
            except Exception:
                pass
        finally:
            if hdesk:
                try:
                    user32.CloseDesktop(hdesk)
                except Exception:
                    pass

        return windows

    _IGNORED_WINDOW_TITLES = frozenset({
        "program manager",
        "default ime",
        "msctfime ui",
        "windows input experience",
        "popuphost",
        "desktopwindowxamlssource",
        "nvidia geforce overlay",
        "battery meter",
        "network flyout",
        "settings",  # only when 0x0 or empty host, handled below
    })
    _IGNORED_SHELL_CLASSES = frozenset({
        "Progman",
        "WorkerW",
        "Shell_TrayWnd",
        "Shell_SecondaryTrayWnd",
        "DV2ControlHost",
        "Windows.UI.Core.CoreWindow",
        "ApplicationFrameInputSinkWindow",
    })
    _IGNORED_PROCESSES = frozenset({
        "textinputhost.exe",
        "shellexperiencehost.exe",
        "searchhost.exe",
        "startmenuexperiencehost.exe",
        "lockapp.exe",
        "idle",
        "system",
    })
    _FRIENDLY_APP_NAMES = {
        "chrome.exe": "Google Chrome",
        "msedge.exe": "Microsoft Edge",
        "brave.exe": "Brave",
        "firefox.exe": "Firefox",
        "code.exe": "VS Code",
        "whatsapp.exe": "WhatsApp",
        "whatsapp.root.exe": "WhatsApp",
        "spotify.exe": "Spotify",
        "explorer.exe": "File Explorer",
        "windowsterminal.exe": "Windows Terminal",
        "powershell.exe": "PowerShell",
        "pwsh.exe": "PowerShell",
        "cmd.exe": "Command Prompt",
        "notepad.exe": "Notepad",
        "applicationframehost.exe": "Windows App",
        "antigravity.exe": "Antigravity",
        "electron.exe": "Desktop App",
        "vlc.exe": "VLC",
        "discord.exe": "Discord",
        "telegram.exe": "Telegram",
    }

    def get_taskbar_open_apps(self) -> Dict[str, Any]:
        """
        Enumerate currently open desktop/taskbar GUI application windows cleanly,
        excluding hidden system/IME/shell helper windows and kernel background processes.
        """
        windows = self._get_window_information() if WIN32_AVAILABLE else []
        filtered_windows: List[Dict[str, Any]] = []
        grouped: Dict[str, Dict[str, Any]] = {}

        for win in windows:
            title = str(win.get("title") or "").strip()
            title_lower = title.lower()
            class_name = str(win.get("class_name") or "").strip()
            proc_name = str(win.get("process_name") or "").strip()
            proc_lower = proc_name.lower()
            pos = win.get("position") or {}
            width = int(pos.get("width", 0) or 0)
            height = int(pos.get("height", 0) or 0)
            is_min = bool(win.get("is_minimized", False))

            if not title or class_name in self._IGNORED_SHELL_CLASSES:
                continue
            if proc_lower in self._IGNORED_PROCESSES:
                continue
            if title_lower in {
                "program manager", "default ime", "msctfime ui",
                "windows input experience", "popuphost", "nvidia geforce overlay",
            }:
                continue
            if title_lower == "settings" and proc_lower in ("applicationframehost.exe", "systemsettings.exe") and width <= 0 and height <= 0:
                continue
            if not is_min and (width <= 2 or height <= 2):
                continue

            friendly = self._FRIENDLY_APP_NAMES.get(proc_lower)
            if not friendly:
                stem = proc_name[:-4] if proc_lower.endswith(".exe") else proc_name
                friendly = stem.replace("_", " ").title() if stem and stem.lower() != "unknown" else title

            entry = {
                "app": friendly,
                "process_name": proc_name,
                "title": title,
                "is_minimized": is_min,
                "is_maximized": bool(win.get("is_maximized", False)),
                "pid": win.get("pid", 0),
            }
            filtered_windows.append(entry)

            key = friendly.lower()
            if key not in grouped:
                grouped[key] = {
                    "app": friendly,
                    "process_name": proc_name,
                    "windows": [],
                    "minimized_count": 0,
                    "visible_count": 0,
                }
            grouped[key]["windows"].append(entry)
            if is_min:
                grouped[key]["minimized_count"] += 1
            else:
                grouped[key]["visible_count"] += 1

        apps_list = list(grouped.values())
        return {
            "apps": apps_list,
            "windows": filtered_windows,
            "app_count": len(apps_list),
            "window_count": len(filtered_windows),
        }

    def format_taskbar_open_apps(self) -> str:
        """Return a clean human-readable multi-line list of open taskbar GUI apps."""
        info = self.get_taskbar_open_apps()
        apps = info.get("apps") or []
        if not apps:
            return "Abhi taskbar par koi visible GUI application window open nahi dikh rahi."

        lines = [f"Taskbar par abhi {len(apps)} app(s) open hain:"]
        for item in apps:
            app_name = item["app"]
            wins = item["windows"]
            sample_title = str(wins[0].get("title") or "").strip()
            if len(sample_title) > 70:
                sample_title = sample_title[:67] + "..."
            state = "minimized" if item["visible_count"] == 0 else "active/visible"
            extra = f" ({len(wins)} windows)" if len(wins) > 1 else ""
            lines.append(f"- {app_name}{extra} [{state}]: {sample_title}")
        return "\n".join(lines)
    
    def get_taskbar_apps_visual(self) -> Dict[str, Any]:
        """
        Use computer vision to analyze the taskbar and identify apps.
        
        Returns:
            Visual analysis of the taskbar including app icons and running applications
        """
        if not self.multimodal:
            return {"error": "Visual analysis not available - Multimodal AI not initialized"}
        
        print("👁️ Analyzing taskbar visually...")
        
        try:
            # Capture the screen
            screenshot = self.multimodal.capture_screen()
            if not screenshot:
                return {"error": "Failed to capture screenshot"}
            
            # Analyze the taskbar area specifically
            taskbar_prompt = """
            Analyze this Windows desktop screenshot and identify:
            
            1. TASKBAR LOCATION: Where is the taskbar located (bottom, top, left, right)?
            
            2. TASKBAR APPS: List all application icons visible in the taskbar, including:
               - App names (if identifiable from icons)
               - Whether apps appear to be running (highlighted/active)
               - Order from left to right
            
            3. SYSTEM TRAY: Describe what's visible in the system tray area (right side of taskbar):
               - System icons (clock, notifications, etc.)
               - Running background applications
               - Network/battery/volume indicators
            
            4. OPEN WINDOWS: Describe any open application windows visible on the desktop
            
            5. START MENU: Is the Start menu open or closed?
            
            Format your response clearly with each section labeled.
            """
            
            analysis = self.multimodal.analyze_image(screenshot, taskbar_prompt)
            
            return {
                "visual_analysis": analysis.get("analysis", ""),
                "timestamp": analysis.get("timestamp"),
                "method": "computer_vision",
                "screenshot_captured": True
            }
            
        except Exception as e:
            return {"error": f"Visual analysis failed: {str(e)}"}
    
    def get_taskbar_region_analysis(self) -> Dict[str, Any]:
        """
        Capture and analyze just the taskbar region for more focused results.
        
        Returns:
            Focused analysis of the taskbar area only
        """
        if not self.multimodal:
            return {"error": "Visual analysis not available"}
        
        logger.info("🔍 Analyzing taskbar region specifically...")
        
        try:
            # Get screen dimensions
            screen = ImageGrab.grab()
            screen_width, screen_height = screen.size
            
            # Assume taskbar is at bottom (most common) - adjust if needed
            taskbar_height = 48  # Standard Windows taskbar height
            taskbar_region = (0, screen_height - taskbar_height, screen_width, screen_height)
            
            # Capture taskbar region
            taskbar_screenshot = self.multimodal.capture_screen(taskbar_region)
            if not taskbar_screenshot:
                return {"error": "Failed to capture taskbar region"}
            
            taskbar_prompt = """
            This is a cropped image of just the Windows taskbar. Please identify:
            
            1. All application icons from left to right
            2. Which apps appear to be running (active/highlighted)
            3. System tray contents on the right side
            4. Start button state
            5. Any other taskbar elements visible
            
            Be specific about what you can see and the order of elements.
            """
            
            analysis = self.multimodal.analyze_image(taskbar_screenshot, taskbar_prompt)
            
            return {
                "taskbar_analysis": analysis.get("analysis", ""),
                "region_captured": taskbar_region,
                "timestamp": analysis.get("timestamp"),
                "method": "focused_region_analysis"
            }
            
        except Exception as e:
            return {"error": f"Taskbar region analysis failed: {str(e)}"}
    
    def get_complete_desktop_analysis(self) -> Dict[str, Any]:
        """
        Provide a complete analysis combining process detection and visual analysis.
        
        Returns:
            Comprehensive desktop and taskbar analysis
        """
        print("🖥️ Performing complete desktop analysis...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "process_analysis": {},
            "visual_analysis": {},
            "taskbar_analysis": {},
            "summary": {}
        }
        
        # Get running applications via process detection
        try:
            results["process_analysis"] = self.get_running_applications()
        except Exception as e:
            results["process_analysis"] = {"error": str(e)}
        
        # Get visual analysis of entire desktop
        try:
            results["visual_analysis"] = self.get_taskbar_apps_visual()
        except Exception as e:
            results["visual_analysis"] = {"error": str(e)}
        
        # Get focused taskbar analysis
        try:
            results["taskbar_analysis"] = self.get_taskbar_region_analysis()
        except Exception as e:
            results["taskbar_analysis"] = {"error": str(e)}
        
        # Create summary
        process_count = len(results["process_analysis"].get("processes", []))
        window_count = len(results["process_analysis"].get("windows", []))
        
        results["summary"] = {
            "total_running_processes": process_count,
            "total_visible_windows": window_count,
            "visual_analysis_success": "visual_analysis" in results["visual_analysis"],
            "taskbar_analysis_success": "taskbar_analysis" in results["taskbar_analysis"],
            "detection_methods": ["process_enumeration"]
        }
        
        if WIN32_AVAILABLE:
            results["summary"]["detection_methods"].append("win32_windows")
        
        if self.multimodal:
            results["summary"]["detection_methods"].append("computer_vision")
        
        return results
    
    def find_specific_app_in_taskbar(self, app_name: str, expected_title_keyword: str = None) -> Dict[str, Any]:
        """
        Look for a specific application in the taskbar and optionally check its window title.
        Strictly distinguishes between genuine taskbar windows vs background daemons (e.g. Ollama, Tray WhatsApp).
        """
        logger.info(f"🔍 Looking for '{app_name}' in taskbar...")
        clean_target = app_name.lower().strip()
        
        # 1. Search genuine visible/minimized taskbar windows first
        app_found_in_windows = False
        title_match_found = False
        matching_windows = []
        
        windows = self._get_window_information()
        for win in windows:
            title_lower = win.get("title", "").lower()
            process_lower = win.get("process_name", "").lower()
            friendly_lower = win.get("app", "").lower()
            
            # Check if this window belongs to our target app
            if (clean_target in process_lower or 
                clean_target in title_lower or 
                clean_target in friendly_lower or
                (clean_target in ("vscode", "vs code", "code") and process_lower == "code.exe")):
                app_found_in_windows = True
                matching_windows.append(win)
                
                if expected_title_keyword and expected_title_keyword.lower() in title_lower:
                    title_match_found = True
                    
        # 2. Check running background processes (to explain if it's running but hidden/daemon)
        app_found_in_processes = False
        matching_processes = []
        if psutil:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    pname = (proc.info.get('name') or '').lower()
                    if clean_target in pname or (clean_target in ("vscode", "vs code", "code") and pname == "code.exe"):
                        matching_processes.append(proc.info)
                        app_found_in_processes = True
                except Exception:
                    continue

        # 3. True taskbar status: is it actually open in the taskbar?
        is_in_taskbar = app_found_in_windows
        is_successful = title_match_found if expected_title_keyword else is_in_taskbar
        
        if is_in_taskbar:
            sample_title = matching_windows[0].get("title", "")
            state = "minimized" if matching_windows[0].get("is_minimized") else "open"
            status_message = f"'{app_name}' is currently {state} in your taskbar: \"{sample_title}\""
        elif app_found_in_processes:
            status_message = f"'{app_name}' is running as a background service/system tray process, but is NOT open in your taskbar."
        else:
            status_message = f"'{app_name}' is not running or open in your taskbar."
            
        return {
            "app_name": app_name,
            "found_in_taskbar": is_in_taskbar,
            "found_in_processes": app_found_in_processes,
            "app_found_in_windows": app_found_in_windows,
            "title_match_found": title_match_found,
            "is_successful": is_successful,
            "status_message": status_message,
            "matching_processes": matching_processes,
            "matching_windows": matching_windows,
            "timestamp": datetime.now().isoformat()
        }

# Convenience functions for easy access
def detect_taskbar_apps() -> str:
    """
    Main function to detect and describe taskbar applications cleanly.
    Returns human-readable description of actual taskbar contents.
    """
    detector = TaskbarDetector()
    return detector.format_taskbar_open_apps()

def can_see_taskbar() -> str:
    """
    Check if the assistant can see and analyze the taskbar.
    
    Returns:
        Capability report
    """
    detector = TaskbarDetector()
    
    capabilities = []
    limitations = []
    
    # Check process detection
    capabilities.append("✅ Process Detection - I can see all running processes")
    
    # Check Windows API access
    if WIN32_AVAILABLE:
        capabilities.append("✅ Window Detection - I can see window titles and states")
    else:
        limitations.append("❌ Win32 API - Limited window information available")
    
    # Check visual analysis
    if detector.multimodal:
        capabilities.append("✅ Visual Analysis - I can see and analyze your screen/taskbar")
        capabilities.append("✅ Icon Recognition - I can identify app icons in the taskbar")
    else:
        limitations.append("❌ Computer Vision - Cannot visually analyze taskbar")
    
    report = []
    report.append("🔍 TASKBAR DETECTION CAPABILITIES")
    report.append("=" * 40)
    report.append("\nWhat I CAN do:")
    report.extend(capabilities)
    
    if limitations:
        report.append("\nLimitations:")
        report.extend(limitations)
    
    report.append(f"\nDetection Methods Available: {len(capabilities)}/3")
    
    return "\n".join(report)