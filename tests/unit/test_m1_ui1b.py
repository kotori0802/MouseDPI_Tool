"""M-1 Axis Projection + UI-1B live Capture UX / snapshot integrity."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from mouse_dpi_tool.capture import CaptureEngine, CaptureSnapshot, SyntheticEventSource, VisualizationPathBuffer
from mouse_dpi_tool.contracts.movement import VISUALIZATION_PATH_MAX_POINTS, MovementSample
from mouse_dpi_tool.measurement.trial import compute_trial
from mouse_dpi_tool.path_quality import StreamingPathQualityAccumulator
from mouse_dpi_tool.session import CaptureAdmissionError, Session
from mouse_dpi_tool.ui.controllers import V1_OPERATOR_MOVEMENT_MODE, AppController
from mouse_dpi_tool.ui.theme import ThemeManager
from mouse_dpi_tool.ui.theme.tokens import DARK, LIGHT


def _samples(n: int, dx: int = 1, dy: int = 0) -> list[MovementSample]:
    return [MovementSample(dx=dx, dy=dy, device_id="synth") for _ in range(n)]


def test_v1_qt_session_defaults_to_fixture_vector():
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    assert controller.session.settings["movement_mode"] == "Vector Magnitude"
    assert V1_OPERATOR_MOVEMENT_MODE == "Vector Magnitude"
    snap = controller.session_snapshot()
    assert snap["settings"]["movement_mode"] == "Vector Magnitude"


def test_vector_magnitude_still_supported_outside_ui_policy():
    t = compute_trial(
        trial_id=1,
        distance_mm=100.0,
        axis="X",
        direction="X+",
        counts_x=3000,
        counts_y=400,
        configured_dpi=800,
        movement_mode="Vector Magnitude",
    )
    assert t["movement_mode"] == "Vector Magnitude"
    assert t["primary_counts"] == int(round((3000**2 + 400**2) ** 0.5))


def test_lateral_deviation_does_not_inflate_axis_projection_primary():
    base = compute_trial(
        trial_id=1,
        distance_mm=100.0,
        axis="X",
        direction="X+",
        counts_x=3150,
        counts_y=0,
        configured_dpi=800,
        movement_mode="Axis Projection",
    )
    leaky = compute_trial(
        trial_id=2,
        distance_mm=100.0,
        axis="X",
        direction="X+",
        counts_x=3150,
        counts_y=400,
        configured_dpi=800,
        movement_mode="Axis Projection",
    )
    assert base["primary_counts"] == leaky["primary_counts"] == 3150
    assert leaky["secondary_counts"] == 400
    assert leaky["axis_leakage_pct"] > base["axis_leakage_pct"]
    assert base["measured_cpi"] == leaky["measured_cpi"]


def test_direction_match_enables_admission_in_viewmodel():
    def factory(*, on_status=None):
        return CaptureEngine(
            source=SyntheticEventSource([MovementSample(dx=3150, dy=0, device_id="s")]),
            on_status=on_status,
        )

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=factory,
    )
    controller.set_direction("X+")
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    vm = controller.capture_viewmodel()
    assert vm.direction_match is True
    assert vm.can_admit is True
    assert vm.direction_issue_code is None


def test_direction_mismatch_disables_admission_in_viewmodel():
    def factory(*, on_status=None):
        return CaptureEngine(
            source=SyntheticEventSource([MovementSample(dx=-3150, dy=0, device_id="s")]),
            on_status=on_status,
        )

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=factory,
    )
    controller.set_movement_mode("Axis Projection")
    controller.set_direction("X+")
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    vm = controller.capture_viewmodel()
    assert vm.is_valid_complete_capture is True
    assert vm.direction_match is False
    assert vm.direction_issue_code == "DIRECTION_MISMATCH"
    assert vm.observed_direction == "X-"
    assert vm.can_admit is False


def test_zero_primary_disables_admission():
    def factory(*, on_status=None):
        return CaptureEngine(
            source=SyntheticEventSource([MovementSample(dx=0, dy=0, device_id="s")]),
            on_status=on_status,
        )

    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=factory,
    )
    controller.start_capture()
    controller._engine.wait_until_idle()
    controller.stop_capture()
    vm = controller.capture_viewmodel()
    assert vm.can_admit is False
    assert vm.direction_issue_code == "ZERO_PRIMARY_MOVEMENT"


def test_session_still_rejects_direction_mismatch():
    engine = CaptureEngine()
    engine.start()
    engine.feed(MovementSample(dx=-100, dy=0, device_id="t"))
    engine.wait_until_idle()
    engine.stop()
    session = Session(settings={"distance_mm": 100.0, "movement_mode": "Axis Projection"})
    with pytest.raises(CaptureAdmissionError):
        session.admit_valid_capture(engine, configured_dpi=800, direction="X+")


def test_capture_snapshot_type_and_coherence():
    engine = CaptureEngine()
    engine.start()
    for _ in range(50):
        engine.feed(MovementSample(dx=2, dy=-1, device_id="a"))
    engine.wait_until_idle()
    snap = engine.snapshot()
    assert isinstance(snap, CaptureSnapshot)
    assert snap.state == "running"
    assert snap.net_counts_x == 100
    assert snap.net_counts_y == -50
    assert snap.published_count == 50
    engine.stop()
    stopped = engine.snapshot()
    assert stopped.is_valid_complete_capture is True


def test_visualization_buffer_bounded_and_thread_safe():
    buf = VisualizationPathBuffer(max_points=100)
    stop = threading.Event()

    def writer():
        i = 0
        while not stop.is_set():
            buf.on_sample(MovementSample(dx=1, dy=0, device_id="w"))
            i += 1
            if i > 5000:
                break

    t = threading.Thread(target=writer)
    t.start()
    for _ in range(200):
        pts = buf.points()
        assert len(pts) <= 100
        assert len(pts) <= VISUALIZATION_PATH_MAX_POINTS
    stop.set()
    t.join(timeout=2)
    assert len(buf.points()) <= 100


def test_path_quality_snapshot_coherent_under_concurrent_writes():
    acc = StreamingPathQualityAccumulator()
    stop = threading.Event()

    def writer():
        while not stop.is_set():
            acc.on_sample(MovementSample(dx=10, dy=0, device_id="w"))

    t = threading.Thread(target=writer)
    t.start()
    last = None
    for _ in range(300):
        snap = acc.snapshot()
        assert snap["sample_count"] >= 0
        assert snap["net_counts_x"] == snap["sample_count"] * 10 or snap["sample_count"] == 0
        last = snap
    stop.set()
    t.join(timeout=2)
    final = acc.snapshot()
    assert final["sample_count"] >= last["sample_count"]


def test_100k_events_with_ui_polling_preserves_evidence():
    n = 100_000
    samples = _samples(n, dx=1, dy=0)

    def run(*, poll: bool):
        engine = CaptureEngine(source=SyntheticEventSource(samples))
        pq = StreamingPathQualityAccumulator()
        viz = VisualizationPathBuffer()
        engine.subscribe(pq.on_sample)
        engine.subscribe(viz.on_sample)
        stop_poll = threading.Event()
        polls: list[tuple] = []

        def poller():
            while not stop_poll.is_set():
                polls.append((engine.snapshot().published_count, pq.snapshot()["sample_count"], len(viz.points())))
                time.sleep(0.001)

        poll_thread = None
        if poll:
            poll_thread = threading.Thread(target=poller)
            poll_thread.start()
        engine.start()
        engine.wait_until_idle(timeout=30)
        engine.stop()
        stop_poll.set()
        if poll_thread is not None:
            poll_thread.join(timeout=2)
        return {
            "net_x": engine.net_counts_x,
            "net_y": engine.net_counts_y,
            "published": engine.published_count,
            "valid": engine.is_valid_complete_capture,
            "pq": pq.snapshot(),
            "viz_len": len(viz.points()),
            "polls": len(polls),
        }

    headless = run(poll=False)
    polled = run(poll=True)
    assert polled["polls"] > 0
    assert headless["net_x"] == polled["net_x"] == n
    assert headless["net_y"] == polled["net_y"] == 0
    assert headless["published"] == polled["published"] == n
    assert headless["valid"] is polled["valid"] is True
    assert headless["pq"]["net_counts_x"] == polled["pq"]["net_counts_x"]
    assert headless["pq"]["sample_count"] == polled["pq"]["sample_count"]
    assert headless["pq"]["status"] == polled["pq"]["status"]
    assert polled["viz_len"] <= VISUALIZATION_PATH_MAX_POINTS


def test_presentation_invariance_across_theme_locale_polling():
    samples = _samples(5000, dx=2, dy=1)

    def evidence(theme: str, locale: str, poll_hz: float):
        controller = AppController(
            preferences={"theme": theme, "locale": locale},
            engine_factory=lambda *, on_status=None: CaptureEngine(
                source=SyntheticEventSource(samples), on_status=on_status
            ),
        )
        controller.set_theme(theme)
        controller.set_locale(locale)
        controller.set_direction("X+")
        controller.start_capture()
        stop = threading.Event()

        def poller():
            interval = 1.0 / poll_hz
            while not stop.is_set():
                _ = controller.capture_viewmodel()
                _ = controller.visualization_points()
                time.sleep(interval)

        t = threading.Thread(target=poller)
        t.start()
        controller._engine.wait_until_idle(timeout=10)
        controller.stop_capture()
        stop.set()
        t.join(timeout=2)
        trial = controller.admit_capture()
        return {
            "trial_counts": (trial["counts_x"], trial["counts_y"]),
            "measured_cpi": trial["measured_cpi"],
            "direction": trial["direction"],
            "movement_mode": trial["movement_mode"],
            "findings": controller.session_snapshot()["findings"],
            "pq_status": trial.get("path_quality_status"),
        }

    a = evidence("light", "en-US", 30)
    b = evidence("dark", "ja-JP", 60)
    c = evidence("light", "de-DE", 15)
    assert a == b == c
    assert a["movement_mode"] == "Vector Magnitude"


def test_path_canvas_theme_does_not_touch_evidence():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.components.path_canvas import PathCanvas

    _ = QApplication.instance() or QApplication([])
    canvas = PathCanvas()
    canvas.set_points(((0.0, 0.0), (10.0, 0.0), (10.0, 5.0)))
    before = canvas.point_count
    canvas.apply_tokens(LIGHT)
    canvas.apply_tokens(DARK)
    assert canvas.point_count == before == 3


def test_f5_esc_behavior_via_page_helpers():
    pytest.importorskip("PySide6")
    from mouse_dpi_tool.ui.views.pages import CapturePage
    from PySide6.QtWidgets import QApplication

    _ = QApplication.instance() or QApplication([])
    ops: list[str] = []

    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    page = CapturePage(controller)
    page._run_op = lambda op: ops.append(op)  # type: ignore[method-assign]

    # Idle → F5 starts (QShortcut handlers)
    page._on_f5()
    assert ops == ["start"]

    # Simulate capturing
    engine = CaptureEngine()
    engine.start()
    controller._engine = engine
    page._on_f5()
    assert ops == ["start", "stop"]

    page._on_esc()
    assert ops == ["start", "stop", "cancel"]
    engine.cancel()


def test_no_pyside_in_domain_packages():
    root = Path(__file__).resolve().parents[2] / "src" / "mouse_dpi_tool"
    offenders: list[str] = []
    for package in ("measurement", "capture", "path_quality", "session", "findings"):
        for path in (root / package).rglob("*.py"):
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if "import PySide6" in line or "from PySide6" in line:
                    offenders.append(f"{path}:{i}")
    assert offenders == []


def test_high_dpi_behavioral_modules_not_implemented_in_v1_tree():
    """V1 tree must not ship speculative high-DPI behavioral packages."""
    root = Path(__file__).resolve().parents[2] / "src" / "mouse_dpi_tool"
    banned = list(root.rglob("*high_dpi*")) + list(root.rglob("*transition*"))
    assert banned == []
