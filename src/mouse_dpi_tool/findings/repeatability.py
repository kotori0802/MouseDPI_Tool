"""Repeatability Finding — group CPI CV from recomputed active groups."""

from __future__ import annotations

from typing import Any

from mouse_dpi_tool.contracts.enums import FindingStatus
from mouse_dpi_tool.findings._common import active_trials_only, finding_dict
from mouse_dpi_tool.measurement.group import build_group_summaries
from mouse_dpi_tool.measurement.settings import normalize_settings, status_from_limits


def build_repeatability_finding(
    trials: list[dict[str, Any]],
    settings: dict[str, Any],
) -> dict[str, Any]:
    policy = normalize_settings(settings)
    active = active_trials_only(trials)
    groups = build_group_summaries(active, policy)
    min_valid = int(policy["min_valid_trials_per_group"])

    if not active or not groups:
        return finding_dict(
            FindingStatus.NOT_TESTED.value,
            issue_codes=["NO_ACTIVE_TRIALS"] if not active else ["NO_GROUPS"],
            metrics={
                "active_trial_count": len(active),
                "group_count": len(groups),
                "evaluated_group_count": 0,
                "insufficient_group_count": 0,
                "max_cpi_cv_pct": None,
                "min_valid_trials_per_group": min_valid,
            },
            notes="Repeatability requires active trials forming groups.",
        )

    evaluated: list[dict[str, Any]] = []
    insufficient = 0
    for group in groups:
        if int(group.get("valid_trials") or 0) < min_valid:
            insufficient += 1
        else:
            evaluated.append(group)

    if not evaluated:
        # Evidence exists but no group meets the minimum trial count — not a FAIL.
        return finding_dict(
            FindingStatus.NOT_EVALUATED.value,
            issue_codes=["INSUFFICIENT_REPEATABILITY_EVIDENCE"],
            metrics={
                "active_trial_count": len(active),
                "group_count": len(groups),
                "evaluated_group_count": 0,
                "insufficient_group_count": insufficient,
                "max_cpi_cv_pct": None,
                "min_valid_trials_per_group": min_valid,
            },
            notes=(
                f"No group reached min_valid_trials_per_group={min_valid}; "
                "repeatability is not evaluated (not treated as FAIL)."
            ),
        )

    cvs = [float(g.get("cpi_cv_pct") or 0.0) for g in evaluated]
    max_cv = max(cvs) if cvs else 0.0
    status = status_from_limits(max_cv, policy["cpi_cv_pass_pct"], policy["cpi_cv_fail_pct"])
    codes: list[str] = []
    if status == FindingStatus.WARN.value:
        codes.append("REPEATABILITY_WARN")
    elif status == FindingStatus.FAIL.value:
        codes.append("REPEATABILITY_FAIL")
    if insufficient:
        codes.append("SOME_GROUPS_INSUFFICIENT_TRIALS")
        # Mixed evidence: keep evaluated CV status, but never report clean PASS.
        if status == FindingStatus.PASS.value:
            status = FindingStatus.WARN.value

    return finding_dict(
        status,
        issue_codes=codes,
        metrics={
            "active_trial_count": len(active),
            "group_count": len(groups),
            "evaluated_group_count": len(evaluated),
            "insufficient_group_count": insufficient,
            "max_cpi_cv_pct": round(max_cv, 4),
            "min_valid_trials_per_group": min_valid,
        },
    )
