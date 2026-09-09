"""O(1) active-motion timing aggregates from MovementSample timestamps.

Auxiliary engineering evidence only — never corrects CPI / Findings / Path Quality.

Timestamp source preference:
1. MovementSample.timestamp_s (Raw Input bridge ``time_perf`` = time.perf_counter())
2. If missing: capture-boundary monotonic clock (time.perf_counter) at on_sample

active_motion_duration_ms = (last_motion_ts − first_motion_ts) × 1000
for samples accepted during this Capture (dx/dy movement reports with a timestamp).

estimated_traversal_speed_mm_s = distance_mm / duration_s when duration > 0.
Never derived from event_count / published_count.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Any

from mouse_dpi_tool.contracts.movement import MovementSample

TIMING_OK = "OK"
TIMING_NOT_EVALUATED = "NOT_EVALUATED"


def _ms_delta(start: float | None, end: float | None) -> float | None:
    if start is None or end is None or end < start:
        return None
    return (end - start) * 1000.0


class StreamingMotionTimingAccumulator:
    """Lock-guarded O(1) timing aggregates — no sample buffer."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._motion_sample_count = 0
            self._samples_with_timestamp = 0
            self._first_motion_ts: float | None = None
            self._last_motion_ts: float | None = None
            self._capture_start_ts: float | None = None
            self._capture_stop_ts: float | None = None
            self._arm_requested_ts: float | None = None
            self._source_ready_ts: float | None = None
            self._stop_requested_ts: float | None = None
            self._source_stopped_ts: float | None = None
            self._used_boundary_clock = False
            self._used_sample_clock = False

    def mark_capture_start(self, *, timestamp_s: float | None = None) -> None:
        with self._lock:
            self._capture_start_ts = (
                float(timestamp_s) if timestamp_s is not None else time.perf_counter()
            )

    def mark_capture_stop(self, *, timestamp_s: float | None = None) -> None:
        with self._lock:
            self._capture_stop_ts = (
                float(timestamp_s) if timestamp_s is not None else time.perf_counter()
            )

    def mark_arm_requested(self, *, timestamp_s: float | None = None) -> None:
        with self._lock:
            self._arm_requested_ts = (
                float(timestamp_s) if timestamp_s is not None else time.perf_counter()
            )

    def mark_source_ready(self, *, timestamp_s: float | None = None) -> None:
        with self._lock:
            self._source_ready_ts = (
                float(timestamp_s) if timestamp_s is not None else time.perf_counter()
            )

    def mark_stop_requested(self, *, timestamp_s: float | None = None) -> None:
        with self._lock:
            self._stop_requested_ts = (
                float(timestamp_s) if timestamp_s is not None else time.perf_counter()
            )

    def mark_source_stopped(self, *, timestamp_s: float | None = None) -> None:
        """Optional: after EventSource.stop returns, before dispatcher drain completes."""
        with self._lock:
            self._source_stopped_ts = (
                float(timestamp_s) if timestamp_s is not None else time.perf_counter()
            )

    def on_sample(self, sample: MovementSample) -> None:
        # Accept any relative movement report (including 0,0 if emitted).
        if sample.timestamp_s is not None:
            ts = float(sample.timestamp_s)
            boundary = False
        else:
            ts = time.perf_counter()
            boundary = True
        with self._lock:
            self._motion_sample_count += 1
            self._samples_with_timestamp += 1
            if boundary:
                self._used_boundary_clock = True
            else:
                self._used_sample_clock = True
            if self._first_motion_ts is None:
                self._first_motion_ts = ts
            self._last_motion_ts = ts

    def snapshot(self, *, distance_mm: float | None = None) -> dict[str, Any]:
        with self._lock:
            count = self._motion_sample_count
            first = self._first_motion_ts
            last = self._last_motion_ts
            start = self._capture_start_ts
            stop = self._capture_stop_ts
            arm = self._arm_requested_ts
            ready = self._source_ready_ts
            stop_req = self._stop_requested_ts
            source_stopped = self._source_stopped_ts
            used_boundary = self._used_boundary_clock
            used_sample = self._used_sample_clock

        duration_ms: float | None = None
        speed: float | None = None
        status = TIMING_NOT_EVALUATED
        if first is not None and last is not None and last >= first:
            duration_ms = (last - first) * 1000.0
            if duration_ms > 0:
                status = TIMING_OK
                if distance_mm is not None:
                    try:
                        dist = float(distance_mm)
                    except (TypeError, ValueError):
                        dist = 0.0
                    if dist > 0:
                        speed = dist / (duration_ms / 1000.0)

        # Backward-compat: capture_start → first motion.
        first_delay_ms = _ms_delta(start, first)

        # Prefer source_ready → first; fall back to capture_start → first.
        ready_to_first_ms = _ms_delta(ready, first)
        if ready_to_first_ms is None:
            ready_to_first_ms = first_delay_ms

        arm_to_ready_ms = _ms_delta(arm, ready)
        stop_to_source_stopped_ms = _ms_delta(stop_req, source_stopped)
        # capture_stop is marked after engine.stop() returns (source + drain done).
        stop_to_drain_complete_ms = _ms_delta(stop_req, stop)

        post_idle_ms: float | None = None
        if stop is not None and last is not None and stop >= last:
            post_idle_ms = (stop - last) * 1000.0

        capture_elapsed_ms: float | None = None
        if start is not None and stop is not None and stop >= start:
            capture_elapsed_ms = (stop - start) * 1000.0

        active_event_rate_hz: float | None = None
        if duration_ms is not None and duration_ms > 0 and count > 0:
            active_event_rate_hz = count / (duration_ms / 1000.0)

        source = "unavailable"
        if used_sample and not used_boundary:
            source = "sample_timestamp_s"
        elif used_boundary and not used_sample:
            source = "capture_boundary_perf_counter"
        elif used_sample and used_boundary:
            source = "mixed_sample_and_boundary"

        def _round_ms(value: float | None) -> float | None:
            return round(value, 3) if value is not None else None

        out: dict[str, Any] = {
            "timing_status": status,
            "motion_sample_count": count,
            "first_motion_timestamp": first,
            "last_motion_timestamp": last,
            "active_motion_duration_ms": _round_ms(duration_ms),
            "estimated_traversal_speed_mm_s": (
                round(speed, 4) if speed is not None and math.isfinite(speed) else None
            ),
            "capture_elapsed_ms": _round_ms(capture_elapsed_ms),
            "first_motion_delay_ms": _round_ms(first_delay_ms),
            "post_motion_idle_ms": _round_ms(post_idle_ms),
            "active_event_rate_hz": (
                round(active_event_rate_hz, 3)
                if active_event_rate_hz is not None
                else None
            ),
            "timing_source": source,
            # Explicit non-velocity: never confuse with physical speed.
            "notes": (
                "Estimated traversal speed from active motion duration and configured "
                "distance only. Not true physical speed. event_count is not velocity."
            ),
        }

        if arm is not None:
            out["arm_requested_ts"] = arm
        if ready is not None:
            out["source_ready_ts"] = ready
        if stop_req is not None:
            out["stop_requested_ts"] = stop_req
        if arm_to_ready_ms is not None:
            out["arm_to_ready_ms"] = _round_ms(arm_to_ready_ms)
        if ready_to_first_ms is not None:
            out["ready_to_first_motion_ms"] = _round_ms(ready_to_first_ms)
        if stop_to_source_stopped_ms is not None:
            out["stop_to_source_stopped_ms"] = _round_ms(stop_to_source_stopped_ms)
        if stop_to_drain_complete_ms is not None:
            out["stop_to_drain_complete_ms"] = _round_ms(stop_to_drain_complete_ms)

        return out


def attach_motion_timing_to_trial(
    trial: dict[str, Any],
    snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    """Attach optional motion_timing object; does not alter CPI fields."""
    if not snapshot:
        return trial
    out = dict(trial)
    out["motion_timing"] = dict(snapshot)
    return out
