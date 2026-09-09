"""UI-3A.3 — axial Fixture Vector diagnostics + procedure/help boundaries."""

from __future__ import annotations

import copy
import inspect
import math

import pytest

from mouse_dpi_tool.reporting.fixture_motion import (
    axial_mean_deg,
    axial_spread_deg,
    build_fixture_motion_diagnostics,
    circular_mean_deg,
    circular_spread_deg,
    endpoint_heading_deg,
    format_fixture_motion_lines,
    travel_polarity,
)
from mouse_dpi_tool.session import Session
from mouse_dpi_tool.ui.help_content import FINDING_HELP_EN
from mouse_dpi_tool.ui.i18n import I18n


def _fv(counts_x: float, counts_y: float, dpi: float = 800) -> dict:
    vec = math.hypot(counts_x, counts_y)
    return {
        "movement_mode": "Vector Magnitude",
        "configured_dpi": dpi,
        "counts_x": counts_x,
        "counts_y": counts_y,
        "vector_counts": int(round(vec)),
        "path_total_counts": vec * 1.01,
        "straightness_pct": 99.0,
    }


def test_axial_theta_and_theta_plus_180_same_axis():
    # −47° and +133° are the same undirected axis.
    a = -47.0
    b = a + 180.0
    mean = axial_mean_deg([a, b])
    spread = axial_spread_deg([a, b])
    assert mean is not None
    assert spread is not None
    # Orientation lands near −47° (or equivalent in (−90, 90])
    assert abs(mean - (-47.0)) < 1.0 or abs(mean - 133.0) < 1.0
    # Axial spread must stay small — unlike directional 360° SD.
    assert spread < 2.0
    dir_spread = circular_spread_deg([a, b])
    assert dir_spread is not None
    assert dir_spread > 50.0  # proves old 360° treatment would inflate


def test_axial_spread_small_for_opposite_travel_same_axis():
    # Cluster around −47° mixed with exact reverse +133°
    headings = [-47.0, -46.8, -47.2, 133.0, 132.5, 133.5]
    spread = axial_spread_deg(headings)
    assert spread is not None
    assert spread < 5.0
    naive360 = circular_spread_deg(headings)
    assert naive360 is not None
    assert naive360 > 40.0


def test_axial_wrap_plus_minus_180():
    # Near ±90 axis wrap in orientation space
    headings = [89.0, -89.0]  # nearly opposite directions on near-vertical axis
    mean = axial_mean_deg(headings)
    spread = axial_spread_deg(headings)
    assert mean is not None
    assert spread is not None
    # Same axis (vertical-ish); axial spread tiny
    assert spread < 2.0
    # Mean near ±90
    assert abs(abs(mean) - 90.0) < 2.0 or abs(mean) < 2.0


def test_fixture_diagnostics_use_axial_not_directional_sd():
    trials = [
        _fv(100 * math.cos(math.radians(-47)), 100 * math.sin(math.radians(-47))),
        _fv(100 * math.cos(math.radians(133)), 100 * math.sin(math.radians(133))),
    ]
    diag = build_fixture_motion_diagnostics(trials)
    assert diag.axis_orientation_deg is not None
    assert diag.axis_spread_deg is not None
    assert diag.axis_spread_deg < 2.0
    # Alias preserved
    assert diag.mean_heading_deg == diag.axis_orientation_deg
    assert diag.heading_spread_deg == diag.axis_spread_deg
    lines = "\n".join(format_fixture_motion_lines(diag)).lower()
    assert "axis" in lines
    assert diag.forward_trials + diag.reverse_trials == 2
    assert diag.forward_trials == 1 and diag.reverse_trials == 1


def test_travel_polarity_descriptive_only():
    assert travel_polarity(-47.0, -47.0) == "forward"
    assert travel_polarity(133.0, -47.0) == "reverse"
    assert travel_polarity(-47.0, 133.0) == "reverse"


def test_directional_axis_semantics_unchanged_by_fixture_module():
    """Directional Axis remains oriented; fixture axial helpers are FV-only."""
    # Ordinary circular helpers still available for oriented angles.
    mean = circular_mean_deg([0.0, 10.0, -10.0])
    assert mean is not None
    assert abs(mean) < 1.0
    # Endpoint heading still atan2-based (used by DA presentation elsewhere).
    assert endpoint_heading_deg(100, 0) == pytest.approx(0.0)
    assert endpoint_heading_deg(0, 100) == pytest.approx(90.0)
    # Non-FV trials ignored by fixture diagnostics.
    da = {
        "movement_mode": "Axis Projection",
        "configured_dpi": 800,
        "counts_x": 800,
        "counts_y": 0,
        "direction": "X+",
    }
    diag = build_fixture_motion_diagnostics([da, _fv(100, 100)])
    assert diag.trial_count == 1
    assert diag.axis_orientation_deg == pytest.approx(45.0, abs=0.2)


def test_fixture_diagnostics_do_not_modify_findings():
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
        operator="ui3a3",
    )
    session.add_synthetic_trial(configured_dpi=800, counts_x=500, counts_y=500)
    before = copy.deepcopy(session.to_session_dict())
    enriched = []
    for t in session.active_trials:
        row = dict(t)
        row["path_total_counts"] = float(row.get("vector_counts") or 1) * 1.01
        row["straightness_pct"] = 99.0
        enriched.append(row)
    _ = build_fixture_motion_diagnostics(enriched)
    after = session.to_session_dict()
    assert after["findings"] == before["findings"]
    assert "fixture" not in after["findings"]
    assert after["group_summaries"] == before["group_summaries"]


def test_procedure_help_text_not_in_session_json():
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
        dut={
            "vendor": "T",
            "model": "M",
            "notes": "Fixture procedure: carriage preloaded against reference edge before Capture.",
        },
        operator="ui3a3",
    )
    session.add_synthetic_trial(configured_dpi=400, counts_x=400, counts_y=0)
    blob = str(session.to_session_dict())
    # Canonical DUT notes may appear; UI help / catalog strings must not.
    assert "capture.procedure_hint" not in blob
    assert "how_to_measure_body" not in blob
    assert "Before Start, seat the carriage" not in blob
    assert "開始前先將載台貼靠" not in blob
    assert "finding.help.path_quality" not in blob


def test_path_quality_help_wording_boundary_no_formula_change():
    text = FINDING_HELP_EN["path_quality"].lower()
    assert "reversal" in text or "jitter" in text
    assert "straightness" in text or "perfect" in text
    assert "tracking quality" not in text
    import mouse_dpi_tool.ui.help_content as hc
    import mouse_dpi_tool.path_quality as pq

    hsrc = inspect.getsource(hc)
    # Help must not redefine Path Quality numeric thresholds.
    assert "fail_pct" not in hsrc
    assert "PATH_QUALITY_REVERSAL" not in hsrc
    # Formula module still owns evaluation.
    assert "straightness" in inspect.getsource(pq).lower() or "path_total" in inspect.getsource(
        pq
    ).lower()


def test_locale_theme_do_not_alter_axial_values():
    trials = [
        _fv(100, -100, 800),
        _fv(-100, 100, 800),  # +180° polarity
    ]
    en = I18n("en-US")
    zh = I18n("zh-TW")
    d1 = build_fixture_motion_diagnostics(trials)
    d2 = build_fixture_motion_diagnostics(trials)
    assert d1.axis_orientation_deg == d2.axis_orientation_deg
    assert d1.axis_spread_deg == d2.axis_spread_deg
    # Presentation strings differ; numeric diagnostics identical
    l_en = format_fixture_motion_lines(d1, t=en.t)
    l_zh = format_fixture_motion_lines(d1, t=zh.t)
    assert d1.axis_spread_deg is not None
    assert d1.axis_spread_deg < 2.0
    assert any("°" in line for line in l_en)
    assert l_en != l_zh


def test_no_v15_residual_reads_pathcanvas():
    import mouse_dpi_tool.reporting.fixture_motion as fm

    src = inspect.getsource(fm)
    assert "from mouse_dpi_tool.ui" not in src
    assert "import PathCanvas" not in src
    assert "path_canvas" not in src
    # Production module must not implement V1.5 residual metrics.
    assert "residual_rms" not in src
    assert "cross_track" not in src
    # Docstring may mention PathCanvas as a forbidden source — that is intentional.
    assert "never PathCanvas" in src or "never" in src.lower()


def test_procedure_catalog_keys_present():
    en = I18n("en-US")
    zh = I18n("zh-TW")
    assert "seat" in en.t("capture.procedure_hint").lower() or "reference" in en.t(
        "capture.procedure_hint"
    ).lower()
    assert "貼靠" in zh.t("capture.procedure_hint")
    body = en.t("capture.how_to_measure_body").lower()
    assert "before" in body and "start" in body
    assert "re-seat" in body or "re-center" in body or "do not" in body
    pq = en.t("finding.help.path_quality").lower()
    assert "perfect" in pq or "straightness" in pq


def test_methodology_numbers_not_hardcoded_in_production():
    import mouse_dpi_tool.reporting.fixture_motion as mod

    src = inspect.getsource(mod)
    for token in ("391.1", "755.6", "1557.2", "3003.0", "3.4116", "57.9"):
        assert token not in src
