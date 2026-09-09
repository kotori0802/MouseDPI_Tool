"""Setup Phase 1.5 — slim operator surface (no lab Optional form)."""

from __future__ import annotations

import pytest


@pytest.fixture
def qapp():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_setup_operator_fields_only_no_lab_optional(qapp):
    from PySide6.QtWidgets import QScrollArea

    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.pages import SetupPage

    controller = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = SetupPage(controller)
    page.resize(1280, 800)
    page.show()
    qapp.processEvents()

    assert isinstance(page._setup_scroll, QScrollArea)
    assert page._setup_scroll.widgetResizable() is True
    from mouse_dpi_tool.ui.layout_metrics import SETUP_WORKSPACE_MAX_WIDTH

    assert page._form_card.maximumWidth() == SETUP_WORKSPACE_MAX_WIDTH

    # Operator-facing controls present.
    for name in (
        "vendor",
        "model",
        "method",
        "distance",
        "unit",
        "geometry",
        "accuracy",
        "ctx_notes",
        "apply_btn",
        "revert_btn",
    ):
        assert hasattr(page, name)

    # Lab metadata editors removed from Setup UI (schema still retained elsewhere).
    for gone in (
        "notes",
        "surface",
        "fixture_type",
        "dpi_configuration_source",
        "control_software_state",
        "control_software_name",
        "control_software_version",
        "profile_note",
        "measurement_system_uncertainty_note",
        "reference_uncertainty_pct",
        "meta_panel",
        "meta_toggle",
    ):
        assert not hasattr(page, gone)

    # Idle: Apply/Revert disabled (no operator dirty).
    assert page.apply_btn.isEnabled() is False
    assert page.revert_btn.isEnabled() is False

    page.vendor.setText("ExampleVendor")
    qapp.processEvents()
    assert page.apply_btn.isEnabled() is True
    assert page.revert_btn.isEnabled() is True


def test_setup_apply_preserves_hidden_metadata(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.pages import SetupPage

    controller = AppController(preferences={"theme": "dark", "locale": "en-US"})
    controller.update_dut(vendor="", model="", notes="legacy-dut-note")
    controller.update_measurement_context(
        surface="reference hard pad",
        fixture_type="rail contact",
        control_software_version="2026.8",
        reference_uncertainty_pct=1.0,
        dpi_configuration_source="vendor_software",
    )
    page = SetupPage(controller)
    page.show()
    qapp.processEvents()
    page.vendor.setText("ExampleVendor")
    page.apply_btn.click()
    qapp.processEvents()

    dut = controller.session.dut
    ctx = controller.session.measurement_context
    assert dut["vendor"] == "ExampleVendor"
    assert dut["notes"] == "legacy-dut-note"
    assert ctx["surface"] == "reference hard pad"
    assert ctx["fixture_type"] == "rail contact"
    assert ctx["control_software_version"] == "2026.8"
    assert float(ctx["reference_uncertainty_pct"]) == pytest.approx(1.0)
    assert ctx["dpi_configuration_source"] == "vendor_software"
