"""Path Quality — sole owner of path_total_counts / straightness / reversal classification."""

from __future__ import annotations

from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.path_quality.accumulator import StreamingPathQualityAccumulator, attach_to_trial
from mouse_dpi_tool.path_quality.metrics import classify_path_quality

PATH_QUALITY_OWNED_FIELDS = (
    "path_total_counts",
    "straightness_pct",
    "path_quality_status",
    "path_quality_issue_codes",
)

__all__ = [
    "PATH_QUALITY_OWNED_FIELDS",
    "StreamingPathQualityAccumulator",
    "MovementSample",
    "attach_to_trial",
    "classify_path_quality",
]
