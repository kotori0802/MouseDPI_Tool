"""Findings Builder — orchestrates independent dimensions from canonical active trials.

Findings-0B/0C: never trust stored group/ratio rows or exported Trial quantitative
derived fields. Recompute via Measurement Domain from primitive evidence.
"""

from __future__ import annotations

from typing import Any, Mapping

from mouse_dpi_tool.contracts.enums import V1_RESERVED_FINDINGS, FindingStatus
from mouse_dpi_tool.findings._common import finding_dict
from mouse_dpi_tool.findings.accuracy import build_accuracy_finding
from mouse_dpi_tool.findings.manual import build_manual_observations
from mouse_dpi_tool.findings.path_quality import build_path_quality_finding
from mouse_dpi_tool.findings.ratio import build_ratio_finding
from mouse_dpi_tool.findings.repeatability import build_repeatability_finding
from mouse_dpi_tool.measurement.settings import normalize_settings
from mouse_dpi_tool.measurement.trial import recompute_trial_from_evidence


def _extract_active_trials(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Active quantitative evidence only — ignore rejected/deleted arrays."""
    return list(payload.get("trials") or [])


def _extract_settings(payload: Mapping[str, Any]) -> dict[str, Any]:
    return normalize_settings(dict(payload.get("settings") or {}))


def _extract_manual(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    findings = payload.get("findings") or {}
    if isinstance(findings, dict) and "manual_observations" in findings:
        return list(findings.get("manual_observations") or [])
    return list(payload.get("manual_observations") or [])


def canonicalize_trials_for_findings(
    trials: list[dict[str, Any]],
    settings: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Recompute quantitative Trial fields under the current measurement policy."""
    policy = normalize_settings(dict(settings))
    return [recompute_trial_from_evidence(trial, policy) for trial in trials]


def build_findings(
    *,
    trials: list[dict[str, Any]],
    settings: Mapping[str, Any],
    manual_observations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build findings from primitive Trial evidence + normalized settings."""
    policy = normalize_settings(dict(settings))
    canonical = canonicalize_trials_for_findings(trials, policy)
    findings: dict[str, Any] = {
        "accuracy": build_accuracy_finding(canonical, policy),
        "repeatability": build_repeatability_finding(canonical, policy),
        "ratio": build_ratio_finding(canonical, policy),
        "path_quality": build_path_quality_finding(canonical),
        "manual_observations": build_manual_observations(manual_observations),
    }
    for name, status in V1_RESERVED_FINDINGS.items():
        findings[name] = finding_dict(
            status.value if isinstance(status, FindingStatus) else str(status),
            notes="Reserved in V1; Extreme DPI / scaling heuristics not implemented.",
        )
    return findings


def build_findings_from_mapping(session: Mapping[str, Any]) -> dict[str, Any]:
    """Findings from a Session Mapping.

    Stored ``group_summaries`` / ``ratio_analysis`` and exported Trial derived
    quantitative fields are not trusted. Primitive counts + settings are
    recomputed through the Measurement Domain first.
    """
    settings = _extract_settings(session)
    return build_findings(
        trials=_extract_active_trials(session),
        settings=settings,
        manual_observations=_extract_manual(session),
    )
