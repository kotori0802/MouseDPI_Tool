"""MS-1.2 — capture transaction phase barrier (F5 correctness)."""

from __future__ import annotations

import pytest

from mouse_dpi_tool.ui.capture_transaction import (
    CaptureTxnPhase,
    f5_action_for_phase,
    resolve_capture_txn_phase,
)


def test_phase_running_f5_is_stop():
    phase = resolve_capture_txn_phase(
        engine_state="running",
        worker_op=None,
        worker_running=False,
        can_admit=False,
        can_discard=False,
        arming=False,
    )
    assert phase is CaptureTxnPhase.RUNNING
    assert f5_action_for_phase(phase, can_admit=False) == "stop"


def test_phase_arming_f5_ignored():
    phase = resolve_capture_txn_phase(
        engine_state="idle",
        worker_op="start",
        worker_running=True,
        can_admit=False,
        can_discard=False,
        arming=True,
    )
    assert phase is CaptureTxnPhase.ARMING
    assert f5_action_for_phase(phase, can_admit=False) == "ignore"


def test_phase_stopping_f5_ignored():
    phase = resolve_capture_txn_phase(
        engine_state="running",
        worker_op="stop",
        worker_running=True,
        can_admit=False,
        can_discard=False,
        arming=False,
    )
    assert phase is CaptureTxnPhase.STOPPING
    assert f5_action_for_phase(phase, can_admit=False) == "ignore"


def test_phase_review_ready_when_admit_and_discard_both_true():
    """Valid pending exposes both Admit and Discard — must not classify as ERROR."""
    phase = resolve_capture_txn_phase(
        engine_state="stopped",
        worker_op=None,
        worker_running=False,
        can_admit=True,
        can_discard=True,
        arming=False,
    )
    assert phase is CaptureTxnPhase.REVIEW_READY
    assert f5_action_for_phase(phase, can_admit=True) == "admit_next"


def test_phase_error_when_discard_only():
    phase = resolve_capture_txn_phase(
        engine_state="error",
        worker_op=None,
        worker_running=False,
        can_admit=False,
        can_discard=True,
        arming=False,
    )
    assert phase is CaptureTxnPhase.ERROR
    assert f5_action_for_phase(phase, can_admit=False) == "ignore"


def test_f5_bounce_during_arming_does_not_queue_stop():
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.capture import CaptureEngine, SyntheticEventSource
    from mouse_dpi_tool.contracts.movement import MovementSample
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.pages import CapturePage

    _ = QApplication.instance() or QApplication([])

    def factory(*, on_status=None):
        return CaptureEngine(
            SyntheticEventSource([MovementSample(dx=1600, dy=0, device_id="s")]),
            on_status=on_status,
        )

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=factory,
    )
    controller.update_distance(distance_input=2.0, unit="inch")
    controller.set_configured_dpi(800)
    controller.set_direction("X+")
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
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
    page._on_f5()
    QCoreApplication.processEvents()
    assert started == ["start"]
    page._on_f5()
    assert page._pending_capture_op is None
    assert page._txn_phase() is CaptureTxnPhase.ARMING
