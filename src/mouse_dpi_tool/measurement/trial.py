"""Per-trial Effective CPI calculation (legacy compute_trial math parity).

Canonical field: configured_dpi (legacy alias: target_dpi).
Trial.status here reflects CPI error and (in Axis Projection) axis leakage only.
Path Quality must NOT be merged into this status.

V1 formal geometries:
- Axis Projection — Directional Axis (|dx| / |dy|)
- Vector Magnitude — Fixture Vector (√(dx²+dy²)); first-class lab fixture mode, not legacy-only
"""

from __future__ import annotations

import math

from mouse_dpi_tool.measurement.legacy_compat import resolve_configured_dpi
from mouse_dpi_tool.measurement.group import (
    FIXTURE_VECTOR_AXIS,
    FIXTURE_VECTOR_DIRECTION,
    is_fixture_vector_mode,
    trial_group_id,
)
from mouse_dpi_tool.measurement.settings import normalize_settings, status_from_limits
from mouse_dpi_tool.measurement.timeutil import now_iso


def compute_trial(
    trial_id: int,
    distance_mm: float,
    axis: str,
    direction: str,
    counts_x: int,
    counts_y: int,
    configured_dpi: int | None = None,
    target_dpi: int | None = None,
    source: str = "raw_input",
    note: str = "",
    movement_mode: str = "Vector Magnitude",
    distance_input: float | None = None,
    distance_unit: str = "mm",
    tolerance_policy: dict | None = None,
) -> dict:
    dpi = resolve_configured_dpi(configured_dpi=configured_dpi, target_dpi=target_dpi)
    distance_input = distance_mm if distance_input is None else distance_input
    distance_unit = str(distance_unit or "mm")
    inch = distance_mm / 25.4
    movement_mode = str(movement_mode or "Vector Magnitude")
    if is_fixture_vector_mode(movement_mode):
        axis = FIXTURE_VECTOR_AXIS
        direction = FIXTURE_VECTOR_DIRECTION
    else:
        axis = str(axis or "").upper()
        direction = str(direction or "")

    abs_x = abs(int(counts_x))
    abs_y = abs(int(counts_y))

    if is_fixture_vector_mode(movement_mode):
        primary_counts = int(round(math.sqrt(abs_x * abs_x + abs_y * abs_y)))
        secondary_counts = min(abs_x, abs_y)
    else:
        if axis == "X":
            primary_counts = abs_x
            secondary_counts = abs_y
        else:
            primary_counts = abs_y
            secondary_counts = abs_x

    measured_cpi = primary_counts / inch if inch else 0.0
    error_pct = (measured_cpi - dpi) / dpi * 100.0 if dpi else 0.0
    axis_leakage_pct = secondary_counts / max(1, primary_counts) * 100.0

    policy = normalize_settings(tolerance_policy or {})
    tags: list[str] = []
    if primary_counts <= 0:
        tags.append("NO_PRIMARY_COUNTS")

    if is_fixture_vector_mode(movement_mode):
        leak_status = "PASS"
    else:
        if axis_leakage_pct > policy["axis_leakage_fail_pct"]:
            tags.append("AXIS_LEAKAGE_FAIL")
        elif axis_leakage_pct > policy["axis_leakage_pass_pct"]:
            tags.append("AXIS_LEAKAGE_WARN")
        leak_status = status_from_limits(
            axis_leakage_pct,
            policy["axis_leakage_pass_pct"],
            policy["axis_leakage_fail_pct"],
        )

    cpi_status = status_from_limits(
        abs(error_pct),
        policy["cpi_error_pass_pct"],
        policy["cpi_error_fail_pct"],
    )

    status_rank = {"PASS": 0, "WARN": 1, "FAIL": 2}
    status = max([cpi_status, leak_status], key=lambda s: status_rank[s])

    if str(policy.get("tolerance_mode") or "").upper().startswith("ENGINEERING"):
        tags.append("NON_STANDARD_TOLERANCE")

    trial = {
        "trial_id": int(trial_id),
        "created_at": now_iso(),
        "configured_dpi": dpi,
        "distance_input": float(distance_input),
        "distance_unit": distance_unit,
        "distance_mm": float(distance_mm),
        "axis": axis,
        "direction": direction,
        "movement_mode": movement_mode,
        "counts_x": int(counts_x),
        "counts_y": int(counts_y),
        "vector_counts": int(round(math.sqrt(abs_x * abs_x + abs_y * abs_y))),
        "primary_counts": int(primary_counts),
        "secondary_counts": int(secondary_counts),
        "measured_cpi": round(measured_cpi, 4),
        "error_pct": round(error_pct, 4),
        "axis_leakage_pct": round(axis_leakage_pct, 4),
        "status": status,
        "cpi_error_pass_pct": policy["cpi_error_pass_pct"],
        "cpi_error_fail_pct": policy["cpi_error_fail_pct"],
        "tolerance_mode": str(policy.get("tolerance_mode") or "FIELD_FORMAL"),
        "run_validity": "REVIEW"
        if str(policy.get("tolerance_mode") or "").upper().startswith("ENGINEERING")
        else "VALID",
        "issue_tags": ";".join(tags),
        "source": source,
        "note": note,
        "accepted": True,
        "deleted": False,
        "rejected": False,
        "group_id": trial_group_id(
            {
                "configured_dpi": dpi,
                "axis": axis,
                "direction": direction,
                "distance_mm": float(distance_mm),
                "movement_mode": movement_mode,
            }
        ),
        "path_total_counts": None,
        "straightness_pct": None,
    }
    return trial


# Fields recomputed from primitive counts + policy (never trusted from export alone).
_QUANTITATIVE_RECOMPUTE_KEYS = (
    "configured_dpi",
    "distance_mm",
    "distance_input",
    "distance_unit",
    "axis",
    "direction",
    "movement_mode",
    "counts_x",
    "counts_y",
    "vector_counts",
    "primary_counts",
    "secondary_counts",
    "measured_cpi",
    "error_pct",
    "axis_leakage_pct",
    "status",
    "cpi_error_pass_pct",
    "cpi_error_fail_pct",
    "tolerance_mode",
    "run_validity",
    "issue_tags",
    "group_id",
)


def recompute_trial_from_evidence(trial: dict, settings: dict | None = None) -> dict:
    """Recompute quantitative Trial fields via ``compute_trial()``.

    Primitive source-of-truth: configured_dpi, counts_x/y, distance, axis,
    direction, movement_mode, and the current normalized measurement policy.

    Preserves identity, lifecycle, capture provenance, Path Quality, notes/source,
    and timestamps. Does not duplicate CPI formulas.
    """
    policy = normalize_settings(settings or {})
    distance_mm = float(trial.get("distance_mm", policy["distance_mm"]))
    recomputed = compute_trial(
        trial_id=int(trial["trial_id"]),
        distance_mm=distance_mm,
        axis=str(trial.get("axis") or "X"),
        direction=str(trial.get("direction") or "X+"),
        counts_x=int(trial.get("counts_x", 0)),
        counts_y=int(trial.get("counts_y", 0)),
        configured_dpi=int(trial["configured_dpi"]),
        source=str(trial.get("source") or "raw_input"),
        note=str(trial.get("note") or ""),
        movement_mode=str(trial.get("movement_mode") or policy.get("movement_mode") or "Vector Magnitude"),
        distance_input=float(trial.get("distance_input", distance_mm)),
        distance_unit=str(trial.get("distance_unit") or policy.get("distance_unit") or "mm"),
        tolerance_policy=policy,
    )
    out = dict(trial)
    for key in _QUANTITATIVE_RECOMPUTE_KEYS:
        if key in recomputed:
            out[key] = recomputed[key]
    out["measurement_status"] = recomputed["status"]
    # Preserve original created_at / lifecycle / capture / Path Quality from ``trial``.
    if "created_at" in trial:
        out["created_at"] = trial["created_at"]
    for key in (
        "accepted",
        "rejected",
        "deleted",
        "rejection_reason",
        "deletion_reason",
        "capture_evidence",
        "path_total_counts",
        "straightness_pct",
        "path_quality_status",
        "path_quality_issue_codes",
        "fixture_noise_floor_counts",
        "fixture_noise_floor_policy",
        "issue_codes",
        "session_trial_id",
        "report_trial_no",
    ):
        if key in trial:
            out[key] = trial[key]
    return out
