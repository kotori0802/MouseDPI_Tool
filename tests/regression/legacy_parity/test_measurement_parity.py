"""Legacy measurement math / group / ratio parity against frozen golden fixtures.

Fixtures were generated from immutable MouseDPI_v0.4.1 only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mouse_dpi_tool.measurement.distance import distance_to_mm
from mouse_dpi_tool.measurement.group import build_group_summaries
from mouse_dpi_tool.measurement.legacy_compat import as_legacy_group, as_legacy_trial
from mouse_dpi_tool.measurement.ratio import build_ratio_analysis
from mouse_dpi_tool.measurement.settings import normalize_settings
from mouse_dpi_tool.measurement.synthetic import make_synthetic_trials
from mouse_dpi_tool.measurement.trial import compute_trial

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "golden"


def load_fixture(name: str) -> dict:
    import json

    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def project(row: dict, fields: list[str]) -> dict:
    return {k: row.get(k) for k in fields}


MATH_TRIAL_FIELDS = [
    "trial_id",
    "target_dpi",
    "distance_input",
    "distance_unit",
    "distance_mm",
    "axis",
    "direction",
    "movement_mode",
    "counts_x",
    "counts_y",
    "vector_counts",
    "primary_counts",
    "secondary_counts",
    "measured_cpi",
    "error_pct",
    "axis_leakage_pct",
    "cpi_error_pass_pct",
    "cpi_error_fail_pct",
    "tolerance_mode",
    "issue_tags",
    "group_id",
    "status",
]

GROUP_FIELDS = [
    "group_id",
    "target_dpi",
    "axis",
    "direction",
    "distance_mm",
    "movement_mode",
    "valid_trials",
    "avg_measured_cpi",
    "min_measured_cpi",
    "max_measured_cpi",
    "cpi_cv_pct",
    "avg_error_pct",
    "max_abs_error_pct",
    "avg_axis_leakage_pct",
    "max_axis_leakage_pct",
    "status",
    "issue_tags",
]

RATIO_FIELDS = [
    "axis",
    "direction",
    "distance_mm",
    "movement_mode",
    "from_dpi",
    "to_dpi",
    "expected_ratio",
    "measured_ratio",
    "ratio_error_pct",
    "status",
    "issue_tags",
]


def _assert_trials_match(actual: list[dict], expected: list[dict]) -> None:
    assert len(actual) == len(expected)
    for a, e in zip(actual, expected):
        assert project(as_legacy_trial(a), MATH_TRIAL_FIELDS) == project(e, MATH_TRIAL_FIELDS)


def test_canonical_trial_does_not_emit_target_dpi():
    t = compute_trial(
        trial_id=1,
        configured_dpi=800,
        distance_mm=30.0,
        axis="X",
        direction="X+",
        counts_x=945,
        counts_y=12,
        movement_mode="Vector Magnitude",
        distance_input=30.0,
        distance_unit="mm",
    )
    assert "configured_dpi" in t
    assert "target_dpi" not in t


def test_distance_to_mm_parity():
    data = load_fixture("03_distance_to_mm.json")
    for case in data["cases"]:
        assert distance_to_mm(case["value"], case["unit"]) == pytest.approx(case["expected_mm"])


def test_compute_trial_vector_magnitude_parity():
    data = load_fixture("01_compute_trial_vector_magnitude.json")
    settings = normalize_settings(data["settings"])
    actual = []
    for c in data["inputs"]:
        actual.append(
            compute_trial(
                trial_id=c["trial_id"],
                target_dpi=c["target_dpi"],
                distance_mm=settings["distance_mm"],
                axis=c["axis"],
                direction=c["direction"],
                counts_x=c["counts_x"],
                counts_y=c["counts_y"],
                source="golden_fixture",
                movement_mode="Vector Magnitude",
                distance_input=settings["distance_input"],
                distance_unit=settings["distance_unit"],
                tolerance_policy=settings,
            )
        )
    _assert_trials_match(actual, data["expected_trials"])


def test_compute_trial_axis_projection_parity():
    data = load_fixture("02_compute_trial_axis_projection.json")
    settings = normalize_settings(data["settings"])
    actual = []
    for c in data["inputs"]:
        actual.append(
            compute_trial(
                trial_id=c["trial_id"],
                target_dpi=c["target_dpi"],
                distance_mm=settings["distance_mm"],
                axis=c["axis"],
                direction=c["direction"],
                counts_x=c["counts_x"],
                counts_y=c["counts_y"],
                source="golden_fixture",
                movement_mode="Axis Projection",
                distance_input=settings["distance_input"],
                distance_unit=settings["distance_unit"],
                tolerance_policy=settings,
            )
        )
    _assert_trials_match(actual, data["expected_trials"])


def test_synthetic_group_ratio_parity():
    data = load_fixture("04_synthetic_group_ratio.json")
    settings = normalize_settings(data["settings"])
    spec = data["synthetic_spec"]
    trials = make_synthetic_trials(
        spec["dpi_steps"],
        distance_mm=spec["distance_mm"],
        trials_per_group=spec["trials_per_group"],
    )
    _assert_trials_match(trials, data["expected_trials"])

    groups = build_group_summaries(trials, settings)
    ratios = build_ratio_analysis(groups, settings)
    assert [project(as_legacy_group(g), GROUP_FIELDS) for g in groups] == data["expected_group_summaries"]
    assert [project(r, RATIO_FIELDS) for r in ratios] == data["expected_ratio_analysis"]


def test_hand_group_ratio_parity():
    data = load_fixture("05_hand_group_ratio.json")
    settings = normalize_settings(data["settings"])
    trials = []
    for c in data["inputs"]:
        trials.append(
            compute_trial(
                trial_id=c["trial_id"],
                target_dpi=c["target_dpi"],
                distance_mm=settings["distance_mm"],
                axis=c["axis"],
                direction=c["direction"],
                counts_x=c["counts_x"],
                counts_y=c["counts_y"],
                source="golden_fixture",
                movement_mode="Vector Magnitude",
                distance_input=settings["distance_input"],
                distance_unit=settings.get("distance_unit", "mm"),
                tolerance_policy=settings,
            )
        )

    _assert_trials_match(trials, data["expected_trials"])
    groups = build_group_summaries(trials, settings)
    ratios = build_ratio_analysis(groups, settings)
    assert [project(as_legacy_group(g), GROUP_FIELDS) for g in groups] == data["expected_group_summaries"]
    assert [project(r, RATIO_FIELDS) for r in ratios] == data["expected_ratio_analysis"]


def test_path_quality_fields_not_computed_by_measurement():
    t = compute_trial(
        trial_id=1,
        target_dpi=800,
        distance_mm=30.0,
        axis="X",
        direction="X+",
        counts_x=945,
        counts_y=12,
        movement_mode="Vector Magnitude",
        distance_input=30.0,
        distance_unit="mm",
    )
    assert t.get("path_total_counts") is None
    assert t.get("straightness_pct") is None
    assert t["configured_dpi"] == 800
    assert "target_dpi" not in t
