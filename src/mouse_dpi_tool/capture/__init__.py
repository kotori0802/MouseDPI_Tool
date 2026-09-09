"""Capture layer — Raw Input / synthetic event source only."""

from __future__ import annotations

from mouse_dpi_tool.capture.engine import CaptureEngine, CaptureSnapshot, CaptureState
from mouse_dpi_tool.capture.motion_timing import (
    StreamingMotionTimingAccumulator,
    attach_motion_timing_to_trial,
)
from mouse_dpi_tool.capture.synthetic import SyntheticEventSource
from mouse_dpi_tool.capture.visualization_buffer import VisualizationPathBuffer

CAPTURE_OWNS = (
    "lifecycle",
    "net_counts_x",
    "net_counts_y",
    "per_device_counts",
    "movement_sample_events",
    "device_ids",
    "capture_integrity",
)

CAPTURE_MUST_NOT_COMPUTE = (
    "path_total_counts",
    "straightness_pct",
    "path_quality_classification",
    "measured_cpi",
    "findings",
)


def create_windows_capture_engine(*, on_status=None) -> CaptureEngine:
    from mouse_dpi_tool.capture.raw_input_source import RawInputSubprocessSource

    return CaptureEngine(source=RawInputSubprocessSource(), on_status=on_status)


__all__ = [
    "CAPTURE_MUST_NOT_COMPUTE",
    "CAPTURE_OWNS",
    "CaptureEngine",
    "CaptureSnapshot",
    "CaptureState",
    "StreamingMotionTimingAccumulator",
    "SyntheticEventSource",
    "VisualizationPathBuffer",
    "attach_motion_timing_to_trial",
    "create_windows_capture_engine",
]


def __getattr__(name: str):
    if name in {"BRIDGE_READY", "RawInputSubprocessSource", "SourceStartError", "SourceStopError"}:
        from mouse_dpi_tool.capture import raw_input_source as _ris

        return getattr(_ris, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
