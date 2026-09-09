"""Findings layer — independent dimensions, no overall health verdict in V1."""

from __future__ import annotations

from typing import Any

from mouse_dpi_tool.contracts.enums import FINDING_DIMENSIONS, V1_RESERVED_FINDINGS, FindingStatus
from mouse_dpi_tool.findings.builder import (
    build_findings,
    build_findings_from_mapping,
    canonicalize_trials_for_findings,
)

__all__ = [
    "FINDING_DIMENSIONS",
    "V1_RESERVED_FINDINGS",
    "FindingStatus",
    "build_findings",
    "build_findings_from_mapping",
    "canonicalize_trials_for_findings",
    "empty_findings_shell",
]


def empty_findings_shell() -> dict[str, Any]:
    """Canonical empty findings object (no overall PASS/WARN/FAIL)."""
    findings: dict[str, Any] = {}
    for name in FINDING_DIMENSIONS:
        if name == "manual_observations":
            findings[name] = []
            continue
        status = V1_RESERVED_FINDINGS.get(name, FindingStatus.NOT_TESTED)
        findings[name] = {
            "status": status.value if isinstance(status, FindingStatus) else status,
            "issue_codes": [],
            "metrics": {},
            "notes": "",
        }
    return findings
