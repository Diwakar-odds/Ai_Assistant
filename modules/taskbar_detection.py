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
    print("Warning: win32gui not available. Some taskbar detection features will be limited.")

# Import multimodal capabilities for visual analysis
try:
    from .multimodal import MultiModalAI
    MULTIMODAL_AVAILABLE = True
except ImportError:
    MULTIMODAL_AVAILABLE = False
    print("Warning: Multimodal AI not available for visual taskbar analysis.")

class TaskbarDetector:
    """Detects and analyzes Windows taskbar and running applications."""
    
    def __init__(self):
        self.multimodal = None
        if MULTIMODAL_AVAILABLE:
            try:
                self.multimodal = MultiModalAI()
            except Exception as e:
                print(f"Warning: Could not initialize MultiModalAI: {e}")
    
    def get_running_applications(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get detailed information about all running applications.
        
        Returns:
            Dictionary with application information including PIDs, names, and window titles
        """
        print("🔍 Detecting running applications...")
        
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
            print(f"Error enumerating windows: {e}")
        
        return windows
    
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
        
        print("🔍 Analyzing taskbar region specifically...")
        
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
    
    def find_specific_app_in_taskbar(self, app_name: str) -> Dict[str, Any]:
        """
        Look for a specific application in the taskbar.
        
        Args:
            app_name: Name of the application to find
            
        Returns:
            Information about whether the app is found and its status
        """
        print(f"🔍 Looking for '{app_name}' in taskbar...")
        
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
        
        # Visual search if available
        visual_result = {}
        if self.multimodal:
            try:
                visual_prompt = f"""
                Look at this Windows desktop screenshot and determine:
                
                1. Is there an icon for "{app_name}" in the taskbar?
                2. If yes, does it appear to be running (highlighted/active)?
                3. Is there an open window for this application?
                4. Where exactly do you see it?
                
                Be specific about what you observe.
                """
                
                visual_result = self.multimodal.answer_visual_question(visual_prompt)
                
            except Exception as e:
                visual_result = {"error": str(e)}
        
        return {
            "app_name": app_name,
            "found_in_processes": app_found_in_processes,
            "matching_processes": matching_processes,
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