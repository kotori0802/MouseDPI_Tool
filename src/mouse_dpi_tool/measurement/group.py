"""Group summary statistics (legacy summarize_group / build_group_summaries math parity).

Canonical field: configured_dpi (not target_dpi).

Fixture Vector (Vector Magnitude): axis/direction are non-authoritative sentinels
``N/A`` — grouping buckets by configured DPI + distance + movement_mode only.
"""

from __future__ import annotations

import statistics

from mouse_dpi_tool.measurement._coerce import safe_float
from mouse_dpi_tool.measurement.legacy_compat import trial_configured_dpi
from mouse_dpi_tool.measurement.settings import normalize_settings, status_from_limits

# Non-authoritative sentinel for Fixture Vector trials (not a measurement claim).
FIXTURE_VECTOR_AXIS = "N/A"
FIXTURE_VECTOR_DIRECTION = "N/A"


def is_fixture_vector_mode(movement_mode: str | None) -> bool:
    return str(movement_mode or "") == "Vector Magnitude"


def normalize_trial_geometry_fields(trial: dict) -> dict:
    """Ensure Fixture Vector trials do not claim fake X+/Y+ directional evidence."""
    if is_fixture_vector_mode(trial.get("movement_mode")):
        trial["axis"] = FIXTURE_VECTOR_AXIS
        trial["direction"] = FIXTURE_VECTOR_DIRECTION
    return trial


def trial_group_key(trial: dict):
    mode = str(trial.get("movement_mode", "Vector Magnitude"))
    dpi = trial_configured_dpi(trial)
    distance = float(trial["distance_mm"])
    if is_fixture_vector_mode(mode):
        return (dpi, FIXTURE_VECTOR_AXIS, FIXTURE_VECTOR_DIRECTION, distance, mode)
    return (
        dpi,
        str(trial.get("axis") or ""),
        str(trial.get("direction") or ""),
        distance,
        mode,
    )


def mean(values):
    return statistics.mean(values) if values else None


def pstdev(values):
    return statistics.pstdev(values) if len(values) > 1 else 0.0


def cv_pct(values):
    avg = mean(values)
    if avg in (None, 0):
        return None
    return pstdev(values) / avg * 100.0


def trial_group_id(trial: dict) -> str:
    dpi, axis, direction, distance, movement_mode = trial_group_key(trial)
    return f"{dpi}_{axis}_{direction}_{distance:g}mm_{movement_mode.replace(' ', '_')}"


def summarize_group(trials: list[dict], settings: dict) -> dict | None:
    policy = normalize_settings(settings)
    active = [t for t in trials if t.get("accepted") and not t.get("deleted") and not t.get("rejected")]
    if not active:
        return None

    first = active[0]
    cpis = [safe_float(t.get("measured_cpi")) for t in active]
    errors = [safe_float(t.get("error_pct")) for t in active]
    leakages = [safe_float(t.get("axis_leakage_pct")) for t in active]

    avg_cpi = mean(cpis)
    cv = cv_pct(cpis)
    avg_error = mean(errors)
    max_abs_error = max(abs(v) for v in errors) if errors else 0.0
    avg_leakage = mean(leakages)
    max_leakage = max(leakages) if leakages else 0.0

    status_rank = {"PASS": 0, "WARN": 1, "FAIL": 2}
    status = "PASS"
    tags: list[str] = []

    if len(active) < policy["min_valid_trials_per_group"]:
        status = "WARN"
        tags.append("INSUFFICIENT_TRIALS")

    movement_mode = first.get("movement_mode", "Vector Magnitude")
    error_status = status_from_limits(max_abs_error, policy["cpi_error_pass_pct"], policy["cpi_error_fail_pct"])
    cv_status = status_from_limits(cv or 0.0, policy["cpi_cv_pass_pct"], policy["cpi_cv_fail_pct"])

    if movement_mode == "Vector Magnitude":
        leakage_status = "PASS"
    else:
        leakage_status = status_from_limits(
            max_leakage, policy["axis_leakage_pass_pct"], policy["axis_leakage_fail_pct"]
        )

    for candidate, tag in [
        (error_status, "CPI_ERROR"),
        (cv_status, "CPI_CV"),
        (leakage_status, "AXIS_LEAKAGE"),
    ]:
        if status_rank[candidate] > status_rank[status]:
            status = candidate
        if candidate != "PASS":
            tags.append(f"{tag}_{candidate}")

    if str(policy.get("tolerance_mode") or "").upper().startswith("ENGINEERING"):
        tags.append("NON_STANDARD_TOLERANCE")

    dpi = trial_configured_dpi(first)
    axis = first.get("axis")
    direction = first.get("direction")
    if is_fixture_vector_mode(movement_mode):
        axis = FIXTURE_VECTOR_AXIS
        direction = FIXTURE_VECTOR_DIRECTION
    return {
        "group_id": trial_group_id(first),
        "configured_dpi": dpi,
        "axis": axis,
        "direction": direction,
        "distance_mm": first["distance_mm"],
        "movement_mode": first.get("movement_mode", "Vector Magnitude"),
        "valid_trials": len(active),
        "avg_measured_cpi": round(avg_cpi, 4) if avg_cpi is not None else None,
        "min_measured_cpi": round(min(cpis), 4) if cpis else None,
        "max_measured_cpi": round(max(cpis), 4) if cpis else None,
        "cpi_cv_pct": round(cv, 4) if cv is not None else None,
        "avg_error_pct": round(avg_error, 4) if avg_error is not None else None,
        "max_abs_error_pct": round(max_abs_error, 4),
        "avg_axis_leakage_pct": round(avg_leakage, 4) if avg_leakage is not None else None,
        "max_axis_leakage_pct": round(max_leakage, 4),
        "status": status,
        "cpi_error_pass_pct": policy["cpi_error_pass_pct"],
        "cpi_error_fail_pct": policy["cpi_error_fail_pct"],
        "tolerance_mode": str(policy.get("tolerance_mode") or "FIELD_FORMAL"),
        "run_validity": "REVIEW"
        if str(policy.get("tolerance_mode") or "").upper().startswith("ENGINEERING")
        else "VALID",
        "issue_tags": ";".join(tags),
    }


def build_group_summaries(trials: list[dict], settings: dict) -> list[dict]:
    groups: dict = {}
    for t in trials:
        if t.get("deleted") or t.get("rejected"):
            continue
        groups.setdefault(trial_group_key(t), []).append(t)

    summaries = []
    for key in sorted(groups.keys()):
        s = summarize_group(groups[key], settings)
        if s:
            summaries.append(s)
    return summaries
