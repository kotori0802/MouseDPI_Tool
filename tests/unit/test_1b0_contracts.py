"""Phase 1B-0 contract tests: distance, timestamps, schema, movement samples, resources."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from mouse_dpi_tool.contracts.movement import VISUALIZATION_PATH_MAX_POINTS, MovementSample
from mouse_dpi_tool.measurement.legacy_compat import resolve_configured_dpi
from mouse_dpi_tool.measurement.settings import normalize_settings
from mouse_dpi_tool.measurement.timeutil import now_iso
from mouse_dpi_tool.measurement.trial import compute_trial
from mouse_dpi_tool.path_quality import StreamingPathQualityAccumulator
from mouse_dpi_tool.resources import manual_observation_template, session_schema

SRC = Path(__file__).resolve().parents[2] / "src"


def _minimal_session(*, created_at: str, extra_trial_fields: dict | None = None) -> dict:
    trial = {
        "trial_id": 1,
        "created_at": created_at,
        "configured_dpi": 800,
        "distance_mm": 100.0,
        "counts_x": 3150,
        "counts_y": 0,
        "vector_counts": 3150,
        "primary_counts": 3150,
        "measured_cpi": 800.1,
        "error_pct": 0.0125,
        "movement_mode": "Vector Magnitude",
        "accepted": True,
        "rejected": False,
        "deleted": False,
    }
    if extra_trial_fields:
        trial.update(extra_trial_fields)
    return {
        "schema_version": "MOUSE_DPI_TOOL_SESSION_V1",
        "tool_name": "Mouse DPI Tool",
        "tool_version": "0.1.0rc1",
        "session_id": "demo_session_001",
        "created_at": created_at,
        "operator": "tester",
        "dut": {"vendor": "ExampleVendor", "model": "DemoMouse", "notes": ""},
        "measurement_context": {
            "method": "synthetic",
            "fixture_type": "",
            "surface": "",
            "direction": "X+",
            "polling_rate_note": "",
            "notes": "",
        },
        "settings": {
            "distance_mm": 100.0,
            "distance_unit": "mm",
            "movement_mode": "Vector Magnitude",
            "cpi_error_pass_pct": 3.0,
            "cpi_error_fail_pct": 5.0,
        },
        "trials": [trial],
        "rejected_trials": [],
        "deleted_trials": [],
        "group_summaries": [],
        "ratio_analysis": [],
        "findings": {
            "accuracy": {"status": "NOT_TESTED", "issue_codes": []},
            "repeatability": {"status": "NOT_TESTED", "issue_codes": []},
            "ratio": {"status": "NOT_TESTED", "issue_codes": []},
            "path_quality": {"status": "NOT_TESTED", "issue_codes": []},
            "manual_observations": [],
            "linearity": {"status": "NOT_EVALUATED", "issue_codes": []},
            "scaling_evidence": {"status": "NOT_EVALUATED", "issue_codes": []},
            "native_capability": {"status": "NOT_EVALUATED", "issue_codes": []},
        },
        "metrics": {
            "active_trial_count": 1,
            "rejected_trial_count": 0,
            "deleted_trial_count": 0,
            "group_count": 0,
            "ratio_pair_count": 0,
        },
    }


def test_explicit_distance_mm_is_not_overridden_by_default_input():
    settings = normalize_settings({"distance_mm": 30})
    assert settings["distance_mm"] == pytest.approx(30.0)
    assert settings["distance_mm"] != pytest.approx(100.0)
    assert settings["distance_input"] == pytest.approx(30.0)
    assert settings["distance_unit"] == "mm"


def test_distance_input_plus_unit_converts_to_canonical_mm():
    settings = normalize_settings({"distance_input": 3.0, "distance_unit": "cm"})
    assert settings["distance_mm"] == pytest.approx(30.0)


def test_distance_input_wins_over_conflicting_distance_mm():
    settings = normalize_settings(
        {"distance_input": 2.0, "distance_unit": "inch", "distance_mm": 999.0}
    )
    assert settings["distance_mm"] == pytest.approx(50.8)


def test_now_iso_is_offset_aware():
    stamp = now_iso()
    parsed = datetime.fromisoformat(stamp)
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() is not None
    trial = compute_trial(
        trial_id=1,
        configured_dpi=800,
        distance_mm=30.0,
        axis="X",
        direction="X+",
        counts_x=1,
        counts_y=0,
    )
    assert datetime.fromisoformat(trial["created_at"]).tzinfo is not None


def test_session_schema_format_checker_rejects_naive_and_accepts_offset():
    jsonschema = pytest.importorskip("jsonschema")
    schema = session_schema()
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())

    validator.validate(_minimal_session(created_at="2026-09-03T10:30:00+08:00"))
    validator.validate(_minimal_session(created_at="2026-09-03T02:30:00Z"))

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(_minimal_session(created_at="2026-09-03T10:30:00"))


def test_session_schema_rejects_target_dpi_and_overall_health():
    jsonschema = pytest.importorskip("jsonschema")
    schema = session_schema()
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())

    with_target = _minimal_session(created_at="2026-09-03T10:30:00+08:00")
    with_target["trials"][0]["target_dpi"] = 800
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(with_target)

    with_health = _minimal_session(created_at="2026-09-03T10:30:00+08:00")
    with_health["metrics"]["health"] = "PASS"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(with_health)

    with_overall = _minimal_session(created_at="2026-09-03T10:30:00+08:00")
    with_overall["metrics"]["overall_status"] = "PASS"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(with_overall)

    with_trial_status = _minimal_session(created_at="2026-09-03T10:30:00+08:00")
    with_trial_status["trials"][0]["status"] = "PASS"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(with_trial_status)

    # metrics is a strict allow-list
    assert schema["properties"]["metrics"]["additionalProperties"] is False
    assert schema["$defs"]["trial"]["additionalProperties"] is False
    assert "status" not in schema["$defs"]["trial"]["properties"]



def test_configured_dpi_alias_and_conflict():
    assert resolve_configured_dpi(configured_dpi=800) == 800
    assert resolve_configured_dpi(target_dpi=1600) == 1600
    assert resolve_configured_dpi(configured_dpi=800, target_dpi=800) == 800
    with pytest.raises(ValueError):
        resolve_configured_dpi(configured_dpi=800, target_dpi=1600)


def test_resources_load_schema_and_template():
    schema = session_schema()
    assert schema["properties"]["schema_version"]["const"] == "MOUSE_DPI_TOOL_SESSION_V1"
    template = manual_observation_template()
    assert {row["id"] for row in template} >= {"dpi_control_identification", "dpi_indicator_check"}


def test_path_quality_accumulator_keeps_complete_stream_not_ui_bound():
    acc = StreamingPathQualityAccumulator()
    n = VISUALIZATION_PATH_MAX_POINTS + 250
    for i in range(n):
        acc.on_sample(MovementSample(dx=10, dy=0, timestamp_s=float(i), device_id="dev"))
    assert acc.sample_count == n
    snap = acc.snapshot()
    assert snap["status"] == "PASS"
    assert snap["path_total_counts"] == float(n * 10)
    assert snap["evidence"] == "streaming_aggregates"
    assert snap["owner"] == "path_quality"


def test_capture_module_does_not_own_path_metrics():
    from mouse_dpi_tool import capture

    assert "path_total_counts" in capture.CAPTURE_MUST_NOT_COMPUTE
    text = Path(capture.__file__).read_text(encoding="utf-8")
    assert "def path_total" not in text
    engine_text = (Path(capture.__file__).parent / "engine.py").read_text(encoding="utf-8")
    assert "measured_cpi" not in engine_text
    assert "path_total_counts +=" not in engine_text


def test_standalone_package_has_no_external_runtime_coupling():
    """Architectural boundary: shipped package stays standalone.

    Forbidden patterns target shared/host orchestration and legacy companion
    tool coupling — not brand or employer names.
    """
    banned = (
        "shared_runtime",
        "run_from_hub",
        "dpi_step_tool",
        "import dpi_step_tool",
        "from dpi_step_tool",
    )
    offenders = []
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in banned:
            if token in text:
                offenders.append(f"{path.relative_to(SRC.parent)}:{token}")
    assert offenders == []


def test_findings_shell_has_no_overall_verdict():
    from mouse_dpi_tool.findings import empty_findings_shell

    shell = empty_findings_shell()
    assert "overall" not in shell
    assert "health" not in shell
    assert shell["linearity"]["status"] == "NOT_EVALUATED"
    assert shell["accuracy"]["status"] == "NOT_TESTED"
