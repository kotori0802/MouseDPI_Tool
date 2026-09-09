"""Capture timing O(1) stress — no progressive rebuild cost in timing accumulator."""

from __future__ import annotations

import time

from mouse_dpi_tool.capture import CaptureEngine, SyntheticEventSource
from mouse_dpi_tool.capture.motion_timing import StreamingMotionTimingAccumulator
from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.path_quality import StreamingPathQualityAccumulator
from mouse_dpi_tool.session import Session


def test_timing_accumulator_o1_under_many_samples():
    acc = StreamingMotionTimingAccumulator()
    acc.mark_capture_start(timestamp_s=0.0)
    t0 = time.perf_counter()
    for i in range(50_000):
        acc.on_sample(MovementSample(dx=1, dy=0, timestamp_s=i * 0.001))
    elapsed = time.perf_counter() - t0
    snap = acc.snapshot(distance_mm=50.8)
    assert snap["motion_sample_count"] == 50_000
    assert snap["timing_status"] == "OK"
    # Soft budget: O(1) work should stay well under a second on CI hardware.
    assert elapsed < 2.0


def test_synthetic_admit_cycles_with_timing_no_schema_break():
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
        measurement_context={"method": "synthetic", "direction": "X+", "surface": "lab cloth"},
        dut={"vendor": "T", "model": "M", "notes": ""},
        operator="stress",
    )
    for i in range(100):
        t0 = 10.0 + i
        timing = {
            "timing_status": "OK",
            "motion_sample_count": 20,
            "first_motion_timestamp": t0,
            "last_motion_timestamp": t0 + 0.8,
            "active_motion_duration_ms": 800.0,
            "estimated_traversal_speed_mm_s": 63.5,
            "timing_source": "sample_timestamp_s",
            "notes": "stress",
        }
        session.add_synthetic_trial(
            configured_dpi=400 + (i % 4) * 400,
            counts_x=400 + (i % 4) * 400,
            counts_y=0,
            motion_timing_snapshot=timing,
        )
    d = session.to_session_dict()
    assert d["metrics"]["active_trial_count"] == 100
    assert all("motion_timing" in t for t in d["trials"])
    # Findings keys unchanged / no overall
    assert "overall" not in d["findings"]
    assert "ratio" in d["findings"]


def test_engine_subscribe_timing_alongside_pq():
    samples = [
        MovementSample(dx=50, dy=0, timestamp_s=1.0 + i * 0.01) for i in range(40)
    ]
    eng = CaptureEngine(source=SyntheticEventSource(samples))
    pq = StreamingPathQualityAccumulator()
    timing = StreamingMotionTimingAccumulator()
    timing.mark_capture_start(timestamp_s=1.0)
    eng.subscribe(pq.on_sample)
    eng.subscribe(timing.on_sample)
    eng.start()
    eng.wait_until_idle()
    eng.stop()
    timing.mark_capture_stop(timestamp_s=2.0)
    snap = timing.snapshot(distance_mm=50.8)
    assert snap["motion_sample_count"] == 40
    assert snap["timing_status"] == "OK"
    assert pq.sample_count == 40
