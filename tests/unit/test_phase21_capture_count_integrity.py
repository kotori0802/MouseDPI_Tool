"""Phase 2.1 — Capture count integrity (Raw Input stop/drain contract)."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time

import pytest

from mouse_dpi_tool.capture import CaptureEngine, CaptureState
from mouse_dpi_tool.capture.raw_input_source import (
    BRIDGE_READY,
    RawInputSubprocessSource,
    SourceStopError,
)
from mouse_dpi_tool.contracts.movement import MovementSample


def _py_cmd(script: str) -> list[str]:
    return [sys.executable, "-c", script]


def _delta(dx: int, dy: int = 0) -> str:
    return json.dumps({"type": "delta", "dx": dx, "dy": dy, "device": "1", "time_perf": 1.0})


READY_STOPPABLE_WITH_TAIL = f"""
import json, sys

print(json.dumps({{"type": "status", "message": "{BRIDGE_READY}"}}), flush=True)
print({_delta(10)!r}, flush=True)
for raw in sys.stdin:
    if (raw or "").strip().lower() in {{"stop", "quit", "exit"}}:
        break
# Buffered tail AFTER stop request — parent must still forward these.
print({_delta(20)!r}, flush=True)
print({_delta(30)!r}, flush=True)
print(json.dumps({{"type": "status", "message": "raw_input_delta_bridge_stopped"}}), flush=True)
"""

READY_THEN_HANG = f"""
import json, sys, time
print(json.dumps({{"type": "status", "message": "{BRIDGE_READY}"}}), flush=True)
# Ignore stdin — force parent graceful timeout → terminate/kill.
time.sleep(60)
"""

READY_THEN_DIE = f"""
import json, sys, time
print(json.dumps({{"type": "status", "message": "{BRIDGE_READY}"}}), flush=True)
time.sleep(0.15)
sys.exit(1)
"""

HIGH_VOLUME = f"""
import json, sys
print(json.dumps({{"type": "status", "message": "{BRIDGE_READY}"}}), flush=True)
n = 5000
for i in range(n):
    print(json.dumps({{"type": "delta", "dx": 1, "dy": 0, "device": "1", "time_perf": float(i)}}), flush=True)
for raw in sys.stdin:
    if (raw or "").strip().lower() in {{"stop", "quit", "exit"}}:
        break
print(json.dumps({{"type": "status", "message": "raw_input_delta_bridge_stopped"}}), flush=True)
"""


class _ControlledStdout:
    """Fake process stdout that can inject lines after stop is requested."""

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._cv = threading.Condition()
        self._closed = False
        self._eof = False

    def push(self, line: str) -> None:
        with self._cv:
            self._lines.append(line)
            self._cv.notify_all()

    def close_writer(self) -> None:
        with self._cv:
            self._eof = True
            self._cv.notify_all()

    def close(self) -> None:
        with self._cv:
            self._closed = True
            self._eof = True
            self._cv.notify_all()

    def __iter__(self):
        return self

    def __next__(self) -> str:
        with self._cv:
            while not self._lines and not self._eof and not self._closed:
                self._cv.wait(timeout=0.05)
            if self._lines:
                return self._lines.pop(0)
            raise StopIteration


class _FakeProc:
    def __init__(self, stdout: _ControlledStdout) -> None:
        self.stdout = stdout
        self.stdin = _FakeStdin(self)
        self._returncode: int | None = None
        self._exit = threading.Event()

    def poll(self) -> int | None:
        return self._returncode

    def wait(self, timeout: float | None = None) -> int:
        if not self._exit.wait(timeout=timeout):
            raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout or 0)
        assert self._returncode is not None
        return self._returncode

    def terminate(self) -> None:
        self._returncode = -15
        self._exit.set()
        self.stdout.close_writer()

    def kill(self) -> None:
        self._returncode = -9
        self._exit.set()
        self.stdout.close_writer()

    def mark_exited(self, code: int = 0) -> None:
        self._returncode = code
        self._exit.set()


class _FakeStdin:
    def __init__(self, proc: _FakeProc) -> None:
        self._proc = proc
        self.writes: list[str] = []

    def write(self, data: str) -> int:
        self.writes.append(data)
        return len(data)

    def flush(self) -> None:
        return None

    def close(self) -> None:
        # Graceful: after stop command, push buffered tail then exit/EOF.
        self._proc.stdout.push(_delta(20) + "\n")
        self._proc.stdout.push(_delta(30) + "\n")
        self._proc.mark_exited(0)
        self._proc.stdout.close_writer()


def test_buffered_tail_survives_stop_request():
    """Stop request must not drop pipe-buffered deltas before EOF."""
    stdout = _ControlledStdout()
    proc = _FakeProc(stdout)

    def fake_popen(_cmd, **_kwargs):
        return proc

    source = RawInputSubprocessSource(
        command=[sys.executable, "-c", "pass"],
        ready_timeout_sec=2.0,
        stop_timeout_sec=2.0,
        popen_factory=fake_popen,
    )
    samples: list[MovementSample] = []
    statuses: list[str] = []

    def boot() -> None:
        time.sleep(0.05)
        stdout.push(json.dumps({"type": "status", "message": BRIDGE_READY}) + "\n")
        stdout.push(_delta(10) + "\n")

    threading.Thread(target=boot, daemon=True).start()
    source.start(samples.append, statuses.append)
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and len(samples) < 1:
        time.sleep(0.01)
    assert len(samples) == 1
    assert samples[0].dx == 10

    source.stop()
    assert [s.dx for s in samples] == [10, 20, 30]
    assert source.last_stop_path == "graceful"
    diag = source.qualification_diagnostics()
    assert diag["delta_lines_forwarded"] == 3
    assert diag["delta_lines_dropped"] == 0
    assert diag["reader_eof_observed"] is True


def test_graceful_child_exit_with_stdout_backlog():
    samples: list[MovementSample] = []
    source = RawInputSubprocessSource(
        command=_py_cmd(READY_STOPPABLE_WITH_TAIL),
        ready_timeout_sec=3.0,
        stop_timeout_sec=5.0,
    )
    source.start(samples.append, lambda _m: None)
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and not samples:
        time.sleep(0.01)
    assert samples and samples[0].dx == 10
    source.stop()
    assert [s.dx for s in samples] == [10, 20, 30]
    assert source.last_stop_path == "graceful"
    assert sum(s.dx for s in samples) == 60


def test_graceful_timeout_terminate_raises():
    source = RawInputSubprocessSource(
        command=_py_cmd(READY_THEN_HANG),
        ready_timeout_sec=2.0,
        stop_timeout_sec=0.3,
    )
    source.start(lambda _s: None, lambda _m: None)
    with pytest.raises(SourceStopError, match="non-graceful stop path"):
        source.stop()
    assert source.last_stop_path in {"terminate", "kill"}


def test_non_graceful_source_stop_engine_not_admissible():
    class NonGracefulSource:
        def start(self, emit_sample, emit_status) -> None:
            emit_status(BRIDGE_READY)
            emit_sample(MovementSample(dx=5, dy=0, device_id="d"))

        def stop(self) -> None:
            raise SourceStopError("non-graceful stop path: terminate")

    engine = CaptureEngine(source=NonGracefulSource())
    engine.start()
    engine.wait_until_idle()
    engine.stop()
    assert engine.state is CaptureState.ERROR
    assert engine.complete is False
    assert engine.integrity_ok is False
    assert engine.is_valid_complete_capture is False


def test_high_volume_graceful_drain_preserves_all_deltas():
    samples: list[MovementSample] = []
    source = RawInputSubprocessSource(
        command=_py_cmd(HIGH_VOLUME),
        ready_timeout_sec=5.0,
        stop_timeout_sec=10.0,
    )
    source.start(samples.append, lambda _m: None)
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline and len(samples) < 4000:
        time.sleep(0.02)
    source.stop()
    assert source.last_stop_path == "graceful"
    assert len(samples) == 5000
    assert sum(s.dx for s in samples) == 5000
    diag = source.qualification_diagnostics()
    assert diag["delta_lines_forwarded"] == 5000
    assert diag["delta_lines_dropped"] == 0


def test_start_handshake_still_requires_bridge_ready():
    statuses: list[str] = []
    source = RawInputSubprocessSource(
        command=_py_cmd(
            f"""
import json, sys
print(json.dumps({{"type": "status", "message": "{BRIDGE_READY}"}}), flush=True)
for raw in sys.stdin:
    if (raw or "").strip().lower() in {{"stop", "quit", "exit"}}:
        break
"""
        ),
        ready_timeout_sec=3.0,
        stop_timeout_sec=3.0,
    )
    source.start(lambda _s: None, statuses.append)
    assert any(BRIDGE_READY in s for s in statuses)
    source.stop()
    assert source.last_stop_path == "graceful"


def test_unexpected_exit_still_invalidates_capture():
    statuses: list[str] = []
    source = RawInputSubprocessSource(
        command=_py_cmd(READY_THEN_DIE),
        ready_timeout_sec=3.0,
        stop_timeout_sec=3.0,
    )
    engine = CaptureEngine(source=source, on_status=statuses.append)
    engine.start()
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        if any("exited_unexpectedly" in s for s in statuses):
            break
        time.sleep(0.05)
    engine.stop()
    assert engine.state is CaptureState.ERROR
    assert engine.complete is False
    assert engine.is_valid_complete_capture is False
