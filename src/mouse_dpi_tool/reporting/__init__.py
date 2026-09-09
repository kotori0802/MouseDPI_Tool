"""Reporting layer — Session JSON export + HTML Test Report (UI-2 / Report-1)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from mouse_dpi_tool.reporting.chart_cards import (
    build_v1_chart_cards,
    finding_metric_rows,
    format_observation_en,
)
from mouse_dpi_tool.reporting.fixture_motion import (
    FixtureMotionDiagnostics,
    PATH_EXCESS_NOT_EVALUATED,
    PerDpiMotionRow,
    build_fixture_motion_diagnostics,
    circular_mean_deg,
    circular_spread_deg,
    endpoint_heading_deg,
    format_fixture_motion_lines,
    path_excess_pct,
    path_excess_result,
)
from mouse_dpi_tool.reporting.scale_pattern import (
    CrossDpiScalePattern,
    build_cross_dpi_scale_pattern,
    format_cross_dpi_scale_lines,
    format_cross_dpi_scale_paragraph_en,
    ratio_context_from_pairs,
)
from mouse_dpi_tool.reporting.generate import (
    ReportArtifacts,
    generate_report_bundle,
    html_report_filename,
    report_run_id,
    session_sidecar_filename,
)
from mouse_dpi_tool.reporting.html_report import (
    accuracy_criterion_lines,
    render_html_report,
)
from mouse_dpi_tool.reporting.trends import render_v1_trend_svgs
from mouse_dpi_tool.reporting.trends_points import group_trend_points
from mouse_dpi_tool.session.writer import load_session_json, validate_session, write_session_json


def sanitize_run_id(run_id: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", str(run_id or "run").strip())
    return text[:80] or "run"


def session_json_filename(run_id: str) -> str:
    return f"mouse_dpi_tool_{sanitize_run_id(run_id)}_session.json"


def default_reports_dir(app_root: Path | None = None) -> Path:
    root = app_root or Path.cwd()
    return root / "reports"


def export_session_json(session: Mapping[str, Any], path: str | Path) -> Path:
    """Validate + atomically write a Session mapping to ``path``."""
    return write_session_json(session, path)


__all__ = [
    "CrossDpiScalePattern",
    "FixtureMotionDiagnostics",
    "PATH_EXCESS_NOT_EVALUATED",
    "PerDpiMotionRow",
    "ReportArtifacts",
    "accuracy_criterion_lines",
    "build_cross_dpi_scale_pattern",
    "build_fixture_motion_diagnostics",
    "build_v1_chart_cards",
    "circular_mean_deg",
    "circular_spread_deg",
    "default_reports_dir",
    "endpoint_heading_deg",
    "export_session_json",
    "finding_metric_rows",
    "format_cross_dpi_scale_lines",
    "format_cross_dpi_scale_paragraph_en",
    "format_fixture_motion_lines",
    "format_observation_en",
    "generate_report_bundle",
    "group_trend_points",
    "html_report_filename",
    "load_session_json",
    "path_excess_pct",
    "path_excess_result",
    "ratio_context_from_pairs",
    "render_html_report",
    "render_v1_trend_svgs",
    "report_run_id",
    "sanitize_run_id",
    "session_json_filename",
    "session_sidecar_filename",
    "validate_session",
    "write_session_json",
]
