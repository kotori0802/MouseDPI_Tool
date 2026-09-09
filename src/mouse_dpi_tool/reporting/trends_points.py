"""Numeric group trend points — shared by chart cards and legacy imports."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def group_trend_points(group_summaries: Sequence[Mapping[str, Any]]) -> list[dict[str, float | None]]:
    """Stable series keyed by configured DPI (numeric ascending)."""
    rows: list[dict[str, float | None]] = []
    for g in group_summaries:
        try:
            dpi = float(g.get("configured_dpi"))
        except (TypeError, ValueError):
            continue
        avg = g.get("avg_measured_cpi")
        err = g.get("max_abs_error_pct")
        cv = g.get("cpi_cv_pct")
        rows.append(
            {
                "configured_dpi": dpi,
                "avg_measured_cpi": float(avg) if avg is not None else None,
                "max_abs_error_pct": float(err) if err is not None else None,
                "cpi_cv_pct": float(cv) if cv is not None else None,
            }
        )
    rows.sort(key=lambda r: float(r["configured_dpi"] or 0.0))
    return rows
