"""Accuracy Finding — CPI error from active trials only (not Path Quality / Manual)."""

from __future__ import annotations

from typing import Any

from mouse_dpi_tool.contracts.enums import FindingStatus
from mouse_dpi_tool.findings._common import active_trials_only, finding_dict
from mouse_dpi_tool.measurement.group import build_group_summaries
from mouse_dpi_tool.measurement.settings import normalize_settings, status_from_limits


def build_accuracy_finding(
    trials: list[dict[str, Any]],
    settings: dict[str, Any],
) -> dict[str, Any]:
    policy = normalize_settings(settings)
    active = active_trials_only(trials)
    groups = build_group_summaries(active, policy)

    if not active:
        return finding_dict(
            FindingStatus.NOT_TESTED.value,
            issue_codes=["NO_ACTIVE_TRIALS"],
            metrics={"active_trial_count": 0, "group_count": 0, "max_abs_error_pct": None},
            notes="Accuracy requires active quantitative trials.",
        )

    errors = [abs(float(t.get("error_pct", 0.0))) for t in active]
    max_abs_error = max(errors) if errors else 0.0
    status = status_from_limits(
        max_abs_error,
        policy["cpi_error_pass_pct"],
        policy["cpi_error_fail_pct"],
    )
    codes: list[str] = []
    if status == FindingStatus.WARN.value:
        codes.append("ACCURACY_WARN")
    elif status == FindingStatus.FAIL.value:
        codes.append("ACCURACY_FAIL")

    # Group error tallies are diagnostic only; status comes from trial CPI errors.
    g_pass = g_warn = g_fail = 0
    for g in groups:
        g_status = status_from_limits(
            float(g.get("max_abs_error_pct") or 0.0),
            policy["cpi_error_pass_pct"],
            policy["cpi_error_fail_pct"],
        )
        if g_status == "PASS":
            g_pass += 1
        elif g_status == "WARN":
            g_warn += 1
        else:
            g_fail += 1

    return finding_dict(
        status,
        issue_codes=codes,
        metrics={
            "active_trial_count": len(active),
            "group_count": len(groups),
            "max_abs_error_pct": round(max_abs_error, 4),
            "groups_pass": g_pass,
            "groups_warn": g_warn,
            "groups_fail": g_fail,
        },
    )
