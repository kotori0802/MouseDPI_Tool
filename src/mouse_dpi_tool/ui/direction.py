"""Canonical measurement direction helpers for the UI boundary.

Domain contract (authoritative evidence is per-trial):
- Trial stores BOTH axis (X|Y) and direction (X+|X-|Y+|Y-)
- measurement_context.direction is NOT per-trial truth (may be empty / non-authoritative)
- Canonical validation and signed-count matching live in measurement.direction_evidence

UI selects one of the four direction codes; axis is derived for Session APIs.
Localized labels never enter Session JSON.
"""

from __future__ import annotations

from mouse_dpi_tool.measurement.direction_evidence import (
    CANONICAL_DIRECTIONS,
    axis_for_direction,
    require_canonical_direction,
)

# Presentation-only orientation for the guided lane (not Session evidence).
LANE_ORIENTATIONS: dict[str, str] = {
    "X+": "horizontal_ltr",
    "X-": "horizontal_rtl",
    "Y+": "vertical_btt",
    "Y-": "vertical_ttb",
}


def canonicalize_direction(code: str | None) -> str:
    """Fail-closed wrapper around measurement.require_canonical_direction."""
    return require_canonical_direction(code)


def lane_orientation(direction: str | None) -> str:
    return LANE_ORIENTATIONS[canonicalize_direction(direction)]


__all__ = [
    "CANONICAL_DIRECTIONS",
    "LANE_ORIENTATIONS",
    "axis_for_direction",
    "canonicalize_direction",
    "lane_orientation",
]
