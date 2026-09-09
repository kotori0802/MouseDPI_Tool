"""Phase 4.1 — Capture surface cleanup (chrome only)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QHeaderView


@pytest.fixture
def qapp():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_capture_structural_surfaces_transparent_roles(qapp):
    from PySide6.QtWidgets import QFrame

    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.theme.tokens import DARK, stylesheet
    from mouse_dpi_tool.ui.views.pages import CapturePage

    css = stylesheet(DARK)
    assert "QFrame#CaptureHeader" in css
    header_css = css.split("QFrame#CaptureHeader")[1].split("}")[0]
    assert "transparent" in header_css
    bar = css.split("QWidget#CaptureActionBar")[1].split("}")[0]
    assert "transparent" in bar
    assert "QTabWidget#TrialTabs QTabBar" in css

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = CapturePage(ctl)
    headers = [w for w in page.findChildren(QFrame) if w.objectName() == "CaptureHeader"]
    assert len(headers) == 1
    assert page.scroll.widget().objectName() == "TransparentSurface"
    assert page.action_bar.objectName() == "CaptureActionBar"
    # Capture outer workspace is an intentional surface; structural children stay transparent.
    from PySide6.QtWidgets import QFrame as _QF

    shells = [w for w in page.findChildren(_QF) if w.objectName() == "CaptureShell"]
    assert len(shells) == 1
    shell_css = css.split("QFrame#CaptureShell")[1].split("}")[0]
    assert "transparent" not in shell_css.replace(" ", "")
    assert page.trials.objectName() == "TrialWorkspace"
    assert page.trials.tabs.objectName() == "TrialTabs"


def test_trial_table_geometry_column_stretches_not_direction(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.components.trial_workspace import TrialWorkspace, _FLEX_COLUMN

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    ws = TrialWorkspace(ctl)
    table = ws.tables["active"]
    header = table.horizontalHeader()
    assert header.stretchLastSection() is False
    assert header.sectionResizeMode(_FLEX_COLUMN) == QHeaderView.ResizeMode.Stretch
    # Direction is last column — must remain Interactive (not absurd stretch).
    last = table.columnCount() - 1
    assert last != _FLEX_COLUMN
    assert header.sectionResizeMode(last) == QHeaderView.ResizeMode.Interactive
    assert table.objectName() == "TrialTable"


def test_capture_idle_refresh_still_skips_table_rebuild(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.presentation_invalidation import COUNTERS, reset_presentation_instrumentation
    from mouse_dpi_tool.ui.views.pages import CapturePage

    reset_presentation_instrumentation()
    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = CapturePage(ctl)
    page.refresh()
    before = COUNTERS.trial_table_rebuilds
    for _ in range(15):
        page.refresh()
    assert COUNTERS.trial_table_rebuilds == before
