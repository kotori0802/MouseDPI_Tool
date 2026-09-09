"""Restrained presentation chrome motion — never touches measurement evidence.

Hard rule: smooth interface, unsmoothed evidence, stable data surfaces.

Do NOT use QGraphicsOpacityEffect on TrialPoster, Capture/Results pages,
Radial Target Gauge, Path Trace, or future scatter evidence. Those surfaces
must paint immediately and deterministically.

Technical Details expand/collapse may toggle instantly (preferred for reliability).
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

CHROME_DURATION_MS = 160


def motion_enabled(preferences: dict | None) -> bool:
    if not preferences:
        return True
    return bool(preferences.get("ui_motion", True))


def fade_widget(
    widget: QWidget,
    *,
    show: bool,
    enabled: bool = True,
    duration_ms: int = CHROME_DURATION_MS,
) -> None:
    """Show/hide lightweight chrome. Instant — no opacity effects on data surfaces."""
    _ = enabled, duration_ms
    # Clear any legacy opacity effect left from older builds.
    if widget.graphicsEffect() is not None:
        widget.setGraphicsEffect(None)
    widget.setVisible(show)
