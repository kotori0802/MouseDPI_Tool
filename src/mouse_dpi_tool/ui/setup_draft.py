"""SetupDraft — UI/application-owned draft vs committed Session truth.

Phase 1 contract + Phase 1.5 product-model correction.
Session schema unchanged. Capture must never read drafts.
Ordinary Apply commits only OPERATOR_EDITABLE_FIELDS (hide+preserve metadata).
Recovery may restore a full committed snapshot.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace
from enum import Enum
from typing import Any, Mapping, Protocol

from mouse_dpi_tool.contracts.measurement_method import (
    is_canonical_measurement_method,
)
from mouse_dpi_tool.measurement.accuracy_profile import (
    DEFAULT_ACCURACY_PROFILE,
    canonicalize_accuracy_profile,
    is_operator_accuracy_profile,
    resolve_operator_profile_from_settings,
)
from mouse_dpi_tool.measurement.distance import (
    canonicalize_distance_unit,
    distance_to_mm,
)

# Keep in sync with ui.controllers movement mode codes (avoid importing AppController).
MOVEMENT_MODE_FIXTURE_VECTOR = "Vector Magnitude"
MOVEMENT_MODE_DIRECTIONAL_AXIS = "Axis Projection"

# Structural fields that Session freezes once any trial evidence exists.
STRUCTURAL_DRAFT_FIELDS: frozenset[str] = frozenset(
    {"distance_input", "distance_unit", "movement_mode"}
)
ACCURACY_DRAFT_FIELDS: frozenset[str] = frozenset({"accuracy_profile"})

# Phase 1.5 — ordinary Setup operator surface (Apply / Unsaved / Revert).
# Hidden snapshot fields (surface, provenance, uncertainty, dut.notes, …) remain
# on SetupDraft for load/debug/recovery but are never ordinary-Apply targets.
OPERATOR_EDITABLE_FIELDS: frozenset[str] = frozenset(
    {
        "vendor",
        "model",
        "method",
        "distance_input",
        "distance_unit",
        "movement_mode",
        "accuracy_profile",
        "ctx_notes",
    }
)

ALLOWED_MOVEMENT_MODES: frozenset[str] = frozenset(
    {MOVEMENT_MODE_FIXTURE_VECTOR, MOVEMENT_MODE_DIRECTIONAL_AXIS}
)


class ApplyStatus(str, Enum):
    SUCCESS = "success"
    PREFLIGHT_REJECTED = "preflight_rejected"
    COMMIT_FAILED_RESTORED = "commit_failed_restored"
    COMMIT_FAILED_PARTIAL = "commit_failed_partial"


@dataclass(frozen=True)
class SetupDraft:
    """Operator-editable Setup state before Apply. Not Session evidence."""

    vendor: str = ""
    model: str = ""
    notes: str = ""
    method: str = "unknown"
    distance_input: float = 100.0
    distance_unit: str = "mm"
    movement_mode: str = MOVEMENT_MODE_FIXTURE_VECTOR
    accuracy_profile: str = DEFAULT_ACCURACY_PROFILE
    surface: str = ""
    fixture_type: str = ""
    ctx_notes: str = ""
    dpi_configuration_source: str = "unknown"
    control_software_state: str = "unknown"
    control_software_name: str = ""
    control_software_version: str = ""
    profile_note: str = ""
    measurement_system_uncertainty_note: str = ""
    reference_uncertainty_pct: float | None = None


# Committed snapshot uses the same shape (Session truth projection).
SetupCommittedSnapshot = SetupDraft


@dataclass(frozen=True)
class UnitBPreview:
    """Draft-only distance preview (Unit B). Not committed Physical distance."""

    entered_value: float
    entered_unit: str
    interpreted_mm: float

    def entered_line(self) -> str:
        return f"Entered value: {self.entered_value:g} {self.entered_unit}"

    def interpreted_line(self) -> str:
        return f"Interpreted distance: {self.interpreted_mm:g} mm"

    def will_apply_line(self) -> str:
        return f"Will apply as: {self.interpreted_mm:g} mm"


@dataclass(frozen=True)
class PreflightIssue:
    field: str
    reason: str


@dataclass(frozen=True)
class ApplyResult:
    status: ApplyStatus
    requested_fields: tuple[str, ...] = ()
    issues: tuple[PreflightIssue, ...] = ()
    error: str | None = None
    noop: bool = False
    mutators_called: tuple[str, ...] = ()


@dataclass(frozen=True)
class StaleReconcileResult:
    draft: SetupDraft
    restored_fields: tuple[str, ...]
    notice: str | None  # info/warning — not Session error


class SetupApplyController(Protocol):
    """Minimal surface used by apply_setup_draft (AppController satisfies this)."""

    @property
    def measurement_config_locked(self) -> bool: ...

    @property
    def accuracy_criterion_locked(self) -> bool: ...

    @property
    def session(self) -> Any: ...

    def update_dut(self, *, vendor: str = "", model: str = "", notes: str = "") -> None: ...

    def update_measurement_context(self, **kwargs: Any) -> None: ...

    def update_distance(self, *, distance_input: float, unit: str) -> None: ...

    def set_movement_mode(self, mode: str) -> None: ...

    def set_accuracy_profile(self, mode: str) -> Any: ...


def _norm_unit(unit: str) -> str:
    return canonicalize_distance_unit(unit)


def _norm_mode(mode: str) -> str:
    """Canonicalize representation only — do not invent a valid mode."""
    return str(mode or "").strip()


def _norm_profile(profile: str) -> str:
    """Canonicalize aliases (e.g. FIELD_FORMAL→STRICT); do not invent a profile.

    Unknown codes remain as returned by canonicalize_accuracy_profile so preflight
    can reject them. load_committed_snapshot uses resolve_operator_profile_from_settings
    which always yields an operator profile from Session settings.
    """
    return canonicalize_accuracy_profile(profile)


def _float_eq(a: float, b: float, *, eps: float = 1e-9) -> bool:
    return abs(float(a) - float(b)) <= eps


def _opt_float_eq(a: float | None, b: float | None) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return _float_eq(a, b)


def normalize_draft(draft: SetupDraft) -> SetupDraft:
    ref = draft.reference_uncertainty_pct
    if ref is not None and float(ref) <= 0.0:
        ref = None
    return replace(
        draft,
        vendor=str(draft.vendor or ""),
        model=str(draft.model or ""),
        notes=str(draft.notes or ""),
        method=str(draft.method or "unknown"),
        distance_input=float(draft.distance_input),
        distance_unit=_norm_unit(draft.distance_unit),
        movement_mode=_norm_mode(draft.movement_mode),
        accuracy_profile=_norm_profile(draft.accuracy_profile),
        surface=str(draft.surface or ""),
        fixture_type=str(draft.fixture_type or ""),
        ctx_notes=str(draft.ctx_notes or ""),
        dpi_configuration_source=str(draft.dpi_configuration_source or "unknown"),
        control_software_state=str(draft.control_software_state or "unknown"),
        control_software_name=str(draft.control_software_name or ""),
        control_software_version=str(draft.control_software_version or ""),
        profile_note=str(draft.profile_note or ""),
        measurement_system_uncertainty_note=str(
            draft.measurement_system_uncertainty_note or ""
        ),
        reference_uncertainty_pct=ref,
    )


def load_committed_snapshot(controller: SetupApplyController) -> SetupCommittedSnapshot:
    """Project Session + accuracy profile into a committed snapshot (truth)."""
    session = controller.session
    dut = session.dut
    ctx = session.measurement_context
    settings = session.settings
    ref = ctx.get("reference_uncertainty_pct")
    ref_f: float | None
    if ref is None or ref == "":
        ref_f = None
    else:
        ref_f = float(ref)
        if ref_f <= 0.0:
            ref_f = None
    return normalize_draft(
        SetupDraft(
            vendor=str(dut.get("vendor") or ""),
            model=str(dut.get("model") or ""),
            notes=str(dut.get("notes") or ""),
            method=str(ctx.get("method") or "unknown"),
            distance_input=float(settings.get("distance_input", 100.0)),
            distance_unit=str(settings.get("distance_unit", "mm")),
            movement_mode=str(
                settings.get("movement_mode", MOVEMENT_MODE_FIXTURE_VECTOR)
            ),
            accuracy_profile=resolve_operator_profile_from_settings(settings),
            surface=str(ctx.get("surface") or ""),
            fixture_type=str(ctx.get("fixture_type") or ""),
            ctx_notes=str(ctx.get("notes") or ""),
            dpi_configuration_source=str(
                ctx.get("dpi_configuration_source") or "unknown"
            ),
            control_software_state=str(ctx.get("control_software_state") or "unknown"),
            control_software_name=str(ctx.get("control_software_name") or ""),
            control_software_version=str(ctx.get("control_software_version") or ""),
            profile_note=str(ctx.get("profile_note") or ""),
            measurement_system_uncertainty_note=str(
                ctx.get("measurement_system_uncertainty_note") or ""
            ),
            reference_uncertainty_pct=ref_f,
        )
    )


def unit_b_preview(draft: SetupDraft) -> UnitBPreview:
    d = normalize_draft(draft)
    mm = float(distance_to_mm(d.distance_input, d.distance_unit))
    return UnitBPreview(
        entered_value=float(d.distance_input),
        entered_unit=str(d.distance_unit),
        interpreted_mm=mm,
    )


def diff_all(draft: SetupDraft, committed: SetupCommittedSnapshot) -> tuple[str, ...]:
    """Full snapshot diff (debug / recovery). Includes hidden metadata fields."""
    a = normalize_draft(draft)
    b = normalize_draft(committed)
    changed: list[str] = []
    for f in fields(SetupDraft):
        name = f.name
        va = getattr(a, name)
        vb = getattr(b, name)
        if name in {"distance_input"}:
            if not _float_eq(float(va), float(vb)):
                changed.append(name)
        elif name == "reference_uncertainty_pct":
            if not _opt_float_eq(va, vb):
                changed.append(name)
        elif va != vb:
            changed.append(name)
    return tuple(changed)


def diff_setup(draft: SetupDraft, committed: SetupCommittedSnapshot) -> tuple[str, ...]:
    """Alias of ``diff_all`` (compat). Prefer ``diff_all`` / ``diff_operator_editable``."""
    return diff_all(draft, committed)


def diff_operator_editable(
    draft: SetupDraft, committed: SetupCommittedSnapshot
) -> tuple[str, ...]:
    """Diff restricted to OPERATOR_EDITABLE_FIELDS (ordinary Setup Apply set)."""
    return tuple(
        name
        for name in diff_all(draft, committed)
        if name in OPERATOR_EDITABLE_FIELDS
    )


def is_operator_dirty(draft: SetupDraft, committed: SetupCommittedSnapshot) -> bool:
    """Setup Unsaved / Apply enabled / Revert enabled — operator fields only."""
    return bool(diff_operator_editable(draft, committed))


def is_dirty(draft: SetupDraft, committed: SetupCommittedSnapshot) -> bool:
    """Phase 1.5+: Setup UX dirty == operator dirty (hidden-only ≠ unsaved)."""
    return is_operator_dirty(draft, committed)


def has_trial_evidence(controller: SetupApplyController) -> bool:
    m = controller.session.metrics()
    return bool(
        m.get("active_trial_count")
        or m.get("rejected_trial_count")
        or m.get("deleted_trial_count")
    )


def structural_settings_locked(controller: SetupApplyController) -> bool:
    """True when distance/movement_mode must not change (mirror Session rules)."""
    return bool(controller.measurement_config_locked) or has_trial_evidence(controller)


def preflight_setup_apply(
    draft: SetupDraft,
    committed: SetupCommittedSnapshot,
    controller: SetupApplyController,
) -> tuple[bool, tuple[PreflightIssue, ...], tuple[str, ...]]:
    """Validate operator-editable changes before any Session mutation.

    Hidden-only diffs are ignored (not requested). Mirrors lock / method rules.
    """
    draft_n = normalize_draft(draft)
    committed_n = normalize_draft(committed)
    requested = diff_operator_editable(draft_n, committed_n)
    if not requested:
        return True, (), ()

    issues: list[PreflightIssue] = []
    struct_locked = structural_settings_locked(controller)
    acc_locked = bool(controller.accuracy_criterion_locked) or bool(
        controller.measurement_config_locked
    )

    for field in requested:
        if field in STRUCTURAL_DRAFT_FIELDS and struct_locked:
            issues.append(
                PreflightIssue(
                    field=field,
                    reason=(
                        "structural measurement settings are locked for this session "
                        "(pending capture or trial evidence exists)"
                    ),
                )
            )
        if field in ACCURACY_DRAFT_FIELDS and acc_locked:
            issues.append(
                PreflightIssue(
                    field=field,
                    reason=(
                        "accuracy criterion is locked after measurement evidence "
                        "or while capture configuration is frozen"
                    ),
                )
            )
        if field == "method" and not is_canonical_measurement_method(draft_n.method):
            issues.append(
                PreflightIssue(
                    field="method",
                    reason=f"measurement method is not a supported value: {draft_n.method!r}",
                )
            )
        if field == "movement_mode" and draft_n.movement_mode not in ALLOWED_MOVEMENT_MODES:
            issues.append(
                PreflightIssue(
                    field="movement_mode",
                    reason=f"unsupported movement_mode: {draft_n.movement_mode!r}",
                )
            )
        if field == "accuracy_profile" and not is_operator_accuracy_profile(
            draft_n.accuracy_profile
        ):
            issues.append(
                PreflightIssue(
                    field="accuracy_profile",
                    reason=(
                        f"unsupported accuracy profile: {draft_n.accuracy_profile!r}; "
                        "expected an operator FIELD_* profile"
                    ),
                )
            )
        if field == "distance_input" and float(draft_n.distance_input) <= 0:
            issues.append(
                PreflightIssue(
                    field="distance_input",
                    reason="distance must be greater than zero",
                )
            )

    # Deduplicate issues by (field, reason)
    uniq: list[PreflightIssue] = []
    seen: set[tuple[str, str]] = set()
    for issue in issues:
        key = (issue.field, issue.reason)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(issue)
    return (not uniq), tuple(uniq), requested


def _full_context_kwargs_for_restore(draft: SetupDraft) -> dict[str, Any]:
    """Full measurement_context write for recovery/rollback only — not ordinary Apply."""
    patch: dict[str, Any] = {
        "surface": draft.surface,
        "fixture_type": draft.fixture_type,
        "method": draft.method,
        "notes": draft.ctx_notes,
        "dpi_configuration_source": draft.dpi_configuration_source,
        "control_software_state": draft.control_software_state,
        "control_software_name": draft.control_software_name,
        "control_software_version": draft.control_software_version,
        "profile_note": draft.profile_note,
        "measurement_system_uncertainty_note": draft.measurement_system_uncertainty_note,
    }
    if draft.reference_uncertainty_pct is not None:
        patch["reference_uncertainty_pct"] = float(draft.reference_uncertainty_pct)
    else:
        patch["reference_uncertainty_pct"] = None
    return patch


def _operator_context_patch(
    draft: SetupDraft, requested: tuple[str, ...]
) -> dict[str, Any]:
    """Fine-grained context keys for ordinary Apply (editable fields only)."""
    patch: dict[str, Any] = {}
    if "method" in requested:
        patch["method"] = draft.method
    if "ctx_notes" in requested:
        patch["notes"] = draft.ctx_notes
    return patch


def _restore_committed(
    controller: SetupApplyController, committed: SetupCommittedSnapshot
) -> None:
    """Best-effort compensating write of full committed snapshot (recovery only)."""
    c = normalize_draft(committed)
    # Prefer unlocking path: only restore what APIs allow.
    if not structural_settings_locked(controller):
        if c.movement_mode in ALLOWED_MOVEMENT_MODES:
            controller.set_movement_mode(c.movement_mode)
        controller.update_distance(
            distance_input=float(c.distance_input),
            unit=str(c.distance_unit),
        )
    if not controller.accuracy_criterion_locked and not controller.measurement_config_locked:
        if is_operator_accuracy_profile(c.accuracy_profile):
            controller.set_accuracy_profile(c.accuracy_profile)
    controller.update_measurement_context(**_full_context_kwargs_for_restore(c))
    controller.update_dut(vendor=c.vendor, model=c.model, notes=c.notes)


def apply_setup_draft(
    controller: SetupApplyController,
    draft: SetupDraft,
    *,
    committed: SetupCommittedSnapshot | None = None,
) -> ApplyResult:
    """Preflight then commit. Never partially applies requested changes by design.

    If commit raises after preflight passed, attempt best-effort restore of the
    pre-Apply committed snapshot. Restoration incomplete is a distinct status.
    """
    committed_snap = (
        normalize_draft(committed)
        if committed is not None
        else load_committed_snapshot(controller)
    )
    draft_n = normalize_draft(draft)
    ok, issues, requested = preflight_setup_apply(draft_n, committed_snap, controller)
    if not requested:
        return ApplyResult(
            status=ApplyStatus.SUCCESS,
            requested_fields=(),
            noop=True,
            mutators_called=(),
        )
    if not ok:
        return ApplyResult(
            status=ApplyStatus.PREFLIGHT_REJECTED,
            requested_fields=requested,
            issues=issues,
            noop=False,
            mutators_called=(),
        )

    # Selective commit: OPERATOR_EDITABLE_FIELDS only (Amendment 1–4).
    called: list[str] = []
    try:
        need_struct = bool(set(requested) & STRUCTURAL_DRAFT_FIELDS)
        need_acc = "accuracy_profile" in requested
        ctx_patch = _operator_context_patch(draft_n, requested)
        need_ctx = bool(ctx_patch)
        need_dut = bool(set(requested) & {"vendor", "model"})

        if need_struct:
            if "movement_mode" in requested:
                controller.set_movement_mode(draft_n.movement_mode)
                called.append("set_movement_mode")
            if "distance_input" in requested or "distance_unit" in requested:
                controller.update_distance(
                    distance_input=float(draft_n.distance_input),
                    unit=str(draft_n.distance_unit),
                )
                called.append("update_distance")
        if need_acc:
            controller.set_accuracy_profile(draft_n.accuracy_profile)
            called.append("set_accuracy_profile")
        if need_ctx:
            controller.update_measurement_context(**ctx_patch)
            called.append("update_measurement_context")
        if need_dut:
            # update_dut is not a patch API — always send full triple; preserve
            # committed dut.notes (hidden from ordinary Setup).
            vendor = (
                draft_n.vendor if "vendor" in requested else committed_snap.vendor
            )
            model = draft_n.model if "model" in requested else committed_snap.model
            notes = committed_snap.notes
            controller.update_dut(vendor=vendor, model=model, notes=notes)
            called.append("update_dut")
    except Exception as exc:  # noqa: BLE001 — Apply boundary
        try:
            _restore_committed(controller, committed_snap)
            after = load_committed_snapshot(controller)
            if after == committed_snap:
                return ApplyResult(
                    status=ApplyStatus.COMMIT_FAILED_RESTORED,
                    requested_fields=requested,
                    error=str(exc),
                    mutators_called=tuple(called),
                )
            return ApplyResult(
                status=ApplyStatus.COMMIT_FAILED_PARTIAL,
                requested_fields=requested,
                error=(
                    f"{exc}; restoration incomplete — refresh Session truth; "
                    "some fields may have been partially applied"
                ),
                mutators_called=tuple(called),
            )
        except Exception as restore_exc:  # noqa: BLE001
            return ApplyResult(
                status=ApplyStatus.COMMIT_FAILED_PARTIAL,
                requested_fields=requested,
                error=(
                    f"{exc}; restore also failed ({restore_exc}) — "
                    "refresh Session truth; possible partial commit"
                ),
                mutators_called=tuple(called),
            )

    return ApplyResult(
        status=ApplyStatus.SUCCESS,
        requested_fields=requested,
        noop=False,
        mutators_called=tuple(called),
    )


def reconcile_stale_locked_draft(
    draft: SetupDraft,
    committed: SetupCommittedSnapshot,
    controller: SetupApplyController,
) -> StaleReconcileResult:
    """Option A: restore illegal structural/accuracy draft fields to committed.

    Notice is info/warning presentation — not a Session error.
    DUT / notes and other still-legal dirty fields are preserved.
    """
    draft_n = normalize_draft(draft)
    committed_n = normalize_draft(committed)
    restored: list[str] = []
    updates: dict[str, Any] = {}

    if structural_settings_locked(controller):
        for name in STRUCTURAL_DRAFT_FIELDS:
            if getattr(draft_n, name) != getattr(committed_n, name):
                if name == "distance_input":
                    if not _float_eq(
                        float(getattr(draft_n, name)),
                        float(getattr(committed_n, name)),
                    ):
                        updates[name] = getattr(committed_n, name)
                        restored.append(name)
                else:
                    updates[name] = getattr(committed_n, name)
                    restored.append(name)

    acc_locked = bool(controller.accuracy_criterion_locked) or bool(
        controller.measurement_config_locked
    )
    if acc_locked and draft_n.accuracy_profile != committed_n.accuracy_profile:
        updates["accuracy_profile"] = committed_n.accuracy_profile
        restored.append("accuracy_profile")

    if not restored:
        return StaleReconcileResult(draft=draft_n, restored_fields=(), notice=None)

    new_draft = replace(draft_n, **updates)
    notice = (
        "Measurement settings were restored because this session now contains "
        "trial evidence (or a pending capture freeze)."
    )
    return StaleReconcileResult(
        draft=new_draft,
        restored_fields=tuple(restored),
        notice=notice,
    )


def revert_draft_to_committed(committed: SetupCommittedSnapshot) -> SetupDraft:
    """Discard changes: draft ← committed (not factory defaults)."""
    return normalize_draft(committed)


def draft_as_dict(draft: SetupDraft) -> dict[str, Any]:
    return asdict(normalize_draft(draft))
