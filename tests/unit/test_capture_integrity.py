"""Phase 1B-2.5 Capture integrity: faults, atomic start, stop/drain, per-device."""

from __future__ import annotations

from mouse_dpi_tool.capture import CaptureEngine, CaptureState, VisualizationPathBuffer
from mouse_dpi_tool.contracts.movement import VISUALIZATION_PATH_MAX_POINTS, MovementSample
from mouse_dpi_tool.path_quality import StreamingPathQualityAccumulator


class FailingEventSource:
    def start(self, emit_sample, emit_status) -> None:
        raise RuntimeError("source_start_boom")

    def stop(self) -> None:
        return None


class LateEmitOnStopSource:
    """Simulates producer stop with already-buffered deltas flushed during stop()."""

    def __init__(self) -> None:
        self._emit = None
        self.early = [
            MovementSample(dx=10, dy=0, device_id="a"),
            MovementSample(dx=10, dy=0, device_id="a"),
        ]
        self.late = [
            MovementSample(dx=7, dy=0, device_id="a"),
            MovementSample(dx=3, dy=1, device_id="b"),
        ]

    def start(self, emit_sample, emit_status) -> None:
        self._emit = emit_sample
        emit_status("late_source_started")
        for sample in self.early:
            emit_sample(sample)

    def stop(self) -> None:
        assert self._emit is not None
        for sample in self.late:
            self._emit(sample)


def test_subscriber_exception_does_not_kill_dispatcher_or_fake_clean_stop():
    received: list[int] = []

    def bad(sample: MovementSample) -> None:
        received.append(sample.dx)
        if sample.dx == 2:
            raise RuntimeError("listener_boom")

    samples = [MovementSample(dx=i, dy=0, device_id="d") for i in range(1, 6)]
    engine = CaptureEngine()
    engine.subscribe(bad)
    engine.start()
    for sample in samples:
        engine.feed(sample)
    engine.wait_until_idle()
    engine.stop()

    # Quarantine after first fault: listener receives through the failing sample only.
    assert received == [1, 2]
    assert engine.published_count == 5
    assert engine.net_counts_x == 15
    assert engine.complete is True
    assert engine.integrity_ok is False
    assert engine.state is CaptureState.ERROR
    assert engine.is_valid_complete_capture is False
    assert engine.last_error and "listener_boom" in engine.last_error
    assert len(engine.subscriber_errors) == 1
    assert any("listener_boom" in e for e in engine.subscriber_errors)


def test_failing_source_start_is_atomic_error_state():
    engine = CaptureEngine(source=FailingEventSource())
    try:
        engine.start()
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "source_start_boom" in str(exc)
    assert raised
    assert engine.state is CaptureState.ERROR
    assert engine.complete is False
    assert engine.integrity_ok is False
    assert engine.last_error and "EventSource.start failed" in engine.last_error
    assert engine._dispatch_thread is None  # noqa: SLF001 — no leaked dispatcher


def test_stop_retains_events_emitted_during_source_stop():
    source = LateEmitOnStopSource()
    received: list[MovementSample] = []
    engine = CaptureEngine(source=source)
    engine.subscribe(received.append)
    engine.start()
    engine.wait_until_idle()
    engine.stop()

    assert len(received) == 4
    assert [(s.dx, s.dy, s.device_id) for s in received] == [
        (10, 0, "a"),
        (10, 0, "a"),
        (7, 0, "a"),
        (3, 1, "b"),
    ]
    assert engine.net_counts_x == 30
    assert engine.net_counts_y == 1
    assert engine.state is CaptureState.STOPPED
    assert engine.is_valid_complete_capture is True


def test_per_device_counts_are_preserved():
    samples = [
        MovementSample(dx=1, dy=2, device_id="11"),
        MovementSample(dx=3, dy=0, device_id="22"),
        MovementSample(dx=4, dy=-1, device_id="11"),
        MovementSample(dx=5, dy=5, device_id=None),
    ]
    engine = CaptureEngine()
    engine.start()
    for sample in samples:
        engine.feed(sample)
    engine.wait_until_idle()
    engine.stop()

    assert engine.net_counts_x == 13
    assert engine.net_counts_y == 6
    assert engine.device_ids == ("11", "22")
    assert engine.per_device_counts == {
        "11": {"dx": 5, "dy": 1, "event_count": 2},
        "22": {"dx": 3, "dy": 0, "event_count": 1},
        "unknown": {"dx": 5, "dy": 5, "event_count": 1},
    }


def test_visualization_buffer_uses_bounded_deque():
    viz = VisualizationPathBuffer(max_points=8)
    for i in range(20):
        viz.on_sample(MovementSample(dx=1, dy=0))
    pts = viz.points()
    assert len(pts) == 8
    # O(1) structure: maxlen attribute from deque
    assert viz._points.maxlen == 8  # noqa: SLF001


def test_high_volume_pipeline_ordered_and_complete():
    n = 100_000
    samples = [MovementSample(dx=1, dy=0, device_id="stress", timestamp_s=float(i)) for i in range(n)]
    received: list[int] = []
    pq = StreamingPathQualityAccumulator(fixture_noise_floor_counts=0)
    engine = CaptureEngine()
    engine.subscribe(lambda s: received.append(s.dx))
    engine.subscribe(pq.on_sample)
    engine.start()
    for sample in samples:
        engine.feed(sample)
    engine.wait_until_idle(timeout=60.0)
    engine.stop()

    assert len(received) == n
    assert engine.published_count == n
    assert engine.net_counts_x == n
    assert engine.state is CaptureState.STOPPED
    assert engine.is_valid_complete_capture is True
    assert pq.sample_count == n
    assert pq.snapshot()["path_total_counts"] == float(n)
