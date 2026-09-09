"""Streaming Path Quality evidence (complete capture, not a UI point buffer).

Stores running aggregates, not an unbounded sample list. Every MovementSample
updates the aggregates; the 6000-point visualization cap is irrelevant here.

on_sample/snapshot are lock-guarded so the Capture dispatcher and UI timer can
run concurrently without torn aggregate reads. Math is unchanged.
"""

from __future__ import annotations

import threading
from typing import Any

from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.path_quality.metrics import (
    classify_path_quality,
    clamp_noise_floor,
    step_hypot,
    straightness_pct,
    vector_counts_from_net,
)


class StreamingPathQualityAccumulator:
    def __init__(
        self,
        *,
        fixture_noise_floor_counts: int = 7,
        straightness_fail_pct: float = 85.0,
    ) -> None:
        self.fixture_noise_floor_counts = clamp_noise_floor(fixture_noise_floor_counts)
        self.straightness_fail_pct = float(straightness_fail_pct)
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._sample_count = 0
            self._included_step_count = 0
            self._ignored_below_floor_count = 0
            self._net_x = 0
            self._net_y = 0
            self._path_total = 0.0

    def on_sample(self, sample: MovementSample) -> None:
        dx = int(sample.dx)
        dy = int(sample.dy)
        step = step_hypot(dx, dy)
        with self._lock:
            self._sample_count += 1
            self._net_x += dx
            self._net_y += dy
            if step > self.fixture_noise_floor_counts:
                self._path_total += step
                self._included_step_count += 1
            else:
                self._ignored_below_floor_count += 1

    @property
    def sample_count(self) -> int:
        with self._lock:
            return self._sample_count

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            net_x = self._net_x
            net_y = self._net_y
            path_total_raw = self._path_total
            sample_count = self._sample_count
            included = self._included_step_count
            ignored = self._ignored_below_floor_count
        vector = vector_counts_from_net(net_x, net_y)
        path_total = round(path_total_raw, 4)
        straightness = round(straightness_pct(vector, path_total_raw), 4)
        status, codes = classify_path_quality(
            vector_counts=vector,
            path_total_counts=path_total_raw,
            straightness=straightness_pct(vector, path_total_raw),
            noise_floor=float(self.fixture_noise_floor_counts),
            straightness_fail_pct=self.straightness_fail_pct,
            sample_count=sample_count,
        )
        return {
            "path_total_counts": path_total if sample_count else None,
            "straightness_pct": straightness if sample_count else None,
            "vector_counts": vector,
            "net_counts_x": int(net_x),
            "net_counts_y": int(net_y),
            "status": status,
            "issue_codes": codes,
            "sample_count": sample_count,
            "included_step_count": included,
            "ignored_below_floor_count": ignored,
            "fixture_noise_floor_counts": self.fixture_noise_floor_counts,
            "straightness_fail_pct": self.straightness_fail_pct,
            "owner": "path_quality",
            "evidence": "streaming_aggregates",
        }


def attach_to_trial(trial: dict, snapshot: dict | None = None, accumulator: StreamingPathQualityAccumulator | None = None) -> dict:
    """Copy Path Quality fields onto a trial without changing measurement status."""
    snap = snapshot if snapshot is not None else accumulator.snapshot()  # type: ignore[union-attr]
    out = dict(trial)
    measurement_status = out.get("status")
    out["path_total_counts"] = snap.get("path_total_counts")
    out["straightness_pct"] = snap.get("straightness_pct")
    out["path_quality_status"] = snap.get("status")
    out["path_quality_issue_codes"] = list(snap.get("issue_codes") or [])
    out["fixture_noise_floor_counts"] = snap.get("fixture_noise_floor_counts")
    out["fixture_noise_floor_policy"] = "not_subtracted_from_dpi_counts"
    out["status"] = measurement_status
    return out
