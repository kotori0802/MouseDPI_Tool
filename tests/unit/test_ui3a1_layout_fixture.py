"""UI-3A.1 — layout robustness + fixture/motion diagnostic feasibility."""

from __future__ import annotations

import copy
import math

import pytest

from mouse_dpi_tool.reporting.fixture_motion import (
    build_fixture_motion_diagnostics,
    circular_mean_deg,
    circular_spread_deg,
    endpoint_heading_deg,
    path_excess_pct,
)
from mouse_dpi_tool.session import Session
from mouse_dpi_tool.ui.controllers import AppController


def _fixture_session() -> Session:
    return Session(
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
        operator="ui3a1",
    )


def test_endpoint_heading_all_quadrants():
    assert abs(endpoint_heading_deg(100, 0) - 0.0) < 1e-9
    assert abs(endpoint_heading_deg(0, 100) - 90.0) < 1e-9
    assert abs(endpoint_heading_deg(-100, 0) - 180.0) < 1e-9 or abs(
        endpoint_heading_deg(-100, 0) + 180.0
    ) < 1e-9
    assert abs(endpoint_heading_deg(0, -100) + 90.0) < 1e-9
    # 45° diagonal
    assert abs(endpoint_heading_deg(100, 100) - 45.0) < 1e-9


def test_circular_mean_and_spread_handle_wrap():
    # Angles around ±180 wrap: 170, 180, -170 → mean near 180, small spread
    angles = [170.0, 180.0, -170.0]
    mean = circular_mean_deg(angles)
    assert mean is not None
    assert abs(abs(mean) - 180.0) < 5.0 or abs(mean) > 170.0
    spread = circular_spread_deg(angles)
    assert spread is not None
    assert spread < 25.0
    # Naive arithmetic mean would be wrong (~60); circular mean stays near 180.
    naive = sum(angles) / len(angles)
    assert abs(naive) < 100.0  # proves wrap trap exists
    assert abs(abs(mean) - abs(naive)) > 50.0


def test_path_excess_reuses_canonical_ratio():
    assert path_excess_pct(100.0, 100.0) == pytest.approx(0.0)
    assert path_excess_pct(110.0, 100.0) == pytest.approx(10.0)
    assert path_excess_pct(0.0, 100.0) is None
    assert path_excess_pct(50.0, 0.0) is None


def test_fixture_diagnostics_from_canonical_trial_fields_only():
    trial = {
        "movement_mode": "Vector Magnitude",
        "counts_x": 600,
        "counts_y": 600,
        "vector_counts": int(round(math.hypot(600, 600))),
        "path_total_counts": float(round(math.hypot(600, 600))) * 1.01,
        "straightness_pct": 99.0,
    }
    diag = build_fixture_motion_diagnostics([trial])
    assert diag.trial_count == 1
    assert diag.avg_straightness_pct == pytest.approx(99.0)
    assert diag.max_path_excess_pct == pytest.approx(1.0, abs=0.05)
    assert diag.mean_heading_deg == pytest.approx(45.0, abs=0.1)
    assert diag.heading_spread_deg == pytest.approx(0.0)
    assert "descriptive" in diag.notes[0].lower()


def test_fixture_diagnostics_do_not_alter_findings():
    session = _fixture_session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=800, counts_y=0)
    before = copy.deepcopy(session.to_session_dict()["findings"])
    trials = list(session.active_trials)
    for t in trials:
        t = dict(t)
        t["path_total_counts"] = float(t.get("vector_counts") or 1) * 1.02
        t["straightness_pct"] = 98.0
        _ = build_fixture_motion_diagnostics([t])
    after = session.to_session_dict()["findings"]
    assert after == before
    # No Overall / Fixture Finding keys invented
    assert "fixture" not in after
    assert "overall" not in after


def test_no_fixture_verdict_in_diagnostic_output():
    diag = build_fixture_motion_diagnostics(
        [
            {
                "movement_mode": "Vector Magnitude",
                "counts_x": 100,
                "counts_y": 20,
                "vector_counts": 102,
                "path_total_counts": 110,
                "straightness_pct": 92.7,
            }
        ]
    )
    blob = " ".join(diag.notes).lower()
    assert "crooked" not in blob
    assert "defective" not in blob
    assert "pass/fail" not in blob or "no" in blob
    assert "descriptive" in blob


def test_empty_trial_table_headers_fit_sections():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.components.trial_workspace import TrialWorkspace
    from mouse_dpi_tool.ui.layout_metrics import header_min_section_widths

    _ = QApplication.instance() or QApplication([])
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    ws = TrialWorkspace(controller)
    ws.retranslate()
    table = ws.tables["active"]
    assert table.rowCount() == 0
    mins = header_min_section_widths(table)
    header = table.horizontalHeader()
    for col, mn in enumerate(mins):
        assert header.sectionSize(col) >= mn - 1, (
            f"col {col} clipped: size={header.sectionSize(col)} min={mn} "
            f"text={table.horizontalHeaderItem(col).text()!r}"
        )
        text = table.horizontalHeaderItem(col).text()
        assert text
        # First glyph must not be missing from label itself
        assert not text.startswith("rial")
        assert not text.startswith("igured")


def test_locale_change_recomputes_header_mins_without_touching_evidence():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.components.trial_workspace import TrialWorkspace
    from mouse_dpi_tool.ui.layout_metrics import header_min_section_widths

    _ = QApplication.instance() or QApplication([])
    session = _fixture_session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=1000, counts_y=0)
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.session = session
    before = copy.deepcopy(controller.session.to_session_dict())
    ws = TrialWorkspace(controller)
    ws.retranslate()
    ws.refresh()
    en_mins = header_min_section_widths(ws.tables["active"])
    controller.set_locale("zh-TW")
    ws.retranslate()
    zh_mins = header_min_section_widths(ws.tables["active"])
    header = ws.tables["active"].horizontalHeader()
    for col, mn in enumerate(zh_mins):
        assert header.sectionSize(col) >= mn - 1
    after = controller.session.to_session_dict()
    assert after["findings"] == before["findings"]
    assert after["trials"] == before["trials"]
    assert after["group_summaries"] == before["group_summaries"]
    # Width policy may differ by glyph metrics; both must be positive.
    assert all(w > 40 for w in en_mins + zh_mins)


def test_preset_combo_sizehint_fits_localized_label():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.components.dpi_field import ConfiguredDpiField
    from mouse_dpi_tool.ui.layout_metrics import combo_min_width_for_items

    _ = QApplication.instance() or QApplication([])
    field = ConfiguredDpiField()
    for label in ("Presets", "預設值", "Voreinstellungen", "Préréglages", "Presets"):
        field.retranslate(presets_label=label)
        need = combo_min_width_for_items(field.combo)
        assert field.combo.minimumWidth() >= need - 1
        assert field.combo.maximumWidth() >= need
        # Closed label text width must fit inside min width budget.
        fm = field.combo.fontMetrics()
        assert fm.boundingRect(label).width() + 20 <= field.combo.minimumWidth()


def test_layout_and_theme_locale_preserve_evidence_fingerprint():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.components.trial_workspace import TrialWorkspace

    _ = QApplication.instance() or QApplication([])
    session = _fixture_session()
    session.add_synthetic_trial(configured_dpi=400, counts_x=400, counts_y=400)
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.session = session
    before = copy.deepcopy(controller.session.to_session_dict())
    ws = TrialWorkspace(controller)
    ws.retranslate()
    ws.refresh()
    controller.set_theme("dark")
    controller.set_locale("zh-TW")
    ws.retranslate()
    ws.refresh()
    after = controller.session.to_session_dict()
    assert after["findings"] == before["findings"]
    assert after["settings"] == before["settings"]
    assert after["group_summaries"] == before["group_summaries"]


def test_methodology_example_does_not_encode_specific_session():
    """400 vs 800 pattern is methodology commentary only — not production thresholds."""
    import inspect

    import mouse_dpi_tool.reporting.fixture_motion as mod

    src = inspect.getsource(mod)
    assert "768.9" not in src
    assert "393.9" not in src
    assert "1.9521" not in src
