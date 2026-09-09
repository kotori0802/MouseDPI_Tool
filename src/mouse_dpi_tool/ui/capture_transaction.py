"""Capture transaction phases — UI lifecycle barrier (not Session evidence).

Debounce may remain as UX bounce protection; phase rules are the correctness
barrier against cross-run F5 / Stop leaks.
"""

from __future__ import annotations

from enum import Enum


class CaptureTxnPhase(str, Enum):
    IDLE = "idle"
    ARMING = "arming"
    RUNNING = "running"
    STOPPING = "stopping"
    DRAINING = "draining"
    REVIEW_READY = "review_ready"
    ERROR = "error"


def resolve_capture_txn_phase(
    *,
    engine_state: str | None,
    worker_op: str | None,
    worker_running: bool,
    can_admit: bool,
    can_discard: bool,
    arming: bool,
) -> CaptureTxnPhase:
    """Derive the operator-visible transaction phase from live UI/controller state."""
    if arming or (worker_running and worker_op == "start"):
        return CaptureTxnPhase.ARMING
    if worker_running and worker_op == "stop":
        # Source stop + dispatcher drain share one worker op today.
        return CaptureTxnPhase.STOPPING
    if worker_running and worker_op == "cancel":
        return CaptureTxnPhase.STOPPING
    state = (engine_state or "idle").lower()
    if state == "running":
        return CaptureTxnPhase.RUNNING
    # Valid pending: Admit and Discard are both available — prefer REVIEW_READY.
    if state == "stopped" and can_admit:
        return CaptureTxnPhase.REVIEW_READY
    if state == "error" or (can_discard and not can_admit):
        return CaptureTxnPhase.ERROR
    if state in {"stopped", "cancelled"}:
        return CaptureTxnPhase.IDLE
    return CaptureTxnPhase.IDLE


def f5_action_for_phase(phase: CaptureTxnPhase, *, can_admit: bool) -> str:
    """Return the single legal F5 action: start | stop | admit_next | ignore."""
    if phase is CaptureTxnPhase.RUNNING:
        return "stop"
    if phase in {CaptureTxnPhase.ARMING, CaptureTxnPhase.STOPPING, CaptureTxnPhase.DRAINING}:
        return "ignore"
    if phase is CaptureTxnPhase.REVIEW_READY and can_admit:
        return "admit_next"
    if phase in {CaptureTxnPhase.IDLE, CaptureTxnPhase.ERROR}:
        # ERROR / incomplete: do not auto-start; require discard or explicit Start when idle.
        if phase is CaptureTxnPhase.ERROR:
            return "ignore"
        return "start"
    return "ignore"


class CaptureActionBarMode(str, Enum):
    """Presentation stack page for Capture actions.

    Derived from CaptureTxnPhase + VM eligibility — not a second state machine.
    Switch QStackedLayout only when this mode changes (not every 33 ms tick).
    """

    IDLE = "idle"
    ARMING = "arming"
    RUNNING = "running"
    STOPPING = "stopping"
    REVIEW_ADMITTABLE = "review_admittable"
    REVIEW_DISCARD_ONLY = "review_discard_only"


def resolve_action_bar_mode(
    phase: CaptureTxnPhase,
    *,
    can_admit: bool,
    can_discard: bool,
) -> CaptureActionBarMode:
    """Map txn phase + admit/discard flags to a stable ActionBar presentation mode.

    Eligibility flags only refine REVIEW_READY / ERROR — they must not override IDLE/RUNNING.
    """
    if phase is CaptureTxnPhase.IDLE:
        return CaptureActionBarMode.IDLE
    if phase is CaptureTxnPhase.ARMING:
        return CaptureActionBarMode.ARMING
    if phase is CaptureTxnPhase.RUNNING:
        return CaptureActionBarMode.RUNNING
    if phase in {CaptureTxnPhase.STOPPING, CaptureTxnPhase.DRAINING}:
        return CaptureActionBarMode.STOPPING
    if phase is CaptureTxnPhase.REVIEW_READY:
        if can_admit:
            return CaptureActionBarMode.REVIEW_ADMITTABLE
        if can_discard:
            return CaptureActionBarMode.REVIEW_DISCARD_ONLY
        # Review without admit/discard eligibility — show idle Start affordance.
        return CaptureActionBarMode.IDLE
    if phase is CaptureTxnPhase.ERROR:
        if can_discard:
            return CaptureActionBarMode.REVIEW_DISCARD_ONLY
        return CaptureActionBarMode.IDLE
    return CaptureActionBarMode.IDLE


def visible_actions_for_mode(mode: CaptureActionBarMode) -> frozenset[str]:
    """Primary/secondary action ids for Phase 1 contract tests (no Discard & Retry)."""
    if mode is CaptureActionBarMode.IDLE:
        return frozenset({"start"})
    if mode is CaptureActionBarMode.ARMING:
        return frozenset({"starting_disabled"})
    if mode is CaptureActionBarMode.RUNNING:
        return frozenset({"stop", "cancel"})
    if mode is CaptureActionBarMode.STOPPING:
        return frozenset({"processing_disabled"})
    if mode is CaptureActionBarMode.REVIEW_ADMITTABLE:
        return frozenset({"admit", "discard"})
    if mode is CaptureActionBarMode.REVIEW_DISCARD_ONLY:
        return frozenset({"discard"})
    return frozenset()
