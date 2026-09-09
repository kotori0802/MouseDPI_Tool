"""Phase 3 / 3.1 — Layout composition + width allocation (presentation only)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QBoxLayout


@pytest.fixture
def qapp():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_setup_wide_allocates_workspace_band(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.layout_metrics import (
        SETUP_TWO_COLUMN_MIN_WIDTH,
        SETUP_WORKSPACE_MAX_WIDTH,
    )
    from mouse_dpi_tool.ui.views.setup_page import SetupPage

    ctl = AppController(preferences={"theme": "light", "locale": "en-US"})
    page = SetupPage(ctl)
    page.resize(1400, 900)
    page.show()
    qapp.processEvents()
    page._apply_setup_composition()
    qapp.processEvents()

    assert page._form_card.maximumWidth() == SETUP_WORKSPACE_MAX_WIDTH
    assert page._two_column is True
    assert page._top_layout.direction() == QBoxLayout.Direction.LeftToRight
    assert page._top_layout.stretch(0) == 2
    assert page._top_layout.stretch(1) == 3
    # Actual allocation — not stuck near ~670ch-era sizeHint.
    w = page._form_card.width()
    assert w >= 1050
    assert w <= SETUP_WORKSPACE_MAX_WIDTH + 2
    assert SETUP_TWO_COLUMN_MIN_WIDTH == 1040


def test_setup_compact_stacks_at_980(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.setup_page import SetupPage

    ctl = AppController(preferences={"theme": "light", "locale": "en-US"})
    page = SetupPage(ctl)
    page.resize(980, 800)
    page.show()
    qapp.processEvents()
    page._apply_setup_composition()
    qapp.processEvents()

    assert page._two_column is False
    assert page._top_layout.direction() == QBoxLayout.Direction.TopToBottom
    assert page._setup_scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert page._setup_scroll.horizontalScrollBar().isVisible() is False


def test_setup_two_column_at_1200(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.setup_page import SetupPage

    ctl = AppController(preferences={"theme": "light", "locale": "en-US"})
    page = SetupPage(ctl)
    page.resize(1200, 900)
    page.show()
    qapp.processEvents()
    page._apply_setup_composition()
    qapp.processEvents()

    assert page._two_column is True
    assert page._form_card.width() >= 1000


def test_capture_instruction_after_viz_before_action_bar(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.layout_metrics import CAPTURE_INSTRUCTION_MAX_WIDTH_PX
    from mouse_dpi_tool.ui.views.pages import CapturePage

    ctl = AppController(preferences={"theme": "light", "locale": "en-US"})
    page = CapturePage(ctl)
    card_l = page.scroll.widget().layout()
    widgets = []
    for i in range(card_l.count()):
        item = card_l.itemAt(i)
        w = item.widget()
        if w is not None:
            widgets.append(w)
    assert page.viz in widgets
    assert page.instruction in widgets
    assert page.action_bar.parent() is not None
    assert widgets.index(page.viz) < widgets.index(page.instruction)
    instr_idx = None
    action_row_idx = None
    for i in range(card_l.count()):
        item = card_l.itemAt(i)
        if item.widget() is page.instruction:
            instr_idx = i
        lay = item.layout()
        if lay is not None:
            for j in range(lay.count()):
                child = lay.itemAt(j).widget()
                if child is page.action_bar:
                    action_row_idx = i
    assert instr_idx is not None and action_row_idx is not None
    assert instr_idx < action_row_idx
    assert widgets.index(page.poster) > widgets.index(page.instruction)
    assert widgets.index(page.trials) > widgets.index(page.poster)
    assert page.instruction.maximumWidth() <= CAPTURE_INSTRUCTION_MAX_WIDTH_PX


def test_capture_viz_path_dominant_stretch(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.pages import CapturePage

    ctl = AppController(preferences={"theme": "light", "locale": "en-US"})
    page = CapturePage(ctl)
    assert page.viz._row.stretch(0) == 2  # gauge
    assert page.viz._row.stretch(1) == 3  # path


def test_results_hierarchy_and_diagnostics_default_collapsed(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.pages import ResultsPage

    ctl = AppController(preferences={"theme": "light", "locale": "en-US"})
    for dpi, counts in ((400, 800), (800, 1600), (1600, 3200)):
        ctl.session.add_synthetic_trial(configured_dpi=dpi, counts_x=counts, counts_y=0)
        ctl.session.add_synthetic_trial(configured_dpi=dpi, counts_x=counts, counts_y=0)

    page = ResultsPage(ctl)
    page.refresh()
    qapp.processEvents()

    assert page.empty_panel.isHidden() is True
    assert page.content_host.isHidden() is False
    assert page.findings_title.text()
    assert page.evidence_title.text()
    assert page.trends_title.text()

    host_l = page.content_host.layout()
    order = []
    for i in range(host_l.count()):
        w = host_l.itemAt(i).widget()
        if w is page.findings_title:
            order.append("findings")
        elif w is page.evidence_title:
            order.append("evidence")
        elif w is page.trends_title:
            order.append("trends")
        elif w is page.eng_diag:
            order.append("eng")
    assert order == ["findings", "evidence", "trends", "eng"]

    assert page.eng_diag.is_expanded() is False
    assert page.eng_diag.body.isHidden() is True
    assert page.eng_diag.collapsed_hint.isHidden() is False

    page.eng_diag.set_expanded(True)
    qapp.processEvents()
    assert page.eng_diag.is_expanded() is True
    assert page.eng_diag.body.isHidden() is False
    assert page.eng_diag.collapsed_hint.isHidden() is True

    page.refresh()
    qapp.processEvents()
    assert page.eng_diag.is_expanded() is True


def test_results_empty_bounded_content_height(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.layout_metrics import RESULTS_EMPTY_MAX_WIDTH
    from mouse_dpi_tool.ui.views.pages import ResultsPage

    ctl = AppController(preferences={"theme": "light", "locale": "en-US"})
    page = ResultsPage(ctl)
    page.resize(1280, 900)
    page.show()
    qapp.processEvents()
    page.refresh()
    qapp.processEvents()

    assert page.empty_panel.isHidden() is False
    assert page.content_host.isHidden() is True
    assert page.empty_panel.maximumWidth() == RESULTS_EMPTY_MAX_WIDTH
    # Content-height: empty card must not fill most of the page height.
    assert page.empty_panel.height() < 420


def test_results_refresh_does_not_stack_finding_cards(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.pages import ResultsPage

    ctl = AppController(preferences={"theme": "light", "locale": "en-US"})
    ctl.session.add_synthetic_trial(configured_dpi=800, counts_x=1600, counts_y=0)
    page = ResultsPage(ctl)
    page.show()
    qapp.processEvents()
    page.refresh()
    qapp.processEvents()
    page.refresh()
    qapp.processEvents()
    assert page.v1_host.count() == 4


def test_settings_panel_owned_width(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.layout_metrics import SETTINGS_PANEL_MAX_WIDTH, comfortable_form_max_width
    from mouse_dpi_tool.ui.views.pages import SettingsPage

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = SettingsPage(ctl, on_prefs_changed=lambda: None)
    page.resize(1280, 800)
    page.show()
    qapp.processEvents()
    assert page._form_card.maximumWidth() == SETTINGS_PANEL_MAX_WIDTH
    assert page._form_card.maximumWidth() != comfortable_form_max_width(page)
    assert page.locale is not None
    assert page.guide_btn is not None


def test_user_guide_desktop_reading_geometry(qapp):
    from mouse_dpi_tool.ui.components.user_guide_dialog import UserGuideDialog
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.layout_metrics import (
        USER_GUIDE_DEFAULT_HEIGHT,
        USER_GUIDE_DEFAULT_WIDTH,
        USER_GUIDE_MIN_HEIGHT,
        USER_GUIDE_MIN_WIDTH,
    )

    ctl = AppController(preferences={"theme": "light", "locale": "en-US"})
    dlg = UserGuideDialog(ctl)
    assert dlg.minimumWidth() == USER_GUIDE_MIN_WIDTH
    assert dlg.minimumHeight() == USER_GUIDE_MIN_HEIGHT
    assert dlg.width() >= USER_GUIDE_DEFAULT_WIDTH - 20
    assert dlg.height() >= USER_GUIDE_DEFAULT_HEIGHT - 20
    assert dlg._scroll.widgetResizable() is True
