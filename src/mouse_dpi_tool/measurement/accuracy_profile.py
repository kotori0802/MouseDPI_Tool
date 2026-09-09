"""Operator Accuracy Acceptance Profiles (Effective CPI only).

Preserves Measurement Domain PASS/WARN/FAIL via cpi_error_pass_pct /
cpi_error_fail_pct. Does not alter CV, Ratio, Path Quality, or leakage limits.
"""

from __future__ import annotations

from typing import Mapping

# Canonical V1 operator profiles (machine evidence — never localize these codes).
FIELD_STRICT = "FIELD_STRICT"
FIELD_MEDIUM = "FIELD_MEDIUM"
FIELD_LENIENT = "FIELD_LENIENT"

# Legacy alias: same 3%/5% band as Strict (pre-M-2.2 default name).
FIELD_FORMAL = "FIELD_FORMAL"

DEFAULT_ACCURACY_PROFILE = FIELD_STRICT

OPERATOR_ACCURACY_PROFILES: tuple[str, ...] = (FIELD_STRICT, FIELD_MEDIUM, FIELD_LENIENT)

# pass_pct, fail_pct — WARN band is always fail - pass = 2.0 points.
_PROFILE_THRESHOLDS: dict[str, tuple[float, float]] = {
    FIELD_STRICT: (3.0, 5.0),
    FIELD_MEDIUM: (6.0, 8.0),
    FIELD_LENIENT: (9.0, 11.0),
}

_ALIASES: dict[str, str] = {
    FIELD_FORMAL: FIELD_STRICT,
}


def canonicalize_accuracy_profile(mode: str | None) -> str:
    """Map legacy / UI codes to a canonical operator profile when applicable."""
    raw = str(mode or DEFAULT_ACCURACY_PROFILE).strip().upper()
    raw = _ALIASES.get(raw, raw)
    if raw in _PROFILE_THRESHOLDS:
        return raw
    return raw


def is_operator_accuracy_profile(mode: str | None) -> bool:
    return canonicalize_accuracy_profile(mode) in _PROFILE_THRESHOLDS


def profile_cpi_error_limits(mode: str | None) -> tuple[float, float]:
    """Return (pass_pct, fail_pct) for a known operator profile.

    Raises KeyError for non-operator modes (e.g. ENGINEERING_*).
    """
    key = canonicalize_accuracy_profile(mode)
    if key not in _PROFILE_THRESHOLDS:
        raise KeyError(f"not an operator accuracy profile: {mode!r}")
    return _PROFILE_THRESHOLDS[key]


def settings_patch_for_accuracy_profile(mode: str) -> dict[str, float | str]:
    """Canonical Session settings patch for an operator Accuracy criterion."""
    key = canonicalize_accuracy_profile(mode)
    if key not in _PROFILE_THRESHOLDS:
        raise ValueError(
            f"unsupported accuracy profile: {mode!r}; "
            f"expected one of {list(OPERATOR_ACCURACY_PROFILES)}"
        )
    pass_pct, fail_pct = _PROFILE_THRESHOLDS[key]
    return {
        "tolerance_mode": key,
        "cpi_error_pass_pct": float(pass_pct),
        "cpi_error_fail_pct": float(fail_pct),
    }


def resolve_operator_profile_from_settings(settings: Mapping) -> str:
    """Best-effort profile code for UI selection (legacy FIELD_FORMAL → STRICT)."""
    mode = canonicalize_accuracy_profile(str(settings.get("tolerance_mode") or ""))
    if mode in _PROFILE_THRESHOLDS:
        return mode
    # Infer from thresholds if mode is unknown but matches a preset band.
    try:
        pass_pct = float(settings.get("cpi_error_pass_pct"))
        fail_pct = float(settings.get("cpi_error_fail_pct"))
    except (TypeError, ValueError):
        return DEFAULT_ACCURACY_PROFILE
    for code, (p, f) in _PROFILE_THRESHOLDS.items():
        if abs(pass_pct - p) < 1e-9 and abs(fail_pct - f) < 1e-9:
            return code
    return DEFAULT_ACCURACY_PROFILE
