"""Canonical measurement_context.method values (Session schema enum)."""

from __future__ import annotations

from typing import Final

# Must match mouse_dpi_tool_session_v1.json measurement_context.method.enum
CANONICAL_MEASUREMENT_METHODS: Final[tuple[str, ...]] = (
    "hand_drag",
    "click_click",
    "fixture",
    "synthetic",
    "unknown",
)

CANONICAL_MEASUREMENT_METHOD_SET: Final[frozenset[str]] = frozenset(
    CANONICAL_MEASUREMENT_METHODS
)


class MeasurementMethodError(ValueError):
    """Raised when a non-canonical method would enter Session storage."""


def is_canonical_measurement_method(value: object) -> bool:
    return isinstance(value, str) and value in CANONICAL_MEASUREMENT_METHOD_SET


def require_canonical_measurement_method(value: object) -> str:
    if is_canonical_measurement_method(value):
        return str(value)
    raise MeasurementMethodError(
        f"measurement_context.method must be one of "
        f"{list(CANONICAL_MEASUREMENT_METHODS)}; got {value!r}"
    )
