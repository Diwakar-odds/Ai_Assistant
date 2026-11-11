"""
System Automation Module

Handles system-level controls:
- Screen Brightness (sbc or Windows CIM WmiMonitorBrightnessMethods)
- WiFi / Bluetooth Radios (non-admin WinRT Windows.Devices.Radios via PowerShell + winsdk fallback)
- Dark Mode / Windows Personalize theme
- Volume (Wrapper around COM-safe core audio utilities)
- Battery & Power
"""

import logging
import subprocess
import platform
import os
import asyncio
import ctypes
from typing import Optional, Dict, Any, Tuple

# Optional dependencies
try:
    import screen_brightness_control as sbc
    BRIGHTNESS_AVAILABLE = True
except ImportError:
    BRIGHTNESS_AVAILABLE = False

try:
    from ai_assistant.core.core import set_system_volume, get_system_volume, volume_up, volume_down, mute_volume, unmute_volume
    VOLUME_AVAILABLE = True
except ImportError:
    VOLUME_AVAILABLE = False

logger = logging.getLogger(__name__)


def _run_powershell(script: str, timeout: int = 12) -> subprocess.CompletedProcess:
    """Run a non-interactive PowerShell snippet cleanly without flashing a console window."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if platform.system().lower() == "windows" else 0
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=flags,
    )


class SystemAutomation:
    """
    Handles system settings and controls
    """

    def __init__(self):
        """Initialize system automation"""
        self.last_error: str = ""
        logger.info("SystemAutomation initialized")
        if not BRIGHTNESS_AVAILABLE:
            logger.debug("'screen_brightness_control' not installed; using Windows CIM/WMI brightness control.")

    # ===== WINRT RADIO HELPER (NON-ADMIN WI-FI & BLUETOOTH) =====

    def _winrt_radio(self, kind: str, enable: Optional[bool] = None) -> Tuple[bool, str, Optional[bool]]:
        """
        Query or toggle a Windows radio ('WiFi' or 'Bluetooth') using inline WinRT
        (`Windows.Devices.Radios.Radio`) via PowerShell without requiring Admin elevation.
        Returns `(ok, message, state_bool_or_none)`.
        """
        if platform.system().lower() != "windows":
            msg = f"{kind} radio control is only supported on Windows."
            self.last_error = msg
            return False, msg, None

        if kind not in ("WiFi", "Bluetooth"):
            msg = f"Unsupported radio kind: {kind}"
            self.last_error = msg
            return False, msg, None

        if enable is not None:
            target_state = "On" if enable else "Off"
            action_block = f"""
$res = Await ($target.SetStateAsync([Windows.Devices.Radios.RadioState]::{target_state})) ([Windows.Devices.Radios.RadioAccessStatus])
Start-Sleep -Milliseconds 150
$cur = $target.State.ToString()
Write-Output ("RES=" + $res.ToString() + "|STATE=" + $cur)
if ($res.ToString() -ne 'Allowed') {{ exit 4 }}
"""
        else:
            action_block = """
Write-Output ("RES=Allowed|STATE=" + $target.State.ToString())
"""

        ps_script = f"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{ $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }})[0]
Function Await($WinRtTask, $ResultType) {{
    $netTask = $asTaskGeneric.MakeGenericMethod($ResultType).Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}}
$null = [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime]
$null = [Windows.Devices.Radios.RadioState,Windows.System.Devices,ContentType=WindowsRuntime]
$null = [Windows.Devices.Radios.RadioKind,Windows.System.Devices,ContentType=WindowsRuntime]
$null = [Windows.Devices.Radios.RadioAccessStatus,Windows.System.Devices,ContentType=WindowsRuntime]

$access = Await ([Windows.Devices.Radios.Radio]::RequestAccessAsync()) ([Windows.Devices.Radios.RadioAccessStatus])
if ($access.ToString() -ne 'Allowed') {{
    Write-Output ("ACCESS=" + $access.ToString())
    exit 2
}}
$radios = Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) ([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])
$target = $radios | Where-Object {{ $_.Kind.ToString() -eq '{kind}' }} | Select-Object -First 1
if (-not $target) {{
    Write-Output 'NO_RADIO'
    exit 3
}}
{action_block}
"""
        try:
            proc = _run_powershell(ps_script, timeout=15)
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()

            state_bool: Optional[bool] = None
            for line in out.splitlines():
                if "STATE=On" in line:
                    state_bool = True
                elif "STATE=Off" in line:
                    state_bool = False

            if proc.returncode == 0 and (enable is None or state_bool == enable or "RES=Allowed" in out):
                self.last_error = ""
                label = "Wi-Fi" if kind == "WiFi" else "Bluetooth"
                if enable is None:
                    return True, f"{label} is {'On' if state_bool else 'Off'}.", state_bool
                return True, f"{label} turned {'on' if enable else 'off'}.", state_bool

            if "NO_RADIO" in out or proc.returncode == 3:
                msg = f"No {kind} radio hardware found on this PC."
            elif "ACCESS=" in out or proc.returncode == 2 or proc.returncode == 4:
                msg = f"Windows denied {kind} radio control access ({out or err})."
            else:
                msg = f"Failed to control {kind} radio: {err or out or f'exit {proc.returncode}'}"
            self.last_error = msg
            logger.warning(msg)
            return False, msg, state_bool
        except subprocess.TimeoutExpired:
            msg = f"Timed out while accessing Windows {kind} radio."
            self.last_error = msg
            logger.error(msg)
            return False, msg, None
        except Exception as e:
            msg = f"{kind} radio error: {e}"
            self.last_error = msg
            logger.error(msg)
            return False, msg, None

    # ===== BRIGHTNESS =====

    def set_brightness_with_status(self, level: int) -> Tuple[bool, str]:
        """Set screen brightness (0-100) and verify OS execution."""
        try:
            target = max(0, min(100, int(str(level).replace('%', '').strip())))
        except (ValueError, TypeError):
            msg = f"Invalid brightness level: {level}"
            self.last_error = msg
            return False, msg

        logger.info(f"Setting brightness to {target}%")

        if BRIGHTNESS_AVAILABLE:
            try:
                sbc.set_brightness(target)
                self.last_error = ""
                return True, f"Screen brightness set to {target}%."
            except Exception as e:
                logger.warning(f"sbc brightness failed ({e}), trying WMI/CIM fallback")

        ps_cmd = (
            "$ErrorActionPreference = 'Stop'; "
            "$m = Get-CimInstance -Namespace root\\WMI -ClassName WmiMonitorBrightnessMethods | Select-Object -First 1; "
            "if (-not $m) { Write-Output 'NO_WMI_MONITOR'; exit 3 }; "
            f"$null = Invoke-CimMethod -InputObject $m -MethodName WmiSetBrightness -Arguments @{{ Timeout = [uint32]1; Brightness = [byte]{target} }}; "
            "Start-Sleep -Milliseconds 100; "
            "$cur = (Get-CimInstance -Namespace root\\WMI -ClassName WmiMonitorBrightness | Select-Object -First 1 -ExpandProperty CurrentBrightness); "
            "Write-Output ('BRIGHTNESS=' + $cur)"
        )
        try:
            res = _run_powershell(ps_cmd, timeout=10)
            out = (res.stdout or "").strip()
            err = (res.stderr or "").strip()
            if res.returncode == 0 and "BRIGHTNESS=" in out:
                actual_str = out.split("BRIGHTNESS=")[-1].strip()
                self.last_error = ""
                return True, f"Screen brightness set to {actual_str}%."
            if "NO_WMI_MONITOR" in out or "not supported" in err.lower():
                msg = "This display does not support software WMI brightness adjustment (external HDMI/DP monitors often disable DDC/WMI)."
            else:
                msg = f"Could not set brightness: {err or out or f'exit {res.returncode}'}"
            self.last_error = msg
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Failed to set brightness: {e}"
            self.last_error = msg
            logger.error(msg)
            return False, msg

    def set_brightness(self, level: int) -> bool:
        """Set screen brightness (0-100)."""
        ok, _ = self.set_brightness_with_status(level)
        return ok

    def get_brightness(self) -> int:
        """Get current brightness level (0-100), or -1 if unavailable."""
        if BRIGHTNESS_AVAILABLE:
            try:
                val = sbc.get_brightness()
                if isinstance(val, (list, tuple)) and val:
                    return int(val[0])
                return int(val)
            except Exception:
                pass
        try:
            ps_cmd = (
                "$ErrorActionPreference = 'Stop'; "
                "$cur = (Get-CimInstance -Namespace root\\WMI -ClassName WmiMonitorBrightness | Select-Object -First 1 -ExpandProperty CurrentBrightness); "
                "Write-Output $cur"
            )
            res = _run_powershell(ps_cmd, timeout=8)
            if res.returncode == 0 and (res.stdout or "").strip().isdigit():
                return int(res.stdout.strip())
        except Exception as e:
            logger.debug(f"get_brightness failed: {e}")
        return -1

    def adjust_brightness_with_status(self, delta: int) -> Tuple[bool, str, int]:
        """Adjust brightness relatively by `delta` (+/-)."""
        current = self.get_brightness()
        if current < 0:
            msg = "Could not read current screen brightness (display may not support WMI brightness control)."
            self.last_error = msg
            return False, msg, -1
        target = max(0, min(100, current + int(delta)))
        ok, msg = self.set_brightness_with_status(target)
        return ok, msg, (target if ok else current)

    # ===== DARK MODE / PERSONALIZATION =====

    def toggle_dark_mode(self, enable: bool) -> Tuple[bool, str]:
        """Enable Dark Mode (`enable=True`) or Light Mode (`enable=False`) on Windows."""
        if platform.system().lower() != "windows":
            return False, "Theme toggling is currently supported on Windows only."
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            val = 0 if enable else 1
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, val)
                winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, val)

            # Notify Explorer / open Windows apps of theme change
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            try:
                ctypes.windll.user32.SendMessageTimeoutW(
                    HWND_BROADCAST, WM_SETTINGCHANGE, 0, "ImmersiveColorSet", SMTO_ABORTIFHUNG, 1000, None
                )
            except Exception:
                pass

            self.last_error = ""
            return True, ("Dark mode enabled." if enable else "Light mode enabled (Dark mode off).")
        except Exception as e:
            msg = f"Failed to change Windows theme mode: {e}"
            self.last_error = msg
            logger.error(msg)
            return False, msg

    # ===== NETWORK / WIFI =====

    def get_wifi_status(self) -> Optional[bool]:
        """Return True if Wi-Fi radio is On, False if Off, None if unknown."""
        _, _, st = self._winrt_radio("WiFi", enable=None)
        return st

    def toggle_wifi_with_status(self, enable: bool) -> Tuple[bool, str]:
        """Enable/Disable Wi-Fi cleanly (WinRT non-admin first, netsh/NetAdapter fallback)."""
        action = "enable" if enable else "disable"
        logger.info(f"Toggling WiFi: {action}")

        if platform.system().lower() != "windows":
            msg = "Wi-Fi toggle is currently implemented for Windows only."
            self.last_error = msg
            return False, msg

        # 1. Primary: Non-admin WinRT Radio API (works cleanly as standard user)
        ok, msg, _ = self._winrt_radio("WiFi", enable=enable)
        if ok:
            return True, msg

        # 2. Fallback: netsh / NetAdapter (succeeds if elevated)
        desired_state = "enabled" if enable else "disabled"
        try:
            discover = subprocess.run(
                ["netsh", "interface", "show", "interface"],
                capture_output=True,
                text=True,
                timeout=8,
            )

            candidate_names = []
            if discover.returncode == 0 and discover.stdout:
                for line in discover.stdout.splitlines():
                    lower = line.lower()
                    if any(tag in lower for tag in ["wi-fi", "wifi", "wireless", "wlan"]):
                        parts = line.split()
                        if parts:
                            candidate_names.append(" ".join(parts[3:]) if len(parts) > 3 else parts[-1])

            if not candidate_names:
                candidate_names = ["Wi-Fi", "WiFi", "Wireless Network Connection"]

            for name in candidate_names:
                result = subprocess.run(
                    ["netsh", "interface", "set", "interface", f"name={name}", f"admin={desired_state}"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                )
                if result.returncode == 0:
                    self.last_error = ""
                    return True, f"Wi-Fi {'turned on' if enable else 'turned off'}."

            ps_action = "Enable" if enable else "Disable"
            ps_cmd = (
                f"Get-NetAdapter | Where-Object {{$_.InterfaceDescription -match 'Wi-Fi|Wireless|WLAN' "
                f"-or $_.Name -match 'Wi-Fi|WiFi|Wireless|WLAN'}} | "
                f"{ps_action}-NetAdapter -Confirm:$false -ErrorAction Stop"
            )
            ps_result = _run_powershell(ps_cmd, timeout=10)
            if ps_result.returncode == 0:
                self.last_error = ""
                return True, f"Wi-Fi {'turned on' if enable else 'turned off'}."

            err_detail = (ps_result.stderr or ps_result.stdout or msg).strip()
            if "denied" in err_detail.lower() or "system error 5" in err_detail.lower():
                final_msg = f"Wi-Fi toggle could not complete without Administrator privileges ({msg})."
            else:
                final_msg = msg or f"Wi-Fi toggle failed: {err_detail}"
            self.last_error = final_msg
            logger.error(final_msg)
            return False, final_msg
        except Exception as e:
            final_msg = msg or f"Wi-Fi toggle error: {e}"
            self.last_error = final_msg
            logger.error(final_msg)
            return False, final_msg

    def toggle_wifi(self, enable: bool) -> bool:
        """Enable/Disable Wi-Fi."""
        ok, _ = self.toggle_wifi_with_status(enable)
        return ok

    def toggle_airplane_mode(self, enable: bool) -> bool:
        """Airplane Mode direct toggle is restricted on Windows without Settings UI."""
        self.last_error = "Direct Airplane Mode toggle is restricted by Windows; open Airplane Mode settings instead."
        logger.warning(self.last_error)
        return False

    # ===== VOLUME (Wrapper) =====

    def set_volume(self, level: int) -> str:
        if VOLUME_AVAILABLE:
            return set_system_volume(level)
        return "❌ Volume module not available"

    def get_volume(self) -> str:
        if VOLUME_AVAILABLE:
            return get_system_volume()
        return "❌ Volume module not available"

    def volume_up(self, amount: int = 10) -> str:
        if VOLUME_AVAILABLE:
            return volume_up(amount)
        return "❌ Volume module not available"

    def volume_down(self, amount: int = 10) -> str:
        if VOLUME_AVAILABLE:
            return volume_down(amount)
        return "❌ Volume module not available"

    def mute(self) -> str:
        if VOLUME_AVAILABLE:
            return mute_volume()
        return "❌ Volume module not available"

    def unmute(self) -> str:
        if VOLUME_AVAILABLE:
            return unmute_volume()
        return "❌ Volume module not available"

    # ===== BATTERY =====

    def get_battery_status(self) -> str:
        """Get current battery percentage and status."""
        try:
            import psutil
            battery = psutil.sensors_battery()
            if not battery:
                return "Battery status not available (might be a desktop computer)."

            percent = battery.percent
            plugged = battery.power_plugged
            status = "plugged in and charging" if plugged else "running on battery"

            return f"Battery is at {percent}%, currently {status}."
        except Exception as e:
            logger.error(f"Failed to get battery status: {e}")
            return "Could not retrieve battery status."

    # ===== BLUETOOTH =====

    def get_bluetooth_status(self) -> Optional[bool]:
        """Return True if Bluetooth radio is On, False if Off, None if unknown."""
        _, _, st = self._winrt_radio("Bluetooth", enable=None)
        return st

    def toggle_bluetooth_with_status(self, enable: bool) -> Tuple[bool, str]:
        """Toggle Bluetooth On/Off via optional winsdk or non-admin WinRT PowerShell."""
        action = "on" if enable else "off"
        logger.info(f"Toggling Bluetooth: {action}")

        if platform.system().lower() != "windows":
            msg = "Bluetooth toggle is only supported on Windows."
            self.last_error = msg
            return False, msg

        try:
            from winsdk.windows.devices.radios import Radio, RadioKind, RadioState

            async def _toggle():
                radios = await Radio.get_radios_async()
                for radio in radios:
                    if radio.kind == RadioKind.BLUETOOTH:
                        state = RadioState.ON if enable else RadioState.OFF
                        await radio.set_state_async(state)
                        return True
                return False

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_toggle())
            loop.close()

            if result:
                self.last_error = ""
                return True, f"Bluetooth turned {action}."
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"winsdk Bluetooth toggle note: {e}")

        # Primary/Fallback: Non-admin WinRT Radio via PowerShell
        ok, msg, _ = self._winrt_radio("Bluetooth", enable=enable)
        return ok, msg

    def toggle_bluetooth(self, enable: bool) -> bool:
        """Toggle Bluetooth On/Off."""
        ok, _ = self.toggle_bluetooth_with_status(enable)
        return ok
