"""Phase 4.3 — busy refresh + pending-op contract hardening."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def qapp():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _busy_vm(*, busy_op: str, state: str = "running") -> MagicMock:
    """Build a CapturePageVM-like object with busy=True (exercises busy refresh)."""
    vm = MagicMock()
    vm.state = state
    vm.display_state = {
        "starting": "starting",
        "stopping": "stopping",
        "cancelling": "cancelling",
        "discarding": "discarding",
    }.get(busy_op, "capturing")
    vm.busy = True
    # Intentionally NO busy_op attribute — VM contract must not require it.
    del vm.busy_op
    vm.last_status = "test"
    vm.configured_dpi = 800
    vm.direction = "X+"
    vm.distance_mm = 50.8
    vm.distance_input = 2.0
    vm.distance_unit = "inch"
    vm.movement_mode = "Fixture Vector"
    vm.net_counts_x = 0
    vm.net_counts_y = 0
    vm.primary_counts = 0
    vm.published_count = 0
    vm.device_ids = ()
    vm.device_count = 0
    vm.is_valid_complete_capture = False
    vm.integrity_ok = True
    vm.complete = False
    vm.can_admit = False
    vm.can_discard = False
    vm.config_locked = True
    vm.last_error = None
    vm.path_quality_status = None
    vm.direction_match = None
    vm.direction_issue_code = None
    vm.expected_direction = "X+"
    vm.observed_direction = None
    vm.path_points = ((0.0, 0.0),)
    return vm


@pytest.mark.parametrize(
    "busy_op,worker_op",
    [
        ("starting", "start"),
        ("stopping", "stop"),
        ("cancelling", "cancel"),
        ("discarding", None),
    ],
)
def test_refresh_under_busy_ops_no_attribute_error(qapp, monkeypatch, busy_op, worker_op):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.pages import CapturePage

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = CapturePage(ctl)
    vm = _busy_vm(busy_op=busy_op, state="running" if busy_op != "discarding" else "stopped")
    if busy_op == "discarding":
        vm.can_discard = True
        vm.state = "error"
    monkeypatch.setattr(ctl, "capture_viewmodel", lambda: vm)

    if worker_op is not None:
        class _FakeThread:
            def isRunning(self) -> bool:  # noqa: N802
                return True

        page._thread = _FakeThread()  # type: ignore[assignment]
        page._worker = MagicMock(op=worker_op)

    # Must exercise busy=True path repeatedly without AttributeError.
    assert vm.busy is True
    assert not hasattr(vm, "busy_op")
    for _ in range(5):
        page.refresh()
    assert page.action_bar.mode is not None
    assert page._action_bar_mode is not None


def test_start_not_queued_while_stop_worker_busy(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.pages import CapturePage

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = CapturePage(ctl)

    class _FakeThread:
        def isRunning(self) -> bool:  # noqa: N802
            return True

    page._thread = _FakeThread()  # type: ignore[assignment]
    page._worker = MagicMock(op="stop")
    page._pending_capture_op = None
    page._run_op("start")
    assert page._pending_capture_op is None


def test_stop_still_queued_while_start_worker_busy(qapp):
    from mouse_dpi_tool.ui.capture_transaction import CaptureTxnPhase
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.pages import CapturePage

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = CapturePage(ctl)

    class _FakeThread:
        def isRunning(self) -> bool:  # noqa: N802
            return True

    page._thread = _FakeThread()  # type: ignore[assignment]
    page._worker = MagicMock(op="start")
    # Simulate confirmed RUNNING + Start thread still winding down is unusual;
    # F5 stop queue requires phase RUNNING via _on_f5. Direct _run_op path:
    page._pending_capture_op = None
    page._run_op("stop")
    # _run_op queues stop when thread busy regardless of engine state check...
    # Actually _run_op returns early when thread busy BEFORE vm.state check,
    # and queues stop. Good.
    assert page._pending_capture_op == "stop"


def test_thread_finished_never_dispatches_pending_start(qapp, monkeypatch):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.pages import CapturePage

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = CapturePage(ctl)
    calls: list[str] = []
    monkeypatch.setattr(page, "_run_op", lambda op: calls.append(op))
    monkeypatch.setattr(page, "refresh", lambda: None)
    page._pending_capture_op = "start"
    page._thread = None
    page._worker = None
    page._on_thread_finished()
    assert calls == []
    assert page._pending_capture_op is None


def test_finishing_worker_keeps_timer_stopped_across_refresh(qapp, monkeypatch):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.pages import CapturePage

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = CapturePage(ctl)
    vm = _busy_vm(busy_op="stopping")
    monkeypatch.setattr(ctl, "capture_viewmodel", lambda: vm)

    class _FakeThread:
        def isRunning(self) -> bool:  # noqa: N802
            return True

    page._thread = _FakeThread()  # type: ignore[assignment]
    page._worker = MagicMock(op="stop")
    page._timer.start()
    assert page._timer.isActive()
    page.refresh()
    assert page._timer.isActive() is False


def test_hide_and_deactivate_clear_pending(qapp):
    from PySide6.QtGui import QHideEvent

    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.pages import CapturePage

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = CapturePage(ctl)
    page._pending_capture_op = "stop"
    page.hideEvent(QHideEvent())
    assert page._pending_capture_op is None

    page._pending_capture_op = "cancel"
    page._clear_pending_capture_op(reason="app_deactivate")
    assert page._pending_capture_op is None


def test_capture_page_vm_has_no_busy_op_field():
    from mouse_dpi_tool.ui.viewmodels import CapturePageVM

    assert "busy_op" not in CapturePageVM.__dataclass_fields__
