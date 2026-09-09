"""V1 chart card models — presentation/interpretation of canonical group evidence.

Not a Finding. Does not alter Measurement / Session / Findings formulas.
Qt Results and HTML report must consume the same model for engineering values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from mouse_dpi_tool.measurement.settings import status_from_limits
from mouse_dpi_tool.reporting.trends_points import group_trend_points


@dataclass(frozen=True)
class ChartSeriesPoint:
    configured_dpi: float
    value: float
    trial_count: int | None = None
    status: str | None = None


@dataclass(frozen=True)
class ChartThresholds:
    pass_pct: float
    fail_pct: float

    @property
    def warn_lo(self) -> float:
        return float(self.pass_pct)

    @property
    def warn_hi(self) -> float:
        return float(self.fail_pct)


@dataclass(frozen=True)
class ChartObservation:
    """Structured fact for localized formatting — not a Finding verdict."""

    code: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChartCardModel:
    chart_id: str
    title_en: str
    caption_en: str
    x_label_en: str
    y_label_en: str
    legend_en: tuple[str, ...]
    points: tuple[ChartSeriesPoint, ...]
    ideal_points: tuple[ChartSeriesPoint, ...] = ()
    thresholds: ChartThresholds | None = None
    group_status_counts: Mapping[str, int] | None = None
    observation: ChartObservation | None = None
    # Clarifies Chart-1 mean deviation vs Accuracy max trial error.
    metric_note_en: str = ""

    def as_xy(self) -> list[tuple[float, float]]:
        return [(p.configured_dpi, p.value) for p in self.points]

    def ideal_as_xy(self) -> list[tuple[float, float]]:
        return [(p.configured_dpi, p.value) for p in self.ideal_points]

    def point_tooltip_en(self, point: ChartSeriesPoint) -> str:
        dpi = int(point.configured_dpi) if float(point.configured_dpi).is_integer() else point.configured_dpi
        lines = [f"Configured DPI: {dpi}"]
        if point.trial_count is not None:
            lines.append(f"Trials: {point.trial_count}")
        if self.chart_id == "measured_cpi":
            lines.append(f"Average measured CPI: {point.value:.1f}")
        elif self.chart_id == "max_error":
            lines.append(f"Maximum absolute CPI error: {point.value:.2f}%")
        elif self.chart_id == "repeatability":
            lines.append(f"CPI CV: {point.value:.4f}%")
        if point.status:
            lines.append(f"Status: {point.status}")
        return "\n".join(lines)


def _status_counts_for_errors(
    groups: Sequence[Mapping[str, Any]],
    *,
    pass_pct: float,
    fail_pct: float,
) -> dict[str, int]:
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for g in groups:
        err = g.get("max_abs_error_pct")
        if err is None:
            continue
        st = status_from_limits(float(err), pass_pct, fail_pct)
        counts[st] = counts.get(st, 0) + 1
    return counts


def _status_counts_for_cv(
    groups: Sequence[Mapping[str, Any]],
    *,
    pass_pct: float,
    fail_pct: float,
) -> dict[str, int]:
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for g in groups:
        cv = g.get("cpi_cv_pct")
        if cv is None:
            continue
        st = status_from_limits(float(cv), pass_pct, fail_pct)
        counts[st] = counts.get(st, 0) + 1
    return counts


def _groups_by_dpi(groups: Sequence[Mapping[str, Any]]) -> dict[float, Mapping[str, Any]]:
    out: dict[float, Mapping[str, Any]] = {}
    for g in groups:
        try:
            out[float(g.get("configured_dpi"))] = g
        except (TypeError, ValueError):
            continue
    return out


def format_observation_en(obs: ChartObservation | None) -> str:
    if obs is None:
        return ""
    p = obs.params
    if obs.code == "cpi.all_below_ideal":
        return (
            "All measured group means are below the ideal 1:1 reference; "
            "the largest deviation of group-average CPI from configured DPI is "
            f"{float(p['max_mean_deviation_pct']):.2f}% "
            "(not the same as Accuracy maximum individual Trial error)."
        )
    if obs.code == "cpi.all_above_ideal":
        return (
            "All measured group means are above the ideal 1:1 reference; "
            "the largest deviation of group-average CPI from configured DPI is "
            f"{float(p['max_mean_deviation_pct']):.2f}% "
            "(not the same as Accuracy maximum individual Trial error)."
        )
    if obs.code == "cpi.mixed_vs_ideal":
        return (
            "Measured group means sit both above and below the ideal 1:1 reference; "
            "the largest deviation of group-average CPI from configured DPI is "
            f"{float(p['max_mean_deviation_pct']):.2f}% "
            "(not the same as Accuracy maximum individual Trial error)."
        )
    if obs.code == "cpi.no_data":
        return "No DPI group averages are available for this Session."
    if obs.code == "error.band_counts":
        return (
            f"PASS {int(p['pass'])} · WARN {int(p['warn'])} · FAIL {int(p['fail'])} "
            f"DPI groups by maximum absolute CPI error vs Session Accuracy thresholds "
            f"(PASS ≤ {float(p['pass_pct']):g}% · WARN > {float(p['pass_pct']):g}%–"
            f"{float(p['fail_pct']):g}% · FAIL > {float(p['fail_pct']):g}%)."
        )
    if obs.code == "error.no_data":
        return "No DPI group error values are available for this Session."
    if obs.code == "cv.highest":
        return (
            f"{int(p['dpi'])} DPI has the highest CPI CV in this Session "
            f"({float(p['cv']):.4f}%) — lower CV means higher repeatability."
        )
    if obs.code == "cv.no_data":
        return "No DPI group CPI CV values are available for this Session."
    return obs.code


def build_v1_chart_cards(
    group_summaries: Sequence[Mapping[str, Any]],
    settings: Mapping[str, Any],
) -> dict[str, ChartCardModel]:
    """Build the three V1 descriptive chart cards from canonical evidence."""
    pts = group_trend_points(group_summaries)
    by_dpi = _groups_by_dpi(group_summaries)
    try:
        pass_pct = float(settings.get("cpi_error_pass_pct"))
        fail_pct = float(settings.get("cpi_error_fail_pct"))
    except (TypeError, ValueError):
        pass_pct, fail_pct = 3.0, 5.0
    try:
        cv_pass = float(settings.get("cpi_cv_pass_pct"))
        cv_fail = float(settings.get("cpi_cv_fail_pct"))
    except (TypeError, ValueError):
        cv_pass, cv_fail = 1.0, 3.0

    cpi_points: list[ChartSeriesPoint] = []
    ideal_points: list[ChartSeriesPoint] = []
    err_points: list[ChartSeriesPoint] = []
    cv_points: list[ChartSeriesPoint] = []
    signed_vs_ideal: list[float] = []
    mean_devs: list[float] = []

    for row in pts:
        dpi = float(row["configured_dpi"])
        g = by_dpi.get(dpi, {})
        trials = int(g.get("valid_trials") or 0) or None
        avg = row.get("avg_measured_cpi")
        if avg is not None:
            cpi_points.append(
                ChartSeriesPoint(dpi, float(avg), trial_count=trials, status=str(g.get("status") or "") or None)
            )
            ideal_points.append(ChartSeriesPoint(dpi, dpi))
            signed_vs_ideal.append(float(avg) - dpi)
            if dpi:
                mean_devs.append(abs(float(avg) - dpi) / dpi * 100.0)
        err = row.get("max_abs_error_pct")
        if err is not None:
            st = status_from_limits(float(err), pass_pct, fail_pct)
            err_points.append(
                ChartSeriesPoint(dpi, float(err), trial_count=trials, status=st)
            )
        cv = row.get("cpi_cv_pct")
        if cv is not None:
            st = status_from_limits(float(cv), cv_pass, cv_fail)
            cv_points.append(
                ChartSeriesPoint(dpi, float(cv), trial_count=trials, status=st)
            )

    if not cpi_points:
        cpi_obs = ChartObservation("cpi.no_data")
    else:
        max_dev = max(mean_devs) if mean_devs else 0.0
        params = {"max_mean_deviation_pct": round(max_dev, 2)}
        if all(d < 0 for d in signed_vs_ideal):
            cpi_obs = ChartObservation("cpi.all_below_ideal", params)
        elif all(d > 0 for d in signed_vs_ideal):
            cpi_obs = ChartObservation("cpi.all_above_ideal", params)
        else:
            cpi_obs = ChartObservation("cpi.mixed_vs_ideal", params)

    err_counts = _status_counts_for_errors(
        group_summaries, pass_pct=pass_pct, fail_pct=fail_pct
    )
    if not err_points:
        err_obs = ChartObservation("error.no_data")
    else:
        err_obs = ChartObservation(
            "error.band_counts",
            {
                "pass": err_counts["PASS"],
                "warn": err_counts["WARN"],
                "fail": err_counts["FAIL"],
                "pass_pct": pass_pct,
                "fail_pct": fail_pct,
            },
        )

    if not cv_points:
        cv_obs = ChartObservation("cv.no_data")
    else:
        top = max(cv_points, key=lambda p: p.value)
        cv_obs = ChartObservation(
            "cv.highest",
            {"dpi": int(top.configured_dpi), "cv": round(top.value, 4)},
        )

    cv_counts = _status_counts_for_cv(group_summaries, pass_pct=cv_pass, fail_pct=cv_fail)

    return {
        "measured_cpi": ChartCardModel(
            chart_id="measured_cpi",
            title_en="Measured CPI vs Configured DPI",
            caption_en=(
                "Compare each DPI group's average measured CPI to the ideal 1:1 target; "
                "closer to the ideal line means Effective CPI is nearer the configured value."
            ),
            x_label_en="Configured DPI",
            y_label_en="Average measured CPI",
            legend_en=("Measured average", "Ideal 1:1"),
            points=tuple(cpi_points),
            ideal_points=tuple(ideal_points),
            observation=cpi_obs,
            metric_note_en=(
                "Chart summary uses deviation of group-average CPI from configured DPI. "
                "Accuracy Finding uses maximum individual Trial |error| — different metrics."
            ),
        ),
        "max_error": ChartCardModel(
            chart_id="max_error",
            title_en="Maximum CPI error by DPI",
            caption_en=(
                "Maximum absolute individual CPI error per DPI group, compared with this "
                "Session's Accuracy PASS / WARN / FAIL thresholds."
            ),
            x_label_en="Configured DPI",
            y_label_en="Maximum absolute CPI error (%)",
            legend_en=("Max individual |error| %", "PASS / WARN / FAIL thresholds"),
            points=tuple(err_points),
            thresholds=ChartThresholds(pass_pct=pass_pct, fail_pct=fail_pct),
            group_status_counts=err_counts,
            observation=err_obs,
            metric_note_en=(
                "Uses each group's maximum absolute Trial CPI error (same family as Accuracy)."
            ),
        ),
        "repeatability": ChartCardModel(
            chart_id="repeatability",
            title_en="Repeatability (CPI CV)",
            caption_en=(
                "CPI CV is the dispersion of repeated measurements at the same DPI; "
                "lower values mean higher repeatability."
            ),
            x_label_en="Configured DPI",
            y_label_en="CPI CV (%)",
            legend_en=("CPI CV %", "Repeatability PASS / WARN / FAIL thresholds"),
            points=tuple(cv_points),
            thresholds=ChartThresholds(pass_pct=cv_pass, fail_pct=cv_fail),
            group_status_counts=cv_counts,
            observation=cv_obs,
        ),
    }


def finding_metric_rows(
    dimension: str,
    metrics: Mapping[str, Any],
    *,
    t: Callable[[str], str] | None = None,
) -> list[tuple[str, str]]:
    """Finding metric rows. Label keys are i18n-ready; pass ``t`` to localize."""

    def label(key: str, fallback: str) -> str:
        if t is None:
            return fallback
        text = t(key)
        return fallback if text == key else text

    m = dict(metrics or {})

    def _fmt(value: object, *, digits: int = 2) -> str:
        if value is None or value == "":
            return "—"
        try:
            return f"{float(value):.{digits}f}"
        except (TypeError, ValueError):
            return str(value)

    if dimension == "accuracy":
        return [
            (
                label("finding.metric.max_individual_error", "Maximum individual CPI error"),
                f"{_fmt(m.get('max_abs_error_pct'))}%",
            ),
            (
                label("finding.metric.groups_dist", "Groups"),
                f"PASS {int(m.get('groups_pass') or 0)} · "
                f"WARN {int(m.get('groups_warn') or 0)} · "
                f"FAIL {int(m.get('groups_fail') or 0)}",
            ),
            (
                label("finding.metric.active_trials", "Active Trials"),
                str(m.get("active_trial_count") if m.get("active_trial_count") is not None else "—"),
            ),
        ]
    if dimension == "repeatability":
        if any(k in m for k in ("groups_pass", "groups_warn", "groups_fail")):
            dist = (
                f"PASS {int(m.get('groups_pass') or 0)} · "
                f"WARN {int(m.get('groups_warn') or 0)} · "
                f"FAIL {int(m.get('groups_fail') or 0)}"
            )
        else:
            dist = (
                f"Evaluated {m.get('evaluated_group_count', '—')} · "
                f"Insufficient {m.get('insufficient_group_count', '—')}"
            )
        return [
            (
                label("finding.metric.max_cpi_cv", "Maximum CPI CV"),
                f"{_fmt(m.get('max_cpi_cv_pct'), digits=4)}%",
            ),
            (label("finding.metric.groups_dist", "Groups"), dist),
            (
                label("finding.metric.min_trials", "Min trials / group"),
                str(
                    m.get("min_valid_trials_per_group")
                    if m.get("min_valid_trials_per_group") is not None
                    else "—"
                ),
            ),
        ]
    if dimension == "ratio":
        return [
            (
                label("finding.metric.max_ratio_error", "Maximum |ratio error|"),
                f"{_fmt(m.get('max_abs_ratio_error_pct'), digits=4)}%",
            ),
            (
                label("finding.metric.pairs_dist", "Pairs"),
                f"PASS {int(m.get('ratios_pass') or 0)} · "
                f"WARN {int(m.get('ratios_warn') or 0)} · "
                f"FAIL {int(m.get('ratios_fail') or 0)}",
            ),
        ]
    if dimension == "path_quality":
        rows = [
            (
                label("finding.metric.pq_pass", "Path Quality PASS"),
                str(m.get("pq_pass") if m.get("pq_pass") is not None else "—"),
            ),
            (
                label("finding.metric.pq_warn", "WARN"),
                str(m.get("pq_warn") if m.get("pq_warn") is not None else "—"),
            ),
            (
                label("finding.metric.pq_fail", "FAIL"),
                str(m.get("pq_fail") if m.get("pq_fail") is not None else "—"),
            ),
            (
                label("finding.metric.pq_not_evaluated", "NOT_EVALUATED"),
                str(m.get("pq_not_evaluated") if m.get("pq_not_evaluated") is not None else "—"),
            ),
            (
                label("finding.metric.pq_trials", "Trials with PQ"),
                str(m.get("pq_trial_count") if m.get("pq_trial_count") is not None else "—"),
            ),
        ]
        try:
            ne = int(m.get("pq_not_evaluated") or 0)
            fail = int(m.get("pq_fail") or 0)
        except (TypeError, ValueError):
            ne, fail = 0, 0
        if ne > 0 and fail == 0:
            note = label(
                "finding.metric.pq_coverage_value",
                "WARN reflects incomplete path-evidence coverage "
                "({n} NOT_EVALUATED); no PQ FAIL detected.",
            ).format(n=ne)
            rows.append(
                (label("finding.metric.pq_coverage_note", "Coverage note"), note)
            )
        return rows
    return [(str(k), str(v)) for k, v in m.items() if v not in (None, "")]
