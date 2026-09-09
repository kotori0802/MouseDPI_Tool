"""Phase Session — lifecycle, admission, JSON writer, schema hardening."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from mouse_dpi_tool.capture import CaptureEngine, CaptureState
from mouse_dpi_tool.contracts.movement import MovementSample
from mouse_dpi_tool.session import (
    CaptureAdmissionError,
    Session,
    SessionValidationError,
    TrialLifecycleError,
    load_session_json,
    validate_session,
    write_session_json,
)


@dataclass
class FakeCapture:
    state: CaptureState = CaptureState.STOPPED
    complete: bool = True
    integrity_ok: bool = True
    published_count: int = 0
    net_counts_x: int = 0
    net_counts_y: int = 0
    device_ids: tuple[str, ...] = ()
    per_device_counts: dict = field(default_factory=dict)
    last_error: str | None = None
    subscriber_errors: tuple[str, ...] = ()
    status_callback_errors: tuple[str, ...] = ()

    @property
    def is_valid_complete_capture(self) -> bool:
        return self.state is CaptureState.STOPPED and self.complete and self.integrity_ok


def _session(**kwargs) -> Session:
    return Session(
        dut={"vendor": "ExampleVendor", "model": "DemoMouse", "notes": "lab"},
        measurement_context={
            "method": "synthetic",
            "fixture_type": "",
            "surface": "cloth",
            "direction": "X+",
            "polling_rate_note": "",
            "notes": "",
        },
        settings={"distance_mm": 100.0, "movement_mode": "Vector Magnitude"},
        operator="tester",
        **kwargs,
    )


def test_create_new_session_identity():
    a = _session()
    b = _session()
    assert a.session_id != b.session_id
    assert a.created_at.endswith(("Z",)) or "+" in a.created_at or a.created_at[-6] in "+-"
    payload = a.to_session_dict()
    assert payload["schema_version"] == "MOUSE_DPI_TOOL_SESSION_V1"
    assert payload["metrics"]["active_trial_count"] == 0
    validate_session(payload)


def test_stable_unique_session_and_trial_ids():
    session = _session()
    t1 = session.add_synthetic_trial(configured_dpi=800, counts_x=3150, counts_y=0)
    t2 = session.add_synthetic_trial(configured_dpi=800, counts_x=3140, counts_y=1)
    assert t1["trial_id"] == 1
    assert t2["trial_id"] == 2
    session.reject_trial(1, reason="operator")
    t3 = session.add_synthetic_trial(configured_dpi=1600, counts_x=6300)
    assert t3["trial_id"] == 3  # IDs never reused
    assert {t["trial_id"] for t in session.active_trials} == {2, 3}
    assert session.session_id == session.to_session_dict()["session_id"]


def test_valid_clean_capture_admitted_as_active_trial():
    engine = CaptureEngine()
    engine.start()
    engine.feed(MovementSample(dx=3150, dy=0, device_id="11"))
    engine.wait_until_idle()
    engine.stop()
    assert engine.is_valid_complete_capture

    session = _session()
    trial = session.admit_valid_capture(engine, configured_dpi=800, axis="X", direction="X+")
    assert trial["accepted"] is True
    assert trial["rejected"] is False
    assert trial["capture_evidence"]["valid_complete_capture"] is True
    assert trial["capture_evidence"]["per_device_counts"]["11"]["dx"] == 3150
    assert len(session.active_trials) == 1
    assert session.metrics()["active_trial_count"] == 1


def test_invalid_incomplete_capture_rejected_from_active_analysis():
    bad = FakeCapture(
        state=CaptureState.ERROR,
        complete=False,
        integrity_ok=False,
        published_count=3,
        net_counts_x=100,
        last_error="EventSource.stop failed",
        per_device_counts={"unknown": {"dx": 100, "dy": 0, "event_count": 3}},
    )
    session = _session()
    with pytest.raises(CaptureAdmissionError):
        session.admit_valid_capture(bad, configured_dpi=800)

    retained = session.retain_invalid_capture(bad, configured_dpi=800, reason="inconclusive stop")
    assert retained["rejected"] is True
    assert retained["accepted"] is False
    assert session.active_trials == []
    assert len(session.rejected_trials) == 1
    assert session.group_summaries == []
    assert session.metrics()["rejected_trial_count"] == 1


def test_reject_trial_retained_and_excluded_from_group_ratio():
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=3150)
    session.add_synthetic_trial(configured_dpi=1600, counts_x=6300)
    assert len(session.group_summaries) == 2
    assert len(session.ratio_analysis) == 1

    session.reject_trial(1, reason="hand slip")
    assert len(session.active_trials) == 1
    assert len(session.rejected_trials) == 1
    assert session.rejected_trials[0]["rejection_reason"] == "hand slip"
    assert len(session.group_summaries) == 1
    assert session.ratio_analysis == []


def test_restore_rejected_trial():
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=3150)
    session.reject_trial(1, reason="oops")
    restored = session.restore_rejected_trial(1)
    assert restored["accepted"] is True
    assert restored["rejected"] is False
    assert len(session.active_trials) == 1
    assert session.group_summaries


def test_restore_invalid_capture_evidence_is_blocked():
    bad = FakeCapture(state=CaptureState.ERROR, complete=False, integrity_ok=False, net_counts_x=1)
    session = _session()
    session.retain_invalid_capture(bad, configured_dpi=800, reason="bad")
    with pytest.raises(TrialLifecycleError, match="cannot be restored"):
        session.restore_rejected_trial(1)


def test_delete_trial_retained_audit_excluded_from_analysis():
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=3150)
    session.add_synthetic_trial(configured_dpi=800, counts_x=3140)
    session.delete_trial(1, reason="duplicate")
    assert len(session.active_trials) == 1
    assert len(session.deleted_trials) == 1
    assert session.deleted_trials[0]["deleted"] is True
    assert session.deleted_trials[0]["deletion_reason"] == "duplicate"
    assert session.group_summaries[0]["valid_trials"] == 1


def test_new_dut_produces_new_session_lifecycle():
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=3150)
    old_id = session.session_id
    nxt = session.new_dut(vendor="Other", model="M2", notes="reset")
    assert nxt.session_id != old_id
    assert nxt.dut["vendor"] == "Other"
    assert nxt.active_trials == []
    assert nxt.metrics()["active_trial_count"] == 0
    # Previous session evidence remains intact on the old object.
    assert len(session.active_trials) == 1


def test_group_ratio_rebuilt_from_active_trials_only():
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=3150, direction="X+")
    session.add_synthetic_trial(configured_dpi=1600, counts_x=6300, direction="X+")
    session.add_synthetic_trial(configured_dpi=3200, counts_x=12600, direction="X+")
    assert len(session.ratio_analysis) == 2
    session.reject_trial(2)
    # Active: 800 and 3200 only → one ratio pair
    assert len(session.group_summaries) == 2
    assert len(session.ratio_analysis) == 1
    assert session.ratio_analysis[0]["from_dpi"] == 800
    assert session.ratio_analysis[0]["to_dpi"] == 3200


def test_per_device_capture_evidence_survives_json_round_trip(tmp_path: Path):
    capture = FakeCapture(
        published_count=4,
        net_counts_x=10,
        net_counts_y=2,
        device_ids=("11", "22"),
        per_device_counts={
            "11": {"dx": 7, "dy": 1, "event_count": 2},
            "22": {"dx": 3, "dy": 1, "event_count": 2},
        },
    )
    session = _session()
    session.admit_valid_capture(capture, configured_dpi=800)
    path = tmp_path / "roundtrip.json"
    write_session_json(session.to_session_dict(), path)
    loaded = load_session_json(path)
    evidence = loaded["trials"][0]["capture_evidence"]
    assert evidence["device_ids"] == ["11", "22"]
    assert evidence["per_device_counts"]["11"]["dx"] == 7
    assert evidence["per_device_counts"]["22"]["event_count"] == 2


def test_offset_aware_timestamp_validation():
    session = _session(created_at="2026-09-03T10:30:00+08:00")
    session.add_synthetic_trial(configured_dpi=800, counts_x=3150)
    validate_session(session.to_session_dict())

    bad = session.to_session_dict()
    bad["created_at"] = "2026-09-03T10:30:00"
    with pytest.raises(SessionValidationError):
        validate_session(bad)


def test_target_dpi_export_rejection():
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=3150)
    payload = session.to_session_dict()
    payload["trials"][0]["target_dpi"] = 800
    with pytest.raises(SessionValidationError):
        validate_session(payload)


@pytest.mark.parametrize(
    "field",
    ["health", "result", "overall_result", "overall_status", "session_status", "arbitrary_verdict"],
)
def test_arbitrary_overall_verdict_field_rejection(field: str):
    session = _session()
    payload = session.to_session_dict()
    payload["metrics"][field] = "PASS"
    with pytest.raises(SessionValidationError):
        validate_session(payload)


def test_json_schema_validation_before_write(tmp_path: Path):
    session = _session()
    payload = session.to_session_dict()
    payload["metrics"]["health"] = "PASS"
    target = tmp_path / "bad.json"
    with pytest.raises(SessionValidationError):
        write_session_json(payload, target)
    assert not target.exists()


def test_atomic_write_failure_does_not_leave_valid_partial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=3150)
    payload = session.to_session_dict()
    target = tmp_path / "session.json"
    write_session_json(payload, target)
    original = target.read_text(encoding="utf-8")

    def boom(src, dst):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError, match="simulated replace failure"):
        write_session_json(payload, target)

    assert target.read_text(encoding="utf-8") == original
    assert json.loads(original)["schema_version"] == "MOUSE_DPI_TOOL_SESSION_V1"
    leftovers = list(tmp_path.glob(".session.json.*.tmp"))
    assert leftovers == []


def test_exported_session_loads_independently_without_legacy(tmp_path: Path):
    session = _session()
    session.add_synthetic_trial(
        configured_dpi=800,
        counts_x=3150,
        capture_evidence={
            "state": "stopped",
            "complete": True,
            "integrity_ok": True,
            "valid_complete_capture": True,
            "published_count": 1,
            "device_ids": ["d1"],
            "per_device_counts": {"d1": {"dx": 3150, "dy": 0, "event_count": 1}},
            "last_error": None,
            "subscriber_errors": [],
            "status_callback_errors": [],
            "issue_codes": [],
        },
    )
    path = tmp_path / "independent.json"
    write_session_json(session.to_session_dict(), path)
    # Pure JSON load path — no CaptureEngine / Hub imports required.
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["tool_name"] == "Mouse DPI Tool"
    assert "target_dpi" not in raw["trials"][0]
    assert "health" not in raw["metrics"]
    loaded = load_session_json(path)
    assert loaded["session_id"] == session.session_id
