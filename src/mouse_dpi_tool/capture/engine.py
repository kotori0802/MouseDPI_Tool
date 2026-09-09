"""Capture Engine — Raw Input / synthetic event source.

Threading / event-delivery model
--------------------------------
1. Event source thread (Windows stdout reader, or test injector) never computes
   metrics. It only enqueues MovementSample (or a stop sentinel).
2. A single dispatcher thread dequeues **every** sample in order, updates net
   dx/dy + per-device counts, then calls subscribers. Source events are not dropped.
3. Subscriber exceptions are **isolated** and the failing listener is **quarantined**
   after its first fault (one error record). Other subscribers continue.
4. on_status callbacks are presentation-only: exceptions are swallowed so they
   cannot kill the dispatcher.
5. queue.Queue is unbounded so a temporarily busy dispatcher cannot lose samples.
6. stop() ordering: stop producer (must not return while source can emit) →
   drain Capture queue → stop dispatcher → mark complete/STOPPED or ERROR.

Capture does not compute CPI, path_total, straightness, findings, or reports.
"""

from __future__ import annotations

import queue
import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from mouse_dpi_tool.contracts.movement import MovementSample

Listener = Callable[[MovementSample], None]
StatusListener = Callable[[str], None]

_STOP = object()


class CaptureState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass(frozen=True)
class CaptureSnapshot:
    """Coherent presentation/evidence read for the GUI thread."""

    state: str
    net_counts_x: int
    net_counts_y: int
    published_count: int
    device_ids: tuple[str, ...]
    complete: bool
    integrity_ok: bool
    is_valid_complete_capture: bool
    last_error: str | None
    # Presentation/debug diagnostics only — not Session / Findings evidence.
    queue_depth: int = 0
    max_queue_depth: int = 0
    dispatcher_processed_count: int = 0
    generation: int = 0
    stale_sample_count: int = 0


class EventSource(Protocol):
    def start(
        self,
        emit_sample: Callable[[MovementSample], None],
        emit_status: Callable[[str], None],
    ) -> None: ...

    def stop(self) -> None: ...


class CaptureEngine:
    def __init__(
        self,
        source: EventSource | None = None,
        *,
        on_status: StatusListener | None = None,
    ) -> None:
        self._source = source
        self._on_status = on_status
        self._listeners: list[Listener] = []
        self._quarantined: set[int] = set()
        self._queue: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._dispatch_thread: threading.Thread | None = None
        self._state = CaptureState.IDLE
        self._net_x = 0
        self._net_y = 0
        self._devices: set[str] = set()
        self._per_device: dict[str, dict[str, int]] = {}
        self._published = 0
        self._complete = False
        self._integrity_ok = True
        self._last_error: str | None = None
        self._subscriber_errors: list[str] = []
        self._status_callback_errors: list[str] = []
        self._dispatcher_fatal = False
        # After EventSource.stop() fails, this engine+source must not start again.
        self._source_faulted = False
        self._max_queue_depth = 0
        self._dispatcher_processed = 0
        self._accepting_samples = False
        self._last_stop_duration_ms: float | None = None
        self._generation = 0
        self._stale_sample_count = 0

    def _set_state(self, state: CaptureState) -> None:
        with self._lock:
            self._state = state

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    @property
    def state(self) -> CaptureState:
        return self._state

    @property
    def net_counts_x(self) -> int:
        return self._net_x

    @property
    def net_counts_y(self) -> int:
        return self._net_y

    @property
    def device_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._devices))

    @property
    def per_device_counts(self) -> dict[str, dict[str, int]]:
        """Per-device dx/dy/event_count. Keys are device_id or 'unknown'."""
        with self._lock:
            return {k: dict(v) for k, v in self._per_device.items()}

    @property
    def published_count(self) -> int:
        return self._published

    @property
    def complete(self) -> bool:
        """True when stop drain finished and dispatcher exited via STOP sentinel.

        False when source stop/drain was inconclusive or the dispatcher died —
        raw capture completeness cannot be asserted in those cases.
        """
        return self._complete

    @property
    def integrity_ok(self) -> bool:
        """True only for a clean, complete capture with no subscriber/dispatcher faults."""
        return (
            self._integrity_ok
            and self._complete
            and not self._subscriber_errors
            and not self._dispatcher_fatal
        )

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def subscriber_errors(self) -> tuple[str, ...]:
        return tuple(self._subscriber_errors)

    @property
    def status_callback_errors(self) -> tuple[str, ...]:
        return tuple(self._status_callback_errors)

    @property
    def last_stop_duration_ms(self) -> float | None:
        return self._last_stop_duration_ms

    @property
    def generation(self) -> int:
        """Active capture generation / epoch (0 before first successful start)."""
        return self._generation

    @property
    def stale_sample_count(self) -> int:
        """Samples rejected as closed-generation or post-accept-freeze arrivals."""
        return self._stale_sample_count

    @property
    def is_valid_complete_capture(self) -> bool:
        """Session Writer must require this; STOPPED alone is not enough."""
        return self._state is CaptureState.STOPPED and self.integrity_ok

    def snapshot(self) -> CaptureSnapshot:
        """Thread-safe coherent snapshot for UI polling (does not compute CPI)."""
        with self._lock:
            integrity = (
                self._integrity_ok
                and self._complete
                and not self._subscriber_errors
                and not self._dispatcher_fatal
            )
            state = self._state
            return CaptureSnapshot(
                state=state.value,
                net_counts_x=int(self._net_x),
                net_counts_y=int(self._net_y),
                published_count=int(self._published),
                device_ids=tuple(sorted(self._devices)),
                complete=bool(self._complete),
                integrity_ok=bool(integrity),
                is_valid_complete_capture=bool(state is CaptureState.STOPPED and integrity),
                last_error=self._last_error,
                queue_depth=int(self._queue.qsize()),
                max_queue_depth=int(self._max_queue_depth),
                dispatcher_processed_count=int(self._dispatcher_processed),
                generation=int(self._generation),
                stale_sample_count=int(self._stale_sample_count),
            )

    def start(self) -> None:
        if self._source_faulted:
            raise RuntimeError(
                "CaptureEngine source is faulted after inconclusive stop; "
                "create a new CaptureEngine/source for the next capture"
            )
        if self._state is CaptureState.RUNNING:
            return
        self._reset_live()
        self._generation += 1
        self._stale_sample_count = 0
        self._complete = False
        self._integrity_ok = True
        self._last_error = None
        self._subscriber_errors = []
        self._status_callback_errors = []
        self._dispatcher_fatal = False
        self._quarantined.clear()
        self._max_queue_depth = 0
        self._dispatcher_processed = 0
        self._accepting_samples = True
        self._last_stop_duration_ms = None
        self._set_state(CaptureState.RUNNING)
        self._dispatch_thread = threading.Thread(
            target=self._dispatch_loop, name="mouse-dpi-capture-dispatch", daemon=True
        )
        self._dispatch_thread.start()
        try:
            if self._source is not None:
                # Windows Raw Input start blocks until ready handshake (or raises).
                self._source.start(self._enqueue_sample, self._emit_status)
        except Exception as exc:
            self._abort_failed_start(exc)
            raise

    def stop(self) -> None:
        """End capture: stop producer, drain events, then stop dispatcher."""
        if self._state is not CaptureState.RUNNING:
            if self._source is not None:
                try:
                    self._source.stop()
                except Exception:
                    self._source_faulted = True
            return

        t0 = time.monotonic()
        source_error: str | None = None
        if self._source is not None:
            try:
                # Producer stop must not return while the source can still emit.
                # Samples emitted during a conclusive drain remain accepted.
                self._source.stop()
            except Exception as exc:
                # Inconclusive stop/drain → raw capture completeness cannot be asserted.
                # Freeze acceptance so a stuck reader cannot keep mutating evidence.
                with self._lock:
                    self._accepting_samples = False
                source_error = f"EventSource.stop failed: {exc}"
                self._integrity_ok = False
                self._last_error = source_error
                self._source_faulted = True

        # Producer claims it can no longer emit — reject any late arrivals.
        with self._lock:
            self._accepting_samples = False

        self._queue.put(_STOP)
        thread = self._dispatch_thread
        if thread is not None:
            thread.join(timeout=10.0)
            if thread.is_alive():
                self._dispatcher_fatal = True
                self._integrity_ok = False
                self._complete = False
                self._last_error = self._last_error or "dispatcher did not exit after STOP"
                self._set_state(CaptureState.ERROR)
                self._dispatch_thread = None
                self._last_stop_duration_ms = (time.monotonic() - t0) * 1000.0
                return
            self._dispatch_thread = None

        if self._dispatcher_fatal:
            self._complete = False
            self._integrity_ok = False
            self._set_state(CaptureState.ERROR)
            self._last_stop_duration_ms = (time.monotonic() - t0) * 1000.0
            return

        if source_error:
            # SourceStopError / stop failure: stream may still emit — not complete.
            self._complete = False
            self._integrity_ok = False
            self._set_state(CaptureState.ERROR)
            self._last_stop_duration_ms = (time.monotonic() - t0) * 1000.0
            return

        self._complete = True
        if self._subscriber_errors:
            # Full raw stream drained; a derived subscriber faulted.
            self._integrity_ok = False
            if not self._last_error:
                self._last_error = self._subscriber_errors[0]
            self._set_state(CaptureState.ERROR)
            self._last_stop_duration_ms = (time.monotonic() - t0) * 1000.0
            return

        self._integrity_ok = True
        self._set_state(CaptureState.STOPPED)
        self._last_stop_duration_ms = (time.monotonic() - t0) * 1000.0

    def cancel(self) -> None:
        """End capture and discard net counts (ESC / abort).

        Clean cancellation → CANCELLED.
        If stop/drain left ERROR/incomplete, keep ERROR (not admissible) —
        do not mask it as CANCELLED.
        """
        if self._state is CaptureState.RUNNING:
            self.stop()
        if self._state is CaptureState.ERROR:
            self._reset_counts_only()
            return
        self._reset_counts_only()
        self._set_state(CaptureState.CANCELLED)

    def feed(self, sample: MovementSample) -> None:
        """Test/synthetic injection onto the same ordered queue."""
        if self._state is not CaptureState.RUNNING:
            raise RuntimeError("CaptureEngine.feed requires a running capture")
        self._enqueue_sample(sample)

    def wait_until_idle(self, timeout: float = 5.0) -> None:
        """Block until the dispatcher has consumed the current queue (tests)."""
        done = threading.Event()

        def _join() -> None:
            self._queue.join()
            done.set()

        waiter = threading.Thread(target=_join, name="mouse-dpi-capture-idle", daemon=True)
        waiter.start()
        if not done.wait(timeout):
            raise TimeoutError("CaptureEngine queue did not drain in time")

    def _enqueue_sample(self, sample: MovementSample) -> None:
        with self._lock:
            if not self._accepting_samples:
                self._stale_sample_count += 1
                return
            generation = self._generation
        self._queue.put((generation, sample))
        depth = self._queue.qsize()
        with self._lock:
            if depth > self._max_queue_depth:
                self._max_queue_depth = depth

    def _emit_status(self, message: str) -> None:
        if not self._on_status:
            return
        try:
            self._on_status(message)
        except Exception as exc:
            msg = f"status callback exception: {exc}"
            with self._lock:
                self._status_callback_errors.append(msg)
            # Presentation-only: never raise into the dispatcher / source reader.

    def _abort_failed_start(self, exc: BaseException) -> None:
        self._last_error = f"EventSource.start failed: {exc}"
        self._integrity_ok = False
        self._complete = False
        self._queue.put(_STOP)
        if self._dispatch_thread is not None:
            self._dispatch_thread.join(timeout=5.0)
            self._dispatch_thread = None
        if self._source is not None:
            try:
                self._source.stop()
            except Exception:
                self._source_faulted = True
        self._set_state(CaptureState.ERROR)

    def _reset_counts_only(self) -> None:
        with self._lock:
            self._net_x = 0
            self._net_y = 0
            self._devices.clear()
            self._per_device.clear()
            self._published = 0

    def _reset_live(self) -> None:
        self._reset_counts_only()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break

    def _note_subscriber_error(self, exc: BaseException) -> None:
        msg = f"subscriber exception: {exc}"
        with self._lock:
            self._subscriber_errors.append(msg)
            self._integrity_ok = False
            if not self._last_error:
                self._last_error = msg

    def _note_dispatcher_fatal(self, exc: BaseException) -> None:
        msg = f"dispatcher fatal: {exc}"
        with self._lock:
            self._dispatcher_fatal = True
            self._integrity_ok = False
            self._complete = False
            self._last_error = msg

    def _accumulate(self, sample: MovementSample) -> list[Listener]:
        with self._lock:
            dx = int(sample.dx)
            dy = int(sample.dy)
            self._net_x += dx
            self._net_y += dy
            device_key = str(sample.device_id) if sample.device_id else "unknown"
            if sample.device_id:
                self._devices.add(str(sample.device_id))
            stats = self._per_device.setdefault(
                device_key, {"dx": 0, "dy": 0, "event_count": 0}
            )
            stats["dx"] += dx
            stats["dy"] += dy
            stats["event_count"] += 1
            self._published += 1
            return [listener for listener in self._listeners if id(listener) not in self._quarantined]

    def _quarantine_listener(self, listener: Listener) -> None:
        with self._lock:
            self._quarantined.add(id(listener))

    def _dispatch_loop(self) -> None:
        try:
            while True:
                item = self._queue.get()
                try:
                    if item is _STOP:
                        return
                    generation, sample = item
                    with self._lock:
                        self._dispatcher_processed += 1
                        if generation != self._generation:
                            self._stale_sample_count += 1
                            continue
                    listeners = self._accumulate(sample)
                    for listener in listeners:
                        try:
                            listener(sample)
                        except Exception as exc:
                            self._note_subscriber_error(exc)
                            self._quarantine_listener(listener)
                            self._emit_status(
                                f"subscriber_error_quarantined:{type(exc).__name__}:{exc}"
                            )
                finally:
                    self._queue.task_done()
        except Exception as exc:
            self._note_dispatcher_fatal(exc)
            self._emit_status(f"dispatcher_fatal:{exc}")
            try:
                traceback.print_exc()
            except Exception:
                pass
