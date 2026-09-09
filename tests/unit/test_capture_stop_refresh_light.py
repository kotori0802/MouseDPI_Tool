"""Capture UI: stop/drain presentation timer; pending Start removed (Phase 4.3)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def qapp():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_stop_op_stops_live_timer_does_not_restart(qapp, monkeypatch):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views import pages as pages_mod
    from mouse_dpi_tool.ui.views.pages import CapturePage

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = CapturePage(ctl)
    timer_calls: list[str] = []
    monkeypatch.setattr(page._timer, "start", lambda: timer_calls.append("start"))
    monkeypatch.setattr(page._timer, "stop", lambda: timer_calls.append("stop"))

    fake_vm = MagicMock()
    fake_vm.state = "running"
    fake_vm.config_locked = True
    fake_vm.can_admit = False
    fake_vm.can_discard = False
    monkeypatch.setattr(ctl, "capture_viewmodel", lambda: fake_vm)
    monkeypatch.setattr(page, "_apply_capture_controls", lambda **_k: None)

    fake_thread = MagicMock()
    fake_thread.isRunning.return_value = False
    monkeypatch.setattr(pages_mod, "QThread", lambda parent=None: fake_thread)
    monkeypatch.setattr(pages_mod, "_CaptureWorker", lambda controller, op: MagicMock(op=op))

    page._run_op("stop")
    assert "stop" in timer_calls
    assert "start" not in timer_calls


def test_start_not_queued_while_worker_busy(qapp):
    from mouse_dpi_tool.ui.controllers import AppController
    from mouse_dpi_tool.ui.views.pages import CapturePage

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = CapturePage(ctl)

    class _FakeThread:
        def isRunning(self) -> bool:  # noqa: N802
            return True

    page._thread = _FakeThread()  # type: ignore[assignment]
    page._pending_capture_op = None
    page._run_op("start")
    assert page._pending_capture_op is None
