"""UI-3B.0b — Layout density & form rhythm (presentation-only)."""

from __future__ import annotations

import pytest

from mouse_dpi_tool.ui.controllers import AppController
from mouse_dpi_tool.ui.layout_metrics import (
    SPACE_CAPTURE_FILTER_GAP,
    SPACE_FORM_GROUP,
)
from mouse_dpi_tool.ui.presentation_invalidation import COUNTERS, reset_presentation_instrumentation


@pytest.fixture
def qapp():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_setup_form_max_width_and_form_labels(qapp):
    from mouse_dpi_tool.ui.layout_metrics import SETUP_WORKSPACE_MAX_WIDTH
    from mouse_dpi_tool.ui.views.pages import SetupPage

    controller = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = SetupPage(controller)
    # Phase 3.1: Setup workspace band is logical-px capped, not ~96ch.
    assert page._form_card.maximumWidth() == SETUP_WORKSPACE_MAX_WIDTH
    assert page._vendor_label.objectName() == "FormLabel"
    assert page._distance_label.objectName() == "FormLabel"
    assert page._group_dut.objectName() == "FormGroupTitle"
    assert page._group_meas.objectName() == "FormGroupTitle"
    assert page._group_notes.objectName() == "FormGroupTitle"
    assert not hasattr(page, "meta_panel")
    # Distance remains value+unit semantic row (UI-3B.0 preserved).
    assert page.distance.parent() is not None
    assert page.unit.parent() is page.distance.parent()
    assert page.distance_mm_preview.objectName() == "PassiveHelper"


def test_setup_idle_refresh_no_periodic_relayout_counter(qapp):
    from mouse_dpi_tool.ui.views.pages import SetupPage

    reset_presentation_instrumentation()
    controller = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = SetupPage(controller)
    before = COUNTERS.trial_table_rebuilds
    for _ in range(20):
        page.refresh()
    assert COUNTERS.trial_table_rebuilds == before


def test_capture_trial_workspace_spacing_constants(qapp):
    from mouse_dpi_tool.ui.components.trial_workspace import TrialWorkspace

    controller = AppController(preferences={"theme": "dark", "locale": "en-US"})
    ws = TrialWorkspace(controller)
    assert ws.tabs.objectName() == "TrialTabs"
    assert ws._dpi_label.objectName() == "FormLabel"
    layout = ws.layout()
    # summary, spacing, filters, spacing, tabs, spacing, actions, message
    assert layout.count() >= 6
    assert SPACE_CAPTURE_FILTER_GAP >= 12
    assert SPACE_FORM_GROUP >= 18


def test_capture_idle_refresh_no_extra_table_rebuild(qapp):
    from mouse_dpi_tool.ui.views.pages import CapturePage

    reset_presentation_instrumentation()
    controller = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = CapturePage(controller)
    page.refresh()
    before = COUNTERS.trial_table_rebuilds
    for _ in range(15):
        page.refresh()
    # Idle empty Capture must not keep rebuilding tables every tick.
    assert COUNTERS.trial_table_rebuilds == before


def test_results_empty_unchanged_from_ui3b0(qapp):
    from mouse_dpi_tool.ui.views.pages import ResultsPage

    controller = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = ResultsPage(controller)
    page.refresh()
    assert page.empty_panel.isHidden() is False
    assert page.content_host.isHidden() is True
    assert page.v1_host.count() == 0


def test_settings_form_bounded(qapp):
    from mouse_dpi_tool.ui.layout_metrics import SETTINGS_PANEL_MAX_WIDTH
    from mouse_dpi_tool.ui.views.pages import SettingsPage

    controller = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = SettingsPage(controller, on_prefs_changed=lambda: None)
    assert page._form_card.maximumWidth() == SETTINGS_PANEL_MAX_WIDTH
    assert page._theme_label.objectName() == "FormLabel"


def test_form_label_stylesheet_transparent(qapp):
    from mouse_dpi_tool.ui.theme.tokens import DARK, stylesheet

    css = stylesheet(DARK)
    assert "QLabel#FormLabel" in css
    assert "QLabel#FormGroupTitle" in css
    assert "QTabWidget#TrialTabs" in css
    block = css.split("QLabel#FormLabel")[1].split("}")[0]
    assert "background: transparent" in block
