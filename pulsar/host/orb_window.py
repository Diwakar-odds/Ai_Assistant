"""
Pulsar Host - Native 4D Wireframe Particle Orb Window (PySide6)
===============================================================
Click-through, 97% see-through transparent, topmost frameless overlay positioned
flush above the Windows taskbar.

Renders the signature Pulsar 4D Wireframe + Vibrating Starlight Particle Orb
(exact vectorized NumPy lattice + Fibonacci halo math matching the WebUI Three.js Orb):
- Compact sleek size (136 logical px, rendered at full HiDPI physical resolution).
- Ultra-fine 12x18 latitude-longitude glowing wireframe mesh + 280 pinpoint starlight dots.
- Crystal-clear transparent center so text/windows underneath remain 100% readable.
- 5 smooth-interpolating states (idle cobalt->magenta, listening cyan->violet,
  speaking sky->neon pink, thinking/processing amber gold->violet, error crimson).
- Win32 click-through + topmost via SetWindowLongW + SetWindowPos(HWND_TOPMOST, SWP_FRAMECHANGED).
- Live 30 Hz Socket.IO client receiving Core `"orb_state"` (`{state, level}`).
- Smooth 180 ms fade-in / instant hide controlled by Host's single `reconcile()`.
"""

import os
import sys
import math
import time
import logging
import threading
from typing import Dict, Optional

import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QImage, QPainter, QGuiApplication
from PySide6.QtWidgets import QWidget

logger = logging.getLogger("pulsar.host.orb_window")

try:
    _env_orb = int(os.environ.get("PULSAR_ORB_SIZE", "136"))
    ORB_SIZE = max(96, min(260, _env_orb))
except ValueError:
    ORB_SIZE = 136

HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020

# Exact 5-State Color & Motion Configuration (matches WebUI Three.js Orb & classic companion_app)
ORB_STATE_CONFIGS: Dict[str, Dict[str, object]] = {
    "idle": {
        "primary": np.array([37.0, 99.0, 235.0], dtype=np.float32),     # Cobalt Blue
        "secondary": np.array([124.0, 58.0, 237.0], dtype=np.float32),  # Indigo Violet
        "accent": np.array([192.0, 38.0, 211.0], dtype=np.float32),     # Soft Magenta
        "speed": 0.65,
        "wave_amp": 0.08,
        "particle_vib": 0.03,
        "jagged": 0.0,
        "swirl": 0.14,
    },
    "warming": {
        "primary": np.array([56.0, 189.0, 248.0], dtype=np.float32),    # Ice Cyan
        "secondary": np.array([99.0, 102.0, 241.0], dtype=np.float32),  # Indigo
        "accent": np.array([168.0, 85.0, 247.0], dtype=np.float32),     # Violet
        "speed": 0.90,
        "wave_amp": 0.10,
        "particle_vib": 0.05,
        "jagged": 0.0,
        "swirl": 0.22,
    },
    "listening": {
        "primary": np.array([0.0, 243.0, 255.0], dtype=np.float32),     # Electric Cyan
        "secondary": np.array([59.0, 130.0, 246.0], dtype=np.float32),  # Vivid Azure
        "accent": np.array([168.0, 85.0, 247.0], dtype=np.float32),     # Violet
        "speed": 1.35,
        "wave_amp": 0.14,
        "particle_vib": 0.10,
        "jagged": 0.0,
        "swirl": 0.30,
    },
    "speaking": {
        "primary": np.array([0.0, 212.0, 255.0], dtype=np.float32),     # Sky Cyan
        "secondary": np.array([139.0, 92.0, 246.0], dtype=np.float32),  # Electric Purple
        "accent": np.array([236.0, 72.0, 153.0], dtype=np.float32),     # Neon Pink-Magenta
        "speed": 1.60,
        "wave_amp": 0.17,
        "particle_vib": 0.12,
        "jagged": 0.0,
        "swirl": 0.34,
    },
    "processing": {
        "primary": np.array([245.0, 158.0, 11.0], dtype=np.float32),    # Amber Gold
        "secondary": np.array([249.0, 115.0, 22.0], dtype=np.float32),  # Warm Orange
        "accent": np.array([139.0, 92.0, 246.0], dtype=np.float32),     # Cosmic Violet
        "speed": 2.25,
        "wave_amp": 0.14,
        "particle_vib": 0.09,
        "jagged": 0.10,
        "swirl": 1.25,
    },
    "thinking": {
        "primary": np.array([245.0, 158.0, 11.0], dtype=np.float32),    # Amber Gold
        "secondary": np.array([249.0, 115.0, 22.0], dtype=np.float32),  # Warm Orange
        "accent": np.array([139.0, 92.0, 246.0], dtype=np.float32),     # Cosmic Violet
        "speed": 2.25,
        "wave_amp": 0.14,
        "particle_vib": 0.09,
        "jagged": 0.10,
        "swirl": 1.25,
    },
    "offline": {
        "primary": np.array([100.0, 116.0, 139.0], dtype=np.float32),
        "secondary": np.array([71.0, 85.0, 105.0], dtype=np.float32),
        "accent": np.array([148.0, 163.0, 184.0], dtype=np.float32),
        "speed": 0.35,
        "wave_amp": 0.04,
        "particle_vib": 0.01,
        "jagged": 0.0,
        "swirl": 0.05,
    },
    "error": {
        "primary": np.array([239.0, 68.0, 68.0], dtype=np.float32),     # Crimson Red
        "secondary": np.array([249.0, 115.0, 22.0], dtype=np.float32),  # Ember Orange
        "accent": np.array([251.0, 113.0, 133.0], dtype=np.float32),    # Hot Rose Alert
        "speed": 2.90,
        "wave_amp": 0.20,
        "particle_vib": 0.18,
        "jagged": 1.0,
        "swirl": 0.55,
    },
}


class WireframeParticleOrbEngine:
    """
    Vectorized NumPy 3D-projected 4D wireframe quad-lattice + vibrating outer starlight
    particle renderer. Produces crystal-clear 97% see-through straight RGBA numpy buffers
    matching the classic Pulsar Orb & WebUI Three.js Orb pixel-for-pixel.
    """

    def __init__(self, pixel_size: int = 180, num_particles: int = 280):
        self.size = int(pixel_size)
        self.half = float(self.size) / 2.0
        self.base_radius = float(self.size) * 0.31
        self.persp_dist = self.base_radius * 4.0

        init_cfg = ORB_STATE_CONFIGS["idle"]
        self.cur_primary = init_cfg["primary"].copy()
        self.cur_secondary = init_cfg["secondary"].copy()
        self.cur_accent = init_cfg["accent"].copy()
        self.cur_audio = 0.0
        self.cur_wave_amp = float(init_cfg["wave_amp"])
        self.cur_vib = float(init_cfg["particle_vib"])
        self.cur_jagged = float(init_cfg["jagged"])
        self.cur_swirl = float(init_cfg["swirl"])
        self.phase_time = 0.0

        # 1. Outer vibrating starlight particle halo on Fibonacci sphere
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

        # 2. Structured 12x18 latitude-longitude quad mesh grid for continuous glowing wireframe curves
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

        # 3. Crystal-clear 97% see-through core masks (text behind orb stays 100% readable)
        yy, xx = np.mgrid[0:self.size, 0:self.size].astype(np.float32)
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
        self.aura_w0_row = (np.float32(1.0) - aura_mix_row)[None, None, :].astype(np.float32)
        self.aura_w1_row = aura_mix_row[None, None, :].astype(np.float32)
        self.core_ambient_prem = (
            np.array([0.005, 0.01, 0.02], dtype=np.float32)[:, None, None] * self.core_body_alpha[None, :, :]
        ).astype(np.float32)
        self.fresnel_base_ca = ((np.float32(0.08) + np.float32(0.38) * self.core_fresnel) * self.core_body_alpha).astype(np.float32)

        self._buf = np.empty((3, self.size, self.size), dtype=np.float32)
        self._tmp2d = np.empty((self.size, self.size), dtype=np.float32)
        self._rgba_out = np.empty((self.size, self.size, 4), dtype=np.uint8)

    def _accumulate_all_splats(self, flat_buf: np.ndarray, idx_list, col_list):
        if not idx_list:
            return
        all_idx = idx_list[0] if len(idx_list) == 1 else np.concatenate(idx_list)
        all_col = col_list[0] if len(col_list) == 1 else np.concatenate(col_list, axis=0)
        n_pix = self.size * self.size
        for ch in range(3):
            flat_buf[ch] += np.bincount(all_idx, weights=all_col[:, ch], minlength=n_pix)

    def render_rgba(self, state: str = "idle", level: float = 0.0, dt: float = 0.033) -> np.ndarray:
        """Renders one straight-alpha RGBA uint8 numpy array (size, size, 4)."""
        cfg = ORB_STATE_CONFIGS.get(state, ORB_STATE_CONFIGS["idle"])
        lerp = np.float32(min(1.0, max(0.05, dt * 8.0)))

        self.cur_primary += (cfg["primary"] - self.cur_primary) * lerp
        self.cur_secondary += (cfg["secondary"] - self.cur_secondary) * lerp
        self.cur_accent += (cfg["accent"] - self.cur_accent) * lerp
        self.cur_wave_amp += (float(cfg["wave_amp"]) - self.cur_wave_amp) * float(lerp)
        self.cur_vib += (float(cfg["particle_vib"]) - self.cur_vib) * float(lerp)
        self.cur_jagged += (float(cfg["jagged"]) - self.cur_jagged) * float(lerp)
        self.cur_swirl += (float(cfg["swirl"]) - self.cur_swirl) * float(lerp)

        target_audio = max(0.0, min(1.0, float(level)))
        a_lerp = 0.45 if target_audio > self.cur_audio else 0.20
        self.cur_audio += (target_audio - self.cur_audio) * a_lerp

        speed = float(cfg["speed"]) + self.cur_audio * 1.1
        self.phase_time += dt * speed
        t = np.float32(self.phase_time)

        ry = float(t) * (0.42 + self.cur_swirl * 0.55)
        rx = 0.22 * math.sin(float(t) * 0.45)
        cy, sy = math.cos(ry), math.sin(ry)
        cx, sx = math.cos(rx), math.sin(rx)
        rot_y = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]], dtype=np.float32)
        rot_x = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]], dtype=np.float32)
        rot = rot_x @ rot_y

        p_norm = (self.cur_primary * np.float32(1.0 / 255.0))[:, None, None]
        a_norm = (self.cur_accent * np.float32(1.0 / 255.0))[:, None, None]
        aura_row = (p_norm * self.aura_w0_row + a_norm * self.aura_w1_row).astype(np.float32)
        buf = self._buf
        np.multiply(aura_row, (self.core_aura * np.float32(0.55 + self.cur_audio * 0.35))[None, :, :], out=buf)
        flat_buf = buf.reshape(3, -1)

        splat_indices = []
        splat_colors = []
        card_offsets = (-1, 1, -self.size, self.size)
        diag_offsets = (-self.size - 1, -self.size + 1, self.size - 1, self.size + 1)
        f0 = np.float32(0.0)
        f1 = np.float32(1.0)

        # 1. Continuous 4D wireframe quad lattice curves
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

        # 2. Outer glowing vibrating starlight particles
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

        rgba = self._rgba_out
        rgba[:, :, 0] = buf[0].astype(np.uint8)
        rgba[:, :, 1] = buf[1].astype(np.uint8)
        rgba[:, :, 2] = buf[2].astype(np.uint8)
        rgba[:, :, 3] = np.clip(out_a * np.float32(255.0), f0, np.float32(255.0)).astype(np.uint8)
        return rgba


class OrbWindow(QWidget):
    """Native, 97% see-through transparent, click-through 4D Wireframe Particle Orb Window."""

    orb_state_received = Signal(str, float)

    def __init__(self, port: int = 5000, parent=None):
        super().__init__(parent)
        self.port = port
        self.orb_size = ORB_SIZE
        self._user_visible = True
        self._reconciled_visible = False

        self.current_state = "idle"
        self.target_level = 0.0
        self.last_anim_time = time.time()

        # Render at crisp HiDPI physical resolution (e.g. 204x204 @ 150% DPI)
        screen = QGuiApplication.primaryScreen()
        dpr = float(screen.devicePixelRatio()) if screen else 1.0
        self._render_px = max(136, min(280, int(round(self.orb_size * dpr))))
        self._engine = WireframeParticleOrbEngine(pixel_size=self._render_px, num_particles=280)
        self._last_rgba = self._engine.render_rgba("idle", 0.0, 0.033)

        # Socket.IO background client state
        self._sio = None
        self._ipc_stop = threading.Event()
        self._ipc_thread: Optional[threading.Thread] = None

        # Smooth fade animation
        self._fade_anim: Optional[QPropertyAnimation] = None
        self._show_delay_timer: Optional[QTimer] = None

        self.orb_state_received.connect(self.set_orb_state)

        self._setup_window_flags()
        self.reposition_above_taskbar()
        self._init_timers()

    def _setup_window_flags(self):
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
            | Qt.NoDropShadowWindowHint
        )
        self.setFixedSize(self.orb_size, self.orb_size)

    def _init_timers(self):
        # 30 FPS smooth SIMD wireframe animation (light CPU, butter smooth)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_tick)
        self.anim_timer.start(30)

        self.topmost_timer = QTimer(self)
        self.topmost_timer.timeout.connect(self._assert_win32_topmost)
        self.topmost_timer.start(2000)

        screen = QGuiApplication.primaryScreen()
        if screen:
            try:
                screen.availableGeometryChanged.connect(lambda _: self.reposition_above_taskbar())
            except Exception:
                pass

    def _apply_win32_flags(self):
        """Locks click-through + topmost flags without calling SetLayeredWindowAttributes."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOOLWINDOW = 0x00000080

            user32 = ctypes.windll.user32
            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            new_ex = ex | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            if new_ex != ex:
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_ex)

            user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED,
            )
        except Exception as e:
            logger.debug(f"[OrbWindow] Win32 flag lock note: {e}")

    def _assert_win32_topmost(self):
        if not self.isVisible() or sys.platform != "win32":
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            # SWP_NOREDRAW (0x0008) | SWP_NOOWNERZORDER (0x0200) prevents DWM desktop repaint flicker
            ctypes.windll.user32.SetWindowPos(
                hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | 0x0008 | 0x0200,
            )
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_win32_flags()

    def reposition_above_taskbar(self):
        """Positions the sleek 136px orb centered horizontally, flush above the Windows taskbar."""
        screen = QGuiApplication.primaryScreen()
        if not screen:
            self.move(572, 608)
            return

        avail = screen.availableGeometry()
        x = avail.x() + (avail.width() - self.orb_size) // 2
        y = avail.y() + avail.height() - self.orb_size - 6

        self.setGeometry(x, y, self.orb_size, self.orb_size)
        logger.info(
            f"[OrbWindow] Positioned at ({x}, {y}) [Size: {self.orb_size}x{self.orb_size} | "
            f"RenderPx: {self._render_px}px | WorkArea: {avail.width()}x{avail.height()}]"
        )

    # ------------------------------------------------------------------
    # Live Socket.IO IPC ("orb_state" from Core at 30 Hz)
    # ------------------------------------------------------------------
    def start_core_ipc(self):
        if self._ipc_thread and self._ipc_thread.is_alive():
            return
        self._ipc_stop.clear()
        self._ipc_thread = threading.Thread(
            target=self._ipc_worker,
            name="OrbSocketIOClient",
            daemon=True,
        )
        self._ipc_thread.start()

    def stop_core_ipc(self):
        self._ipc_stop.set()
        if self._sio is not None:
            try:
                self._sio.disconnect()
            except Exception:
                pass
            self._sio = None

    def _ipc_worker(self):
        try:
            import socketio
        except ImportError:
            return

        url = f"http://127.0.0.1:{self.port}"
        while not self._ipc_stop.is_set():
            sio = socketio.Client(reconnection=False, logger=False, engineio_logger=False)
            self._sio = sio

            @sio.on("orb_state")
            def on_orb_state(data):
                if isinstance(data, dict):
                    st = str(data.get("state", "idle"))
                    lvl = float(data.get("level", 0.0))
                    self.orb_state_received.emit(st, lvl)

            try:
                sio.connect(url, headers={"Origin": url}, wait_timeout=3)
                logger.info(f"[OrbWindow] Connected to Core Socket.IO at {url}")
                while not self._ipc_stop.is_set() and sio.connected:
                    time.sleep(0.25)
            except Exception:
                pass
            finally:
                try:
                    if sio.connected:
                        sio.disconnect()
                except Exception:
                    pass
                self._sio = None

            if not self._ipc_stop.is_set():
                time.sleep(2.0)

    # ------------------------------------------------------------------
    # State & Animation
    # ------------------------------------------------------------------
    def set_orb_state(self, state: str, level: float = 0.0):
        if state in ORB_STATE_CONFIGS:
            self.current_state = state
        self.target_level = max(0.0, min(1.0, float(level)))

    def _on_tick(self):
        if not self.isVisible():
            return
        now = time.time()
        dt = min(0.06, max(0.01, now - self.last_anim_time))
        self.last_anim_time = now
        self._last_rgba = self._engine.render_rgba(self.current_state, self.target_level, dt)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # Single atomic source blit preserving 97% crystal-clear per-pixel transparency
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        rgba = self._last_rgba
        h, w, _ = rgba.shape
        qimg = QImage(rgba.data, w, h, w * 4, QImage.Format_RGBA8888)
        painter.drawImage(self.rect(), qimg)
        painter.end()

    # ------------------------------------------------------------------
    # Reconcile-Controlled Visibility with 180 ms Fade
    # ------------------------------------------------------------------
    def _cancel_pending_animations(self):
        if self._show_delay_timer is not None:
            self._show_delay_timer.stop()
            self._show_delay_timer = None
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None

    def set_reconciled_visible(self, visible: bool, delay_ms: int = 120):
        target = bool(visible)
        effective = target and self._user_visible
        if self._reconciled_visible == target and self.isVisible() == effective:
            return
        self._reconciled_visible = target
        self._cancel_pending_animations()

        if not effective:
            if self.isVisible():
                self.hide()
                logger.info("[OrbWindow] 4D Orb hidden (Dashboard / Browser WebUI active).")
            return

        if self.isVisible():
            return

        def _do_fade_in():
            if not (self._reconciled_visible and self._user_visible):
                return
            self.reposition_above_taskbar()
            self._last_rgba = self._engine.render_rgba(self.current_state, self.target_level, 0.033)
            self.setWindowOpacity(0.0)
            self.show()
            self._apply_win32_flags()
            anim = QPropertyAnimation(self, b"windowOpacity")
            anim.setDuration(180)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            self._fade_anim = anim
            anim.start()
            logger.info("[OrbWindow] 4D Wireframe Orb visible above taskbar.")

        if delay_ms > 0:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(_do_fade_in)
            self._show_delay_timer = timer
            timer.start(delay_ms)
        else:
            _do_fade_in()

    def show_orb(self):
        self._user_visible = True
        self.set_reconciled_visible(True, delay_ms=0)

    def hide_orb(self):
        self._cancel_pending_animations()
        self.hide()

    def toggle_orb(self) -> bool:
        self._user_visible = not self._user_visible
        self.set_reconciled_visible(self._reconciled_visible, delay_ms=0)
        return self._user_visible
