"""Session Evidence Integrity — mutability boundary, semantics, runtime dep."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import venv
from pathlib import Path

import pytest

from mouse_dpi_tool.capture import CaptureState
from mouse_dpi_tool.session import Session, SessionValidationError, validate_session, write_session_json
from mouse_dpi_tool.session.semantics import validate_session_semantics


def _session(**kwargs) -> Session:
    return Session(
        dut={"vendor": "ExampleVendor", "model": "DemoMouse", "notes": ""},
        measurement_context={
            "method": "synthetic",
            "fixture_type": "",
            "surface": "",
            "direction": "X+",
            "polling_rate_note": "",
            "notes": "",
        },
        settings={"distance_mm": 100.0, "movement_mode": "Vector Magnitude", "min_valid_trials_per_group": 1},
        operator="tester",
        **kwargs,
    )


def _evidence(*, dx: int, dy: int = 0, events: int = 1, device: str = "d1") -> dict:
    return {
        "state": "stopped",
        "complete": True,
        "integrity_ok": True,
        "valid_complete_capture": True,
        "published_count": events,
        "device_ids": [device],
        "per_device_counts": {device: {"dx": dx, "dy": dy, "event_count": events}},
        "last_error": None,
        "subscriber_errors": [],
        "status_callback_errors": [],
        "issue_codes": [],
    }


def test_public_evidence_accessors_return_deep_copies():
    session = _session()
    session.add_synthetic_trial(
        configured_dpi=800,
        counts_x=3150,
        counts_y=12,
        capture_evidence=_evidence(dx=3150, dy=12, events=5),
    )
    session.add_synthetic_trial(configured_dpi=1600, counts_x=6300, capture_evidence=_evidence(dx=6300, events=7))
    session.reject_trial(2, reason="demo")
    session.delete_trial(1, reason="demo-delete")
    # Re-add so active/group/ratio exist for mutation checks.
    session.add_synthetic_trial(configured_dpi=800, counts_x=3140, capture_evidence=_evidence(dx=3140, events=3))
    session.add_synthetic_trial(configured_dpi=1600, counts_x=6280, capture_evidence=_evidence(dx=6280, events=4))

    before = session.to_session_dict()

    active = session.active_trials
    active[0]["configured_dpi"] = 99999
    active[0]["capture_evidence"]["published_count"] = -1

    rejected = session.rejected_trials
    rejected[0]["configured_dpi"] = 11111

    deleted = session.deleted_trials
    deleted[0]["configured_dpi"] = 22222

    groups = session.group_summaries
    groups[0]["configured_dpi"] = 33333
    groups[0]["avg_measured_cpi"] = -1

    ratios = session.ratio_analysis
    ratios[0]["from_dpi"] = 44444

    after = session.to_session_dict()
    assert after["trials"][0]["configured_dpi"] == before["trials"][0]["configured_dpi"]
    assert after["trials"][0]["capture_evidence"]["published_count"] == before["trials"][0]["capture_evidence"]["published_count"]
    assert after["rejected_trials"][0]["configured_dpi"] == before["rejected_trials"][0]["configured_dpi"]
    assert after["deleted_trials"][0]["configured_dpi"] == before["deleted_trials"][0]["configured_dpi"]
    assert after["group_summaries"][0]["configured_dpi"] == before["group_summaries"][0]["configured_dpi"]
    assert after["group_summaries"][0]["avg_measured_cpi"] == before["group_summaries"][0]["avg_measured_cpi"]
    assert after["ratio_analysis"][0]["from_dpi"] == before["ratio_analysis"][0]["from_dpi"]


def test_exported_trial_has_measurement_status_not_status():
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=3150)
    payload = session.to_session_dict()
    assert "status" not in payload["trials"][0]
    assert payload["trials"][0]["measurement_status"] in {"PASS", "WARN", "FAIL"}
    assert "status" in payload["group_summaries"][0]
    validate_session(payload)


def _valid_payload() -> dict:
    session = _session(created_at="2026-09-03T13:00:00+08:00", session_id="mds_sem_test")
    session.add_synthetic_trial(
        configured_dpi=800,
        counts_x=3150,
        counts_y=0,
        source="raw_input",
        capture_evidence=_evidence(dx=3150, events=10),
    )
    return session.to_session_dict()


def test_semantic_rejects_active_trial_with_rejected_flags():
    payload = _valid_payload()
    payload["trials"][0]["accepted"] = False
    payload["trials"][0]["rejected"] = True
    with pytest.raises(SessionValidationError, match="semantic"):
        validate_session(payload)


def test_semantic_rejects_active_invalid_capture_evidence():
    payload = _valid_payload()
    payload["trials"][0]["capture_evidence"]["valid_complete_capture"] = False
    with pytest.raises(SessionValidationError, match="valid_complete_capture"):
        validate_session(payload)


def test_semantic_rejects_metrics_count_mismatch():
    payload = _valid_payload()
    payload["metrics"]["active_trial_count"] = 999
    with pytest.raises(SessionValidationError, match="active_trial_count"):
        validate_session(payload)


def test_semantic_rejects_rejected_bucket_flag_mismatch():
    payload = _valid_payload()
    trial = copy.deepcopy(payload["trials"][0])
    trial["trial_id"] = 99
    trial["accepted"] = True
    trial["rejected"] = False
    payload["rejected_trials"] = [trial]
    payload["metrics"]["rejected_trial_count"] = 1
    errs = validate_session_semantics(payload)
    assert any("rejected_trials.0.accepted" in e for e in errs)


def test_semantic_rejects_duplicate_trial_ids():
    payload = _valid_payload()
    dup = copy.deepcopy(payload["trials"][0])
    dup["accepted"] = False
    dup["rejected"] = True
    payload["rejected_trials"] = [dup]
    payload["metrics"]["rejected_trial_count"] = 1
    with pytest.raises(SessionValidationError, match="duplicates"):
        validate_session(payload)


def test_semantic_rejects_raw_input_active_without_capture_evidence():
    payload = _valid_payload()
    del payload["trials"][0]["capture_evidence"]
    with pytest.raises(SessionValidationError, match="capture_evidence"):
        validate_session(payload)


def test_semantic_rejects_capture_aggregate_mismatch():
    payload = _valid_payload()
    payload["trials"][0]["capture_evidence"]["published_count"] = 999
    with pytest.raises(SessionValidationError, match="published_count"):
        validate_session(payload)

    payload = _valid_payload()
    payload["trials"][0]["counts_x"] = 1
    with pytest.raises(SessionValidationError, match="counts_x"):
        validate_session(payload)


def test_semantic_rejects_trial_level_status_field():
    payload = _valid_payload()
    payload["trials"][0]["status"] = "PASS"
    with pytest.raises(SessionValidationError):
        validate_session(payload)


def test_runtime_wheel_install_without_dev_extra_can_export(tmp_path: Path):
    """Plain runtime install (no [dev]) must provide jsonschema and export Session JSON."""
    root = Path(__file__).resolve().parents[2]
    venv_dir = tmp_path / "runtime_venv"
    venv.create(venv_dir, with_pip=True)
    if sys.platform == "win32":
        python = venv_dir / "Scripts" / "python.exe"
    else:
        python = venv_dir / "bin" / "python"

    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip", "wheel"], check=True, cwd=root)
    # Runtime-only install: project metadata dependencies, no [dev].
    subprocess.run([str(python), "-m", "pip", "install", str(root)], check=True, cwd=root)

    probe = tmp_path / "probe.py"
    out_json = tmp_path / "exported.json"
    probe.write_text(
        f"""
import jsonschema
from mouse_dpi_tool.session import Session, write_session_json
s = Session(
    dut={{"vendor":"V","model":"M","notes":""}},
    measurement_context={{
        "method":"synthetic","fixture_type":"","surface":"","direction":"X+",
        "polling_rate_note":"","notes":""
    }},
    settings={{"distance_mm":100.0,"min_valid_trials_per_group":1}},
    session_id="mds_runtime_smoke",
    created_at="2026-09-03T13:00:00+08:00",
)
s.add_synthetic_trial(configured_dpi=800, counts_x=3150)
write_session_json(s.to_session_dict(), r"{out_json}")
print("ok", jsonschema.__name__)
""",
        encoding="utf-8",
    )
    # Prove pytest is NOT required at runtime.
    missing = subprocess.run(
        [str(python), "-c", "import pytest"],
        capture_output=True,
        text=True,
    )
    assert missing.returncode != 0

    result = subprocess.run([str(python), str(probe)], capture_output=True, text=True, check=True)
    assert "ok jsonschema" in result.stdout
    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["schema_version"] == "MOUSE_DPI_TOOL_SESSION_V1"
    assert "status" not in data["trials"][0]
