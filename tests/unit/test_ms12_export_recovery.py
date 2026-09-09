"""MS-1.2 — report export recovery with large Session + invalid method."""

from __future__ import annotations

from pathlib import Path

import pytest

from mouse_dpi_tool.contracts.measurement_method import MeasurementMethodError
from mouse_dpi_tool.reporting import generate_report_bundle
from mouse_dpi_tool.session import Session, SessionValidationError, validate_session


def _large_session() -> Session:
    session = Session(
        settings={
            "distance_mm": 50.8,
            "min_valid_trials_per_group": 1,
            "movement_mode": "Vector Magnitude",
            "tolerance_mode": "FIELD_RELAXED",
            "cpi_error_pass_pct": 10.0,
            "cpi_error_fail_pct": 15.0,
            "cpi_cv_pass_pct": 5.0,
            "cpi_cv_fail_pct": 10.0,
        },
        measurement_context={
            "method": "fixture",
            "direction": "N/A",
            "dpi_configuration_source": "unknown",
            "control_software_state": "unknown",
            "measurement_system_uncertainty_note": "Stakeholder fixture uncertainty ~10% (descriptive).",
        },
        dut={"vendor": "T", "model": "M", "notes": ""},
        operator="ms12",
    )
    dpis = (800, 3200, 6400, 9600, 12750, 26000)
    # 72 trials across 6 DPI groups (+ motion_timing-shaped attach via synthetic fields)
    for i in range(72):
        dpi = dpis[i % len(dpis)]
        scale = dpi / 800.0
        session.add_synthetic_trial(
            configured_dpi=int(dpi),
            counts_x=int(800 * scale),
            counts_y=int(100 * scale),
            motion_timing_snapshot={
                "timing_status": "OK",
                "motion_sample_count": 40,
                "first_motion_timestamp": 1.0,
                "last_motion_timestamp": 1.4,
                "active_motion_duration_ms": 400.0,
                "estimated_traversal_speed_mm_s": 127.0,
                "ready_to_first_motion_ms": 80.0 + (i % 5) * 10.0,
                "timing_source": "sample_timestamp_s",
                "notes": "synthetic",
            },
        )
    return session


def test_large_session_export_ok(tmp_path: Path):
    session = _large_session()
    assert len(session.active_trials) == 72
    payload = session.to_session_dict()
    validate_session(payload)
    artifacts = generate_report_bundle(payload, tmp_path)
    assert Path(artifacts.json_path).is_file()
    assert Path(artifacts.html_path).is_file()


def test_invalid_method_blocks_export_without_silent_rewrite(tmp_path: Path):
    session = _large_session()
    payload = session.to_session_dict()
    payload["measurement_context"]["method"] = "unknown123"
    with pytest.raises((SessionValidationError, Exception)):
        validate_session(payload)
    before = list(tmp_path.iterdir())
    with pytest.raises((SessionValidationError, Exception)):
        generate_report_bundle(payload, tmp_path)
    # No new durable report artifacts from the failed validation path.
    after = list(tmp_path.iterdir())
    assert after == before

    # Operator-visible recovery: select canonical method, then export succeeds.
    with pytest.raises(MeasurementMethodError):
        session.update_measurement_context(method="unknown123")
    session.update_measurement_context(method="fixture")
    fixed = session.to_session_dict()
    validate_session(fixed)
    artifacts = generate_report_bundle(fixed, tmp_path)
    assert Path(artifacts.json_path).is_file()
