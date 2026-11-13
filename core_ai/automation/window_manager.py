"""
Window Management Module
Provides robust window discovery, foreground activation, and graceful window closing
using Windows Win32 APIs, psutil, and WScript.Shell fallbacks.
"""

import os
import sys
import time
import logging
from typing import Optional, List, Dict, Any, Union

logger = logging.getLogger(__name__)

# Try importing pywin32 modules
try:
    import win32gui
    import win32con
    import win32process
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logger.warning("pywin32 not available; window management features will use fallback methods.")

# Try importing psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available; process inspection features will be limited.")

# Known process name mappings for common apps
KNOWN_PROCESS_MAP = {
    'code': ['code.exe'],
    'vs code': ['code.exe'],
    'vscode': ['code.exe'],
    'visual studio code': ['code.exe'],
    'chrome': ['chrome.exe'],
    'google chrome': ['chrome.exe'],
    'brave': ['brave.exe'],
    'edge': ['msedge.exe'],
    'microsoft edge': ['msedge.exe'],
    'notepad': ['notepad.exe'],
    'calculator': ['calculatorapp.exe', 'calculator.exe', 'calc.exe'],
    'calc': ['calculatorapp.exe', 'calculator.exe', 'calc.exe'],
    'whatsapp': ['whatsapp.exe', 'whatsdesktop.exe'],
    'whtsp': ['whatsapp.exe', 'whatsdesktop.exe'],
    'whtsap': ['whatsapp.exe', 'whatsdesktop.exe'],
    'spotify': ['spotify.exe'],
    'paint': ['mspaint.exe', 'paint.exe'],
    'cmd': ['cmd.exe'],
    'command prompt': ['cmd.exe'],
    'terminal': ['windowsterminal.exe', 'wt.exe'],
    'windows terminal': ['windowsterminal.exe', 'wt.exe'],
    'wt': ['windowsterminal.exe', 'wt.exe'],
    'explorer': ['explorer.exe'],
    'file explorer': ['explorer.exe'],
    'vlc': ['vlc.exe'],
    'vlc media player': ['vlc.exe'],
    'discord': ['discord.exe'],
    'slack': ['slack.exe'],
    'word': ['winword.exe'],
    'microsoft word': ['winword.exe'],
    'excel': ['excel.exe'],
    'microsoft excel': ['excel.exe'],
    'powerpoint': ['powerpnt.exe'],
    'microsoft powerpoint': ['powerpnt.exe'],
    'teams': ['ms-teams.exe', 'teams.exe'],
    'settings': ['systemsettings.exe', 'systemsettingsadminflows.exe']
}


def get_running_windows(visible_only: bool = True) -> List[Dict[str, Any]]:
    """
    Get detailed information about running top-level windows.
    Returns list of dicts with: hwnd, title, pid, process_name, is_minimized, is_foreground.
    """
    windows = []
    if not WIN32_AVAILABLE:
        return windows

    foreground_hwnd = win32gui.GetForegroundWindow()

    def enum_cb(hwnd, _):
        try:
            if not win32gui.IsWindow(hwnd):
                return True
            if visible_only and not win32gui.IsWindowVisible(hwnd):
                return True

            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)

            # Skip empty or known OS background windows
            if not title and class_name in ['Shell_TrayWnd', 'DV2ControlHost', 'Progman']:
                return True

            pid = 0
            process_name = ""
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if PSUTIL_AVAILABLE and pid > 0:
                    try:
                        process_name = psutil.Process(pid).name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        process_name = ""
            except Exception:
                pass

            is_min = False
            try:
                is_min = bool(win32gui.IsIconic(hwnd))
            except Exception:
                pass

            windows.append({
                'hwnd': hwnd,
                'title': title,
                'class_name': class_name,
                'pid': pid,
                'process_name': process_name,
                'is_minimized': is_min,
                'is_foreground': (hwnd == foreground_hwnd)
            })
        except Exception:
            pass
        return True

    try:
        win32gui.EnumWindows(enum_cb, None)
    except Exception as e:
        logger.debug(f"EnumWindows error: {e}")

    return windows


def find_window_by_name(target_name: str, visible_only: bool = True) -> Optional[int]:
    """
    Find window handle (HWND) for an application by title or process name.
    Supports smart fuzzy matching and known alias expansion.
    """
    if not target_name:
        return None

    if not WIN32_AVAILABLE:
        return None

    target_lower = target_name.lower().strip()
    target_procs = [p.lower() for p in KNOWN_PROCESS_MAP.get(target_lower, [])]
    target_clean = target_lower.replace('.exe', '')

    all_windows = get_running_windows(visible_only=visible_only)
    if not all_windows:
        return None

    best_match_hwnd = None
    best_score = -1

    for w in all_windows:
        title = w['title'].lower()
        proc = w['process_name'].lower()
        score = 0

        # Exact title match
        if target_lower == title:
            score += 100
        # Title starts with target
        elif title.startswith(target_lower):
            score += 70
        # Target in title
        elif target_lower in title:
            score += 50
        # Clean target in title (e.g. "code" in "Visual Studio Code")
        elif target_clean in title:
            score += 45

        # Process name matching
        if proc:
            if proc in target_procs:
                score += 80
            elif target_clean == proc.replace('.exe', ''):
                score += 75
            elif target_clean in proc:
                score += 40

        if score > best_score and score >= 40:
            best_score = score
            best_match_hwnd = w['hwnd']

    return best_match_hwnd


def is_window_foreground(hwnd: int) -> bool:
    """Check if given window handle is currently in the foreground."""
    if not WIN32_AVAILABLE or not hwnd:
        return False
    try:
        return win32gui.GetForegroundWindow() == hwnd
    except Exception:
        return False


def bring_window_to_foreground(target_name_or_hwnd: Union[str, int], timeout: float = 2.5) -> bool:
    """
    Bring a window to the foreground using Windows Win32 API with WScript.Shell fallback.
    Accepts either an integer HWND or an application name string.
    Polls/retries if the window is currently starting up.
    """
    if not target_name_or_hwnd:
        return False

    hwnd = None
    if isinstance(target_name_or_hwnd, int) or (isinstance(target_name_or_hwnd, str) and target_name_or_hwnd.isdigit()):
        hwnd = int(target_name_or_hwnd)
    else:
        # Resolve target by name, with polling retry up to timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            hwnd = find_window_by_name(str(target_name_or_hwnd))
            if hwnd:
                break
            time.sleep(0.25)

    if not hwnd and not isinstance(target_name_or_hwnd, str):
        return False

    # Attempt Win32 activation if hwnd is found
    if WIN32_AVAILABLE and hwnd:
        try:
            # 1. Restore window if minimized
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

            # 2. Simulate Alt key to bypass Windows UIPI foreground lock
            try:
                win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
                win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
            except Exception:
                pass

            # 3. AttachThreadInput trick for foreground permissions
            try:
                fore_hwnd = win32gui.GetForegroundWindow()
                if fore_hwnd and fore_hwnd != hwnd:
                    fore_tid, _ = win32process.GetWindowThreadProcessId(fore_hwnd)
                    cur_tid = win32api.GetCurrentThreadId()
                    if fore_tid != cur_tid:
                        win32process.AttachThreadInput(cur_tid, fore_tid, True)
                        win32gui.BringWindowToTop(hwnd)
                        win32gui.SetForegroundWindow(hwnd)
                        win32process.AttachThreadInput(cur_tid, fore_tid, False)
                    else:
                        win32gui.BringWindowToTop(hwnd)
                        win32gui.SetForegroundWindow(hwnd)
                else:
                    win32gui.BringWindowToTop(hwnd)
                    win32gui.SetForegroundWindow(hwnd)
            except Exception:
                try:
                    win32gui.BringWindowToTop(hwnd)
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    pass

            time.sleep(0.1)
            if is_window_foreground(hwnd):
                return True
        except Exception as e:
            logger.debug(f"Win32 SetForegroundWindow failed: {e}")

    # Fallback to WScript.Shell AppActivate
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        if hwnd:
            success = shell.AppActivate(hwnd)
            if success:
                return True
        if isinstance(target_name_or_hwnd, str):
            success = shell.AppActivate(target_name_or_hwnd)
            if success:
                return True
    except Exception as e:
        logger.debug(f"WScript.Shell AppActivate failed: {e}")

    # Check foreground one more time
    if WIN32_AVAILABLE and hwnd and is_window_foreground(hwnd):
        return True

    return hwnd is not None


def close_window_gracefully(target_name_or_hwnd: Union[str, int], timeout: float = 2.0) -> bool:
    """
    Gracefully close an application by window handle, process name, or window title.
    Attempts WM_CLOSE first, then process termination if necessary.
    """
    if not target_name_or_hwnd:
        return False

    # HWND branch
    if isinstance(target_name_or_hwnd, int) or (isinstance(target_name_or_hwnd, str) and str(target_name_or_hwnd).isdigit()):
        hwnd = int(target_name_or_hwnd)
        if WIN32_AVAILABLE and win32gui.IsWindow(hwnd):
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                # Wait for closure
                start = time.time()
                while time.time() - start < timeout:
                    if not win32gui.IsWindow(hwnd):
                        return True
                    time.sleep(0.1)
            except Exception:
                pass

            # If still open, terminate process
            if PSUTIL_AVAILABLE and win32gui.IsWindow(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid > 0:
                        p = psutil.Process(pid)
                        p.terminate()
                        p.wait(timeout=1.0)
                        return True
                except Exception:
                    pass
        return True

    target_str = str(target_name_or_hwnd).strip()
    target_lower = target_str.lower()
    target_procs = [p.lower() for p in KNOWN_PROCESS_MAP.get(target_lower, [])]
    target_clean = target_lower.replace('.exe', '')

    any_closed = False

    # 1. Try finding matching windows and sending WM_CLOSE
    if WIN32_AVAILABLE:
        windows = get_running_windows(visible_only=False)
        for w in windows:
            title = w['title'].lower()
            proc = w['process_name'].lower()
            match = False

            if target_lower in title or target_clean in title:
                match = True
            elif proc and (proc in target_procs or target_clean == proc.replace('.exe', '')):
                match = True

            if match:
                try:
                    win32gui.PostMessage(w['hwnd'], win32con.WM_CLOSE, 0, 0)
                    any_closed = True
                except Exception:
                    pass

    if any_closed:
        time.sleep(0.5)

    # 2. Terminate matching processes via psutil if still running
    if PSUTIL_AVAILABLE:
        for p in psutil.process_iter(['pid', 'name']):
            try:
                pname = p.info['name'].lower()
                is_match = False
                if pname in target_procs:
                    is_match = True
                elif target_clean == pname.replace('.exe', ''):
                    is_match = True
                elif target_lower == pname:
                    is_match = True

                if is_match:
                    try:
                        p.terminate()
                        any_closed = True
                    except Exception:
                        try:
                            p.kill()
                            any_closed = True
                        except Exception:
                            pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    # 3. Fallback taskkill
    if not any_closed:
        import subprocess
        for candidate in target_procs or [f"{target_clean}.exe"]:
            try:
                res = subprocess.run(
                    ["taskkill", "/IM", candidate, "/F"],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if res.returncode == 0:
                    any_closed = True
            except Exception:
                pass

    return any_closed
