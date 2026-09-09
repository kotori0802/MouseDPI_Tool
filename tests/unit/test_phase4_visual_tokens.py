"""Phase 4 — Visual tokens / chrome (presentation only)."""

from __future__ import annotations

import pytest


@pytest.fixture
def qapp():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_empty_state_title_role_transparent(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.theme.tokens import DARK, LIGHT, stylesheet
    from mouse_dpi_tool.ui.views.pages import ResultsPage

    for tok in (LIGHT, DARK):
        css = stylesheet(tok)
        assert "QLabel#EmptyStateTitle" in css
        block = css.split("QLabel#EmptyStateTitle")[1].split("}")[0]
        assert "background: transparent" in block
        assert "border: none" in block

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = ResultsPage(ctl)
    page.refresh()
    assert page.empty_title.objectName() == "EmptyStateTitle"
    assert page.empty_title.objectName() != "SectionTitle"


def test_section_title_transparent_no_fill_strip(qapp):
    from mouse_dpi_tool.ui.theme.tokens import DARK, stylesheet

    css = stylesheet(DARK)
    block = css.split("QLabel#SectionTitle")[1].split("}")[0]
    assert "background: transparent" in block


def test_selected_focus_primary_roles_separated(qapp):
    from mouse_dpi_tool.ui.theme.tokens import LIGHT, stylesheet

    css = stylesheet(LIGHT)
    # Selected Geometry: soft tint + accent border (not sole solid-blue chrome).
    geo_sel = css.split("QFrame#GeometryTile[selected=\"true\"]")[1].split("}")[0]
    assert "accent_soft" in geo_sel or "#E8F1FC" in geo_sel
    # Focus ring distinct rule exists.
    assert "QFrame#GeometryTile:focus" in css
    assert "QPushButton#PrimaryButton" in css
    # Nav selected scoped — soft, not Primary solid fill.
    assert 'QPushButton[class="NavButton"][active="true"]' in css
    nav = css.split('QPushButton[class="NavButton"][active="true"]')[1].split("}")[0]
    assert "PrimaryButton" not in nav
    assert "#0071E3" not in nav or "accent_soft" in nav or "#E8F1FC" in nav


def test_capture_action_bar_command_zone_chrome(qapp):
    from mouse_dpi_tool.ui.theme.tokens import LIGHT, stylesheet
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.pages import CapturePage

    css = stylesheet(LIGHT)
    assert "QWidget#CaptureActionBar" in css
    bar = css.split("QWidget#CaptureActionBar")[1].split("}")[0]
    assert "transparent" in bar
    ctl = AppController(preferences={"theme": "light", "locale": "en-US"})
    page = CapturePage(ctl)
    assert page.action_bar.objectName() == "CaptureActionBar"
    assert page.shortcut_hint.objectName() == "CaptureCommandHint"


def test_setup_internal_panels_transparent_surface(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.setup_page import SetupPage

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = SetupPage(ctl)
    assert page._dut_panel.objectName() == "TransparentSurface"
    assert page._meas_panel.objectName() == "TransparentSurface"
