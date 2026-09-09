"""Cross-DPI Scale Pattern — descriptive reporting helper (not a Finding).

Uses canonical group_summaries only (avg_measured_cpi / configured_dpi).
Never reads Qt widgets, PathCanvas, or invents root-cause verdicts.

Pattern intent:
- Separate absolute/common scale offset from relative DPI-step scaling.
- Do NOT claim fixture calibration failure, sensor CPI offset, or auto distance.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

# Absolute span of scale factors (max − min) under which same-side offsets
# are described as a near-common scale pattern (presentation threshold only).
COMMON_SCALE_SPREAD_MAX = 0.025


@dataclass(frozen=True)
class CrossDpiScalePattern:
    """Descriptive cross-DPI scale summary — never a Finding status."""

    group_count: int
    scale_factors: tuple[float, ...]
    min_scale: float | None
    max_scale: float | None
    mean_scale: float | None
    median_scale: float | None
    spread: float | None
    min_deviation_pct: float | None
    max_deviation_pct: float | None
    pattern_id: str  # common_scale_offset | mixed_or_nonuniform | insufficient
    notes: tuple[str, ...]

    @property
    def available(self) -> bool:
        return self.group_count > 0 and self.mean_scale is not None


def _group_scale(group: Mapping[str, Any]) -> float | None:
    try:
        configured = float(group.get("configured_dpi"))
        avg = float(group.get("avg_measured_cpi"))
    except (TypeError, ValueError):
        return None
    if configured <= 0:
        return None
    return avg / configured


def build_cross_dpi_scale_pattern(
    group_summaries: Sequence[Mapping[str, Any]],
) -> CrossDpiScalePattern:
    """Derive Cross-DPI Scale Pattern from canonical group summaries only."""
    factors: list[float] = []
    for g in group_summaries:
        sf = _group_scale(g)
        if sf is not None:
            factors.append(sf)

    empty_notes = (
        "Descriptive only — not a Finding and not a root-cause verdict.",
    )
    if len(factors) < 2:
        return CrossDpiScalePattern(
            group_count=len(factors),
            scale_factors=tuple(factors),
            min_scale=round(factors[0], 6) if factors else None,
            max_scale=round(factors[0], 6) if factors else None,
            mean_scale=round(factors[0], 6) if factors else None,
            median_scale=round(factors[0], 6) if factors else None,
            spread=0.0 if factors else None,
            min_deviation_pct=round((factors[0] - 1.0) * 100.0, 4) if factors else None,
            max_deviation_pct=round((factors[0] - 1.0) * 100.0, 4) if factors else None,
            pattern_id="insufficient",
            notes=empty_notes + ("Need at least two DPI groups for a cross-DPI scale pattern.",),
        )

    mn = min(factors)
    mx = max(factors)
    mean = statistics.fmean(factors)
    med = float(statistics.median(factors))
    spread = mx - mn
    all_below = all(f < 1.0 for f in factors)
    all_above = all(f > 1.0 for f in factors)
    same_side = all_below or all_above
    common = same_side and spread <= COMMON_SCALE_SPREAD_MAX

    notes = [
        "Descriptive only — not a Finding and not a root-cause verdict.",
        "Does not select among distance, fixture geometry, product CPI offset, "
        "or other common measurement/product effects.",
        "Never auto-corrects configured distance.",
    ]
    if common:
        pattern_id = "common_scale_offset"
        notes.append(
            "Session shows a near-common scale-offset pattern across evaluated DPI groups."
        )
    else:
        pattern_id = "mixed_or_nonuniform"
        notes.append(
            "Scale factors are mixed or nonuniform across DPI groups — "
            "not described as a common-scale-offset pattern."
        )

    return CrossDpiScalePattern(
        group_count=len(factors),
        scale_factors=tuple(round(f, 6) for f in factors),
        min_scale=round(mn, 6),
        max_scale=round(mx, 6),
        mean_scale=round(mean, 6),
        median_scale=round(med, 6),
        spread=round(spread, 6),
        min_deviation_pct=round((mn - 1.0) * 100.0, 4),
        max_deviation_pct=round((mx - 1.0) * 100.0, 4),
        pattern_id=pattern_id,
        notes=tuple(notes),
    )


def ratio_context_from_pairs(
    ratio_analysis: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Optional relative-scaling context from canonical ratio_analysis rows."""
    pairs = list(ratio_analysis or [])
    if not pairs:
        return {"pair_count": 0, "max_abs_ratio_error_pct": None, "all_pass": False}
    errs: list[float] = []
    statuses: list[str] = []
    for row in pairs:
        try:
            if row.get("ratio_error_pct") is not None:
                errs.append(abs(float(row["ratio_error_pct"])))
        except (TypeError, ValueError):
            pass
        statuses.append(str(row.get("status") or ""))
    max_err = max(errs) if errs else None
    return {
        "pair_count": len(pairs),
        "max_abs_ratio_error_pct": round(max_err, 4) if max_err is not None else None,
        "all_pass": bool(statuses) and all(s == "PASS" for s in statuses),
    }


def format_cross_dpi_scale_lines(
    pattern: CrossDpiScalePattern,
    *,
    ratio_ctx: Mapping[str, Any] | None = None,
    t: Any | None = None,
) -> list[str]:
    """Human-facing lines for Results / HTML (presentation only)."""

    def _t(key: str, fallback: str) -> str:
        if t is None:
            return fallback
        text = t(key)
        return fallback if text == key else text

    lines = [
        _t("scale.pattern.title", "Cross-DPI Scale Pattern"),
        _t(
            "scale.pattern.disclaimer",
            "Descriptive diagnostic only — not a Finding; no automatic root cause.",
        ),
    ]
    if pattern.group_count <= 0 or pattern.mean_scale is None:
        lines.append(
            _t("scale.pattern.none", "Insufficient DPI-group means for a scale pattern.")
        )
        return lines

    lines.append(
        _t("scale.pattern.groups", "Evaluated DPI groups: {n}").format(n=pattern.group_count)
    )
    lines.append(
        _t(
            "scale.pattern.scale_range",
            "Normalized scale (avg CPI / configured): {min_s} – {max_s} "
            "(mean {mean_s}, median {med_s}, spread {spread})",
        ).format(
            min_s=f"{pattern.min_scale:.4f}",
            max_s=f"{pattern.max_scale:.4f}",
            mean_s=f"{pattern.mean_scale:.4f}",
            med_s=f"{pattern.median_scale:.4f}",
            spread=f"{pattern.spread:.4f}",
        )
    )
    if pattern.min_deviation_pct is not None and pattern.max_deviation_pct is not None:
        lo = min(pattern.min_deviation_pct, pattern.max_deviation_pct)
        hi = max(pattern.min_deviation_pct, pattern.max_deviation_pct)
        lines.append(
            _t(
                "scale.pattern.dev_range",
                "Group-average deviation from configured: approximately {lo:+.2f}% to {hi:+.2f}%.",
            ).format(lo=lo, hi=hi)
        )

    ctx = dict(ratio_ctx or {})
    if pattern.pattern_id == "common_scale_offset":
        if ctx.get("all_pass") and ctx.get("max_abs_ratio_error_pct") is not None:
            lines.append(
                _t(
                    "scale.pattern.common_with_ratio",
                    "All evaluated DPI-group means share a near-common offset from configured "
                    "values, while adjacent measured DPI ratios remain close to their configured "
                    "ratios (max |ratio error| {err}%). "
                    "This warrants measurement-system or product calibration review — "
                    "not an automatic fixture or sensor verdict.",
                ).format(err=f"{float(ctx['max_abs_ratio_error_pct']):.4f}")
            )
        else:
            lines.append(
                _t(
                    "scale.pattern.common",
                    "All evaluated DPI-group means share a near-common offset from configured "
                    "values. This warrants measurement-system or product calibration review — "
                    "not an automatic fixture or sensor verdict.",
                )
            )
    elif pattern.pattern_id == "mixed_or_nonuniform":
        lines.append(
            _t(
                "scale.pattern.mixed",
                "Scale factors differ materially across DPI groups (or signs mix). "
                "Not described as a common-scale-offset pattern.",
            )
        )

    lines.append(
        _t(
            "scale.pattern.no_root_cause",
            "Possible contributors include travel-distance definition, fixture geometry/preload, "
            "start/end references, product-wide CPI offset, or other common effects. "
            "The Tool does not choose among them.",
        )
    )
    return lines


def format_cross_dpi_scale_paragraph_en(
    pattern: CrossDpiScalePattern,
    *,
    ratio_ctx: Mapping[str, Any] | None = None,
) -> str:
    """Single English paragraph for HTML reports (Session-derived values)."""
    return " ".join(format_cross_dpi_scale_lines(pattern, ratio_ctx=ratio_ctx, t=None))
