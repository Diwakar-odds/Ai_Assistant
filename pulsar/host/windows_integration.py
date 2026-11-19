"""
Pulsar Host - Production Windows 11 Desktop Integration
=======================================================
Provides native Windows 11 App identity & shell integration:
1. AppUserModelID (`Pulsar.AIAssistant.App.v1`) so Windows 11 merges the
   pinned Taskbar icon, Start Menu tile, and live Dashboard window into
   ONE single native application icon (never grouped under generic Python).
2. `SHGetPropertyStoreForWindow` relaunch properties (`Pulsar.exe`,
   `assets/pulsar_app.ico`, `Pulsar AI Assistant`) so right-clicking the
   running taskbar icon -> "Pin to taskbar" pins `Pulsar.exe` cleanly.
3. Autostart with Windows via `HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run`
   (interactive user session only, per Claude Blueprint Phase 5).
4. Foreground focus helper (`AllowSetForegroundWindow` / `SetForegroundWindow`),
   browser launcher, and logs explorer opener.
"""

import os
import sys
import logging
import webbrowser
from pathlib import Path
from typing import Optional

logger = logging.getLogger("pulsar.host.windows")

PULSAR_APP_ID = "Pulsar.AIAssistant.App.v1"
PULSAR_DISPLAY_NAME = "Pulsar AI Assistant"
AUTOSTART_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_VALUE_NAME = "PulsarAIAssistant"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def get_app_exe_path() -> Path:
    """Returns path to the native Pulsar.exe (works in frozen standalone & dev modes)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return REPO_ROOT / "Pulsar.exe"


def get_app_icon_path() -> Path:
    """Returns path to the multi-DPI Windows .ico file (frozen & dev modes)."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        meipass = Path(getattr(sys, "_MEIPASS", exe_dir))
        for cand in (
            meipass / "assets" / "pulsar_app.ico",
            exe_dir / "assets" / "pulsar_app.ico",
            exe_dir / "_internal" / "assets" / "pulsar_app.ico",
        ):
            if cand.exists():
                return cand
    return REPO_ROOT / "assets" / "pulsar_app.ico"


def set_process_app_user_model_id(app_id: str = PULSAR_APP_ID) -> bool:
    """
    Sets Windows AppUserModelID for this process.
    MUST be called BEFORE QApplication() is constructed!
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        hr = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        if hr == 0:
            logger.info(f"[Windows] AppUserModelID set to '{app_id}'")
            return True
        logger.debug(f"[Windows] SetCurrentProcessExplicitAppUserModelID returned HRESULT {hr}")
        return False
    except Exception as e:
        logger.debug(f"[Windows] AppUserModelID setup note: {e}")
        return False


def configure_window_taskbar_identity(
    hwnd: int,
    app_id: str = PULSAR_APP_ID,
    exe_path: Optional[Path] = None,
    icon_path: Optional[Path] = None,
    display_name: str = PULSAR_DISPLAY_NAME,
) -> bool:
    """
    Stamps AppUserModel.ID and Relaunch* properties directly onto a top-level HWND
    via `SHGetPropertyStoreForWindow`.

    Result on Windows 11:
    - Running Dashboard groups directly onto the pinned Pulsar taskbar icon.
    - Right-clicking the running icon -> "Pin to taskbar" pins `Pulsar.exe` with
      the glowing `pulsar_app.ico` icon instead of generic `pythonw.exe`.
    """
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        from win32com.propsys import propsys, pscon

        exe = exe_path or get_app_exe_path()
        ico = icon_path or get_app_icon_path()

        store = propsys.SHGetPropertyStoreForWindow(int(hwnd))
        store.SetValue(pscon.PKEY_AppUserModel_ID, propsys.PROPVARIANTType(app_id))
        store.SetValue(
            pscon.PKEY_AppUserModel_RelaunchDisplayNameResource,
            propsys.PROPVARIANTType(display_name),
        )
        if exe.exists():
            store.SetValue(
                pscon.PKEY_AppUserModel_RelaunchCommand,
                propsys.PROPVARIANTType(f'"{exe}"'),
            )
        if ico.exists():
            store.SetValue(
                pscon.PKEY_AppUserModel_RelaunchIconResource,
                propsys.PROPVARIANTType(f"{ico},0"),
            )
        store.Commit()
        logger.info(f"[Windows] Taskbar Relaunch Identity bound to HWND {hwnd} -> {exe.name}")
        return True
    except Exception as e:
        logger.debug(f"[Windows] Window taskbar identity note: {e}")
        return False


def allow_foreground_activation() -> None:
    """Grants Windows permission to bring the running Host Dashboard to the foreground."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ASFW_ANY = 0xFFFFFFFF
        ctypes.windll.user32.AllowSetForegroundWindow(ASFW_ANY)
    except Exception:
        pass


def force_window_foreground(hwnd: int) -> None:
    """Reliably restores and focuses a window on Windows 11 when woken from tray."""
    if sys.platform != "win32" or not hwnd:
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        SW_RESTORE = 9
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def is_autostart_enabled() -> bool:
    """Returns True if Pulsar is registered in HKCU\\...\\Run for Windows login."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_PATH, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, AUTOSTART_VALUE_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_autostart_enabled(enabled: bool) -> bool:
    """
    Enables or disables automatic launch of Pulsar (minimized to tray + 4D Orb)
    when the user logs into Windows (HKCU Run key — interactive session only).
    """
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                exe = get_app_exe_path()
                if exe.exists():
                    cmd = f'"{exe}" --tray'
                else:
                    pyw = REPO_ROOT / "venv" / "Scripts" / "pythonw.exe"
                    cmd = f'"{pyw}" "{REPO_ROOT / "web.py"}" --tray'
                winreg.SetValueEx(key, AUTOSTART_VALUE_NAME, 0, winreg.REG_SZ, cmd)
                logger.info(f"[Windows] Autostart ENABLED: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, AUTOSTART_VALUE_NAME)
                    logger.info("[Windows] Autostart DISABLED.")
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        logger.warning(f"[Windows] Failed to update Autostart registry key: {e}")
        return False


def open_browser_dashboard(port: int = 5000) -> None:
    """Opens the Pulsar Web UI in the user's default web browser."""
    try:
        webbrowser.open(f"http://127.0.0.1:{port}/")
    except Exception as e:
        logger.debug(f"[Windows] Failed to open browser: {e}")


def open_logs_folder() -> None:
    """Opens %LOCALAPPDATA%\\Pulsar\\logs in Windows File Explorer."""
    try:
        from pulsar.logging_setup import get_log_dir
        log_dir = get_log_dir()
        if sys.platform == "win32":
            os.startfile(str(log_dir))
    except Exception as e:
        logger.debug(f"[Windows] Failed to open logs folder: {e}")
