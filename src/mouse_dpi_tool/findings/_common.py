"""Shared Findings helpers — no duplicated CPI/group/ratio formulas."""

from __future__ import annotations

from typing import Any

from mouse_dpi_tool.contracts.enums import FindingStatus

_STATUS_RANK = {
    FindingStatus.PASS.value: 0,
    FindingStatus.WARN.value: 1,
    FindingStatus.FAIL.value: 2,
}


def finding_dict(
    status: str,
    *,
    issue_codes: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "status": status,
        "issue_codes": list(issue_codes or []),
        "metrics": dict(metrics or {}),
        "notes": notes,
    }


def worse_status(*statuses: str) -> str:
    ranked = [s for s in statuses if s in _STATUS_RANK]
    if not ranked:
        return FindingStatus.NOT_TESTED.value
    return max(ranked, key=lambda s: _STATUS_RANK[s])


def active_trials_only(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        t
        for t in trials
        if t.get("accepted") and not t.get("rejected") and not t.get("deleted")
    ]
