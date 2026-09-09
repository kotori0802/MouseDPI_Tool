"""UI-1A — direction selector, guided lane, presentation invariance."""

from __future__ import annotations

from pathlib import Path

import pytest

from mouse_dpi_tool.ui.controllers import AppController
from mouse_dpi_tool.ui.direction import (
    CANONICAL_DIRECTIONS,
    axis_for_direction,
    canonicalize_direction,
    lane_orientation,
)
from mouse_dpi_tool.ui.i18n import I18n, SHELL_REQUIRED_KEYS


@pytest.fixture
def qapp():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_canonical_direction_contract_maps_four_choices():
    expected = {
        "X+": ("X", "horizontal_ltr"),
        "X-": ("X", "horizontal_rtl"),
        "Y+": ("Y", "vertical_btt"),
        "Y-": ("Y", "vertical_ttb"),
    }
    assert CANONICAL_DIRECTIONS == ("X+", "X-", "Y+", "Y-")
    for code, (axis, orient) in expected.items():
        assert canonicalize_direction(code) == code
        assert axis_for_direction(code) == axis
        assert lane_orientation(code) == orient


def test_controller_direction_flows_to_existing_session_fields():
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    ctx0 = controller.session.measurement_context["direction"]
    for code in CANONICAL_DIRECTIONS:
        controller.set_direction(code)
        assert controller.direction == code
        assert controller.axis == axis_for_direction(code)
        # Per-trial fields are authoritative; top-level context must not track UI selection.
        assert controller.session.measurement_context["direction"] == ctx0
        snap = controller.session_snapshot()
        assert "direction_code" not in snap


def test_locale_changes_direction_label_not_canonical_evidence():
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.set_direction("Y-")
    before_dir = controller.direction
    before_ctx = controller.session.measurement_context["direction"]
    en_label = controller.i18n.direction("Y-")
    controller.set_locale("zh-TW")
    zh_label = controller.i18n.direction("Y-")
    assert en_label != zh_label
    assert controller.direction == before_dir == "Y-"
    assert controller.session.measurement_context["direction"] == before_ctx
    assert "→" not in controller.direction


def test_direction_keys_in_shell_inventory_and_all_locales():
    for key in (
        "capture.direction",
        "capture.instruction",
        "capture.lane.start",
        "capture.lane.target",
        "direction.X+",
        "direction.X-",
        "direction.Y+",
        "direction.Y-",
    ):
        assert key in SHELL_REQUIRED_KEYS
    for locale in ("en-US", "zh-TW", "zh-CN", "ja-JP", "ko-KR", "de-DE", "fr-FR", "es-ES"):
        i18n = I18n(locale)
        for code in CANONICAL_DIRECTIONS:
            text = i18n.direction(code)
            assert text and text != f"direction.{code}"
            assert code in text


def test_guided_lane_orientation_follows_direction(qapp):
    from mouse_dpi_tool.ui.components.guided_lane import GuidedLane

    _ = qapp
    lane = GuidedLane()
    for code in CANONICAL_DIRECTIONS:
        lane.set_direction(code)
        assert lane.direction == code
        assert lane.orientation == lane_orientation(code)


def test_capture_page_direction_combo_preserves_canonical(qapp):
    from mouse_dpi_tool.ui.components.combo import combo_data
    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = qapp
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    page = CapturePage(controller)
    idx = page.direction.findData("Y+")
    assert idx >= 0
    page.direction.setCurrentIndex(idx)
    assert combo_data(page.direction) == "Y+"
    assert controller.direction == "Y+"
    assert controller.axis == "Y"
    assert page.lane.orientation == "vertical_btt"
    distance_before = float(controller.session.settings["distance_mm"])
    controller.set_locale("ja-JP")
    page.retranslate()
    assert controller.session.settings["distance_mm"] == pytest.approx(distance_before)
    assert combo_data(page.direction) == "Y+"
    assert page.direction.currentText() != "Y+"


def test_admit_writes_axis_and_direction_not_localized_label():
    from mouse_dpi_tool.capture import CaptureEngine, SyntheticEventSource
    from mouse_dpi_tool.contracts.movement import MovementSample

    def factory(*, on_status=None):
        return CaptureEngine(
            source=SyntheticEventSource([MovementSample(dx=0, dy=-3150, device_id="synth")]),
            on_status=on_status,
        )

    controller = AppController(
        preferences={"theme": "light", "locale": "zh-TW"},
        engine_factory=factory,
    )
    controller.set_movement_mode("Axis Projection")
    controller.set_direction("Y+")
    controller.set_configured_dpi(800)
    controller.start_capture()
    assert controller._engine is not None
    controller._engine.wait_until_idle()
    controller.stop_capture()
    trial = controller.admit_capture()
    assert trial["axis"] == "Y"
    assert trial["direction"] == "Y+"
    assert "下" not in trial["direction"]
    assert "→" not in trial["direction"]


def test_no_circle_or_extreme_dpi_ui_modules():
    root = Path(__file__).resolve().parents[2] / "src" / "mouse_dpi_tool" / "ui"
    banned = ("circle", "figure8", "figure_8", "extreme_dpi", "sensor_db", "compare_dut")
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for token in banned:
            if token in text:
                offenders.append(f"{path.name}:{token}")
    assert offenders == []
