#!/usr/bin/env python3
"""
Pulsar AI Assistant - Phase 1: Standalone 4D Orb Prototype Spike
================================================================
PySide6 Standalone Prototype:
- Fully transparent, click-through, topmost 4D particle orb overlay.
- Positioned flush above the Windows taskbar using screen().availableGeometry().
- High-throughput 60 FPS WebGL/Canvas rendering with smooth color/vibration state cycling.
- Includes QPainter native fallback for dual-mode verification.
- Logs FPS to console every second.
"""

import sys
import os
import math
import time
from typing import Optional

# Ensure high-DPI scaling is enabled before QApplication
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PySide6.QtCore import Qt, QTimer, QUrl, QPoint, QSize
from PySide6.QtGui import QColor, QPainter, QRadialGradient, QBrush, QPen, QFont
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout

# Check WebEngine availability
WEBENGINE_AVAILABLE = False
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEnginePage
    WEBENGINE_AVAILABLE = True
except ImportError:
    pass

ORB_SIZE = 240

# HTML / WebGL / Canvas for the 60 FPS Particle Orb
HTML_CANVAS_ORB = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: transparent !important;
  }
  canvas {
    display: block;
    width: 240px;
    height: 240px;
    background: transparent !important;
  }
</style>
</head>
<body>
<canvas id="orbCanvas" width="240" height="240"></canvas>
<script>
const canvas = document.getElementById('orbCanvas');
const ctx = canvas.getContext('2d');

const NUM_PARTICLES = 220;
const particles = [];
let currentState = 'idle';
let currentLevel = 0.0;
let lastTime = performance.now();
let frameCount = 0;
let lastFpsUpdate = performance.now();
let fps = 60;

// State Color Palettes [R, G, B]
const PALETTES = {
  idle:      { core: [0, 243, 255], outer: [139, 92, 246], halo: 'rgba(0, 243, 255, 0.15)' },
  listening: { core: [0, 255, 200], outer: [56, 189, 248], halo: 'rgba(0, 255, 200, 0.35)' },
  speaking:  { core: [236, 72, 153], outer: [168, 85, 247], halo: 'rgba(236, 72, 153, 0.35)' },
  thinking:  { core: [245, 158, 11], outer: [239, 68, 68],  halo: 'rgba(245, 158, 11, 0.25)' },
  error:     { core: [239, 68, 68],  outer: [185, 28, 28],  halo: 'rgba(239, 68, 68, 0.40)' }
};

// Initialize Fibonacci spherical particle distribution
for (let i = 0; i < NUM_PARTICLES; i++) {
  const phi = Math.acos(1 - 2 * (i + 0.5) / NUM_PARTICLES);
  const theta = Math.PI * (1 + Math.sqrt(5)) * (i + 0.5);
  particles.push({
    x: Math.sin(phi) * Math.cos(theta),
    y: Math.sin(phi) * Math.sin(theta),
    z: Math.cos(phi),
    baseSize: 1.2 + Math.random() * 2.2,
    speed: 0.4 + Math.random() * 0.8,
    phase: Math.random() * Math.PI * 2
  });
}

let rotX = 0, rotY = 0, rotZ = 0;

function render(now) {
  requestAnimationFrame(render);
  const dt = (now - lastTime) / 1000.0;
  lastTime = now;

  frameCount++;
  if (now - lastFpsUpdate >= 1000) {
    fps = frameCount;
    frameCount = 0;
    lastFpsUpdate = now;
  }

  ctx.clearRect(0, 0, 240, 240);

  const cx = 120, cy = 120;
  const p = PALETTES[currentState] || PALETTES.idle;
  
  // Speed shifts by state
  const rotSpeed = currentState === 'thinking' ? 2.5 : (currentState === 'speaking' ? 1.4 : 0.8);
  rotX += dt * 0.7 * rotSpeed;
  rotY += dt * 1.1 * rotSpeed;
  rotZ += dt * 0.4 * rotSpeed;

  const baseRadius = 55 + currentLevel * 32.0;

  // 1. Draw soft pulsing central glow halo
  const glowRad = baseRadius * (1.1 + Math.sin(now * 0.003) * 0.08);
  const grad = ctx.createRadialGradient(cx, cy, 10, cx, cy, glowRad);
  grad.addColorStop(0, p.halo);
  grad.addColorStop(0.6, p.halo.replace(/[^,]+(?=\))/, '0.08'));
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.arc(cx, cy, glowRad, 0, Math.PI * 2);
  ctx.fill();

  // 2. Project & Render 3D Wireframe Particles
  ctx.globalCompositeOperation = 'lighter';
  
  const cosX = Math.cos(rotX), sinX = Math.sin(rotX);
  const cosY = Math.cos(rotY), sinY = Math.sin(rotY);
  const cosZ = Math.cos(rotZ), sinZ = Math.sin(rotZ);

  for (let i = 0; i < NUM_PARTICLES; i++) {
    const pt = particles[i];
    
    // Pulse individual particle radially with level
    const vibr = Math.sin(now * 0.008 * pt.speed + pt.phase) * (currentLevel * 14.0);
    const r = baseRadius + vibr;

    // 3D rotation
    let px = pt.x * r, py = pt.y * r, pz = pt.z * r;
    
    // Y rotation
    let x1 = px * cosY + pz * sinY;
    let z1 = -px * sinY + pz * cosY;
    // X rotation
    let y2 = py * cosX - z1 * sinX;
    let z2 = py * sinX + z1 * cosX;
    // Z rotation
    let x3 = x1 * cosZ - y2 * sinZ;
    let y3 = x1 * sinZ + y2 * cosZ;

    // Perspective projection
    const fov = 300;
    const scale = fov / (fov + z2 + 80);
    const screenX = cx + x3 * scale;
    const screenY = cy + y3 * scale;

    if (scale <= 0) continue;

    // Depth-based brightness & size
    const normDepth = Math.max(0.1, Math.min(1.0, (z2 + baseRadius) / (2 * baseRadius)));
    const size = pt.baseSize * scale * (1.0 + currentLevel * 0.6);
    
    // Interpolate core to outer color based on depth
    const red = Math.round(p.core[0] * normDepth + p.outer[0] * (1 - normDepth));
    const green = Math.round(p.core[1] * normDepth + p.outer[1] * (1 - normDepth));
    const blue = Math.round(p.core[2] * normDepth + p.outer[2] * (1 - normDepth));
    const alpha = (0.35 + 0.65 * normDepth) * (0.8 + currentLevel * 0.2);

    ctx.fillStyle = `rgba(${red}, ${green}, ${blue}, ${alpha.toFixed(2)})`;
    ctx.beginPath();
    ctx.arc(screenX, screenY, Math.max(0.8, size), 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.globalCompositeOperation = 'source-over';
}

// Global API called from Python Qt
window.setOrbState = function(state, level) {
  currentState = state;
  currentLevel = Math.max(0.0, Math.min(1.0, level));
};

window.getFps = function() {
  return fps;
};

requestAnimationFrame(render);
</script>
</body>
</html>
"""


class WebEngineOrbWindow(QWidget):
    """Primary WebGL/Canvas Particle Orb Window powered by QWebEngineView."""

    def __init__(self):
        super().__init__()
        self.state_index = 0
        self.states = ["idle", "listening", "speaking", "thinking"]
        self.current_state = "idle"
        self.current_level = 0.0
        self.fps_counter = 0
        self.last_fps_time = time.time()

        self._init_window()
        self._init_webview()
        self._init_position()
        self._init_timers()

    def _init_window(self):
        # Frameless, Always on Top, Click-through transparent
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(ORB_SIZE, ORB_SIZE)

    def _init_webview(self):
        self.view = QWebEngineView(self)
        self.view.setStyleSheet("background: transparent;")
        self.view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self.view.setHtml(HTML_CANVAS_ORB)
        self.view.setFixedSize(ORB_SIZE, ORB_SIZE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

    def _init_position(self):
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry()
        x = avail.x() + (avail.width() - ORB_SIZE) // 2
        y = avail.y() + avail.height() - ORB_SIZE
        self.setGeometry(x, y, ORB_SIZE, ORB_SIZE)
        print(f"[ORB POSITION] Placed at ({x}, {y}) flush above workarea [bottom={avail.bottom()}].")

    def _init_timers(self):
        # State cycling timer (every 4s)
        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self._cycle_state)
        self.state_timer.start(4000)

        # 30-60 Hz Audio Level & Animation simulation timer (every 33ms)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_anim)
        self.anim_timer.start(33)

        # 1-second FPS console reporting timer
        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self._log_fps)
        self.fps_timer.start(1000)

    def _cycle_state(self):
        self.state_index = (self.state_index + 1) % len(self.states)
        self.current_state = self.states[self.state_index]
        print(f"\n[STATE CYCLE] -> Switched to: '{self.current_state.upper()}'")

    def _update_anim(self):
        t = time.time()
        # Simulated audio envelope: reactive sine pulses
        if self.current_state == "idle":
            self.current_level = 0.05 + 0.05 * math.sin(t * 3.0)
        elif self.current_state == "listening":
            self.current_level = 0.25 + 0.20 * math.sin(t * 8.0)
        elif self.current_state == "speaking":
            self.current_level = 0.40 + 0.35 * abs(math.sin(t * 12.0) * math.cos(t * 5.0))
        elif self.current_state == "thinking":
            self.current_level = 0.15 + 0.10 * math.sin(t * 6.0)

        # Push state and level to WebGL/Canvas
        js_cmd = f"window.setOrbState('{self.current_state}', {self.current_level:.3f});"
        self.view.page().runJavaScript(js_cmd)
        self.fps_counter += 1

    def _log_fps(self):
        now = time.time()
        elapsed = now - self.last_fps_time
        actual_fps = self.fps_counter / elapsed if elapsed > 0 else 60.0
        self.fps_counter = 0
        self.last_fps_time = now

        # Ask WebGL canvas for its internal render loop FPS
        def _on_web_fps(web_fps):
            render_fps = int(web_fps) if web_fps else int(actual_fps)
            print(f"[FPS: {render_fps:2d}] State: {self.current_state:9s} | Level: {self.current_level:.2f} | Pos: ({self.x()}, {self.y()})")

        self.view.page().runJavaScript("window.getFps();", _on_web_fps)

    def showEvent(self, event):
        super().showEvent(event)
        # Ensure Win32 layered click-through is explicitly locked at the OS level
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                GWL_EXSTYLE = -20
                WS_EX_LAYERED = 0x00080000
                WS_EX_TRANSPARENT = 0x00000020
                WS_EX_TOOLWINDOW = 0x00000080
                WS_EX_NOACTIVATE = 0x08000000
                user32 = ctypes.windll.user32
                ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
            except Exception:
                pass


class QPainterOrbFallbackWindow(QWidget):
    """High-performance native QPainter fallback window (max 600 particles)."""

    def __init__(self):
        super().__init__()
        self.states = ["idle", "listening", "speaking", "thinking"]
        self.state_idx = 0
        self.current_state = "idle"
        self.level = 0.0
        self.rot_x = 0.0
        self.rot_y = 0.0
        self.rot_z = 0.0
        self.fps_count = 0
        self.last_fps_time = time.time()
        self.fps = 60

        self.palettes = {
            "idle": (QColor(0, 243, 255), QColor(139, 92, 246)),
            "listening": (QColor(0, 255, 200), QColor(56, 189, 248)),
            "speaking": (QColor(236, 72, 153), QColor(168, 85, 247)),
            "thinking": (QColor(245, 158, 11), QColor(239, 68, 68)),
        }

        # Fibonacci sphere particles
        self.num_particles = 320
        self.particles = []
        for i in range(self.num_particles):
            phi = math.acos(1 - 2 * (i + 0.5) / self.num_particles)
            theta = math.pi * (1 + math.sqrt(5)) * (i + 0.5)
            self.particles.append((
                math.sin(phi) * math.cos(theta),
                math.sin(phi) * math.sin(theta),
                math.cos(phi),
                1.5 + (i % 3) * 0.8, # size
                0.5 + (i % 5) * 0.2, # speed
            ))

        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(ORB_SIZE, ORB_SIZE)

        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry()
        x = avail.x() + (avail.width() - ORB_SIZE) // 2
        y = avail.y() + avail.height() - ORB_SIZE
        self.setGeometry(x, y, ORB_SIZE, ORB_SIZE)

        # Timers
        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self._cycle_state)
        self.state_timer.start(4000)

        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self.update)
        self.render_timer.start(16) # ~60 FPS

        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self._log_fps)
        self.fps_timer.start(1000)

    def _cycle_state(self):
        self.state_idx = (self.state_idx + 1) % len(self.states)
        self.current_state = self.states[self.state_idx]
        print(f"\n[STATE CYCLE QPAINTER] -> '{self.current_state.upper()}'")

    def _log_fps(self):
        now = time.time()
        elapsed = now - self.last_fps_time
        self.fps = int(self.fps_count / elapsed) if elapsed > 0 else 60
        self.fps_count = 0
        self.last_fps_time = now
        print(f"[QPAINTER FPS: {self.fps:2d}] State: {self.current_state:9s} | Level: {self.level:.2f}")

    def paintEvent(self, event):
        self.fps_count += 1
        t = time.time()
        dt = 0.016

        # Simulate audio level
        if self.current_state == "idle":
            self.level = 0.05 + 0.05 * math.sin(t * 3.0)
        elif self.current_state == "listening":
            self.level = 0.25 + 0.20 * math.sin(t * 8.0)
        elif self.current_state == "speaking":
            self.level = 0.40 + 0.35 * abs(math.sin(t * 12.0) * math.cos(t * 5.0))
        elif self.current_state == "thinking":
            self.level = 0.15 + 0.10 * math.sin(t * 6.0)

        rot_speed = 2.5 if self.current_state == "thinking" else (1.4 if self.current_state == "speaking" else 0.8)
        self.rot_x += dt * 0.7 * rot_speed
        self.rot_y += dt * 1.1 * rot_speed
        self.rot_z += dt * 0.4 * rot_speed

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        cx, cy = ORB_SIZE / 2.0, ORB_SIZE / 2.0
        base_r = 55.0 + self.level * 32.0

        c_core, c_outer = self.palettes.get(self.current_state, self.palettes["idle"])

        # Radial glow halo
        halo_grad = QRadialGradient(cx, cy, base_r * 1.2)
        c_halo = QColor(c_core)
        c_halo.setAlpha(60)
        halo_grad.setColorAt(0.0, c_halo)
        halo_grad.setColorAt(0.7, QColor(c_core.red(), c_core.green(), c_core.blue(), 15))
        halo_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(halo_grad))
        painter.drawEllipse(QPoint(int(cx), int(cy)), int(base_r * 1.2), int(base_r * 1.2))

        # Rotate & draw particles
        cos_x, sin_x = math.cos(self.rot_x), math.sin(self.rot_x)
        cos_y, sin_y = math.cos(self.rot_y), math.sin(self.rot_y)
        cos_z, sin_z = math.cos(self.rot_z), math.sin(self.rot_z)

        fov = 300.0
        for px, py, pz, psize, pspeed in self.particles:
            vibr = math.sin(t * 8.0 * pspeed) * (self.level * 14.0)
            r = base_r + vibr

            x0, y0, z0 = px * r, py * r, pz * r

            # Y
            x1 = x0 * cos_y + z0 * sin_y
            z1 = -x0 * sin_y + z0 * cos_y
            # X
            y2 = y0 * cos_x - z1 * sin_x
            z2 = y0 * sin_x + z1 * cos_x
            # Z
            x3 = x1 * cos_z - y2 * sin_z
            y3 = x1 * sin_z + y2 * cos_z

            scale = fov / (fov + z2 + 80.0)
            if scale <= 0:
                continue

            sx = cx + x3 * scale
            sy = cy + y3 * scale

            norm_depth = max(0.1, min(1.0, (z2 + base_r) / (2.0 * base_r)))
            dot_size = max(1.0, psize * scale * (1.0 + self.level * 0.5))

            r_col = int(c_core.red() * norm_depth + c_outer.red() * (1 - norm_depth))
            g_col = int(c_core.green() * norm_depth + c_outer.green() * (1 - norm_depth))
            b_col = int(c_core.blue() * norm_depth + c_outer.blue() * (1 - norm_depth))
            alpha = int(255 * (0.35 + 0.65 * norm_depth) * (0.8 + self.level * 0.2))

            painter.setBrush(QBrush(QColor(r_col, g_col, b_col, alpha)))
            painter.drawEllipse(QPoint(int(sx), int(sy)), int(dot_size), int(dot_size))

        painter.end()


def main():
    app = QApplication(sys.argv)
    
    use_fallback = "--painter" in sys.argv or not WEBENGINE_AVAILABLE
    if use_fallback:
        print("[ORB SPIKE] Launching Native QPainter Fallback Window...")
        window = QPainterOrbFallbackWindow()
    else:
        print("[ORB SPIKE] Launching Primary QtWebEngine WebGL Canvas Window...")
        window = WebEngineOrbWindow()

    window.show()
    print("[ORB SPIKE] Window is shown and floating above taskbar.")
    print("[ORB SPIKE] Pass Criteria Check: Transparent background, 60 FPS, click-through, topmost.")
    print("[ORB SPIKE] Press Ctrl+C in terminal to exit.")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
