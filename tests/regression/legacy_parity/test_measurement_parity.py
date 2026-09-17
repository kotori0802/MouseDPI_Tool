"""Legacy measurement math / group / ratio parity against frozen golden fixtures.

Fixtures were generated from immutable MouseDPI_v0.4.1 only and must not be edited.
They remain historical evidence of the legacy directional Fixture Vector serialization.

V1 Fixture Vector intentionally normalizes axis/direction to N/A and merges opposite
signed directions into one DPI/distance/mode bucket. This harness therefore:

- compares legacy-comparable trial fields for Vector Magnitude (not axis/direction/group_id)
- keeps full geometry parity for Axis Projection
- derives V1 merged group/ratio *numeric* expectations independently from frozen
  expected_trials (stdlib statistics) — never by calling build_group_summaries /
  build_ratio_analysis to produce the expected side
- still records grouping/ratio *shape* incompatibility vs frozen directional aggregates
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

import pytest

from mouse_dpi_tool.measurement.distance import distance_to_mm
from mouse_dpi_tool.measurement.group import build_group_summaries
from mouse_dpi_tool.measurement.legacy_compat import as_legacy_group, as_legacy_trial
from mouse_dpi_tool.measurement.ratio import build_ratio_analysis
from mouse_dpi_tool.measurement.settings import normalize_settings, status_from_limits
from mouse_dpi_tool.measurement.synthetic import make_synthetic_trials
from mouse_dpi_tool.measurement.trial import compute_trial

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "golden"

# V1 Fixture Vector serialization excluded from Vector Magnitude trial parity:
# axis, direction, group_id.


def load_fixture(name: str) -> dict:
    import json

    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def project(row: dict, fields: list[str]) -> dict:
    return {k: row.get(k) for k in fields}


# Fields still comparable to MouseDPI_v0.4.1 trial rows under Vector Magnitude.
# Name stresses "comparable contract", not pure arithmetic-only.
LEGACY_COMPARABLE_TRIAL_FIELDS = [
    "trial_id",
    "target_dpi",
    "distance_input",
    "distance_unit",
    "distance_mm",
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
    "status",
]

# Axis Projection still claims directional metadata — include geometry in that gate.
AXIS_PROJECTION_TRIAL_FIELDS = [
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

# Group numeric/statistical fields that survive X+/X- → N/A merge.
V1_MERGED_GROUP_NUMERIC_FIELDS = [
    "target_dpi",
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

V1_MERGED_RATIO_NUMERIC_FIELDS = [
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


def _assert_trials_match(actual: list[dict], expected: list[dict], fields: list[str]) -> None:
    assert len(actual) == len(expected)
    for a, e in zip(actual, expected):
        assert project(as_legacy_trial(a), fields) == project(e, fields)


def _population_cv_pct(values: list[float]) -> float | None:
    """Independent CV% using population stdev (matches legacy group math)."""
    if not values:
        return None
    avg = mean(values)
    if avg == 0:
        return None
    if len(values) == 1:
        return 0.0
    return pstdev(values) / avg * 100.0


def _merge_key_from_legacy_trial(trial: dict) -> tuple:
    """V1 Fixture Vector merge key: ignore legacy axis/direction."""
    return (trial["target_dpi"], trial["distance_mm"], trial["movement_mode"])


def _expected_v1_merged_groups_from_legacy_trials(
    legacy_trials: list[dict], settings: dict
) -> list[dict]:
    """Derive V1 merged group numerics from frozen trial rows only (no production aggregators)."""
    policy = normalize_settings(settings)
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for trial in legacy_trials:
        buckets[_merge_key_from_legacy_trial(trial)].append(trial)

    expected: list[dict] = []
    for key in sorted(buckets.keys()):
        rows = buckets[key]
        cpis = [float(t["measured_cpi"]) for t in rows]
        errors = [float(t["error_pct"]) for t in rows]
        leaks = [float(t["axis_leakage_pct"]) for t in rows]
        avg_cpi = mean(cpis)
        cv = _population_cv_pct(cpis)
        avg_error = mean(errors)
        max_abs_error = max(abs(v) for v in errors)
        avg_leak = mean(leaks)
        max_leak = max(leaks)

        status = "PASS"
        tags: list[str] = []
        if len(rows) < policy["min_valid_trials_per_group"]:
            status = "WARN"
            tags.append("INSUFFICIENT_TRIALS")

        error_status = status_from_limits(
            max_abs_error, policy["cpi_error_pass_pct"], policy["cpi_error_fail_pct"]
        )
        cv_status = status_from_limits(
            cv or 0.0, policy["cpi_cv_pass_pct"], policy["cpi_cv_fail_pct"]
        )
        # Vector Magnitude: leakage does not escalate group status.
        leakage_status = "PASS"
        rank = {"PASS": 0, "WARN": 1, "FAIL": 2}
        for candidate, tag in [
            (error_status, "CPI_ERROR"),
            (cv_status, "CPI_CV"),
            (leakage_status, "AXIS_LEAKAGE"),
        ]:
            if rank[candidate] > rank[status]:
                status = candidate
            if candidate != "PASS":
                tags.append(f"{tag}_{candidate}")

        expected.append(
            {
                "target_dpi": key[0],
                "distance_mm": key[1],
                "movement_mode": key[2],
                "valid_trials": len(rows),
                "avg_measured_cpi": round(avg_cpi, 4),
                "min_measured_cpi": round(min(cpis), 4),
                "max_measured_cpi": round(max(cpis), 4),
                "cpi_cv_pct": round(cv, 4) if cv is not None else None,
                "avg_error_pct": round(avg_error, 4),
                "max_abs_error_pct": round(max_abs_error, 4),
                "avg_axis_leakage_pct": round(avg_leak, 4),
                "max_axis_leakage_pct": round(max_leak, 4),
                "status": status,
                "issue_tags": ";".join(tags),
            }
        )
    return expected


def _expected_v1_merged_ratios_from_legacy_trials(
    legacy_trials: list[dict], settings: dict
) -> list[dict]:
    """Derive V1 merged DPI-step ratios from frozen trial CPI means (no production aggregators)."""
    policy = normalize_settings(settings)
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for trial in legacy_trials:
        buckets[_merge_key_from_legacy_trial(trial)].append(trial)

    # One merged group per DPI at a given distance/mode.
    by_lane: dict[tuple, list[tuple[int, float]]] = defaultdict(list)
    for (dpi, distance, mode), rows in buckets.items():
        avg_cpi = mean(float(t["measured_cpi"]) for t in rows)
        by_lane[(distance, mode)].append((dpi, avg_cpi))

    expected: list[dict] = []
    for (distance, mode), items in sorted(by_lane.items()):
        items = sorted(items, key=lambda x: x[0])
        for (from_dpi, from_cpi), (to_dpi, to_cpi) in zip(items, items[1:]):
            expected_ratio = to_dpi / from_dpi
            measured_ratio = to_cpi / from_cpi
            ratio_error_pct = (measured_ratio - expected_ratio) / expected_ratio * 100.0
            status = status_from_limits(
                abs(ratio_error_pct),
                policy["ratio_error_pass_pct"],
                policy["ratio_error_fail_pct"],
            )
            expected.append(
                {
                    "distance_mm": distance,
                    "movement_mode": mode,
                    "from_dpi": from_dpi,
                    "to_dpi": to_dpi,
                    "expected_ratio": round(expected_ratio, 6),
                    "measured_ratio": round(measured_ratio, 6),
                    "ratio_error_pct": round(ratio_error_pct, 4),
                    "status": status,
                    "issue_tags": "" if status == "PASS" else f"DPI_RATIO_{status}",
                }
            )
    return expected


def _assert_v1_merged_group_numeric_parity(
    actual_groups: list[dict], legacy_trials: list[dict], settings: dict
) -> None:
    expected = _expected_v1_merged_groups_from_legacy_trials(legacy_trials, settings)
    actual = [as_legacy_group(g) for g in actual_groups]
    assert [project(g, V1_MERGED_GROUP_NUMERIC_FIELDS) for g in actual] == [
        project(g, V1_MERGED_GROUP_NUMERIC_FIELDS) for g in expected
    ]
    for g in actual:
        assert g["axis"] == "N/A"
        assert g["direction"] == "N/A"
        assert "N/A" in str(g["group_id"])


def _assert_v1_merged_ratio_numeric_parity(
    actual_ratios: list[dict], legacy_trials: list[dict], settings: dict
) -> None:
    expected = _expected_v1_merged_ratios_from_legacy_trials(legacy_trials, settings)
    assert [project(r, V1_MERGED_RATIO_NUMERIC_FIELDS) for r in actual_ratios] == [
        project(r, V1_MERGED_RATIO_NUMERIC_FIELDS) for r in expected
    ]
    for r in actual_ratios:
        assert r["axis"] == "N/A"
        assert r["direction"] == "N/A"


def _assert_v1_fixture_vector_grouping_shape_vs_legacy(
    actual_groups: list[dict],
    legacy_groups: list[dict],
    actual_ratios: list[dict],
    legacy_ratios: list[dict],
) -> None:
    """Shape-only: legacy directional aggregates remain finer than V1 merged N/A buckets."""
    assert any(g.get("direction") in {"X+", "X-", "Y+", "Y-"} for g in legacy_groups)
    assert len(legacy_groups) == 2 * len(actual_groups)
    assert len(legacy_ratios) == 2 * len(actual_ratios)


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
    _assert_trials_match(actual, data["expected_trials"], LEGACY_COMPARABLE_TRIAL_FIELDS)
    for a in actual:
        legacy = as_legacy_trial(a)
        assert legacy["axis"] == "N/A"
        assert legacy["direction"] == "N/A"
        assert "N/A" in str(legacy["group_id"])


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
    _assert_trials_match(actual, data["expected_trials"], AXIS_PROJECTION_TRIAL_FIELDS)


def test_synthetic_group_ratio_parity():
    data = load_fixture("04_synthetic_group_ratio.json")
    settings = normalize_settings(data["settings"])
    spec = data["synthetic_spec"]
    # Counts/math from shared generator; re-apply fixture tolerance_policy for
    # comparable tolerance_mode without editing production make_synthetic_trials.
    seeded = make_synthetic_trials(
        spec["dpi_steps"],
        distance_mm=spec["distance_mm"],
        trials_per_group=spec["trials_per_group"],
    )
    trials = [
        compute_trial(
            trial_id=t["trial_id"],
            configured_dpi=t["configured_dpi"],
            distance_mm=t["distance_mm"],
            axis="X",
            direction="X+",
            counts_x=t["counts_x"],
            counts_y=t["counts_y"],
            source=t.get("source", "self_test"),
            movement_mode="Vector Magnitude",
            distance_input=t["distance_input"],
            distance_unit=t["distance_unit"],
            tolerance_policy=settings,
        )
        for t in seeded
    ]
    _assert_trials_match(trials, data["expected_trials"], LEGACY_COMPARABLE_TRIAL_FIELDS)

    groups = build_group_summaries(trials, settings)
    ratios = build_ratio_analysis(groups, settings)
    _assert_v1_merged_group_numeric_parity(groups, data["expected_trials"], settings)
    _assert_v1_merged_ratio_numeric_parity(ratios, data["expected_trials"], settings)
    _assert_v1_fixture_vector_grouping_shape_vs_legacy(
        groups,
        data["expected_group_summaries"],
        ratios,
        data["expected_ratio_analysis"],
    )


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

    _assert_trials_match(trials, data["expected_trials"], LEGACY_COMPARABLE_TRIAL_FIELDS)
    groups = build_group_summaries(trials, settings)
    ratios = build_ratio_analysis(groups, settings)
    _assert_v1_merged_group_numeric_parity(groups, data["expected_trials"], settings)
    _assert_v1_merged_ratio_numeric_parity(ratios, data["expected_trials"], settings)
    _assert_v1_fixture_vector_grouping_shape_vs_legacy(
        groups,
        data["expected_group_summaries"],
        ratios,
        data["expected_ratio_analysis"],
    )


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
