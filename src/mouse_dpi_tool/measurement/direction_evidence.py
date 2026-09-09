"""Direction evidence vs signed Raw Input counts (separate from CPI magnitude).

Canonical trial fields remain:
  axis: X | Y
  direction: X+ | X- | Y+ | Y-

CPI magnitude still uses absolute counts inside compute_trial(); this module only
checks that the selected canonical direction matches the signed primary axis
movement from Windows relative Raw Input.

Windows relative Y is positive downward. Measurement naming:
  Y+ = bottom → top  → counts_y < 0
  Y- = top → bottom  → counts_y > 0
  X+ = left → right  → counts_x > 0
  X- = right → left  → counts_x < 0
"""

from __future__ import annotations

from dataclasses import dataclass

CANONICAL_DIRECTIONS: tuple[str, ...] = ("X+", "X-", "Y+", "Y-")

# Expected sign of the primary Raw Input axis count for each direction.
# (+1 means primary count must be > 0; -1 means primary count must be < 0.)
_EXPECTED_PRIMARY_SIGN: dict[str, int] = {
    "X+": 1,
    "X-": -1,
    "Y+": -1,  # bottom → top against Windows +Y-down
    "Y-": 1,
}


class DirectionEvidenceError(ValueError):
    """Invalid direction string or other direction-evidence contract error."""


class DirectionMismatchError(ValueError):
    """Selected direction does not match signed primary Raw Input movement."""

    code = "DIRECTION_MISMATCH"

    def __init__(self, message: str, *, result: DirectionMatchResult | None = None) -> None:
        super().__init__(message)
        self.result = result


@dataclass(frozen=True)
class DirectionMatchResult:
    direction: str
    axis: str
    expected_raw_sign: int
    primary_signed_count: int
    matches: bool
    inferred_direction: str | None
    reason: str


def require_canonical_direction(code: str | None) -> str:
    """Fail-closed: only exact V1 codes X+/X-/Y+/Y- are accepted."""
    if code is None or str(code).strip() == "":
        raise DirectionEvidenceError("direction is required")
    raw = str(code).strip().upper().replace(" ", "")
    if raw not in CANONICAL_DIRECTIONS:
        raise DirectionEvidenceError(f"unsupported direction: {code!r}")
    return raw


def axis_for_direction(direction: str | None) -> str:
    code = require_canonical_direction(direction)
    return "Y" if code.startswith("Y") else "X"


def expected_raw_sign(direction: str | None) -> int:
    code = require_canonical_direction(direction)
    return _EXPECTED_PRIMARY_SIGN[code]


def primary_signed_count(direction: str | None, counts_x: int, counts_y: int) -> int:
    code = require_canonical_direction(direction)
    return int(counts_y) if code.startswith("Y") else int(counts_x)


def infer_direction_from_primary(*, axis: str, primary_signed: int) -> str | None:
    """Infer canonical direction from signed primary count on a known axis."""
    ax = str(axis or "").upper()
    if primary_signed == 0:
        return None
    if ax == "X":
        return "X+" if primary_signed > 0 else "X-"
    if ax == "Y":
        # Windows +Y down: negative dy ⇒ Y+ (bottom→top)
        return "Y+" if primary_signed < 0 else "Y-"
    return None


def evaluate_direction_match(
    direction: str | None,
    counts_x: int,
    counts_y: int,
) -> DirectionMatchResult:
    code = require_canonical_direction(direction)
    axis = axis_for_direction(code)
    expected = expected_raw_sign(code)
    primary = primary_signed_count(code, counts_x, counts_y)
    inferred = infer_direction_from_primary(axis=axis, primary_signed=primary)
    if primary == 0:
        return DirectionMatchResult(
            direction=code,
            axis=axis,
            expected_raw_sign=expected,
            primary_signed_count=primary,
            matches=False,
            inferred_direction=None,
            reason="ZERO_PRIMARY_MOVEMENT",
        )
    matches = (primary > 0 and expected > 0) or (primary < 0 and expected < 0)
    return DirectionMatchResult(
        direction=code,
        axis=axis,
        expected_raw_sign=expected,
        primary_signed_count=primary,
        matches=matches,
        inferred_direction=inferred,
        reason="OK" if matches else "DIRECTION_MISMATCH",
    )


def assert_direction_matches_counts(
    direction: str | None,
    counts_x: int,
    counts_y: int,
) -> DirectionMatchResult:
    """Raise DirectionMismatchError unless signed primary movement matches direction."""
    result = evaluate_direction_match(direction, counts_x, counts_y)
    if result.matches:
        return result
    raise DirectionMismatchError(
        f"{result.reason}: selected {result.direction} but primary "
        f"count on {result.axis} is {result.primary_signed_count} "
        f"(expected sign {result.expected_raw_sign:+d}"
        f"{'' if result.inferred_direction is None else f'; observed≈{result.inferred_direction}'})",
        result=result,
    )


__all__ = [
    "CANONICAL_DIRECTIONS",
    "DirectionEvidenceError",
    "DirectionMatchResult",
    "DirectionMismatchError",
    "assert_direction_matches_counts",
    "axis_for_direction",
    "evaluate_direction_match",
    "expected_raw_sign",
    "infer_direction_from_primary",
    "primary_signed_count",
    "require_canonical_direction",
]
