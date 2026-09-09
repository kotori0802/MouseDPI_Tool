"""Deterministic synthetic trials matching legacy make_synthetic_trials (seed=42)."""

from __future__ import annotations

import random

from mouse_dpi_tool.measurement.trial import compute_trial


def make_synthetic_trials(dpi_steps, distance_mm: float = 100.0, trials_per_group: int = 5) -> list[dict]:
    trials = []
    trial_id = 1
    inch = distance_mm / 25.4
    rng = random.Random(42)

    for dpi in dpi_steps:
        for direction in ["X+", "X-"]:
            for _ in range(trials_per_group):
                ideal = dpi * inch
                noise = rng.uniform(-0.008, 0.008)
                counts = int(round(ideal * (1 + noise)))
                leakage = int(round(abs(counts) * rng.uniform(0.000, 0.008)))
                signed = counts if direction == "X+" else -counts
                trial = compute_trial(
                    trial_id=trial_id,
                    configured_dpi=dpi,
                    distance_mm=distance_mm,
                    axis="X",
                    direction=direction,
                    counts_x=signed,
                    counts_y=leakage,
                    source="self_test",
                    movement_mode="Vector Magnitude",
                    distance_input=distance_mm,
                    distance_unit="mm",
                )
                trials.append(trial)
                trial_id += 1

    return trials
