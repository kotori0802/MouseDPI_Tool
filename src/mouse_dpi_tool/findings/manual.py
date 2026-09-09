"""Manual Observations — independent from quantitative Findings."""

from __future__ import annotations

import copy
from typing import Any


def build_manual_observations(
    observations: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Return a deep-copied list of manual observation rows (no quantitative merge)."""
    out: list[dict[str, Any]] = []
    for row in observations or []:
        item = {
            "id": str(row["id"]),
            "label": str(row["label"]),
            "status": str(row.get("status") or "NOT_TESTED"),
        }
        if "notes" in row and row["notes"] is not None:
            item["notes"] = str(row["notes"])
        out.append(item)
    return out


def clone_manual_observations(observations: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return copy.deepcopy(list(observations or []))
