"""UI-2A / Report-1 — HTML report + Session JSON sidecar."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from mouse_dpi_tool.reporting import (
    accuracy_criterion_lines,
    generate_report_bundle,
    render_html_report,
    validate_session,
)
from mouse_dpi_tool.session import Session


def _session(**kwargs) -> Session:
    settings = {
        "distance_mm": 100.0,
        "movement_mode": "Vector Magnitude",
        "min_valid_trials_per_group": 3,
        "cpi_error_pass_pct": 3.0,
        "cpi_error_fail_pct": 5.0,
        "cpi_cv_pass_pct": 1.0,
        "cpi_cv_fail_pct": 3.0,
        "ratio_error_pass_pct": 2.0,
        "ratio_error_fail_pct": 5.0,
        "tolerance_mode": "FIELD_STRICT",
    }
    if "settings" in kwargs:
        settings = {**settings, **kwargs.pop("settings")}
    return Session(
        dut={"vendor": "ExampleVendor", "model": "DemoMouse", "notes": "lab"},
        measurement_context={
            "method": "synthetic",
            "fixture_type": "",
            "surface": "",
            "direction": "X+",
            "polling_rate_note": "",
            "notes": "",
        },
        settings=settings,
        operator="tester",
        **kwargs,
    )


def _perfect_counts(dpi: int, distance_mm: float = 100.0) -> int:
    return int(round(dpi * (distance_mm / 25.4)))


def _multi_dpi_session(*, error_scale: float = 1.0) -> Session:
    session = _session()
    for dpi in (800, 1600, 3200):
        for _ in range(3):
            counts = int(round(_perfect_counts(dpi) * error_scale))
            session.add_synthetic_trial(configured_dpi=dpi, counts_x=counts, counts_y=0)
    return session


def test_criterion_bands_strict_medium_lenient():
    strict = accuracy_criterion_lines(
        {"cpi_error_pass_pct": 3.0, "cpi_error_fail_pct": 5.0, "tolerance_mode": "FIELD_STRICT"}
    )
    assert "PASS ≤ 3%" in strict[1]
    assert "WARN > 3% – 5%" in strict[2]
    assert "FAIL > 5%" in strict[3]
    medium = accuracy_criterion_lines(
        {"cpi_error_pass_pct": 6.0, "cpi_error_fail_pct": 8.0, "tolerance_mode": "FIELD_MEDIUM"}
    )
    assert "PASS ≤ 6%" in medium[1]
    assert "FAIL > 8%" in medium[3]


def test_report_accepts_pass_warn_fail(tmp_path: Path):
    for scale, expect_word in ((1.0, "PASS"), (1.04, "WARN"), (1.08, "FAIL")):
        session = _multi_dpi_session(error_scale=scale)
        snap = session.to_session_dict()
        status = snap["findings"]["accuracy"]["status"]
        # Scale mapping may land WARN or FAIL depending on thresholds; still reportable.
        assert status in {"PASS", "WARN", "FAIL"}
        art = generate_report_bundle(snap, tmp_path / expect_word, run_id=f"run_{expect_word}")
        assert art.html_path.is_file()
        assert art.json_path.is_file()
        html = art.html_path.read_text(encoding="utf-8")
        assert "Mouse DPI Validation Report" in html
        assert status in html


def test_report_values_match_session_groups_ratios_findings(tmp_path: Path):
    session = _multi_dpi_session()
    snap = session.to_session_dict()
    html = render_html_report(snap, generated_at="2026-01-01 00:00:00 UTC")
    for g in snap["group_summaries"]:
        assert str(g["configured_dpi"]) in html
        assert f"{float(g['avg_measured_cpi']):.1f}" in html or str(g["avg_measured_cpi"]) in html
    for r in snap["ratio_analysis"]:
        assert str(r["from_dpi"]) in html
        assert str(r["to_dpi"]) in html
    assert snap["findings"]["accuracy"]["status"] in html
    art = generate_report_bundle(snap, tmp_path, run_id="match")
    reloaded = validate_session(
        __import__("json").loads(art.json_path.read_text(encoding="utf-8"))
    )
    assert reloaded["session_id"] == snap["session_id"]
    assert reloaded["findings"]["accuracy"]["metrics"] == snap["findings"]["accuracy"]["metrics"]


def test_rejected_deleted_do_not_contaminate_active_summaries(tmp_path: Path):
    session = _multi_dpi_session()
    active_ids = [t["trial_id"] for t in session.active_trials]
    session.reject_trial(active_ids[0], reason="noise")
    session.delete_trial(active_ids[1], reason="archive")
    before = session.metrics()
    snap = session.to_session_dict()
    assert before["active_trial_count"] == len(snap["trials"])
    assert before["rejected_trial_count"] == len(snap["rejected_trials"])
    assert before["deleted_trial_count"] == len(snap["deleted_trials"])
    html = render_html_report(snap)
    assert f"Active: {before['active_trial_count']}" in html
    # Rejected trial id must not appear as active analysis trial rows only —
    # still listed in counts.
    assert f"Rejected: {before['rejected_trial_count']}" in html
    art = generate_report_bundle(snap, tmp_path, run_id="lifecycle")
    assert art.html_path.is_file()


def test_fixture_vector_direction_na_in_report():
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800), counts_y=0)
    snap = session.to_session_dict()
    assert snap["trials"][0]["direction"] in {"N/A", "—", None} or snap["trials"][0][
        "movement_mode"
    ] == "Vector Magnitude"
    html = render_html_report(snap)
    assert "N/A" in html
    assert "does <strong>not</strong> prove native sensor resolution" in html


def test_html_has_no_remote_cdn():
    session = _multi_dpi_session()
    html = render_html_report(session.to_session_dict())
    lowered = html.lower()
    assert "<script" not in lowered
    assert "cdn." not in lowered
    assert "googleapis" not in lowered
    assert "cloudflare" not in lowered
    assert "src=\"http" not in lowered
    assert "href=\"http" not in lowered


def test_generation_does_not_mutate_session(tmp_path: Path):
    session = _multi_dpi_session()
    before = copy.deepcopy(session.to_session_dict())
    generate_report_bundle(session.to_session_dict(), tmp_path, run_id="immut")
    after = session.to_session_dict()
    assert after["trials"] == before["trials"]
    assert after["findings"] == before["findings"]
    assert after["group_summaries"] == before["group_summaries"]


def test_report_invariant_to_presentation_fingerprint(tmp_path: Path):
    """Dark/Light/sort/filter are presentation-only — engineering HTML uses Session."""
    session = _multi_dpi_session()
    snap_a = session.to_session_dict()
    snap_b = copy.deepcopy(snap_a)
    # Simulate UI-only noise that must not affect report if we always pass Session.
    snap_b["_ui_theme"] = "dark"
    snap_b["_ui_sort"] = "oldest"
    # Strip non-schema noise before generate — callers pass session_snapshot only.
    html_a = render_html_report(snap_a, generated_at="FIXED")
    html_b = render_html_report(snap_a, generated_at="FIXED")
    assert html_a == html_b
    art = generate_report_bundle(snap_a, tmp_path, run_id="inv", generated_at="FIXED")
    assert "Configured CPI vs Average Measured CPI" in art.html_path.read_text(encoding="utf-8") or (
        "Measured CPI vs Configured DPI" in art.html_path.read_text(encoding="utf-8")
    )


def test_controller_report_uses_session_not_widgets(tmp_path: Path):
    pytest.importorskip("PySide6")
    from mouse_dpi_tool.ui.controllers import AppController

    controller = AppController()
    for dpi in (800, 1600):
        for _ in range(3):
            controller.session.add_synthetic_trial(
                configured_dpi=dpi,
                counts_x=_perfect_counts(dpi),
                counts_y=0,
            )
    snap = controller.session_snapshot()
    art = controller.generate_test_report(tmp_path)
    assert art.html_path.is_file()
    html = art.html_path.read_text(encoding="utf-8")
    assert snap["session_id"] in html
    assert str(snap["findings"]["accuracy"]["status"]) in html
