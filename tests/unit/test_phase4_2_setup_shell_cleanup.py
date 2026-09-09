"""Phase 4.2 corrected — intentional outer Cards; transparent structural wrappers."""

from __future__ import annotations

import pytest


@pytest.fixture
def qapp():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_setup_one_outer_card_transparent_internals(qapp):
    from PySide6.QtWidgets import QFrame, QWidget

    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.setup_page import SetupPage

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = SetupPage(ctl)
    assert page._form_card.objectName() == "Card"
    surfaces = [w for w in page.findChildren(QWidget) if w.objectName() == "TransparentSurface"]
    assert len(surfaces) >= 2
    nested_cards = [
        w
        for w in page._form_card.findChildren(QFrame)
        if w is not page._form_card and w.objectName() == "Card"
    ]
    assert nested_cards == []


def test_settings_one_outer_card_bounded_width(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.layout_metrics import SETTINGS_PANEL_MAX_WIDTH
    from mouse_dpi_tool.ui.views.pages import SettingsPage

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = SettingsPage(ctl, on_prefs_changed=lambda: None)
    assert page._form_card.objectName() == "Card"
    assert page._form_card.maximumWidth() == SETTINGS_PANEL_MAX_WIDTH


def test_capture_shell_is_intentional_surface(qapp):
    from PySide6.QtWidgets import QFrame

    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.theme.tokens import DARK, stylesheet
    from mouse_dpi_tool.ui.views.pages import CapturePage

    css = stylesheet(DARK)
    shell = css.split("QFrame#CaptureShell")[1].split("}")[0]
    assert "transparent" not in shell.replace(" ", "")
    assert "background:" in shell.replace(" ", "") or "background-color:" in shell.replace(
        " ", ""
    )

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = CapturePage(ctl)
    shells = [w for w in page.findChildren(QFrame) if w.objectName() == "CaptureShell"]
    assert len(shells) == 1
    headers = [w for w in page.findChildren(QFrame) if w.objectName() == "CaptureHeader"]
    assert len(headers) == 1
    assert page.scroll.widget().objectName() == "TransparentSurface"
    assert page.action_bar.objectName() == "CaptureActionBar"
    assert page.viz.objectName() == "EvidenceCanvasHost"
