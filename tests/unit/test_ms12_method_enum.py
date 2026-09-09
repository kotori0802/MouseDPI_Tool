"""MS-1.2 — canonical measurement_context.method enum + Setup apply path."""

from __future__ import annotations

from pathlib import Path

import pytest

from mouse_dpi_tool.contracts.measurement_method import MeasurementMethodError
from mouse_dpi_tool.reporting import generate_report_bundle
from mouse_dpi_tool.session import Session, SessionValidationError, validate_session
from mouse_dpi_tool.ui.controllers import AppController


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


def _perfect_counts(dpi: int, distance_mm: float = 100.0) -> int:
    return int(round(dpi * (distance_mm / 25.4)))


def test_update_measurement_context_rejects_unknown123():
    session = _session()
    with pytest.raises(MeasurementMethodError, match="unknown123"):
        session.update_measurement_context(method="unknown123")
    assert session.measurement_context["method"] == "synthetic"


def test_canonical_method_fixture_accepted():
    session = _session()
    session.update_measurement_context(method="fixture")
    assert session.measurement_context["method"] == "fixture"
    validate_session(session.to_session_dict())


def test_report_generate_succeeds_with_valid_method(tmp_path: Path):
    session = _session()
    for _ in range(3):
        session.add_synthetic_trial(
            configured_dpi=800, counts_x=_perfect_counts(800), counts_y=0
        )
    art = generate_report_bundle(session.to_session_dict(), tmp_path, run_id="ms12_ok")
    assert art.html_path.is_file()
    assert art.json_path.is_file()


def test_validate_session_fails_cleanly_on_injected_invalid_method(tmp_path: Path):
    session = _session()
    for _ in range(3):
        session.add_synthetic_trial(
            configured_dpi=800, counts_x=_perfect_counts(800), counts_y=0
        )
    payload = session.to_session_dict()
    payload["measurement_context"] = {
        **payload["measurement_context"],
        "method": "unknown123",
    }
    with pytest.raises(SessionValidationError, match="method"):
        validate_session(payload)
    with pytest.raises(SessionValidationError, match="method"):
        generate_report_bundle(payload, tmp_path, run_id="ms12_bad")
    assert not any(tmp_path.iterdir()), "invalid method must not leave partial report files"


@pytest.fixture
def qapp():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_setup_apply_cannot_commit_unknown123(qapp):
    from PySide6.QtWidgets import QComboBox

    from mouse_dpi_tool.ui.components.combo import combo_data
    from mouse_dpi_tool.ui.views.pages import SetupPage

    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    page = SetupPage(controller)
    assert isinstance(page.method, QComboBox)
    assert page.method.isEditable() is False
    assert page.method.findData("unknown123") < 0

    idx = page.method.findData("fixture")
    assert idx >= 0
    page.method.setCurrentIndex(idx)
    page._apply()
    assert controller.session.measurement_context["method"] == "fixture"
    assert combo_data(page.method, "unknown") == "fixture"

    # Free-text commit path is gone: apply always uses combo item data.
    with pytest.raises(MeasurementMethodError):
        controller.update_measurement_context(method="unknown123")
    assert controller.session.measurement_context["method"] == "fixture"
