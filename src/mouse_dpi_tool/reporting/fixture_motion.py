"""Fixture / Motion descriptive diagnostics from canonical Trial evidence.

Presentation/reporting helper only — not a Finding, not a fixture/sensor verdict.
Uses Session Trial fields only (never PathCanvas presentation buffers).

Canonical fields consumed (when present on Active Fixture Vector trials):
- counts_x, counts_y          → endpoint heading via atan2(dy, dx)
- vector_counts               → net displacement magnitude (measurement)
- path_total_counts           → Path Quality path length (noise-floor semantics)
- straightness_pct            → Path Quality straightness (owned formula; capped at 100)

Fixture Vector orientation is an AXIS (undirected), not an oriented arrow.
Travel at θ and θ+180° is the same physical fixture axis. Diagnostics therefore
use doubled-angle (axial) circular statistics, not 360° directional SD.

Path Quality semantics (do not change in this module):
- net dx/dy include every sample
- path_total only includes steps above the fixture noise floor
- straightness = min(100, vector/path_total*100)

Therefore straightness == 100% is a metric ceiling, not proof of perfect geometry.
If path_total < vector (noise-floor exclusion), path_excess is NOT_EVALUATED.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

MOVEMENT_MODE_FIXTURE_VECTOR = "Vector Magnitude"
PATH_EXCESS_NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(frozen=True)
class PerDpiMotionRow:
    configured_dpi: float
    trial_count: int
    axis_orientation_deg: float | None
    axis_spread_deg: float | None
    forward_trials: int
    reverse_trials: int
    forward_avg_measured_cpi: float | None
    reverse_avg_measured_cpi: float | None
    forward_avg_error_pct: float | None
    reverse_avg_error_pct: float | None
    forward_reverse_mean_cpi_diff_pct: float | None
    directional_asymmetry_note: str | None
    avg_straightness_pct: float | None
    straightness_at_ceiling: bool
    path_excess_state: str

    # Backward-compatible aliases (axial values; not directional SD).
    @property
    def mean_heading_deg(self) -> float | None:
        return self.axis_orientation_deg

    @property
    def heading_spread_deg(self) -> float | None:
        return self.axis_spread_deg


@dataclass(frozen=True)
class FixtureMotionDiagnostics:
    """Descriptive aggregates — no PASS/WARN/FAIL verdict."""

    trial_count: int
    trials_with_straightness: int
    trials_with_path_excess: int
    trials_with_heading: int
    avg_straightness_pct: float | None
    min_straightness_pct: float | None
    straightness_at_ceiling: bool
    max_path_excess_pct: float | None
    path_excess_state: str
    axis_orientation_deg: float | None
    axis_spread_deg: float | None
    forward_trials: int
    reverse_trials: int
    per_dpi: tuple[PerDpiMotionRow, ...]
    missing_fields: tuple[str, ...]
    notes: tuple[str, ...]

    @property
    def mean_heading_deg(self) -> float | None:
        """Alias — Fixture Vector reports axial orientation here."""
        return self.axis_orientation_deg

    @property
    def heading_spread_deg(self) -> float | None:
        """Alias — Fixture Vector reports axial spread here."""
        return self.axis_spread_deg

    @property
    def available(self) -> bool:
        return self.trial_count > 0 and (
            self.avg_straightness_pct is not None
            or self.path_excess_state not in {"—", PATH_EXCESS_NOT_EVALUATED}
            or self.max_path_excess_pct is not None
            or self.axis_orientation_deg is not None
        )


def endpoint_heading_deg(counts_x: float | int, counts_y: float | int) -> float:
    """Signed endpoint travel heading from net counts (−180…+180]."""
    return math.degrees(math.atan2(float(counts_y), float(counts_x)))


def circular_mean_deg(angles_deg: Sequence[float]) -> float | None:
    """Ordinary 360° circular mean (Directional Axis / polarity helpers)."""
    if not angles_deg:
        return None
    sx = sum(math.cos(math.radians(a)) for a in angles_deg)
    sy = sum(math.sin(math.radians(a)) for a in angles_deg)
    if abs(sx) < 1e-15 and abs(sy) < 1e-15:
        return None
    return math.degrees(math.atan2(sy, sx))


def circular_spread_deg(angles_deg: Sequence[float]) -> float | None:
    """Ordinary 360° circular standard deviation (degrees)."""
    n = len(angles_deg)
    if n == 0:
        return None
    if n == 1:
        return 0.0
    sx = sum(math.cos(math.radians(a)) for a in angles_deg) / n
    sy = sum(math.sin(math.radians(a)) for a in angles_deg) / n
    r = math.hypot(sx, sy)
    if r >= 1.0 - 1e-12:
        return 0.0
    if r <= 1e-12:
        return 180.0
    return math.degrees(math.sqrt(max(0.0, -2.0 * math.log(r))))


def axial_mean_deg(headings_deg: Sequence[float]) -> float | None:
    """Fixture-axis orientation via doubled-angle circular mean.

    θ and θ+180° map to the same axis. Result is in (−90…+90] degrees.
    """
    if not headings_deg:
        return None
    doubled = [2.0 * float(h) for h in headings_deg]
    mean2 = circular_mean_deg(doubled)
    if mean2 is None:
        return None
    axis = 0.5 * mean2
    # Normalize to (−90, 90]
    while axis <= -90.0:
        axis += 180.0
    while axis > 90.0:
        axis -= 180.0
    return axis


def axial_spread_deg(headings_deg: Sequence[float]) -> float | None:
    """Axial orientation spread: circular SD of 2θ, then halved back to axis space.

    Opposite travel on the same fixture yields near-zero spread (unlike 360° SD).
    """
    n = len(headings_deg)
    if n == 0:
        return None
    if n == 1:
        return 0.0
    doubled = [2.0 * float(h) for h in headings_deg]
    spread2 = circular_spread_deg(doubled)
    if spread2 is None:
        return None
    # Cap at 90° in orientation space (maximum axial dispersion).
    return min(90.0, 0.5 * spread2)


def travel_polarity(heading_deg: float, axis_deg: float) -> str:
    """Classify travel as forward/reverse along the fixture AXIS (not PASS/FAIL)."""
    # Smallest signed difference in (−180, 180]
    d = (float(heading_deg) - float(axis_deg) + 180.0) % 360.0 - 180.0
    return "forward" if abs(d) <= 90.0 else "reverse"


def path_excess_result(
    path_total_counts: float | None,
    vector_counts: float | None,
) -> tuple[float | None, str]:
    if path_total_counts is None or vector_counts is None:
        return None, "—"
    try:
        path = float(path_total_counts)
        vec = float(vector_counts)
    except (TypeError, ValueError):
        return None, "—"
    if vec <= 0 or path <= 0:
        return None, "—"
    if path < vec:
        return None, PATH_EXCESS_NOT_EVALUATED
    return (path / vec - 1.0) * 100.0, "ok"


def path_excess_pct(path_total_counts: float, vector_counts: float) -> float | None:
    value, state = path_excess_result(path_total_counts, vector_counts)
    if state != "ok":
        return None
    return value


def _is_fixture_vector(trial: Mapping[str, Any]) -> bool:
    return str(trial.get("movement_mode") or "") == MOVEMENT_MODE_FIXTURE_VECTOR


def _headings_from_trials(trials: Sequence[Mapping[str, Any]]) -> list[float]:
    out: list[float] = []
    for t in trials:
        if "counts_x" not in t or "counts_y" not in t:
            continue
        try:
            out.append(endpoint_heading_deg(t["counts_x"], t["counts_y"]))
        except (TypeError, ValueError):
            continue
    return out


def _polarity_counts(
    headings: Sequence[float], axis_deg: float | None
) -> tuple[int, int]:
    if axis_deg is None or not headings:
        return 0, 0
    fwd = sum(1 for h in headings if travel_polarity(h, axis_deg) == "forward")
    return fwd, len(headings) - fwd


def _mean(vals: Sequence[float]) -> float | None:
    if not vals:
        return None
    return sum(vals) / len(vals)


def _per_dpi_rows(fixture: Sequence[Mapping[str, Any]]) -> tuple[PerDpiMotionRow, ...]:
    by_dpi: dict[float, list[Mapping[str, Any]]] = {}
    for t in fixture:
        try:
            dpi = float(t.get("configured_dpi"))
        except (TypeError, ValueError):
            continue
        by_dpi.setdefault(dpi, []).append(t)
    rows: list[PerDpiMotionRow] = []
    for dpi in sorted(by_dpi):
        group = by_dpi[dpi]
        headings = _headings_from_trials(group)
        straight: list[float] = []
        excess_ok: list[float] = []
        excess_states: list[str] = []
        for t in group:
            st = t.get("straightness_pct")
            if st is not None:
                try:
                    straight.append(float(st))
                except (TypeError, ValueError):
                    pass
            val, state = path_excess_result(t.get("path_total_counts"), t.get("vector_counts"))
            excess_states.append(state)
            if state == "ok" and val is not None:
                excess_ok.append(val)
        if any(s == PATH_EXCESS_NOT_EVALUATED for s in excess_states):
            pe_state = PATH_EXCESS_NOT_EVALUATED
        elif excess_ok:
            pe_state = f"{max(excess_ok):.2f}%"
        else:
            pe_state = "—"
        avg_st = sum(straight) / len(straight) if straight else None
        ceiling = bool(straight) and min(straight) >= 100.0 - 1e-9
        axis = axial_mean_deg(headings)
        spread = axial_spread_deg(headings)
        fwd_cpi: list[float] = []
        rev_cpi: list[float] = []
        fwd_err: list[float] = []
        rev_err: list[float] = []
        if axis is not None:
            for t in group:
                if "counts_x" not in t or "counts_y" not in t:
                    continue
                try:
                    h = endpoint_heading_deg(t["counts_x"], t["counts_y"])
                    pol = travel_polarity(h, axis)
                    cpi = float(t["measured_cpi"]) if t.get("measured_cpi") is not None else None
                    err = float(t["error_pct"]) if t.get("error_pct") is not None else None
                except (TypeError, ValueError):
                    continue
                if cpi is None:
                    continue
                if pol == "forward":
                    fwd_cpi.append(cpi)
                    if err is not None:
                        fwd_err.append(err)
                else:
                    rev_cpi.append(cpi)
                    if err is not None:
                        rev_err.append(err)
        fwd_n, rev_n = len(fwd_cpi), len(rev_cpi)
        fwd_avg = _mean(fwd_cpi)
        rev_avg = _mean(rev_cpi)
        diff_pct = None
        note = None
        if fwd_avg is not None and rev_avg is not None and dpi > 0:
            diff_pct = abs(fwd_avg - rev_avg) / dpi * 100.0
            if diff_pct >= 0.5 and fwd_n >= 2 and rev_n >= 2:
                note = (
                    "Directional asymmetry observed. Forward/reverse measurements differ; "
                    "fixture/contact-condition review may be useful."
                )
        rows.append(
            PerDpiMotionRow(
                configured_dpi=dpi,
                trial_count=len(group),
                axis_orientation_deg=round(axis, 1) if axis is not None else None,
                axis_spread_deg=round(spread, 1) if spread is not None else None,
                forward_trials=fwd_n,
                reverse_trials=rev_n,
                forward_avg_measured_cpi=round(fwd_avg, 2) if fwd_avg is not None else None,
                reverse_avg_measured_cpi=round(rev_avg, 2) if rev_avg is not None else None,
                forward_avg_error_pct=round(_mean(fwd_err), 4) if fwd_err else None,
                reverse_avg_error_pct=round(_mean(rev_err), 4) if rev_err else None,
                forward_reverse_mean_cpi_diff_pct=(
                    round(diff_pct, 4) if diff_pct is not None else None
                ),
                directional_asymmetry_note=note,
                avg_straightness_pct=round(avg_st, 2) if avg_st is not None else None,
                straightness_at_ceiling=ceiling,
                path_excess_state=pe_state,
            )
        )
    return tuple(rows)


def build_fixture_motion_diagnostics(
    trials: Sequence[Mapping[str, Any]],
) -> FixtureMotionDiagnostics:
    """Aggregate descriptive diagnostics for Active Fixture Vector trials."""
    fixture = [t for t in trials if _is_fixture_vector(t)]
    missing: list[str] = []
    notes: list[str] = []

    empty = FixtureMotionDiagnostics(
        trial_count=0,
        trials_with_straightness=0,
        trials_with_path_excess=0,
        trials_with_heading=0,
        avg_straightness_pct=None,
        min_straightness_pct=None,
        straightness_at_ceiling=False,
        max_path_excess_pct=None,
        path_excess_state="—",
        axis_orientation_deg=None,
        axis_spread_deg=None,
        forward_trials=0,
        reverse_trials=0,
        per_dpi=(),
        missing_fields=("no_fixture_vector_trials",),
        notes=("No Active Fixture Vector trials — diagnostics unavailable.",),
    )
    if not fixture:
        return empty

    straightness: list[float] = []
    excesses: list[float] = []
    excess_unevaluable = 0
    headings = _headings_from_trials(fixture)

    for t in fixture:
        st = t.get("straightness_pct")
        if st is not None:
            try:
                straightness.append(float(st))
            except (TypeError, ValueError):
                pass
        val, state = path_excess_result(t.get("path_total_counts"), t.get("vector_counts"))
        if state == "ok" and val is not None:
            excesses.append(val)
        elif state == PATH_EXCESS_NOT_EVALUATED:
            excess_unevaluable += 1

    if not straightness:
        missing.append("straightness_pct")
    if not excesses and excess_unevaluable == 0:
        missing.append("path_total_counts+vector_counts")
    if not headings:
        missing.append("counts_x+counts_y")

    notes.append("Descriptive diagnostics only — no fixture/sensor verdict.")
    notes.append(
        "Fixture Vector orientation is axial (mod 180°): opposite travel polarity "
        "on the same fixture does not inflate axis-orientation spread."
    )
    notes.append(
        "Absolute axis orientation is not a quality score; small spread means "
        "consistent travel orientation, not perfect fixture straightness."
    )
    notes.append(
        "Straightness uses the Path Quality formula (capped at 100%). "
        "100% is a metric ceiling — not proof of perfect physical geometry."
    )
    if excess_unevaluable:
        notes.append(
            "Path excess is NOT_EVALUATED when path_total < vector_counts "
            "(noise-floor exclusion). Do not treat that as zero detour."
        )

    avg_st = sum(straightness) / len(straightness) if straightness else None
    min_st = min(straightness) if straightness else None
    ceiling = bool(straightness) and min(straightness) >= 100.0 - 1e-9
    if excess_unevaluable and not excesses:
        pe_state = PATH_EXCESS_NOT_EVALUATED
        max_ex = None
    elif excesses:
        pe_state = "ok"
        max_ex = max(excesses)
    else:
        pe_state = "—"
        max_ex = None

    axis = axial_mean_deg(headings)
    spread = axial_spread_deg(headings)
    fwd, rev = _polarity_counts(headings, axis)

    return FixtureMotionDiagnostics(
        trial_count=len(fixture),
        trials_with_straightness=len(straightness),
        trials_with_path_excess=len(excesses),
        trials_with_heading=len(headings),
        avg_straightness_pct=round(avg_st, 2) if avg_st is not None else None,
        min_straightness_pct=round(min_st, 2) if min_st is not None else None,
        straightness_at_ceiling=ceiling,
        max_path_excess_pct=round(max_ex, 2) if max_ex is not None else None,
        path_excess_state=pe_state,
        axis_orientation_deg=round(axis, 1) if axis is not None else None,
        axis_spread_deg=round(spread, 1) if spread is not None else None,
        forward_trials=fwd,
        reverse_trials=rev,
        per_dpi=_per_dpi_rows(fixture),
        missing_fields=tuple(missing),
        notes=tuple(notes),
    )


def format_fixture_motion_lines(
    diag: FixtureMotionDiagnostics,
    *,
    t: Any | None = None,
) -> list[str]:
    """Human-facing lines for Technical Details (presentation only)."""

    def _t(key: str, fallback: str) -> str:
        if t is None:
            return fallback
        text = t(key)
        return fallback if text == key else text

    if diag.trial_count <= 0:
        return [_t("fixture.diag.none", "Fixture / Motion Diagnostics: no Fixture Vector trials.")]

    lines = [
        _t("fixture.diag.title", "Fixture / Motion Diagnostics"),
        _t(
            "fixture.diag.disclaimer",
            "Descriptive diagnostics only — no fixture/sensor verdict.",
        ),
    ]
    if diag.avg_straightness_pct is not None:
        key = (
            "fixture.diag.avg_straightness_ceiling"
            if diag.straightness_at_ceiling
            else "fixture.diag.avg_straightness"
        )
        fb = (
            "Average straightness: {value}% (metric ceiling)"
            if diag.straightness_at_ceiling
            else "Average straightness: {value}%"
        )
        lines.append(_t(key, fb).format(value=f"{diag.avg_straightness_pct:.2f}"))
    if diag.min_straightness_pct is not None:
        key = (
            "fixture.diag.min_straightness_ceiling"
            if diag.straightness_at_ceiling
            else "fixture.diag.min_straightness"
        )
        fb = (
            "Minimum straightness: {value}% (metric ceiling)"
            if diag.straightness_at_ceiling
            else "Minimum straightness: {value}%"
        )
        lines.append(_t(key, fb).format(value=f"{diag.min_straightness_pct:.2f}"))
    if diag.path_excess_state == PATH_EXCESS_NOT_EVALUATED:
        lines.append(
            _t(
                "fixture.diag.path_excess_ne",
                "Path excess: NOT_EVALUATED (path_total < vector under noise-floor semantics)",
            )
        )
    elif diag.max_path_excess_pct is not None:
        lines.append(
            _t("fixture.diag.max_path_excess", "Maximum path excess: {value}%").format(
                value=f"{diag.max_path_excess_pct:.2f}"
            )
        )
    if diag.axis_orientation_deg is not None:
        lines.append(
            _t(
                "fixture.diag.axis_orientation",
                "Fixture axis orientation: {value}°",
            ).format(value=f"{diag.axis_orientation_deg:.1f}")
        )
    if diag.axis_spread_deg is not None:
        lines.append(
            _t(
                "fixture.diag.axis_spread",
                "Axis-orientation spread: {value}°",
            ).format(value=f"{diag.axis_spread_deg:.1f}")
        )
        lines.append(
            _t(
                "fixture.diag.axis_note",
                "Axis orientation is axial (mod 180°). Absolute angle is not a quality score; "
                "opposite travel polarity does not inflate spread.",
            )
        )
    if diag.forward_trials or diag.reverse_trials:
        lines.append(
            _t(
                "fixture.diag.polarity",
                "Travel polarity — forward: {forward} · reverse: {reverse} (descriptive only).",
            ).format(forward=diag.forward_trials, reverse=diag.reverse_trials)
        )
    if diag.per_dpi:
        lines.append(_t("fixture.diag.per_dpi_title", "Per-DPI motion consistency (descriptive):"))
        lines.append(
            _t(
                "fixture.diag.per_dpi_header",
                "DPI | Trials | Axis | Spread | Fwd/Rev | Fwd CPI | Rev CPI | |ΔCPI|% | Straight | Excess",
            )
        )
        for row in diag.per_dpi:
            st = (
                f"{row.avg_straightness_pct:.2f}%*"
                if row.straightness_at_ceiling and row.avg_straightness_pct is not None
                else (
                    f"{row.avg_straightness_pct:.2f}%"
                    if row.avg_straightness_pct is not None
                    else "—"
                )
            )
            ao = (
                f"{row.axis_orientation_deg:.1f}°"
                if row.axis_orientation_deg is not None
                else "—"
            )
            asp = f"{row.axis_spread_deg:.1f}°" if row.axis_spread_deg is not None else "—"
            dpi_txt = (
                str(int(row.configured_dpi))
                if float(row.configured_dpi).is_integer()
                else f"{row.configured_dpi:g}"
            )
            fc = (
                f"{row.forward_avg_measured_cpi:.1f}"
                if row.forward_avg_measured_cpi is not None
                else "—"
            )
            rc = (
                f"{row.reverse_avg_measured_cpi:.1f}"
                if row.reverse_avg_measured_cpi is not None
                else "—"
            )
            dd = (
                f"{row.forward_reverse_mean_cpi_diff_pct:.2f}"
                if row.forward_reverse_mean_cpi_diff_pct is not None
                else "—"
            )
            lines.append(
                f"{dpi_txt} | {row.trial_count} | {ao} | {asp} | "
                f"{row.forward_trials}/{row.reverse_trials} | {fc} | {rc} | {dd} | "
                f"{st} | {row.path_excess_state}"
            )
            if row.directional_asymmetry_note:
                lines.append(f"  · {row.directional_asymmetry_note}")
        if any(r.straightness_at_ceiling for r in diag.per_dpi):
            lines.append(
                _t(
                    "fixture.diag.ceiling_footnote",
                    "* straightness at Path Quality metric ceiling (≤100%)",
                )
            )
        if any(r.directional_asymmetry_note for r in diag.per_dpi):
            lines.append(
                _t(
                    "fixture.diag.asymmetry_disclaimer",
                    "Directional asymmetry is descriptive only — not a fixture-drag or "
                    "mechanical-defect Finding.",
                )
            )
    if diag.missing_fields and not diag.available:
        lines.append(
            _t(
                "fixture.diag.missing",
                "Insufficient canonical evidence: {fields}",
            ).format(fields=", ".join(diag.missing_fields))
        )
    return lines
