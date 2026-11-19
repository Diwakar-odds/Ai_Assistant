"""
Pulsar Host - Native System Tray Application (PySide6)
======================================================
Production Windows 11 system tray controller:
- Multi-DPI (16/24/32/48/64 px) crisp glowing orb vector icon.
- Persistent QMenu reference (stored on self._menu to prevent PySide6 GC bug).
- Left-click / Double-click restores and focuses the Dashboard Window.
- Full production context menu:
    Open Pulsar Dashboard | Open in Web Browser
    Toggle 4D Orb | Always Show Orb | Start with Windows
    Restart Core Engine | Open Logs Folder | Status
    Quit Pulsar
"""

import logging
from typing import Optional, Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QRadialGradient, QPen, QFont, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

logger = logging.getLogger("pulsar.host.tray")


def _draw_orb_pixmap(size: int) -> QPixmap:
    """Draws a vivid, high-contrast glowing cobalt-cyan-magenta circular orb."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    center = size / 2.0
    margin = max(1.0, size * 0.06)
    radius = (size / 2.0) - margin

    gradient = QRadialGradient(center, center, radius)
    gradient.setColorAt(0.0, QColor(255, 255, 255, 255))
    gradient.setColorAt(0.28, QColor(0, 243, 255, 255))
    gradient.setColorAt(0.68, QColor(99, 102, 241, 245))
    gradient.setColorAt(0.92, QColor(192, 38, 211, 235))
    gradient.setColorAt(1.0, QColor(192, 38, 211, 0))

    painter.setBrush(gradient)
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(int(margin), int(margin), int(size - 2 * margin), int(size - 2 * margin))

    ring_pen = QPen(QColor(0, 243, 255, 225))
    ring_pen.setWidthF(max(1.0, size * 0.06))
    painter.setPen(ring_pen)
    painter.setBrush(Qt.NoBrush)
    ring_m = max(2.0, size * 0.12)
    painter.drawEllipse(int(ring_m), int(ring_m), int(size - 2 * ring_m), int(size - 2 * ring_m))

    painter.end()
    return pixmap


def create_tray_orb_icon(size: int = 32) -> QIcon:
    """Generates a multi-DPI glowing cyan-purple circular vector icon for Windows 11."""
    icon = QIcon()
    sizes = sorted(set([16, 24, 32, 48, 64, int(size)]))
    for s in sizes:
        icon.addPixmap(_draw_orb_pixmap(s))
    return icon


class PulsarTrayIcon(QSystemTrayIcon):
    """Native Windows 11 System Tray icon for Pulsar AI Assistant."""

    def __init__(
        self,
        on_open_dashboard: Optional[Callable[[], None]] = None,
        on_open_browser: Optional[Callable[[], None]] = None,
        on_toggle_orb: Optional[Callable[[], None]] = None,
        on_toggle_always_show_orb: Optional[Callable[[bool], None]] = None,
        on_toggle_autostart: Optional[Callable[[bool], None]] = None,
        autostart_initial: bool = False,
        on_restart_core: Optional[Callable[[], None]] = None,
        on_open_logs: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.on_open_dashboard = on_open_dashboard
        self.on_open_browser = on_open_browser
        self.on_toggle_orb = on_toggle_orb
        self.on_toggle_always_show_orb = on_toggle_always_show_orb
        self.on_toggle_autostart = on_toggle_autostart
        self._autostart_initial = bool(autostart_initial)
        self.on_restart_core = on_restart_core
        self.on_open_logs = on_open_logs
        self.on_exit = on_exit

        self._icon = create_tray_orb_icon(32)
        self.setIcon(self._icon)
        self.setToolTip("Pulsar AI Assistant — Starting...")

        # Persistent menu reference so PySide6 never garbage-collects it
        self._menu: Optional[QMenu] = None
        self._build_context_menu()
        self.activated.connect(self._on_tray_activated)

    def _build_context_menu(self):
        """Constructs and retains the production right-click context menu."""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 5px;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 26px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
            QMenu::item:disabled {
                color: #94a3b8;
            }
            QMenu::separator {
                height: 1px;
                background-color: #1e293b;
                margin: 5px 10px;
            }
        """)

        # 1. Open / Show Dashboard (bold primary action)
        self.action_dashboard = QAction("Open Pulsar Dashboard", self)
        bold_font = QFont(self.action_dashboard.font())
        bold_font.setBold(True)
        self.action_dashboard.setFont(bold_font)
        if self.on_open_dashboard:
            self.action_dashboard.triggered.connect(self.on_open_dashboard)
        menu.addAction(self.action_dashboard)

        # 2. Open in Web Browser
        self.action_browser = QAction("Open in Web Browser", self)
        if self.on_open_browser:
            self.action_browser.triggered.connect(self.on_open_browser)
        menu.addAction(self.action_browser)

        menu.addSeparator()

        # 3. Toggle 4D Orb
        self.action_orb = QAction("Toggle 4D Orb", self)
        if self.on_toggle_orb:
            self.action_orb.triggered.connect(self.on_toggle_orb)
        menu.addAction(self.action_orb)

        # 4. Always Show Orb
        self.action_always_orb = QAction("Always Show Orb", self)
        self.action_always_orb.setCheckable(True)
        self.action_always_orb.setChecked(False)
        if self.on_toggle_always_show_orb:
            self.action_always_orb.toggled.connect(self.on_toggle_always_show_orb)
        menu.addAction(self.action_always_orb)

        # 5. Start with Windows (HKCU Run key)
        self.action_autostart = QAction("Start with Windows", self)
        self.action_autostart.setCheckable(True)
        self.action_autostart.setChecked(self._autostart_initial)
        if self.on_toggle_autostart:
            self.action_autostart.toggled.connect(self.on_toggle_autostart)
        menu.addAction(self.action_autostart)

        menu.addSeparator()

        # 6. Restart Core Engine
        self.action_restart_core = QAction("Restart Core Engine", self)
        if self.on_restart_core:
            self.action_restart_core.triggered.connect(self.on_restart_core)
        menu.addAction(self.action_restart_core)

        # 7. Open Logs Folder
        self.action_logs = QAction("Open Logs Folder", self)
        if self.on_open_logs:
            self.action_logs.triggered.connect(self.on_open_logs)
        menu.addAction(self.action_logs)

        # 8. Live Core Status
        self.action_status = QAction("Status: Initializing...", self)
        self.action_status.setEnabled(False)
        menu.addAction(self.action_status)

        menu.addSeparator()

        # 9. Quit Pulsar (ONLY true exit)
        self.action_exit = QAction("Quit Pulsar", self)
        if self.on_exit:
            self.action_exit.triggered.connect(self.on_exit)
        else:
            self.action_exit.triggered.connect(QApplication.quit)
        menu.addAction(self.action_exit)

        # CRITICAL: retain Python reference on self!
        self._menu = menu
        self.setContextMenu(self._menu)

    def update_core_status(self, status: str):
        """Updates the status line in the tray context menu and tooltip."""
        label = f"Status: {status.capitalize()}"
        self.action_status.setText(label)
        self.setToolTip(f"Pulsar AI Assistant ({status.capitalize()})")

    def _on_tray_activated(self, reason):
        """Handle single-click or double-click on the tray icon."""
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            if self.on_open_dashboard:
                self.on_open_dashboard()
