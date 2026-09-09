#!/usr/bin/env python3
"""Generate frozen golden fixtures from immutable MouseDPI_v0.4.1 ONLY.

Owner attestation: MouseDPI_v0.4.1 is the project owner's earlier prototype
(USER_ATTESTED_CLEAN). This script must import legacy code exclusively.
Do not import mouse_dpi_tool. Re-run only when intentionally refreshing
fixtures from a known legacy tag. Do not embed machine-specific paths
in committed config; pass --legacy-root or MOUSEDPI_LEGACY_ROOT.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "golden"
LEGACY_SOURCE = "MouseDPI_v0.4.1"
LEGACY_VERSION = "0.4.11-report-lifecycle-field-result"

# Fields that are time-varying or intentionally divergent in V1 — strip from expected.
STRIP_TRIAL_FIELDS = {"created_at"}
# Legacy merged status includes leakage into trial.status; we still capture it for
# documentation, but parity tests compare measurement math fields, not path-merged status.
COMPARE_TRIAL_FIELDS = [
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
    # Keep legacy status for documentation of intentional divergence; parity tests
    # compare cpi_status-relevant math, not path_quality-merged status.
    "status",
]

COMPARE_GROUP_FIELDS = [
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

COMPARE_RATIO_FIELDS = [
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


def _project(row: dict, fields: list[str]) -> dict:
    return {k: row.get(k) for k in fields}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate golden fixtures from immutable legacy package only.")
    parser.add_argument(
        "--legacy-root",
        default=os.environ.get("MOUSEDPI_LEGACY_ROOT", ""),
        help="Path to MouseDPI_v0.4.1 package root (or set MOUSEDPI_LEGACY_ROOT).",
    )
    args = parser.parse_args(argv)
    if not str(args.legacy_root).strip():
        print("error: pass --legacy-root PATH or set MOUSEDPI_LEGACY_ROOT", file=sys.stderr)
        return 2
    legacy_app = Path(args.legacy_root).expanduser().resolve() / "app"
    if not (legacy_app / "dpi_step_tool" / "core.py").is_file():
        print(f"error: legacy core not found under {legacy_app}", file=sys.stderr)
        return 2
    if str(legacy_app) not in sys.path:
        sys.path.insert(0, str(legacy_app))

    from dpi_step_tool.core import (  # type: ignore
        build_group_summaries,
        build_ratio_analysis,
        compute_trial,
        distance_to_mm,
        make_synthetic_trials,
        normalize_settings,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source_package": LEGACY_SOURCE,
        "source_tool_version": LEGACY_VERSION,
        "generator": Path(__file__).name,
        "note": "Frozen from legacy only. Do not regenerate from MouseDPI_Tool outputs.",
        "fixtures": [],
    }

    # --- Fixture 01: single vector-magnitude trials (hand-picked counts) ---
    settings_vm = normalize_settings(
        {
            "distance_input": 30.0,
            "distance_unit": "mm",
            "movement_mode": "Vector Magnitude",
            "cpi_error_pass_pct": 3.0,
            "cpi_error_fail_pct": 5.0,
            "dpi_steps": [800],
        }
    )
    cases_vm = [
        {"trial_id": 1, "target_dpi": 800, "counts_x": 945, "counts_y": 12, "axis": "X", "direction": "X+"},
        {"trial_id": 2, "target_dpi": 800, "counts_x": -940, "counts_y": 8, "axis": "X", "direction": "X-"},
        {"trial_id": 3, "target_dpi": 1600, "counts_x": 1880, "counts_y": 20, "axis": "X", "direction": "X+"},
        {"trial_id": 4, "target_dpi": 800, "counts_x": 600, "counts_y": 600, "axis": "X", "direction": "DIAG"},
        {"trial_id": 5, "target_dpi": 800, "counts_x": 0, "counts_y": 0, "axis": "X", "direction": "X+"},
    ]
    trials_vm = []
    for c in cases_vm:
        t = compute_trial(
            trial_id=c["trial_id"],
            target_dpi=c["target_dpi"],
            distance_mm=settings_vm["distance_mm"],
            axis=c["axis"],
            direction=c["direction"],
            counts_x=c["counts_x"],
            counts_y=c["counts_y"],
            source="golden_fixture",
            movement_mode="Vector Magnitude",
            distance_input=settings_vm["distance_input"],
            distance_unit=settings_vm["distance_unit"],
            tolerance_policy=settings_vm,
        )
        trials_vm.append(_project(t, COMPARE_TRIAL_FIELDS))

    _write(
        OUT_DIR / "01_compute_trial_vector_magnitude.json",
        {
            "fixture_id": "01_compute_trial_vector_magnitude",
            "kind": "compute_trial",
            "settings": {k: settings_vm[k] for k in (
                "distance_input", "distance_unit", "distance_mm", "movement_mode",
                "cpi_error_pass_pct", "cpi_error_fail_pct", "tolerance_mode",
            )},
            "inputs": cases_vm,
            "expected_trials": trials_vm,
        },
        manifest,
    )

    # --- Fixture 02: axis projection ---
    settings_ap = normalize_settings(
        {
            "distance_input": 5.0,
            "distance_unit": "cm",
            "movement_mode": "Axis Projection",
            "cpi_error_pass_pct": 3.0,
            "axis_leakage_pass_pct": 2.0,
            "axis_leakage_fail_pct": 5.0,
        }
    )
    cases_ap = [
        {"trial_id": 1, "target_dpi": 400, "counts_x": 787, "counts_y": 5, "axis": "X", "direction": "X+"},
        {"trial_id": 2, "target_dpi": 400, "counts_x": 787, "counts_y": 50, "axis": "X", "direction": "X+"},
        {"trial_id": 3, "target_dpi": 800, "counts_x": 10, "counts_y": 1575, "axis": "Y", "direction": "Y+"},
    ]
    trials_ap = []
    for c in cases_ap:
        t = compute_trial(
            trial_id=c["trial_id"],
            target_dpi=c["target_dpi"],
            distance_mm=settings_ap["distance_mm"],
            axis=c["axis"],
            direction=c["direction"],
            counts_x=c["counts_x"],
            counts_y=c["counts_y"],
            source="golden_fixture",
            movement_mode="Axis Projection",
            distance_input=settings_ap["distance_input"],
            distance_unit=settings_ap["distance_unit"],
            tolerance_policy=settings_ap,
        )
        trials_ap.append(_project(t, COMPARE_TRIAL_FIELDS))

    _write(
        OUT_DIR / "02_compute_trial_axis_projection.json",
        {
            "fixture_id": "02_compute_trial_axis_projection",
            "kind": "compute_trial",
            "settings": {k: settings_ap[k] for k in (
                "distance_input", "distance_unit", "distance_mm", "movement_mode",
                "cpi_error_pass_pct", "cpi_error_fail_pct",
                "axis_leakage_pass_pct", "axis_leakage_fail_pct", "tolerance_mode",
            )},
            "inputs": cases_ap,
            "expected_trials": trials_ap,
        },
        manifest,
    )

    # --- Fixture 03: distance conversion ---
    distance_cases = [
        {"value": 100.0, "unit": "mm", "expected_mm": distance_to_mm(100.0, "mm")},
        {"value": 3.0, "unit": "cm", "expected_mm": distance_to_mm(3.0, "cm")},
        {"value": 2.0, "unit": "inch", "expected_mm": distance_to_mm(2.0, "inch")},
        {"value": 1.0, "unit": "in", "expected_mm": distance_to_mm(1.0, "in")},
        {"value": 5.0, "unit": "centimeters", "expected_mm": distance_to_mm(5.0, "centimeters")},
    ]
    _write(
        OUT_DIR / "03_distance_to_mm.json",
        {
            "fixture_id": "03_distance_to_mm",
            "kind": "distance_to_mm",
            "cases": distance_cases,
        },
        manifest,
    )

    # --- Fixture 04: group + ratio from synthetic (seeded) ---
    syn_settings = normalize_settings(
        {
            "distance_input": 100.0,
            "distance_unit": "mm",
            "dpi_steps": [400, 800, 1600],
            "trials_per_group": 3,
            "min_valid_trials_per_group": 3,
            "movement_mode": "Vector Magnitude",
            "cpi_error_pass_pct": 3.0,
            "cpi_cv_pass_pct": 1.0,
            "cpi_cv_fail_pct": 3.0,
            "ratio_error_pass_pct": 2.0,
            "ratio_error_fail_pct": 5.0,
        }
    )
    syn_trials_raw = make_synthetic_trials([400, 800, 1600], distance_mm=100.0, trials_per_group=3)
    # Freeze without timestamps
    syn_trials = [_project(t, COMPARE_TRIAL_FIELDS) for t in syn_trials_raw]
    # Rebuild trial dicts with enough fields for group/ratio (use full raw but strip created_at)
    syn_for_group = []
    for t in syn_trials_raw:
        row = deepcopy(t)
        row.pop("created_at", None)
        syn_for_group.append(row)
    groups = build_group_summaries(syn_for_group, syn_settings)
    ratios = build_ratio_analysis(groups, syn_settings)

    _write(
        OUT_DIR / "04_synthetic_group_ratio.json",
        {
            "fixture_id": "04_synthetic_group_ratio",
            "kind": "group_and_ratio",
            "settings": {
                k: syn_settings[k]
                for k in (
                    "distance_input",
                    "distance_unit",
                    "distance_mm",
                    "dpi_steps",
                    "trials_per_group",
                    "min_valid_trials_per_group",
                    "movement_mode",
                    "cpi_error_pass_pct",
                    "cpi_error_fail_pct",
                    "cpi_cv_pass_pct",
                    "cpi_cv_fail_pct",
                    "ratio_error_pass_pct",
                    "ratio_error_fail_pct",
                    "tolerance_mode",
                )
            },
            "synthetic_spec": {
                "dpi_steps": [400, 800, 1600],
                "distance_mm": 100.0,
                "trials_per_group": 3,
                "random_seed": 42,
                "generator": "legacy make_synthetic_trials",
            },
            "expected_trials": syn_trials,
            "expected_group_summaries": [_project(g, COMPARE_GROUP_FIELDS) for g in groups],
            "expected_ratio_analysis": [_project(r, COMPARE_RATIO_FIELDS) for r in ratios],
        },
        manifest,
    )

    # --- Fixture 05: hand-built multi-DPI group/ratio (deterministic, no RNG) ---
    settings_g = normalize_settings(
        {
            "distance_input": 50.0,
            "distance_unit": "mm",
            "movement_mode": "Vector Magnitude",
            "min_valid_trials_per_group": 2,
            "cpi_error_pass_pct": 3.0,
            "cpi_cv_pass_pct": 1.0,
            "cpi_cv_fail_pct": 3.0,
            "ratio_error_pass_pct": 2.0,
            "ratio_error_fail_pct": 5.0,
        }
    )
    # Ideal counts for 50mm (= 50/25.4 inch): dpi * inch
    inch = 50.0 / 25.4
    hand_inputs = [
        # 800 DPI ~ 1574.8 counts
        {"trial_id": 1, "target_dpi": 800, "counts_x": 1575, "counts_y": 3, "axis": "X", "direction": "X+"},
        {"trial_id": 2, "target_dpi": 800, "counts_x": 1570, "counts_y": 2, "axis": "X", "direction": "X+"},
        {"trial_id": 3, "target_dpi": 800, "counts_x": -1578, "counts_y": 4, "axis": "X", "direction": "X-"},
        {"trial_id": 4, "target_dpi": 800, "counts_x": -1572, "counts_y": 1, "axis": "X", "direction": "X-"},
        # 1600 DPI ~ 3149.6 counts
        {"trial_id": 5, "target_dpi": 1600, "counts_x": 3150, "counts_y": 5, "axis": "X", "direction": "X+"},
        {"trial_id": 6, "target_dpi": 1600, "counts_x": 3140, "counts_y": 6, "axis": "X", "direction": "X+"},
        {"trial_id": 7, "target_dpi": 1600, "counts_x": -3155, "counts_y": 3, "axis": "X", "direction": "X-"},
        {"trial_id": 8, "target_dpi": 1600, "counts_x": -3148, "counts_y": 2, "axis": "X", "direction": "X-"},
    ]
    hand_trials_full = []
    for c in hand_inputs:
        t = compute_trial(
            trial_id=c["trial_id"],
            target_dpi=c["target_dpi"],
            distance_mm=settings_g["distance_mm"],
            axis=c["axis"],
            direction=c["direction"],
            counts_x=c["counts_x"],
            counts_y=c["counts_y"],
            source="golden_fixture",
            movement_mode="Vector Magnitude",
            distance_input=settings_g["distance_input"],
            distance_unit="mm",
            tolerance_policy=settings_g,
        )
        t.pop("created_at", None)
        hand_trials_full.append(t)

    hand_groups = build_group_summaries(hand_trials_full, settings_g)
    hand_ratios = build_ratio_analysis(hand_groups, settings_g)

    _write(
        OUT_DIR / "05_hand_group_ratio.json",
        {
            "fixture_id": "05_hand_group_ratio",
            "kind": "group_and_ratio",
            "meta": {"physical_inch_at_50mm": inch},
            "settings": {
                k: settings_g[k]
                for k in (
                    "distance_input",
                    "distance_unit",
                    "distance_mm",
                    "movement_mode",
                    "min_valid_trials_per_group",
                    "cpi_error_pass_pct",
                    "cpi_error_fail_pct",
                    "cpi_cv_pass_pct",
                    "cpi_cv_fail_pct",
                    "ratio_error_pass_pct",
                    "ratio_error_fail_pct",
                    "tolerance_mode",
                )
            },
            "inputs": hand_inputs,
            "expected_trials": [_project(t, COMPARE_TRIAL_FIELDS) for t in hand_trials_full],
            "expected_group_summaries": [_project(g, COMPARE_GROUP_FIELDS) for g in hand_groups],
            "expected_ratio_analysis": [_project(r, COMPARE_RATIO_FIELDS) for r in hand_ratios],
        },
        manifest,
    )

    # --- Fixture 06: intentional divergence note (path quality NOT in measurement) ---
    _write(
        OUT_DIR / "00_fixture_policy.json",
        {
            "fixture_id": "00_fixture_policy",
            "kind": "policy",
            "parity_scope": [
                "distance_to_mm",
                "compute_trial measured_cpi / error_pct / primary_counts / vector_counts / axis_leakage",
                "build_group_summaries numeric fields and status from CPI/CV/leakage only",
                "build_ratio_analysis",
            ],
            "out_of_parity_scope": [
                "legacy classify_path_quality merging PATH_REVERSAL into trial.status",
                "legacy compute_metrics.health overall verdict",
                "Hub summary schema",
                "created_at timestamps",
            ],
            "compare_trial_fields": COMPARE_TRIAL_FIELDS,
            "compare_group_fields": COMPARE_GROUP_FIELDS,
            "compare_ratio_fields": COMPARE_RATIO_FIELDS,
            "strip_fields": list(STRIP_TRIAL_FIELDS),
        },
        manifest,
    )

    (OUT_DIR / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(manifest['fixtures'])} fixtures to {OUT_DIR}")
    for f in manifest["fixtures"]:
        print(f"  - {f}")
    return 0


def _write(path: Path, payload: dict, manifest: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest["fixtures"].append(path.name)


if __name__ == "__main__":
    raise SystemExit(main())
