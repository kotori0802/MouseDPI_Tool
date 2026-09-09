"""Path Quality Finding — trial path_quality_* fields only (not Tracking / not Accuracy)."""

from __future__ import annotations

from typing import Any

from mouse_dpi_tool.contracts.enums import FindingStatus
from mouse_dpi_tool.findings._common import active_trials_only, finding_dict, worse_status


def build_path_quality_finding(trials: list[dict[str, Any]]) -> dict[str, Any]:
    active = active_trials_only(trials)
    if not active:
        return finding_dict(
            FindingStatus.NOT_TESTED.value,
            issue_codes=["NO_ACTIVE_TRIALS"],
            metrics={
                "active_trial_count": 0,
                "pq_trial_count": 0,
                "pq_missing_count": 0,
                "pq_pass": 0,
                "pq_warn": 0,
                "pq_fail": 0,
                "pq_not_evaluated": 0,
                "pq_not_tested": 0,
            },
        )

    counts = {
        "PASS": 0,
        "WARN": 0,
        "FAIL": 0,
        "NOT_EVALUATED": 0,
        "NOT_TESTED": 0,
    }
    missing = 0
    codes: list[str] = []
    evaluated_statuses: list[str] = []

    for trial in active:
        status = trial.get("path_quality_status")
        if status is None or status == "":
            missing += 1
            continue
        status_s = str(status)
        if status_s not in counts:
            missing += 1
            continue
        counts[status_s] += 1
        for code in trial.get("path_quality_issue_codes") or []:
            if code not in codes:
                codes.append(str(code))
        if status_s in {"PASS", "WARN", "FAIL"}:
            evaluated_statuses.append(status_s)

    pq_present = sum(counts.values())
    # NOT_EVALUATED is incomplete coverage when other trials were evaluated (PASS/WARN/FAIL).
    incomplete_coverage = (
        missing > 0
        or counts["NOT_TESTED"] > 0
        or (counts["NOT_EVALUATED"] > 0 and bool(evaluated_statuses))
    )

    if pq_present == 0:
        return finding_dict(
            FindingStatus.NOT_TESTED.value,
            issue_codes=["PATH_QUALITY_NOT_RUN"],
            metrics={
                "active_trial_count": len(active),
                "pq_trial_count": 0,
                "pq_missing_count": missing,
                "pq_pass": 0,
                "pq_warn": 0,
                "pq_fail": 0,
                "pq_not_evaluated": 0,
                "pq_not_tested": 0,
            },
            notes="No Path Quality fields on active trials.",
        )

    if evaluated_statuses:
        status = worse_status(*evaluated_statuses)
        if status == FindingStatus.WARN.value:
            codes.append("PATH_QUALITY_WARN")
        elif status == FindingStatus.FAIL.value:
            codes.append("PATH_QUALITY_FAIL")
        # Partial coverage must not look like a clean PASS (FAIL still wins).
        if incomplete_coverage:
            if status == FindingStatus.PASS.value:
                status = FindingStatus.WARN.value
            if "PATH_QUALITY_COVERAGE_INCOMPLETE" not in codes:
                codes.append("PATH_QUALITY_COVERAGE_INCOMPLETE")
    elif counts["NOT_EVALUATED"] > 0:
        status = FindingStatus.NOT_EVALUATED.value
        if "NO_PATH_EVIDENCE_ABOVE_NOISE_FLOOR" not in codes and not any(
            c.startswith("PATH_") for c in codes
        ):
            codes.append("PATH_QUALITY_NOT_EVALUATED")
        if incomplete_coverage and "PATH_QUALITY_COVERAGE_INCOMPLETE" not in codes:
            codes.append("PATH_QUALITY_COVERAGE_INCOMPLETE")
    else:
        status = FindingStatus.NOT_TESTED.value
        codes.append("PATH_QUALITY_NOT_TESTED")

    return finding_dict(
        status,
        issue_codes=codes,
        metrics={
            "active_trial_count": len(active),
            "pq_trial_count": pq_present,
            "pq_missing_count": missing,
            "pq_pass": counts["PASS"],
            "pq_warn": counts["WARN"],
            "pq_fail": counts["FAIL"],
            "pq_not_evaluated": counts["NOT_EVALUATED"],
            "pq_not_tested": counts["NOT_TESTED"],
        },
    )
