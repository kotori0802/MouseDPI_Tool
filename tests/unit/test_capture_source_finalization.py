"""Phase 1B-2.6 — Source Finalization: ready handshake, conclusive stop, quarantine."""

from __future__ import annotations

import sys
import threading
import time

import pytest

from mouse_dpi_tool.capture import CaptureEngine, CaptureState
from mouse_dpi_tool.capture.raw_input_source import (
    BRIDGE_READY,
    RawInputSubprocessSource,
    SourceStartError,
    SourceStopError,
)
from mouse_dpi_tool.contracts.movement import MovementSample


def _py_cmd(script: str) -> list[str]:
    return [sys.executable, "-c", script]


READY_THEN_IDLE = f"""
import json, sys
print(json.dumps({{"type": "status", "message": "{BRIDGE_READY}"}}), flush=True)
for raw in sys.stdin:
    if (raw or "").strip().lower() in {{"stop", "quit", "exit"}}:
        break
"""

REGISTRATION_FAIL = """
import json, sys
print(json.dumps({"type": "status", "message": "RegisterRawInputDevices failed"}), flush=True)
time.sleep(1)
"""

EXIT_BEFORE_READY = """
import sys
sys.exit(2)
"""

NEVER_READY = """
import time
time.sleep(30)
"""

READY_THEN_DIE = f"""
import json, sys, time
print(json.dumps({{"type": "status", "message": "{BRIDGE_READY}"}}), flush=True)
time.sleep(0.15)
sys.exit(1)
"""


def test_ready_handshake_start_succeeds():
    statuses: list[str] = []
    source = RawInputSubprocessSource(
        command=_py_cmd(READY_THEN_IDLE),
        ready_timeout_sec=3.0,
        stop_timeout_sec=3.0,
    )
    source.start(lambda _s: None, statuses.append)
    assert any(BRIDGE_READY in s for s in statuses)
    source.stop()
    assert source._proc is None  # noqa: SLF001
    assert source._thread is None  # noqa: SLF001


def test_registration_failure_start_raises():
    statuses: list[str] = []
    source = RawInputSubprocessSource(
        command=_py_cmd(REGISTRATION_FAIL),
        ready_timeout_sec=3.0,
        stop_timeout_sec=3.0,
    )
    with pytest.raises(SourceStartError, match="RegisterRawInputDevices failed"):
        source.start(lambda _s: None, statuses.append)
    assert source._proc is None  # noqa: SLF001
    assert source._thread is None  # noqa: SLF001


def test_helper_exits_before_ready_start_raises():
    source = RawInputSubprocessSource(
        command=_py_cmd(EXIT_BEFORE_READY),
        ready_timeout_sec=3.0,
        stop_timeout_sec=3.0,
    )
    with pytest.raises(SourceStartError, match="exited before ready"):
        source.start(lambda _s: None, lambda _m: None)
    assert source._proc is None  # noqa: SLF001
    assert source._thread is None  # noqa: SLF001


def test_readiness_timeout_start_raises_and_no_leak():
    source = RawInputSubprocessSource(
        command=_py_cmd(NEVER_READY),
        ready_timeout_sec=0.4,
        stop_timeout_sec=3.0,
    )
    with pytest.raises(SourceStartError, match="readiness timeout"):
        source.start(lambda _s: None, lambda _m: None)
    assert source._proc is None  # noqa: SLF001
    assert source._thread is None  # noqa: SLF001


def test_alive_reader_cannot_produce_clean_stop():
    source = RawInputSubprocessSource(stop_timeout_sec=0.2)

    def hang() -> None:
        time.sleep(60)

    thread = threading.Thread(target=hang, name="fake-stuck-reader", daemon=True)
    thread.start()
    source._thread = thread  # noqa: SLF001
    source._proc = None  # noqa: SLF001 — producer already gone
    source._unexpected_exit = False  # noqa: SLF001

    with pytest.raises(SourceStopError, match="reader still alive"):
        source.stop()


def test_source_stop_failure_is_incomplete_and_not_reusable():
    class RaisingStopSource:
        def start(self, emit_sample, emit_status) -> None:
            emit_status("ok")
            emit_sample(MovementSample(dx=1, dy=0, device_id="d"))

        def stop(self) -> None:
            raise SourceStopError("reader still alive after stop timeout")

    engine = CaptureEngine(source=RaisingStopSource())
    engine.start()
    engine.wait_until_idle()
    engine.stop()

    assert engine.state is CaptureState.ERROR
    assert engine.complete is False
    assert engine.integrity_ok is False
    assert engine.is_valid_complete_capture is False
    assert engine.last_error and "EventSource.stop failed" in engine.last_error

    with pytest.raises(RuntimeError, match="faulted after inconclusive stop"):
        engine.start()


def test_completion_subscriber_failure_complete_true_integrity_false():
    def bad(sample: MovementSample) -> None:
        raise RuntimeError("listener_boom")

    engine = CaptureEngine()
    engine.subscribe(bad)
    engine.start()
    engine.feed(MovementSample(dx=1, dy=0))
    engine.wait_until_idle()
    engine.stop()
    assert engine.state is CaptureState.ERROR
    assert engine.complete is True
    assert engine.integrity_ok is False
    assert engine.is_valid_complete_capture is False


def test_completion_source_stop_failure_complete_false():
    class RaisingStopSource:
        def start(self, emit_sample, emit_status) -> None:
            return None

        def stop(self) -> None:
            raise SourceStopError("inconclusive drain")

    engine = CaptureEngine(source=RaisingStopSource())
    engine.start()
    engine.stop()
    assert engine.state is CaptureState.ERROR
    assert engine.complete is False
    assert engine.integrity_ok is False
    assert engine.is_valid_complete_capture is False


def test_completion_dispatcher_fatal_complete_false():
    engine = CaptureEngine()
    engine.start()
    engine._note_dispatcher_fatal(RuntimeError("dispatch_boom"))  # noqa: SLF001
    engine.stop()
    assert engine.state is CaptureState.ERROR
    assert engine.complete is False
    assert engine.integrity_ok is False
    assert engine.is_valid_complete_capture is False


def test_completion_clean_stop_complete_true_integrity_true():
    engine = CaptureEngine()
    engine.start()
    engine.feed(MovementSample(dx=2, dy=0))
    engine.wait_until_idle()
    engine.stop()
    assert engine.state is CaptureState.STOPPED
    assert engine.complete is True
    assert engine.integrity_ok is True
    assert engine.is_valid_complete_capture is True


def test_premature_bridge_death_invalidates_capture():
    statuses: list[str] = []
    source = RawInputSubprocessSource(
        command=_py_cmd(READY_THEN_DIE),
        ready_timeout_sec=3.0,
        stop_timeout_sec=3.0,
    )
    engine = CaptureEngine(source=source, on_status=statuses.append)
    engine.start()
    assert any(BRIDGE_READY in s for s in statuses)

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        if any("exited_unexpectedly" in s for s in statuses):
            break
        if source._proc is not None and source._proc.poll() is not None:  # noqa: SLF001
            break
        time.sleep(0.05)

    engine.stop()
    assert engine.state is CaptureState.ERROR
    assert engine.complete is False
    assert engine.is_valid_complete_capture is False
    assert engine.integrity_ok is False
    assert engine.last_error and "EventSource.stop failed" in engine.last_error
    with pytest.raises(RuntimeError, match="faulted after inconclusive stop"):
        engine.start()


def test_failing_subscriber_quarantined_after_first_fault():
    good: list[int] = []
    bad_calls = 0

    def always_bad(sample: MovementSample) -> None:
        nonlocal bad_calls
        bad_calls += 1
        raise RuntimeError("perm_fail")

    def healthy(sample: MovementSample) -> None:
        good.append(sample.dx)

    n = 1000
    engine = CaptureEngine()
    engine.subscribe(always_bad)
    engine.subscribe(healthy)
    engine.start()
    for i in range(n):
        engine.feed(MovementSample(dx=1, dy=0, device_id="d"))
    engine.wait_until_idle()
    engine.stop()

    assert bad_calls == 1
    assert len(engine.subscriber_errors) == 1
    assert len(good) == n
    assert engine.published_count == n
    assert engine.state is CaptureState.ERROR
    assert engine.is_valid_complete_capture is False


def test_status_callback_exception_does_not_kill_dispatcher():
    received: list[int] = []

    def boom_status(_message: str) -> None:
        raise RuntimeError("status_ui_boom")

    engine = CaptureEngine(on_status=boom_status)
    engine.subscribe(lambda s: received.append(s.dx))
    engine.start()
    # Force a status emit via subscriber quarantine path and via direct emit.
    engine._emit_status("probe")  # noqa: SLF001
    for i in range(1, 6):
        engine.feed(MovementSample(dx=i, dy=0))
    engine.wait_until_idle()
    engine.stop()

    assert received == [1, 2, 3, 4, 5]
    assert engine.published_count == 5
    assert engine.state is CaptureState.STOPPED
    assert engine.is_valid_complete_capture is True
    assert any("status_ui_boom" in e for e in engine.status_callback_errors)
