"""SVG helpers for Trial engineering diagnostics (HTML report; Qt-free)."""

from __future__ import annotations

from typing import Sequence

from mouse_dpi_tool.reporting.trial_diagnostics import (
    DpiErrorDistribution,
    SpeedErrorPoint,
    TrialSequencePoint,
)


def _esc(text: object) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_trial_sequence_svg(
    points: Sequence[TrialSequencePoint],
    *,
    width: int = 720,
    height: int = 280,
) -> str:
    if not points:
        return _empty(width, height, "No trial sequence data")
    xs = [p.report_trial_no for p in points]
    ys = [p.error_pct for p in points]
    return _scatter_svg(
        list(zip(xs, ys, [str(int(p.configured_dpi)) for p in points])),
        width=width,
        height=height,
        title="Trial CPI Error over Test Sequence",
        xlabel="Trial #",
        ylabel="CPI error %",
    )


def render_error_distribution_svg(
    rows: Sequence[DpiErrorDistribution],
    *,
    width: int = 720,
    height: int = 280,
) -> str:
    if not rows:
        return _empty(width, height, "No distribution data")
    # Represent as median + min/max whiskers per DPI (lightweight).
    pad_l, pad_r, pad_t, pad_b = 56, 20, 40, 48
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    all_y: list[float] = []
    for r in rows:
        for v in (r.min_error_pct, r.median_error_pct, r.max_error_pct, r.q1_error_pct, r.q3_error_pct):
            if v is not None:
                all_y.append(float(v))
    ymin, ymax = min(all_y), max(all_y)
    if abs(ymax - ymin) < 1e-9:
        ymax = ymin + 1
    ypad = (ymax - ymin) * 0.1
    ymin -= ypad
    ymax += ypad
    n = len(rows)
    slot = plot_w / max(1, n)

    def my(y: float) -> float:
        return pad_t + plot_h - ((y - ymin) / (ymax - ymin)) * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width // 2}" y="22" text-anchor="middle" font-size="14" fill="#1d1d1f" '
        f'font-family="Segoe UI, Helvetica, Arial, sans-serif">CPI Error Distribution by DPI</text>',
        f'<rect x="{pad_l}" y="{pad_t}" width="{plot_w}" height="{plot_h}" '
        f'fill="none" stroke="#d2d2d7"/>',
    ]
    if ymin <= 0 <= ymax:
        parts.append(
            f'<line x1="{pad_l}" y1="{my(0):.1f}" x2="{pad_l + plot_w}" y2="{my(0):.1f}" '
            f'stroke="#d2d2d7" stroke-dasharray="4 3"/>'
        )
    for i, r in enumerate(rows):
        cx = pad_l + (i + 0.5) * slot
        if r.min_error_pct is not None and r.max_error_pct is not None:
            parts.append(
                f'<line x1="{cx:.1f}" y1="{my(r.min_error_pct):.1f}" x2="{cx:.1f}" '
                f'y2="{my(r.max_error_pct):.1f}" stroke="#0071e3" stroke-width="1.5"/>'
            )
        if r.q1_error_pct is not None and r.q3_error_pct is not None:
            top, bot = my(r.q3_error_pct), my(r.q1_error_pct)
            parts.append(
                f'<rect x="{cx - 12:.1f}" y="{min(top, bot):.1f}" width="24" '
                f'height="{abs(bot - top):.1f}" fill="#0071e333" stroke="#0071e3"/>'
            )
        if r.median_error_pct is not None:
            yy = my(r.median_error_pct)
            parts.append(
                f'<line x1="{cx - 12:.1f}" y1="{yy:.1f}" x2="{cx + 12:.1f}" y2="{yy:.1f}" '
                f'stroke="#1d1d1f" stroke-width="2"/>'
            )
        label = str(int(r.configured_dpi)) if float(r.configured_dpi).is_integer() else f"{r.configured_dpi:g}"
        parts.append(
            f'<text x="{cx:.1f}" y="{height - 18}" text-anchor="middle" font-size="11" '
            f'fill="#6e6e73">{_esc(label)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def render_speed_error_svg(
    points: Sequence[SpeedErrorPoint],
    *,
    width: int = 720,
    height: int = 280,
) -> str:
    if not points:
        return _empty(width, height, "Motion timing evidence not available")
    return _scatter_svg(
        [(p.speed_mm_s, p.error_pct, str(int(p.configured_dpi))) for p in points],
        width=width,
        height=height,
        title="CPI Error vs Estimated Traversal Speed",
        xlabel="Estimated traversal speed (mm/s)",
        ylabel="CPI error %",
    )


def _empty(width: int, height: int, msg: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" fill="#ffffff"/>'
        f'<text x="{width // 2}" y="{height // 2}" text-anchor="middle" fill="#6e6e73" '
        f'font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="13">{_esc(msg)}</text></svg>'
    )


def _scatter_svg(
    points: list[tuple[float, float, str]],
    *,
    width: int,
    height: int,
    title: str,
    xlabel: str,
    ylabel: str,
) -> str:
    pad_l, pad_r, pad_t, pad_b = 56, 20, 40, 48
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    xs = [a for a, _, _ in points]
    ys = [b for _, b, _ in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if abs(xmax - xmin) < 1e-9:
        xmax = xmin + 1
    if abs(ymax - ymin) < 1e-9:
        ymax = ymin + 1
    ypad = (ymax - ymin) * 0.08
    ymin -= ypad
    ymax += ypad

    def mx(x: float) -> float:
        return pad_l + ((x - xmin) / (xmax - xmin)) * plot_w

    def my(y: float) -> float:
        return pad_t + plot_h - ((y - ymin) / (ymax - ymin)) * plot_h

    colors = ["#0071e3", "#34c759", "#ff9f0a", "#af52de", "#ff375f"]
    cmap: dict[str, str] = {}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width // 2}" y="22" text-anchor="middle" font-size="14" fill="#1d1d1f" '
        f'font-family="Segoe UI, Helvetica, Arial, sans-serif">{_esc(title)}</text>',
        f'<rect x="{pad_l}" y="{pad_t}" width="{plot_w}" height="{plot_h}" '
        f'fill="none" stroke="#d2d2d7"/>',
        f'<text x="{width // 2}" y="{height - 12}" text-anchor="middle" font-size="11" '
        f'fill="#6e6e73">{_esc(xlabel)}</text>',
    ]
    if ymin <= 0 <= ymax:
        parts.append(
            f'<line x1="{pad_l}" y1="{my(0):.1f}" x2="{pad_l + plot_w}" y2="{my(0):.1f}" '
            f'stroke="#d2d2d7" stroke-dasharray="4 3"/>'
        )
    for x, y, lab in points:
        if lab not in cmap:
            cmap[lab] = colors[len(cmap) % len(colors)]
        parts.append(
            f'<circle cx="{mx(x):.1f}" cy="{my(y):.1f}" r="3.2" fill="{cmap[lab]}"/>'
        )
    parts.append("</svg>")
    return "".join(parts)
