"""Semantic evidence invariants for MOUSE_DPI_TOOL_SESSION_V1."""

from __future__ import annotations

from typing import Any


def _path(prefix: str, *parts: Any) -> str:
    bits = [prefix, *[str(p) for p in parts]]
    return ".".join(bits)


def _check_flags(
    trial: dict[str, Any],
    *,
    path: str,
    accepted: bool,
    rejected: bool,
    deleted: bool,
    errors: list[str],
) -> None:
    if bool(trial.get("accepted")) is not accepted:
        errors.append(f"{path}.accepted must be {accepted}")
    if bool(trial.get("rejected")) is not rejected:
        errors.append(f"{path}.rejected must be {rejected}")
    if bool(trial.get("deleted")) is not deleted:
        errors.append(f"{path}.deleted must be {deleted}")


def _validate_capture_aggregates(trial: dict[str, Any], *, path: str, errors: list[str]) -> None:
    evidence = trial.get("capture_evidence")
    if not isinstance(evidence, dict):
        return
    per_device = evidence.get("per_device_counts") or {}
    if not isinstance(per_device, dict):
        errors.append(f"{path}.capture_evidence.per_device_counts must be an object")
        return

    sum_events = 0
    sum_dx = 0
    sum_dy = 0
    for device_id, stats in per_device.items():
        if not isinstance(stats, dict):
            errors.append(f"{path}.capture_evidence.per_device_counts.{device_id} must be an object")
            continue
        sum_events += int(stats.get("event_count", 0))
        sum_dx += int(stats.get("dx", 0))
        sum_dy += int(stats.get("dy", 0))

    published = int(evidence.get("published_count", 0))
    if sum_events != published:
        errors.append(
            f"{path}.capture_evidence: sum(per_device_counts.event_count)={sum_events} "
            f"!= published_count={published}"
        )
    counts_x = int(trial.get("counts_x", 0))
    counts_y = int(trial.get("counts_y", 0))
    if sum_dx != counts_x:
        errors.append(
            f"{path}.capture_evidence: sum(per_device_counts.dx)={sum_dx} != counts_x={counts_x}"
        )
    if sum_dy != counts_y:
        errors.append(
            f"{path}.capture_evidence: sum(per_device_counts.dy)={sum_dy} != counts_y={counts_y}"
        )


def validate_session_semantics(payload: dict[str, Any]) -> list[str]:
    """Return human-readable semantic errors (empty list means OK)."""
    errors: list[str] = []

    trials = list(payload.get("trials") or [])
    rejected = list(payload.get("rejected_trials") or [])
    deleted = list(payload.get("deleted_trials") or [])
    groups = list(payload.get("group_summaries") or [])
    ratios = list(payload.get("ratio_analysis") or [])
    metrics = dict(payload.get("metrics") or {})

    for i, trial in enumerate(trials):
        path = _path("trials", i)
        _check_flags(trial, path=path, accepted=True, rejected=False, deleted=False, errors=errors)
        if "status" in trial:
            errors.append(f"{path}: canonical Session trial must not emit 'status' (use measurement_status)")
        evidence = trial.get("capture_evidence")
        source = str(trial.get("source") or "")
        if source == "raw_input" and not isinstance(evidence, dict):
            errors.append(f"{path}: source=raw_input active trial requires capture_evidence")
        if isinstance(evidence, dict):
            if evidence.get("valid_complete_capture") is not True:
                errors.append(f"{path}.capture_evidence.valid_complete_capture must be true for active trials")
            if evidence.get("complete") is not True:
                errors.append(f"{path}.capture_evidence.complete must be true for active trials")
            if evidence.get("integrity_ok") is not True:
                errors.append(f"{path}.capture_evidence.integrity_ok must be true for active trials")
            _validate_capture_aggregates(trial, path=path, errors=errors)

    for i, trial in enumerate(rejected):
        path = _path("rejected_trials", i)
        _check_flags(trial, path=path, accepted=False, rejected=True, deleted=False, errors=errors)
        if "status" in trial:
            errors.append(f"{path}: canonical Session trial must not emit 'status' (use measurement_status)")
        if isinstance(trial.get("capture_evidence"), dict):
            _validate_capture_aggregates(trial, path=path, errors=errors)

    for i, trial in enumerate(deleted):
        path = _path("deleted_trials", i)
        _check_flags(trial, path=path, accepted=False, rejected=False, deleted=True, errors=errors)
        if "status" in trial:
            errors.append(f"{path}: canonical Session trial must not emit 'status' (use measurement_status)")
        if isinstance(trial.get("capture_evidence"), dict):
            _validate_capture_aggregates(trial, path=path, errors=errors)

    seen: dict[int, str] = {}
    for bucket_name, bucket in (
        ("trials", trials),
        ("rejected_trials", rejected),
        ("deleted_trials", deleted),
    ):
        for i, trial in enumerate(bucket):
            tid = int(trial.get("trial_id", -1))
            path = _path(bucket_name, i, "trial_id")
            if tid in seen:
                errors.append(f"{path}={tid} duplicates {seen[tid]}")
            else:
                seen[tid] = f"{bucket_name}[{i}]"

    expected_metrics = {
        "active_trial_count": len(trials),
        "rejected_trial_count": len(rejected),
        "deleted_trial_count": len(deleted),
        "group_count": len(groups),
        "ratio_pair_count": len(ratios),
    }
    for key, expected in expected_metrics.items():
        actual = metrics.get(key)
        if actual != expected:
            errors.append(f"metrics.{key}={actual!r} != {expected} (array length)")

    return errors
