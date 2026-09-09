"""UI-2A.1 — chart comprehension + report/Qt chart model parity."""

from __future__ import annotations

import copy
from pathlib import Path

from mouse_dpi_tool.reporting import (
    build_v1_chart_cards,
    finding_metric_rows,
    format_observation_en,
    generate_report_bundle,
    render_html_report,
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
        dut={"vendor": "ExampleVendor", "model": "DemoMouse", "notes": ""},
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


def _perfect(dpi: int, distance_mm: float = 100.0) -> int:
    return int(round(dpi * (distance_mm / 25.4)))


def _build_session(*, scale: float = 0.96, dpis=(800, 1600, 3200), n: int = 5) -> Session:
    session = _session()
    for dpi in dpis:
        for _ in range(n):
            session.add_synthetic_trial(
                configured_dpi=dpi,
                counts_x=int(round(_perfect(dpi) * scale)),
                counts_y=0,
            )
    return session


def test_chart1_points_from_group_summaries_and_ideal_1to1():
    session = _build_session()
    snap = session.to_session_dict()
    cards = build_v1_chart_cards(snap["group_summaries"], snap["settings"])
    cpi = cards["measured_cpi"]
    assert [p.configured_dpi for p in cpi.points] == [800.0, 1600.0, 3200.0]
    for g, pt in zip(snap["group_summaries"], cpi.points, strict=True):
        assert abs(pt.value - float(g["avg_measured_cpi"])) < 1e-9
        assert abs(pt.configured_dpi - float(g["configured_dpi"])) < 1e-9
    assert len(cpi.ideal_points) == 3
    for ideal in cpi.ideal_points:
        assert ideal.value == ideal.configured_dpi


def test_chart2_uses_session_accuracy_thresholds_strict_medium_lenient():
    for mode, pass_pct, fail_pct in (
        ("FIELD_STRICT", 3.0, 5.0),
        ("FIELD_MEDIUM", 6.0, 8.0),
        ("FIELD_LENIENT", 9.0, 11.0),
    ):
        session = _session(
            settings={
                "cpi_error_pass_pct": pass_pct,
                "cpi_error_fail_pct": fail_pct,
                "tolerance_mode": mode,
            }
        )
        for dpi in (800, 1600):
            for _ in range(3):
                session.add_synthetic_trial(
                    configured_dpi=dpi, counts_x=int(round(_perfect(dpi) * 0.96)), counts_y=0
                )
        snap = session.to_session_dict()
        card = build_v1_chart_cards(snap["group_summaries"], snap["settings"])["max_error"]
        assert card.thresholds is not None
        assert card.thresholds.pass_pct == pass_pct
        assert card.thresholds.fail_pct == fail_pct


def test_chart2_status_summary_matches_group_evidence():
    session = _build_session(scale=0.96)  # ~4% error → WARN under Strict 3/5
    snap = session.to_session_dict()
    card = build_v1_chart_cards(snap["group_summaries"], snap["settings"])["max_error"]
    assert card.group_status_counts is not None
    assert card.group_status_counts["WARN"] == 3
    assert card.group_status_counts["FAIL"] == 0
    assert card.group_status_counts["PASS"] == 0
    text = format_observation_en(card.observation)
    assert "WARN 3" in text
    assert "FAIL 0" in text


def test_chart3_uses_canonical_cv_and_numeric_dpi_order():
    session = _build_session(dpis=(3200, 800, 1600, 42000))
    snap = session.to_session_dict()
    card = build_v1_chart_cards(snap["group_summaries"], snap["settings"])["repeatability"]
    xs = [p.configured_dpi for p in card.points]
    assert xs == sorted(xs)
    assert 42000.0 in xs
    by_dpi = {float(g["configured_dpi"]): g.get("cpi_cv_pct") for g in snap["group_summaries"]}
    for pt in card.points:
        expected = by_dpi[pt.configured_dpi]
        if expected is None:
            continue
        assert abs(pt.value - float(expected)) < 1e-9


def test_chart_summaries_do_not_alter_findings():
    session = _build_session()
    before = copy.deepcopy(session.to_session_dict()["findings"])
    _ = build_v1_chart_cards(session.group_summaries, session.settings)
    after = session.to_session_dict()["findings"]
    assert after == before


def test_accuracy_finding_rows_use_status_distribution():
    rows = finding_metric_rows(
        "accuracy",
        {
            "max_abs_error_pct": 4.2,
            "groups_pass": 0,
            "groups_warn": 3,
            "groups_fail": 0,
            "active_trial_count": 15,
        },
    )
    labels = dict(rows)
    assert "PASS 0 · WARN 3 · FAIL 0" in labels["Groups"]
    assert "0 / 3" not in labels.get("DPI groups passed", "")


def test_report_and_qt_chart_models_identical(tmp_path: Path):
    session = _build_session()
    snap = session.to_session_dict()
    a = build_v1_chart_cards(snap["group_summaries"], snap["settings"])
    b = build_v1_chart_cards(snap["group_summaries"], snap["settings"])
    assert a["measured_cpi"].as_xy() == b["measured_cpi"].as_xy()
    assert a["max_error"].thresholds == b["max_error"].thresholds
    assert a["repeatability"].as_xy() == b["repeatability"].as_xy()
    html = render_html_report(snap, generated_at="FIXED")
    assert a["measured_cpi"].title_en in html
    assert a["max_error"].title_en in html
    assert "WARN 3" in html
    assert "FAIL 0" in html
    assert "PASS ≤ 3%" in html or "PASS &le; 3%" in html or "PASS ≤ 3%" in html.replace("&le;", "≤")
    # Theme/locale noise must not change Session-derived chart values.
    snap2 = copy.deepcopy(snap)
    snap2["_ui_theme"] = "dark"
    snap2["_ui_locale"] = "zh-TW"
    c = build_v1_chart_cards(snap2["group_summaries"], snap2["settings"])
    assert c["measured_cpi"].as_xy() == a["measured_cpi"].as_xy()
    art = generate_report_bundle(snap, tmp_path, run_id="ui2a1", generated_at="FIXED")
    assert art.html_path.is_file()


def test_sort_filter_do_not_alter_chart_values():
    session = _build_session()
    snap = session.to_session_dict()
    base = build_v1_chart_cards(snap["group_summaries"], snap["settings"])
    shuffled = list(reversed(snap["group_summaries"]))
    again = build_v1_chart_cards(shuffled, snap["settings"])
    assert again["measured_cpi"].as_xy() == base["measured_cpi"].as_xy()


def test_report_generation_does_not_alter_session_fingerprint(tmp_path: Path):
    session = _build_session()
    before = copy.deepcopy(session.to_session_dict())
    generate_report_bundle(session.to_session_dict(), tmp_path, run_id="fp")
    after = session.to_session_dict()
    assert after["findings"] == before["findings"]
    assert after["group_summaries"] == before["group_summaries"]
    assert after["trials"] == before["trials"]
