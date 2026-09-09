"""UI-1B.4.1 — Presentation state reliability (Poster / Gauge / async Stop)."""

from __future__ import annotations

import time

import pytest

from mouse_dpi_tool.capture import CaptureEngine, SyntheticEventSource
from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.ui.controllers import AppController


def _factory(samples):
    def factory(*, on_status=None):
        return CaptureEngine(source=SyntheticEventSource(samples), on_status=on_status)

    return factory


def test_stop_freezes_presentation_snapshot_immediately():
    samples = [MovementSample(dx=1600, dy=1200, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    snap = controller.last_capture_presentation()
    assert snap is not None
    assert snap["phase"] == "pending"
    assert snap["integrity_ok"] is True
    assert snap["measured_cpi"] is not None
    assert len(snap["path_points"]) >= 1
    poster = controller.trial_result_poster()
    assert poster is not None
    assert poster["phase"] == "pending"
    assert abs(float(poster["measured_cpi"]) - float(snap["measured_cpi"])) < 1e-9


def test_admit_keeps_presentation_gauge_and_path():
    samples = [MovementSample(dx=1600, dy=1200, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    before = controller.last_capture_presentation()
    assert before is not None
    path_before = tuple(before["path_points"])
    nets = (before["net_counts_x"], before["net_counts_y"])
    trial = controller.admit_capture()
    after = controller.last_capture_presentation()
    assert after is not None
    assert after["phase"] == "admitted"
    assert after["trial_id"] == trial["trial_id"]
    assert tuple(after["path_points"]) == path_before
    assert (after["net_counts_x"], after["net_counts_y"]) == nets
    assert controller.visualization_points() == path_before
    assert controller._engine is None
    poster = controller.trial_result_poster()
    assert poster is not None
    assert poster["phase"] == "admitted"


def test_next_start_clears_live_viz_keeps_admitted_poster():
    samples_a = [MovementSample(dx=1600, dy=1200, device_id="s")]
    samples_b = [MovementSample(dx=100, dy=0, device_id="s")]

    def factory(*, on_status=None):
        factory.n += 1  # type: ignore[attr-defined]
        src = samples_a if factory.n == 1 else samples_b  # type: ignore[attr-defined]
        return CaptureEngine(source=SyntheticEventSource(src), on_status=on_status)

    factory.n = 0  # type: ignore[attr-defined]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=factory,
    )
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    controller.admit_capture()
    admitted = controller.last_capture_presentation()
    assert admitted is not None and admitted["phase"] == "admitted"
    controller.start_capture()
    still = controller.trial_result_poster()
    assert still is not None
    assert still["phase"] == "admitted"
    assert still["trial_id"] == admitted["trial_id"]
    controller.cancel_capture()


def test_qt_poster_populated_immediately_after_async_stop():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    app = QApplication.instance() or QApplication([])
    samples = [MovementSample(dx=3150, dy=0, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US", "ui_motion": True},
        engine_factory=_factory(samples),
    )
    page = CapturePage(controller)
    page.refresh()
    assert page.poster.isHidden() is True

    page._run_op("start")
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        app.processEvents()
        if controller._engine is not None and controller._engine.snapshot().state == "running":
            if page._thread is None or not page._thread.isRunning():
                break
        time.sleep(0.01)
    assert controller._engine is not None
    # Drain Start QThread.finished before Stop (avoids stale finished races).
    for _ in range(30):
        app.processEvents()
        time.sleep(0.01)
    controller._engine.wait_until_idle()

    t0 = time.perf_counter()
    page._run_op("stop")
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        app.processEvents()
        if controller.last_capture_presentation() is not None and "CPI" in page.poster_cpi.text():
            break
        time.sleep(0.005)
    latency_ms = (time.perf_counter() - t0) * 1000.0
    assert controller.last_capture_presentation() is not None
    assert page.poster.isHidden() is False
    assert "CPI" in page.poster_cpi.text()
    assert page.poster.graphicsEffect() is None
    assert latency_ms < 2000.0
    assert controller.trial_result_poster()["phase"] == "pending"


def test_refresh_idempotent_pending_and_admitted():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    samples = [MovementSample(dx=1600, dy=1200, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    page = CapturePage(controller)
    page.show()
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    page.refresh()
    title1 = page.poster_title.text()
    cpi1 = page.poster_cpi.text()
    path1 = page.canvas.point_count
    assert page.poster.isHidden() is False
    for _ in range(12):
        page.refresh()
    assert page.poster.isHidden() is False
    assert page.poster_title.text() == title1
    assert page.poster_cpi.text() == cpi1
    assert page.canvas.point_count == path1

    controller.admit_capture()
    page.refresh()
    title2 = page.poster_title.text()
    cpi2 = page.poster_cpi.text()
    path2 = page.canvas.point_count
    for _ in range(12):
        page.refresh()
    assert page.poster.isHidden() is False
    assert page.poster_title.text() == title2
    assert page.poster_cpi.text() == cpi2
    assert page.canvas.point_count == path2
    assert page.canvas.point_count >= 1


def test_stop_during_start_thread_winddown_is_queued_not_sync():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])

    class SlowStartSource:
        def __init__(self, samples):
            self._samples = samples

        def start(self, on_sample, on_status=None):
            time.sleep(0.08)
            if on_status:
                on_status("ready")
            for s in self._samples:
                on_sample(s)

        def stop(self):
            return None

        def cancel(self):
            return None

    samples = [MovementSample(dx=10, dy=0, device_id="s")]

    def factory(*, on_status=None):
        return CaptureEngine(source=SlowStartSource(samples), on_status=on_status)

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=factory,
    )
    page = CapturePage(controller)
    page._run_op("start")
    assert page._thread is not None and page._thread.isRunning()
    sync_on_gui: list[str] = []
    real_stop = controller.stop_capture

    def guard_stop():
        if (
            page._thread is not None
            and page._thread.isRunning()
            and page._worker is not None
            and page._worker.op == "start"
        ):
            sync_on_gui.append("sync_stop_while_start_worker")
        return real_stop()

    controller.stop_capture = guard_stop  # type: ignore[method-assign]
    page._run_op("stop")
    assert page._pending_capture_op == "stop"
    assert sync_on_gui == []
    deadline = time.monotonic() + 5.0
    app = QApplication.instance()
    while time.monotonic() < deadline:
        app.processEvents()
        if page._pending_capture_op is None and (page._thread is None or not page._thread.isRunning()):
            if controller.capture_viewmodel().state != "running":
                break
        time.sleep(0.01)
    assert sync_on_gui == []


def test_no_opacity_effect_helpers_on_data_surfaces():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QLabel

    from mouse_dpi_tool.ui import chrome_motion
    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])
    assert not hasattr(chrome_motion, "flash_appear")
    w = QLabel("x")
    chrome_motion.fade_widget(w, show=True)
    assert w.graphicsEffect() is None
    page = CapturePage(AppController(preferences={"theme": "light", "locale": "en-US"}))
    assert page.poster.graphicsEffect() is None


def test_application_active_refresh_keeps_pending_poster():
    pytest.importorskip("PySide6")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views import MainWindow

    app = QApplication.instance() or QApplication([])
    samples = [MovementSample(dx=1600, dy=1200, device_id="s")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_factory(samples),
    )
    window = MainWindow(controller)
    window.show()
    window._navigate("capture")
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    window.capture_page.refresh()
    assert window.capture_page.poster.isHidden() is False
    cpi = window.capture_page.poster_cpi.text()
    window._on_application_state_changed(Qt.ApplicationState.ApplicationInactive)
    window._on_application_state_changed(Qt.ApplicationState.ApplicationActive)
    app.processEvents()
    assert window.capture_page.poster.isHidden() is False
    assert window.capture_page.poster_cpi.text() == cpi
    assert controller.last_capture_presentation()["phase"] == "pending"
