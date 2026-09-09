"""UI-1C — Trial lifecycle workspace + Session Domain synchronization."""

from __future__ import annotations

import pytest

from mouse_dpi_tool.measurement.accuracy_profile import FIELD_MEDIUM, FIELD_STRICT
from mouse_dpi_tool.session import Session
from mouse_dpi_tool.ui.controllers import AppController


def _axis_session() -> Session:
    session = Session(
        settings={
            "distance_mm": 100.0,
            "min_valid_trials_per_group": 1,
            "movement_mode": "Axis Projection",
            "tolerance_mode": FIELD_STRICT,
            "cpi_error_pass_pct": 3.0,
            "cpi_error_fail_pct": 5.0,
        },
        measurement_context={"method": "synthetic", "direction": "X+"},
    )
    session.add_synthetic_trial(configured_dpi=800, counts_x=3150, direction="X+")
    session.add_synthetic_trial(configured_dpi=1600, counts_x=6300, direction="X+")
    return session


def test_tables_match_session_buckets():
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.session = _axis_session()
    assert len(controller.session.active_trials) == 2
    controller.reject_trial(1)
    assert [t["trial_id"] for t in controller.session.active_trials] == [2]
    assert [t["trial_id"] for t in controller.session.rejected_trials] == [1]
    controller.delete_trial(1)
    assert [t["trial_id"] for t in controller.session.deleted_trials] == [1]
    assert controller.session.rejected_trials == []


def test_reject_restore_delete_rebuild_analysis_and_findings():
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.session = _axis_session()
    before = controller.session_snapshot()
    assert before["findings"]["accuracy"]["status"] in {"PASS", "WARN", "FAIL"}
    assert len(before["group_summaries"]) >= 1
    assert len(before["ratio_analysis"]) >= 1
    tid = controller.session.active_trials[0]["trial_id"]
    controller.reject_trial(tid)
    mid = controller.session_snapshot()
    active_ids = {int(t["trial_id"]) for t in controller.session.active_trials}
    assert int(tid) not in active_ids
    # Exported active trials list must not include rejected.
    assert all(int(t["trial_id"]) != int(tid) for t in mid.get("trials") or [])
    controller.restore_rejected_trial(tid)
    restored = controller.session_snapshot()
    assert int(tid) in {int(t["trial_id"]) for t in controller.session.active_trials}
    assert restored["findings"]["accuracy"]["status"] in {"PASS", "WARN", "FAIL"}
    controller.delete_trial(tid, reason="archive")
    after = controller.session_snapshot()
    assert int(tid) not in {int(t["trial_id"]) for t in controller.session.active_trials}
    assert after["group_summaries"] is not None


def test_stable_trial_id_preserved():
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.session = _axis_session()
    tid = int(controller.session.active_trials[0]["trial_id"])
    controller.reject_trial(tid)
    controller.restore_rejected_trial(tid)
    assert int(controller.session.active_trials[0]["trial_id"]) == tid or tid in {
        int(t["trial_id"]) for t in controller.session.active_trials
    }


def test_fixture_vector_table_hides_fake_direction():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.components.trial_workspace import TrialWorkspace

    _ = QApplication.instance() or QApplication([])
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.set_movement_mode("Vector Magnitude")
    # Build FV trial via compute path used by Session admit helpers.
    from mouse_dpi_tool.measurement.trial import compute_trial

    trial = compute_trial(
        trial_id=1,
        distance_mm=100.0,
        axis="X",
        direction="X+",
        counts_x=2000,
        counts_y=1500,
        configured_dpi=800,
        movement_mode="Vector Magnitude",
    )
    trial["accepted"] = True
    trial["rejected"] = False
    trial["deleted"] = False
    controller.session._active.append(trial)
    controller.session._rebuild_analysis()
    ws = TrialWorkspace(controller)
    ws.retranslate()
    ws.refresh()
    table = ws.tables["active"]
    assert table.rowCount() == 1
    direction_cell = table.item(0, 8).text()
    assert direction_cell == "—"
    assert "X+" not in direction_cell


def test_directional_axis_shows_direction():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.components.trial_workspace import TrialWorkspace

    _ = QApplication.instance() or QApplication([])
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.session = _axis_session()
    ws = TrialWorkspace(controller)
    ws.retranslate()
    ws.refresh()
    assert "X+" in ws.tables["active"].item(0, 8).text()


def test_sort_filter_do_not_change_evidence():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.components.trial_workspace import TrialWorkspace

    _ = QApplication.instance() or QApplication([])
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.session = _axis_session()
    before = controller.session_snapshot()
    ws = TrialWorkspace(controller)
    ws.retranslate()
    ws.refresh()
    ws.dpi_filter.setCurrentIndex(1)
    from PySide6.QtCore import Qt

    ws.tables["active"].sortByColumn(1, Qt.SortOrder.AscendingOrder)
    after = controller.session_snapshot()
    assert before["trials"] == after["trials"]
    assert before["findings"] == after["findings"]


def test_theme_locale_do_not_change_evidence():
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.session = _axis_session()
    before = controller.session_snapshot()
    controller.set_theme("dark")
    controller.set_locale("zh-TW")
    after = controller.session_snapshot()
    assert before["trials"] == after["trials"]
    assert before["findings"] == after["findings"]
    assert before["settings"]["tolerance_mode"] == after["settings"]["tolerance_mode"]


def test_accuracy_remains_locked_with_evidence():
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.session = _axis_session()
    assert controller.accuracy_criterion_locked is True
    with pytest.raises(RuntimeError, match="locked"):
        controller.set_accuracy_profile(FIELD_MEDIUM)


def test_new_test_session_clears_evidence_keeps_setup():
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.update_dut(vendor="Acme", model="Mouse-1")
    controller.set_accuracy_profile(FIELD_MEDIUM)
    controller.session = _axis_session()
    # Re-apply medium onto the replaced session for keep_setup path:
    controller.session.update_settings(
        {
            "tolerance_mode": FIELD_MEDIUM,
            "cpi_error_pass_pct": 6.0,
            "cpi_error_fail_pct": 8.0,
        }
    )
    controller.session.update_dut(vendor="Acme", model="Mouse-1")
    assert controller.accuracy_criterion_locked is True
    controller.new_test_session(keep_dut=True, keep_setup=True)
    assert controller.session.active_trials == []
    assert controller.accuracy_criterion_locked is False
    assert controller.session.dut["vendor"] == "Acme"
    assert controller.session.settings["cpi_error_pass_pct"] == 6.0
