"""UI-1B.2 — packaged Raw Input runtime, failed-start unlock, bridge command."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from mouse_dpi_tool.capture import CaptureEngine, CaptureState, SyntheticEventSource
from mouse_dpi_tool.capture.bridge_command import (
    BridgeHelperNotFoundError,
    FROZEN_HELPER_NAME,
    resolve_bridge_command,
)
from mouse_dpi_tool.capture.raw_input_source import BRIDGE_READY, SourceStartError, SourceStopError
from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.ui.controllers import AppController


def test_dev_bridge_command_uses_module_launch():
    cmd = resolve_bridge_command(frozen=False)
    assert cmd[0] == sys.executable
    assert cmd[1:] == ["-m", "mouse_dpi_tool.capture.raw_input_bridge"]


def test_frozen_bridge_command_requires_helper_exe(tmp_path: Path):
    with pytest.raises(BridgeHelperNotFoundError, match="Raw Input helper executable not found"):
        resolve_bridge_command(frozen=True, app_dir=tmp_path)
    helper = tmp_path / FROZEN_HELPER_NAME
    helper.write_bytes(b"MZ")  # existence only
    cmd = resolve_bridge_command(frozen=True, app_dir=tmp_path)
    assert cmd == [str(helper)]


def test_failed_start_clears_freeze_and_unlocks_measurement():
    class BoomSource:
        def start(self, *_a, **_k):
            raise SourceStartError("Raw Input helper executable not found: missing")

        def stop(self):
            return None

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=lambda *, on_status=None: CaptureEngine(source=BoomSource(), on_status=on_status),
    )
    controller.set_configured_dpi(800)
    controller.set_direction("X+")
    controller.update_distance(distance_input=120.0, unit="mm")
    with pytest.raises(SourceStartError, match="helper executable not found"):
        controller.start_capture()
    assert controller.run_config is None
    assert controller.run_started is False
    assert controller.measurement_config_locked is False
    # Error text preserved for operator.
    assert "helper" in controller._last_status.lower() or "not found" in controller._last_status.lower()
    # Measurement edits unlocked.
    controller.update_distance(distance_input=50.0, unit="mm")
    assert abs(float(controller.session.settings["distance_mm"]) - 50.0) < 1e-9
    controller.set_configured_dpi(1600)
    controller.set_direction("Y+")
    assert controller.configured_dpi == 1600
    assert controller.direction == "Y+"


def test_successful_start_remains_frozen_through_stop_admit():
    samples = [MovementSample(dx=3150, dy=0, device_id="s")]

    def factory(*, on_status=None):
        return CaptureEngine(source=SyntheticEventSource(samples), on_status=on_status)

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=factory,
    )
    controller.set_direction("X+")
    controller.set_configured_dpi(800)
    controller.start_capture()
    assert controller.run_started is True
    assert controller.measurement_config_locked is True
    with pytest.raises(RuntimeError, match="frozen"):
        controller.update_distance(distance_input=50.0, unit="mm")
    controller._engine.wait_until_idle()
    controller.stop_capture()
    assert controller.measurement_config_locked is True
    trial = controller.admit_capture()
    assert abs(trial["measured_cpi"] - 800.0) < 1.0
    assert controller.measurement_config_locked is False


def test_stop_integrity_error_keeps_freeze_until_cancel():
    class FaultyStopSource:
        def start(self, on_sample, on_status=None):
            if on_status:
                on_status(BRIDGE_READY)
            on_sample(MovementSample(dx=100, dy=0, device_id="s"))

        def stop(self):
            raise SourceStopError("inconclusive drain")

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=lambda *, on_status=None: CaptureEngine(
            source=FaultyStopSource(), on_status=on_status
        ),
    )
    controller.set_direction("X+")
    controller.start_capture()
    assert controller.run_started is True
    controller.stop_capture()
    assert controller._engine.snapshot().state == CaptureState.ERROR.value
    assert controller.measurement_config_locked is True
    with pytest.raises(RuntimeError, match="frozen"):
        controller.set_configured_dpi(999)
    # Cancel/discard unlocks without claiming clean cancel status.
    controller.cancel_capture()
    assert controller.measurement_config_locked is False
    assert controller._last_status != "capture_cancelled"
    assert "error" in controller._last_status.lower() or "inconclusive" in controller._last_status.lower() or "failed" in controller._last_status.lower() or "capture_error" in controller._last_status


def test_clean_cancel_status_is_capture_cancelled():
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=lambda *, on_status=None: CaptureEngine(
            source=SyntheticEventSource([]), on_status=on_status
        ),
    )
    controller.start_capture()
    controller.cancel_capture()
    assert controller._last_status == "capture_cancelled"
    assert controller.measurement_config_locked is False


def test_focus_loss_cancels_only_running_capture():
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=lambda *, on_status=None: CaptureEngine(
            source=SyntheticEventSource([MovementSample(dx=10, dy=0, device_id="s")]),
            on_status=on_status,
        ),
    )
    assert controller.handle_application_deactivated() is False
    controller.start_capture()
    assert controller.handle_application_deactivated() is True
    assert controller.operator_issue == "APPLICATION_LOST_FOCUS"
    assert controller.measurement_config_locked is False

    # Stopped pending capture must not be altered by focus loss.
    controller2 = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=lambda *, on_status=None: CaptureEngine(
            source=SyntheticEventSource([MovementSample(dx=3150, dy=0, device_id="s")]),
            on_status=on_status,
        ),
    )
    controller2.set_direction("X+")
    controller2.start_capture()
    controller2._engine.wait_until_idle()
    controller2.stop_capture()
    assert controller2.measurement_config_locked is True
    assert controller2.handle_application_deactivated() is False
    assert controller2.measurement_config_locked is True


def test_setup_page_locked_unlocked_ux():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import SetupPage

    _ = QApplication.instance() or QApplication([])

    class BoomSource:
        def start(self, *_a, **_k):
            raise SourceStartError("helper missing")

        def stop(self):
            return None

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=lambda *, on_status=None: CaptureEngine(source=BoomSource(), on_status=on_status),
    )
    page = SetupPage(controller)
    page.distance.setValue(77.0)
    page._apply()
    assert abs(float(controller.session.settings["distance_input"]) - 77.0) < 1e-9
    assert page.distance.isEnabled()

    # Successful pending freeze locks Setup distance with an explicit message.
    ok = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=lambda *, on_status=None: CaptureEngine(
            source=SyntheticEventSource([MovementSample(dx=10, dy=0, device_id="s")]),
            on_status=on_status,
        ),
    )
    page2 = SetupPage(ok)
    ok.start_capture()
    page2.refresh()
    assert page2.distance.isEnabled() is False
    assert "locked" in page2.message_label.text().lower() or "鎖定" in page2.message_label.text()
    page2.distance.setValue(11.0)
    page2._apply()
    # DUT may apply; distance must remain frozen value, with message (not silent snap alone).
    assert abs(float(ok.session.settings["distance_mm"]) - 100.0) < 1e-9
    assert page2.message_label.text()


@pytest.mark.windows_hw
@pytest.mark.skipif(sys.platform != "win32", reason="Windows packaged helper only")
@pytest.mark.skipif(
    os.environ.get("MOUSEDPI_PACKAGED_SMOKE") != "1",
    reason="Set MOUSEDPI_PACKAGED_SMOKE=1 after packaging/build_windows.py",
)
def test_packaged_raw_input_helper_ready_smoke():
    dist = Path(__file__).resolve().parents[2] / "dist" / "MouseDPI_Tool_UI"
    helper = dist / FROZEN_HELPER_NAME
    ui = dist / "MouseDPI_Tool_UI.exe"
    assert helper.is_file(), f"missing packaged helper: {helper}"
    assert ui.is_file(), f"missing packaged UI: {ui}"

    creationflags = 0x08000000  # CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen(
            [str(helper)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            creationflags=creationflags,
        )
    except OSError as exc:
        # WDAC/AppLocker may block freshly built EXEs in locked-down CI agents.
        pytest.skip(f"packaged helper blocked by OS policy: {exc}")
    ready = False
    deadline = time.monotonic() + 5.0
    assert proc.stdout is not None
    try:
        while time.monotonic() < deadline:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                continue
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "status" and event.get("message") == BRIDGE_READY:
                ready = True
                break
        assert ready, "packaged helper did not emit ready handshake"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    assert proc.returncode is not None
