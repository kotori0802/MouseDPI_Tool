"""Subprocess Windows Raw Input source.

Start contract
--------------
start() returns success only after the bridge readiness handshake:
  raw_input_delta_bridge_started
Registration failure, early helper exit, or readiness timeout → raise SourceStartError
(and clean up process/reader).

Frozen builds must launch MouseDPI_RawInputBridge.exe — never re-exec the UI EXE
with a .py script argument.

Stop contract (Phase 2.1 — Capture Count Integrity)
---------------------------------------------------
1. Mark shutdown *expected* (does NOT suppress delta forwarding).
2. Graceful: write ``stop\\n`` on helper stdin → wait process exit.
3. Parent reader continues forwarding ALL remaining stdout delta lines until EOF.
4. Join reader after natural EOF (preferred).
5. close local stdout only as emergency unblock if reader will not exit.
6. terminate/kill are cleanup-only → raise SourceStopError (not evidence-complete).
7. Unexpected helper exit before shutdown request → SourceStopError.

EventSource.stop() must not return successfully while the source can still emit
samples, and must not discard pipe-buffered samples produced before EOF.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Sequence
from typing import Any

from mouse_dpi_tool.capture.bridge_command import (
    BridgeHelperNotFoundError,
    resolve_bridge_command,
)
from mouse_dpi_tool.contracts.movement import MovementSample

BRIDGE_READY = "raw_input_delta_bridge_started"
BRIDGE_STOP_CMD = "stop\n"

# Hide the helper console window when the parent is a GUI app (Windows).
_CREATE_NO_WINDOW = 0x08000000


class SourceStartError(RuntimeError):
    """Windows Raw Input source failed before readiness."""


class SourceStopError(RuntimeError):
    """Source could not be conclusively stopped/drained, or died prematurely."""


def _bridge_command() -> list[str]:
    try:
        return resolve_bridge_command()
    except BridgeHelperNotFoundError as exc:
        raise SourceStartError(str(exc)) from exc


def _popen_kwargs() -> dict:
    kwargs: dict = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        # stdin is the graceful-stop control channel for the packaged helper.
        "stdin": subprocess.PIPE,
        "text": True,
        "bufsize": 1,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = _CREATE_NO_WINDOW
    return kwargs


class RawInputSubprocessSource:
    def __init__(
        self,
        *,
        command: Sequence[str] | None = None,
        ready_timeout_sec: float = 5.0,
        stop_timeout_sec: float = 5.0,
        popen_factory=subprocess.Popen,
    ) -> None:
        # Resolve at construction when using the default so missing helper fails early.
        if command is not None:
            self._command = list(command)
        else:
            self._command = _bridge_command()
        self._ready_timeout_sec = float(ready_timeout_sec)
        self._stop_timeout_sec = float(stop_timeout_sec)
        self._popen_factory = popen_factory
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._start_failed_reason: str | None = None
        # Expected shutdown classification only — MUST NOT suppress delta forwarding.
        self._shutdown_requested = False
        self._unexpected_exit = False
        self._lock = threading.Lock()
        self._last_stop_duration_ms: float | None = None
        self._last_stop_path: str | None = None
        self._reader_eof_observed = False
        self._ready_timestamp_s: float | None = None
        self._stop_request_timestamp_s: float | None = None
        self._reader_join_duration_ms: float | None = None
        self._delta_lines_parsed = 0
        self._delta_lines_forwarded = 0
        self._delta_lines_dropped = 0  # Should stay 0 on graceful drain (qualification).

    @property
    def last_stop_duration_ms(self) -> float | None:
        return self._last_stop_duration_ms

    @property
    def last_stop_path(self) -> str | None:
        """How producer teardown completed: graceful | terminate | kill | already_exited."""
        return self._last_stop_path

    def qualification_diagnostics(self) -> dict[str, Any]:
        """Presentation/debug counters only — not Session / Findings evidence."""
        return {
            "ready_timestamp_s": self._ready_timestamp_s,
            "stop_request_timestamp_s": self._stop_request_timestamp_s,
            "delta_lines_parsed": int(self._delta_lines_parsed),
            "delta_lines_forwarded": int(self._delta_lines_forwarded),
            "delta_lines_dropped": int(self._delta_lines_dropped),
            "reader_eof_observed": bool(self._reader_eof_observed),
            "stop_path": self._last_stop_path,
            "reader_join_duration_ms": self._reader_join_duration_ms,
            "last_stop_duration_ms": self._last_stop_duration_ms,
        }

    def start(
        self,
        emit_sample: Callable[[MovementSample], None],
        emit_status: Callable[[str], None],
    ) -> None:
        if self._proc and self._proc.poll() is None:
            return

        self._ready.clear()
        self._start_failed_reason = None
        self._shutdown_requested = False
        self._unexpected_exit = False
        self._last_stop_duration_ms = None
        self._last_stop_path = None
        self._reader_eof_observed = False
        self._ready_timestamp_s = None
        self._stop_request_timestamp_s = None
        self._reader_join_duration_ms = None
        self._delta_lines_parsed = 0
        self._delta_lines_forwarded = 0
        self._delta_lines_dropped = 0

        try:
            self._proc = self._popen_factory(self._command, **_popen_kwargs())
        except OSError as exc:
            winerr = getattr(exc, "winerror", None)
            if winerr == 4551 or "4551" in str(exc):
                raise SourceStartError(
                    "Windows Application Control blocked MouseDPI_RawInputBridge.exe "
                    "(WinError 4551). Unblock that helper beside the UI EXE in Windows "
                    "Security, or run the unpackaged app: mouse-dpi-tool ui"
                ) from exc
            raise SourceStartError(f"failed to launch Raw Input helper: {exc}") from exc
        self._thread = threading.Thread(
            target=self._reader,
            args=(emit_sample, emit_status),
            name="mouse-dpi-raw-input-reader",
            daemon=True,
        )
        self._thread.start()

        deadline = time.monotonic() + self._ready_timeout_sec
        while time.monotonic() < deadline:
            if self._ready.wait(timeout=0.05):
                break
            if self._proc is not None and self._proc.poll() is not None and not self._ready.is_set():
                self._force_shutdown()
                raise SourceStartError("helper exited before ready handshake")
        else:
            self._force_shutdown()
            raise SourceStartError(
                f"readiness timeout after {self._ready_timeout_sec:g}s "
                f"(waiting for '{BRIDGE_READY}')"
            )

        if self._start_failed_reason:
            reason = self._start_failed_reason
            self._force_shutdown()
            raise SourceStartError(reason)

        if self._proc is not None and self._proc.poll() is not None:
            self._force_shutdown()
            raise SourceStartError("helper exited immediately after ready handshake")

        emit_status(f"raw_input_source_ready:{BRIDGE_READY}")

    def stop(self) -> None:
        """Stop producer and drain stdout. Non-graceful teardown → SourceStopError."""
        t0 = time.monotonic()
        with self._lock:
            premature = self._unexpected_exit
            proc = self._proc
            if proc is not None and proc.poll() is not None and not self._shutdown_requested:
                premature = True
            self._shutdown_requested = True
            self._stop_request_timestamp_s = time.monotonic()

        inconclusive: str | None = None
        try:
            path = self._shutdown_producer()
            self._last_stop_path = path
            if path in {"terminate", "kill"}:
                inconclusive = f"non-graceful stop path: {path}"

            # Preferred: natural EOF after child exit — do not close stdout yet.
            if not self._join_reader(timeout=self._stop_timeout_sec):
                # Emergency unblock only.
                self._close_stdout_to_unblock_reader()
                if not self._join_reader(timeout=self._stop_timeout_sec):
                    inconclusive = (
                        inconclusive
                        or "reader still alive after stop timeout; source may still emit"
                    )

            with self._lock:
                premature = premature or self._unexpected_exit

            if premature:
                raise SourceStopError("bridge exited prematurely during active capture")
            if inconclusive:
                raise SourceStopError(inconclusive)
        finally:
            self._last_stop_duration_ms = (time.monotonic() - t0) * 1000.0
            self._proc = None
            self._thread = None

    def force_kill(self) -> None:
        """Best-effort hard cleanup for Discard / application close."""
        with self._lock:
            self._shutdown_requested = True
        try:
            self._kill_producer()
        except Exception:
            pass
        self._close_stdout_to_unblock_reader()
        try:
            self._join_reader(timeout=self._stop_timeout_sec)
        except Exception:
            pass
        self._proc = None
        self._thread = None

    def _request_graceful_stop(self) -> None:
        proc = self._proc
        if proc is None or proc.stdin is None:
            return
        try:
            proc.stdin.write(BRIDGE_STOP_CMD)
            proc.stdin.flush()
        except Exception:
            pass
        try:
            proc.stdin.close()
        except Exception:
            pass

    def _shutdown_producer(self) -> str:
        """graceful → terminate → kill. Returns stop path label."""
        proc = self._proc
        if proc is None:
            return "already_exited"
        if proc.poll() is not None:
            return "already_exited"

        self._request_graceful_stop()
        try:
            proc.wait(timeout=self._stop_timeout_sec)
            return "graceful"
        except subprocess.TimeoutExpired:
            pass

        try:
            proc.terminate()
        except OSError:
            pass
        try:
            proc.wait(timeout=self._stop_timeout_sec)
            return "terminate"
        except subprocess.TimeoutExpired:
            pass

        self._kill_producer()
        return "kill"

    def _kill_producer(self) -> None:
        proc = self._proc
        if proc is None:
            return
        if proc.poll() is not None:
            return
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=self._stop_timeout_sec)
        except subprocess.TimeoutExpired as exc:
            raise SourceStopError("producer process did not terminate after kill") from exc

    def _close_stdout_to_unblock_reader(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        try:
            proc.stdout.close()
        except Exception:
            pass

    def _join_reader(self, *, timeout: float) -> bool:
        """Join reader thread. Returns True if reader is no longer alive."""
        thread = self._thread
        if thread is None:
            return True
        t0 = time.monotonic()
        thread.join(timeout=timeout)
        self._reader_join_duration_ms = (time.monotonic() - t0) * 1000.0
        return not thread.is_alive()

    def _force_shutdown(self) -> None:
        with self._lock:
            self._shutdown_requested = True
        try:
            self._shutdown_producer()
        except SourceStopError:
            pass
        self._close_stdout_to_unblock_reader()
        try:
            self._join_reader(timeout=self._stop_timeout_sec)
        except Exception:
            pass
        self._proc = None
        self._thread = None

    def _reader(
        self,
        emit_sample: Callable[[MovementSample], None],
        emit_status: Callable[[str], None],
    ) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    emit_status(line)
                    continue
                if event.get("type") == "delta":
                    with self._lock:
                        self._delta_lines_parsed += 1
                    # Phase 2.1: forward through graceful drain until EOF.
                    # CaptureEngine owns acceptance freeze after EventSource.stop returns.
                    emit_sample(
                        MovementSample(
                            dx=int(event.get("dx", 0)),
                            dy=int(event.get("dy", 0)),
                            timestamp_s=(
                                float(event["time_perf"])
                                if event.get("time_perf") is not None
                                else None
                            ),
                            device_id=(
                                str(event["device"])
                                if event.get("device") is not None
                                else None
                            ),
                        )
                    )
                    with self._lock:
                        self._delta_lines_forwarded += 1
                    continue

                message = str(event.get("message", event))
                self._observe_status_message(message)
                emit_status(message)
            with self._lock:
                self._reader_eof_observed = True
        finally:
            with self._lock:
                shutdown_requested = self._shutdown_requested
                if not shutdown_requested:
                    self._unexpected_exit = True
            if not shutdown_requested:
                try:
                    emit_status("raw_input_bridge_exited_unexpectedly")
                except Exception:
                    pass
            try:
                emit_status("raw_input_reader_stopped")
            except Exception:
                pass
            # Unblock a start() waiter if the helper died before ready.
            if not self._ready.is_set():
                if self._start_failed_reason is None and not shutdown_requested:
                    self._start_failed_reason = "helper exited before ready handshake"
                self._ready.set()

    def _observe_status_message(self, message: str) -> None:
        if self._ready.is_set():
            return
        if message == BRIDGE_READY:
            self._ready_timestamp_s = time.monotonic()
            self._ready.set()
            return
        lowered = message.lower()
        if "failed" in lowered or "error" in lowered:
            self._start_failed_reason = message
            self._ready.set()
