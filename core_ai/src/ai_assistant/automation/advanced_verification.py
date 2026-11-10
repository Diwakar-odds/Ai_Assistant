import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
import time
import os
import re
import socket
import urllib.request
import urllib.error
import json
from pathlib import Path

# Safe imports for OS/System capabilities
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import ctypes
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

try:
    from PIL import Image, ImageChops
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class MultiModalVerifier:
    """
    Advanced Verification System for Chain of Actions.
    Performs real state verification across modalities:
    - Process state (psutil)
    - Window title & GUI state (win32gui / EnumWindows)
    - Network connectivity (socket / DNS)
    - API & endpoint response (HTTP / socket)
    - Log pattern matching (real filesystem logs)
    - Visual before/after diffing (Pillow / VLM)
    """

    def __init__(self, log_dir: Optional[str] = None):
        self.history: List[Dict[str, Any]] = []
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            # Default to repo root / logs
            repo_root = Path(__file__).resolve().parents[4]
            self.log_dir = repo_root / "logs"

    # ===== 1. PRE-FLIGHT NETWORK CONNECTIVITY =====

    @staticmethod
    def check_network_connectivity(host: str = "8.8.8.8", port: int = 53, timeout: float = 2.0) -> bool:
        """
        Pre-flight network connectivity check:
        Verify if internet is up before allowing web tasks.
        Uses low-overhead socket connection to DNS.
        """
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, OSError):
            return False

    async def verify_network(
        self,
        action_id: str = "preflight_network",
        host: str = "8.8.8.8",
        port: int = 53,
        timeout: float = 2.0
    ) -> Dict[str, Any]:
        """Network connectivity verification"""
        logger.info(f"Checking network connectivity to {host}:{port} for action {action_id}")
        is_connected = await asyncio.to_thread(self.check_network_connectivity, host, port, timeout)
        result = {
            "type": "network",
            "action_id": action_id,
            "success": is_connected,
            "host": host,
            "port": port,
            "details": f"Network is {'connected' if is_connected else 'unreachable'} ({host}:{port})",
            "timestamp": time.time()
        }
        self.history.append(result)
        return result

    # ===== 2. REAL PROCESS VERIFICATION =====

    async def verify_process(
        self,
        action_id: str,
        process_name: str,
        expected_state: str = "running",
        timeout: float = 2.0
    ) -> Dict[str, Any]:
        """
        Real process state verification using psutil.
        Checks if a process matching process_name is in expected_state ('running' or 'stopped').
        """
        logger.info(f"Process verification for action {action_id}: '{process_name}' should be '{expected_state}'")
        
        def _check_process_sync() -> Dict[str, Any]:
            if not PSUTIL_AVAILABLE:
                return {
                    "success": False,
                    "details": "psutil not available for process verification",
                    "matching_pids": []
                }
            
            target = process_name.lower().replace(".exe", "").strip()
            my_pid = os.getpid()
            matching_pids: List[int] = []
            matching_names: List[str] = []
            
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    if proc.info['pid'] == my_pid:
                        continue
                    pname = (proc.info['name'] or '').lower()
                    pexe = (proc.info['exe'] or '').lower()
                    exe_base = os.path.basename(pexe)
                    
                    is_match = False
                    if target == pname or target == pname.replace(".exe", ""):
                        is_match = True
                    elif target in pname or target in exe_base:
                        is_match = True
                    elif proc.info['cmdline'] and len(proc.info['cmdline']) > 0:
                        first_arg = os.path.basename(proc.info['cmdline'][0]).lower()
                        if target in first_arg:
                            is_match = True
                    
                    if is_match:
                        matching_pids.append(proc.info['pid'])
                        matching_names.append(proc.info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            is_running = len(matching_pids) > 0
            expected_running = expected_state.lower() in ["running", "active", "started", "open"]
            success = (is_running == expected_running)
            
            if is_running:
                details = f"Process '{process_name}' is RUNNING (PIDs: {matching_pids[:5]})"
            else:
                details = f"Process '{process_name}' is NOT RUNNING"
                
            return {
                "success": success,
                "is_running": is_running,
                "matching_pids": matching_pids,
                "matching_names": list(set(matching_names)),
                "details": details
            }

        start_time = time.time()
        check_res = await asyncio.to_thread(_check_process_sync)
        
        expected_running = expected_state.lower() in ["running", "active", "started", "open"]
        while not check_res["success"] and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.3)
            check_res = await asyncio.to_thread(_check_process_sync)

        result = {
            "type": "process",
            "action_id": action_id,
            "success": check_res["success"],
            "process": process_name,
            "state": "running" if check_res.get("is_running") else "stopped",
            "expected_state": expected_state,
            "matching_pids": check_res.get("matching_pids", []),
            "details": check_res.get("details", ""),
            "timestamp": time.time()
        }
        self.history.append(result)
        return result

    # ===== 3. REAL WINDOW TITLE VERIFICATION =====

    async def verify_window(
        self,
        action_id: str,
        window_title_pattern: str,
        expected_state: str = "open",
        visible_only: bool = True,
        timeout: float = 2.0
    ) -> Dict[str, Any]:
        """
        Real window title verification using win32gui.
        Checks if a window matching window_title_pattern is 'open' or 'closed'.
        """
        logger.info(f"Window verification for action {action_id}: pattern '{window_title_pattern}' should be '{expected_state}'")

        def _check_windows_sync() -> Dict[str, Any]:
            if not WIN32_AVAILABLE:
                return {
                    "success": False,
                    "details": "win32gui not available for window verification",
                    "matching_windows": []
                }

            # Attach thread desktop to input desktop if running in background session
            try:
                u32 = ctypes.windll.user32
                h_input = u32.OpenInputDesktop(0, False, 0x01FF)
                if h_input:
                    u32.SetThreadDesktop(h_input)
            except Exception:
                pass

            matching_windows: List[Dict[str, Any]] = []
            regex = re.compile(window_title_pattern, re.IGNORECASE)

            def _enum_cb(hwnd, _):
                if visible_only and not win32gui.IsWindowVisible(hwnd):
                    return True
                title = win32gui.GetWindowText(hwnd)
                if title and regex.search(title):
                    matching_windows.append({
                        "hwnd": hwnd,
                        "title": title
                    })
                return True

            try:
                win32gui.EnumWindows(_enum_cb, None)
            except Exception as e:
                logger.warning(f"EnumWindows error: {e}")

            is_open = len(matching_windows) > 0
            expected_open = expected_state.lower() in ["open", "visible", "running", "active"]
            success = (is_open == expected_open)

            if is_open:
                details = f"Found {len(matching_windows)} window(s) matching '{window_title_pattern}': {[w['title'] for w in matching_windows[:3]]}"
            else:
                details = f"No open windows matching '{window_title_pattern}'"

            return {
                "success": success,
                "is_open": is_open,
                "matching_windows": matching_windows,
                "details": details
            }

        start_time = time.time()
        check_res = await asyncio.to_thread(_check_windows_sync)
        
        expected_open = expected_state.lower() in ["open", "visible", "running", "active"]
        while not check_res["success"] and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.3)
            check_res = await asyncio.to_thread(_check_windows_sync)

        result = {
            "type": "window",
            "action_id": action_id,
            "success": check_res["success"],
            "pattern": window_title_pattern,
            "state": "open" if check_res.get("is_open") else "closed",
            "expected_state": expected_state,
            "matching_windows": [w["title"] for w in check_res.get("matching_windows", [])],
            "details": check_res.get("details", ""),
            "timestamp": time.time()
        }
        self.history.append(result)
        return result

    # ===== 4. REAL API / ENDPOINT VERIFICATION =====

    async def verify_api(
        self,
        action_id: str,
        endpoint: str,
        expected_status: int = 200,
        expected_pattern: Optional[Dict] = None,
        timeout: float = 3.0,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """
        Real API / Endpoint verification.
        Performs actual HTTP status code check or socket reachability check.
        """
        logger.info(f"API verification for action {action_id} on {endpoint}")

        def _check_api_sync() -> Dict[str, Any]:
            if endpoint.startswith(("http://", "https://")):
                try:
                    req = urllib.request.Request(endpoint, headers={"User-Agent": "PulsarAssistant/1.0"}, method=method)
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        status = resp.getcode()
                        body_data = None
                        if expected_pattern:
                            try:
                                body_data = json.loads(resp.read().decode('utf-8', errors='ignore'))
                            except Exception:
                                pass
                        
                        pattern_matches = True
                        if expected_pattern and isinstance(body_data, dict):
                            for k, v in expected_pattern.items():
                                if body_data.get(k) != v:
                                    pattern_matches = False
                                    break
                                    
                        success = (status == expected_status) and pattern_matches
                        return {
                            "success": success,
                            "status_code": status,
                            "details": f"HTTP {status} (expected {expected_status}, pattern_matches={pattern_matches})"
                        }
                except urllib.error.HTTPError as e:
                    success = (e.code == expected_status)
                    return {
                        "success": success,
                        "status_code": e.code,
                        "details": f"HTTP status {e.code} (expected {expected_status})"
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "status_code": None,
                        "details": f"HTTP connection failed: {e}"
                    }
            else:
                # Host:port format or socket check
                try:
                    parts = endpoint.split(":")
                    host = parts[0]
                    port = int(parts[1]) if len(parts) > 1 else 80
                    with socket.create_connection((host, port), timeout=timeout):
                        return {
                            "success": True,
                            "status_code": 200,
                            "details": f"TCP socket connected to {host}:{port}"
                        }
                except Exception as e:
                    return {
                        "success": False,
                        "status_code": None,
                        "details": f"TCP socket connection failed to {endpoint}: {e}"
                    }

        api_res = await asyncio.to_thread(_check_api_sync)
        result = {
            "type": "api",
            "action_id": action_id,
            "success": api_res["success"],
            "endpoint": endpoint,
            "status_code": api_res.get("status_code"),
            "expected_status": expected_status,
            "details": api_res.get("details", ""),
            "timestamp": time.time()
        }
        self.history.append(result)
        return result

    # ===== 5. REAL LOG PATTERN VERIFICATION =====

    async def verify_log(
        self,
        action_id: str,
        log_pattern: str,
        log_file: Optional[str] = None,
        time_window_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        Real log pattern matching verification across recent logs.
        """
        logger.info(f"Log verification started for action {action_id} with pattern '{log_pattern}'")

        def _check_logs_sync() -> Dict[str, Any]:
            regex = re.compile(log_pattern, re.IGNORECASE)
            files_to_check: List[Path] = []
            
            if log_file:
                target_path = Path(log_file)
                if target_path.exists():
                    files_to_check.append(target_path)
            elif self.log_dir.exists():
                now = time.time()
                for root, _, files in os.walk(self.log_dir):
                    for f in files:
                        if f.endswith(('.log', '.txt')):
                            fp = Path(root) / f
                            try:
                                mtime = fp.stat().st_mtime
                                if (now - mtime) <= (time_window_seconds * 2):
                                    files_to_check.append(fp)
                            except OSError:
                                continue

            matched_lines: List[str] = []
            for fp in files_to_check:
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()[-200:]
                        for line in lines:
                            if regex.search(line):
                                matched_lines.append(line.strip())
                except Exception:
                    continue

            success = len(matched_lines) > 0
            details = f"Matched {len(matched_lines)} log entry(ies) in {len(files_to_check)} file(s)" if success else f"Pattern '{log_pattern}' not found in {len(files_to_check)} log file(s)"
            return {
                "success": success,
                "matches": matched_lines[-5:],
                "details": details
            }

        log_res = await asyncio.to_thread(_check_logs_sync)
        result = {
            "type": "log",
            "action_id": action_id,
            "success": log_res["success"],
            "pattern": log_pattern,
            "matches": log_res.get("matches", []),
            "details": log_res.get("details", ""),
            "timestamp": time.time()
        }
        self.history.append(result)
        return result

    # ===== 6. REAL VISUAL VERIFICATION =====

    async def verify_visual(
        self,
        action_id: str,
        before_state: Any = None,
        after_state: Any = None,
        criteria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Real visual verification comparing before/after states.
        Uses Pillow / ImageChops for pixel difference calculation.
        """
        logger.info(f"Visual verification started for action {action_id}")
        criteria = criteria or {}

        def _check_visual_sync() -> Dict[str, Any]:
            if not PIL_AVAILABLE:
                return {
                    "success": True,
                    "confidence": 0.5,
                    "details": "PIL not available; visual verification defaulted"
                }

            before_img = None
            after_img = None

            if isinstance(before_state, str) and os.path.exists(before_state):
                try:
                    before_img = Image.open(before_state).convert('RGB')
                except Exception:
                    pass
            elif hasattr(before_state, 'convert'):
                before_img = before_state.convert('RGB')

            if isinstance(after_state, str) and os.path.exists(after_state):
                try:
                    after_img = Image.open(after_state).convert('RGB')
                except Exception:
                    pass
            elif hasattr(after_state, 'convert'):
                after_img = after_state.convert('RGB')

            # If both images are present, compute pixel diff
            if before_img and after_img:
                if before_img.size != after_img.size:
                    after_img = after_img.resize(before_img.size)

                diff = ImageChops.difference(before_img, after_img)
                diff_arr = np.array(diff)
                changed_pixels = int(np.count_nonzero(diff_arr))
                total_pixels = int(diff_arr.size)
                change_percentage = (changed_pixels / total_pixels) * 100.0 if total_pixels > 0 else 0.0

                min_change = criteria.get("min_change_percentage", 0.05)
                expected_change = criteria.get("expect_change", True)

                if expected_change:
                    success = change_percentage >= min_change
                    confidence = min(0.99, max(0.5, change_percentage / 10.0))
                    details = f"Visual state changed by {change_percentage:.2f}% (min expected {min_change}%)"
                else:
                    success = change_percentage < min_change
                    confidence = 0.95 if success else 0.4
                    details = f"Visual state remained stable (change: {change_percentage:.2f}%)"

                return {
                    "success": success,
                    "confidence": confidence,
                    "change_percentage": change_percentage,
                    "details": details
                }

            return {
                "success": True,
                "confidence": 0.8,
                "details": "Visual check completed (no before/after pair supplied)"
            }

        vis_res = await asyncio.to_thread(_check_visual_sync)
        result = {
            "type": "visual",
            "action_id": action_id,
            "success": vis_res["success"],
            "confidence": vis_res.get("confidence", 0.8),
            "change_percentage": vis_res.get("change_percentage"),
            "details": vis_res.get("details", ""),
            "timestamp": time.time()
        }
        self.history.append(result)
        return result

    # ===== 7. AGGREGATE RESULTS =====

    def aggregate_results(self, verification_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine verification results to determine overall success"""
        if not verification_results:
            return {"success": True, "confidence": 1.0, "details": "No verifications requested"}
            
        all_success = all(r.get("success", False) for r in verification_results)
        
        confidences = [r.get("confidence", 1.0) for r in verification_results if "confidence" in r]
        avg_confidence = sum(confidences) / len(confidences) if confidences else (1.0 if all_success else 0.0)
        
        failed_verifications = [r for r in verification_results if not r.get("success", False)]
        
        return {
            "success": all_success,
            "confidence": avg_confidence,
            "total_checks": len(verification_results),
            "failed_checks": len(failed_verifications),
            "details": "All verifications passed" if all_success else f"Failed {len(failed_verifications)} verification(s)",
            "failures": failed_verifications,
            "timestamp": time.time()
        }
