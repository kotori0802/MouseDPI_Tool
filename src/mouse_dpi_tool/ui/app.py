"""Qt application entrypoint."""

from __future__ import annotations

import sys


def run(argv: list[str] | None = None) -> int:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views import MainWindow

    app = QApplication(argv or sys.argv)
    app.setApplicationName("Mouse DPI Tool")
    controller = AppController()
    # Seed Follow-system from OS color scheme before first paint.
    scheme = QGuiApplication.styleHints().colorScheme()
    controller.set_system_is_dark(scheme == Qt.ColorScheme.Dark)
    window = MainWindow(controller)
    window.show()
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    return run(argv)
