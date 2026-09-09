"""UI-1A.1 — direction evidence integrity (signed Raw Input vs selected direction)."""

from __future__ import annotations

import pytest

from mouse_dpi_tool.capture import CaptureEngine, SyntheticEventSource
from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.measurement.direction_evidence import (
    DirectionEvidenceError,
    DirectionMismatchError,
    assert_direction_matches_counts,
    evaluate_direction_match,
    require_canonical_direction,
)
from mouse_dpi_tool.session import CaptureAdmissionError, Session
from mouse_dpi_tool.ui.controllers import AppController
from mouse_dpi_tool.ui.theme import ThemeManager
from mouse_dpi_tool.ui.theme.tokens import DARK, LIGHT


# Selected direction → matching signed primary counts (Windows Y+ down).
_MATCHING = {
    "X+": (3150, 0),
    "X-": (-3150, 0),
    "Y+": (0, -3150),  # bottom → top
    "Y-": (0, 3150),  # top → bottom
}

_OPPOSITE = {
    "X+": (-3150, 0),
    "X-": (3150, 0),
    "Y+": (0, 3150),
    "Y-": (0, -3150),
}

_AXIS = {"X+": "X", "X-": "X", "Y+": "Y", "Y-": "Y"}


def test_invalid_direction_fail_closed():
    with pytest.raises(DirectionEvidenceError):
        require_canonical_direction("DIAG")
    with pytest.raises(DirectionEvidenceError):
        require_canonical_direction("left_to_right")
    with pytest.raises(DirectionEvidenceError):
        require_canonical_direction("")
    with pytest.raises(DirectionEvidenceError):
        require_canonical_direction(None)
    # Must not silently become X+.
    for bogus in ("nope", "XP", "xpositive", "FORWARD"):
        with pytest.raises(DirectionEvidenceError):
            require_canonical_direction(bogus)


@pytest.mark.parametrize("direction", list(_MATCHING))
def test_matching_signed_counts_pass(direction: str):
    dx, dy = _MATCHING[direction]
    result = evaluate_direction_match(direction, dx, dy)
    assert result.matches is True
    assert result.reason == "OK"
    assert_direction_matches_counts(direction, dx, dy)


@pytest.mark.parametrize("direction", list(_OPPOSITE))
def test_opposite_signed_counts_fail(direction: str):
    dx, dy = _OPPOSITE[direction]
    result = evaluate_direction_match(direction, dx, dy)
    assert result.matches is False
    assert result.reason == "DIRECTION_MISMATCH"
    with pytest.raises(DirectionMismatchError) as exc:
        assert_direction_matches_counts(direction, dx, dy)
    assert exc.value.code == "DIRECTION_MISMATCH"


@pytest.mark.parametrize("direction", list(_MATCHING))
def test_zero_primary_movement_fails(direction: str):
    result = evaluate_direction_match(direction, 0, 0)
    assert result.matches is False
    assert result.reason == "ZERO_PRIMARY_MOVEMENT"
    with pytest.raises(DirectionMismatchError):
        assert_direction_matches_counts(direction, 0, 0)


@pytest.mark.parametrize("direction", list(_MATCHING))
def test_admit_accepts_matching_direction(direction: str):
    dx, dy = _MATCHING[direction]
    engine = CaptureEngine()
    engine.start()
    engine.feed(MovementSample(dx=dx, dy=dy, device_id="t"))
    engine.wait_until_idle()
    engine.stop()
    session = Session(
        settings={
            "distance_mm": 100.0,
            "min_valid_trials_per_group": 1,
            "movement_mode": "Axis Projection",
        }
    )
    trial = session.admit_valid_capture(
        engine,
        configured_dpi=800,
        axis=_AXIS[direction],
        direction=direction,
    )
    assert trial["direction"] == direction
    assert trial["axis"] == _AXIS[direction]
    assert trial["accepted"] is True


@pytest.mark.parametrize("direction", list(_OPPOSITE))
def test_admit_rejects_mismatched_direction(direction: str):
    dx, dy = _OPPOSITE[direction]
    engine = CaptureEngine()
    engine.start()
    engine.feed(MovementSample(dx=dx, dy=dy, device_id="t"))
    engine.wait_until_idle()
    engine.stop()
    assert engine.is_valid_complete_capture
    session = Session(
        settings={
            "distance_mm": 100.0,
            "min_valid_trials_per_group": 1,
            "movement_mode": "Axis Projection",
        }
    )
    with pytest.raises(CaptureAdmissionError) as exc:
        session.admit_valid_capture(
            engine,
            configured_dpi=800,
            axis=_AXIS[direction],
            direction=direction,
        )
    assert "DIRECTION_MISMATCH" in str(exc.value)
    assert session.active_trials == []
    # Capture evidence remains on the engine; tester can correct direction or re-measure.
    assert engine.net_counts_x == dx
    assert engine.net_counts_y == dy


def test_admit_rejects_zero_primary():
    engine = CaptureEngine()
    engine.start()
    engine.feed(MovementSample(dx=0, dy=0, device_id="t"))
    engine.wait_until_idle()
    engine.stop()
    session = Session(settings={"distance_mm": 100.0, "movement_mode": "Axis Projection"})
    with pytest.raises(CaptureAdmissionError) as exc:
        session.admit_valid_capture(engine, configured_dpi=800, direction="X+")
    assert "ZERO_PRIMARY_MOVEMENT" in str(exc.value)


def test_controller_does_not_rewrite_session_wide_direction():
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    assert controller.session.measurement_context["direction"] == ""
    controller.set_direction("Y+")
    controller.set_direction("X-")
    assert controller.direction == "X-"
    assert controller.session.measurement_context["direction"] == ""


def test_controller_admit_mismatch_preserves_capture():
    def factory(*, on_status=None):
        return CaptureEngine(
            source=SyntheticEventSource([MovementSample(dx=-3150, dy=0, device_id="synth")]),
            on_status=on_status,
        )

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=factory,
    )
    controller.set_movement_mode("Axis Projection")
    controller.set_direction("X+")  # opposite of actual movement
    controller.start_capture()
    assert controller._engine is not None
    controller._engine.wait_until_idle()
    controller.stop_capture()
    assert controller.capture_viewmodel().is_valid_complete_capture
    with pytest.raises((CaptureAdmissionError, RuntimeError)):
        controller.admit_capture()
    assert controller.session.active_trials == []
    assert controller._engine.net_counts_x == -3150
    assert controller.capture_viewmodel().can_admit is False
    assert controller.capture_viewmodel().direction_issue_code == "DIRECTION_MISMATCH"


def test_cpi_magnitude_unchanged_by_direction_helper():
    from mouse_dpi_tool.measurement.trial import compute_trial

    # Absolute counts still drive CPI; direction check is separate.
    t_pos = compute_trial(
        trial_id=1,
        distance_mm=100.0,
        axis="X",
        direction="X+",
        counts_x=3150,
        counts_y=0,
        configured_dpi=800,
    )
    t_neg = compute_trial(
        trial_id=2,
        distance_mm=100.0,
        axis="X",
        direction="X-",
        counts_x=-3150,
        counts_y=0,
        configured_dpi=800,
    )
    assert t_pos["measured_cpi"] == t_neg["measured_cpi"]
    assert t_pos["primary_counts"] == t_neg["primary_counts"]


def test_guided_lane_uses_theme_tokens():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.components.guided_lane import GuidedLane

    _ = QApplication.instance() or QApplication([])
    lane = GuidedLane()
    lane.apply_tokens(LIGHT)
    assert lane.accent_color.lower() == LIGHT.accent.lower()
    assert lane.muted_color.lower() == LIGHT.text_secondary.lower()
    lane.apply_tokens(DARK)
    assert lane.accent_color.lower() == DARK.accent.lower()
    assert lane.muted_color.lower() == DARK.text_secondary.lower()
    dark_mgr = ThemeManager("dark")
    lane.apply_tokens(dark_mgr.tokens)
    assert lane.accent_color.lower() == DARK.accent.lower()
