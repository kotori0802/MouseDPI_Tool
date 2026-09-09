"""Measurement settings / tolerance policy.

Distance normalization is an intentional V1 divergence from legacy:

- explicit distance_input + distance_unit → convert to canonical distance_mm
- else explicit distance_mm → use that value as canonical mm; derive distance_input
- else defaults
"""

from __future__ import annotations

from mouse_dpi_tool.measurement._coerce import safe_float, safe_int
from mouse_dpi_tool.measurement.accuracy_profile import DEFAULT_ACCURACY_PROFILE
from mouse_dpi_tool.measurement.distance import canonicalize_distance_unit, distance_to_mm, mm_to_distance_input

DEFAULT_SETTINGS = {
    "profile": "Engineering",
    "capture_mode": "Windows Raw Input",
    "distance_mm": 100.0,
    "distance_input": 100.0,
    "distance_unit": "mm",
    "dpi_steps": [400, 800, 1600, 3200],
    "trials_per_group": 5,
    "axis": "X",
    "directions": ["X+", "X-"],
    "movement_mode": "Vector Magnitude",
    "min_valid_trials_per_group": 3,
    "cpi_error_pass_pct": 3.0,
    "cpi_error_fail_pct": 5.0,
    "straightness_fail_pct": 85.0,
    "fixture_noise_floor_counts": 7,
    "cpi_cv_pass_pct": 1.0,
    "cpi_cv_fail_pct": 3.0,
    "axis_leakage_pass_pct": 2.0,
    "axis_leakage_fail_pct": 5.0,
    "ratio_error_pass_pct": 2.0,
    "ratio_error_fail_pct": 5.0,
    "tolerance_mode": DEFAULT_ACCURACY_PROFILE,
}


def _normalize_distance(raw: dict, merged: dict) -> tuple[float, float, str]:
    has_input = "distance_input" in raw
    has_mm = "distance_mm" in raw
    unit = canonicalize_distance_unit(str(raw.get("distance_unit", merged.get("distance_unit", "mm"))))

    if has_input:
        distance_input = safe_float(raw.get("distance_input"), DEFAULT_SETTINGS["distance_input"])
        distance_mm = max(1.0, distance_to_mm(distance_input, unit))
        return distance_input, distance_mm, unit

    if has_mm:
        distance_mm = max(1.0, safe_float(raw.get("distance_mm"), DEFAULT_SETTINGS["distance_mm"]))
        distance_input = mm_to_distance_input(distance_mm, unit)
        return distance_input, distance_mm, unit

    unit = str(DEFAULT_SETTINGS["distance_unit"])
    distance_input = float(DEFAULT_SETTINGS["distance_input"])
    distance_mm = max(1.0, distance_to_mm(distance_input, unit))
    return distance_input, distance_mm, canonicalize_distance_unit(unit)


def normalize_settings(settings: dict | None) -> dict:
    raw = dict(settings or {})
    merged = dict(DEFAULT_SETTINGS)
    merged.update(raw)

    distance_input, distance_mm, unit = _normalize_distance(raw, merged)
    merged["distance_unit"] = unit
    merged["distance_input"] = distance_input
    merged["distance_mm"] = distance_mm
    merged["trials_per_group"] = max(1, safe_int(merged.get("trials_per_group"), 5))
    merged["min_valid_trials_per_group"] = max(1, safe_int(merged.get("min_valid_trials_per_group"), 3))
    merged["movement_mode"] = str(merged.get("movement_mode", "Vector Magnitude"))
    # Preserve explicit legacy FIELD_FORMAL; new empty defaults use FIELD_STRICT.
    merged["tolerance_mode"] = str(merged.get("tolerance_mode") or DEFAULT_ACCURACY_PROFILE).upper()
    merged["cpi_error_pass_pct"] = max(
        0.1,
        min(100.0, safe_float(merged.get("cpi_error_pass_pct"), DEFAULT_SETTINGS["cpi_error_pass_pct"])),
    )
    merged["cpi_error_fail_pct"] = max(
        safe_float(merged.get("cpi_error_fail_pct"), DEFAULT_SETTINGS["cpi_error_fail_pct"]),
        merged["cpi_error_pass_pct"] + 2.0,
    )
    merged["straightness_fail_pct"] = max(
        1.0,
        min(100.0, safe_float(merged.get("straightness_fail_pct"), DEFAULT_SETTINGS["straightness_fail_pct"])),
    )
    merged["fixture_noise_floor_counts"] = max(
        0,
        min(25, safe_int(merged.get("fixture_noise_floor_counts"), DEFAULT_SETTINGS["fixture_noise_floor_counts"])),
    )
    return merged


def status_from_limits(value_abs, pass_limit, fail_limit) -> str:
    if value_abs <= pass_limit:
        return "PASS"
    if value_abs <= fail_limit:
        return "WARN"
    return "FAIL"
