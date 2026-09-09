"""Optional Windows real-mouse smoke. Not required for generic CI.

Enable with: set MOUSEDPI_HW_SMOKE=1

Requires the bridge readiness handshake:
  raw_input_delta_bridge_started
Physical motion remains optional.
"""

from __future__ import annotations

import os
import sys
import time

import pytest

pytestmark = pytest.mark.windows_hw

BRIDGE_READY = "raw_input_delta_bridge_started"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Raw Input only")
@pytest.mark.skipif(os.environ.get("MOUSEDPI_HW_SMOKE") != "1", reason="Set MOUSEDPI_HW_SMOKE=1 for real-mouse smoke")
def test_windows_raw_input_bridge_ready_smoke():
    from mouse_dpi_tool.capture import CaptureState, create_windows_capture_engine
    from mouse_dpi_tool.path_quality import StreamingPathQualityAccumulator

    statuses: list[str] = []
    pq = StreamingPathQualityAccumulator()
    engine = create_windows_capture_engine(on_status=statuses.append)
    engine.subscribe(pq.on_sample)
    # start() blocks until raw_input_delta_bridge_started (or raises).
    engine.start()
    try:
        assert any(BRIDGE_READY in s for s in statuses), statuses
        # Optional dwell for manual motion; not required for pass.
        time.sleep(0.3)
    finally:
        engine.stop()

    assert any(BRIDGE_READY in s for s in statuses)
    assert engine.state is CaptureState.STOPPED
    assert engine.complete is True
    assert engine.is_valid_complete_capture is True
    # Motion optional — nets may be zero.
    _ = (engine.net_counts_x, engine.net_counts_y, pq.snapshot(), engine.per_device_counts)
