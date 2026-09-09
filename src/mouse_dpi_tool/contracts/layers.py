"""Layer ownership contracts.

Qt UI must only call through these boundaries. Capture never computes Path Quality.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from mouse_dpi_tool.contracts.movement import MovementSample


@runtime_checkable
class CaptureEngine(Protocol):
    """Owns Raw Input lifecycle and publishes MovementSample events.

    Must NOT compute path_total_counts, straightness_pct, or reversal/jitter.
    Must NOT compute CPI / findings / report schema.
    Must NOT treat a bounded UI path buffer as Path Quality evidence.
    """

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def cancel(self) -> None: ...

    def subscribe(self, listener: Callable[[MovementSample], None]) -> None:
        """Register a listener (Path Quality accumulator, optional UI)."""
        ...

    @property
    def net_counts_x(self) -> int:
        """Net start-to-end dx for CPI (not path length)."""
        ...

    @property
    def net_counts_y(self) -> int: ...

    @property
    def device_ids(self) -> Sequence[str]: ...


@runtime_checkable
class PathQualityAccumulator(Protocol):
    """Streaming Path Quality evidence owner.

    Subscribes to every MovementSample for the capture. Must retain complete
    evidence (or equivalent streaming totals) — not a 6000-point UI buffer.
    """

    def reset(self) -> None: ...

    def on_sample(self, sample: MovementSample) -> None: ...

    def snapshot(self) -> Mapping[str, Any]:
        """path_total_counts, straightness_pct, classification. Never mutates Accuracy."""
        ...


@runtime_checkable
class VisualizationPathBuffer(Protocol):
    """Bounded / decimated path for display only. Not Path Quality evidence."""

    def on_sample(self, sample: MovementSample) -> None: ...

    def points(self) -> Sequence[Mapping[str, float]]: ...


@runtime_checkable
class MeasurementDomain(Protocol):
    """CPI math, group stats, ratio analysis."""

    def compute_trial(self, **kwargs: Any) -> Mapping[str, Any]: ...
    def build_group_summaries(self, trials: Sequence[Mapping[str, Any]], settings: Mapping[str, Any]) -> list[dict]: ...
    def build_ratio_analysis(self, groups: Sequence[Mapping[str, Any]], settings: Mapping[str, Any]) -> list[dict]: ...


@runtime_checkable
class SessionStore(Protocol):
    """DUT metadata, trial lifecycle, run/session identity."""

    def new_dut(self) -> None: ...
    def add_trial(self, trial: Mapping[str, Any]) -> None: ...
    def reject_trials(self, trial_ids: Sequence[int]) -> None: ...
    def delete_trials(self, trial_ids: Sequence[int]) -> None: ...
    def to_session_dict(self) -> Mapping[str, Any]: ...


@runtime_checkable
class FindingsBuilder(Protocol):
    """Builds independent findings dimensions. No overall health verdict."""

    def build(self, session: Mapping[str, Any]) -> Mapping[str, Any]: ...


@runtime_checkable
class ReportWriter(Protocol):
    """Tool-owned artifact naming and export. Session JSON schema is source of truth."""

    def write_session_json(self, session: Mapping[str, Any], path: Any) -> Any: ...
