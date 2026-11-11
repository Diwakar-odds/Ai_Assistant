# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

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
        """Get information about all visible windows using win32gui."""
        windows = []
        
        def enum_window_callback(hwnd, _):
            if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
                try:
                    window_text = win32gui.GetWindowText(hwnd)
                    class_name = win32gui.GetClassName(hwnd)
                    
                    # Skip empty titles and certain system windows
                    if window_text and class_name not in ['Shell_TrayWnd', 'DV2ControlHost']:
                        # Get process information
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            proc = psutil.Process(pid)
                            process_name = proc.name()
                        except:
                            process_name = "Unknown"
                            pid = 0
                        
                        # Get window position
                        try:
                            rect = win32gui.GetWindowRect(hwnd)
                            position = {
                                "left": rect[0],
                                "top": rect[1], 
                                "right": rect[2],
                                "bottom": rect[3],
                                "width": rect[2] - rect[0],
                                "height": rect[3] - rect[1]
                            }
                        except:
                            position = {}
                        
                        windows.append({
                            "hwnd": hwnd,
                            "title": window_text,
                            "class_name": class_name,
                            "process_name": process_name,
                            "pid": pid,
                            "position": position,
                            "is_minimized": win32gui.IsIconic(hwnd),
                            "is_maximized": win32gui.IsZoomed(hwnd)
                        })
                except Exception as e:
                    pass  # Skip windows we can't access
        
        try:
            win32gui.EnumWindows(enum_window_callback, None)
        except Exception as e:
            logger.error(f"Error enumerating windows: {e}")
        
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
        
        Args:
            app_name: Name of the application to find (e.g., 'chrome', 'antigravity')
            expected_title_keyword: Optional keyword to look for in the window title (e.g., folder name or profile)
            
        Returns:
            Information about whether the app is found and its status
        """
        logger.info(f"🔍 Looking for '{app_name}' in taskbar...")
        
        # Check running processes first
        app_found_in_processes = False
        matching_processes = []
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if app_name.lower() in proc.info['name'].lower():
                    matching_processes.append(proc.info)
                    app_found_in_processes = True
            except:
                continue

        # Check Window Titles for deep verification (e.g., Folder name in IDE, Profile in Chrome)
        app_found_in_windows = False
        title_match_found = False
        matching_windows = []
        
        if WIN32_AVAILABLE:
            windows = self._get_window_information()
            for win in windows:
                title_lower = win.get("title", "").lower()
                process_lower = win.get("process_name", "").lower()
                
                # Check if this window belongs to our target app (by process name or title)
                if app_name.lower() in process_lower or app_name.lower() in title_lower:
                    app_found_in_windows = True
                    matching_windows.append(win)
                    
                    # If we need a specific title keyword, check for it
                    if expected_title_keyword and expected_title_keyword.lower() in title_lower:
                        title_match_found = True
        
        # Determine overall success state
        is_successful = False
        if expected_title_keyword:
            # If a specific keyword was requested, we MUST find it in the window title
            is_successful = title_match_found
        else:
            # Otherwise, just finding the app process or window is enough
            is_successful = app_found_in_processes or app_found_in_windows
        
        # Visual search if available (Fallback - only when active provider is Gemini with key)
        visual_result = {}
        allow_vlm = False
        if self.multimodal and not is_successful:
            try:
                import sys
                from pathlib import Path
                bdir = str(Path(__file__).resolve().parents[4] / "backend")
                if bdir not in sys.path:
                    sys.path.insert(0, bdir)
                from settings_manager import get_provider, get_api_key
                allow_vlm = (get_provider() == "gemini" and bool(get_api_key("gemini")))
            except Exception:
                allow_vlm = False

        if self.multimodal and not is_successful and allow_vlm:
            try:
                visual_prompt = f"""
                Look at this Windows desktop screenshot and determine:
                
                1. Is there an icon for "{app_name}" in the taskbar?
                2. If yes, does it appear to be running (highlighted/active)?
                3. Is there an open window for this application?
                4. Where exactly do you see it?
                
                Be specific about what you observe.
                """
                if expected_title_keyword:
                    visual_prompt += f'\n5. Do you see the text "{expected_title_keyword}" anywhere in the application window?'
                
                visual_result = self.multimodal.answer_visual_question(visual_prompt)
                
            except Exception as e:
                visual_result = {"error": str(e)}
        
        return {
            "app_name": app_name,
            "found_in_processes": app_found_in_processes,
            "app_found_in_windows": app_found_in_windows,
            "title_match_found": title_match_found,
            "is_successful": is_successful,
            "matching_processes": matching_processes,
            "matching_windows": matching_windows,
            "visual_search_result": visual_result,
            "timestamp": datetime.now().isoformat()
        }

# Convenience functions for easy access
def detect_taskbar_apps() -> str:
    """
    Main function to detect and describe taskbar applications.
    
    Returns:
        Human-readable description of taskbar contents
    """
    detector = TaskbarDetector()
    analysis = detector.get_complete_desktop_analysis()
    
    # Format results for human reading
    report_lines = []
    report_lines.append("📊 TASKBAR & RUNNING APPS ANALYSIS")
    report_lines.append("=" * 50)
    
    # Process information
    if "process_analysis" in analysis and "summary" in analysis["process_analysis"]:
        summary = analysis["process_analysis"]["summary"]
        report_lines.append(f"🔄 Total Running Processes: {summary.get('total_processes', 0)}")
        report_lines.append(f"🪟 Visible Windows: {summary.get('total_windows', 0)}")
    
    # Visual analysis
    if "visual_analysis" in analysis and "visual_analysis" in analysis["visual_analysis"]:
        report_lines.append("\n👁️ VISUAL TASKBAR ANALYSIS:")
        report_lines.append(analysis["visual_analysis"]["visual_analysis"])
    
    # Focused taskbar analysis  
    if "taskbar_analysis" in analysis and "taskbar_analysis" in analysis["taskbar_analysis"]:
        report_lines.append("\n🎯 FOCUSED TASKBAR ANALYSIS:")
        report_lines.append(analysis["taskbar_analysis"]["taskbar_analysis"])
    
    # Running processes summary
    if "process_analysis" in analysis and "processes" in analysis["process_analysis"]:
        processes = analysis["process_analysis"]["processes"]
        # Show top processes by memory usage
        top_processes = sorted(processes, key=lambda x: x.get('memory_mb', 0), reverse=True)[:10]
        
        report_lines.append("\n💾 TOP MEMORY-USING PROCESSES:")
        for proc in top_processes:
            name = proc.get('name', 'Unknown')[:20].ljust(20)
            memory = f"{proc.get('memory_mb', 0):.1f}MB".rjust(10)
            report_lines.append(f"  • {name} {memory}")
    
    return "\n".join(report_lines)

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