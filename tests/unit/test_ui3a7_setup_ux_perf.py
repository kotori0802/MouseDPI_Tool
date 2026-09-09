"""UI-3A.7 — Setup distance/unit UX + presentation-trial perf."""

from __future__ import annotations

import pytest

from mouse_dpi_tool.session import Session
from mouse_dpi_tool.ui.controllers import AppController
from mouse_dpi_tool.ui.presentation_invalidation import COUNTERS, reset_presentation_instrumentation


def test_setup_unit_change_keeps_typed_number():
    """Type 2 then switch to inch → keep 2 (reinterpret), not convert 2 mm → inches."""
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import SetupPage

    _ = QApplication.instance() or QApplication([])
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    page = SetupPage(controller)
    page.distance.setValue(2.0)
    # Start from mm
    mm_idx = page.unit.findData("mm")
    page.unit.setCurrentIndex(mm_idx)
    page._unit_code = "mm"
    inch_idx = page.unit.findData("inch")
    page.unit.setCurrentIndex(inch_idx)
    assert page.distance.value() == pytest.approx(2.0)
    assert page._unit_code == "inch"
    assert "50.8" in page.distance_mm_preview.text().replace(",", "")


def test_presentation_trials_omit_capture_evidence():
    session = Session(
        settings={"distance_mm": 50.8, "min_valid_trials_per_group": 1},
        measurement_context={"method": "fixture", "direction": "N/A"},
        dut={"vendor": "T", "model": "M", "notes": ""},
        operator="ux",
    )
    session.add_synthetic_trial(
        configured_dpi=800,
        counts_x=1600,
        counts_y=0,
        capture_evidence={
            "state": "stopped",
            "complete": True,
            "integrity_ok": True,
            "valid_complete_capture": True,
            "published_count": 10,
            "device_ids": ["d"],
            "per_device_counts": {},
            "last_error": None,
            "subscriber_errors": [],
            "status_callback_errors": [],
            "issue_codes": [],
        },
    )
    full = session.active_trials[0]
    assert "capture_evidence" in full
    light = session.presentation_trials("active")[0]
    assert "capture_evidence" not in light
    assert light["trial_id"] == full["trial_id"]
    assert light["measured_cpi"] == full["measured_cpi"]


def test_idle_admit_path_skips_fixture_diag_when_tech_collapsed():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    reset_presentation_instrumentation()
    session = Session(
        settings={
            "distance_mm": 50.8,
            "min_valid_trials_per_group": 1,
            "movement_mode": "Vector Magnitude",
        },
        measurement_context={"method": "fixture", "direction": "N/A"},
        dut={"vendor": "T", "model": "M", "notes": ""},
        operator="perf",
    )
    for _ in range(40):
        session.add_synthetic_trial(configured_dpi=1600, counts_x=2120, counts_y=-2265)
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.session = session
    page = CapturePage(controller)
    page.tech_toggle.setChecked(False)
    page.refresh()
    assert COUNTERS.fixture_diag_renders == 0
    # Simulate lifecycle bump after Admit while idle / tech collapsed.
    from mouse_dpi_tool.ui.presentation_invalidation import REVISIONS

    REVISIONS.bump_trial_lifecycle()
    page._fixture_diag_fp = None
    page.refresh()
    assert COUNTERS.fixture_diag_renders == 0
