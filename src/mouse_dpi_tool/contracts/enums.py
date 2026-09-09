"""Shared enums and status vocabulary for Mouse DPI Tool."""

from __future__ import annotations

from enum import Enum


class FindingStatus(str, Enum):
    """Status for a single findings dimension.

    PASS/WARN/FAIL: dimension was measured and evaluated against thresholds.
    NOT_TESTED: this measurement dimension was not executed in this session.
    NOT_EVALUATED: related data exists, but this version did not run interpretation.
    """

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    NOT_TESTED = "NOT_TESTED"
    NOT_EVALUATED = "NOT_EVALUATED"


class ManualObservationStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"
    NOT_TESTED = "NOT_TESTED"


class MovementMode(str, Enum):
    VECTOR_MAGNITUDE = "Vector Magnitude"
    AXIS_PROJECTION = "Axis Projection"


class DistanceUnit(str, Enum):
    MM = "mm"
    CM = "cm"
    INCH = "inch"


# Canonical storage unit for physical distance in Session JSON and measurement domain.
CANONICAL_DISTANCE_UNIT = DistanceUnit.MM

FINDING_DIMENSIONS = (
    "accuracy",
    "repeatability",
    "ratio",
    "path_quality",
    "manual_observations",
    "linearity",
    "scaling_evidence",
    "native_capability",
)

# V1 defaults for dimensions that are reserved but not interpreted yet.
V1_RESERVED_FINDINGS = {
    "linearity": FindingStatus.NOT_EVALUATED,
    "scaling_evidence": FindingStatus.NOT_EVALUATED,
    "native_capability": FindingStatus.NOT_EVALUATED,
}
