"""Canonical raw movement evidence shared by Capture and Path Quality.

Capture is the event source. Path Quality owns complete/streaming evidence.
UI visualization buffers are bounded/decimated and are never Path Quality truth.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MovementSample:
    """One Raw Input relative movement report.

    dx/dy are host-side relative counts for this event, not cursor pixels
    and not accumulated path totals.
    """

    dx: int
    dy: int
    timestamp_s: float | None = None
    device_id: str | None = None


# UI display buffers may drop samples; Path Quality must not.
VISUALIZATION_PATH_MAX_POINTS = 6000
