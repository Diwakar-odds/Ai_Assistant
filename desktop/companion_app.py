#!/usr/bin/env python3
"""
Pulsar AI Assistant - Transparent Minimized 4D Orb Desktop Overlay
===================================================================
Click-through, 100% transparent Win32 layered 4D glowing particle orb overlay:
- Appears centered horizontally flush above the Windows taskbar (SPI_GETWORKAREA).
- Constantly visible whenever: overlay_enabled == True AND app_minimized == True
  (automatically hides when Pulsar WebUI / desktop window opens, reappears on minimize/hide/close).
- Shifts colors across all 5 states (idle, listening, speaking, processing, error)
  with real-time radial outer particle vibration matched to speaking intensity.
- WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
  guarantees zero rectangular background and 100% pass-through clicks to underlying apps.
"""

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import ctypes
from ctypes import wintypes
import math
from pathlib import Path
import sys
import threading
import time
from typing import Dict, Optional, Tuple

import numpy as np
from dotenv import load_dotenv
from PIL import Image

# Windows Per-Monitor DPI Awareness (must happen before GUI metrics/windows)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

if getattr(sys, 'frozen', False):
    project_root = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)).resolve()
else:
    project_root = Path(__file__).resolve().parent.parent
for p in (
    project_root,
    project_root / "backend",
    project_root / "core_ai" / "src",
    project_root / "shared",
    project_root / "desktop",
):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

try:
    from settings_manager import get_env_file
    _c_env = get_env_file()
    if _c_env.exists():
        load_dotenv(_c_env, override=False)
    else:
        load_dotenv(project_root / ".env", override=False)
except Exception:
    load_dotenv(project_root / ".env", override=False)

import win32api
import win32con
import win32gui

from companion_bridge import CompanionBridgeClient
from companion_voice import CompanionVoiceListener

try:
    import socketio as sio_lib

    SOCKETIO_CLIENT_AVAILABLE = True
except Exception:
    sio_lib = None
    SOCKETIO_CLIENT_AVAILABLE = False

MUTEX_NAME = "Global\\Pulsar_Ambient_Mascot_Robot_Mutex"
APP_LAUNCHER_MUTEX_NAME = "Local\\Pulsar_AI_Desktop_App_Mutex"
WINDOW_TITLE = "Pulsar 4D Orb Overlay"
try:
    _env_orb = int(os.environ.get("PULSAR_ORB_SIZE", "136"))
    DEFAULT_ORB_SIZE = max(96, min(320, _env_orb))
except ValueError:
    DEFAULT_ORB_SIZE = 136

_SCREEN_REQUEST_PHRASES = (
    "screenshot",
    "screen shot",
    "on my screen",
    "on this screen",
    "my screen",
    "this screen",
    "the screen",
    "screen dekho",
    "screen padho",
    "screen check",
    "mere screen",
    "screen pe",
    "screen par",
    "kya dikh raha",
    "what is on screen",
    "what's on screen",
    "what is on my screen",
    "what's on my screen",
    "look at my screen",
    "look at the screen",
    "see my screen",
    "check email grammar",
    "check grammar",
    "grammar check",
    "check spelling",
    "explain this code",
    "explain code on screen",
    "read this pdf",
    "summarize pdf",
    "summarize this pdf",
    "end video call",
    "end call",
    "cut call",
    "call kaat",
    "disconnect call",
    "स्क्रीन",
    "स्क्रीनशॉट",
    "क्या दिख रहा",
    "ग्रामर",
    "पीडीएफ",
)


def command_requests_screen(command: str) -> bool:
    """Return True only when user explicitly asks to inspect or act on the screen."""
    raw = (command or "").strip().lower()
    if not raw:
        return False
    return any(phrase in raw for phrase in _SCREEN_REQUEST_PHRASES)

WS_EX_NOACTIVATE = getattr(win32con, "WS_EX_NOACTIVATE", 0x08000000)
SPI_GETWORKAREA = 0x0030
DWMWA_CLOAKED = 14
_EXCLUDED_WINDOW_HINTS = (
    "pulsar 4d orb overlay",
    "visual studio code",
    "antigravity",
    "powershell",
    "command prompt",
    "windows terminal",
    "cmd.exe",
)

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_byte),
        ("BlendFlags", ctypes.c_byte),
        ("SourceConstantAlpha", ctypes.c_byte),
        ("AlphaFormat", ctypes.c_byte),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", wintypes.LONG), ("cy", wintypes.LONG)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


# ------------------------------------------------------------------
# 5-State Color & Motion Configuration (matches WebUI Three.js Orb)
# ------------------------------------------------------------------
ORB_STATE_CONFIGS: Dict[str, Dict[str, object]] = {
    "idle": {
        "primary": np.array([37.0, 99.0, 235.0]),     # Cobalt Blue
        "secondary": np.array([124.0, 58.0, 237.0]),  # Indigo Violet
        "accent": np.array([192.0, 38.0, 211.0]),     # Soft Magenta
        "speed": 0.65,
        "wave_amp": 0.08,
        "particle_vib": 0.03,
        "jagged": 0.0,
        "swirl": 0.14,
    },
    "listening": {
        "primary": np.array([0.0, 243.0, 255.0]),     # Electric Cyan
        "secondary": np.array([59.0, 130.0, 246.0]),  # Vivid Azure
        "accent": np.array([168.0, 85.0, 247.0]),     # Violet
        "speed": 1.35,
        "wave_amp": 0.14,
        "particle_vib": 0.10,
        "jagged": 0.0,
        "swirl": 0.30,
    },
    "speaking": {
        "primary": np.array([0.0, 212.0, 255.0]),     # Sky Cyan
        "secondary": np.array([139.0, 92.0, 246.0]),  # Electric Purple
        "accent": np.array([236.0, 72.0, 153.0]),     # Neon Pink-Magenta
        "speed": 1.60,
        "wave_amp": 0.17,
        "particle_vib": 0.12,
        "jagged": 0.0,
        "swirl": 0.34,
    },
    "processing": {
        "primary": np.array([245.0, 158.0, 11.0]),    # Amber Gold
        "secondary": np.array([249.0, 115.0, 22.0]),  # Warm Orange
        "accent": np.array([139.0, 92.0, 246.0]),     # Cosmic Violet
        "speed": 2.25,
        "wave_amp": 0.14,
        "particle_vib": 0.09,
        "jagged": 0.10,
        "swirl": 1.25,
    },
    "error": {
        "primary": np.array([239.0, 68.0, 68.0]),     # Crimson Red
        "secondary": np.array([249.0, 115.0, 22.0]),  # Ember Orange
        "accent": np.array([251.0, 113.0, 133.0]),    # Hot Rose Alert
        "speed": 2.90,
        "wave_amp": 0.20,
        "particle_vib": 0.18,
        "jagged": 1.0,
        "swirl": 0.55,
    },
}


def compute_overlay_visibility(overlay_enabled: bool, app_minimized: bool, orb_state: str = "idle") -> bool:
    """Constant visibility gate: show whenever overlay is enabled and WebUI/app is minimized or hidden."""
    return bool(overlay_enabled and app_minimized)


def get_workarea_bottom_center_coords(
    width: int = DEFAULT_ORB_SIZE,
    height: int = DEFAULT_ORB_SIZE,
    bottom_margin: int = 8,
) -> Tuple[int, int]:
    """Compute bottom-center screen coordinates sitting flush along the top of the Windows taskbar."""
    work_rect = RECT()
    screen_w = int(user32.GetSystemMetrics(0) or 1920)
    screen_h = int(user32.GetSystemMetrics(1) or 1080)
    ok = bool(user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(work_rect), 0))
    if ok and (work_rect.right - work_rect.left) > width and (work_rect.bottom - work_rect.top) > height:
        work_w = work_rect.right - work_rect.left
        x = int(work_rect.left + (work_w - width) // 2)
        y = max(0, min(screen_h - height, int(work_rect.bottom - height - bottom_margin)))
        return x, y

    x = max(0, (screen_w - width) // 2)
    y = max(0, min(screen_h - height, int(screen_h - 48 - height - bottom_margin)))
    return x, y


def detect_webui_window_open() -> bool:
    """Detect whether the Pulsar WebUI/desktop app window is currently open & un-minimized on desktop."""
    found = [False]
    dwmapi = getattr(ctypes.windll, "dwmapi", None)
    enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def _callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title_l = buf.value.strip().lower()
        if not title_l or "pulsar ai assistant" not in title_l:
            return True
        if any(hint in title_l for hint in _EXCLUDED_WINDOW_HINTS):
            return True

        if dwmapi is not None:
            cloaked = ctypes.c_int(0)
            hr = dwmapi.DwmGetWindowAttribute(
                hwnd,
                DWMWA_CLOAKED,
                ctypes.byref(cloaked),
                ctypes.sizeof(cloaked),
            )
            if hr == 0 and cloaked.value != 0:
                return True

        rect = RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            if (rect.right - rect.left) < 120 or (rect.bottom - rect.top) < 120:
                return True

        found[0] = True
        return False

    try:
        user32.EnumWindows(enum_proc_type(_callback), 0)
    except Exception:
        return False
    return bool(found[0])


def apply_layered_image(hwnd, pil_img: Image.Image, x: int, y: int) -> bool:
    """Update Win32 layered window with vectorized premultiplied 32-bit BGRA buffer."""
    w, h = pil_img.size
    rgba = np.asarray(pil_img.convert("RGBA"), dtype=np.uint8)
    alpha_f = rgba[:, :, 3].astype(np.uint16)

    bgra = np.empty_like(rgba)
    bgra[:, :, 0] = ((rgba[:, :, 2].astype(np.uint16) * alpha_f) // 255).astype(np.uint8)
    bgra[:, :, 1] = ((rgba[:, :, 1].astype(np.uint16) * alpha_f) // 255).astype(np.uint8)
    bgra[:, :, 2] = ((rgba[:, :, 0].astype(np.uint16) * alpha_f) // 255).astype(np.uint8)
    bgra[:, :, 3] = rgba[:, :, 3]
    raw = bgra.tobytes()

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

    ctypes.memmove(ppv_bits, raw, len(raw))
    old_bm = gdi32.SelectObject(hdc_mem, hbitmap)

    pt_src = POINT(0, 0)
    pt_dst = POINT(int(x), int(y))
    sz = SIZE(w, h)
    blend = BLENDFUNCTION(0, 0, 255, 1)  # AC_SRC_OVER, 0, 255, AC_SRC_ALPHA

    res = user32.UpdateLayeredWindow(
        hwnd,
        hdc_screen,
        ctypes.byref(pt_dst),
        ctypes.byref(sz),
        hdc_mem,
        ctypes.byref(pt_src),
        0,
        ctypes.byref(blend),
        2,
    )

    gdi32.SelectObject(hdc_mem, old_bm)
    gdi32.DeleteObject(hbitmap)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_screen)
    return bool(res)


class ParticleOrbRenderer:
    """Vectorized 3D-projected 4D wireframe + vibrating outer particle orb renderer."""

    def __init__(self, size: int = DEFAULT_ORB_SIZE, num_particles: int = 280):
        self.size = size
        self.half = float(size) / 2.0
        self.base_radius = float(size) * 0.31
        self.persp_dist = self.base_radius * 4.0

        # Smoothed transition state (float32 for high-throughput CPU SIMD at 30+ FPS)
        init_cfg = ORB_STATE_CONFIGS["idle"]
        self.cur_primary = init_cfg["primary"].astype(np.float32)
        self.cur_secondary = init_cfg["secondary"].astype(np.float32)
        self.cur_accent = init_cfg["accent"].astype(np.float32)
        self.cur_audio = 0.0
        self.cur_wave_amp = float(init_cfg["wave_amp"])
        self.cur_vib = float(init_cfg["particle_vib"])
        self.cur_jagged = float(init_cfg["jagged"])
        self.cur_swirl = float(init_cfg["swirl"])
        self.phase_time = 0.0

        # 1. Outer vibrating particle halo on Fibonacci sphere
        idx = np.arange(num_particles, dtype=np.float32)
        golden = np.float32(math.pi * (3.0 - math.sqrt(5.0)))
        y = np.float32(1.0) - (idx / np.float32(max(1, num_particles - 1))) * np.float32(2.0)
        r = np.sqrt(np.maximum(np.float32(0.0), np.float32(1.0) - y * y))
        theta = golden * idx
        self.p_dir = np.column_stack((np.cos(theta) * r, y, np.sin(theta) * r)).astype(np.float32)
        self.p_phases = ((idx * np.float32(0.61803398875)) * np.float32(2.0 * math.pi)).astype(np.float32)
        ar_idx = np.arange(num_particles)
        self.p_outer = np.where((ar_idx % 3) == 0, 1.0, 0.48).astype(np.float32)
        self.p_base_scale = np.where((ar_idx % 3) == 0, 1.06, 0.99).astype(np.float32)

        # 2. Structured latitude-longitude quad mesh grid for continuous glowing wireframe curves
        self.grid_lat = 12
        self.grid_lon = 18
        lat_angles = np.linspace(0.20, math.pi - 0.20, self.grid_lat, dtype=np.float32)
        lon_angles = np.linspace(0.0, 2.0 * math.pi, self.grid_lon, endpoint=False, dtype=np.float32)
        phi_g, th_g = np.meshgrid(lat_angles, lon_angles, indexing="ij")
        self.g_dir = np.stack(
            (np.sin(phi_g) * np.cos(th_g), np.cos(phi_g), np.sin(phi_g) * np.sin(th_g)),
            axis=-1,
        ).reshape(-1, 3).astype(np.float32)
        self.seg_t = np.linspace(0.0, 1.0, 11, dtype=np.float32)[None, :, None]
        self.seg_1mt = np.float32(1.0) - self.seg_t

        # 3. Precompute radial vignette + crystal-clear see-through core masks
        #    (keep center ~90% transparent so windows/text underneath remain clearly readable)
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
        dx = (xx - self.half) / np.float32(max(1.0, self.half - 6.0))
        dy = (yy - self.half) / np.float32(max(1.0, self.half - 6.0))
        dist_norm = np.sqrt(dx * dx + dy * dy)
        self.edge_mask = np.clip((np.float32(1.0) - dist_norm) * np.float32(5.0), 0.0, 1.0).astype(np.float32)

        r_sphere = np.sqrt((xx - self.half) ** 2 + (yy - self.half) ** 2) / np.float32(max(1.0, self.base_radius))
        core_silhouette = np.clip((np.float32(1.03) - r_sphere) / np.float32(0.22), 0.0, 1.0)
        self.core_body_alpha = (np.power(core_silhouette, 1.35) * np.float32(0.03) * self.edge_mask).astype(np.float32)
        self.one_minus_core_a = (np.float32(1.0) - self.core_body_alpha).astype(np.float32)
        self.core_fresnel = (np.power(np.clip(r_sphere, 0.0, 1.0), 2.0) * core_silhouette).astype(np.float32)
        self.core_aura = (np.exp(-np.square(r_sphere / np.float32(0.75))) * np.float32(0.05) * self.edge_mask).astype(np.float32)

        aura_mix_row = np.clip(np.float32(0.5) + np.float32(0.48) * dx[0, :], np.float32(0.0), np.float32(1.0))
        self.aura_w0_row = (np.float32(1.0) - aura_mix_row)[None, None, :].astype(np.float32)  # (1, 1, size)
        self.aura_w1_row = aura_mix_row[None, None, :].astype(np.float32)
        self.core_ambient_prem = (
            np.array([0.005, 0.01, 0.02], dtype=np.float32)[:, None, None] * self.core_body_alpha[None, :, :]
        ).astype(np.float32)
        self.fresnel_base_ca = ((np.float32(0.08) + np.float32(0.38) * self.core_fresnel) * self.core_body_alpha).astype(np.float32)
        self._buf = np.empty((3, size, size), dtype=np.float32)
        self._tmp2d = np.empty((size, size), dtype=np.float32)

    def _accumulate_all_splats(self, flat_buf: np.ndarray, idx_list, col_list):
        """Single-pass C-level bincount accumulation into channel-first (3, size*size) buffer."""
        if not idx_list:
            return
        all_idx = idx_list[0] if len(idx_list) == 1 else np.concatenate(idx_list)
        all_col = col_list[0] if len(col_list) == 1 else np.concatenate(col_list, axis=0)
        n_pix = self.size * self.size
        for ch in range(3):
            flat_buf[ch] += np.bincount(all_idx, weights=all_col[:, ch], minlength=n_pix)

    def render_frame(self, state: str = "idle", audio_level: float = 0.0, dt: float = 0.03) -> Image.Image:
        """Render one 32-bit RGBA transparent 4D orb frame for state & voice level."""
        cfg = ORB_STATE_CONFIGS.get(state, ORB_STATE_CONFIGS["idle"])
        lerp = np.float32(min(1.0, max(0.05, dt * 8.0)))

        self.cur_primary += (cfg["primary"].astype(np.float32) - self.cur_primary) * lerp
        self.cur_secondary += (cfg["secondary"].astype(np.float32) - self.cur_secondary) * lerp
        self.cur_accent += (cfg["accent"].astype(np.float32) - self.cur_accent) * lerp
        self.cur_wave_amp += (float(cfg["wave_amp"]) - self.cur_wave_amp) * float(lerp)
        self.cur_vib += (float(cfg["particle_vib"]) - self.cur_vib) * float(lerp)
        self.cur_jagged += (float(cfg["jagged"]) - self.cur_jagged) * float(lerp)
        self.cur_swirl += (float(cfg["swirl"]) - self.cur_swirl) * float(lerp)

        target_audio = max(0.0, min(1.0, float(audio_level) / 100.0))
        a_lerp = 0.45 if target_audio > self.cur_audio else 0.20
        self.cur_audio += (target_audio - self.cur_audio) * a_lerp

        speed = float(cfg["speed"]) + self.cur_audio * 1.1
        self.phase_time += dt * speed
        t = np.float32(self.phase_time)

        # Rotation matrix
        ry = float(t) * (0.42 + self.cur_swirl * 0.55)
        rx = 0.22 * math.sin(float(t) * 0.45)
        cy, sy = math.cos(ry), math.sin(ry)
        cx, sx = math.cos(rx), math.sin(rx)
        rot_y = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]], dtype=np.float32)
        rot_x = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]], dtype=np.float32)
        rot = rot_x @ rot_y

        p_norm = (self.cur_primary * np.float32(1.0 / 255.0))[:, None, None]
        a_norm = (self.cur_accent * np.float32(1.0 / 255.0))[:, None, None]
        aura_row = (p_norm * self.aura_w0_row + a_norm * self.aura_w1_row).astype(np.float32)  # (3, 1, size)
        buf = self._buf
        np.multiply(aura_row, (self.core_aura * np.float32(0.55 + self.cur_audio * 0.35))[None, :, :], out=buf)
        flat_buf = buf.reshape(3, -1)

        splat_indices = []
        splat_colors = []
        card_offsets = (-1, 1, -self.size, self.size)
        diag_offsets = (-self.size - 1, -self.size + 1, self.size - 1, self.size + 1)

        f0 = np.float32(0.0)
        f1 = np.float32(1.0)

        # 1. Project & queue continuous 4D wireframe quad lattice curves
        r_g = self.g_dir @ rot.T
        wave_g = (
            np.float32(0.55) * np.sin(np.float32(3.2) * r_g[:, 0] + np.float32(1.6) * t) * np.cos(np.float32(3.0) * r_g[:, 1] - np.float32(1.2) * t)
            + np.float32(0.45) * np.sin(np.float32(4.4) * r_g[:, 2] + np.float32(2.2) * t + np.float32(1.8) * r_g[:, 0])
        )
        if self.cur_jagged > 0.01:
            wave_g += np.float32(self.cur_jagged * 0.65) * np.abs(np.sin(np.float32(9.5) * r_g[:, 0] + np.float32(7.0) * t))

        disp_g = np.float32(0.92) + wave_g * np.float32(self.cur_wave_amp + self.cur_audio * 0.11)
        world_g = r_g * (np.float32(self.base_radius) * disp_g[:, None])
        persp_g = np.float32(self.persp_dist) / np.maximum(np.float32(self.persp_dist * 0.45), np.float32(self.persp_dist) - world_g[:, 2])
        fx = (np.float32(self.half) + world_g[:, 0] * persp_g).reshape(self.grid_lat, self.grid_lon)
        fy = (np.float32(self.half) + world_g[:, 1] * persp_g).reshape(self.grid_lat, self.grid_lon)

        depth_g = np.clip((r_g[:, 2] + np.float32(1.15)) * np.float32(0.50), np.float32(0.20), f1)
        ridge_g = np.clip((wave_g + np.float32(0.25)) * np.float32(0.55), f0, f1)
        sweep_g = np.clip(np.float32(0.5) + np.float32(0.52) * r_g[:, 0] - np.float32(0.18) * r_g[:, 1] + np.float32(0.15) * wave_g, f0, f1)
        s1_g = np.clip(sweep_g * np.float32(2.0), f0, f1)[:, None]
        s2_g = np.clip((sweep_g - np.float32(0.5)) * np.float32(2.0), f0, f1)[:, None]
        cols_g = self.cur_primary * (f1 - s1_g) + self.cur_secondary * s1_g
        cols_g = cols_g * (f1 - s2_g) + self.cur_accent * s2_g
        cols_g = (cols_g * np.float32(1.0 / 255.0)) * (depth_g * (np.float32(0.36 + self.cur_audio * 0.28) + np.float32(0.42) * ridge_g))[:, None]
        cols_grid = cols_g.reshape(self.grid_lat, self.grid_lon, 3)

        pts_grid = np.stack((fx, fy), axis=-1)
        seg_a = np.concatenate((pts_grid.reshape(-1, 2), pts_grid[:-1, :, :].reshape(-1, 2)), axis=0)
        seg_b = np.concatenate((np.roll(pts_grid, -1, axis=1).reshape(-1, 2), pts_grid[1:, :, :].reshape(-1, 2)), axis=0)
        col_a = np.concatenate((cols_grid.reshape(-1, 3), cols_grid[:-1, :, :].reshape(-1, 3)), axis=0)
        col_b = np.concatenate((np.roll(cols_grid, -1, axis=1).reshape(-1, 3), cols_grid[1:, :, :].reshape(-1, 3)), axis=0)

        pts = (seg_a[:, None, :] * self.seg_1mt + seg_b[:, None, :] * self.seg_t).reshape(-1, 2)
        seg_cols = (col_a[:, None, :] * self.seg_1mt + col_b[:, None, :] * self.seg_t).reshape(-1, 3)

        lx = np.rint(pts[:, 0]).astype(np.int32)
        ly = np.rint(pts[:, 1]).astype(np.int32)
        l_valid = (lx >= 3) & (lx < self.size - 3) & (ly >= 3) & (ly < self.size - 3)
        if np.any(l_valid):
            lf0 = ly[l_valid] * self.size + lx[l_valid]
            lvc = seg_cols[l_valid]
            l_main = lvc * np.float32(0.54)
            l_aa = lvc * np.float32(0.11)
            splat_indices.append(lf0)
            splat_colors.append(l_main)
            for off in card_offsets:
                splat_indices.append(lf0 + off)
                splat_colors.append(l_aa)

        # 2. Project & queue outer glowing vibrating particle halo
        r_p = self.p_dir @ rot.T
        wave_p = (
            np.float32(0.55) * np.sin(np.float32(3.2) * r_p[:, 0] + np.float32(1.6) * t) * np.cos(np.float32(3.0) * r_p[:, 1] - np.float32(1.2) * t)
            + np.float32(0.45) * np.sin(np.float32(4.4) * r_p[:, 2] + np.float32(2.2) * t + np.float32(1.8) * r_p[:, 0])
        )
        if self.cur_jagged > 0.01:
            wave_p += np.float32(self.cur_jagged * 0.65) * np.abs(np.sin(np.float32(9.5) * r_p[:, 0] + np.float32(7.0) * t))

        osc = np.float32(0.55) * np.sin(np.float32(18.0) * t + self.p_phases * np.float32(3.0)) + np.float32(0.45) * np.cos(np.float32(11.0) * t - self.p_phases * np.float32(2.0))
        vib_amp = np.float32(self.cur_vib) + np.float32(self.cur_audio) * (np.float32(0.28) + np.float32(0.24) * self.p_outer)
        rad_vib = osc * vib_amp + np.float32(self.cur_audio * 0.16) * self.p_outer
        if self.cur_jagged > 0.01:
            rad_vib += np.sin(np.float32(28.0) * t + self.p_phases) * np.float32(self.cur_jagged * 0.045)

        disp_p = self.p_base_scale + wave_p * np.float32(self.cur_wave_amp + self.cur_audio * 0.10) + rad_vib
        world_p = r_p * (np.float32(self.base_radius) * disp_p[:, None])
        persp_p = np.float32(self.persp_dist) / np.maximum(np.float32(self.persp_dist * 0.45), np.float32(self.persp_dist) - world_p[:, 2])
        px = np.rint(np.float32(self.half) + world_p[:, 0] * persp_p).astype(np.int32)
        py = np.rint(np.float32(self.half) + world_p[:, 1] * persp_p).astype(np.int32)

        depth_p = np.clip((r_p[:, 2] + np.float32(1.15)) * np.float32(0.52), np.float32(0.24), f1)
        sweep_p = np.clip(np.float32(0.5) + np.float32(0.52) * r_p[:, 0] - np.float32(0.18) * r_p[:, 1] + np.float32(0.15) * wave_p, f0, f1)
        s1_p = np.clip(sweep_p * np.float32(2.0), f0, f1)[:, None]
        s2_p = np.clip((sweep_p - np.float32(0.5)) * np.float32(2.0), f0, f1)[:, None]
        cols_p = self.cur_primary * (f1 - s1_p) + self.cur_secondary * s1_p
        cols_p = cols_p * (f1 - s2_p) + self.cur_accent * s2_p
        cols_p = (cols_p * np.float32(1.0 / 255.0)) * (depth_p * np.float32(0.82 + self.cur_audio * 0.85))[:, None]

        p_valid = (px >= 3) & (px < self.size - 3) & (py >= 3) & (py < self.size - 3)
        if np.any(p_valid):
            pf0 = py[p_valid] * self.size + px[p_valid]
            pvc = cols_p[p_valid]
            p_soft = pvc * np.float32(0.52 + self.cur_audio * 0.28)
            p_dim = pvc * np.float32(0.20 + self.cur_audio * 0.14)
            splat_indices.append(pf0)
            splat_colors.append(pvc)
            for off in card_offsets:
                splat_indices.append(pf0 + off)
                splat_colors.append(p_soft)
            for off in diag_offsets:
                splat_indices.append(pf0 + off)
                splat_colors.append(p_dim)

        self._accumulate_all_splats(flat_buf, splat_indices, splat_colors)

        # 3. Channel-first SIMD compositing -> straight RGBA
        raw_max = self._tmp2d
        np.maximum(buf[0], buf[1], out=raw_max)
        np.maximum(raw_max, buf[2], out=raw_max)
        glow_int = np.clip(raw_max, f0, f1)
        scale = (glow_int * self.edge_mask) / np.maximum(raw_max, np.float32(1e-5))
        core_white = np.clip((raw_max - np.float32(0.85)) * np.float32(0.48), f0, np.float32(0.65))
        buf *= (scale * (f1 - core_white))[None, :, :]
        buf += (glow_int * core_white * self.edge_mask)[None, :, :]

        fresnel_k = self.fresnel_base_ca + np.float32(0.12 * self.cur_audio) * self.core_body_alpha
        buf += aura_row * fresnel_k[None, :, :]
        buf += self.core_ambient_prem

        out_a = np.clip(self.core_body_alpha + glow_int * self.one_minus_core_a, f0, f1) * self.edge_mask
        np.minimum(buf, out_a[None, :, :], out=buf)

        inv_a_255 = np.where(out_a > np.float32(1e-4), np.float32(255.0) / np.maximum(out_a, np.float32(1e-4)), f0)
        buf *= inv_a_255[None, :, :]
        np.clip(buf, f0, np.float32(255.0), out=buf)

        rgba_out = np.empty((self.size, self.size, 4), dtype=np.uint8)
        rgba_out[:, :, 0] = buf[0].astype(np.uint8)
        rgba_out[:, :, 1] = buf[1].astype(np.uint8)
        rgba_out[:, :, 2] = buf[2].astype(np.uint8)
        rgba_out[:, :, 3] = np.clip(out_a * np.float32(255.0), f0, np.float32(255.0)).astype(np.uint8)
        return Image.fromarray(rgba_out)


class AmbientMascotApp:
    """Click-through transparent minimized 4D orb overlay & wake-word daemon."""

    def __init__(self, acquire_mutex: bool = True, port: Optional[int] = None):
        if acquire_mutex:
            self._acquire_single_instance()

        self.port = int(port or os.environ.get("PULSAR_PORT") or os.environ.get("PORT") or 5000)
        self.w = DEFAULT_ORB_SIZE
        self.h = DEFAULT_ORB_SIZE
        self.x, self.y = get_workarea_bottom_center_coords(self.w, self.h)

        # Synchronized overlay state (default app_minimized=True until WebUI window detected open)
        self._state_lock = threading.Lock()
        self.overlay_enabled = True
        self.app_minimized = not detect_webui_window_open()
        self.always_wake_enabled = True
        try:
            from settings_manager import get_tts_config
            _init_tts = get_tts_config()
        except Exception:
            _init_tts = {}
        self.tts_enabled = bool(_init_tts.get("enabled", True))
        self.tts_voice_id = str(_init_tts.get("voice_id") or "hi-IN-SwaraNeural").strip() or "hi-IN-SwaraNeural"
        self.orb_state = "idle"
        self.audio_level = 0.0
        self.webui_mic_active = False
        self.is_tts_speaking = False
        self.remote_tts_speaking = False
        self._remote_tts_cooldown_until = 0.0
        self._suppress_cooldown_until = 0.0
        self._currently_visible = False
        self._error_until = 0.0
        self._last_level_emit = 0.0
        self._last_webui_open: Optional[bool] = not self.app_minimized

        self.sio = None
        self.sio_connected = False
        self._stop_event = threading.Event()
        self._tts_abort_event = threading.Event()
        self._speak_sync_lock = threading.Lock()
        self._active_pyttsx3 = None
        self._last_http_poll = 0.0
        self.tray_icon = None

        self.renderer = ParticleOrbRenderer(size=self.w, num_particles=280)
        self.bridge = CompanionBridgeClient(port=self.port)

        self.voice = CompanionVoiceListener(
            on_wake=self._on_wake_heard,
            on_wake_ack=self._on_wake_ack,
            on_command=self._on_voice_command,
            on_audio_level=self._on_mic_audio_level,
            on_wake_ignored=self._on_wake_ignored,
            is_paused_fn=lambda: (
                (not self.always_wake_enabled)
                or (self.orb_state == "processing")
                or (
                    self.webui_mic_active
                    and not (
                        self.is_tts_speaking
                        or self.remote_tts_speaking
                        or (time.time() < self._remote_tts_cooldown_until)
                    )
                )
            ),
            is_capture_aborted_fn=lambda: (
                (not self.always_wake_enabled)
                or self.webui_mic_active
            ),
            get_wake_phrases_fn=self.bridge.get_wake_words,
            is_tts_speaking_fn=lambda: bool(
                self.is_tts_speaking
                or self.remote_tts_speaking
                or (time.time() < self._remote_tts_cooldown_until)
            ),
            on_barge_in=self._on_barge_in,
        )
        self.voice.start()

        self._init_hotkeys()
        if acquire_mutex and os.environ.get("PULSAR_NO_TRAY") != "1":
            self._init_tray()
        self._create_window()
        self._start_socket_sync()
        threading.Thread(
            target=self._sync_initial_settings,
            daemon=True,
            name="CompanionInitialSettingsSync",
        ).start()
        self._start_window_autodetect()

    def _acquire_single_instance(self):
        self._mutex = kernel32.CreateMutexW(None, True, MUTEX_NAME)
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            print("[OVERLAY] Minimized 4D Orb overlay is already running. Exiting duplicate.")
            sys.exit(0)

    def _is_app_launcher_running(self) -> bool:
        try:
            SYNCHRONIZE = 0x00100000
            h = kernel32.OpenMutexW(SYNCHRONIZE, False, APP_LAUNCHER_MUTEX_NAME)
            if h:
                kernel32.CloseHandle(h)
                return True
        except Exception:
            pass
        return False

    def _init_tray(self):
        """Expose a lightweight System Tray menu when companion runs standalone outside app_launcher."""
        if self._is_app_launcher_running():
            return

        def _start_tray():
            try:
                import pystray
                import webbrowser

                tray_img = self.renderer.render_frame(state="idle", audio_level=15.0, dt=0.03).resize(
                    (64, 64), Image.Resampling.LANCZOS
                )

                def on_open_dashboard(icon, item):
                    try:
                        webbrowser.open(f"http://127.0.0.1:{self.port}")
                    except Exception:
                        pass

                def on_toggle_listen(icon, item):
                    with self._state_lock:
                        new_val = not self.always_wake_enabled
                        self.always_wake_enabled = new_val
                    try:
                        self.bridge.session.post(
                            f"{self.bridge.base_url}/api/settings/voice",
                            json={"stt": {"continuous": new_val}},
                            timeout=2.0,
                        )
                    except Exception:
                        pass

                def on_toggle_overlay(icon, item):
                    with self._state_lock:
                        new_val = not self.overlay_enabled
                        self.overlay_enabled = new_val
                    self._emit_orb_update(state=self.orb_state, audio_level=self.audio_level, source="companion_tray")

                def on_stop_speaking(icon, item):
                    self._on_barge_in("tray_stop")

                def on_quit(icon, item):
                    self.close()

                menu = pystray.Menu(
                    pystray.MenuItem("Open Pulsar Dashboard", on_open_dashboard, default=True),
                    pystray.MenuItem("Listen Now (F8)", lambda i, m: self.voice.trigger_manual_listen()),
                    pystray.MenuItem("Stop Speaking", on_stop_speaking),
                    pystray.MenuItem(
                        lambda item: "Pause Voice Wake" if self.always_wake_enabled else "Resume Voice Wake",
                        on_toggle_listen,
                    ),
                    pystray.MenuItem(
                        lambda item: "Hide Floating Orb" if self.overlay_enabled else "Show Floating Orb",
                        on_toggle_overlay,
                    ),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Quit Pulsar Companion", on_quit),
                )
                self.tray_icon = pystray.Icon("PulsarCompanionOrb", tray_img, "Pulsar AI Companion", menu)
                self.tray_icon.run()
            except Exception as e:
                print(f"[OVERLAY] Tray icon unavailable: {e}")

        threading.Thread(target=_start_tray, daemon=True, name="CompanionTrayIcon").start()

    def _init_hotkeys(self):
        def _hook():
            try:
                from pynput import keyboard

                def on_press(key):
                    if key == keyboard.Key.pause:
                        with self._state_lock:
                            self.orb_state = "error"
                            self._error_until = time.time() + 2.5
                    elif key == keyboard.Key.f8:
                        self.voice.trigger_manual_listen()

                with keyboard.Listener(on_press=on_press) as listener:
                    listener.join()
            except Exception:
                pass

        threading.Thread(target=_hook, daemon=True).start()

    def _create_window(self):
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._wndproc
        wc.lpszClassName = "PulsarTransparentOrbOverlayClass"
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        try:
            win32gui.RegisterClass(wc)
        except Exception:
            pass

        ex_style = (
            win32con.WS_EX_LAYERED
            | win32con.WS_EX_TRANSPARENT
            | win32con.WS_EX_TOPMOST
            | win32con.WS_EX_TOOLWINDOW
            | WS_EX_NOACTIVATE
        )
        self.hwnd = win32gui.CreateWindowEx(
            ex_style,
            wc.lpszClassName,
            WINDOW_TITLE,
            win32con.WS_POPUP,
            self.x,
            self.y,
            self.w,
            self.h,
            0,
            0,
            wc.hInstance,
            None,
        )

        # Synchronized to visibility gate (overlay_enabled & app_minimized) on first 33ms tick
        win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
        self._currently_visible = False

        # 33 ms (~30 FPS) animation + visibility check timer
        user32.SetTimer(self.hwnd, 1, 33, None)
        print(f"[OVERLAY] Transparent click-through 4D Orb ready at ({self.x}, {self.y}) [size={self.w}px].")

    def _start_window_autodetect(self):
        """Edge-triggered Win32 monitor that hides orb when WebUI/desktop app opens and shows on minimize/close."""
        def _push_vis(minimized: bool):
            with self._state_lock:
                self.app_minimized = minimized
            if self.sio and self.sio_connected:
                try:
                    self.sio.emit("app_visibility", {"minimized": minimized, "source": "companion_autodetect", "force": True})
                    return
                except Exception:
                    pass
            try:
                self.bridge.update_overlay_state(app_minimized=minimized, source="companion_autodetect")
            except Exception:
                pass

        def _watch():
            while not self._stop_event.is_set():
                try:
                    webui_open = detect_webui_window_open()
                    if self._last_webui_open is None or webui_open != self._last_webui_open:
                        self._last_webui_open = webui_open
                        _push_vis(not webui_open)
                except Exception:
                    pass
                time.sleep(0.40)

        threading.Thread(target=_watch, daemon=True, name="OrbWindowWatcher").start()

    def _apply_settings_payload(self, all_settings: dict):
        if not isinstance(all_settings, dict):
            return
        sys_cfg = all_settings.get("system")
        if isinstance(sys_cfg, dict) and isinstance(sys_cfg.get("desktopOverlay"), bool):
            with self._state_lock:
                self.overlay_enabled = sys_cfg["desktopOverlay"]
        voice_cfg = all_settings.get("voice")
        if isinstance(voice_cfg, dict):
            stt_cfg = voice_cfg.get("stt")
            if isinstance(stt_cfg, dict) and isinstance(stt_cfg.get("continuous"), bool):
                with self._state_lock:
                    self.always_wake_enabled = stt_cfg["continuous"]
            tts_cfg = voice_cfg.get("tts")
            if isinstance(tts_cfg, dict):
                with self._state_lock:
                    if isinstance(tts_cfg.get("enabled"), bool):
                        self.tts_enabled = tts_cfg["enabled"]
                    voice_val = tts_cfg.get("voice_id") or tts_cfg.get("voice")
                    if isinstance(voice_val, str) and voice_val.strip():
                        self.tts_voice_id = voice_val.strip()

    def _sync_initial_settings(self):
        try:
            resp = self.bridge.session.get(f"{self.bridge.base_url}/api/settings/all", timeout=2.0)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and isinstance(data.get("settings"), dict):
                    self._apply_settings_payload(data["settings"])
        except Exception:
            pass

    def _start_socket_sync(self):
        if not SOCKETIO_CLIENT_AVAILABLE or sio_lib is None:
            threading.Thread(target=self._poll_loop_fallback, daemon=True).start()
            return

        sio = sio_lib.Client(reconnection=True, reconnection_attempts=0, reconnection_delay=2)
        self.sio = sio

        @sio.event
        def connect():
            self.sio_connected = True
            ov = self.bridge.get_overlay_state()
            if ov:
                self._apply_remote_snapshot(ov)
            self._sync_initial_settings()
            try:
                webui_open = detect_webui_window_open()
                self._last_webui_open = webui_open
                with self._state_lock:
                    self.app_minimized = not webui_open
                sio.emit("app_visibility", {"minimized": not webui_open, "source": "companion_autodetect", "force": True})
            except Exception:
                pass

        @sio.event
        def disconnect():
            self.sio_connected = False

        @sio.on("orb_state_sync")
        def on_orb_state_sync(data):
            if isinstance(data, dict):
                self._apply_remote_snapshot(data)

        @sio.on("overlay_config_updated")
        def on_overlay_config_updated(data):
            if isinstance(data, dict) and "enabled" in data:
                with self._state_lock:
                    self.overlay_enabled = bool(data["enabled"])

        @sio.on("settings_updated")
        def on_settings_updated(data):
            if not isinstance(data, dict):
                return
            all_settings = data.get("all_settings") or {}
            if isinstance(all_settings, dict) and all_settings:
                self._apply_settings_payload(all_settings)
                return
            cat = data.get("category")
            cfg = data.get("settings") or {}
            if cat == "system" and isinstance(cfg.get("desktopOverlay"), bool):
                with self._state_lock:
                    self.overlay_enabled = bool(cfg["desktopOverlay"])
            elif cat == "voice":
                stt_cfg = cfg.get("stt")
                if isinstance(stt_cfg, dict) and isinstance(stt_cfg.get("continuous"), bool):
                    with self._state_lock:
                        self.always_wake_enabled = bool(stt_cfg["continuous"])
                tts_cfg = cfg.get("tts")
                if isinstance(tts_cfg, dict):
                    with self._state_lock:
                        if isinstance(tts_cfg.get("enabled"), bool):
                            self.tts_enabled = bool(tts_cfg["enabled"])
                        voice_val = tts_cfg.get("voice_id") or tts_cfg.get("voice")
                        if isinstance(voice_val, str) and voice_val.strip():
                            self.tts_voice_id = voice_val.strip()

        def _connect_worker():
            while not self._stop_event.is_set():
                try:
                    if not self.sio_connected:
                        sio.connect(f"http://127.0.0.1:{self.port}?role=companion", wait_timeout=5)
                        sio.wait()
                except Exception:
                    self.sio_connected = False
                time.sleep(2.0)

        threading.Thread(target=_connect_worker, daemon=True).start()

    def _poll_loop_fallback(self):
        while not self._stop_event.is_set():
            ov = self.bridge.get_overlay_state()
            if ov:
                self._apply_remote_snapshot(ov)
            time.sleep(1.0)

    def _apply_remote_snapshot(self, snap: dict):
        with self._state_lock:
            if isinstance(snap.get("overlay_enabled"), bool):
                self.overlay_enabled = snap["overlay_enabled"]
            if isinstance(snap.get("app_minimized"), bool):
                self.app_minimized = snap["app_minimized"]
            if isinstance(snap.get("webui_mic_active"), bool):
                self.webui_mic_active = snap["webui_mic_active"]
            if isinstance(snap.get("tts_speaking"), bool):
                prev_remote_tts = self.remote_tts_speaking
                self.remote_tts_speaking = snap["tts_speaking"]
                if time.time() < getattr(self, "_suppress_cooldown_until", 0.0):
                    self._remote_tts_cooldown_until = 0.0
                elif prev_remote_tts and not self.remote_tts_speaking:
                    self._remote_tts_cooldown_until = time.time() + 0.45
                elif self.remote_tts_speaking:
                    self._remote_tts_cooldown_until = 0.0

            src = str(snap.get("source", ""))
            # Don't let stale remote packets override local companion fallback TTS playback
            if self.is_tts_speaking and src != "companion_tts":
                return

            remote_state = snap.get("state")
            if remote_state in ORB_STATE_CONFIGS:
                self.orb_state = remote_state
            if snap.get("audio_level") is not None:
                try:
                    self.audio_level = max(0.0, min(100.0, float(snap["audio_level"])))
                except (TypeError, ValueError):
                    pass

    def _emit_orb_update(self, state: Optional[str] = None, audio_level: Optional[float] = None, source: str = "companion_voice"):
        payload: Dict[str, object] = {"source": source}
        if state is not None:
            payload["state"] = state
        if audio_level is not None:
            payload["audio_level"] = float(audio_level)

        if self.sio and self.sio_connected:
            try:
                self.sio.emit("orb_state_update", payload)
                return
            except Exception:
                pass
        self.bridge.update_overlay_state(state=state, audio_level=audio_level, source=source)

    def _on_wake_heard(self, wake_word: Optional[str] = None):
        if self.remote_tts_speaking:
            self.bridge.stop_speaking("companion_wake")
        with self._state_lock:
            self.remote_tts_speaking = False
            self._remote_tts_cooldown_until = 0.0
            self.orb_state = "listening"
            self.audio_level = 18.0
        if self.sio and self.sio_connected:
            try:
                self.sio.emit("companion_wake", {"wake_word": wake_word or "hey pulsar", "confidence": 0.95})
                return
            except Exception:
                pass
        self._emit_orb_update(state="listening", audio_level=18.0, source="companion_wake")

    def _on_wake_ack(self, wake_word: Optional[str] = None):
        """Immediate crisp dynamic verbal + visual confirmation via unified persona & TTS."""
        with self._state_lock:
            tts_on = getattr(self, "tts_enabled", True)
        if tts_on:
            ack_res = self.bridge.request_wake_ack(
                wake_word=wake_word or "",
                raw_transcript=wake_word or "",
                kind="wake",
                speak=True,
                wait=True,
                source="companion_wake",
            )
            ack_text = str((ack_res or {}).get("text") or "").strip()
            spoken_remote = bool((ack_res or {}).get("spoken") or (ack_res or {}).get("queued"))
            is_fallback = bool((ack_res or {}).get("_local_fallback"))
            if spoken_remote:
                # Allow speaker reverb tail to decay before opening mic for follow-up command
                time.sleep(0.25)
            elif is_fallback and ack_text:
                self._speak_sync(ack_text, rate=188)
        with self._state_lock:
            self._suppress_cooldown_until = time.time() + 1.5
            self.remote_tts_speaking = False
            self._remote_tts_cooldown_until = 0.0
            self.orb_state = "listening"
            self.audio_level = 16.0
        self._emit_orb_update(state="listening", audio_level=16.0, source="companion_wake")

    def _on_barge_in(self, transcript: str = ""):
        """Immediate voice/tray barge-in: abort local and backend TTS without speaking back."""
        self._tts_abort_event.set()
        eng = getattr(self, "_active_pyttsx3", None)
        if eng is not None:
            try:
                eng.stop()
            except Exception:
                pass

        if self.remote_tts_speaking or (time.time() < self._remote_tts_cooldown_until):
            self.bridge.stop_speaking("companion_voice_barge_in")

        with self._state_lock:
            self.is_tts_speaking = False
            self.remote_tts_speaking = False
            self._remote_tts_cooldown_until = 0.0
            if self.orb_state == "speaking":
                self.orb_state = "idle"
                self.audio_level = 0.0
        self._emit_orb_update(state="idle", audio_level=0.0, source="companion_barge_in")

    def _on_wake_ignored(self):
        with self._state_lock:
            if not self.is_tts_speaking and not self.remote_tts_speaking:
                self.orb_state = "idle"
                self.audio_level = 0.0
        self._emit_orb_update(state="idle", audio_level=0.0, source="companion_voice")

    def _on_mic_audio_level(self, level: float):
        with self._state_lock:
            if self.orb_state == "listening":
                self.audio_level = float(level)
        now = time.time()
        if now - self._last_level_emit >= 0.055:
            self._last_level_emit = now
            self._emit_orb_update(state="listening", audio_level=level, source="companion_voice")

    def _on_voice_command(self, command: str):
        with self._state_lock:
            self.orb_state = "processing"
            self.audio_level = 0.0
        self._emit_orb_update(state="processing", audio_level=0.0, source="companion_voice")

        def _worker():
            try:
                req_screen = command_requests_screen(command)
                result = self.bridge.send_command(command, include_screen=req_screen, source="companion_voice")
                is_ok = bool(result.get("success", True))
                resp_text = str(result.get("response", ""))
                tts_text = str(result.get("tts", resp_text)).strip()
                is_local_fallback = bool(result.get("_local_fallback"))

                with self._state_lock:
                    app_min = self.app_minimized

                if is_local_fallback:
                    pre_report_text = str(result.get("pre_report") or "").strip()
                    if app_min and pre_report_text:
                        self._speak_sync(pre_report_text[:180])
                    if not is_ok:
                        with self._state_lock:
                            self.orb_state = "error"
                            self._error_until = time.time() + 3.2
                        self._emit_orb_update(state="error", audio_level=0.0, source="companion_voice")
                        if app_min and tts_text:
                            self._speak_sync(tts_text[:180])
                        time.sleep(3.2)
                    elif tts_text:
                        if app_min:
                            self._speak_sync(tts_text[:240])
                        else:
                            with self._state_lock:
                                self.orb_state = "speaking"
                                self.audio_level = 42.0
                            time.sleep(min(4.0, max(1.5, len(tts_text) * 0.045)))

                    with self._state_lock:
                        if time.time() >= self._error_until:
                            self.orb_state = "idle"
                            self.audio_level = 0.0
                    self._emit_orb_update(state="idle", audio_level=0.0, source="companion_voice")
                    return

                # Backend Agent Brain already triggered unified single-speaker TTSOutputService
                if not is_ok:
                    with self._state_lock:
                        self.orb_state = "error"
                        self._error_until = time.time() + 3.2
                    self._emit_orb_update(state="error", audio_level=0.0, source="companion_voice")
                    time.sleep(3.2)
                    with self._state_lock:
                        if self.orb_state == "error" and time.time() >= self._error_until:
                            self.orb_state = "idle"
                            self.audio_level = 0.0
                            self._emit_orb_update(state="idle", audio_level=0.0, source="companion_voice")
                    return

                # Wait while backend TTSOutputService synthesizes and speaks without prematurely emitting idle
                time.sleep(0.25)
                wait_window_s = 40.0 if result.get("_timed_out") else 25.0
                deadline = time.time() + wait_window_s
                while not self._stop_event.is_set() and time.time() < deadline:
                    if self.remote_tts_speaking:
                        time.sleep(0.15)
                        continue
                    status_snap = self.bridge.get_tts_status()
                    tts_info = (status_snap or {}).get("tts") or {}
                    if tts_info.get("speaking") or tts_info.get("queued_synth", 0) > 0 or tts_info.get("queued_play", 0) > 0:
                        time.sleep(0.15)
                        continue
                    break

                with self._state_lock:
                    if (
                        not self.remote_tts_speaking
                        and not self.is_tts_speaking
                        and self.orb_state in ("processing", "speaking")
                        and time.time() >= self._error_until
                    ):
                        self.orb_state = "idle"
                        self.audio_level = 0.0
                        self._emit_orb_update(state="idle", audio_level=0.0, source="companion_voice")
            except Exception as e:
                with self._state_lock:
                    self.orb_state = "error"
                    self._error_until = time.time() + 3.2
                self._emit_orb_update(state="error", audio_level=0.0, source="companion_error")
                time.sleep(3.2)
                with self._state_lock:
                    self.orb_state = "idle"
                    self.audio_level = 0.0
                self._emit_orb_update(state="idle", audio_level=0.0, source="companion_error")
                print(f"[OVERLAY] Voice command execution error: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _speak_sync(self, text: str, rate: int = 175):
        """Local offline fallback TTS (KittenTTS mini-0.8 via sounddevice -> COM pyttsx3) when backend is down."""
        clean_text = (text or "").strip()
        if not clean_text or self.remote_tts_speaking:
            return
        with self._speak_sync_lock:
            with self._state_lock:
                tts_on = getattr(self, "tts_enabled", True)
                voice_cfg_id = getattr(self, "tts_voice_id", "hi-IN-SwaraNeural")
                remote_busy = bool(self.remote_tts_speaking)
            if not tts_on or not clean_text or remote_busy:
                return

            self._tts_abort_event.clear()
            self.is_tts_speaking = True
            with self._state_lock:
                self.orb_state = "speaking"
                self.audio_level = 48.0
            self._emit_orb_update(state="speaking", audio_level=48.0, source="companion_tts")

            stop_pulse = threading.Event()

            def _pulse_loop():
                t0 = time.time()
                while not stop_pulse.is_set() and not self._tts_abort_event.is_set():
                    elapsed = time.time() - t0
                    lvl = 38.0 + 34.0 * abs(math.sin(elapsed * 9.5) * math.cos(elapsed * 3.7))
                    with self._state_lock:
                        if self.is_tts_speaking:
                            self.orb_state = "speaking"
                            self.audio_level = lvl
                    if int(elapsed * 16) != int((elapsed - 0.05) * 16):
                        self._emit_orb_update(state="speaking", audio_level=lvl, source="companion_tts")
                    time.sleep(0.05)

            pulse_thread = threading.Thread(target=_pulse_loop, daemon=True)
            pulse_thread.start()

            spoke_via_kitten = False
            try:
                try:
                    import sounddevice as sd
                    from ai_assistant.voice.text_cleaner import prepare_text_for_kitten_tts
                    from ai_assistant.voice.tts_output_service import (
                        BLOCK_SAMPLES,
                        TARGET_SAMPLE_RATE,
                        load_kitten_mini_model,
                        resolve_kitten_voice,
                    )

                    cleaned_k = prepare_text_for_kitten_tts(clean_text) or clean_text
                    if cleaned_k and not self._tts_abort_event.is_set() and not self.remote_tts_speaking:
                        model = load_kitten_mini_model()
                        k_voice = resolve_kitten_voice(voice_cfg_id)
                        pcm = np.asarray(model.generate(cleaned_k, voice=k_voice, speed=1.0, clean_text=True), dtype=np.float32).reshape(-1)
                        if pcm.size > 0 and not self._tts_abort_event.is_set() and not self.remote_tts_speaking:
                            with sd.OutputStream(
                                samplerate=TARGET_SAMPLE_RATE,
                                channels=1,
                                dtype="float32",
                                blocksize=BLOCK_SAMPLES,
                            ) as stream:
                                for start in range(0, pcm.size, BLOCK_SAMPLES):
                                    if self._stop_event.is_set() or self._tts_abort_event.is_set() or self.remote_tts_speaking:
                                        try:
                                            stream.abort()
                                        except Exception:
                                            pass
                                        break
                                    stream.write(pcm[start : start + BLOCK_SAMPLES].reshape(-1, 1))
                            spoke_via_kitten = True
                except Exception as kitten_err:
                    print(f"[OVERLAY] Offline KittenTTS fallback note: {kitten_err}")

                if not spoke_via_kitten and not self._tts_abort_event.is_set() and not self.remote_tts_speaking:
                    coinit_done = False
                    try:
                        try:
                            import pythoncom

                            pythoncom.CoInitialize()
                            coinit_done = True
                        except Exception:
                            pass

                        import pyttsx3
                        from ai_assistant.voice.tts_output_service import configure_sapi5_voice

                        engine = pyttsx3.init()
                        self._active_pyttsx3 = engine
                        configure_sapi5_voice(engine, configured_voice=voice_cfg_id)
                        engine.setProperty("rate", rate)
                        engine.say(clean_text)
                        engine.runAndWait()
                    except Exception as e:
                        print(f"[OVERLAY] Local TTS note: {e}")
                        time.sleep(min(6.0, max(1.0, len(clean_text) * 0.05)))
                    finally:
                        self._active_pyttsx3 = None
                        if coinit_done:
                            try:
                                import pythoncom

                                pythoncom.CoUninitialize()
                            except Exception:
                                pass
            finally:
                stop_pulse.set()
                pulse_thread.join(timeout=0.3)
                self.is_tts_speaking = False

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_NCHITTEST:
            return win32con.HTTRANSPARENT

        if msg == win32con.WM_TIMER and wparam == 1:
            # Periodic HTTP fallback poll when SocketIO isn't connected
            now = time.time()
            if not self.sio_connected and (now - self._last_http_poll) > 1.2:
                self._last_http_poll = now
                threading.Thread(
                    target=lambda: self._apply_remote_snapshot(self.bridge.get_overlay_state() or {}),
                    daemon=True,
                ).start()

            with self._state_lock:
                enabled = self.overlay_enabled
                minimized = self.app_minimized
                state = self.orb_state
                level = self.audio_level

            should_show = compute_overlay_visibility(enabled, minimized, state)
            if not should_show:
                if self._currently_visible:
                    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                    self._currently_visible = False
                return 0

            # Keep aligned cleanly above taskbar on work area bottom-center
            self.x, self.y = get_workarea_bottom_center_coords(self.w, self.h)
            frame = self.renderer.render_frame(state=state, audio_level=level, dt=0.033)
            apply_layered_image(hwnd, frame, self.x, self.y)

            if not self._currently_visible:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWNA)
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOPMOST,
                    self.x,
                    self.y,
                    self.w,
                    self.h,
                    win32con.SWP_NOACTIVATE | win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
                )
                self._currently_visible = True
            return 0

        if msg == win32con.WM_CLOSE:
            win32gui.DestroyWindow(hwnd)
            return 0

        if msg == win32con.WM_DESTROY:
            self._stop_event.set()
            win32gui.PostQuitMessage(0)
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def close(self):
        self._stop_event.set()
        self._tts_abort_event.set()
        try:
            self.voice.stop()
            if self.tray_icon:
                try:
                    self.tray_icon.stop()
                except Exception:
                    pass
            if self.sio:
                self.sio.disconnect()
            if hasattr(self, "hwnd") and self.hwnd:
                win32api.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception:
            pass

    def run(self):
        win32gui.PumpMessages()


def _parse_companion_port(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    for idx, token in enumerate(args):
        if token == "--port" and idx + 1 < len(args) and str(args[idx + 1]).isdigit():
            return int(args[idx + 1])
        if token == "--companion" and idx + 1 < len(args) and str(args[idx + 1]).isdigit():
            return int(args[idx + 1])
        if str(token).isdigit():
            return int(token)
    for env_key in ("PULSAR_PORT", "PORT"):
        val = os.environ.get(env_key, "")
        if str(val).isdigit():
            return int(val)
    return 5000


def main(port: Optional[int] = None):
    resolved_port = int(port) if port else _parse_companion_port()
    app = AmbientMascotApp(acquire_mutex=True, port=resolved_port)
    app.run()


if __name__ == "__main__":
    main()
