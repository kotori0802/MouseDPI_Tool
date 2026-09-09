"""Capture control enable matrix + DPI presets."""

from __future__ import annotations

import pytest

from mouse_dpi_tool.capture import CaptureEngine, SyntheticEventSource
from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.ui.controllers import AppController
from mouse_dpi_tool.ui.components.dpi_field import DPI_PRESETS, ConfiguredDpiField


def test_dpi_presets_include_requested_stages():
    assert DPI_PRESETS == (400, 800, 1600, 3200, 6400)


def test_dpi_field_is_non_editable_dropdown():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    _ = QApplication.instance() or QApplication([])
    field = ConfiguredDpiField()
    assert field.combo.isEditable() is False
    assert field.combo.count() == len(DPI_PRESETS) + 1  # "Presets" + values
    field.setValue(1600)
    assert field.value() == 1600
    field.spin.setValue(900)
    assert field.value() == 900


def test_valid_stopped_enables_admit_and_discard_not_stop():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=lambda *, on_status=None: CaptureEngine(
            source=SyntheticEventSource([MovementSample(dx=3150, dy=0, device_id="s")]),
            on_status=on_status,
        ),
    )
    controller.set_direction("X+")
    page = CapturePage(controller)
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    page.refresh()
    assert page.start_btn.isEnabled() is True  # Start = admit + next (continuous)
    assert page.stop_btn.isEnabled() is False
    assert page.cancel_btn.isEnabled() is False
    assert page.admit_btn.isEnabled() is True
    assert page.discard_btn.isEnabled() is True


def test_discard_unlocks_start_immediately():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=lambda *, on_status=None: CaptureEngine(
            source=SyntheticEventSource([MovementSample(dx=3150, dy=0, device_id="s")]),
            on_status=on_status,
        ),
    )
    controller.set_direction("X+")
    page = CapturePage(controller)
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    page.refresh()
    page._run_op("discard")
    assert controller.measurement_config_locked is False
    assert page.start_btn.isEnabled() is True
    assert page.stop_btn.isEnabled() is False
    assert page.admit_btn.isEnabled() is False
    assert page.discard_btn.isEnabled() is False
