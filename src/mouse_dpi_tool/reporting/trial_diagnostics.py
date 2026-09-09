"""Trial-level engineering diagnostics (descriptive; not Findings).

Built only from canonical Session trials / group summaries — never Qt widgets.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


def _active_trials(trials: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [
        t
        for t in trials
        if t.get("accepted") and not t.get("rejected") and not t.get("deleted")
    ]


@dataclass(frozen=True)
class TrialSequencePoint:
    report_trial_no: int
    trial_id: int
    configured_dpi: float
    error_pct: float


@dataclass(frozen=True)
class DpiErrorDistribution:
    configured_dpi: float
    trial_count: int
    median_error_pct: float | None
    q1_error_pct: float | None
    q3_error_pct: float | None
    min_error_pct: float | None
    max_error_pct: float | None
    errors: tuple[float, ...]


@dataclass(frozen=True)
class SpeedErrorPoint:
    configured_dpi: float
    speed_mm_s: float
    error_pct: float
    trial_id: int


@dataclass(frozen=True)
class LatencyErrorPoint:
    configured_dpi: float
    ready_to_first_motion_ms: float
    error_pct: float
    trial_id: int


@dataclass(frozen=True)
class SpeedCorrelation:
    configured_dpi: float
    n: int
    spearman_rho: float | None


def build_trial_sequence_points(
    trials: Sequence[Mapping[str, Any]],
    *,
    dpi_filter: float | None = None,
) -> list[TrialSequencePoint]:
    active = _active_trials(trials)
    # Prefer report_trial_no when present; else stable trial_id order.
    ordered = sorted(
        active,
        key=lambda t: (
            int(t["report_trial_no"])
            if t.get("report_trial_no") is not None
            else int(t.get("trial_id") or 0)
        ),
    )
    out: list[TrialSequencePoint] = []
    for i, t in enumerate(ordered, start=1):
        try:
            dpi = float(t["configured_dpi"])
            err = float(t["error_pct"])
            tid = int(t["trial_id"])
        except (KeyError, TypeError, ValueError):
            continue
        if dpi_filter is not None and abs(dpi - float(dpi_filter)) > 1e-9:
            continue
        seq = int(t["report_trial_no"]) if t.get("report_trial_no") is not None else i
        out.append(
            TrialSequencePoint(
                report_trial_no=seq,
                trial_id=tid,
                configured_dpi=dpi,
                error_pct=err,
            )
        )
    return out


def _quartile(sorted_vals: Sequence[float], q: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    # Inclusive method compatible with statistics.quantiles n=4 when n>=2.
    try:
        qs = statistics.quantiles(sorted_vals, n=4, method="inclusive")
        if q <= 0.25:
            return qs[0]
        if q <= 0.5:
            return qs[1]
        return qs[2]
    except statistics.StatisticsError:
        return sorted_vals[len(sorted_vals) // 2]


def build_dpi_error_distributions(
    trials: Sequence[Mapping[str, Any]],
) -> list[DpiErrorDistribution]:
    by_dpi: dict[float, list[float]] = {}
    for t in _active_trials(trials):
        try:
            dpi = float(t["configured_dpi"])
            err = float(t["error_pct"])
        except (KeyError, TypeError, ValueError):
            continue
        by_dpi.setdefault(dpi, []).append(err)
    rows: list[DpiErrorDistribution] = []
    for dpi in sorted(by_dpi):
        errs = sorted(by_dpi[dpi])
        med = statistics.median(errs) if errs else None
        rows.append(
            DpiErrorDistribution(
                configured_dpi=dpi,
                trial_count=len(errs),
                median_error_pct=round(med, 4) if med is not None else None,
                q1_error_pct=(
                    round(_quartile(errs, 0.25), 4) if errs else None  # type: ignore[arg-type]
                ),
                q3_error_pct=(
                    round(_quartile(errs, 0.75), 4) if errs else None  # type: ignore[arg-type]
                ),
                min_error_pct=round(errs[0], 4) if errs else None,
                max_error_pct=round(errs[-1], 4) if errs else None,
                errors=tuple(round(e, 4) for e in errs),
            )
        )
    return rows


def trial_motion_speed_mm_s(trial: Mapping[str, Any]) -> float | None:
    mt = trial.get("motion_timing")
    if not isinstance(mt, Mapping):
        return None
    if str(mt.get("timing_status") or "") != "OK":
        return None
    try:
        speed = float(mt["estimated_traversal_speed_mm_s"])
    except (KeyError, TypeError, ValueError):
        return None
    if not math.isfinite(speed) or speed <= 0:
        return None
    return speed


def build_speed_error_points(
    trials: Sequence[Mapping[str, Any]],
) -> list[SpeedErrorPoint]:
    out: list[SpeedErrorPoint] = []
    for t in _active_trials(trials):
        speed = trial_motion_speed_mm_s(t)
        if speed is None:
            continue
        try:
            out.append(
                SpeedErrorPoint(
                    configured_dpi=float(t["configured_dpi"]),
                    speed_mm_s=speed,
                    error_pct=float(t["error_pct"]),
                    trial_id=int(t["trial_id"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return out


def trial_ready_to_first_motion_ms(trial: Mapping[str, Any]) -> float | None:
    """Prefer ready_to_first_motion_ms; fall back to first_motion_delay_ms."""
    mt = trial.get("motion_timing")
    if not isinstance(mt, Mapping):
        return None
    for key in ("ready_to_first_motion_ms", "first_motion_delay_ms"):
        try:
            value = float(mt[key])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(value) and value >= 0:
            return value
    return None


def build_latency_error_points(
    trials: Sequence[Mapping[str, Any]],
) -> list[LatencyErrorPoint]:
    out: list[LatencyErrorPoint] = []
    for t in _active_trials(trials):
        delay = trial_ready_to_first_motion_ms(t)
        if delay is None:
            continue
        try:
            out.append(
                LatencyErrorPoint(
                    configured_dpi=float(t["configured_dpi"]),
                    ready_to_first_motion_ms=delay,
                    error_pct=float(t["error_pct"]),
                    trial_id=int(t["trial_id"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _spearman_rho(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    n = len(xs)
    if n < 2 or n != len(ys):
        return None

    def ranks(vals: Sequence[float]) -> list[float]:
        order = sorted(range(n), key=lambda i: vals[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx = ranks(xs)
    ry = ranks(ys)
    mean_x = sum(rx) / n
    mean_y = sum(ry) / n
    num = sum((a - mean_x) * (b - mean_y) for a, b in zip(rx, ry))
    den_x = math.sqrt(sum((a - mean_x) ** 2 for a in rx))
    den_y = math.sqrt(sum((b - mean_y) ** 2 for b in ry))
    if den_x <= 0 or den_y <= 0:
        return None
    return num / (den_x * den_y)


def build_speed_correlations(
    trials: Sequence[Mapping[str, Any]],
    *,
    min_n: int = 8,
) -> list[SpeedCorrelation]:
    """Per-DPI Spearman rho only — never pool DPI groups."""
    by_dpi: dict[float, list[tuple[float, float]]] = {}
    for p in build_speed_error_points(trials):
        by_dpi.setdefault(p.configured_dpi, []).append((p.speed_mm_s, p.error_pct))
    out: list[SpeedCorrelation] = []
    for dpi in sorted(by_dpi):
        pairs = by_dpi[dpi]
        n = len(pairs)
        rho = None
        if n >= min_n:
            rho = _spearman_rho([a for a, _ in pairs], [b for _, b in pairs])
            if rho is not None:
                rho = round(rho, 4)
        out.append(SpeedCorrelation(configured_dpi=dpi, n=n, spearman_rho=rho))
    return out


def session_has_motion_timing(trials: Sequence[Mapping[str, Any]]) -> bool:
    return any(trial_motion_speed_mm_s(t) is not None for t in _active_trials(trials))
