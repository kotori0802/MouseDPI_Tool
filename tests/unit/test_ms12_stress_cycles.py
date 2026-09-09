"""MS-1.2 — synthetic capture transaction stress (100+ cycles)."""

from __future__ import annotations

from mouse_dpi_tool.capture import CaptureEngine, SyntheticEventSource
from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.ui.controllers import AppController


def test_100_admit_cycles_single_generation_no_stale():
    """Rapid legal Start→Stop→Admit cycles must not leak stale samples across gens."""

    def factory(*, on_status=None):
        return CaptureEngine(
            SyntheticEventSource(
                [MovementSample(dx=20, dy=20, device_id="s")] * 40
            ),
            on_status=on_status,
        )

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=factory,
    )
    controller.update_distance(distance_input=50.8, unit="mm")
    controller.set_configured_dpi(800)
    controller.session.update_measurement_context(method="fixture")

    gens: list[int] = []
    for i in range(100):
        controller.start_capture()
        eng = controller._engine
        assert eng is not None
        gens.append(int(eng.generation))
        eng.wait_until_idle()
        controller.stop_capture()
        assert eng.stale_sample_count == 0
        snap = eng.snapshot()
        assert snap.stale_sample_count == 0
        assert snap.generation == gens[-1]
        if eng.is_valid_complete_capture:
            controller.admit_capture()
        else:
            controller.discard_capture()

    assert len(controller.session.active_trials) + len(
        controller.session.rejected_trials
    ) + len(controller.session.deleted_trials) >= 1
    # Each Start creates a new engine; generation within an engine starts at 1.
    assert all(g >= 1 for g in gens)
    assert len(gens) == 100


def test_qt_repaint_does_not_mutate_raw_counts():
    """Presentation refresh must not alter CaptureEngine net counts (READY vs gauge)."""
    pytest = __import__("pytest")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])

    def factory(*, on_status=None):
        return CaptureEngine(
            SyntheticEventSource([MovementSample(dx=100, dy=50, device_id="s")] * 10),
            on_status=on_status,
        )

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=factory,
    )
    controller.update_distance(distance_input=50.8, unit="mm")
    controller.set_configured_dpi(800)
    controller.start_capture()
    eng = controller._engine
    assert eng is not None
    eng.wait_until_idle()
    before = (eng.net_counts_x, eng.net_counts_y, eng.published_count)
    page = CapturePage(controller)
    for _ in range(20):
        page.refresh()
    after = (eng.net_counts_x, eng.net_counts_y, eng.published_count)
    assert after == before
    controller.stop_capture()
