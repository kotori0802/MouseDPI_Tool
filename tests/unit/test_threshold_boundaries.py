"""Frozen V1 threshold-boundary cases (not a real mouse capture)."""

from __future__ import annotations

import json
from pathlib import Path

from mouse_dpi_tool.measurement.group import summarize_group
from mouse_dpi_tool.measurement.ratio import build_ratio_analysis
from mouse_dpi_tool.measurement.settings import normalize_settings, status_from_limits

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "boundaries" / "threshold_status.json"


def _load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _trials(cpis, errors, configured_dpi=800, distance_mm=100.0):
    rows = []
    for i, (cpi, err) in enumerate(zip(cpis, errors), start=1):
        rows.append(
            {
                "trial_id": i,
                "configured_dpi": configured_dpi,
                "axis": "X",
                "direction": "X+",
                "distance_mm": distance_mm,
                "movement_mode": "Vector Magnitude",
                "measured_cpi": cpi,
                "error_pct": err,
                "axis_leakage_pct": 0.0,
                "accepted": True,
                "deleted": False,
                "rejected": False,
            }
        )
    return rows


def test_status_from_limits_boundaries():
    data = _load()
    for case in data["status_from_limits"]:
        assert status_from_limits(case["value_abs"], case["pass"], case["fail"]) == case["expected"]


def test_cpi_group_boundaries():
    data = _load()
    settings = normalize_settings(data["settings"])
    for case in data["cpi_groups"]:
        summary = summarize_group(_trials(case["measured_cpis"], case["error_pcts"]), settings)
        assert summary["status"] == case["expected_status"], case["id"]
        tags = summary["issue_tags"].split(";") if summary["issue_tags"] else []
        for tag in case["expected_tags_contains"]:
            assert tag in tags, (case["id"], tags)


def test_cv_group_boundaries():
    data = _load()
    settings = normalize_settings(data["settings"])
    for case in data["cv_groups"]:
        summary = summarize_group(_trials(case["measured_cpis"], case["error_pcts"]), settings)
        assert summary["status"] == case["expected_status"], case["id"]
        if case["id"] == "cv_pass":
            assert summary["cpi_cv_pct"] == case["expected_cv_pct"]
        if case["id"] == "cv_fail":
            assert "CPI_CV_FAIL" in summary["issue_tags"]


def test_insufficient_trials_warn():
    data = _load()
    settings = normalize_settings(data["settings"])
    case = data["insufficient_trials"]
    summary = summarize_group(_trials(case["measured_cpis"], case["error_pcts"]), settings)
    assert summary["status"] == case["expected_status"]
    for tag in case["expected_tags_contains"]:
        assert tag in summary["issue_tags"]
    assert summary["valid_trials"] == 2


def test_ratio_boundaries():
    data = _load()
    settings = normalize_settings(data["settings"])
    for case in data["ratio_pairs"]:
        groups = [
            {
                "axis": "X",
                "direction": "X+",
                "distance_mm": 100.0,
                "movement_mode": "Vector Magnitude",
                "configured_dpi": case["from_dpi"],
                "avg_measured_cpi": case["from_avg"],
            },
            {
                "axis": "X",
                "direction": "X+",
                "distance_mm": 100.0,
                "movement_mode": "Vector Magnitude",
                "configured_dpi": case["to_dpi"],
                "avg_measured_cpi": case["to_avg"],
            },
        ]
        rows = build_ratio_analysis(groups, settings)
        assert len(rows) == 1, case["id"]
        assert rows[0]["status"] == case["expected_status"], (case["id"], rows[0])
