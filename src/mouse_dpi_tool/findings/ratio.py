"""Ratio Finding — configured-DPI step ratios (not firmware-scaling conclusions)."""

from __future__ import annotations

from typing import Any

from mouse_dpi_tool.contracts.enums import FindingStatus
from mouse_dpi_tool.findings._common import active_trials_only, finding_dict, worse_status
from mouse_dpi_tool.measurement.group import build_group_summaries
from mouse_dpi_tool.measurement.ratio import build_ratio_analysis
from mouse_dpi_tool.measurement.settings import normalize_settings


def build_ratio_finding(
    trials: list[dict[str, Any]],
    settings: dict[str, Any],
) -> dict[str, Any]:
    policy = normalize_settings(settings)
    active = active_trials_only(trials)
    groups = build_group_summaries(active, policy)
    ratios = build_ratio_analysis(groups, policy)

    if not active:
        return finding_dict(
            FindingStatus.NOT_TESTED.value,
            issue_codes=["NO_ACTIVE_TRIALS"],
            metrics={
                "active_trial_count": 0,
                "ratio_pair_count": 0,
                "max_abs_ratio_error_pct": None,
                "ratios_pass": 0,
                "ratios_warn": 0,
                "ratios_fail": 0,
            },
        )

    if not ratios:
        return finding_dict(
            FindingStatus.NOT_TESTED.value,
            issue_codes=["NO_RATIO_PAIRS"],
            metrics={
                "active_trial_count": len(active),
                "ratio_pair_count": 0,
                "max_abs_ratio_error_pct": None,
                "ratios_pass": 0,
                "ratios_warn": 0,
                "ratios_fail": 0,
            },
            notes="Ratio Finding needs at least two configured-DPI groups on the same axis/direction/distance.",
        )

    statuses = [str(r.get("status") or "PASS") for r in ratios]
    status = worse_status(*statuses)
    codes: list[str] = []
    if status == FindingStatus.WARN.value:
        codes.append("RATIO_WARN")
    elif status == FindingStatus.FAIL.value:
        codes.append("RATIO_FAIL")

    r_pass = sum(1 for s in statuses if s == "PASS")
    r_warn = sum(1 for s in statuses if s == "WARN")
    r_fail = sum(1 for s in statuses if s == "FAIL")
    max_abs = max(abs(float(r.get("ratio_error_pct") or 0.0)) for r in ratios)

    return finding_dict(
        status,
        issue_codes=codes,
        metrics={
            "active_trial_count": len(active),
            "ratio_pair_count": len(ratios),
            "max_abs_ratio_error_pct": round(max_abs, 4),
            "ratios_pass": r_pass,
            "ratios_warn": r_warn,
            "ratios_fail": r_fail,
        },
        notes="Configured-DPI step ratio only; not a native-capability or firmware-scaling verdict.",
    )
