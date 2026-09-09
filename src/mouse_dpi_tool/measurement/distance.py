"""Physical distance conversion. Canonical storage unit: millimetres (mm)."""

from __future__ import annotations

from mouse_dpi_tool.measurement._coerce import safe_float

CANONICAL_DISTANCE_UNITS = ("mm", "cm", "inch")


def canonicalize_distance_unit(unit: str) -> str:
    """Map UI/legacy aliases to canonical codes: mm | cm | inch."""
    raw = str(unit or "mm").lower().strip()
    if raw in {"inch", "in", "inches", '"'}:
        return "inch"
    if raw in {"cm", "centimeter", "centimeters", "centimetre", "centimetres"}:
        return "cm"
    if raw in {"mm", "millimeter", "millimeters", "millimetre", "millimetres"}:
        return "mm"
    return "mm"


def _norm_unit(unit: str) -> str:
    return canonicalize_distance_unit(unit)


def distance_to_mm(value, unit: str) -> float:
    """Convert a UI/input distance to millimetres (legacy-compatible)."""
    unit = _norm_unit(unit)
    value = safe_float(value, 100.0)
    if unit == "inch":
        return value * 25.4
    if unit == "cm":
        return value * 10.0
    return value


def mm_to_distance_input(distance_mm: float, unit: str) -> float:
    """Derive a UI/input representation from canonical millimetres."""
    unit = _norm_unit(unit)
    value = float(distance_mm)
    if unit == "inch":
        return value / 25.4
    if unit == "cm":
        return value / 10.0
    return value
