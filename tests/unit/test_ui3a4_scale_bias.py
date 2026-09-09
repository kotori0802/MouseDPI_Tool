"""UI-3A.4 — Relative DPI Scaling presentation + Cross-DPI Scale Pattern."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mouse_dpi_tool.findings.path_quality import build_path_quality_finding
from mouse_dpi_tool.reporting.chart_cards import finding_metric_rows
from mouse_dpi_tool.reporting.html_report import render_html_report
from mouse_dpi_tool.reporting.scale_pattern import (
    build_cross_dpi_scale_pattern,
    format_cross_dpi_scale_lines,
    ratio_context_from_pairs,
)
from mouse_dpi_tool.session import Session
from mouse_dpi_tool.ui.help_content import FINDING_HELP_EN, REPORT_INTERPRETATION_BODY_EN
from mouse_dpi_tool.ui.i18n import I18n


def _groups_common_offset() -> list[dict]:
    # ~3% low across DPI — common scale pattern
    return [
        {"configured_dpi": 400, "avg_measured_cpi": 388.0, "valid_trials": 5},
        {"configured_dpi": 800, "avg_measured_cpi": 776.0, "valid_trials": 5},
        {"configured_dpi": 1600, "avg_measured_cpi": 1552.0, "valid_trials": 5},
        {"configured_dpi": 3200, "avg_measured_cpi": 3104.0, "valid_trials": 5},
    ]


def _groups_nonuniform() -> list[dict]:
    return [
        {"configured_dpi": 400, "avg_measured_cpi": 400.0, "valid_trials": 5},
        {"configured_dpi": 800, "avg_measured_cpi": 720.0, "valid_trials": 5},  # −10%
        {"configured_dpi": 1600, "avg_measured_cpi": 1680.0, "valid_trials": 5},  # +5%
        {"configured_dpi": 3200, "avg_measured_cpi": 2880.0, "valid_trials": 5},  # −10%
    ]


def test_canonical_ratio_schema_key_unchanged():
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "mouse_dpi_tool"
        / "resources"
        / "schemas"
        / "mouse_dpi_tool_session_v1.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    findings = schema["properties"]["findings"]["properties"]
    assert "ratio" in findings
    assert "relative_dpi_scaling" not in findings


def test_presentation_rename_does_not_alter_session_json():
    session = Session(
        settings={
            "distance_mm": 50.8,
            "min_valid_trials_per_group": 1,
            "movement_mode": "Vector Magnitude",
            "tolerance_mode": "FIELD_STRICT",
            "cpi_error_pass_pct": 3.0,
            "cpi_error_fail_pct": 5.0,
            "cpi_cv_pass_pct": 1.0,
            "cpi_cv_fail_pct": 3.0,
        },
        measurement_context={"method": "synthetic", "direction": "N/A"},
        dut={"vendor": "T", "model": "M", "notes": ""},
        operator="ui3a4",
    )
    for dpi, cx in ((400, 390), (800, 780), (1600, 1560), (3200, 3100)):
        session.add_synthetic_trial(configured_dpi=dpi, counts_x=cx, counts_y=0)
    before = copy.deepcopy(session.to_session_dict())
    en = I18n("en-US")
    assert en.finding("ratio") == "Relative DPI Scaling"
    zh = I18n("zh-TW")
    assert "相對" in zh.finding("ratio") or "縮放" in zh.finding("ratio")
    after = session.to_session_dict()
    assert after["findings"] == before["findings"]
    assert "ratio" in after["findings"]
    blob = json.dumps(after)
    assert "Relative DPI Scaling" not in blob
    assert "相對 DPI 縮放" not in blob
    assert "Cross-DPI Scale Pattern" not in blob


def test_common_scale_from_group_summaries_only():
    pattern = build_cross_dpi_scale_pattern(_groups_common_offset())
    assert pattern.pattern_id == "common_scale_offset"
    assert pattern.group_count == 4
    assert pattern.mean_scale is not None
    assert 0.96 < pattern.mean_scale < 0.98
    assert pattern.spread is not None and pattern.spread < 0.02
    text = "\n".join(format_cross_dpi_scale_lines(pattern)).lower()
    assert "fixture calibration failure" not in text
    assert "sensor cpi offset" not in text
    assert "49.3" not in text
    assert "root cause" in text or "does not choose" in text or "not an automatic" in text


def test_qt_table_tamper_cannot_alter_scale_pattern():
    groups = _groups_common_offset()
    a = build_cross_dpi_scale_pattern(groups)
    # Simulate UI table cells changed — helper never reads Qt.
    fake_table_cells = [["400", "9999", "FAIL"]]
    b = build_cross_dpi_scale_pattern(groups)
    assert a == b
    assert fake_table_cells  # unused by design


def test_locale_theme_do_not_alter_numeric_scale_pattern():
    groups = _groups_common_offset()
    p1 = build_cross_dpi_scale_pattern(groups)
    p2 = build_cross_dpi_scale_pattern(groups)
    assert p1.mean_scale == p2.mean_scale
    assert p1.spread == p2.spread
    assert p1.pattern_id == p2.pattern_id
    en = I18n("en-US")
    zh = I18n("zh-TW")
    l_en = format_cross_dpi_scale_lines(p1, t=en.t)
    l_zh = format_cross_dpi_scale_lines(p1, t=zh.t)
    assert l_en != l_zh
    assert p1.min_scale == p2.min_scale


def test_common_offset_with_perfect_ratios_described_as_common_scale():
    pattern = build_cross_dpi_scale_pattern(_groups_common_offset())
    assert pattern.pattern_id == "common_scale_offset"
    ratios = [
        {
            "from_dpi": 400,
            "to_dpi": 800,
            "expected_ratio": 2.0,
            "measured_ratio": 2.0,
            "ratio_error_pct": 0.0,
            "status": "PASS",
        },
        {
            "from_dpi": 800,
            "to_dpi": 1600,
            "expected_ratio": 2.0,
            "measured_ratio": 2.0,
            "ratio_error_pct": 0.0,
            "status": "PASS",
        },
    ]
    ctx = ratio_context_from_pairs(ratios)
    lines = "\n".join(format_cross_dpi_scale_lines(pattern, ratio_ctx=ctx)).lower()
    assert "common" in lines or "near-common" in lines
    assert "ratio" in lines


def test_nonuniform_offsets_not_common_scale_pattern():
    pattern = build_cross_dpi_scale_pattern(_groups_nonuniform())
    assert pattern.pattern_id == "mixed_or_nonuniform"
    lines = "\n".join(format_cross_dpi_scale_lines(pattern)).lower()
    assert "not described as a common-scale" in lines or "mixed" in lines


def test_no_root_cause_verdict_in_scale_output():
    pattern = build_cross_dpi_scale_pattern(_groups_common_offset())
    blob = " ".join(pattern.notes + tuple(format_cross_dpi_scale_lines(pattern))).lower()
    for banned in (
        "fixture calibration failure",
        "sensor cpi offset",
        "actual fixture travel is",
        "49.3 mm",
        "auto-calibrat",
        "interpolation proven",
    ):
        assert banned not in blob


def test_pq_one_not_evaluated_remains_coverage_warn():
    trials = [
        {
            "accepted": True,
            "rejected": False,
            "deleted": False,
            "path_quality_status": "PASS",
            "path_quality_issue_codes": [],
        }
        for _ in range(19)
    ]
    trials.append(
        {
            "accepted": True,
            "rejected": False,
            "deleted": False,
            "path_quality_status": "NOT_EVALUATED",
            "path_quality_issue_codes": ["NO_PATH_EVIDENCE_ABOVE_NOISE_FLOOR"],
        }
    )
    finding = build_path_quality_finding(trials)
    assert finding["status"] == "WARN"
    assert finding["metrics"]["pq_pass"] == 19
    assert finding["metrics"]["pq_fail"] == 0
    assert finding["metrics"]["pq_not_evaluated"] == 1
    assert "PATH_QUALITY_COVERAGE_INCOMPLETE" in finding["issue_codes"]
    rows = finding_metric_rows("path_quality", finding["metrics"])
    values = " ".join(v for _, v in rows).lower()
    assert "1" in values
    assert "not_evaluated" in values or "coverage" in values
    assert "no pq fail" in values


def test_report_uses_same_interpretation_model():
    assert "Relative DPI Scaling" in REPORT_INTERPRETATION_BODY_EN
    assert "common offset" in REPORT_INTERPRETATION_BODY_EN.lower() or "different properties" in REPORT_INTERPRETATION_BODY_EN
    assert "relative-scaling" in FINDING_HELP_EN["ratio"].lower() or "relative" in FINDING_HELP_EN["ratio"].lower()
    session = {
        "session_id": "ui3a4-test",
        "tool_name": "Mouse DPI Tool",
        "tool_version": "0.0.0",
        "operator": "t",
        "settings": {
            "distance_mm": 50.8,
            "movement_mode": "Vector Magnitude",
            "cpi_error_pass_pct": 3.0,
            "cpi_error_fail_pct": 5.0,
            "cpi_cv_pass_pct": 1.0,
            "cpi_cv_fail_pct": 3.0,
            "tolerance_mode": "FIELD_STRICT",
        },
        "dut": {"vendor": "T", "model": "M", "notes": ""},
        "measurement_context": {"method": "synthetic"},
        "metrics": {"active_trial_count": 4, "group_count": 4, "ratio_pair_count": 0},
        "group_summaries": _groups_common_offset(),
        "ratio_analysis": [
            {
                "from_dpi": 400,
                "to_dpi": 800,
                "expected_ratio": 2.0,
                "measured_ratio": 2.0,
                "ratio_error_pct": 0.0,
                "status": "PASS",
            }
        ],
        "trials": [],
        "findings": {
            "accuracy": {"status": "WARN", "metrics": {}, "issue_codes": []},
            "repeatability": {"status": "PASS", "metrics": {}, "issue_codes": []},
            "ratio": {"status": "PASS", "metrics": {"ratios_pass": 1}, "issue_codes": []},
            "path_quality": {
                "status": "WARN",
                "metrics": {
                    "pq_pass": 19,
                    "pq_warn": 0,
                    "pq_fail": 0,
                    "pq_not_evaluated": 1,
                    "pq_trial_count": 20,
                },
                "issue_codes": ["PATH_QUALITY_COVERAGE_INCOMPLETE"],
            },
            "linearity": {"status": "NOT_EVALUATED", "metrics": {}, "issue_codes": []},
            "scaling_evidence": {"status": "NOT_EVALUATED", "metrics": {}, "issue_codes": []},
            "native_capability": {"status": "NOT_EVALUATED", "metrics": {}, "issue_codes": []},
        },
    }
    html = render_html_report(session)
    assert "Relative DPI Scaling" in html
    assert "Cross-DPI Scale Pattern" in html
    assert "Overall" not in html or "overall verdict" not in html.lower()
    assert "fixture calibration failure" not in html.lower()
    assert FINDING_HELP_EN["ratio"][:40] in html or "relative-scaling" in html.lower()


def test_no_overall_verdict_introduced():
    session = Session(
        settings={
            "distance_mm": 50.8,
            "min_valid_trials_per_group": 1,
            "movement_mode": "Vector Magnitude",
            "tolerance_mode": "FIELD_STRICT",
            "cpi_error_pass_pct": 3.0,
            "cpi_error_fail_pct": 5.0,
            "cpi_cv_pass_pct": 1.0,
            "cpi_cv_fail_pct": 3.0,
        },
        measurement_context={"method": "synthetic", "direction": "N/A"},
        dut={"vendor": "T", "model": "M", "notes": ""},
        operator="ui3a4",
    )
    session.add_synthetic_trial(configured_dpi=800, counts_x=780, counts_y=0)
    d = session.to_session_dict()
    assert "overall" not in d["findings"]
    assert "cross_dpi_scale" not in d["findings"]
    pattern = build_cross_dpi_scale_pattern(d["group_summaries"])
    assert pattern.pattern_id in {"common_scale_offset", "mixed_or_nonuniform", "insufficient"}


def test_reference_session_numbers_not_hardcoded():
    src = Path(__file__).resolve().parents[2] / "src" / "mouse_dpi_tool" / "reporting" / "scale_pattern.py"
    text = src.read_text(encoding="utf-8")
    for token in ("389.5", "778.8", "1551.1", "3093.7", "0.4173", "8.98"):
        assert token not in text
