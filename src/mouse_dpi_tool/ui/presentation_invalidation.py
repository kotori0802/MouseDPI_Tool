"""Presentation invalidation revisions — UI-only, never Session evidence.

The ~30 Hz Capture timer may update LIVE visualization only.
All other surfaces refresh when their dependency revision bumps.

Test/dev instrumentation counters live here and must not enter Session JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PresentationRevisions:
    """Bump counters owned by the UI shell / Capture page."""

    capture_live: int = 0  # path/gauge may track separately; informational
    capture_state: int = 0  # start/stop/cancel/pending chrome
    trial_lifecycle: int = 0  # admit/reject/restore/delete/new session
    session_analysis: int = 0  # findings/groups/ratios dependent
    locale: int = 0
    theme: int = 0

    def bump_locale(self) -> None:
        self.locale += 1

    def bump_theme(self) -> None:
        self.theme += 1

    def bump_trial_lifecycle(self) -> None:
        self.trial_lifecycle += 1
        self.session_analysis += 1

    def bump_session_analysis(self) -> None:
        """Groups / ratios / fixture diagnostics that depend on settings rebuild."""
        self.session_analysis += 1

    def bump_capture_state(self) -> None:
        self.capture_state += 1


@dataclass
class PresentationCounters:
    """Development/test-only counters — reset between tests."""

    fixture_diag_renders: int = 0
    trial_table_rebuilds: int = 0
    header_resize_calls: int = 0
    sidebar_polish_calls: int = 0
    gauge_updates: int = 0
    path_updates: int = 0
    live_timer_ticks: int = 0

    def reset(self) -> None:
        self.fixture_diag_renders = 0
        self.trial_table_rebuilds = 0
        self.header_resize_calls = 0
        self.sidebar_polish_calls = 0
        self.gauge_updates = 0
        self.path_updates = 0
        self.live_timer_ticks = 0


# Process-wide presentation revisions + counters (not Session evidence).
REVISIONS = PresentationRevisions()
COUNTERS = PresentationCounters()


def reset_presentation_instrumentation() -> None:
    """Test helper — clear counters; leave revisions."""
    COUNTERS.reset()


def reset_all_presentation_state() -> None:
    """Test helper — reset revisions + counters in-place (keep object identity).

    Callers that ``from ... import REVISIONS`` must keep the same object identity;
    rebinding module globals would desync those imports.
    """
    REVISIONS.capture_live = 0
    REVISIONS.capture_state = 0
    REVISIONS.trial_lifecycle = 0
    REVISIONS.session_analysis = 0
    REVISIONS.locale = 0
    REVISIONS.theme = 0
    COUNTERS.reset()
