"""
System Automation Module

Handles system-level controls:
- Screen Brightness
- WiFi / Network (Toggle, Airplane Mode)
- Volume (Wrapper around existing audio utilities)
- Power (Sleep, Shutdown - optional)
"""

import logging
import subprocess
import platform
import os
from typing import Optional, Dict, Any

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

class SystemAutomation:
    """
    Handles system settings and controls
    """
    
    def __init__(self):
        """Initialize system automation"""
        logger.info("âš™ï¸ SystemAutomation initialized")
        if not BRIGHTNESS_AVAILABLE:
            logger.warning("âš ï¸ 'screen_brightness_control' not installed. Brightness control will be limited.")
            
    # ===== BRIGHTNESS =====
    
    def set_brightness(self, level: int) -> bool:
        """
        Set screen brightness (0-100)
        """
        logger.info(f"ðŸ”† Setting brightness to {level}%")
        
        if BRIGHTNESS_AVAILABLE:
            try:
                sbc.set_brightness(level)
                return True
            except Exception as e:
                logger.error(f"âŒ Failed to set brightness (sbc): {e}")
        
        # Fallback using PowerShell (WmiMonitorBrightnessMethods)
        # Note: This often requires admin privileges or specific driver support
        try:
            cmd = f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"
            subprocess.run(["powershell", "-Command", cmd], capture_output=True)
            return True
        except Exception as e:
            logger.error(f"âŒ Failed to set brightness (powershell): {e}")
            return False

    def get_brightness(self) -> int:
        """Get current brightness level"""
        if BRIGHTNESS_AVAILABLE:
            try:
                return sbc.get_brightness()[0]
            except:
                pass
        return -1

    # ===== NETWORK / WIFI =====

    def toggle_wifi(self, enable: bool) -> bool:
        """
        Enable/Disable WiFi
        """
        action = "enable" if enable else "disable"
        logger.info(f"ðŸ“¶ Toggling WiFi: {action}")

        if platform.system().lower() != "windows":
            logger.error("âŒ WiFi toggle is currently implemented for Windows only")
            return False

        desired_state = "enabled" if enable else "disabled"

        try:
            # Discover likely Wi-Fi adapter names first.
            discover = subprocess.run(
                ["netsh", "interface", "show", "interface"],
                capture_output=True,
                text=True,
            )

            candidate_names = []
            if discover.returncode == 0 and discover.stdout:
                for line in discover.stdout.splitlines():
                    lower = line.lower()
                    if any(tag in lower for tag in ["wi-fi", "wifi", "wireless", "wlan"]):
                        # Interface name is typically the trailing token(s).
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
                )
                if result.returncode == 0:
                    logger.info(f"âœ… WiFi {desired_state} via adapter '{name}'")
                    return True

            # Fallback PowerShell command.
            ps_action = "Enable" if enable else "Disable"
            ps_cmd = (
                f"Get-NetAdapter | Where-Object {{$_.InterfaceDescription -match 'Wi-Fi|Wireless|WLAN' "
                f"-or $_.Name -match 'Wi-Fi|WiFi|Wireless|WLAN'}} | "
                f"{ps_action}-NetAdapter -Confirm:$false"
            )
            ps_result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
            )
            if ps_result.returncode == 0:
                logger.info(f"âœ… WiFi {desired_state} via PowerShell fallback")
                return True

            logger.error(
                "âŒ WiFi toggle failed via netsh and PowerShell. "
                f"PowerShell error: {ps_result.stderr or ps_result.stdout}"
            )
            return False

        except Exception as e:
            logger.error(f"âŒ WiFi toggle error: {e}")
            return False

    def toggle_airplane_mode(self, enable: bool) -> bool:
        """
        Toggle Airplane Mode (Windows 10/11)
        This is tricky via command line without specialized tools.
        Leaving as a placeholder or using GUI automation fallback if needed.
        """
        logger.warning("âš ï¸ Airplane mode toggle requires GUI automation or specific registry hacks (unreliable).")
        return False
        
    # ===== VOLUME (Wrapper) =====
    
    def set_volume(self, level: int) -> str:
        if VOLUME_AVAILABLE:
            return set_system_volume(level)
        return "Volume module not available"

    def get_volume(self) -> str:
        if VOLUME_AVAILABLE:
            return get_system_volume()
        return "Volume module not available"
        
    def volume_up(self, amount: int = 10) -> str:
        if VOLUME_AVAILABLE:
            return volume_up(amount)
        return "Volume module not available"
        
    def volume_down(self, amount: int = 10) -> str:
        if VOLUME_AVAILABLE:
            return volume_down(amount)
        return "Volume module not available"

    def mute(self) -> str:
        if VOLUME_AVAILABLE:
            return mute_volume()
        return "Volume module not available"

    def unmute(self) -> str:
        if VOLUME_AVAILABLE:
            return unmute_volume()
        return "Volume module not available"

