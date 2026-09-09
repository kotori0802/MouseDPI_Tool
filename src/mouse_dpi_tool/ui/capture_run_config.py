"""Frozen measurement configuration for one Capture start→admit lifecycle.

Presentation preferences (theme/locale) are never stored here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class CaptureRunConfig:
    """Snapshot of measurement-affecting settings taken at Capture Start."""

    configured_dpi: int
    direction: str
    axis: str
    distance_mm: float
    distance_input: float
    distance_unit: str
    movement_mode: str
    # Normalized policy fields used by Path Quality / measurement tolerances.
    fixture_noise_floor_counts: int
    straightness_fail_pct: float
    cpi_error_pass_pct: float
    cpi_error_fail_pct: float
    axis_leakage_pass_pct: float
    axis_leakage_fail_pct: float
    tolerance_mode: str

    def as_settings_patch(self) -> dict[str, Any]:
        return {
            "distance_mm": float(self.distance_mm),
            "distance_input": float(self.distance_input),
            "distance_unit": str(self.distance_unit),
            "movement_mode": str(self.movement_mode),
            "fixture_noise_floor_counts": int(self.fixture_noise_floor_counts),
            "straightness_fail_pct": float(self.straightness_fail_pct),
            "cpi_error_pass_pct": float(self.cpi_error_pass_pct),
            "cpi_error_fail_pct": float(self.cpi_error_fail_pct),
            "axis_leakage_pass_pct": float(self.axis_leakage_pass_pct),
            "axis_leakage_fail_pct": float(self.axis_leakage_fail_pct),
            "tolerance_mode": str(self.tolerance_mode),
        }


def freeze_capture_run_config(
    *,
    configured_dpi: int,
    direction: str,
    axis: str,
    settings: Mapping[str, Any],
) -> CaptureRunConfig:
    s = dict(settings)
    return CaptureRunConfig(
        configured_dpi=max(1, int(configured_dpi)),
        direction=str(direction),
        axis=str(axis),
        distance_mm=float(s.get("distance_mm", 100.0)),
        distance_input=float(s.get("distance_input", s.get("distance_mm", 100.0))),
        distance_unit=str(s.get("distance_unit", "mm")),
        movement_mode=str(s.get("movement_mode", "Vector Magnitude")),
        fixture_noise_floor_counts=int(s.get("fixture_noise_floor_counts", 7)),
        straightness_fail_pct=float(s.get("straightness_fail_pct", 85.0)),
        cpi_error_pass_pct=float(s.get("cpi_error_pass_pct", 3.0)),
        cpi_error_fail_pct=float(s.get("cpi_error_fail_pct", 5.0)),
        axis_leakage_pass_pct=float(s.get("axis_leakage_pass_pct", 2.0)),
        axis_leakage_fail_pct=float(s.get("axis_leakage_fail_pct", 5.0)),
        tolerance_mode=str(s.get("tolerance_mode") or "FIELD_STRICT"),
    )
