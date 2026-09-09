"""Controller-owned Capture presentation snapshot (not Session evidence).

Frozen after a valid Stop / Admit so Gauge, Path Trace, and TrialPoster remain
stable after engine release, focus changes, and refresh(). Cleared on next Start
(live viz reset) or Discard/Cancel as appropriate.
"""

from __future__ import annotations

from typing import Any, TypedDict


class LastCapturePresentationSnapshot(TypedDict):
    phase: str  # "pending" | "admitted"
    trial_id: int | None
    measured_cpi: float | None
    configured_dpi: int | None
    error_pct: float | None
    status: str | None
    counts_x: int | None
    counts_y: int | None
    primary_counts: int | None
    vector_counts: int | None
    vector_cpi: float | None
    distance_mm: float | None
    movement_mode: str | None
    direction: str | None
    axis_leakage_pct: float | None
    path_quality_status: str | None
    integrity_ok: bool
    net_counts_x: int
    net_counts_y: int
    path_points: tuple[tuple[float, float], ...]


def poster_fields(snap: LastCapturePresentationSnapshot) -> dict[str, Any]:
    """Subset used by TrialPoster (excludes raw path_points for layout)."""
    return {
        "phase": snap["phase"],
        "trial_id": snap["trial_id"],
        "measured_cpi": snap["measured_cpi"],
        "configured_dpi": snap["configured_dpi"],
        "error_pct": snap["error_pct"],
        "counts_x": snap["counts_x"],
        "counts_y": snap["counts_y"],
        "primary_counts": snap["primary_counts"],
        "vector_counts": snap["vector_counts"],
        "vector_cpi": snap["vector_cpi"],
        "distance_mm": snap["distance_mm"],
        "movement_mode": snap["movement_mode"],
        "direction": snap["direction"],
        "status": snap["status"],
        "axis_leakage_pct": snap["axis_leakage_pct"],
        "path_quality_status": snap["path_quality_status"],
        "integrity_ok": snap["integrity_ok"],
    }
