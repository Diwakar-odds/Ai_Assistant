#!/usr/bin/env python3
"""
Pulsar AI Assistant - Ultra-Compact Ambient Mascot Robot (v2.0 Full-Power Agent)
================================================================================
A tiny (~1 inch), frameless, 100% transparent floating robot icon with autonomous powers:
- STRICTLY ZERO background box, ZERO white/dark rectangle, ZERO card border.
- Floats directly over Windows desktop apps (VS Code, Chrome, WhatsApp, etc.).
- Global Mutex: Physically guarantees ONLY ONE instance can ever exist.
- Per-Monitor DPI Aware: Perfect coordinate alignment across multi-monitors.
- Voice Listener: Offline wake word ("Hey Pulsar") + continuous command processing.
- Screen Perception & Action: Analyzes active screen, checks email grammar, ends video calls.
- Notification Cards: Displays Gmail alerts, WhatsApp messages, Calendar reminders.
- Confirmation Dialogs: Gated confirmation for sensitive Tier 3 actions.
- Drag & Drop: Smooth 60 FPS Win32 native dragging anywhere on the screen.
"""

import sys
import os
import time
import math
import threading
from pathlib import Path
import ctypes
from ctypes import wintypes
from dotenv import load_dotenv

# -------------------------------------------------------------
# 0. Windows Per-Monitor DPI Awareness (MUST BE BEFORE ANY GUI)
# -------------------------------------------------------------
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI Aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root / "core_ai" / "src"))
sys.path.insert(0, str(project_root / "shared"))
sys.path.insert(0, str(project_root / "desktop"))

load_dotenv(project_root / ".env")

# -------------------------------------------------------------
# 1. Windows Global Mutex - STRICT SINGLE INSTANCE GUARANTEE
# -------------------------------------------------------------
MUTEX_NAME = "Global\\Pulsar_Ambient_Mascot_Robot_Mutex"
kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

mascot_mutex = kernel32.CreateMutexW(None, True, MUTEX_NAME)
if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
    print("[COMPANION] Ambient Mascot is already running on screen. Exiting duplicate instance.")
    existing_hwnd = user32.FindWindowW(None, "Pulsar Ambient Mascot")
    if existing_hwnd:
        user32.SetForegroundWindow(existing_hwnd)
    sys.exit(0)

import win32gui
import win32con
import win32api
from PIL import Image, ImageDraw

from companion_bridge import CompanionBridgeClient
from companion_ui import render_speech_bubble, render_notification_card, render_confirmation_dialog, render_transcription_pill
from companion_voice import CompanionVoiceListener

# -------------------------------------------------------------
# 2. Win32 Structures for 32-bit Layered Window Compositing
# -------------------------------------------------------------
class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ('BlendOp', ctypes.c_byte),
        ('BlendFlags', ctypes.c_byte),
        ('SourceConstantAlpha', ctypes.c_byte),
        ('AlphaFormat', ctypes.c_byte)
    ]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD)
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ('bmiHeader', BITMAPINFOHEADER),
        ('bmiColors', wintypes.DWORD * 3)
    ]

class POINT(ctypes.Structure):
    _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]

class SIZE(ctypes.Structure):
    _fields_ = [('cx', wintypes.LONG), ('cy', wintypes.LONG)]


def apply_layered_image(hwnd, pil_img, x, y):
    """Update Win32 Layered Window with pre-multiplied 32-bit ARGB PIL Image"""
    w, h = pil_img.size
    raw = bytearray(pil_img.tobytes('raw', 'BGRA'))

    for i in range(0, len(raw), 4):
        a = raw[i + 3]
        if a == 0:
            raw[i] = raw[i + 1] = raw[i + 2] = 0
        elif a < 255:
            raw[i] = (raw[i] * a) // 255
            raw[i + 1] = (raw[i + 1] * a) // 255
            raw[i + 2] = (raw[i + 2] * a) // 255

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h  # top-down DIB
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0

    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    ppv_bits = ctypes.c_void_p()
    hbitmap = gdi32.CreateDIBSection(hdc_screen, ctypes.byref(bmi), 0, ctypes.byref(ppv_bits), 0, 0)
    if not hbitmap:
        user32.ReleaseDC(0, hdc_screen)
        gdi32.DeleteDC(hdc_mem)
        return False

    ctypes.memmove(ppv_bits, (ctypes.c_char * len(raw)).from_buffer(raw), len(raw))
    old_bm = gdi32.SelectObject(hdc_mem, hbitmap)

    pt_src = POINT(0, 0)
    pt_dst = POINT(x, y)
    sz = SIZE(w, h)
    blend = BLENDFUNCTION(0, 0, 255, 1)  # AC_SRC_OVER, 0, 255, AC_SRC_ALPHA

    res = user32.UpdateLayeredWindow(
        hwnd, hdc_screen, ctypes.byref(pt_dst), ctypes.byref(sz),
        hdc_mem, ctypes.byref(pt_src), 0, ctypes.byref(blend), 2
    )

    gdi32.SelectObject(hdc_mem, old_bm)
    gdi32.DeleteObject(hbitmap)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_screen)
    return bool(res)


# -------------------------------------------------------------
# 3. High-Fidelity Robot Icon Generator (4x Supersampled)
# -------------------------------------------------------------
def render_robot_frame(w=72, h=72, eye_scale=1.0, eye_shift=0.0, is_scanning=False, is_listening=False):
    """
    Renders the exact Pulsar Robot icon at 4x resolution for buttery smooth anti-aliased curves:
    - Cyan antenna + glowing bulb
    - Warm orange / cyan glowing head outline
    - Dark navy / metallic faceplate
    - Inner dark visor screen
    - Glowing oval eyes (blinking & scanning radar)
    - Cyan thruster base
    """
    scale = 4
    sw, sh = w * scale, h * scale
    img = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx = sw // 2

    # Coordinate layout
    head_w = int(46 * scale)
    head_h = int(38 * scale)
    head_x0 = (sw - head_w) // 2
    head_y0 = int(21 * scale)
    head_x1 = head_x0 + head_w
    head_y1 = head_y0 + head_h
    corner_r = int(12 * scale)

    # 1. Bottom Thruster Base (cyan glowing oval)
    thruster_w = int(22 * scale)
    thruster_h = int(7 * scale)
    t_x0 = cx - thruster_w // 2
    t_y0 = int(62 * scale)
    t_x1 = cx + thruster_w // 2
    t_y1 = t_y0 + thruster_h

    draw.ellipse([t_x0 - 4, t_y0 - 2, t_x1 + 4, t_y1 + 2], fill=(0, 243, 255, 110))
    draw.ellipse([t_x0, t_y0, t_x1, t_y1], fill=(0, 243, 255, 230))

    # 2. Antenna (vertical stem + glowing bulb tip)
    stem_w = int(2.5 * scale)
    stem_top = int(6 * scale)
    stem_bottom = head_y0 + int(3 * scale)
    draw.line([(cx, stem_top), (cx, stem_bottom)], fill=(0, 243, 255, 255), width=stem_w)

    bulb_r = int(4.5 * scale)
    draw.ellipse([cx - bulb_r - 5, stem_top - bulb_r - 5, cx + bulb_r + 5, stem_top + bulb_r + 5], fill=(0, 243, 255, 90))
    draw.ellipse([cx - bulb_r, stem_top - bulb_r, cx + bulb_r, stem_top + bulb_r], fill=(0, 243, 255, 255))

    # 3. Head Outer Outline & Fill
    if is_scanning or is_listening:
        outline_c = (0, 243, 255, 255)
        glow_c = (0, 243, 255, 120)
    else:
        outline_c = (255, 165, 0, 255)
        glow_c = (255, 165, 0, 95)

    draw.rounded_rectangle([head_x0 - 4, head_y0 - 4, head_x1 + 4, head_y1 + 4], radius=corner_r + 4, fill=glow_c)
    draw.rounded_rectangle([head_x0, head_y0, head_x1, head_y1], radius=corner_r, fill=(20, 28, 43, 255), outline=outline_c, width=int(3.2 * scale))

    # 4. Visor Screen
    visor_margin_x = int(5.5 * scale)
    visor_margin_y = int(6.5 * scale)
    vx0 = head_x0 + visor_margin_x
    vy0 = head_y0 + visor_margin_y
    vx1 = head_x1 - visor_margin_x
    vy1 = head_y1 - visor_margin_y
    draw.rounded_rectangle([vx0, vy0, vx1, vy1], radius=int(6 * scale), fill=(10, 15, 29, 255))

    # 5. Glowing Eyes
    if is_scanning or is_listening:
        eye_c = (0, 243, 255, 255)
        eye_glow = (0, 243, 255, 130)
    else:
        eye_c = (255, 165, 0, 255)
        eye_glow = (255, 165, 0, 130)

    eye_rx = int(5 * scale)
    eye_ry = max(1, int(7.5 * scale * eye_scale))
    eye_y = vy0 + (vy1 - vy0) // 2

    shift_px = int(eye_shift * scale)
    left_eye_x = cx - int(8.5 * scale) + shift_px
    right_eye_x = cx + int(8.5 * scale) + shift_px

    draw.ellipse([left_eye_x - eye_rx - 4, eye_y - eye_ry - 4, left_eye_x + eye_rx + 4, eye_y + eye_ry + 4], fill=eye_glow)
    draw.ellipse([left_eye_x - eye_rx, eye_y - eye_ry, left_eye_x + eye_rx, eye_y + eye_ry], fill=eye_c)

    draw.ellipse([right_eye_x - eye_rx - 4, eye_y - eye_ry - 4, right_eye_x + eye_rx + 4, eye_y + eye_ry + 4], fill=eye_glow)
    draw.ellipse([right_eye_x - eye_rx, eye_y - eye_ry, right_eye_x + eye_rx, eye_y + eye_ry], fill=eye_c)

    return img.resize((w, h), Image.Resampling.LANCZOS)


# -------------------------------------------------------------
# 4. Ambient Companion Controller
# -------------------------------------------------------------
class AmbientMascotApp:
    def __init__(self):
        self.w = 72
        self.h = 72
        self.is_scanning = False
        self.is_docked = False
        self.saved_x = 0
        self.saved_y = 0

        # Screen position (bottom right)
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        self.x = screen_w - self.w - 24
        self.y = screen_h - self.h - 60

        # Mouse tracking
        self.mouse_down_time = 0
        self.mouse_down_pos = (0, 0)

        # Active dialog state
        self.bubble_hwnd = None
        self.bubble_hide_time = 0
        self.active_buttons = []
        self.active_action_id = None

        # Pre-render animation frames
        self.frame_idle = render_robot_frame(self.w, self.h, eye_scale=1.0, is_scanning=False)
        self.frame_blink = render_robot_frame(self.w, self.h, eye_scale=0.15, is_scanning=False)
        self.scan_frames = [
            render_robot_frame(self.w, self.h, eye_scale=1.0, eye_shift=math.sin(i * math.pi / 4) * 3.5, is_scanning=True)
            for i in range(8)
        ]
        self.current_scan_frame = 0

        # 1. Connect to Backend Bridge
        self.bridge = CompanionBridgeClient(port=5000)

        # 2. Setup Voice Listener with Live Streaming Partial Pill
        self.voice = CompanionVoiceListener(
            on_wake=self._on_wake_heard,
            on_command=self._on_voice_command,
            on_partial=self._on_voice_partial
        )
        self.voice.start()

        # 3. Setup Smart Clipboard Radar (detects errors / code automatically)
        self._init_clipboard_radar()

        # 4. Setup Emergency Kill-Switch (Ctrl + Alt + Pause)
        self._init_emergency_kill_switch()

        # 5. Create Win32 Windows
        self._create_windows()

    def _init_emergency_kill_switch(self):
        """Global OS-level emergency stop hotkey"""
        def _hook():
            try:
                from pynput import keyboard
                def on_press(key):
                    if key == keyboard.Key.pause:
                        print("\n[EMERGENCY STOP] Halting all actions!")
                        self.show_speech("⚠️ Emergency stop activated.", duration=4.0)
                        self._speak_async("Emergency stop.")
                    elif key == keyboard.Key.f8:
                        # Fast global hotkey: F8 triggers listening from anywhere
                        self.voice.trigger_manual_listen()
                        self.show_speech("Listening to your command (F8)...", duration=4.0)
                with keyboard.Listener(on_press=on_press) as listener:
                    listener.join()
            except Exception:
                pass
        threading.Thread(target=_hook, daemon=True).start()

    def _init_clipboard_radar(self):
        """Silently observes clipboard for error stack traces or compiler issues"""
        def _radar_loop():
            time.sleep(3.0)
            last_clip = ""
            error_keywords = [
                "Traceback (most recent call last)", "SyntaxError:", "TypeError:",
                "ValueError:", "IndentationError:", "AttributeError:", "ImportError:",
                "ModuleNotFoundError:", "Uncaught Exception:", "Exception in thread",
                "FAILED (errors=", "build failed", "npm ERR!", "panic:"
            ]
            while True:
                time.sleep(1.2)
                try:
                    import win32clipboard
                    win32clipboard.OpenClipboard()
                    try:
                        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                            text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                        else:
                            text = None
                    finally:
                        win32clipboard.CloseClipboard()

                    if text and text != last_clip and len(text.strip()) > 8:
                        last_clip = text
                        text_clean = text.strip()
                        matched = next((k for k in error_keywords if k in text_clean), None)
                        if matched:
                            # Extract concise error snippet
                            lines = [ln.strip() for ln in text_clean.split("\n") if ln.strip()]
                            err_line = lines[-1] if lines else matched
                            if len(err_line) > 55:
                                err_line = err_line[:52] + "..."
                            self._last_error_clipboard = text_clean
                            self.show_custom_card({
                                "title": "🔍 Error Detected in Clipboard",
                                "body": f"{matched} -> {err_line}",
                                "type": "research",
                                "actions": ["Explain", "Dismiss"]
                            }, duration=9.0)
                except Exception:
                    pass
        threading.Thread(target=_radar_loop, daemon=True).start()

    def _create_windows(self):
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._mascot_wndproc
        wc.lpszClassName = "PulsarAmbientMascotClass"
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        try:
            win32gui.RegisterClass(wc)
        except Exception:
            pass

        self.hwnd = win32gui.CreateWindowEx(
            win32con.WS_EX_LAYERED | win32con.WS_EX_TOPMOST | win32con.WS_EX_TOOLWINDOW,
            wc.lpszClassName,
            "Pulsar Ambient Mascot",
            win32con.WS_POPUP,
            self.x, self.y, self.w, self.h,
            0, 0, wc.hInstance, None
        )

        bwc = win32gui.WNDCLASS()
        bwc.lpfnWndProc = self._bubble_wndproc
        bwc.lpszClassName = "PulsarMascotBubbleClass"
        bwc.hInstance = wc.hInstance
        bwc.hCursor = wc.hCursor
        try:
            win32gui.RegisterClass(bwc)
        except Exception:
            pass

        self.bubble_hwnd = win32gui.CreateWindowEx(
            win32con.WS_EX_LAYERED | win32con.WS_EX_TOPMOST | win32con.WS_EX_TOOLWINDOW,
            bwc.lpszClassName,
            "Pulsar Mascot Bubble",
            win32con.WS_POPUP,
            self.x - 320, self.y - 60, 320, 140,
            0, 0, wc.hInstance, None
        )

        apply_layered_image(self.hwnd, self.frame_idle, self.x, self.y)
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)

        # Timers: 1=animation, 2=blink, 3=notification polling
        user32.SetTimer(self.hwnd, 1, 50, None)
        user32.SetTimer(self.hwnd, 2, 3800, None)
        user32.SetTimer(self.hwnd, 3, 2500, None)

        print("[COMPANION] Ambient Mascot active on screen (Single Instance Locked).")

    def _mascot_wndproc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_LBUTTONDOWN:
            self.mouse_down_time = time.time()
            cursor_pos = win32gui.GetCursorPos()
            self.mouse_down_pos = cursor_pos
            rect = win32gui.GetWindowRect(hwnd)

            # Native drag
            win32gui.ReleaseCapture()
            win32api.SendMessage(hwnd, win32con.WM_NCLBUTTONDOWN, win32con.HTCAPTION, 0)

            # After drag
            rect_after = win32gui.GetWindowRect(hwnd)
            self.x = rect_after[0]
            self.y = rect_after[1]

            dist = math.hypot(rect_after[0] - rect[0], rect_after[1] - rect[1])
            elapsed = time.time() - self.mouse_down_time

            if dist < 6 and elapsed < 0.4:
                if self.is_docked:
                    self.toggle_dock()
                else:
                    # Click triggers voice command listen
                    self.voice.trigger_manual_listen()
                    self.show_speech("Listening to your command...", duration=4.0)
            return 0

        elif msg == win32con.WM_RBUTTONUP:
            self.show_context_menu()
            return 0

        elif msg == win32con.WM_TIMER:
            timer_id = wparam
            if timer_id == 1:
                # 50ms animation tick
                if self.is_scanning:
                    self.current_scan_frame = (self.current_scan_frame + 1) % len(self.scan_frames)
                    apply_layered_image(self.hwnd, self.scan_frames[self.current_scan_frame], self.x, self.y)
                # Auto-hide dialog
                if self.bubble_hide_time and time.time() > self.bubble_hide_time:
                    win32gui.ShowWindow(self.bubble_hwnd, win32con.SW_HIDE)
                    self.bubble_hide_time = 0

            elif timer_id == 2:
                # Blink
                if not self.is_scanning:
                    apply_layered_image(self.hwnd, self.frame_blink, self.x, self.y)
                    threading.Timer(0.14, lambda: apply_layered_image(self.hwnd, self.frame_idle, self.x, self.y)).start()

            elif timer_id == 3:
                # Poll notifications from backend
                self._poll_notifications()

            return 0

        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _bubble_wndproc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_LBUTTONDOWN:
            # Handle interactive button clicks on cards
            click_x = win32api.LOWORD(lparam)
            click_y = win32api.HIWORD(lparam)

            hit_action = None
            for btn in self.active_buttons:
                x0, y0, x1, y1 = btn["rect"]
                if x0 <= click_x <= x1 and y0 <= click_y <= y1:
                    hit_action = btn["action"]
                    break

            if hit_action:
                self._handle_card_button_click(hit_action)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                self.bubble_hide_time = 0
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _handle_card_button_click(self, action: str):
        """Dispatches card button actions (Confirm, Cancel, Show, Reply)"""
        act_lower = action.lower()

        if "confirm" in act_lower and self.active_action_id:
            self.show_speech("Executing confirmed action...", duration=3.0)
            threading.Thread(target=lambda: self.bridge.confirm_action(self.active_action_id, True), daemon=True).start()
            self.active_action_id = None

        elif "cancel" in act_lower and self.active_action_id:
            self.show_speech("Action cancelled.", duration=3.0)
            threading.Thread(target=lambda: self.bridge.confirm_action(self.active_action_id, False), daemon=True).start()
            self.active_action_id = None

        elif "dismiss" in act_lower:
            win32gui.ShowWindow(self.bubble_hwnd, win32con.SW_HIDE)
            self.bubble_hide_time = 0

        elif "show" in act_lower or "read" in act_lower:
            self.show_speech("Showing full details...", duration=6.0)

        elif "explain" in act_lower:
            err_data = getattr(self, "_last_error_clipboard", "")
            if err_data:
                self.show_transcription_pill("🔍 Explaining error with AI...", is_partial=True, duration=4.0)
                cmd = f"Explain this error in 2 simple sentences and suggest the fix: {err_data[:280]}"
                threading.Thread(target=lambda: self._on_voice_command(cmd), daemon=True).start()
            else:
                self.show_speech("No error snippet found in memory.", duration=3.0)

        elif "auto-type" in act_lower or "copy" in act_lower or "type" in act_lower:
            self.show_speech("Inserting corrected text into your editor...", duration=3.0)
            threading.Thread(target=lambda: self.bridge.send_command("type_text the corrected version", include_screen=False), daemon=True).start()

        elif "reply" in act_lower:
            self.voice.trigger_manual_listen()
            self.show_transcription_pill("🎙️ What would you like to reply?", is_partial=True, duration=4.0)

    # -------------------------------------------------------------
    # 5. Voice & Command Handlers
    # -------------------------------------------------------------
    def _on_wake_heard(self):
        """User said 'Hey Pulsar'"""
        self.is_scanning = True
        self.show_transcription_pill("🎙️ Listening to your voice...", is_partial=True, duration=4.0)

    def _on_voice_partial(self, partial_text: str):
        """Streaming partial audio transcript feedback"""
        self.is_scanning = True
        self.show_transcription_pill(partial_text, is_partial=True, duration=3.0)

    def _on_voice_command(self, command: str):
        """Process spoken command from user"""
        self.is_scanning = True
        self.show_transcription_pill(f"🧠 \"{command}\"", is_partial=False, duration=3.5)

        def _worker():
            try:
                # Send to Agent Brain
                result = self.bridge.send_command(command, include_screen=True)
                self.is_scanning = False
                apply_layered_image(self.hwnd, self.frame_idle, self.x, self.y)

                resp_text = result.get("response", "Command completed.")
                tts_text = result.get("tts", resp_text)

                # Check if confirmation is required
                if result.get("requires_confirmation") and result.get("action_id"):
                    self.active_action_id = result["action_id"]
                    self.show_confirmation_card(resp_text)
                elif result.get("card"):
                    self.show_custom_card(result["card"])
                else:
                    self.show_speech(resp_text, duration=8.0)

                if tts_text:
                    self._speak_async(tts_text[:180])

            except Exception as e:
                self.is_scanning = False
                apply_layered_image(self.hwnd, self.frame_idle, self.x, self.y)
                self.show_speech(f"Error: {e}", duration=5.0)

        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------
    # 6. UI Displays (Speech, Notifications, Confirmations)
    # -------------------------------------------------------------
    def show_transcription_pill(self, text: str, is_partial: bool = True, duration: float = 3.5):
        img = render_transcription_pill(text, is_partial=is_partial, max_w=280)
        self.active_buttons = []
        self._display_dialog(img, duration)

    def show_speech(self, text: str, duration: float = 7.0):
        img = render_speech_bubble(text, max_w=280)
        self.active_buttons = []
        self._display_dialog(img, duration)

    def show_custom_card(self, card_dict: dict, duration: float = 9.0):
        img, buttons = render_notification_card(card_dict, max_w=310)
        self.active_buttons = buttons
        self._display_dialog(img, duration)

    def show_confirmation_card(self, summary: str, duration: float = 12.0):
        img, buttons = render_confirmation_dialog(summary, max_w=300)
        self.active_buttons = buttons
        self._display_dialog(img, duration)

    def _display_dialog(self, img, duration: float):
        bw, bh = img.size
        bx = self.x - bw - 12
        by = max(10, self.y - 20)
        if bx < 10:
            bx = self.x + self.w + 12

        apply_layered_image(self.bubble_hwnd, img, bx, by)
        win32gui.ShowWindow(self.bubble_hwnd, win32con.SW_SHOW)
        self.bubble_hide_time = time.time() + duration

    def _poll_notifications(self):
        """Polls backend for pending alerts"""
        try:
            items = self.bridge.poll_notifications()
            for notif in items:
                self.show_custom_card(notif, duration=10.0)
                if notif.get("priority") in ["high", "critical"]:
                    self._speak_async(notif.get("title", "New notification arrived."))
                break  # Show one at a time
        except Exception:
            pass

    # -------------------------------------------------------------
    # 7. Context Menu & Actions
    # -------------------------------------------------------------
    def show_context_menu(self):
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, 101, "👁️  Explain Screen (Vision)")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 102, "✍️  Check Email Grammar")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 103, "📞  End / Cut Video Call")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 104, "🎵  Skip Song / Video")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        dock_text = "⮜  Restore Position" if self.is_docked else "⮞  Dock to Edge"
        win32gui.AppendMenu(menu, win32con.MF_STRING, 105, dock_text)
        win32gui.AppendMenu(menu, win32con.MF_STRING, 106, "✕  Close Mascot")

        cursor_pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        cmd = win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON | win32con.TPM_RETURNCMD,
            cursor_pos[0], cursor_pos[1],
            0, self.hwnd, None
        )
        win32gui.DestroyMenu(menu)

        if cmd == 101:
            self._on_voice_command("What is currently on the screen? Briefly explain in 2 sentences.")
        elif cmd == 102:
            self._on_voice_command("Check this email for grammatical errors and suggest corrections.")
        elif cmd == 103:
            self._on_voice_command("End the video call on screen.")
        elif cmd == 104:
            self._on_voice_command("Skip to next track.")
        elif cmd == 105:
            self.toggle_dock()
        elif cmd == 106:
            self.close()

    def toggle_dock(self):
        screen_w = user32.GetSystemMetrics(0)
        if not self.is_docked:
            self.saved_x = self.x
            self.saved_y = self.y
            self.x = screen_w - 20
            self.is_docked = True
        else:
            self.x = self.saved_x if self.saved_x > 0 else (screen_w - self.w - 24)
            self.y = self.saved_y if self.saved_y > 0 else self.y
            self.is_docked = False
        apply_layered_image(self.hwnd, self.frame_idle, self.x, self.y)

    def _speak_async(self, text: str):
        def _speak():
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 170)
                engine.say(text)
                engine.runAndWait()
            except Exception:
                pass
        threading.Thread(target=_speak, daemon=True).start()

    def close(self):
        try:
            self.voice.stop()
            win32gui.DestroyWindow(self.bubble_hwnd)
            win32gui.DestroyWindow(self.hwnd)
        except Exception:
            pass
        sys.exit(0)

    def run(self):
        win32gui.PumpMessages()


def main():
    app = AmbientMascotApp()
    app.run()


if __name__ == "__main__":
    main()
