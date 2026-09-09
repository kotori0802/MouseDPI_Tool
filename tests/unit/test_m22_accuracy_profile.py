"""M-2.2 — Accuracy Acceptance Profile (Strict / Medium / Lenient)."""

from __future__ import annotations

import pytest

from mouse_dpi_tool.capture import CaptureEngine, SyntheticEventSource
from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.measurement.accuracy_profile import (
    FIELD_LENIENT,
    FIELD_MEDIUM,
    FIELD_STRICT,
    profile_cpi_error_limits,
    settings_patch_for_accuracy_profile,
)
from mouse_dpi_tool.measurement.settings import status_from_limits
from mouse_dpi_tool.session import Session
from mouse_dpi_tool.ui.controllers import AppController


def _status(error_pct: float, mode: str) -> str:
    pass_pct, fail_pct = profile_cpi_error_limits(mode)
    return status_from_limits(abs(error_pct), pass_pct, fail_pct)


def test_profile_mappings():
    assert profile_cpi_error_limits(FIELD_STRICT) == (3.0, 5.0)
    assert profile_cpi_error_limits(FIELD_MEDIUM) == (6.0, 8.0)
    assert profile_cpi_error_limits(FIELD_LENIENT) == (9.0, 11.0)
    assert settings_patch_for_accuracy_profile(FIELD_STRICT)["tolerance_mode"] == FIELD_STRICT


def test_four_percent_error_across_profiles():
    assert _status(4.0, FIELD_STRICT) == "WARN"
    assert _status(4.0, FIELD_MEDIUM) == "PASS"
    assert _status(4.0, FIELD_LENIENT) == "PASS"


def test_profile_changes_only_accuracy_thresholds():
    session = Session(settings={"distance_mm": 100.0, "min_valid_trials_per_group": 1})
    before = dict(session.settings)
    session.update_settings(settings_patch_for_accuracy_profile(FIELD_MEDIUM))
    after = session.settings
    assert after["cpi_error_pass_pct"] == 6.0
    assert after["cpi_error_fail_pct"] == 8.0
    assert after["tolerance_mode"] == FIELD_MEDIUM
    for key in (
        "cpi_cv_pass_pct",
        "cpi_cv_fail_pct",
        "ratio_error_pass_pct",
        "ratio_error_fail_pct",
        "straightness_fail_pct",
        "axis_leakage_pass_pct",
        "axis_leakage_fail_pct",
        "fixture_noise_floor_counts",
    ):
        assert after[key] == before[key]


def test_canonical_tolerance_mode_exported():
    session = Session(settings=settings_patch_for_accuracy_profile(FIELD_LENIENT))
    snap = session.to_session_dict()
    assert snap["settings"]["tolerance_mode"] == FIELD_LENIENT
    assert snap["settings"]["cpi_error_pass_pct"] == 9.0
    assert snap["settings"]["cpi_error_fail_pct"] == 11.0


def test_locale_does_not_alter_canonical_policy():
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.set_accuracy_profile(FIELD_MEDIUM)
    a = dict(controller.session.settings)
    controller.set_locale("zh-TW")
    controller.set_theme("dark")
    b = dict(controller.session.settings)
    assert a["tolerance_mode"] == b["tolerance_mode"] == FIELD_MEDIUM
    assert a["cpi_error_pass_pct"] == b["cpi_error_pass_pct"] == 6.0
    assert a["cpi_error_fail_pct"] == b["cpi_error_fail_pct"] == 8.0


def test_criterion_editable_before_evidence_locked_after():
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    assert controller.accuracy_criterion_locked is False
    controller.set_accuracy_profile(FIELD_LENIENT)
    assert controller.accuracy_profile == FIELD_LENIENT
    session = controller.session
    session.add_synthetic_trial(configured_dpi=800, counts_x=3150)
    assert controller.accuracy_criterion_locked is True
    with pytest.raises(RuntimeError, match="locked"):
        controller.set_accuracy_profile(FIELD_STRICT)
    # Domain still allows analysis re-evaluation; UI policy blocks.
    session.update_settings(settings_patch_for_accuracy_profile(FIELD_STRICT))
    assert session.settings["cpi_error_pass_pct"] == 3.0


def test_capture_run_config_freezes_selected_policy():
    samples = [MovementSample(dx=3150, dy=0, device_id="s")]

    def factory(*, on_status=None):
        return CaptureEngine(source=SyntheticEventSource(samples), on_status=on_status)

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=factory,
    )
    controller.set_accuracy_profile(FIELD_MEDIUM)
    controller.start_capture()
    cfg = controller.run_config
    assert cfg is not None
    assert cfg.tolerance_mode == FIELD_MEDIUM
    assert cfg.cpi_error_pass_pct == 6.0
    assert cfg.cpi_error_fail_pct == 8.0
    controller.cancel_capture()


def test_default_is_strict_compatible():
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    assert controller.accuracy_profile == FIELD_STRICT
    assert controller.session.settings["cpi_error_pass_pct"] == 3.0
    assert controller.session.settings["cpi_error_fail_pct"] == 5.0
