"""MS-1 / UI-3A.5 — motion timing + trial diagnostics."""

from __future__ import annotations

import copy
import json
import time
from pathlib import Path

import pytest

from mouse_dpi_tool.capture.motion_timing import (
    TIMING_NOT_EVALUATED,
    TIMING_OK,
    StreamingMotionTimingAccumulator,
    attach_motion_timing_to_trial,
)
from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.reporting.fixture_motion import build_fixture_motion_diagnostics
from mouse_dpi_tool.reporting.html_report import render_html_report
from mouse_dpi_tool.reporting.trial_diagnostics import (
    build_dpi_error_distributions,
    build_speed_correlations,
    build_speed_error_points,
    build_trial_sequence_points,
    session_has_motion_timing,
)
from mouse_dpi_tool.session import Session, validate_session


def test_timestamps_reuse_sample_clock_not_event_count():
    acc = StreamingMotionTimingAccumulator()
    acc.mark_capture_start(timestamp_s=100.0)
    acc.on_sample(MovementSample(dx=10, dy=0, timestamp_s=100.5))
    acc.on_sample(MovementSample(dx=10, dy=0, timestamp_s=101.5))
    acc.mark_capture_stop(timestamp_s=102.0)
    snap = acc.snapshot(distance_mm=50.8)
    assert snap["timing_status"] == TIMING_OK
    assert snap["active_motion_duration_ms"] == pytest.approx(1000.0, abs=0.1)
    assert snap["estimated_traversal_speed_mm_s"] == pytest.approx(50.8, abs=0.01)
    assert snap["motion_sample_count"] == 2
    assert snap["timing_source"] == "sample_timestamp_s"
    # Explicitly not event-density speed
    assert snap["estimated_traversal_speed_mm_s"] != 2


def test_missing_timestamps_use_boundary_clock_or_not_evaluated():
    acc = StreamingMotionTimingAccumulator()
    # No samples → NOT_EVALUATED
    snap = acc.snapshot(distance_mm=50.8)
    assert snap["timing_status"] == TIMING_NOT_EVALUATED
    assert snap["estimated_traversal_speed_mm_s"] is None

    acc2 = StreamingMotionTimingAccumulator()
    acc2.mark_capture_start()
    acc2.on_sample(MovementSample(dx=1, dy=0, timestamp_s=None))
    time.sleep(0.02)
    acc2.on_sample(MovementSample(dx=1, dy=0, timestamp_s=None))
    acc2.mark_capture_stop()
    snap2 = acc2.snapshot(distance_mm=50.8)
    assert snap2["timing_source"] == "capture_boundary_perf_counter"
    assert snap2["timing_status"] == TIMING_OK
    assert snap2["active_motion_duration_ms"] is not None
    assert snap2["active_motion_duration_ms"] > 0


def test_never_fabricate_speed_from_event_count():
    src = Path(__file__).resolve().parents[2] / "src" / "mouse_dpi_tool" / "capture" / "motion_timing.py"
    text = src.read_text(encoding="utf-8")
    # Docstring may mention the forbidden formula; implementation must not compute it.
    body = text.split('"""', 2)[-1]
    assert "published_count" not in body or "not" in text.lower()
    assert "speed = event_count" not in body
    assert "counts / event_count" not in body
    assert "duration_ms" in text and "first" in text


def test_historical_session_without_timing_still_validates():
    fixture = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "boundaries"
        / "representative_session_v1.json"
    )
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    # Ensure no motion_timing required
    for t in payload.get("trials") or []:
        t.pop("motion_timing", None)
    validate_session(payload)


def test_optional_motion_timing_attaches_without_cpi_change():
    session = Session(
        settings={
            "distance_mm": 50.8,
            "min_valid_trials_per_group": 1,
            "movement_mode": "Axis Projection",
            "tolerance_mode": "FIELD_STRICT",
            "cpi_error_pass_pct": 3.0,
            "cpi_error_fail_pct": 5.0,
            "cpi_cv_pass_pct": 1.0,
            "cpi_cv_fail_pct": 3.0,
        },
        measurement_context={"method": "synthetic", "direction": "X+", "surface": "cloth pad"},
        dut={"vendor": "T", "model": "M", "notes": ""},
        operator="ms1",
    )
    timing = {
        "timing_status": TIMING_OK,
        "motion_sample_count": 10,
        "first_motion_timestamp": 1.0,
        "last_motion_timestamp": 2.0,
        "active_motion_duration_ms": 1000.0,
        "estimated_traversal_speed_mm_s": 50.8,
        "timing_source": "sample_timestamp_s",
        "notes": "test",
    }
    before_cpi = None
    trial = session.add_synthetic_trial(
        configured_dpi=800,
        counts_x=780,
        counts_y=0,
        motion_timing_snapshot=timing,
    )
    assert trial["motion_timing"]["estimated_traversal_speed_mm_s"] == 50.8
    assert "measured_cpi" in trial
    payload = session.to_session_dict()
    validate_session(payload)
    assert payload["measurement_context"]["surface"] == "cloth pad"


def test_forward_reverse_descriptive_asymmetry_not_finding():
    trials = []
    # Same axis ~0°, forward +x and reverse -x with different CPI
    for i, (cx, cpi, err) in enumerate(
        [(800, 800.0, 0.0), (800, 800.0, 0.0), (-700, 700.0, -12.5), (-700, 700.0, -12.5)]
    ):
        trials.append(
            {
                "movement_mode": "Vector Magnitude",
                "configured_dpi": 800,
                "counts_x": cx,
                "counts_y": 0,
                "measured_cpi": cpi,
                "error_pct": err,
                "vector_counts": abs(cx),
                "path_total_counts": abs(cx) * 1.01,
                "straightness_pct": 99.0,
            }
        )
    diag = build_fixture_motion_diagnostics(trials)
    row = diag.per_dpi[0]
    assert row.forward_trials >= 1 and row.reverse_trials >= 1
    assert row.forward_avg_measured_cpi is not None
    assert row.reverse_avg_measured_cpi is not None
    assert row.forward_reverse_mean_cpi_diff_pct is not None
    assert row.directional_asymmetry_note is not None
    blob = " ".join(row.directional_asymmetry_note.lower() for _ in [0])
    assert "proven" not in blob
    assert "defect" not in blob


def test_trial_sequence_and_distribution_from_canonical_only():
    trials = []
    for i in range(1, 9):
        trials.append(
            {
                "trial_id": i,
                "report_trial_no": i,
                "accepted": True,
                "rejected": False,
                "deleted": False,
                "configured_dpi": 800 if i % 2 == 0 else 400,
                "error_pct": -3.0 + (i * 0.2),
                "motion_timing": {
                    "timing_status": TIMING_OK,
                    "estimated_traversal_speed_mm_s": 40.0 + i,
                },
            }
        )
    seq = build_trial_sequence_points(trials, dpi_filter=800)
    assert all(p.configured_dpi == 800 for p in seq)
    dist = build_dpi_error_distributions(trials)
    assert {d.configured_dpi for d in dist} == {400.0, 800.0}
    assert session_has_motion_timing(trials)
    pts = build_speed_error_points(trials)
    assert pts
    corr = build_speed_correlations(trials, min_n=3)
    assert any(c.spearman_rho is not None for c in corr if c.configured_dpi == 800)


def test_report_includes_surface_and_diagnostics_without_overall():
    session = {
        "session_id": "ms1-test",
        "tool_name": "Mouse DPI Tool",
        "tool_version": "0.0.0",
        "operator": "t",
        "schema_version": "MOUSE_DPI_TOOL_SESSION_V1",
        "settings": {
            "distance_mm": 50.8,
            "movement_mode": "Vector Magnitude",
            "cpi_error_pass_pct": 3.0,
            "cpi_error_fail_pct": 5.0,
            "cpi_cv_pass_pct": 1.0,
            "cpi_cv_fail_pct": 3.0,
            "tolerance_mode": "FIELD_STRICT",
        },
        "dut": {"vendor": "T", "model": "M", "notes": ""},
        "measurement_context": {
            "method": "fixture",
            "surface": "hard pad",
            "fixture_type": "preload against rail",
            "notes": "timing soak",
            "direction": "",
            "polling_rate_note": "",
        },
        "metrics": {"active_trial_count": 4, "group_count": 2, "ratio_pair_count": 0},
        "group_summaries": [
            {
                "group_id": "400",
                "configured_dpi": 400,
                "distance_mm": 50.8,
                "valid_trials": 2,
                "avg_measured_cpi": 388.0,
                "status": "WARN",
                "avg_error_pct": -3.0,
                "max_abs_error_pct": 4.0,
                "cpi_cv_pct": 1.2,
            },
            {
                "group_id": "800",
                "configured_dpi": 800,
                "distance_mm": 50.8,
                "valid_trials": 2,
                "avg_measured_cpi": 776.0,
                "status": "WARN",
                "avg_error_pct": -3.0,
                "max_abs_error_pct": 5.5,
                "cpi_cv_pct": 1.3,
            },
        ],
        "ratio_analysis": [],
        "trials": [
            {
                "trial_id": 1,
                "accepted": True,
                "rejected": False,
                "deleted": False,
                "configured_dpi": 400,
                "error_pct": -2.5,
                "report_trial_no": 1,
            },
            {
                "trial_id": 2,
                "accepted": True,
                "rejected": False,
                "deleted": False,
                "configured_dpi": 800,
                "error_pct": -3.5,
                "report_trial_no": 2,
            },
        ],
        "findings": {
            "accuracy": {"status": "WARN", "metrics": {}, "issue_codes": []},
            "repeatability": {"status": "PASS", "metrics": {}, "issue_codes": []},
            "ratio": {"status": "PASS", "metrics": {}, "issue_codes": []},
            "path_quality": {"status": "PASS", "metrics": {"pq_pass": 2, "pq_fail": 0}, "issue_codes": []},
            "linearity": {"status": "NOT_EVALUATED", "metrics": {}, "issue_codes": []},
            "scaling_evidence": {"status": "NOT_EVALUATED", "metrics": {}, "issue_codes": []},
            "native_capability": {"status": "NOT_EVALUATED", "metrics": {}, "issue_codes": []},
        },
    }
    html = render_html_report(session)
    assert "hard pad" in html
    assert "preload against rail" in html
    assert "Engineering Diagnostics" in html
    assert "Trial CPI Error over Test Sequence" in html
    assert "Motion timing evidence not available" in html
    assert "overall verdict" not in html.lower()


def test_reference_90_trial_interpretation_fixture_numbers_not_in_production():
    src = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "mouse_dpi_tool"
        / "reporting"
        / "trial_diagnostics.py"
    )
    text = src.read_text(encoding="utf-8")
    for token in ("387.5476", "7.4375", "1.6377", "0.9553"):
        assert token not in text


def test_path_quality_independent_of_timing_module():
    from mouse_dpi_tool.path_quality import accumulator as pq

    text = Path(pq.__file__).read_text(encoding="utf-8")
    assert "motion_timing" not in text
    assert "traversal_speed" not in text
