"""UI-1B.1 — Capture Run Integrity (freeze, PathCanvas Y, cancel ERROR, shortcuts)."""

from __future__ import annotations

import pytest

from mouse_dpi_tool.capture import CaptureEngine, CaptureState, SyntheticEventSource
from mouse_dpi_tool.capture.raw_input_source import SourceStopError
from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.ui.controllers import AppController


def _factory(samples):
    def factory(*, on_status=None):
        return CaptureEngine(source=SyntheticEventSource(samples), on_status=on_status)

    return factory


def test_distance_mutation_after_start_cannot_change_pending_cpi():
    """GPT repro: Start@100mm dx=3150 then mutate to 50mm must not yield ~1600 CPI."""
    samples = [MovementSample(dx=3150, dy=0, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.update_distance(distance_input=100.0, unit="mm")
    controller.set_configured_dpi(800)
    controller.set_direction("X+")
    controller.start_capture()
    assert controller.measurement_config_locked is True
    with pytest.raises(RuntimeError, match="frozen"):
        controller.update_distance(distance_input=50.0, unit="mm")
    # Even a direct Session bypass must not win on Admit — freeze is restored.
    controller.session.update_settings({"distance_input": 50.0, "distance_unit": "mm"})
    assert abs(float(controller.session.settings["distance_mm"]) - 50.0) < 1e-9
    controller._engine.wait_until_idle()
    controller.stop_capture()
    vm = controller.capture_viewmodel()
    assert vm.distance_mm == 100.0
    assert vm.config_locked is True
    trial = controller.admit_capture()
    assert abs(trial["distance_mm"] - 100.0) < 1e-9
    assert abs(trial["measured_cpi"] - 800.0) < 1.0


def test_dpi_mutation_after_start_cannot_change_pending_target():
    samples = [MovementSample(dx=3150, dy=0, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.set_configured_dpi(800)
    controller.set_direction("X+")
    controller.start_capture()
    with pytest.raises(RuntimeError, match="frozen"):
        controller.set_configured_dpi(1600)
    controller._engine.wait_until_idle()
    controller.stop_capture()
    assert controller.capture_viewmodel().configured_dpi == 800
    trial = controller.admit_capture()
    assert trial["configured_dpi"] == 800
    assert abs(trial["measured_cpi"] - 800.0) < 1.0


def test_direction_mutation_after_start_cannot_reinterpret_pending():
    samples = [MovementSample(dx=3150, dy=0, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.set_movement_mode("Axis Projection")
    controller.set_direction("X+")
    controller.start_capture()
    with pytest.raises(RuntimeError, match="frozen"):
        controller.set_direction("X-")
    controller._engine.wait_until_idle()
    controller.stop_capture()
    vm = controller.capture_viewmodel()
    assert vm.direction == "X+"
    assert vm.direction_match is True
    assert vm.can_admit is True
    trial = controller.admit_capture()
    assert trial["direction"] == "X+"


def test_frozen_config_survives_running_stop_admit():
    samples = [MovementSample(dx=0, dy=-2000, device_id="s")]  # Y+ physical
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.update_distance(distance_input=100.0, unit="mm")
    controller.set_configured_dpi(800)
    controller.set_movement_mode("Axis Projection")
    controller.set_direction("Y+")
    controller.start_capture()
    cfg = controller.run_config
    assert cfg is not None
    assert cfg.direction == "Y+" and cfg.axis == "Y" and cfg.configured_dpi == 800
    assert controller.measurement_config_locked is True
    controller._engine.wait_until_idle()
    controller.stop_capture()
    assert controller.run_config is cfg
    assert controller.measurement_config_locked is True
    trial = controller.admit_capture()
    assert trial["direction"] == "Y+"
    assert controller.run_config is None
    assert controller.measurement_config_locked is False


def test_next_capture_uses_newly_selected_configuration():
    samples_a = [MovementSample(dx=3150, dy=0, device_id="s")]
    samples_b = [MovementSample(dx=0, dy=1575, device_id="s")]  # Y- (raw +dy)

    def factory(*, on_status=None):
        # Alternate sources by call count
        factory.n += 1  # type: ignore[attr-defined]
        src = samples_a if factory.n == 1 else samples_b  # type: ignore[attr-defined]
        return CaptureEngine(source=SyntheticEventSource(src), on_status=on_status)

    factory.n = 0  # type: ignore[attr-defined]

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=factory,
    )
    controller.set_movement_mode("Axis Projection")
    controller.set_direction("X+")
    controller.set_configured_dpi(800)
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    controller.admit_capture()

    # Direction / DPI are Capture-level (not Session structural after first trial).
    controller.set_direction("Y-")
    controller.set_configured_dpi(400)
    controller.start_capture()
    cfg = controller.run_config
    assert cfg is not None
    assert cfg.direction == "Y-"
    assert cfg.configured_dpi == 400
    controller._engine.wait_until_idle()
    controller.stop_capture()
    trial = controller.admit_capture()
    assert trial["direction"] == "Y-"
    assert trial["configured_dpi"] == 400


def test_theme_locale_remain_allowed_and_evidence_invariant():
    samples = [MovementSample(dx=3150, dy=0, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.set_movement_mode("Axis Projection")
    controller.set_direction("X+")
    controller.start_capture()
    controller.set_theme("dark")
    controller.set_locale("zh-TW")
    assert controller.measurement_config_locked is True
    controller._engine.wait_until_idle()
    controller.stop_capture()
    trial = controller.admit_capture()
    assert trial["direction"] == "X+"
    assert abs(trial["measured_cpi"] - 800.0) < 1.0
    snap = controller.session_snapshot()
    assert "theme" not in snap.get("settings", {})
    assert "locale" not in snap.get("settings", {})


def test_cancel_preserves_error_when_stop_inconclusive():
    class FaultySource:
        def start(self, on_sample, on_status=None):
            if on_status:
                on_status("ready")

        def stop(self):
            raise SourceStopError("inconclusive drain")

    engine = CaptureEngine(source=FaultySource())
    engine.start()
    engine.cancel()
    snap = engine.snapshot()
    assert snap.state == CaptureState.ERROR.value
    assert snap.complete is False
    assert snap.integrity_ok is False
    assert snap.is_valid_complete_capture is False


def test_clean_cancel_becomes_cancelled():
    engine = CaptureEngine(source=SyntheticEventSource([]))
    engine.start()
    engine.cancel()
    assert engine.snapshot().state == CaptureState.CANCELLED.value


def test_path_canvas_signed_axis_mapping():
    from mouse_dpi_tool.ui.components.path_canvas import map_raw_path_to_widget

    w, h = 200.0, 200.0
    # X+: increasing raw x → screen right
    xp = map_raw_path_to_widget([(0.0, 0.0), (100.0, 0.0)], width=w, height=h)
    assert xp[-1][0] > xp[0][0]
    assert abs(xp[0][1] - h / 2.0) < 1.0  # horizontal centered

    # X-: decreasing raw x → screen left
    xm = map_raw_path_to_widget([(0.0, 0.0), (-100.0, 0.0)], width=w, height=h)
    assert xm[-1][0] < xm[0][0]

    # Y+: physical up → raw dy < 0 → screen up (smaller widget y)
    yp = map_raw_path_to_widget([(0.0, 0.0), (0.0, -100.0)], width=w, height=h)
    assert yp[-1][1] < yp[0][1]
    assert abs(yp[0][0] - w / 2.0) < 1.0  # vertical centered

    # Y-: physical down → raw dy > 0 → screen down (larger widget y)
    ym = map_raw_path_to_widget([(0.0, 0.0), (0.0, 100.0)], width=w, height=h)
    assert ym[-1][1] > ym[0][1]


def test_stop_enabled_while_start_worker_thread_still_quitting():
    """Regression: Start finished → state running, QThread not quit yet → Stop must work."""
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory([MovementSample(dx=100, dy=0, device_id="s")]),
    )
    page = CapturePage(controller)
    controller.start_capture()
    # Simulate worker still winding down while capture is already RUNNING.
    page._worker = type("W", (), {"op": "start"})()  # type: ignore[assignment]

    class _Alive:
        def isRunning(self):  # noqa: N802
            return True

    page._thread = _Alive()  # type: ignore[assignment]
    page.refresh()
    assert page.stop_btn.isEnabled() is True
    assert page.cancel_btn.isEnabled() is True
    controller.cancel_capture()


def test_f5_esc_shortcuts_fire_with_child_focus():
    pytest.importorskip("PySide6")
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeySequence
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views import MainWindow

    app = QApplication.instance() or QApplication([])
    ops: list[str] = []
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    window = MainWindow(controller)
    window._navigate("capture")
    page = window.capture_page
    page._run_op = lambda op: ops.append(op)  # type: ignore[method-assign]
    window.show()
    app.processEvents()

    page.dpi.setFocus(Qt.FocusReason.OtherFocusReason)
    assert window._shortcut_f5.context() == Qt.ShortcutContext.WindowShortcut
    assert window._shortcut_esc.context() == Qt.ShortcutContext.WindowShortcut
    window._shortcut_f5.activated.emit()
    assert ops == ["start"]

    engine = CaptureEngine()
    engine.start()
    controller._engine = engine
    window._shortcut_f5.activated.emit()
    assert ops == ["start", "stop"]
    window._shortcut_esc.activated.emit()
    assert ops == ["start", "stop", "cancel"]
    engine.cancel()
    window.close()
    _ = QKeySequence, QTest


def test_admit_releases_idle_and_f5_can_start_next_trial():
    """Continuous testing: Admit → Ready → F5/Start for trial 2 (no stuck stopped gate)."""
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    samples = [MovementSample(dx=1600, dy=0, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.update_distance(distance_input=2.0, unit="inch")
    controller.set_configured_dpi(800)
    controller.set_direction("X+")
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    pending = controller.trial_result_poster()
    assert pending is not None
    assert pending["phase"] == "pending"
    assert pending["measured_cpi"] is not None

    trial = controller.admit_capture()
    assert trial["trial_id"] == 1
    assert controller._engine is None
    vm = controller.capture_viewmodel()
    assert vm.state == "idle"
    assert vm.can_admit is False
    assert vm.can_discard is False
    assert controller.measurement_config_locked is False
    poster = controller.trial_result_poster()
    assert poster is not None
    assert poster["phase"] == "admitted"
    assert poster["trial_id"] == 1

    page = CapturePage(controller)
    ops: list[str] = []
    page._run_op = lambda op: ops.append(op)  # type: ignore[method-assign]
    page.refresh()
    assert page.start_btn.isEnabled() is True
    page._on_f5()
    assert ops == ["start"]


def test_f5_on_pending_admit_admits_and_starts_next():
    """Tester continuous flow: Stop → F5 admits trial 1 and starts trial 2."""
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    samples = [MovementSample(dx=1600, dy=0, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.update_distance(distance_input=2.0, unit="inch")
    controller.set_configured_dpi(800)
    controller.set_direction("X+")
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    assert controller.capture_viewmodel().can_admit is True

    page = CapturePage(controller)
    ops: list[str] = []
    page._run_op = lambda op: ops.append(op)  # type: ignore[method-assign]
    page.refresh()
    page._on_f5()
    from PySide6.QtCore import QCoreApplication

    QCoreApplication.processEvents()
    assert len(controller.session.active_trials) == 1
    assert controller.session.active_trials[0]["trial_id"] == 1
    assert ops == ["start"]


def test_f5_bounce_during_admit_start_does_not_queue_stop():
    """Rapid extra F5 after Admit+Start must not arm pending Stop on the next capture."""
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    samples = [MovementSample(dx=1600, dy=0, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.update_distance(distance_input=2.0, unit="inch")
    controller.set_configured_dpi(800)
    controller.set_direction("X+")
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    assert controller.capture_viewmodel().can_admit is True

    page = CapturePage(controller)
    started: list[str] = []

    def fake_run(op: str) -> None:
        started.append(op)

        class _FakeThread:
            def isRunning(self) -> bool:  # noqa: N802
                return True

        page._thread = _FakeThread()  # type: ignore[assignment]
        page._worker = type("W", (), {"op": "start"})()  # type: ignore[assignment]

    page._run_op = fake_run  # type: ignore[method-assign]
    page.refresh()
    page._on_f5()  # Admit + arm Start
    QCoreApplication.processEvents()
    assert started == ["start"]
    page._on_f5()  # bounce during arming window
    assert page._pending_capture_op is None


def test_diagonal_poster_shows_vector_magnitude_as_official_under_fixture_vector():
    samples = [MovementSample(dx=1080, dy=1184, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.update_distance(distance_input=2.0, unit="inch")
    controller.set_configured_dpi(800)
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    poster = controller.trial_result_poster()
    assert poster is not None
    assert poster["phase"] == "pending"
    # Fixture Vector primary = √(dx²+dy²)/inch ≈ 801 CPI.
    assert float(poster["measured_cpi"]) > 750
    assert poster["movement_mode"] == "Vector Magnitude"


def test_diagonal_poster_axis_mode_shows_low_cpi_and_vector_ref():
    samples = [MovementSample(dx=1080, dy=1184, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.set_movement_mode("Axis Projection")
    controller.update_distance(distance_input=2.0, unit="inch")
    controller.set_configured_dpi(800)
    controller.set_direction("X+")
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    poster = controller.trial_result_poster()
    assert poster is not None
    assert float(poster["measured_cpi"]) < 700
    assert float(poster["vector_cpi"]) > 750
