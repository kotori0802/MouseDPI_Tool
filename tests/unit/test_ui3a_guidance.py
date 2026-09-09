"""UI-3A — first-use guidance, chart interpretation, zh-TW primary surfaces."""

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
from mouse_dpi_tool.reporting.trends import render_chart_card_svg
from mouse_dpi_tool.session import Session
from mouse_dpi_tool.ui.help_content import (
    CHART_CUES_EN,
    REPORT_INTERPRETATION_BODY_EN,
    REPORT_INTERPRETATION_TITLE_EN,
    USER_GUIDE_SECTIONS,
)
from mouse_dpi_tool.ui.i18n import I18n
from mouse_dpi_tool.ui.i18n.catalogs import CATALOGS, _EN, _ZH_TW


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


UI3A_SHORTCUT_KEYS = (
    "capture.start_f5",
    "capture.stop_f5",
    "capture.cancel_esc",
    "capture.shortcut_hint",
    "capture.how_to_measure",
    "capture.procedure_hint",
)

UI3A_OPERATOR_KEYS = UI3A_SHORTCUT_KEYS + (
    "help.guide.title",
    "help.guide.open",
    "charts.measured_cpi.cue",
    "charts.max_error.cue",
    "charts.repeatability.cue",
    "finding.metric.max_individual_error",
    "finding.help.accuracy",
    "setup.accuracy_locked",
    "setup.accuracy_locked_short",
    "report.interpretation.title",
)


def test_shortcut_labels_visible_and_localized():
    en = I18n("en-US")
    zh = I18n("zh-TW")
    for key in UI3A_SHORTCUT_KEYS:
        text = en.t(key)
        assert text != key
        ok = (
            "F5" in text
            or "Esc" in text
            or "measure" in text.lower()
            or "?" in text
            or "seat" in text.lower()
            or "reference" in text.lower()
        )
        assert ok, key
        assert zh.t(key) != en.t(key)
        assert zh.t(key) != key
    assert "F5" in en.t("capture.shortcut_hint")
    assert "Esc" in en.t("capture.shortcut_hint")
    assert "F5" in zh.t("capture.shortcut_hint")
    assert "Esc" in zh.t("capture.shortcut_hint")
    assert "貼靠" in zh.t("capture.procedure_hint")


def test_help_content_does_not_enter_session_json():
    session = _build_session()
    before = session.to_session_dict()
    # Simulate presentation-only help access (catalog + guide keys).
    _ = [(_EN[a], _EN[b]) for a, b in USER_GUIDE_SECTIONS]
    _ = CHART_CUES_EN
    after = session.to_session_dict()
    assert after == before
    blob = __import__("json").dumps(after)
    assert "How to measure" not in blob
    assert "User Guide" not in blob
    assert "shortcuts" not in blob.lower() or "shortcut" not in str(after.get("settings"))


def test_chart_interpretation_text_does_not_alter_chart_values():
    session = _build_session()
    snap = session.to_session_dict()
    cards = build_v1_chart_cards(snap["group_summaries"], snap["settings"])
    xy_before = cards["measured_cpi"].as_xy()
    _ = format_observation_en(cards["measured_cpi"].observation)
    _ = CHART_CUES_EN["measured_cpi"]
    cards2 = build_v1_chart_cards(snap["group_summaries"], snap["settings"])
    assert cards2["measured_cpi"].as_xy() == xy_before
    assert cards2["max_error"].as_xy() == cards["max_error"].as_xy()
    assert cards2["repeatability"].as_xy() == cards["repeatability"].as_xy()


def test_y_axis_presentation_derives_from_numeric_values_only():
    session = _build_session()
    snap = session.to_session_dict()
    card = build_v1_chart_cards(snap["group_summaries"], snap["settings"])["max_error"]
    svg = render_chart_card_svg(card)
    # Threshold labels use Session policy numbers, not hard-coded Strict-only if policy changes.
    assert f"PASS ≤ {card.thresholds.pass_pct:g}%" in svg
    assert f"FAIL > {card.thresholds.fail_pct:g}%" in svg
    assert "WARN" in svg
    # Y label is the chart model field (numeric axis meaning).
    assert card.y_label_en in svg
    # Values in series match group max_abs_error_pct.
    by_dpi = {float(g["configured_dpi"]): float(g["max_abs_error_pct"]) for g in snap["group_summaries"]}
    for pt in card.points:
        assert abs(pt.value - by_dpi[pt.configured_dpi]) < 1e-9


def test_threshold_labels_follow_session_policy_not_hardcoded_strict():
    for pass_pct, fail_pct in ((3.0, 5.0), (6.0, 8.0), (9.0, 11.0)):
        session = _session(
            settings={
                "cpi_error_pass_pct": pass_pct,
                "cpi_error_fail_pct": fail_pct,
            }
        )
        for dpi in (800, 1600):
            for _ in range(3):
                session.add_synthetic_trial(
                    configured_dpi=dpi,
                    counts_x=int(round(_perfect(dpi) * 0.96)),
                    counts_y=0,
                )
        snap = session.to_session_dict()
        card = build_v1_chart_cards(snap["group_summaries"], snap["settings"])["max_error"]
        svg = render_chart_card_svg(card)
        assert f"PASS ≤ {pass_pct:g}%" in svg
        assert f"FAIL > {fail_pct:g}%" in svg
        assert f"WARN {pass_pct:g}–{fail_pct:g}%" in svg


def test_group_average_deviation_distinct_from_max_trial_error():
    session = _build_session(scale=0.96)
    snap = session.to_session_dict()
    cards = build_v1_chart_cards(snap["group_summaries"], snap["settings"])
    obs = format_observation_en(cards["measured_cpi"].observation)
    assert "group-average" in obs.lower() or "deviation of group-average" in obs.lower()
    assert "max_mean_deviation_pct" in (cards["measured_cpi"].observation.params if cards["measured_cpi"].observation else {})
    rows = dict(
        finding_metric_rows(
            "accuracy",
            snap["findings"]["accuracy"]["metrics"],
        )
    )
    assert "Maximum individual CPI error" in rows
    # Chart observation must not claim "Maximum error" alone as Accuracy metric.
    assert "Maximum error" not in obs or "individual" in obs.lower()
    note = cards["measured_cpi"].metric_note_en
    assert "group-average" in note.lower() or "group-average" in note.replace(" ", "").lower() or "deviation of group-average" in note.lower()
    assert "individual" in note.lower()


def test_tooltip_values_match_canonical_chart_group_data():
    session = _build_session(scale=0.92)  # ~8% → FAIL under Strict
    snap = session.to_session_dict()
    cards = build_v1_chart_cards(snap["group_summaries"], snap["settings"])
    err_card = cards["max_error"]
    by_dpi = {float(g["configured_dpi"]): g for g in snap["group_summaries"]}
    for pt in err_card.points:
        g = by_dpi[pt.configured_dpi]
        tip = err_card.point_tooltip_en(pt)
        assert str(int(pt.configured_dpi)) in tip
        assert f"{pt.value:.2f}%" in tip
        assert abs(pt.value - float(g["max_abs_error_pct"])) < 1e-9
        assert pt.status in tip
        if pt.trial_count is not None:
            assert f"Trials: {pt.trial_count}" in tip
            assert pt.trial_count == int(g["valid_trials"])


def test_zh_tw_primary_ui3a_keys_no_english_fallback():
    allowed_same = {
        # Intentional shared technical tokens / band strings
        "setup.accuracy.help.FIELD_STRICT",
        "setup.accuracy.help.FIELD_MEDIUM",
        "setup.accuracy.help.FIELD_LENIENT",
        "results.group.cv",
        "finding.metric.pq_warn",
        "finding.metric.pq_fail",
        "setup.dut",
        "status.PASS",
        "status.WARN",
        "status.FAIL",
        "status.NOT_TESTED",
        "status.NOT_EVALUATED",
        "status.SKIP",
    }
    for key in UI3A_OPERATOR_KEYS:
        assert key in _ZH_TW
        assert _ZH_TW[key] != key
        if key not in allowed_same:
            assert _ZH_TW[key] != _EN[key], key


def test_user_guide_theme_locale_do_not_change_session_evidence():
    session = _build_session()
    before = copy.deepcopy(session.to_session_dict())
    i18n = I18n("zh-TW")
    _ = i18n.t("help.guide.title")
    for a, b in USER_GUIDE_SECTIONS:
        _ = i18n.t(a)
        _ = i18n.t(b)
    # Locale catalog access must not mutate Session.
    after = session.to_session_dict()
    assert after["findings"] == before["findings"]
    assert after["group_summaries"] == before["group_summaries"]
    assert after["settings"] == before["settings"]
    assert "theme" not in after["settings"]
    assert CATALOGS["zh-TW"]["help.guide.title"] != CATALOGS["en-US"]["help.guide.title"]


def test_html_interpretation_guide_matches_session_thresholds(tmp_path: Path):
    session = _build_session(scale=0.96)
    snap = session.to_session_dict()
    html = render_html_report(snap, generated_at="FIXED")
    assert REPORT_INTERPRETATION_TITLE_EN in html
    assert "group-average" in html.lower() or "group-average deviation" in html.lower() or "≠" in html or "different metrics" in html.lower() or "maximum individual" in html.lower()
    assert CHART_CUES_EN["measured_cpi"] in html
    assert CHART_CUES_EN["max_error"] in html
    assert CHART_CUES_EN["repeatability"] in html
    assert "PASS ≤ 3%" in html
    assert "FAIL > 5%" in html
    # Medium policy updates automatically
    snap_m = copy.deepcopy(snap)
    snap_m["settings"] = {
        **snap_m["settings"],
        "cpi_error_pass_pct": 6.0,
        "cpi_error_fail_pct": 8.0,
        "tolerance_mode": "FIELD_MEDIUM",
    }
    html_m = render_html_report(snap_m, generated_at="FIXED")
    assert "PASS ≤ 6%" in html_m
    assert "FAIL > 8%" in html_m
    art = generate_report_bundle(snap, tmp_path, run_id="ui3a", generated_at="FIXED")
    assert art.html_path.is_file()
    # Bundle must not mutate session
    assert session.to_session_dict()["findings"] == snap["findings"]
