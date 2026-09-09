"""V1 DPI Behavior Trends — SVG rendering from shared ChartCardModel."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from mouse_dpi_tool.reporting.chart_cards import (
    ChartCardModel,
    build_v1_chart_cards,
    format_observation_en,
)
from mouse_dpi_tool.reporting.trends_points import group_trend_points
from mouse_dpi_tool.ui.help_content import CHART_CUES_EN

# Re-export for callers that imported group_trend_points from trends.
__all__ = [
    "group_trend_points",
    "render_v1_trend_svgs",
    "render_chart_card_svg",
]


def _svg_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _nice_ticks(lo: float, hi: float, count: int = 4) -> list[float]:
    if hi <= lo:
        return [lo]
    span = hi - lo
    step = span / max(1, count)
    exp = math.floor(math.log10(step)) if step > 0 else 0
    base = step / (10**exp)
    if base <= 1:
        nice = 1.0
    elif base <= 2:
        nice = 2.0
    elif base <= 5:
        nice = 5.0
    else:
        nice = 10.0
    step = nice * (10**exp)
    start = math.floor(lo / step) * step
    ticks: list[float] = []
    v = start
    while v <= hi + step * 0.01:
        if v >= lo - step * 0.01:
            ticks.append(v)
        v += step
        if len(ticks) > 12:
            break
    return ticks or [lo, hi]


def render_chart_card_svg(card: ChartCardModel, *, width: int = 720, height: int = 320) -> str:
    """Self-contained SVG for one engineering chart card (print/HTML)."""
    pad_l, pad_r, pad_t, pad_b = 64, 28, 72, 56
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    points = card.as_xy()
    if not points:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">'
            f'<rect width="100%" height="100%" fill="#ffffff"/>'
            f'<text x="{width // 2}" y="{height // 2}" text-anchor="middle" '
            f'fill="#6e6e73" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="13">'
            f"No group data</text></svg>"
        )

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    if card.ideal_points:
        ys = ys + [p.value for p in card.ideal_points]
        xs = xs + [p.configured_dpi for p in card.ideal_points]
    if card.thresholds is not None:
        ys = ys + [card.thresholds.pass_pct, card.thresholds.fail_pct, 0.0]

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    if x_max <= x_min:
        x_max = x_min + 1.0
    if y_max <= y_min:
        y_max = y_min + 1.0
    x_pad = (x_max - x_min) * 0.05
    y_pad = (y_max - y_min) * 0.10
    x_min -= x_pad
    x_max += x_pad
    y_min = min(0.0, y_min - y_pad) if card.thresholds else y_min - y_pad
    y_max += y_pad

    def sx(x: float) -> float:
        return pad_l + (x - x_min) / (x_max - x_min) * plot_w

    def sy(y: float) -> float:
        return pad_t + (1.0 - (y - y_min) / (y_max - y_min)) * plot_h

    layers: list[str] = []
    # Y-axis numeric ticks (from chart numeric values only — not pixel evidence).
    for tick in _nice_ticks(y_min, y_max, count=4):
        yy = sy(tick)
        if yy < pad_t - 1 or yy > pad_t + plot_h + 1:
            continue
        layers.append(
            f'<line x1="{pad_l}" y1="{yy:.2f}" x2="{pad_l + plot_w}" y2="{yy:.2f}" '
            f'stroke="#d2d2d7" stroke-width="1" stroke-dasharray="2 3"/>'
        )
        label = f"{tick:.0f}" if abs(tick) >= 10 else f"{tick:.2g}"
        layers.append(
            f'<text x="{pad_l - 6}" y="{yy + 3:.2f}" text-anchor="end" '
            f'fill="#6e6e73" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="10">'
            f"{_svg_escape(label)}</text>"
        )

    # Subtle WARN band between pass and fail when thresholds exist.
    if card.thresholds is not None:
        y_pass = card.thresholds.pass_pct
        y_fail = card.thresholds.fail_pct
        y0 = sy(max(y_pass, y_min))
        y1 = sy(min(y_fail, y_max))
        top, bot = min(y0, y1), max(y0, y1)
        layers.append(
            f'<rect x="{pad_l}" y="{top:.2f}" width="{plot_w}" height="{max(0.0, bot - top):.2f}" '
            f'fill="#FFD60A" fill-opacity="0.08"/>'
        )
        layers.append(
            f'<line x1="{pad_l}" y1="{sy(y_pass):.2f}" x2="{pad_l + plot_w}" y2="{sy(y_pass):.2f}" '
            f'stroke="#1F8F4E" stroke-width="1.2" stroke-dasharray="4 3"/>'
        )
        layers.append(
            f'<line x1="{pad_l}" y1="{sy(y_fail):.2f}" x2="{pad_l + plot_w}" y2="{sy(y_fail):.2f}" '
            f'stroke="#C9342D" stroke-width="1.2" stroke-dasharray="4 3"/>'
        )
        layers.append(
            f'<text x="{pad_l + 4}" y="{sy(y_pass) - 4:.2f}" text-anchor="start" '
            f'fill="#1F8F4E" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="10">'
            f"PASS ≤ {card.thresholds.pass_pct:g}%</text>"
        )
        mid = (y_pass + y_fail) / 2
        layers.append(
            f'<text x="{pad_l + 4}" y="{sy(mid) + 3:.2f}" text-anchor="start" '
            f'fill="#B26A00" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="10">'
            f"WARN {card.thresholds.pass_pct:g}–{card.thresholds.fail_pct:g}%</text>"
        )
        layers.append(
            f'<text x="{pad_l + 4}" y="{sy(y_fail) - 4:.2f}" text-anchor="start" '
            f'fill="#C9342D" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="10">'
            f"FAIL > {card.thresholds.fail_pct:g}%</text>"
        )

    if card.ideal_points:
        ideal_xy = card.ideal_as_xy()
        # Draw ideal as y=x across numeric domain of configured DPI.
        lo = min(p[0] for p in ideal_xy)
        hi = max(p[0] for p in ideal_xy)
        layers.append(
            f'<line x1="{sx(lo):.2f}" y1="{sy(lo):.2f}" x2="{sx(hi):.2f}" y2="{sy(hi):.2f}" '
            f'stroke="#8E8E93" stroke-width="1.6" stroke-dasharray="6 4"/>'
        )

    poly = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in points)
    layers.append(f'<polyline fill="none" stroke="#0071E3" stroke-width="2.5" points="{poly}"/>')
    layers.append(
        "".join(
            f'<circle cx="{sx(x):.2f}" cy="{sy(y):.2f}" r="4" fill="#0071E3"/>' for x, y in points
        )
    )

    # Numeric tick labels on x (configured DPI values).
    x_ticks = "".join(
        f'<text x="{sx(x):.2f}" y="{pad_t + plot_h + 16:.2f}" text-anchor="middle" '
        f'fill="#6e6e73" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="10">'
        f"{int(x) if float(x).is_integer() else x}</text>"
        for x, _ in points
    )

    legend = " · ".join(card.legend_en)
    obs = format_observation_en(card.observation)
    cue = CHART_CUES_EN.get(card.chart_id, "")
    note = card.metric_note_en or ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="#ffffff"/>
<text x="{pad_l}" y="22" fill="#1d1d1f" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="15" font-weight="600">{_svg_escape(card.title_en)}</text>
<text x="{pad_l}" y="42" fill="#6e6e73" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="11">{_svg_escape(cue[:140] if cue else card.caption_en[:120])}{"…" if len(cue or card.caption_en) > 140 else ""}</text>
<rect x="{pad_l}" y="{pad_t}" width="{plot_w}" height="{plot_h}" fill="#f5f5f7" stroke="#d2d2d7"/>
{''.join(layers)}
{x_ticks}
<text x="{width // 2}" y="{height - 14}" text-anchor="middle" fill="#6e6e73" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="11">{_svg_escape(card.x_label_en)}</text>
<text x="16" y="{pad_t + plot_h / 2}" text-anchor="middle" fill="#6e6e73" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="11" transform="rotate(-90 16 {pad_t + plot_h / 2})">{_svg_escape(card.y_label_en)}</text>
<text x="{pad_l}" y="{height - 28}" fill="#6e6e73" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="10">{_svg_escape(legend)}</text>
</svg>
<!-- observation: {_svg_escape(obs)} -->
<!-- metric_note: {_svg_escape(note)} -->
"""


def render_v1_trend_svgs(
    group_summaries: Sequence[Mapping[str, Any]],
    settings: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    settings = dict(settings or {})
    cards = build_v1_chart_cards(group_summaries, settings)
    return {
        "measured_cpi": render_chart_card_svg(cards["measured_cpi"]),
        "max_error": render_chart_card_svg(cards["max_error"]),
        "repeatability": render_chart_card_svg(cards["repeatability"]),
        # Backward-compatible aliases used by older callers/tests.
        "measured_vs_configured": render_chart_card_svg(cards["measured_cpi"]),
        "error_vs_dpi": render_chart_card_svg(cards["max_error"]),
        "cv_vs_dpi": render_chart_card_svg(cards["repeatability"]),
    }


def render_v1_trend_svgs(
    group_summaries: Sequence[Mapping[str, Any]],
    settings: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    settings = dict(settings or {})
    cards = build_v1_chart_cards(group_summaries, settings)
    return {
        "measured_cpi": render_chart_card_svg(cards["measured_cpi"]),
        "max_error": render_chart_card_svg(cards["max_error"]),
        "repeatability": render_chart_card_svg(cards["repeatability"]),
        # Backward-compatible aliases used by older callers/tests.
        "measured_vs_configured": render_chart_card_svg(cards["measured_cpi"]),
        "error_vs_dpi": render_chart_card_svg(cards["max_error"]),
        "cv_vs_dpi": render_chart_card_svg(cards["repeatability"]),
    }
