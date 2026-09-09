"""Findings Layer + Findings-0A/0B guardrails."""

from __future__ import annotations

import pytest

from mouse_dpi_tool.findings import build_findings_from_mapping, empty_findings_shell
from mouse_dpi_tool.session import Session, validate_session


def _session(**kwargs) -> Session:
    settings = {
        "distance_mm": 100.0,
        "movement_mode": "Vector Magnitude",
        "min_valid_trials_per_group": 3,
        "cpi_error_pass_pct": 3.0,
        "cpi_error_fail_pct": 5.0,
        "cpi_cv_pass_pct": 1.0,
        "cpi_cv_fail_pct": 3.0,
        "ratio_error_pass_pct": 2.0,
        "ratio_error_fail_pct": 5.0,
    }
    if "settings" in kwargs:
        settings = {**settings, **kwargs.pop("settings")}
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
        settings=settings,
        operator="tester",
        **kwargs,
    )


def _perfect_counts(dpi: int, distance_mm: float = 100.0) -> int:
    return int(round(dpi * (distance_mm / 25.4)))


def test_findings_0a_settings_dut_context_manual_snapshots_immutable():
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    session.set_manual_observation("dpi_indicator_check", status="PASS")

    settings = session.settings
    settings["distance_mm"] = 50
    dut = session.dut
    dut["vendor"] = "HACKED"
    ctx = session.measurement_context
    ctx["method"] = "fixture"
    manuals = session.manual_observations
    manuals[0]["status"] = "FAIL"

    assert session.settings["distance_mm"] == 100.0
    assert session.dut["vendor"] == "ExampleVendor"
    assert session.measurement_context["method"] == "synthetic"
    assert session.manual_observations[0]["status"] == "PASS"
    payload = session.to_session_dict()
    assert payload["settings"]["distance_mm"] == 100.0
    assert payload["dut"]["vendor"] == "ExampleVendor"
    assert payload["findings"]["manual_observations"][0]["status"] == "PASS"


def test_findings_0a_structural_settings_locked_after_trials():
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    with pytest.raises(ValueError, match="structural setting"):
        session.update_settings({"distance_mm": 50.0})
    # Threshold updates still allowed and rebuild analysis.
    session.update_settings({"cpi_error_pass_pct": 2.5})
    assert session.settings["cpi_error_pass_pct"] == 2.5


def test_accuracy_pass_warn_fail():
    s_pass = _session()
    s_pass.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    assert s_pass.to_session_dict()["findings"]["accuracy"]["status"] == "PASS"

    s_warn = _session()
    # ~4% error → WARN (pass 3, fail 5)
    s_warn.add_synthetic_trial(configured_dpi=800, counts_x=int(_perfect_counts(800) * 1.04))
    assert s_warn.to_session_dict()["findings"]["accuracy"]["status"] == "WARN"

    s_fail = _session()
    s_fail.add_synthetic_trial(configured_dpi=800, counts_x=int(_perfect_counts(800) * 1.10))
    assert s_fail.to_session_dict()["findings"]["accuracy"]["status"] == "FAIL"


def test_accuracy_unaffected_by_path_quality_failure():
    session = _session()
    session.add_synthetic_trial(
        configured_dpi=800,
        counts_x=_perfect_counts(800),
        path_quality_snapshot={
            "path_total_counts": 5000.0,
            "straightness_pct": 10.0,
            "status": "FAIL",
            "issue_codes": ["PATH_REVERSAL_OR_JITTER_FAIL"],
            "fixture_noise_floor_counts": 7,
        },
    )
    findings = session.to_session_dict()["findings"]
    assert findings["accuracy"]["status"] == "PASS"
    assert findings["path_quality"]["status"] == "FAIL"


def test_accuracy_unaffected_by_manual_observation_failure():
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    session.set_manual_observation("dpi_indicator_check", status="FAIL")
    findings = session.to_session_dict()["findings"]
    assert findings["accuracy"]["status"] == "PASS"
    assert findings["manual_observations"][0]["status"] == "FAIL"


def test_repeatability_pass_warn_fail_with_sufficient_evidence():
    session = _session(settings={
        "distance_mm": 100.0,
        "min_valid_trials_per_group": 3,
        "cpi_cv_pass_pct": 1.0,
        "cpi_cv_fail_pct": 3.0,
    })
    base = _perfect_counts(800)
    for n in (base, base, base):
        session.add_synthetic_trial(configured_dpi=800, counts_x=n)
    assert session.to_session_dict()["findings"]["repeatability"]["status"] == "PASS"

    session2 = _session(settings={
        "distance_mm": 100.0,
        "min_valid_trials_per_group": 3,
        "cpi_cv_pass_pct": 1.0,
        "cpi_cv_fail_pct": 3.0,
    })
    for n in (base, int(base * 1.08), int(base * 0.92)):
        session2.add_synthetic_trial(configured_dpi=800, counts_x=n)
    assert session2.to_session_dict()["findings"]["repeatability"]["status"] == "FAIL"


def test_repeatability_warn_with_moderate_cv():
    session = _session(settings={
        "distance_mm": 100.0,
        "min_valid_trials_per_group": 3,
        "cpi_cv_pass_pct": 1.0,
        "cpi_cv_fail_pct": 3.0,
    })
    base = _perfect_counts(800)
    # ~1.5–2% CV band → WARN
    for n in (base, int(base * 1.02), int(base * 0.98)):
        session.add_synthetic_trial(configured_dpi=800, counts_x=n)
    status = session.to_session_dict()["findings"]["repeatability"]["status"]
    assert status == "WARN"


def test_repeatability_insufficient_evidence_is_not_evaluated_not_fail():
    session = _session(settings={"distance_mm": 100.0, "min_valid_trials_per_group": 3})
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    finding = session.to_session_dict()["findings"]["repeatability"]
    assert finding["status"] == "NOT_EVALUATED"
    assert "INSUFFICIENT_REPEATABILITY_EVIDENCE" in finding["issue_codes"]


def test_ratio_pass_warn_fail():
    session = _session(settings={"distance_mm": 100.0, "min_valid_trials_per_group": 1})
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    session.add_synthetic_trial(configured_dpi=1600, counts_x=_perfect_counts(1600))
    assert session.to_session_dict()["findings"]["ratio"]["status"] == "PASS"

    bad = _session(settings={"distance_mm": 100.0, "min_valid_trials_per_group": 1})
    bad.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    bad.add_synthetic_trial(configured_dpi=1600, counts_x=_perfect_counts(800))
    assert bad.to_session_dict()["findings"]["ratio"]["status"] == "FAIL"


def test_ratio_warn():
    session = _session(settings={
        "distance_mm": 100.0,
        "min_valid_trials_per_group": 1,
        "ratio_error_pass_pct": 2.0,
        "ratio_error_fail_pct": 5.0,
    })
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    # Expected ratio 2.0; measured ~2.06 → ~3% error → WARN
    session.add_synthetic_trial(configured_dpi=1600, counts_x=int(_perfect_counts(1600) * 1.03))
    assert session.to_session_dict()["findings"]["ratio"]["status"] == "WARN"


def test_path_quality_statuses():
    s = _session()
    assert s.to_session_dict()["findings"]["path_quality"]["status"] == "NOT_TESTED"

    s2 = _session()
    s2.add_synthetic_trial(
        configured_dpi=800,
        counts_x=_perfect_counts(800),
        path_quality_snapshot={
            "path_total_counts": 3150.0,
            "straightness_pct": 100.0,
            "status": "PASS",
            "issue_codes": [],
            "fixture_noise_floor_counts": 7,
        },
    )
    assert s2.to_session_dict()["findings"]["path_quality"]["status"] == "PASS"

    s3 = _session()
    s3.add_synthetic_trial(
        configured_dpi=800,
        counts_x=_perfect_counts(800),
        path_quality_snapshot={
            "path_total_counts": 0.0,
            "straightness_pct": 0.0,
            "status": "NOT_EVALUATED",
            "issue_codes": ["NO_PATH_EVIDENCE_ABOVE_NOISE_FLOOR"],
            "fixture_noise_floor_counts": 7,
        },
    )
    assert s3.to_session_dict()["findings"]["path_quality"]["status"] == "NOT_EVALUATED"


def test_path_quality_not_evaluated_mixed_with_pass_is_warn():
    session = _session(settings={"distance_mm": 100.0, "min_valid_trials_per_group": 1})
    session.add_synthetic_trial(
        configured_dpi=800,
        counts_x=_perfect_counts(800),
        path_quality_snapshot={
            "path_total_counts": 3150.0,
            "straightness_pct": 100.0,
            "status": "PASS",
            "issue_codes": [],
            "fixture_noise_floor_counts": 7,
        },
    )
    session.add_synthetic_trial(
        configured_dpi=800,
        counts_x=_perfect_counts(800),
        path_quality_snapshot={
            "path_total_counts": 0.0,
            "straightness_pct": 0.0,
            "status": "NOT_EVALUATED",
            "issue_codes": ["NO_PATH_EVIDENCE_ABOVE_NOISE_FLOOR"],
            "fixture_noise_floor_counts": 7,
        },
    )
    finding = session.to_session_dict()["findings"]["path_quality"]
    assert finding["status"] == "WARN"
    assert "PATH_QUALITY_COVERAGE_INCOMPLETE" in finding["issue_codes"]
    assert finding["metrics"]["pq_not_evaluated"] == 1


def test_path_quality_incomplete_coverage_is_warn():
    session = _session(settings={"distance_mm": 100.0, "min_valid_trials_per_group": 1})
    session.add_synthetic_trial(
        configured_dpi=800,
        counts_x=_perfect_counts(800),
        path_quality_snapshot={
            "path_total_counts": 3150.0,
            "straightness_pct": 100.0,
            "status": "PASS",
            "issue_codes": [],
            "fixture_noise_floor_counts": 7,
        },
    )
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    finding = session.to_session_dict()["findings"]["path_quality"]
    assert finding["status"] == "WARN"
    assert "PATH_QUALITY_COVERAGE_INCOMPLETE" in finding["issue_codes"]
    assert finding["metrics"]["pq_missing_count"] == 1


def test_path_quality_fail_still_wins_over_incomplete_coverage():
    session = _session(settings={"distance_mm": 100.0, "min_valid_trials_per_group": 1})
    session.add_synthetic_trial(
        configured_dpi=800,
        counts_x=_perfect_counts(800),
        path_quality_snapshot={
            "path_total_counts": 9000.0,
            "straightness_pct": 5.0,
            "status": "FAIL",
            "issue_codes": ["PATH_REVERSAL_OR_JITTER_FAIL"],
            "fixture_noise_floor_counts": 7,
        },
    )
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    finding = session.to_session_dict()["findings"]["path_quality"]
    assert finding["status"] == "FAIL"
    assert "PATH_QUALITY_COVERAGE_INCOMPLETE" in finding["issue_codes"]


def test_failed_path_quality_does_not_rewrite_accuracy():
    session = _session()
    session.add_synthetic_trial(
        configured_dpi=800,
        counts_x=_perfect_counts(800),
        path_quality_snapshot={
            "path_total_counts": 9000.0,
            "straightness_pct": 5.0,
            "status": "FAIL",
            "issue_codes": ["PATH_REVERSAL_OR_JITTER_FAIL"],
            "fixture_noise_floor_counts": 7,
        },
    )
    f = session.to_session_dict()["findings"]
    assert f["accuracy"]["status"] == "PASS"
    assert f["path_quality"]["status"] == "FAIL"
    assert session.active_trials[0]["measurement_status"] == "PASS"


def test_manual_observations_independent():
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=int(_perfect_counts(800) * 1.10))
    session.set_manual_observation("dpi_stage_count", status="PASS")
    f = session.to_session_dict()["findings"]
    assert f["accuracy"]["status"] == "FAIL"
    assert f["manual_observations"][0]["status"] == "PASS"


def test_reserved_findings_remain_not_evaluated():
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    f = session.to_session_dict()["findings"]
    assert f["linearity"]["status"] == "NOT_EVALUATED"
    assert f["scaling_evidence"]["status"] == "NOT_EVALUATED"
    assert f["native_capability"]["status"] == "NOT_EVALUATED"


def test_findings_from_active_trials_only_rejected_deleted_ignored():
    session = _session(settings={"distance_mm": 100.0, "min_valid_trials_per_group": 1})
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    session.add_synthetic_trial(configured_dpi=800, counts_x=int(_perfect_counts(800) * 1.20))
    session.reject_trial(2)
    session.add_synthetic_trial(configured_dpi=800, counts_x=int(_perfect_counts(800) * 1.20))
    session.delete_trial(3)
    f = session.to_session_dict()["findings"]
    assert f["accuracy"]["status"] == "PASS"
    assert f["accuracy"]["metrics"]["active_trial_count"] == 1


def test_tampered_derived_trial_and_group_fields_cannot_forge_findings():
    session = _session(settings={"distance_mm": 100.0, "min_valid_trials_per_group": 1})
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    session.add_synthetic_trial(configured_dpi=1600, counts_x=_perfect_counts(1600))
    payload = session.to_session_dict()
    clean = build_findings_from_mapping(payload)

    # Tamper exported derived Trial + group/ratio rows; keep primitive counts.
    for trial in payload["trials"]:
        trial["error_pct"] = 99.0
        trial["measured_cpi"] = 1.0
        trial["axis_leakage_pct"] = 99.0
        trial["measurement_status"] = "FAIL"
    payload["group_summaries"][0]["status"] = "FAIL"
    payload["group_summaries"][0]["avg_measured_cpi"] = 1.0
    payload["ratio_analysis"][0]["status"] = "FAIL"
    payload["ratio_analysis"][0]["measured_ratio"] = 99.0

    rebuilt = build_findings_from_mapping(payload)
    assert rebuilt["accuracy"]["status"] == clean["accuracy"]["status"] == "PASS"
    assert rebuilt["ratio"]["status"] == clean["ratio"]["status"] == "PASS"
    assert rebuilt["accuracy"]["metrics"]["max_abs_error_pct"] == clean["accuracy"]["metrics"]["max_abs_error_pct"]


def test_policy_update_reevaluates_trial_group_and_finding_consistently():
    session = _session(settings={
        "distance_mm": 100.0,
        "min_valid_trials_per_group": 1,
        "cpi_error_pass_pct": 3.0,
        "cpi_error_fail_pct": 5.0,
    })
    # ~4% error → WARN under 3%/5%
    session.add_synthetic_trial(configured_dpi=800, counts_x=int(_perfect_counts(800) * 1.04))
    before = session.to_session_dict()
    assert before["trials"][0]["measurement_status"] == "WARN"
    assert before["findings"]["accuracy"]["status"] == "WARN"

    session.update_settings({"cpi_error_pass_pct": 4.5})
    after = session.to_session_dict()
    assert after["settings"]["cpi_error_pass_pct"] == 4.5
    assert after["trials"][0]["measurement_status"] == "PASS"
    assert after["trials"][0]["cpi_error_pass_pct"] == 4.5
    assert after["group_summaries"][0]["status"] == "PASS"
    assert after["findings"]["accuracy"]["status"] == "PASS"
    validate_session(after)


def test_no_overall_verdict_in_findings_or_metrics():
    session = _session()
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    payload = session.to_session_dict()
    assert "overall" not in payload["findings"]
    assert "health" not in payload["findings"]
    assert "health" not in payload["metrics"]
    assert "overall_status" not in payload["metrics"]
    for key, value in payload["findings"].items():
        if key == "manual_observations":
            continue
        assert set(value.keys()) <= {"status", "issue_codes", "metrics", "notes"}


def test_findings_json_validates_against_session_schema():
    session = _session(settings={"distance_mm": 100.0, "min_valid_trials_per_group": 1})
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    session.add_synthetic_trial(configured_dpi=1600, counts_x=_perfect_counts(1600))
    session.set_manual_observation("dpi_control_identification", status="PASS")
    validate_session(session.to_session_dict())


def test_empty_findings_shell_still_has_no_overall():
    shell = empty_findings_shell()
    assert "overall" not in shell
    assert shell["linearity"]["status"] == "NOT_EVALUATED"
