"""Capture Engine synthetic tests (no Windows hardware)."""

from __future__ import annotations

from pathlib import Path

from mouse_dpi_tool.capture import (
    CAPTURE_MUST_NOT_COMPUTE,
    CaptureEngine,
    CaptureState,
    SyntheticEventSource,
    VisualizationPathBuffer,
)
from mouse_dpi_tool.contracts.movement import VISUALIZATION_PATH_MAX_POINTS, MovementSample
from mouse_dpi_tool.path_quality import StreamingPathQualityAccumulator

CAPTURE_DIR = Path(__file__).resolve().parents[2] / "src" / "mouse_dpi_tool" / "capture"


def test_start_stop_cancel_lifecycle():
    engine = CaptureEngine()
    assert engine.state is CaptureState.IDLE
    engine.start()
    assert engine.state is CaptureState.RUNNING
    engine.feed(MovementSample(dx=5, dy=1, device_id="a"))
    engine.wait_until_idle()
    engine.stop()
    assert engine.state is CaptureState.STOPPED
    assert engine.net_counts_x == 5
    assert engine.net_counts_y == 1
    engine.cancel()
    assert engine.state is CaptureState.CANCELLED
    assert engine.net_counts_x == 0
    assert engine.net_counts_y == 0


def test_cancel_discards_counts_stop_keeps_them():
    engine = CaptureEngine()
    engine.start()
    engine.feed(MovementSample(dx=4, dy=-3))
    engine.wait_until_idle()
    engine.stop()
    assert (engine.net_counts_x, engine.net_counts_y) == (4, -3)
    engine2 = CaptureEngine()
    engine2.start()
    engine2.feed(MovementSample(dx=4, dy=-3))
    engine2.wait_until_idle()
    engine2.cancel()
    assert (engine2.net_counts_x, engine2.net_counts_y) == (0, 0)


def test_subscriber_receives_all_ordered_samples():
    samples = [MovementSample(dx=i, dy=-i, timestamp_s=float(i), device_id="d1") for i in range(1, 51)]
    received: list[MovementSample] = []
    engine = CaptureEngine(source=SyntheticEventSource(samples))
    engine.subscribe(received.append)
    engine.start()
    engine.wait_until_idle()
    engine.stop()
    assert [(s.dx, s.dy, s.timestamp_s) for s in received] == [(s.dx, s.dy, s.timestamp_s) for s in samples]
    assert engine.published_count == 50
    assert engine.net_counts_x == sum(s.dx for s in samples)
    assert engine.net_counts_y == sum(s.dy for s in samples)


def test_multiple_device_ids():
    samples = [
        MovementSample(dx=1, dy=0, device_id="11"),
        MovementSample(dx=2, dy=0, device_id="22"),
        MovementSample(dx=3, dy=0, device_id="11"),
    ]
    engine = CaptureEngine(source=SyntheticEventSource(samples))
    engine.start()
    engine.wait_until_idle()
    engine.stop()
    assert engine.device_ids == ("11", "22")
    assert engine.net_counts_x == 6
    assert engine.per_device_counts["11"] == {"dx": 4, "dy": 0, "event_count": 2}
    assert engine.per_device_counts["22"] == {"dx": 2, "dy": 0, "event_count": 1}

def test_pipeline_capture_to_path_quality():
    samples = [MovementSample(dx=10, dy=0, device_id="syn") for _ in range(40)]
    pq = StreamingPathQualityAccumulator()
    engine = CaptureEngine(source=SyntheticEventSource(samples))
    engine.subscribe(pq.on_sample)
    engine.start()
    engine.wait_until_idle()
    engine.stop()
    snap = pq.snapshot()
    assert engine.net_counts_x == 400
    assert snap["net_counts_x"] == 400
    assert snap["path_total_counts"] == 400.0
    assert snap["status"] == "PASS"
    assert snap["owner"] == "path_quality"


def test_viz_buffer_is_bounded_path_quality_is_not():
    n = VISUALIZATION_PATH_MAX_POINTS + 120
    samples = [MovementSample(dx=10, dy=0) for _ in range(n)]
    viz = VisualizationPathBuffer()
    pq = StreamingPathQualityAccumulator()
    engine = CaptureEngine(source=SyntheticEventSource(samples))
    engine.subscribe(pq.on_sample)
    engine.subscribe(viz.on_sample)
    engine.start()
    engine.wait_until_idle()
    engine.stop()
    assert pq.sample_count == n
    assert pq.snapshot()["net_counts_x"] == n * 10
    assert len(viz.points()) == viz.max_points


def test_capture_modules_do_not_compute_path_or_cpi():
    banned_snippets = (
        "measured_cpi",
        "compute_trial",
        "path_total_counts +=",
        "straightness_pct =",
        "PATH_REVERSAL",
    )
    offenders = []
    for path in CAPTURE_DIR.glob("*.py"):
        if path.name == "__init__.py":
            continue
        text = path.read_text(encoding="utf-8")
        for snippet in banned_snippets:
            if snippet in text:
                offenders.append(f"{path.name}:{snippet}")
    assert offenders == []
    assert "path_total_counts" in CAPTURE_MUST_NOT_COMPUTE
