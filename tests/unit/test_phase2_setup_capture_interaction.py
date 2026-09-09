"""Phase 2 — Setup draft survival + geometry tiles + Capture ActionBar."""

from __future__ import annotations

import pytest

from mouse_dpi_tool.ui.capture_transaction import CaptureActionBarMode
from mouse_dpi_tool.ui.controllers import (
    MOVEMENT_MODE_DIRECTIONAL_AXIS,
    MOVEMENT_MODE_FIXTURE_VECTOR,
    AppController,
)
from mouse_dpi_tool.ui.setup_draft import load_committed_snapshot


@pytest.fixture
def qapp():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_setup_draft_survives_refresh_and_retranslate(qapp):
    from mouse_dpi_tool.ui.views.setup_page import SetupPage

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = SetupPage(ctl)
    page.show()
    qapp.processEvents()

    page.vendor.setText("ExampleVendor")
    page.ctx_notes.setText("bench deviation")
    page.geometry.set_current(MOVEMENT_MODE_DIRECTIONAL_AXIS, emit=True)
    qapp.processEvents()

    assert page.apply_btn.isEnabled() is True
    assert page._draft.vendor == "ExampleVendor"
    assert page._draft.ctx_notes == "bench deviation"
    assert page._draft.movement_mode == MOVEMENT_MODE_DIRECTIONAL_AXIS

    # Session still committed old values.
    committed = load_committed_snapshot(ctl)
    assert committed.vendor == ""
    assert committed.movement_mode == MOVEMENT_MODE_FIXTURE_VECTOR

    page.refresh()
    qapp.processEvents()
    assert page.vendor.text() == "ExampleVendor"
    assert page.ctx_notes.text() == "bench deviation"
    assert page.geometry.current() == MOVEMENT_MODE_DIRECTIONAL_AXIS

    page.retranslate()
    qapp.processEvents()
    assert page.vendor.text() == "ExampleVendor"
    assert page.ctx_notes.text() == "bench deviation"
    assert page.geometry.current() == MOVEMENT_MODE_DIRECTIONAL_AXIS
    assert load_committed_snapshot(ctl).vendor == ""

    page.revert_btn.click()
    qapp.processEvents()
    assert page.vendor.text() == ""
    assert page.ctx_notes.text() == ""
    assert page.geometry.current() == MOVEMENT_MODE_FIXTURE_VECTOR
    assert page.apply_btn.isEnabled() is False

    page.vendor.setText("Logitech")
    page.geometry.set_current(MOVEMENT_MODE_DIRECTIONAL_AXIS, emit=True)
    page.apply_btn.click()
    qapp.processEvents()
    after = load_committed_snapshot(ctl)
    assert after.vendor == "Logitech"
    assert after.movement_mode == MOVEMENT_MODE_DIRECTIONAL_AXIS
    assert page.vendor.text() == "Logitech"
    assert page.geometry.current() == MOVEMENT_MODE_DIRECTIONAL_AXIS
    assert page.apply_btn.isEnabled() is False


def test_geometry_tile_keyboard_arrows(qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.components.geometry_tiles import GeometryTileGroup

    group = GeometryTileGroup()
    assert group.current() == MOVEMENT_MODE_FIXTURE_VECTOR
    ev = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(group, ev)
    assert group.current() == MOVEMENT_MODE_DIRECTIONAL_AXIS


def test_capture_geometry_is_readonly_summary(qapp):
    from mouse_dpi_tool.ui.views.pages import CapturePage

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    ctl.set_movement_mode(MOVEMENT_MODE_DIRECTIONAL_AXIS)
    page = CapturePage(ctl)
    page.show()
    qapp.processEvents()
    page.refresh()
    assert hasattr(page, "geometry_summary")
    assert not hasattr(page, "geometry") or not hasattr(getattr(page, "geometry", None), "currentIndexChanged")
    assert "Directional" in page.geometry_summary.text() or "方向" in page.geometry_summary.text()
    assert page.direction.isVisible() is True


def test_capture_action_bar_mode_switch_stable(qapp):
    from mouse_dpi_tool.ui.components.capture_action_bar import CaptureActionBar

    bar = CaptureActionBar()
    assert bar.set_mode(CaptureActionBarMode.IDLE) is False  # already idle
    assert bar.set_mode(CaptureActionBarMode.RUNNING) is True
    assert bar.mode is CaptureActionBarMode.RUNNING
    assert bar.set_mode(CaptureActionBarMode.RUNNING) is False
    assert bar.set_mode(CaptureActionBarMode.REVIEW_ADMITTABLE) is True
    assert bar.admit_btn.isVisibleTo(bar) or bar.mode is CaptureActionBarMode.REVIEW_ADMITTABLE
