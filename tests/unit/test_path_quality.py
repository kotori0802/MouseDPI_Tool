"""Path Quality streaming metrics — legacy-derived, CPI-isolated."""

from __future__ import annotations

import math

from mouse_dpi_tool.contracts.movement import VISUALIZATION_PATH_MAX_POINTS, MovementSample
from mouse_dpi_tool.measurement.trial import compute_trial
from mouse_dpi_tool.path_quality import StreamingPathQualityAccumulator, attach_to_trial


def _run(samples, **kwargs) -> dict:
    acc = StreamingPathQualityAccumulator(**kwargs)
    for sample in samples:
        acc.on_sample(sample)
    return acc.snapshot()


def test_perfectly_straight_x_movement():
    samples = [MovementSample(dx=10, dy=0) for _ in range(100)]
    snap = _run(samples)
    assert snap["net_counts_x"] == 1000
    assert snap["net_counts_y"] == 0
    assert snap["vector_counts"] == 1000
    assert snap["path_total_counts"] == 1000.0
    assert snap["straightness_pct"] == 100.0
    assert snap["status"] == "PASS"
    assert snap["issue_codes"] == []


def test_perfectly_straight_y_movement():
    samples = [MovementSample(dx=0, dy=10) for _ in range(50)]
    snap = _run(samples)
    assert snap["net_counts_x"] == 0
    assert snap["net_counts_y"] == 500
    assert snap["vector_counts"] == 500
    assert snap["path_total_counts"] == 500.0
    assert snap["status"] == "PASS"


def test_small_lateral_noise_still_pass():
    samples = [MovementSample(dx=10, dy=1) for _ in range(80)]
    snap = _run(samples)
    assert snap["status"] == "PASS"
    assert snap["straightness_pct"] >= 85.0
    expected_path = round(80 * math.hypot(10, 1), 4)
    assert snap["path_total_counts"] == expected_path


def test_forward_reversal_fail():
    forward = [MovementSample(dx=10, dy=0) for _ in range(100)]
    back = [MovementSample(dx=-10, dy=0) for _ in range(40)]
    snap = _run(forward + back)
    assert snap["net_counts_x"] == 600
    assert snap["path_total_counts"] == 1400.0
    assert snap["straightness_pct"] < 85.0
    assert snap["status"] == "FAIL"
    assert "PATH_REVERSAL_OR_JITTER_FAIL" in snap["issue_codes"]


def test_zero_movement_no_samples_not_tested():
    snap = _run([])
    assert snap["status"] == "NOT_TESTED"
    assert snap["path_total_counts"] is None
    assert snap["issue_codes"] == []


def test_zero_net_after_out_and_back():
    samples = [MovementSample(dx=10, dy=0) for _ in range(20)] + [
        MovementSample(dx=-10, dy=0) for _ in range(20)
    ]
    snap = _run(samples)
    assert snap["vector_counts"] == 0
    assert snap["path_total_counts"] == 400.0
    assert snap["status"] == "FAIL"
    assert "NO_MOVEMENT" in snap["issue_codes"]


def test_below_noise_floor_deltas_excluded_from_path_total():
    samples = [MovementSample(dx=3, dy=0) for _ in range(100)]
    snap = _run(samples, fixture_noise_floor_counts=7)
    assert snap["net_counts_x"] == 300
    assert snap["path_total_counts"] == 0.0
    assert snap["ignored_below_floor_count"] == 100
    assert snap["included_step_count"] == 0
    assert snap["straightness_pct"] == 0.0
    # V1: net movement without above-floor path evidence is NOT_EVALUATED
    assert snap["status"] == "NOT_EVALUATED"
    assert "NO_PATH_EVIDENCE_ABOVE_NOISE_FLOOR" in snap["issue_codes"]


def test_exact_noise_floor_yields_not_evaluated_path_quality():
    samples = [MovementSample(dx=7, dy=0) for _ in range(10)]
    snap = _run(samples, fixture_noise_floor_counts=7)
    assert snap["included_step_count"] == 0
    assert snap["path_total_counts"] == 0.0
    assert snap["net_counts_x"] == 70
    assert snap["status"] == "NOT_EVALUATED"
    assert "NO_PATH_EVIDENCE_ABOVE_NOISE_FLOOR" in snap["issue_codes"]
    samples8 = [MovementSample(dx=8, dy=0) for _ in range(10)]
    snap8 = _run(samples8, fixture_noise_floor_counts=7)
    assert snap8["included_step_count"] == 10
    assert snap8["path_total_counts"] == 80.0
    assert snap8["status"] == "PASS"

def test_more_than_6000_samples_use_full_capture():
    n = VISUALIZATION_PATH_MAX_POINTS + 500
    samples = [MovementSample(dx=10, dy=0) for _ in range(n)]
    snap = _run(samples)
    assert snap["sample_count"] == n
    assert snap["net_counts_x"] == n * 10
    assert snap["path_total_counts"] == float(n * 10)
    assert snap["straightness_pct"] == 100.0
    assert snap["status"] == "PASS"


def test_path_quality_does_not_rewrite_measurement_status():
    trial = compute_trial(
        trial_id=1,
        configured_dpi=800,
        distance_mm=30.0,
        axis="X",
        direction="X+",
        counts_x=945,
        counts_y=12,
        movement_mode="Vector Magnitude",
        distance_input=30.0,
        distance_unit="mm",
    )
    assert trial["status"] == "PASS"
    acc = StreamingPathQualityAccumulator()
    for _ in range(100):
        acc.on_sample(MovementSample(dx=10, dy=0))
    for _ in range(80):
        acc.on_sample(MovementSample(dx=-10, dy=0))
    out = attach_to_trial(trial, accumulator=acc)
    assert out["path_quality_status"] == "FAIL"
    assert "PATH_REVERSAL_OR_JITTER_FAIL" in out["path_quality_issue_codes"]
    assert out["status"] == "PASS"
    assert trial["status"] == "PASS"


def test_diagonal_vector_matches_hypot():
    samples = [MovementSample(dx=6, dy=8) for _ in range(10)]  # hypot 10 each
    snap = _run(samples, fixture_noise_floor_counts=7)
    assert snap["path_total_counts"] == 100.0
    assert snap["vector_counts"] == int(round(math.hypot(60, 80)))
    assert snap["status"] == "PASS"
