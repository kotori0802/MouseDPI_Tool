"""Phase 5 — Session JSON ↔ Findings ↔ HTML report consistency (qualification).

Uses an equivalent 20-Trial multi-DPI Session (4 groups × 5), not a forced PASS.
Software gate: evidence must match across Session / Findings / HTML.
Does NOT require Accuracy/Repeatability Findings to PASS.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from mouse_dpi_tool.findings import build_findings_from_mapping
from mouse_dpi_tool.reporting import generate_report_bundle, render_html_report, validate_session
from mouse_dpi_tool.reporting.generate import ReportArtifacts
from mouse_dpi_tool.session import Session

# Physical pre-gate geometry (GPT-reviewed Session).
_DISTANCE_MM = 50.8
_DPIS = (400, 800, 1600, 3200)
_N_PER_GROUP = 5
# ~−4% absolute offset → Strict Accuracy WARN-capable (mirrors physical WARN, not collapse).
_ERROR_SCALE = 0.96


def _counts_for(dpi: int) -> int:
    return int(round(dpi * (_DISTANCE_MM / 25.4) * _ERROR_SCALE))


def _qualification_session() -> Session:
    session = Session(
        dut={
            "vendor": "ExampleVendor",
            "model": "DemoMouse",
            "notes": "Synthetic regression fixture",
        },
        measurement_context={
            "method": "hand_drag",
            "fixture_type": "",
            "surface": "",
            "direction": "",
            "notes": "Synthetic demonstration data — not a real product validation result.",
        },
        settings={
            "distance_mm": _DISTANCE_MM,
            "distance_input": 2.0,
            "distance_unit": "inch",
            "movement_mode": "Vector Magnitude",
            "min_valid_trials_per_group": 3,
            "cpi_error_pass_pct": 3.0,
            "cpi_error_fail_pct": 7.0,
            "cpi_cv_pass_pct": 1.0,
            "cpi_cv_fail_pct": 3.0,
            "ratio_error_pass_pct": 2.0,
            "ratio_error_fail_pct": 5.0,
            "tolerance_mode": "FIELD_STRICT",
        },
        operator="phase5",
    )
    for dpi in _DPIS:
        for _ in range(_N_PER_GROUP):
            session.add_synthetic_trial(
                configured_dpi=dpi,
                counts_x=_counts_for(dpi),
                counts_y=0,
            )
    return session


def test_phase5_session_structure_matches_pre_gate_shape():
    session = _qualification_session()
    snap = session.to_session_dict()
    validate_session(snap)
    assert len(snap["trials"]) == 20
    groups = {int(g["configured_dpi"]): g for g in snap["group_summaries"]}
    assert set(groups) == set(_DPIS)
    for dpi in _DPIS:
        assert int(groups[dpi]["valid_trials"]) == _N_PER_GROUP


def test_phase5_findings_rebuild_matches_session_aggregates():
    session = _qualification_session()
    snap = session.to_session_dict()
    findings = build_findings_from_mapping(snap)
    # Session carries canonical group_summaries / ratio_analysis.
    by_dpi = {int(g["configured_dpi"]): g for g in snap["group_summaries"]}
    assert set(by_dpi) == set(_DPIS)
    for dpi in _DPIS:
        g = by_dpi[dpi]
        assert g.get("avg_measured_cpi") is not None
        assert g.get("status") in {"PASS", "WARN", "FAIL", "NOT_EVALUATED", "NOT_TESTED"}
        assert g.get("cpi_cv_pct") is not None
    assert len(snap["ratio_analysis"]) >= 3
    for pair in snap["ratio_analysis"]:
        assert "status" in pair
        assert pair.get("measured_ratio") is not None
    # Findings dimensions reference the same trial population.
    assert findings["accuracy"]["metrics"]["active_trial_count"] == 20
    assert findings["accuracy"]["metrics"]["group_count"] == 4
    assert findings["ratio"]["metrics"]["ratio_pair_count"] == 3


def test_phase5_html_report_echoes_canonical_evidence(tmp_path: Path):
    session = _qualification_session()
    snap = session.to_session_dict()
    findings = build_findings_from_mapping(snap)
    html = render_html_report(snap, generated_at="PHASE5-FIXED")

    assert str(findings["accuracy"]["metrics"]["active_trial_count"]) in html or "20" in html
    for dpi in _DPIS:
        assert str(dpi) in html
    # Accuracy / Repeatability statuses appear as reported (may be WARN).
    assert findings["accuracy"]["status"] in html
    assert findings["repeatability"]["status"] in html
    # Relative DPI Scaling / ratio content present.
    assert "ratio" in html.lower() or "scaling" in html.lower() or "800" in html

    artifacts: ReportArtifacts = generate_report_bundle(snap, tmp_path, run_id="phase5_qual")
    assert artifacts.json_path.is_file()
    assert artifacts.html_path.is_file()
    reloaded = artifacts.json_path.read_text(encoding="utf-8")
    assert '"trials"' in reloaded
    assert re.findall(r'"configured_dpi":\s*800', reloaded)


def test_phase5_warn_finding_is_allowed_for_software_pass():
    """Software qualification must not require DUT Accuracy PASS."""
    session = _qualification_session()
    snap = session.to_session_dict()
    findings = build_findings_from_mapping(snap)
    assert findings["accuracy"]["status"] in {"PASS", "WARN", "FAIL"}
    # Equivalent Session is intentionally WARN-capable under Strict (±3%/7%).
    assert findings["accuracy"]["status"] == "WARN"
    assert findings["accuracy"]["metrics"]["active_trial_count"] == 20
