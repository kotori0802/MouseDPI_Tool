"""Self-contained HTML Test Report — Session snapshot only (never Qt widgets)."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from mouse_dpi_tool.reporting.chart_cards import (
    build_v1_chart_cards,
    finding_metric_rows,
    format_observation_en,
)
from mouse_dpi_tool.reporting.trends import render_v1_trend_svgs
from mouse_dpi_tool.reporting.scale_pattern import (
    build_cross_dpi_scale_pattern,
    format_cross_dpi_scale_paragraph_en,
    ratio_context_from_pairs,
)
from mouse_dpi_tool.reporting.trial_diagnostics import (
    build_dpi_error_distributions,
    build_speed_correlations,
    build_speed_error_points,
    build_trial_sequence_points,
    session_has_motion_timing,
)
from mouse_dpi_tool.reporting.trial_diagnostics_svg import (
    render_error_distribution_svg,
    render_speed_error_svg,
    render_trial_sequence_svg,
)
from mouse_dpi_tool.ui.help_content import (
    CHART_CUES_EN,
    FINDING_HELP_EN,
    REPORT_INTERPRETATION_BODY_EN,
    REPORT_INTERPRETATION_TITLE_EN,
    RESEARCH_HELP_EN,
)


_V1_FINDINGS = ("accuracy", "repeatability", "path_quality", "ratio")
_RESEARCH = ("linearity", "scaling_evidence", "native_capability")


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _fmt_num(value: object, *, digits: int = 2) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return _esc(value)


def accuracy_criterion_lines(settings: Mapping[str, Any]) -> list[str]:
    """Exact PASS / WARN / FAIL bands for operator + report."""
    try:
        pass_pct = float(settings.get("cpi_error_pass_pct") or 0.0)
        fail_pct = float(settings.get("cpi_error_fail_pct") or 0.0)
    except (TypeError, ValueError):
        return ["Accuracy criterion unavailable"]
    mode = str(settings.get("tolerance_mode") or "")
    return [
        f"Mode: {mode}" if mode else "Mode: —",
        f"PASS ≤ {pass_pct:g}%",
        f"WARN > {pass_pct:g}% – {fail_pct:g}%",
        f"FAIL > {fail_pct:g}%",
    ]


_FINDING_TITLES = {
    "accuracy": "Accuracy",
    "repeatability": "Repeatability",
    "ratio": "Relative DPI Scaling",
    "path_quality": "Path Quality",
    "linearity": "Linearity",
    "scaling_evidence": "Scaling evidence",
    "native_capability": "Native capability",
}


def render_html_report(session: Mapping[str, Any], *, generated_at: str | None = None) -> str:
    """Build a print-friendly, self-contained HTML document from a Session mapping."""
    generated = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    settings = dict(session.get("settings") or {})
    dut = dict(session.get("dut") or {})
    metrics = dict(session.get("metrics") or {})
    findings = dict(session.get("findings") or {})
    groups: Sequence[Mapping[str, Any]] = list(session.get("group_summaries") or [])
    ratios: Sequence[Mapping[str, Any]] = list(session.get("ratio_analysis") or [])
    trials: Sequence[Mapping[str, Any]] = list(session.get("trials") or [])
    rejected = list(session.get("rejected_trials") or [])
    deleted = list(session.get("deleted_trials") or [])
    manuals = list(session.get("findings", {}).get("manual_observations") or [])
    if not manuals and isinstance(findings.get("manual_observations"), list):
        manuals = list(findings["manual_observations"])
    ctx = dict(session.get("measurement_context") or {})
    chart_models = build_v1_chart_cards(groups, settings)
    charts = render_v1_trend_svgs(groups, settings)
    criterion = accuracy_criterion_lines(settings)
    mode = str(settings.get("movement_mode") or ctx.get("direction") or "—")
    fixture = mode == "Vector Magnitude"

    # Presentation enrichment for Repeatability distribution (not a Findings formula change).
    rep_counts = chart_models["repeatability"].group_status_counts or {}

    finding_blocks = []
    for dim in _V1_FINDINGS:
        row = dict(findings.get(dim) or {})
        status = str(row.get("status") or "NOT_TESTED")
        metrics_row = dict(row.get("metrics") or {})
        if dim == "repeatability" and rep_counts:
            metrics_row = {
                **metrics_row,
                "groups_pass": rep_counts.get("PASS", 0),
                "groups_warn": rep_counts.get("WARN", 0),
                "groups_fail": rep_counts.get("FAIL", 0),
            }
        rows_html = "".join(
            f"<tr><th>{_esc(k)}</th><td>{_esc(v)}</td></tr>"
            for k, v in finding_metric_rows(dim, metrics_row)
        )
        help_line = FINDING_HELP_EN.get(dim, "")
        secondary_cls = " finding-secondary" if dim == "ratio" else ""
        finding_blocks.append(
            f"""
<section class="finding{secondary_cls} status-{_esc(status.lower())}">
  <header><h3>{_esc(_FINDING_TITLES.get(dim, dim))}</h3>
  <span class="badge">{_esc(status)}</span></header>
  <p class="meta">{_esc(help_line)}</p>
  <table class="kv">{rows_html}</table>
</section>"""
        )

    scale_pattern = build_cross_dpi_scale_pattern(groups)
    scale_para = format_cross_dpi_scale_paragraph_en(
        scale_pattern,
        ratio_ctx=ratio_context_from_pairs(ratios),
    )
    seq_pts = build_trial_sequence_points(trials)
    dist_rows = build_dpi_error_distributions(trials)
    speed_pts = build_speed_error_points(trials)
    has_timing = session_has_motion_timing(trials)
    seq_svg = render_trial_sequence_svg(seq_pts)
    dist_svg = render_error_distribution_svg(dist_rows)
    speed_svg = render_speed_error_svg(speed_pts) if has_timing else ""
    corr_html = ""
    if has_timing:
        bits = []
        for c in build_speed_correlations(trials):
            if c.spearman_rho is None:
                bits.append(f"{int(c.configured_dpi)} DPI: n={c.n} (need ≥8 for Spearman)")
            else:
                bits.append(
                    f"{int(c.configured_dpi)} DPI: n={c.n}, Spearman ρ={c.spearman_rho:+.3f}"
                )
        corr_html = "<p class=\"meta\">" + _esc(" · ".join(bits)) + "</p>"
    speed_block = (
        f'<div class="chart">{speed_svg}</div>'
        f'<p class="meta">Estimated traversal speed from active-motion duration and configured '
        f'distance — not true physical speed. event_count is not velocity. Descriptive only.</p>'
        f'{corr_html}'
        if has_timing
        else '<p class="meta">Motion timing evidence not available for this Session.</p>'
    )

    research = []
    for dim in _RESEARCH:
        row = dict(findings.get(dim) or {})
        status = str(row.get("status") or "NOT_TESTED")
        research.append(
            f"<li><strong>{_esc(_FINDING_TITLES.get(dim, dim))}</strong> — {_esc(status)}</li>"
        )

    group_rows = []
    for g in groups:
        group_rows.append(
            "<tr>"
            f"<td>{_esc(g.get('configured_dpi'))}</td>"
            f"<td>{_esc(g.get('valid_trials'))}</td>"
            f"<td>{_fmt_num(g.get('avg_measured_cpi'), digits=1)}</td>"
            f"<td>{_fmt_num(g.get('max_abs_error_pct'))}</td>"
            f"<td>{_fmt_num(g.get('cpi_cv_pct'), digits=4)}</td>"
            f"<td>{_esc(g.get('status'))}</td>"
            "</tr>"
        )

    ratio_rows = []
    for r in ratios:
        ratio_rows.append(
            "<tr>"
            f"<td>{_esc(r.get('from_configured_dpi') or r.get('from_dpi'))}</td>"
            f"<td>{_esc(r.get('to_configured_dpi') or r.get('to_dpi'))}</td>"
            f"<td>{_fmt_num(r.get('expected_ratio'), digits=4)}</td>"
            f"<td>{_fmt_num(r.get('measured_ratio'), digits=4)}</td>"
            f"<td>{_fmt_num(r.get('ratio_error_pct'), digits=4)}</td>"
            f"<td>{_esc(r.get('status'))}</td>"
            "</tr>"
        )

    trial_rows = []
    for t in trials:
        direction = t.get("direction")
        if fixture or str(t.get("movement_mode")) == "Vector Magnitude":
            direction = "N/A"
        trial_rows.append(
            "<tr>"
            f"<td>{_esc(t.get('trial_id'))}</td>"
            f"<td>{_esc(t.get('configured_dpi'))}</td>"
            f"<td>{_fmt_num(t.get('measured_cpi'), digits=1)}</td>"
            f"<td>{_fmt_num(t.get('error_pct'))}</td>"
            f"<td>{_esc(t.get('status') or t.get('measurement_status'))}</td>"
            f"<td>{_esc(t.get('path_quality_status'))}</td>"
            f"<td>{_esc(direction)}</td>"
            "</tr>"
        )

    manual_html = "<p>None recorded.</p>"
    if manuals:
        items = "".join(
            f"<li>{_esc(m.get('code') or m.get('id') or 'observation')}: "
            f"{_esc(m.get('status'))} — {_esc(m.get('notes') or '')}</li>"
            for m in manuals
        )
        manual_html = f"<ul>{items}</ul>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Mouse DPI Validation Report — {_esc(session.get('session_id'))}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font-family: "Segoe UI", Helvetica, Arial, sans-serif; color: #1d1d1f; background: #fff;
         margin: 0; padding: 32px; line-height: 1.45; }}
  h1 {{ font-size: 28px; letter-spacing: -0.4px; margin: 0 0 8px; }}
  h2 {{ font-size: 18px; margin: 28px 0 10px; border-bottom: 1px solid #d2d2d7; padding-bottom: 6px; }}
  h3 {{ font-size: 15px; margin: 0; }}
  .meta {{ color: #6e6e73; font-size: 13px; }}
  .finding {{ border: 1px solid #d2d2d7; border-radius: 12px; padding: 14px 16px; margin: 10px 0; }}
  .finding-secondary {{ border-style: dashed; opacity: 0.95; }}
  .finding header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
  .badge {{ font-weight: 650; font-size: 13px; }}
  .status-pass .badge {{ color: #1f8f4e; }}
  .status-warn .badge {{ color: #b26a00; }}
  .status-fail .badge {{ color: #c9342d; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid #e8e8ed; }}
  table.kv th {{ width: 48%; color: #6e6e73; font-weight: 500; }}
  .chart {{ margin: 12px 0; overflow: auto; }}
  .chart svg {{ max-width: 100%; height: auto; border: 1px solid #e8e8ed; border-radius: 10px; }}
  ul.limits {{ margin: 6px 0; padding-left: 18px; }}
  .research {{ color: #6e6e73; }}
  .scale-box {{ border: 1px solid #e8e8ed; border-radius: 10px; padding: 12px 14px; background: #fafafa; }}
  @media print {{
    body {{ padding: 12px; }}
    .finding {{ break-inside: avoid; }}
  }}
</style>
</head>
<body>
  <header>
    <h1>Mouse DPI Validation Report</h1>
    <p class="meta">
      Session ID: {_esc(session.get('session_id'))}<br/>
      Generated: {_esc(generated)}<br/>
      Tool: {_esc(session.get('tool_name'))} {_esc(session.get('tool_version'))}<br/>
      Operator: {_esc(session.get('operator') or '—')}
    </p>
  </header>

  <h2>DUT</h2>
  <table class="kv">
    <tr><th>Vendor</th><td>{_esc(dut.get('vendor') or '—')}</td></tr>
    <tr><th>Model</th><td>{_esc(dut.get('model') or '—')}</td></tr>
    <tr><th>Notes</th><td>{_esc(dut.get('notes') or '—')}</td></tr>
  </table>

  <h2>Test Configuration</h2>
  <table class="kv">
    <tr><th>Movement mode</th><td>{_esc(settings.get('movement_mode') or '—')}</td></tr>
    <tr><th>Physical distance</th><td>{_fmt_num(settings.get('distance_mm'))} mm</td></tr>
    <tr><th>Capture method</th><td>{_esc(ctx.get('method') or 'native Windows Raw Input')}</td></tr>
    <tr><th>Tracking surface</th><td>{_esc(ctx.get('surface') or '—')}</td></tr>
    <tr><th>Fixture / contact notes</th><td>{_esc(ctx.get('fixture_type') or '—')}</td></tr>
    <tr><th>Engineering notes</th><td>{_esc(ctx.get('notes') or '—')}</td></tr>
    <tr><th>Configured DPI groups</th><td>{_esc(', '.join(str(g.get('configured_dpi')) for g in groups) or '—')}</td></tr>
  </table>
  <p><strong>Accuracy criterion</strong></p>
  <ul class="limits">{''.join(f'<li>{_esc(line)}</li>' for line in criterion)}</ul>

  <h2>{_esc(REPORT_INTERPRETATION_TITLE_EN)}</h2>
  <p class="meta">{_esc(REPORT_INTERPRETATION_BODY_EN)}</p>

  <h2>Engineering Findings</h2>
  {''.join(finding_blocks)}

  <h2>DPI Group Summary</h2>
  <table>
    <thead><tr>
      <th>Configured DPI</th><th>Trial count</th><th>Avg measured CPI</th>
      <th>Max |error| %</th><th>CPI CV %</th><th>Status</th>
    </tr></thead>
    <tbody>{''.join(group_rows) or '<tr><td colspan="6">No groups</td></tr>'}</tbody>
  </table>

  <h2>Relative DPI Scaling</h2>
  <p class="meta">Measured CPI step ratios vs configured step ratios. Useful for relative-scaling review; does not prove sensor linearity or native capability.</p>
  <table>
    <thead><tr>
      <th>From DPI</th><th>To DPI</th><th>Configured ratio</th>
      <th>Measured ratio</th><th>Ratio error %</th><th>Status</th>
    </tr></thead>
    <tbody>{''.join(ratio_rows) or '<tr><td colspan="6">No ratio pairs</td></tr>'}</tbody>
  </table>

  <h2>Cross-DPI Scale Pattern</h2>
  <div class="scale-box"><p class="meta">{_esc(scale_para)}</p></div>

  <h2>Engineering Diagnostics</h2>
  <p class="meta">Descriptive Trial distribution views from canonical evidence — not Findings.</p>
  <div class="chart">{seq_svg}</div>
  <div class="chart">{dist_svg}</div>
  {speed_block}

  <h2>DPI Behavior Trends</h2>
  <p class="meta">Descriptive charts from canonical group summaries. Not a Finding and not a high-DPI interpolation verdict.</p>
  <div class="chart">{charts['measured_cpi']}</div>
  <p class="meta"><em>{_esc(CHART_CUES_EN['measured_cpi'])}</em><br/>
  {_esc(format_observation_en(chart_models['measured_cpi'].observation))}<br/>
  {_esc(chart_models['measured_cpi'].metric_note_en)}</p>
  <div class="chart">{charts['max_error']}</div>
  <p class="meta"><em>{_esc(CHART_CUES_EN['max_error'])}</em><br/>
  {_esc(format_observation_en(chart_models['max_error'].observation))}<br/>
  {_esc(chart_models['max_error'].metric_note_en)}</p>
  <div class="chart">{charts['repeatability']}</div>
  <p class="meta"><em>{_esc(CHART_CUES_EN['repeatability'])}</em><br/>
  {_esc(format_observation_en(chart_models['repeatability'].observation))}</p>

  <h2>Trial Evidence</h2>
  <p class="meta">
    Active: {_esc(metrics.get('active_trial_count', len(trials)))} ·
    Rejected: {_esc(metrics.get('rejected_trial_count', len(rejected)))} ·
    History: {_esc(metrics.get('deleted_trial_count', len(deleted)))}
  </p>
  <table>
    <thead><tr>
      <th>Trial #</th><th>Configured DPI</th><th>Measured CPI</th>
      <th>Error %</th><th>Status</th><th>Path Quality</th><th>Direction</th>
    </tr></thead>
    <tbody>{''.join(trial_rows) or '<tr><td colspan="7">No active trials</td></tr>'}</tbody>
  </table>

  <h2>Manual Observations</h2>
  {manual_html}

  <h2 class="research">Research / Not Evaluated</h2>
  <p class="meta">{_esc(RESEARCH_HELP_EN)}</p>
  <ul class="research">{''.join(research)}</ul>

  <h2>Method / Limitations</h2>
  <ul>
    <li>This report validates <strong>effective CPI</strong> against a known physical distance.</li>
    <li>Capture uses <strong>native Windows Raw Input</strong> (or the method recorded in measurement context).</li>
    <li>Fixture Vector geometry uses <strong>Vector Magnitude</strong> √(dx²+dy²); direction is N/A.</li>
    <li>Directional Axis geometry uses <strong>Axis Projection</strong> on the selected axis.</li>
    <li>This report does <strong>not</strong> prove native sensor resolution.</li>
    <li>This report does <strong>not</strong> identify firmware interpolation or scaling mechanisms.</li>
  </ul>
</body>
</html>
"""
