"""Capture aggregate provenance for Session / Trial evidence."""

from __future__ import annotations

from typing import Any, Protocol


class CaptureEvidenceSource(Protocol):
    @property
    def state(self) -> Any: ...

    @property
    def complete(self) -> bool: ...

    @property
    def integrity_ok(self) -> bool: ...

    @property
    def is_valid_complete_capture(self) -> bool: ...

    @property
    def published_count(self) -> int: ...

    @property
    def net_counts_x(self) -> int: ...

    @property
    def net_counts_y(self) -> int: ...

    @property
    def device_ids(self) -> Any: ...

    @property
    def per_device_counts(self) -> dict[str, dict[str, int]]: ...

    @property
    def last_error(self) -> str | None: ...

    @property
    def subscriber_errors(self) -> Any: ...

    @property
    def status_callback_errors(self) -> Any: ...


def build_capture_evidence(capture: CaptureEvidenceSource) -> dict[str, Any]:
    """Serialize aggregate capture provenance (not raw MovementSample streams)."""
    state = capture.state
    state_value = state.value if hasattr(state, "value") else str(state)
    issue_codes: list[str] = []
    if not capture.complete:
        issue_codes.append("CAPTURE_INCOMPLETE")
    if not capture.integrity_ok:
        issue_codes.append("CAPTURE_INTEGRITY_FAILED")
    if not capture.is_valid_complete_capture:
        issue_codes.append("CAPTURE_NOT_VALID_COMPLETE")

    per_device: dict[str, dict[str, int]] = {}
    for device_id, stats in (capture.per_device_counts or {}).items():
        per_device[str(device_id)] = {
            "dx": int(stats.get("dx", 0)),
            "dy": int(stats.get("dy", 0)),
            "event_count": int(stats.get("event_count", 0)),
        }

    evidence: dict[str, Any] = {
        "state": state_value,
        "complete": bool(capture.complete),
        "integrity_ok": bool(capture.integrity_ok),
        "valid_complete_capture": bool(capture.is_valid_complete_capture),
        "published_count": int(capture.published_count),
        "device_ids": [str(d) for d in capture.device_ids],
        "per_device_counts": per_device,
        "last_error": capture.last_error,
        "subscriber_errors": [str(e) for e in capture.subscriber_errors],
        # Presentation diagnostics — retained but not used as integrity failure.
        "status_callback_errors": [str(e) for e in getattr(capture, "status_callback_errors", ())],
        "issue_codes": issue_codes,
    }
    generation = getattr(capture, "generation", None)
    if generation is not None:
        try:
            evidence["capture_generation"] = int(generation)
        except (TypeError, ValueError):
            pass
    stale = getattr(capture, "stale_sample_count", None)
    if stale is not None:
        try:
            evidence["stale_sample_count"] = int(stale)
        except (TypeError, ValueError):
            pass
    return evidence
