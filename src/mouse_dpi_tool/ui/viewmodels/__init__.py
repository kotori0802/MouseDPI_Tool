"""ViewModels — presentation adapters over immutable domain snapshots.

Never compute CPI / group / ratio / Finding status. Only format display fields.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping

from mouse_dpi_tool.measurement.direction_evidence import evaluate_direction_match
from mouse_dpi_tool.ui.direction import axis_for_direction, canonicalize_direction
from mouse_dpi_tool.ui.i18n import I18n


@dataclass(frozen=True)
class FindingCardVM:
    dimension: str
    canonical_status: str
    title: str
    status_label: str
    issue_labels: tuple[str, ...] = ()
    metrics: Mapping[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass(frozen=True)
class ResultsPageVM:
    session_id: str
    finding_cards: tuple[FindingCardVM, ...]
    active_trial_count: int
    group_count: int
    ratio_pair_count: int
    evidence_fingerprint: Mapping[str, Any]


@dataclass(frozen=True)
class CapturePageVM:
    state: str
    display_state: str
    last_status: str
    configured_dpi: int
    direction: str
    axis: str
    distance_mm: float
    distance_input: float
    distance_unit: str
    movement_mode: str
    net_counts_x: int
    net_counts_y: int
    primary_counts: int
    published_count: int
    device_ids: tuple[str, ...]
    device_count: int
    is_valid_complete_capture: bool
    integrity_ok: bool
    complete: bool
    can_admit: bool
    busy: bool
    last_error: str | None
    path_quality_status: str | None
    direction_match: bool | None
    direction_issue_code: str | None
    expected_direction: str
    observed_direction: str | None
    path_points: tuple[tuple[float, float], ...] = ()
    config_locked: bool = False
    can_discard: bool = False


def _display_state(
    *,
    busy_op: str | None,
    snap_state: str,
    valid: bool,
    direction_match: bool | None,
    direction_issue: str | None,
    fixture_vector: bool = False,
) -> str:
    if busy_op == "starting":
        return "starting"
    if busy_op == "stopping":
        return "stopping"
    if busy_op == "cancelling":
        return "cancelling"
    if busy_op == "discarding":
        return "discarding"
    if snap_state == "running":
        return "capturing"
    if snap_state == "cancelled":
        return "cancelled"
    if snap_state == "error":
        return "error"
    if snap_state == "stopped":
        if fixture_vector:
            if valid and direction_match is True:
                return "valid_stopped"
            if direction_issue == "ZERO_PRIMARY_MOVEMENT":
                return "zero_primary"
            if not valid:
                return "error"
            return "stopped"
        if valid and direction_match is True:
            return "valid_stopped"
        if direction_issue == "DIRECTION_MISMATCH":
            return "direction_mismatch"
        if direction_issue == "ZERO_PRIMARY_MOVEMENT":
            return "zero_primary"
        if not valid:
            return "error"
        return "stopped"
    return "idle"


def build_capture_viewmodel(
    *,
    capture_snapshot: Any | None,
    i18n: I18n,
    last_status: str,
    configured_dpi: int,
    busy: bool,
    busy_op: str | None = None,
    admitted: bool = False,
    direction: str = "X+",
    distance_mm: float = 100.0,
    distance_input: float = 100.0,
    distance_unit: str = "mm",
    movement_mode: str = "Vector Magnitude",
    path_quality: Mapping[str, Any] | None = None,
    path_points: tuple[tuple[float, float], ...] = (),
    config_locked: bool = False,
) -> CapturePageVM:
    _ = i18n
    code = canonicalize_direction(direction)
    axis = axis_for_direction(code)
    fixture_vector = str(movement_mode) == "Vector Magnitude"
    if capture_snapshot is None:
        return CapturePageVM(
            state="idle",
            display_state="idle",
            last_status=last_status,
            configured_dpi=int(configured_dpi),
            direction=code,
            axis=axis,
            distance_mm=float(distance_mm),
            distance_input=float(distance_input),
            distance_unit=str(distance_unit),
            movement_mode=str(movement_mode),
            net_counts_x=0,
            net_counts_y=0,
            primary_counts=0,
            published_count=0,
            device_ids=(),
            device_count=0,
            is_valid_complete_capture=False,
            integrity_ok=True,
            complete=False,
            can_admit=False,
            busy=bool(busy),
            last_error=None,
            path_quality_status=None,
            direction_match=None,
            direction_issue_code=None,
            expected_direction=code,
            observed_direction=None,
            path_points=path_points,
            config_locked=False,
            can_discard=False,
        )

    state = str(capture_snapshot.state)
    net_x = int(capture_snapshot.net_counts_x)
    net_y = int(capture_snapshot.net_counts_y)
    published = int(capture_snapshot.published_count)
    valid = bool(capture_snapshot.is_valid_complete_capture)
    vector_counts = int(round(math.sqrt(net_x * net_x + net_y * net_y)))
    if fixture_vector:
        primary = vector_counts
    else:
        primary = abs(net_y) if axis == "Y" else abs(net_x)

    direction_match: bool | None = None
    direction_issue: str | None = None
    observed: str | None = None
    # Evaluate once capture has produced movement evidence or has finished.
    if published > 0 or state in {"stopped", "error", "cancelled"}:
        if fixture_vector:
            if vector_counts > 0:
                direction_match = True
                direction_issue = None
            else:
                direction_match = False
                direction_issue = "ZERO_PRIMARY_MOVEMENT"
            observed = None
        else:
            result = evaluate_direction_match(code, net_x, net_y)
            direction_match = bool(result.matches)
            direction_issue = None if result.matches else str(result.reason)
            observed = result.inferred_direction

    can_admit = (
        valid
        and not busy
        and not admitted
        and direction_match is True
        and int(configured_dpi) >= 1
        and primary > 0
    )
    can_discard = not busy and not admitted and state in {"stopped", "error"}
    pq_status = None
    if path_quality is not None:
        pq_status = str(path_quality.get("status") or "") or None

    display = _display_state(
        busy_op=busy_op,
        snap_state=state,
        valid=valid,
        direction_match=direction_match,
        direction_issue=direction_issue,
        fixture_vector=fixture_vector,
    )
    return CapturePageVM(
        state=state,
        display_state=display,
        last_status=last_status,
        configured_dpi=int(configured_dpi),
        direction=code,
        axis=axis,
        distance_mm=float(distance_mm),
        distance_input=float(distance_input),
        distance_unit=str(distance_unit),
        movement_mode=str(movement_mode),
        net_counts_x=net_x,
        net_counts_y=net_y,
        primary_counts=int(primary),
        published_count=published,
        device_ids=tuple(capture_snapshot.device_ids),
        device_count=len(capture_snapshot.device_ids),
        is_valid_complete_capture=valid,
        integrity_ok=bool(capture_snapshot.integrity_ok),
        complete=bool(capture_snapshot.complete),
        can_admit=can_admit,
        busy=bool(busy),
        last_error=capture_snapshot.last_error,
        path_quality_status=pq_status,
        direction_match=direction_match,
        direction_issue_code=direction_issue,
        expected_direction=code,
        observed_direction=observed,
        path_points=path_points,
        config_locked=bool(config_locked),
        can_discard=bool(can_discard),
    )


def build_results_viewmodel(session_dict: Mapping[str, Any], i18n: I18n) -> ResultsPageVM:
    findings = dict(session_dict.get("findings") or {})
    cards: list[FindingCardVM] = []
    for dim in (
        "accuracy",
        "repeatability",
        "ratio",
        "path_quality",
        "linearity",
        "scaling_evidence",
        "native_capability",
    ):
        row = dict(findings.get(dim) or {})
        status = str(row.get("status") or "NOT_TESTED")
        cards.append(
            FindingCardVM(
                dimension=dim,
                canonical_status=status,
                title=i18n.finding(dim),
                status_label=i18n.status(status),
                issue_labels=tuple(i18n.issue(c) for c in (row.get("issue_codes") or [])),
                metrics=dict(row.get("metrics") or {}),
                notes=str(row.get("notes") or ""),
            )
        )
    metrics = dict(session_dict.get("metrics") or {})
    fingerprint = {
        "session_id": session_dict.get("session_id"),
        "trials": session_dict.get("trials"),
        "group_summaries": session_dict.get("group_summaries"),
        "ratio_analysis": session_dict.get("ratio_analysis"),
        "findings": session_dict.get("findings"),
        "settings": session_dict.get("settings"),
        "metrics": metrics,
    }
    return ResultsPageVM(
        session_id=str(session_dict.get("session_id") or ""),
        finding_cards=tuple(cards),
        active_trial_count=int(metrics.get("active_trial_count") or 0),
        group_count=int(metrics.get("group_count") or 0),
        ratio_pair_count=int(metrics.get("ratio_pair_count") or 0),
        evidence_fingerprint=fingerprint,
    )
