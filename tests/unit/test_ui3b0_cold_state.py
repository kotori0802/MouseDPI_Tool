"""UI-3B.0 — Results empty state, Setup distance row, passive helper (presentation-only)."""

from __future__ import annotations

import pytest

from mouse_dpi_tool.ui.controllers import AppController
from mouse_dpi_tool.ui.presentation_invalidation import COUNTERS, reset_presentation_instrumentation


@pytest.fixture
def qapp():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_results_empty_state_hides_analytics(qapp):
    from mouse_dpi_tool.ui.views.pages import ResultsPage

    controller = AppController(preferences={"theme": "dark", "locale": "en-US"})
    assert controller.session.metrics()["active_trial_count"] == 0
    page = ResultsPage(controller)
    page.refresh()
    # Headless widgets: use isHidden() (isVisible requires a shown ancestry).
    assert page.empty_panel.isHidden() is False
    assert page.content_host.isHidden() is True
    assert page.v1_host.count() == 0
    assert page.groups_table.rowCount() == 0
    assert page.ratios_table.rowCount() == 0
    assert page.content_host.isHidden() is True
    assert page.report_btn.isEnabled() is False


def test_results_populated_shows_content(qapp):
    from mouse_dpi_tool.session import Session
    from mouse_dpi_tool.ui.views.pages import ResultsPage

    session = Session(
        settings={"distance_mm": 50.8, "min_valid_trials_per_group": 1},
        measurement_context={"method": "fixture", "direction": "N/A"},
        dut={"vendor": "T", "model": "M", "notes": ""},
        operator="ui3b0",
    )
    session.add_synthetic_trial(configured_dpi=800, counts_x=1600, counts_y=0)
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.session = session
    page = ResultsPage(controller)
    page.refresh()
    assert page.empty_panel.isHidden() is True
    assert page.content_host.isHidden() is False
    assert page.v1_host.count() >= 1
    assert page.report_btn.isEnabled() is True


def test_setup_distance_semantic_row_keep_number(qapp):
    from mouse_dpi_tool.ui.components.combo import combo_data
    from mouse_dpi_tool.ui.views.pages import SetupPage

    controller = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = SetupPage(controller)
    assert page.distance_mm_preview.objectName() == "PassiveHelper"
    page.distance.setValue(2.0)
    page.unit.setCurrentIndex(page.unit.findData("inch"))
    assert page.distance.value() == pytest.approx(2.0)
    assert combo_data(page.unit) == "inch"
    assert "50.8" in page.distance_mm_preview.text().replace(",", "")
    page.distance.setValue(100.0)
    page.unit.setCurrentIndex(page.unit.findData("mm"))
    assert page.distance.value() == pytest.approx(100.0)
    assert "100" in page.distance_mm_preview.text()
    page._apply()
    assert controller.session.settings["distance_mm"] == pytest.approx(100.0)
    assert controller.session.settings["distance_unit"] == "mm"


def test_results_empty_repeated_refresh_stays_light(qapp):
    from mouse_dpi_tool.ui.views.pages import ResultsPage

    reset_presentation_instrumentation()
    controller = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = ResultsPage(controller)
    for _ in range(25):
        page.refresh()
    assert page.empty_panel.isHidden() is False
    assert page.v1_host.count() == 0
    # Empty path must not rebuild trial tables via Capture counters.
    assert COUNTERS.trial_table_rebuilds == 0


def test_passive_helper_stylesheet_is_transparent(qapp):
    from mouse_dpi_tool.ui.theme.tokens import DARK, stylesheet

    css = stylesheet(DARK)
    assert "QLabel#PassiveHelper" in css
    assert "QLabel#Hint, QLabel#PassiveHelper" in css
    block = css.split("QLabel#Hint, QLabel#PassiveHelper")[1].split("}")[0]
    assert "background: transparent" in block
