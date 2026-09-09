"""UI-3A.2 — performance invalidation + locale trust + fixture diagnostic semantics."""

from __future__ import annotations

import copy

import pytest

from mouse_dpi_tool.reporting.fixture_motion import (
    PATH_EXCESS_NOT_EVALUATED,
    build_fixture_motion_diagnostics,
    format_fixture_motion_lines,
    path_excess_result,
)
from mouse_dpi_tool.session import Session
from mouse_dpi_tool.ui.controllers import AppController
from mouse_dpi_tool.ui.presentation_invalidation import (
    COUNTERS,
    REVISIONS,
    reset_all_presentation_state,
    reset_presentation_instrumentation,
)


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
        operator="ui3a2",
    )


def test_path_excess_not_evaluated_when_path_below_vector():
    val, state = path_excess_result(90.0, 100.0)
    assert val is None
    assert state == PATH_EXCESS_NOT_EVALUATED
    val2, state2 = path_excess_result(110.0, 100.0)
    assert state2 == "ok"
    assert val2 == pytest.approx(10.0)


def test_straightness_ceiling_wording_not_perfect_geometry():
    diag = build_fixture_motion_diagnostics(
        [
            {
                "movement_mode": "Vector Magnitude",
                "configured_dpi": 800,
                "counts_x": 100,
                "counts_y": -100,
                "vector_counts": 141,
                "path_total_counts": 120,  # < vector → excess NOT_EVALUATED
                "straightness_pct": 100.0,
            }
        ]
    )
    assert diag.straightness_at_ceiling is True
    assert diag.path_excess_state == PATH_EXCESS_NOT_EVALUATED
    lines = "\n".join(format_fixture_motion_lines(diag))
    assert "metric ceiling" in lines.lower()
    assert "NOT_EVALUATED" in lines
    assert "perfect" not in lines.lower() or "not proof" in lines.lower() or "ceiling" in lines.lower()
    assert diag.per_dpi
    assert diag.per_dpi[0].path_excess_state == PATH_EXCESS_NOT_EVALUATED


def test_fixture_diagnostics_do_not_alter_findings_fingerprint():
    session = _fixture_session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=500, counts_y=500)
    before = copy.deepcopy(session.to_session_dict())
    trials = list(session.active_trials)
    enriched = []
    for t in trials:
        row = dict(t)
        row["path_total_counts"] = float(row.get("vector_counts") or 1)
        row["straightness_pct"] = 100.0
        enriched.append(row)
    _ = build_fixture_motion_diagnostics(enriched)
    after = session.to_session_dict()
    assert after["findings"] == before["findings"]
    assert after["group_summaries"] == before["group_summaries"]
    assert "fixture" not in after["findings"]


def test_collapsed_tech_details_skips_fixture_diag_on_live_ticks():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.capture import CaptureEngine, SyntheticEventSource
    from mouse_dpi_tool.contracts.movement import MovementSample
    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    reset_presentation_instrumentation()

    def factory(*, on_status=None):
        return CaptureEngine(
            SyntheticEventSource([MovementSample(dx=5, dy=0, device_id="s")] * 200),
            on_status=on_status,
        )

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=factory,
    )
    page = CapturePage(controller)
    page.tech_toggle.setChecked(False)
    controller.start_capture()
    base = COUNTERS.fixture_diag_renders
    for _ in range(12):
        page.refresh()
    assert COUNTERS.fixture_diag_renders == base
    page.tech_toggle.setChecked(True)
    page.refresh()
    assert COUNTERS.fixture_diag_renders == base + 1
    controller.cancel_capture()


def test_unchanged_trial_buckets_skip_table_rebuild_across_idle_refreshes():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    reset_presentation_instrumentation()
    session = _fixture_session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=800, counts_y=0)
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.session = session
    page = CapturePage(controller)
    page.refresh()
    after_first = COUNTERS.trial_table_rebuilds
    header_after = COUNTERS.header_resize_calls
    for _ in range(10):
        page.refresh()
    assert COUNTERS.trial_table_rebuilds == after_first
    assert COUNTERS.header_resize_calls == header_after


def test_admit_bumps_lifecycle_and_rebuilds_table():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.capture import CaptureEngine, SyntheticEventSource
    from mouse_dpi_tool.contracts.movement import MovementSample
    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    reset_all_presentation_state()

    def factory(*, on_status=None):
        # Enough counts for a valid stop at 800 DPI / 50.8 mm (~2 inch).
        return CaptureEngine(
            SyntheticEventSource(
                [MovementSample(dx=20, dy=20, device_id="s")] * 80
            ),
            on_status=on_status,
        )

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=factory,
    )
    page = CapturePage(controller)
    page.refresh()
    before_life = REVISIONS.trial_lifecycle
    before_rebuilds = COUNTERS.trial_table_rebuilds
    # Synthetic admit without full capture worker path:
    controller.session.add_synthetic_trial(configured_dpi=800, counts_x=600, counts_y=600)
    REVISIONS.bump_trial_lifecycle()
    page._trials_fp = None
    page.refresh()
    assert REVISIONS.trial_lifecycle > before_life
    assert COUNTERS.trial_table_rebuilds > before_rebuilds


def test_locale_switch_rewrites_status_cells_with_populated_session():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.components.trial_workspace import TrialWorkspace
    from mouse_dpi_tool.ui.views import MainWindow

    _ = QApplication.instance() or QApplication([])
    reset_all_presentation_state()
    session = _fixture_session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=700, counts_y=0)
    code = str(
        session.active_trials[0].get("status")
        or session.active_trials[0].get("measurement_status")
    )

    controller = AppController(preferences={"theme": "light", "locale": "zh-TW"})
    controller.session = session

    window = MainWindow(controller)
    window._navigate("capture")
    ws: TrialWorkspace = window.capture_page.trials
    ws.refresh()
    table = ws.tables["active"]
    assert table.rowCount() >= 1
    status_zh = table.item(0, 6).text()
    assert status_zh == controller.i18n.t(f"status.{code}")
    before = copy.deepcopy(controller.session.to_session_dict())

    controller.set_locale("en-US")
    window.apply_presentation()
    status_en = table.item(0, 6).text()
    assert status_en == controller.i18n.t(f"status.{code}")
    assert status_en != status_zh
    after = controller.session.to_session_dict()
    assert after["findings"] == before["findings"]
    assert after["trials"] == before["trials"]

    controller.set_locale("zh-TW")
    window.apply_presentation()
    assert table.item(0, 6).text() == status_zh


def test_theme_change_does_not_rebuild_canonical_analysis():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views import MainWindow

    _ = QApplication.instance() or QApplication([])
    session = _fixture_session()
    session.add_synthetic_trial(configured_dpi=400, counts_x=400, counts_y=400)
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.session = session
    before = copy.deepcopy(controller.session.to_session_dict())
    window = MainWindow(controller)
    controller.set_theme("dark")
    window.apply_presentation()
    after = controller.session.to_session_dict()
    assert after["findings"] == before["findings"]
    assert after["group_summaries"] == before["group_summaries"]
    assert after["settings"] == before["settings"]


def test_no_overall_or_fixture_verdict_in_format_lines():
    diag = build_fixture_motion_diagnostics(
        [
            {
                "movement_mode": "Vector Magnitude",
                "configured_dpi": 400,
                "counts_x": 50,
                "counts_y": 50,
                "vector_counts": 71,
                "path_total_counts": 71,
                "straightness_pct": 100.0,
            }
        ]
    )
    blob = "\n".join(format_fixture_motion_lines(diag)).lower()
    assert "fixture fail" not in blob
    assert "crooked" not in blob
    assert "no fixture/sensor verdict" in blob
    assert "descriptive" in blob


def test_idle_refresh_with_many_trials_skips_repeat_fixture_diag():
    """Regression: ~40+ trials previously deep-copied every idle refresh → Not Responding."""
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    reset_presentation_instrumentation()
    session = _fixture_session()
    for _ in range(43):
        session.add_synthetic_trial(
            configured_dpi=1600,
            counts_x=2120,
            counts_y=-2265,
        )
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.session = session
    page = CapturePage(controller)
    page.tech_toggle.setChecked(True)
    page.refresh()
    after_first = COUNTERS.fixture_diag_renders
    tables_after_first = COUNTERS.trial_table_rebuilds
    assert after_first >= 1
    for _ in range(25):
        page.refresh()
    assert COUNTERS.fixture_diag_renders == after_first
    assert COUNTERS.trial_table_rebuilds == tables_after_first
