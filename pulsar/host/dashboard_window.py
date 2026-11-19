"""
Pulsar Host - Dashboard Window (PySide6)

Embeds the full Pulsar AI Assistant React web dashboard inside a native PySide6 window.
Features:
- Minimizes to system tray when the window close button [X] is clicked.
- Emits dashboard_opened and dashboard_closed signals to coordinate 4D Orb auto-hiding.
"""

import logging
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QIcon, QCloseEvent
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEngineScript, QWebEnginePage

from pulsar.host.tray_app import create_tray_orb_icon

logger = logging.getLogger("pulsar.host.dashboard")

LOADING_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Pulsar AI Assistant</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 0;
    background: #0f172a;
    color: #f8fafc;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    overflow: hidden;
  }
  .spinner-box {
    position: relative;
    width: 64px;
    height: 64px;
    margin-bottom: 24px;
  }
  .spinner {
    width: 64px;
    height: 64px;
    border: 3px solid rgba(0, 243, 255, 0.15);
    border-top-color: #00f3ff;
    border-radius: 50%;
    animation: spin 0.9s cubic-bezier(0.55, 0.15, 0.45, 0.85) infinite;
  }
  .glow {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 24px;
    height: 24px;
    background: radial-gradient(circle, #00f3ff 0%, transparent 70%);
    filter: blur(4px);
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  h2 {
    font-size: 22px;
    font-weight: 600;
    margin: 0 0 10px 0;
    background: linear-gradient(135deg, #00f3ff 0%, #a855f7 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  p {
    color: #94a3b8;
    font-size: 14px;
    margin: 0;
  }
  .badge {
    margin-top: 16px;
    padding: 4px 12px;
    background: rgba(30, 41, 59, 0.8);
    border: 1px solid rgba(51, 65, 85, 0.6);
    border-radius: 9999px;
    font-size: 12px;
    color: #38bdf8;
  }
</style>
</head>
<body>
  <div class="spinner-box">
    <div class="spinner"></div>
    <div class="glow"></div>
  </div>
  <h2>Pulsar AI Assistant</h2>
  <p>Starting Core Engine & Pre-warming Neural Pipeline...</p>
  <div class="badge">Decoupled Architecture &bull; Port 5000</div>
</body>
</html>
"""


class SilentWebEnginePage(QWebEnginePage):
    """Suppresses raw Chromium/MediaPipe/OpenGL console spam from polluting the developer terminal."""
    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        # Completely silent in terminal
        pass


class DashboardWindow(QMainWindow):
    """Native window displaying the Pulsar Web Application."""

    dashboard_opened = Signal()
    dashboard_closed = Signal()
    closed_to_tray = Signal()

    def __init__(self, port: int = 5000, parent=None):
        super().__init__(parent)
        self.port = port
        self.dashboard_url = QUrl(f"http://127.0.0.1:{self.port}/")
        self._render_recovery_count = 0
        self._force_quit = False
        self._loaded_live_url = False
        self._taskbar_identity_bound = False

        self.setWindowTitle("Pulsar AI Assistant")
        try:
            from pulsar.host.windows_integration import get_app_icon_path
            ico = get_app_icon_path()
            if ico.exists():
                self.setWindowIcon(QIcon(str(ico)))
            else:
                self.setWindowIcon(create_tray_orb_icon(64))
        except Exception:
            self.setWindowIcon(create_tray_orb_icon(64))
        self._center_on_screen()

        # Web view setup
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView(self)
        self.web_page = SilentWebEnginePage(self.web_view)
        self.web_view.setPage(self.web_page)

        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)

        # Show elegant dark loader until Core reaches ready
        self.web_view.setHtml(LOADING_HTML)

        # Polyfill unsupported Chromium Web Speech API (media.mojom.SpeechRecognizer)
        # with safe JavaScript stub to prevent bad IPC Mojo crash (reason 123) in QtWebEngine
        speech_guard_script = QWebEngineScript()
        speech_guard_script.setName("polyfill_unsupported_web_speech")
        speech_guard_script.setSourceCode("""
        (function() {
            class DummySpeechRecognition {
                constructor() {
                    this.continuous = false;
                    this.interimResults = false;
                    this.lang = '';
                    this.maxAlternatives = 1;
                    this.onresult = null;
                    this.onerror = null;
                    this.onend = null;
                    this.onstart = null;
                }
                start() {}
                stop() {}
                abort() {}
                addEventListener() {}
                removeEventListener() {}
                dispatchEvent() { return false; }
            }
            try {
                window.webkitSpeechRecognition = DummySpeechRecognition;
                window.SpeechRecognition = DummySpeechRecognition;
                if (window.Window && window.Window.prototype) {
                    window.Window.prototype.webkitSpeechRecognition = DummySpeechRecognition;
                    window.Window.prototype.SpeechRecognition = DummySpeechRecognition;
                }
            } catch (e) {}
        })();
        """)
        speech_guard_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        speech_guard_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        speech_guard_script.setRunsOnSubFrames(True)
        self.web_page.scripts().insert(speech_guard_script)
        self.web_page.renderProcessTerminated.connect(self._on_renderer_terminated)

        layout.addWidget(self.web_view)

    def _on_renderer_terminated(self, status, exit_code):
        logger.warning(f"[Dashboard] Renderer terminated (status: {status}, code: {exit_code}).")
        if self._render_recovery_count < 2:
            self._render_recovery_count += 1
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, self.load_dashboard)

    def _center_on_screen(self):
        """Centers window on primary screen adapting dynamically to work area."""
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            w = min(1200, max(800, int(geo.width() * 0.90)))
            h = min(800, max(550, int(geo.height() * 0.88)))
            x = geo.x() + (geo.width() - w) // 2
            y = geo.y() + (geo.height() - h) // 2
            self.setGeometry(x, y, w, h)
        else:
            self.resize(1000, 700)

    def allow_real_close(self):
        """Permits closeEvent to accept and destroy the window during application Quit."""
        self._force_quit = True

    def load_dashboard(self, focus_if_visible: bool = True):
        """Loads the React dashboard URL cleanly."""
        logger.info(f"[Dashboard] Navigating to {self.dashboard_url.toString()}")
        self._loaded_live_url = True
        self.web_view.setUrl(self.dashboard_url)
        if focus_if_visible and self.isVisible() and not self.isMinimized():
            self.raise_()
            self.activateWindow()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._taskbar_identity_bound:
            self._taskbar_identity_bound = True
            try:
                from pulsar.host.windows_integration import configure_window_taskbar_identity
                configure_window_taskbar_identity(int(self.winId()))
            except Exception:
                pass

    def show_and_focus(self):
        """Restores/shows the dashboard, forces foreground focus on Windows 11, and triggers reconcile()."""
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        try:
            from pulsar.host.windows_integration import force_window_foreground
            force_window_foreground(int(self.winId()))
        except Exception:
            pass
        self.dashboard_opened.emit()
        logger.info("[Dashboard] Window opened and focused.")

    def closeEvent(self, event: QCloseEvent):
        """
        Intercepts window close button [X].
        Hides window to tray instead of quitting unless Quit was explicitly requested.
        """
        if self._force_quit:
            event.accept()
            return
        event.ignore()
        self.hide()
        self.closed_to_tray.emit()
        self.dashboard_closed.emit()
        logger.info("[Dashboard] Window closed to system tray.")

    def changeEvent(self, event):
        """Detect minimize/restore events to trigger reconcile()."""
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized():
                self.dashboard_closed.emit()
            elif self.isVisible() and not self.isMinimized():
                self.dashboard_opened.emit()
