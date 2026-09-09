"""Measurement domain — Effective CPI math (brand-neutral, Hub-free)."""

from mouse_dpi_tool.measurement.direction_evidence import (
    DirectionEvidenceError,
    DirectionMismatchError,
    assert_direction_matches_counts,
    require_canonical_direction,
)
from mouse_dpi_tool.measurement.distance import distance_to_mm
from mouse_dpi_tool.measurement.group import build_group_summaries, summarize_group, trial_group_id
from mouse_dpi_tool.measurement.legacy_compat import as_legacy_group, as_legacy_trial, resolve_configured_dpi
from mouse_dpi_tool.measurement.ratio import build_ratio_analysis
from mouse_dpi_tool.measurement.settings import DEFAULT_SETTINGS, normalize_settings, status_from_limits
from mouse_dpi_tool.measurement.synthetic import make_synthetic_trials
from mouse_dpi_tool.measurement.trial import compute_trial, recompute_trial_from_evidence

__all__ = [
    "DEFAULT_SETTINGS",
    "DirectionEvidenceError",
    "DirectionMismatchError",
    "as_legacy_group",
    "as_legacy_trial",
    "assert_direction_matches_counts",
    "build_group_summaries",
    "build_ratio_analysis",
    "compute_trial",
    "distance_to_mm",
    "make_synthetic_trials",
    "normalize_settings",
    "recompute_trial_from_evidence",
    "require_canonical_direction",
    "resolve_configured_dpi",
    "status_from_limits",
    "summarize_group",
    "trial_group_id",
]
