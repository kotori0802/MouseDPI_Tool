"""M-2.1 + UI-1B.4 regression coverage."""

from __future__ import annotations

import math

import pytest

from mouse_dpi_tool.capture import CaptureEngine, SyntheticEventSource
from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.measurement.group import FIXTURE_VECTOR_AXIS, FIXTURE_VECTOR_DIRECTION, trial_group_id
from mouse_dpi_tool.measurement.ratio import build_ratio_analysis
from mouse_dpi_tool.measurement.trial import compute_trial
from mouse_dpi_tool.ui.controllers import AppController


def _factory(samples):
    def factory(*, on_status=None):
        return CaptureEngine(source=SyntheticEventSource(samples), on_status=on_status)

    return factory


def test_fixture_vector_stores_na_axis_direction():
    t = compute_trial(
        trial_id=1,
        distance_mm=50.8,
        axis="X",
        direction="X+",
        counts_x=1080,
        counts_y=1184,
        configured_dpi=800,
        movement_mode="Vector Magnitude",
    )
    assert t["axis"] == FIXTURE_VECTOR_AXIS
    assert t["direction"] == FIXTURE_VECTOR_DIRECTION
    assert "N/A" in t["group_id"]
    assert t["measured_cpi"] == pytest.approx(math.sqrt(1080**2 + 1184**2) / 2.0, rel=1e-3)


def test_running_integrity_display_is_pending_not_fail():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory([MovementSample(dx=10, dy=0, device_id="s")]),
    )
    page = CapturePage(controller)
    controller.start_capture()
    page.refresh()
    assert "Pending" in page.ops_line.text() or "待定" in page.ops_line.text()
    assert "FAIL" not in page.ops_line.text()
    # KPI text is deferred while Technical Details is collapsed (live layout cost).
    page.tech_toggle.setChecked(True)
    page.refresh()
    assert "Pending" in page.kpi_label.text() or "待定" in page.kpi_label.text()
    controller.cancel_capture()


def test_navigation_locked_while_capturing():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views import MainWindow

    _ = QApplication.instance() or QApplication([])
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory([MovementSample(dx=10, dy=0, device_id="s")]),
    )
    window = MainWindow(controller)
    window._navigate("capture")
    controller.start_capture()
    window._sync_nav_lock()
    assert controller.capture_navigation_locked is True
    assert window.nav_buttons["setup"].isEnabled() is False
    assert window.nav_buttons["capture"].isEnabled() is True
    window._navigate("results")
    assert window.stack.currentWidget() is window.capture_page
    controller.cancel_capture()
    window._sync_nav_lock()
    assert window.nav_buttons["setup"].isEnabled() is True


def test_group_id_fixture_vector_ignores_fake_axis():
    a = {
        "configured_dpi": 800,
        "axis": "X",
        "direction": "X+",
        "distance_mm": 50.8,
        "movement_mode": "Vector Magnitude",
    }
    b = {
        "configured_dpi": 800,
        "axis": "Y",
        "direction": "Y-",
        "distance_mm": 50.8,
        "movement_mode": "Vector Magnitude",
    }
    assert trial_group_id(a) == trial_group_id(b)


def test_presentation_invariance_viz_motion_locale_theme():
    """Widget size / motion / locale / theme must not change canonical evidence."""
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.components.engineering_viz_host import EngineeringVisualizationHost
    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    samples = [MovementSample(dx=1600, dy=1200, device_id="s")]

    def run(*, theme: str, locale: str, motion: bool, tech_open: bool, size: tuple[int, int]):
        controller = AppController(
            preferences={"theme": theme, "locale": locale, "ui_motion": motion},
            engine_factory=_factory(samples),
        )
        page = CapturePage(controller)
        page.resize(*size)
        page.tech_toggle.setChecked(tech_open)
        host = EngineeringVisualizationHost()
        host.resize(size[0] - 80, max(320, size[1] // 2))
        host.set_path_points(((0.0, 0.0), (1600.0, 1200.0)))
        host.set_gauge_state(
            net_dx=1600.0,
            net_dy=1200.0,
            configured_dpi=800,
            distance_mm=50.8,
            pass_pct=3.0,
        )
        controller.start_capture()
        controller._engine.wait_until_idle()
        controller.stop_capture()
        page.refresh()
        trial = controller.admit_capture()
        snap = controller.session_snapshot()
        return {
            "counts": (trial["counts_x"], trial["counts_y"]),
            "cpi": trial["measured_cpi"],
            "direction": trial["direction"],
            "axis": trial["axis"],
            "group_id": trial["group_id"],
            "integrity": True,
            "findings": snap["findings"],
        }

    variants = [
        run(theme="light", locale="en-US", motion=True, tech_open=False, size=(1400, 900)),
        run(theme="dark", locale="ja-JP", motion=False, tech_open=True, size=(900, 700)),
        run(theme="light", locale="de-DE", motion=True, tech_open=True, size=(640, 800)),
    ]
    assert variants[0] == variants[1] == variants[2]
    assert variants[0]["axis"] == "N/A"
    assert variants[0]["direction"] == "N/A"


def test_engineering_host_hides_future_stack():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QLabel

    from mouse_dpi_tool.ui.components.engineering_viz_host import EngineeringVisualizationHost

    _ = QApplication.instance() or QApplication([])
    host = EngineeringVisualizationHost()
    assert host._future.isVisible() is False
    host.register_future_view("normalized_path_residual", QLabel("future"))
    assert host._future.isVisible() is False
    assert host.gauge.minimumHeight() >= 280


def test_fixture_vector_ratio_bucket_uses_na():
    groups = [
        {
            "configured_dpi": 800,
            "avg_measured_cpi": 800.0,
            "axis": "N/A",
            "direction": "N/A",
            "distance_mm": 50.8,
            "movement_mode": "Vector Magnitude",
        },
        {
            "configured_dpi": 1600,
            "avg_measured_cpi": 1600.0,
            "axis": "N/A",
            "direction": "N/A",
            "distance_mm": 50.8,
            "movement_mode": "Vector Magnitude",
        },
    ]
    rows = build_ratio_analysis(
        groups, {"ratio_error_pass_pct": 3.0, "ratio_error_fail_pct": 8.0}
    )
    assert len(rows) == 1
    assert rows[0]["axis"] == "N/A"
    assert rows[0]["direction"] == "N/A"
