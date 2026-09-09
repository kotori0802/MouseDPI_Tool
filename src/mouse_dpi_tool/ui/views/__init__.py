"""Main application window shell."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from mouse_dpi_tool.ui.controllers import AppController
from mouse_dpi_tool.ui.views.pages import CapturePage, ResultsPage, SettingsPage, SetupPage


def _system_is_dark() -> bool:
    scheme = QGuiApplication.styleHints().colorScheme()
    return scheme == Qt.ColorScheme.Dark


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController | None = None) -> None:
        super().__init__()
        self.controller = controller or AppController()
        self.controller.set_system_is_dark(_system_is_dark())
        self.setMinimumSize(960, 640)
        # Operator preference: open maximized (portfolio / lab monitor presentation).
        # Geometry preferences remain presentation-only (not Session evidence).
        if bool(self.controller.preferences.get("start_maximized", True)):
            self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
        else:
            w = int(self.controller.preferences.get("window_width", 1180))
            h = int(self.controller.preferences.get("window_height", 760))
            self.resize(w, h)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(220)
        side_l = QVBoxLayout(self.sidebar)
        side_l.setContentsMargins(16, 20, 16, 20)
        side_l.setSpacing(8)
        self.brand = QLabel("Mouse DPI Tool")
        self.brand.setObjectName("SectionTitle")
        side_l.addWidget(self.brand)
        side_l.addSpacing(12)

        self.nav_buttons: dict[str, QPushButton] = {}
        self.stack = QStackedWidget()
        self.setup_page = SetupPage(self.controller)
        self.capture_page = CapturePage(self.controller)
        self.results_page = ResultsPage(self.controller)
        self.settings_page = SettingsPage(self.controller, on_prefs_changed=self.apply_presentation)
        for key, page in (
            ("setup", self.setup_page),
            ("capture", self.capture_page),
            ("results", self.results_page),
            ("settings", self.settings_page),
        ):
            btn = QPushButton()
            btn.setProperty("class", "NavButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, k=key: self._navigate(k))
            self.nav_buttons[key] = btn
            side_l.addWidget(btn)
            self.stack.addWidget(page)
        side_l.addStretch(1)
        self.help_btn = QPushButton()
        self.help_btn.setProperty("class", "NavButton")
        self.help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.help_btn.clicked.connect(self._open_user_guide)
        side_l.addWidget(self.help_btn)

        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)
        self._navigate("setup")
        self.apply_presentation()

        # Window-level shortcuts so F5/ESC work even when Capture page lost focus
        # to another child after Admit (WidgetWithChildren alone was unreliable).
        self._shortcut_f5 = QShortcut(QKeySequence(Qt.Key.Key_F5), self)
        self._shortcut_f5.setContext(Qt.ShortcutContext.WindowShortcut)
        self._shortcut_f5.activated.connect(self._on_window_f5)
        self._shortcut_esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._shortcut_esc.setContext(Qt.ShortcutContext.WindowShortcut)
        self._shortcut_esc.activated.connect(self._on_window_esc)

        self.capture_page.refresh_requested.connect(self._on_capture_refresh_request)
        self.capture_page.nav_sync_needed.connect(self._sync_nav_lock)
        self.results_page.go_to_capture.connect(lambda: self._navigate("capture"))
        self.results_page.open_user_guide.connect(self._open_user_guide)

        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(self._on_system_color_scheme_changed)

        app = QApplication.instance()
        if app is not None and hasattr(app, "applicationStateChanged"):
            app.applicationStateChanged.connect(self._on_application_state_changed)

    def _open_user_guide(self) -> None:
        from mouse_dpi_tool.ui.components.user_guide_dialog import UserGuideDialog

        dlg = UserGuideDialog(self.controller, self)
        dlg.exec()

    def _on_window_f5(self) -> None:
        if self.stack.currentWidget() is self.capture_page:
            self.capture_page._on_f5()

    def _on_window_esc(self) -> None:
        if self.stack.currentWidget() is self.capture_page:
            self.capture_page._on_esc()

    def _on_capture_refresh_request(self) -> None:
        self.capture_page.refresh()
        self._sync_nav_lock()

    def _sync_nav_lock(self) -> None:
        from mouse_dpi_tool.ui.presentation_invalidation import COUNTERS

        locked = self.controller.capture_navigation_locked
        current = self.stack.currentWidget()
        for name, btn in self.nav_buttons.items():
            want_enabled = (not locked) or name == "capture"
            if btn.isEnabled() != want_enabled:
                btn.setEnabled(want_enabled)
                COUNTERS.sidebar_polish_calls += 1
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            if locked and current is not self.capture_page and name == "capture":
                self.stack.setCurrentIndex(1)
                btn.setProperty("active", "true")
                COUNTERS.sidebar_polish_calls += 1
                btn.style().unpolish(btn)
                btn.style().polish(btn)

    def _on_application_state_changed(self, state) -> None:
        # Lost foreground → cancel RUNNING only (does not touch STOPPED pending).
        inactive = state in (
            Qt.ApplicationState.ApplicationInactive,
            Qt.ApplicationState.ApplicationHidden,
        )
        if inactive:
            # Ownership boundary: never let a pending Stop/Cancel survive deactivation.
            self.capture_page._clear_pending_capture_op(reason="app_deactivate")
            if self.controller.handle_application_deactivated():
                self.capture_page.message_label.setText(
                    self.controller.i18n.t("capture.focus_lost")
                )
                self.capture_page.refresh()
                if self.stack.currentWidget() is self.setup_page:
                    self.setup_page.refresh()
            return
        if state != Qt.ApplicationState.ApplicationActive:
            return
        # Defensive repaint from presentation snapshots — no evidence mutation.
        page = self.stack.currentWidget()
        if page is self.capture_page:
            self.capture_page.refresh()
        elif page is self.results_page:
            self.results_page.refresh()
        elif page is self.setup_page:
            self.setup_page.refresh()
        elif page is self.settings_page:
            self.settings_page.retranslate()

    def _on_system_color_scheme_changed(self, *_args) -> None:
        self.controller.set_system_is_dark(_system_is_dark())
        if self.controller.theme.mode == "system":
            self.apply_presentation()

    def _navigate(self, key: str) -> None:
        if key != "capture" and self.controller.capture_navigation_locked:
            # Fail-safe: never leave Capture while Raw Input may still be collecting.
            if self.stack.currentWidget() is not self.capture_page:
                self.stack.setCurrentIndex(1)
            for name, btn in self.nav_buttons.items():
                btn.setProperty("active", "true" if name == "capture" else "false")
                btn.setEnabled(name == "capture")
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            self.capture_page.message_label.setText(
                self.controller.i18n.t("capture.nav_locked")
            )
            self.capture_page.refresh()
            return
        index = {"setup": 0, "capture": 1, "results": 2, "settings": 3}[key]
        self.stack.setCurrentIndex(index)
        locked = self.controller.capture_navigation_locked
        for name, btn in self.nav_buttons.items():
            btn.setProperty("active", "true" if name == key else "false")
            btn.setEnabled((not locked) or name == "capture")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if key == "results":
            self.results_page.refresh()
        elif key == "capture":
            self.capture_page.refresh()
        elif key == "setup":
            self.setup_page.refresh()

    def apply_presentation(self) -> None:
        from mouse_dpi_tool.ui.presentation_invalidation import REVISIONS

        # Always bump locale+theme revision so skip-caches cannot keep stale strings.
        REVISIONS.bump_locale()
        REVISIONS.bump_theme()
        self.setWindowTitle(self.controller.i18n.t("app.title"))
        self.brand.setText(self.controller.i18n.t("app.title"))
        self.nav_buttons["setup"].setText(self.controller.i18n.t("nav.setup"))
        self.nav_buttons["capture"].setText(self.controller.i18n.t("nav.capture"))
        self.nav_buttons["results"].setText(self.controller.i18n.t("nav.results"))
        self.nav_buttons["settings"].setText(self.controller.i18n.t("nav.settings"))
        self.help_btn.setText(self.controller.i18n.t("help.guide.open"))
        self.setup_page.retranslate()
        self.capture_page.retranslate()
        self.results_page.retranslate()
        self.settings_page.retranslate()
        self.setStyleSheet(self.controller.theme.qss())

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        # Best-effort capture/helper cleanup so Raw Input subprocess does not linger.
        try:
            if self.capture_page._thread is not None and self.capture_page._thread.isRunning():
                self.capture_page._thread.wait(3000)
        except Exception:
            pass
        try:
            self.controller.shutdown_capture()
        except Exception:
            pass
        super().closeEvent(event)
