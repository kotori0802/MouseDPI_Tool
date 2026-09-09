"""UI-1B.3A — conclusive Stop, Discard Failed Run, sample freeze on teardown."""

from __future__ import annotations

import sys
import threading
import time

import pytest

from mouse_dpi_tool.capture import CaptureEngine, CaptureState, SyntheticEventSource
from mouse_dpi_tool.capture.raw_input_source import (
    BRIDGE_READY,
    RawInputSubprocessSource,
    SourceStopError,
)
from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.ui.controllers import AppController


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Raw Input helper")
def test_graceful_stdin_stop_exits_reader_and_helper():
    """Healthy Stop should use stdin stop and leave no live reader."""
    source = RawInputSubprocessSource(stop_timeout_sec=5.0)
    statuses: list[str] = []
    samples: list[MovementSample] = []
    source.start(samples.append, statuses.append)
    assert any(BRIDGE_READY in s for s in statuses)
    assert source._proc is not None and source._proc.poll() is None  # noqa: SLF001
    source.stop()
    assert source._proc is None  # noqa: SLF001
    assert source._thread is None  # noqa: SLF001
    assert source.last_stop_path in {"graceful", "terminate", "kill", "already_exited"}
    # Prefer graceful on the real module bridge.
    assert source.last_stop_path == "graceful"
    assert source.last_stop_duration_ms is not None
    assert source.last_stop_duration_ms < 5000


def test_engine_rejects_samples_after_stop_begins():
    engine = CaptureEngine(source=SyntheticEventSource([]))
    engine.start()
    engine.feed(MovementSample(dx=5, dy=0, device_id="a"))
    engine.wait_until_idle()
    # Simulate teardown acceptance freeze before drain.
    with engine._lock:  # noqa: SLF001
        engine._accepting_samples = False  # noqa: SLF001
    engine._enqueue_sample(MovementSample(dx=99, dy=0, device_id="a"))  # noqa: SLF001
    engine.stop()
    assert engine.net_counts_x == 5
    assert engine.state is CaptureState.STOPPED


def test_discard_failed_run_unlocks_after_stop_error():
    class FaultyStopSource:
        def start(self, on_sample, on_status=None):
            if on_status:
                on_status(BRIDGE_READY)
            on_sample(MovementSample(dx=10, dy=0, device_id="s"))

        def stop(self):
            raise SourceStopError("reader still alive after stop timeout")

        def force_kill(self):
            return None

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=lambda *, on_status=None: CaptureEngine(
            source=FaultyStopSource(), on_status=on_status
        ),
    )
    controller.set_direction("X+")
    controller.start_capture()
    controller.stop_capture()
    assert controller._engine.snapshot().state == CaptureState.ERROR.value
    assert controller.measurement_config_locked is True
    with pytest.raises(RuntimeError, match="frozen"):
        controller.update_distance(distance_input=50.0, unit="mm")
    vm = controller.capture_viewmodel()
    assert vm.can_discard is True
    assert vm.can_admit is False
    controller.discard_capture()
    assert controller.measurement_config_locked is False
    assert controller.run_config is None
    assert controller._engine is None
    controller.update_distance(distance_input=50.0, unit="mm")
    assert abs(float(controller.session.settings["distance_mm"]) - 50.0) < 1e-9
    assert "capture_discarded" in controller._last_status


def test_discard_valid_stopped_without_admit():
    samples = [MovementSample(dx=3150, dy=0, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=lambda *, on_status=None: CaptureEngine(
            source=SyntheticEventSource(samples), on_status=on_status
        ),
    )
    controller.set_direction("X+")
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    assert controller.capture_viewmodel().can_admit is True
    assert controller.capture_viewmodel().can_discard is True
    controller.discard_capture()
    assert controller.measurement_config_locked is False
    assert controller.session.active_trials == []


def test_stop_status_includes_timing_diagnostics():
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=lambda *, on_status=None: CaptureEngine(
            source=SyntheticEventSource([MovementSample(dx=1, dy=0, device_id="s")]),
            on_status=on_status,
        ),
    )
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    assert "stop_ms=" in controller._last_status
