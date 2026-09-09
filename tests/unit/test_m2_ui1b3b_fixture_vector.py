"""M-2 + UI-1B.3B — Fixture Vector admit + Radial Target Gauge."""

from __future__ import annotations

import math

import pytest

from mouse_dpi_tool.capture import CaptureEngine, SyntheticEventSource
from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.session import Session
from mouse_dpi_tool.ui.components.radial_target_gauge import (
    expected_target_radius_counts,
    map_counts_to_gauge,
)
from mouse_dpi_tool.ui.controllers import (
    MOVEMENT_MODE_DIRECTIONAL_AXIS,
    MOVEMENT_MODE_FIXTURE_VECTOR,
    AppController,
)


def _factory(samples):
    def factory(*, on_status=None):
        return CaptureEngine(source=SyntheticEventSource(samples), on_status=on_status)

    return factory


def test_expected_target_radius_counts():
    assert expected_target_radius_counts(configured_dpi=800, distance_mm=50.8) == pytest.approx(1600.0)


def test_map_counts_to_gauge_scales_endpoint():
    mapped = map_counts_to_gauge(800.0, 0.0, target_radius=1600.0, width=400, height=400, pass_pct=5.0)
    assert float(mapped["ring_px"]) > 0
    ex, ey = mapped["endpoint"]  # type: ignore[misc]
    cx, cy = mapped["center"]  # type: ignore[misc]
    assert float(ex) > float(cx)
    assert abs(float(ey) - float(cy)) < 1.0


def test_fixture_vector_diagonal_cpi_and_admit():
    samples = [MovementSample(dx=1080, dy=1184, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    assert controller.movement_mode == MOVEMENT_MODE_FIXTURE_VECTOR
    controller.update_distance(distance_input=2.0, unit="inch")
    controller.set_configured_dpi(800)
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    vm = controller.capture_viewmodel()
    assert vm.can_admit is True
    assert vm.direction_issue_code is None
    trial = controller.admit_capture()
    assert trial["movement_mode"] == "Vector Magnitude"
    assert trial["measured_cpi"] == pytest.approx(
        math.sqrt(1080**2 + 1184**2) / 2.0, rel=1e-3
    )
    assert trial["status"] in {"PASS", "WARN"}


def test_axis_projection_diagonal_still_wrong_cpi():
    samples = [MovementSample(dx=1080, dy=1184, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.set_movement_mode(MOVEMENT_MODE_DIRECTIONAL_AXIS)
    controller.update_distance(distance_input=2.0, unit="inch")
    controller.set_configured_dpi(800)
    controller.set_direction("X+")
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    trial = controller.admit_capture()
    assert trial["movement_mode"] == "Axis Projection"
    assert trial["measured_cpi"] == pytest.approx(540.0, abs=0.1)
    assert trial["status"] == "FAIL"


def test_fixture_vector_ignores_direction_mismatch_for_admit():
    """Negative dx would mismatch X+ under Axis mode; Fixture Vector still admits."""
    samples = [MovementSample(dx=-1080, dy=1184, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.update_distance(distance_input=2.0, unit="inch")
    controller.set_configured_dpi(800)
    controller.set_direction("X+")
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    assert controller.capture_viewmodel().can_admit is True
    trial = controller.admit_capture()
    assert trial["direction"] == "N/A"
    assert trial["axis"] == "N/A"
    assert trial["measured_cpi"] == pytest.approx(
        math.sqrt(1080**2 + 1184**2) / 2.0, rel=1e-3
    )


def test_axis_projection_still_blocks_direction_mismatch():
    samples = [MovementSample(dx=-1080, dy=0, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.set_movement_mode(MOVEMENT_MODE_DIRECTIONAL_AXIS)
    controller.set_direction("X+")
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    vm = controller.capture_viewmodel()
    assert vm.can_admit is False
    assert vm.direction_issue_code == "DIRECTION_MISMATCH"


def test_session_fixture_vector_skips_direction_evidence():
    session = Session(
        settings={
            "distance_mm": 50.8,
            "distance_input": 2.0,
            "distance_unit": "inch",
            "movement_mode": "Vector Magnitude",
            "min_valid_trials_per_group": 1,
        }
    )
    engine = CaptureEngine(
        source=SyntheticEventSource([MovementSample(dx=-500, dy=500, device_id="s")])
    )
    engine.start()
    engine.wait_until_idle()
    engine.stop()
    trial = session.admit_valid_capture(
        engine, configured_dpi=800, axis="X", direction="X+"
    )
    assert trial["primary_counts"] == int(round(math.sqrt(500**2 + 500**2)))


def test_capture_page_mode_toggles_gauge_and_lane():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    page = CapturePage(controller)
    page.refresh()
    assert page.gauge.isHidden() is False
    assert page.lane.isHidden() is True
    assert page.direction.isHidden() is True

    controller.set_movement_mode(MOVEMENT_MODE_DIRECTIONAL_AXIS)
    page.refresh()
    assert page.gauge.isHidden() is True
    assert page.lane.isHidden() is False
    assert page.direction.isHidden() is False

    controller.start_capture()
    with pytest.raises(RuntimeError, match="frozen"):
        controller.set_movement_mode(MOVEMENT_MODE_FIXTURE_VECTOR)
    controller.cancel_capture()
