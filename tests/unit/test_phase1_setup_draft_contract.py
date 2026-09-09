"""Phase 1 — SetupDraft / Apply preflight / ActionBarMode contract (no UI chrome)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from mouse_dpi_tool.ui.capture_transaction import (
    CaptureActionBarMode,
    CaptureTxnPhase,
    f5_action_for_phase,
    resolve_action_bar_mode,
    resolve_capture_txn_phase,
    visible_actions_for_mode,
)
from mouse_dpi_tool.ui.controllers import (
    MOVEMENT_MODE_DIRECTIONAL_AXIS,
    MOVEMENT_MODE_FIXTURE_VECTOR,
    AppController,
)
from mouse_dpi_tool.ui.setup_draft import (
    ApplyStatus,
    OPERATOR_EDITABLE_FIELDS,
    SetupDraft,
    apply_setup_draft,
    diff_all,
    diff_operator_editable,
    diff_setup,
    is_dirty,
    is_operator_dirty,
    load_committed_snapshot,
    normalize_draft,
    preflight_setup_apply,
    reconcile_stale_locked_draft,
    revert_draft_to_committed,
    unit_b_preview,
)


@pytest.fixture
def controller():
    return AppController(preferences={"theme": "dark", "locale": "en-US"})


def test_load_committed_and_dirty_diff(controller):
    committed = load_committed_snapshot(controller)
    draft = replace(committed, vendor="Acme", distance_input=2.0, distance_unit="inch")
    assert is_dirty(draft, committed)
    assert is_operator_dirty(draft, committed)
    changed = diff_operator_editable(draft, committed)
    assert "vendor" in changed
    assert "distance_input" in changed
    assert "distance_unit" in changed
    assert not is_dirty(committed, committed)


def test_hidden_only_diff_is_not_operator_dirty(controller):
    committed = load_committed_snapshot(controller)
    draft = replace(
        committed,
        surface="glass",
        control_software_version="9.9",
        reference_uncertainty_pct=3.0,
        notes="dut-side",
    )
    assert "surface" in diff_all(draft, committed)
    assert "notes" in diff_all(draft, committed)
    assert diff_operator_editable(draft, committed) == ()
    assert is_operator_dirty(draft, committed) is False
    assert is_dirty(draft, committed) is False
    # Compat alias still returns full snapshot diff.
    assert "surface" in diff_setup(draft, committed)


def test_unit_b_preview_wording_not_recorded_travel(controller):
    draft = SetupDraft(distance_input=100.0, distance_unit="inch")
    prev = unit_b_preview(draft)
    assert prev.interpreted_mm == pytest.approx(2540.0)
    assert "Entered value:" in prev.entered_line()
    assert "100" in prev.entered_line()
    assert "Interpreted distance:" in prev.interpreted_line()
    assert "2540" in prev.interpreted_line()
    assert "Will apply as:" in prev.will_apply_line()
    assert "Recorded travel" not in prev.entered_line()
    assert "Recorded travel" not in prev.interpreted_line()


def test_apply_noop_when_draft_equals_committed(controller):
    committed = load_committed_snapshot(controller)
    calls: list[str] = []

    class _Probe:
        measurement_config_locked = False
        accuracy_criterion_locked = False
        session = controller.session

        def update_dut(self, **kwargs):
            calls.append("update_dut")
            return controller.update_dut(**kwargs)

        def update_measurement_context(self, **kwargs):
            calls.append("update_measurement_context")
            return controller.update_measurement_context(**kwargs)

        def update_distance(self, **kwargs):
            calls.append("update_distance")
            return controller.update_distance(**kwargs)

        def set_movement_mode(self, mode):
            calls.append("set_movement_mode")
            return controller.set_movement_mode(mode)

        def set_accuracy_profile(self, mode):
            calls.append("set_accuracy_profile")
            return controller.set_accuracy_profile(mode)

    result = apply_setup_draft(_Probe(), committed, committed=committed)
    assert result.status is ApplyStatus.SUCCESS
    assert result.noop is True
    assert result.mutators_called == ()
    assert calls == []


def test_invalid_movement_mode_preflight_rejected_zero_mutate(controller):
    committed = load_committed_snapshot(controller)
    # Bypass normalize silent path: construct draft then normalize keeps invalid strip-only.
    dirty = replace(committed, movement_mode="NotARealMode")
    result = apply_setup_draft(controller, dirty, committed=committed)
    assert result.status is ApplyStatus.PREFLIGHT_REJECTED
    assert any(i.field == "movement_mode" for i in result.issues)
    assert result.mutators_called == ()
    assert load_committed_snapshot(controller).movement_mode == committed.movement_mode
    assert normalize_draft(dirty).movement_mode == "NotARealMode"


def test_invalid_accuracy_profile_preflight_rejected(controller):
    committed = load_committed_snapshot(controller)
    dirty = replace(committed, accuracy_profile="ENGINEERING_CUSTOM")
    result = apply_setup_draft(controller, dirty, committed=committed)
    assert result.status is ApplyStatus.PREFLIGHT_REJECTED
    assert any(i.field == "accuracy_profile" for i in result.issues)
    assert result.mutators_called == ()
    assert load_committed_snapshot(controller).accuracy_profile == committed.accuracy_profile


def test_ordinary_apply_ignores_reference_uncertainty_clear(controller):
    """Phase 1.5: uncertainty is hidden — ordinary Apply must not clear it."""
    controller.update_measurement_context(reference_uncertainty_pct=1.5)
    committed = load_committed_snapshot(controller)
    assert committed.reference_uncertainty_pct == pytest.approx(1.5)
    draft = replace(committed, reference_uncertainty_pct=None)
    result = apply_setup_draft(controller, draft, committed=committed)
    assert result.status is ApplyStatus.SUCCESS
    assert result.noop is True
    after = load_committed_snapshot(controller)
    assert after.reference_uncertainty_pct == pytest.approx(1.5)


def test_vendor_only_apply_preserves_hidden_metadata(controller):
    controller.update_dut(vendor="Old", model="M1", notes="keep-dut-notes")
    controller.update_measurement_context(
        surface="reference hard pad",
        control_software_version="2026.8",
        reference_uncertainty_pct=1.0,
        fixture_type="contact A",
    )
    committed = load_committed_snapshot(controller)
    # Draft pretends hidden fields were wiped (UI gone / defaults) — Apply must ignore.
    draft = replace(
        committed,
        vendor="ExampleVendor",
        surface="",
        fixture_type="",
        control_software_version="",
        reference_uncertainty_pct=None,
        notes="",
        dpi_configuration_source="unknown",
    )
    result = apply_setup_draft(controller, draft, committed=committed)
    assert result.status is ApplyStatus.SUCCESS
    assert result.requested_fields == ("vendor",)
    after = load_committed_snapshot(controller)
    assert after.vendor == "ExampleVendor"
    assert after.model == "M1"
    assert after.notes == "keep-dut-notes"
    assert after.surface == "reference hard pad"
    assert after.fixture_type == "contact A"
    assert after.control_software_version == "2026.8"
    assert after.reference_uncertainty_pct == pytest.approx(1.0)


def test_reference_uncertainty_clear_restored_on_failed_commit(controller):
    controller.update_measurement_context(method="fixture", reference_uncertainty_pct=2.25)
    committed = load_committed_snapshot(controller)

    class _BoomAfterRef:
        measurement_config_locked = False
        accuracy_criterion_locked = False

        def __init__(self, ctl: AppController) -> None:
            self._ctl = ctl
            self.session = ctl.session
            self._blow_up = True

        def set_movement_mode(self, mode):
            return self._ctl.set_movement_mode(mode)

        def update_distance(self, **kwargs):
            return self._ctl.update_distance(**kwargs)

        def set_accuracy_profile(self, mode):
            return self._ctl.set_accuracy_profile(mode)

        def update_measurement_context(self, **kwargs):
            self._ctl.update_measurement_context(**kwargs)
            if self._blow_up:
                self._blow_up = False
                raise RuntimeError("fail after context write")

        def update_dut(self, **kwargs):
            return self._ctl.update_dut(**kwargs)

    # Use editable ctx_notes so ordinary Apply actually writes context.
    draft = replace(committed, ctx_notes="deviation")
    result = apply_setup_draft(_BoomAfterRef(controller), draft, committed=committed)
    assert result.status is ApplyStatus.COMMIT_FAILED_RESTORED
    after = load_committed_snapshot(controller)
    assert after.reference_uncertainty_pct == pytest.approx(2.25)
    assert after.ctx_notes == committed.ctx_notes
    assert after.surface == committed.surface


def test_apply_commits_all_or_nothing_happy_path(controller):
    controller.update_measurement_context(surface="keep-surface")
    committed = load_committed_snapshot(controller)
    draft = replace(
        committed,
        vendor="V",
        model="M",
        method="fixture",
        distance_input=2.0,
        distance_unit="inch",
        movement_mode=MOVEMENT_MODE_DIRECTIONAL_AXIS,
        accuracy_profile="FIELD_MEDIUM",
        surface="cloth",  # hidden — must not commit
        ctx_notes="ok deviation",
    )
    result = apply_setup_draft(controller, draft, committed=committed)
    assert result.status is ApplyStatus.SUCCESS
    assert result.noop is False
    assert "set_movement_mode" in result.mutators_called
    assert "update_distance" in result.mutators_called
    after = load_committed_snapshot(controller)
    assert after.vendor == "V"
    assert after.model == "M"
    assert after.method == "fixture"
    assert after.distance_input == pytest.approx(2.0)
    assert after.distance_unit == "inch"
    assert after.movement_mode == MOVEMENT_MODE_DIRECTIONAL_AXIS
    assert controller.session.settings["distance_mm"] == pytest.approx(50.8)
    assert after.accuracy_profile == "FIELD_MEDIUM"
    assert after.surface == "keep-surface"
    assert after.ctx_notes == "ok deviation"
    assert set(result.requested_fields) <= OPERATOR_EDITABLE_FIELDS


def test_preflight_rejects_structural_when_evidence_exists_zero_mutate(controller):
    controller.update_distance(distance_input=100.0, unit="mm")
    controller.session.add_synthetic_trial(configured_dpi=800, counts_x=1600, counts_y=0)
    committed = load_committed_snapshot(controller)
    draft = replace(
        committed,
        movement_mode=MOVEMENT_MODE_DIRECTIONAL_AXIS,
        vendor="ShouldNotCommit",
    )
    ok, issues, requested = preflight_setup_apply(draft, committed, controller)
    assert ok is False
    assert any(i.field == "movement_mode" for i in issues)
    result = apply_setup_draft(controller, draft, committed=committed)
    assert result.status is ApplyStatus.PREFLIGHT_REJECTED
    assert result.mutators_called == ()
    after = load_committed_snapshot(controller)
    assert after.movement_mode == MOVEMENT_MODE_FIXTURE_VECTOR
    assert after.vendor == committed.vendor
    assert "ShouldNotCommit" not in after.vendor


def test_dut_only_apply_allowed_when_structural_locked(controller):
    controller.update_distance(distance_input=100.0, unit="mm")
    controller.session.add_synthetic_trial(configured_dpi=800, counts_x=1600, counts_y=0)
    committed = load_committed_snapshot(controller)
    draft = replace(committed, vendor="OnlyDut")
    result = apply_setup_draft(controller, draft, committed=committed)
    assert result.status is ApplyStatus.SUCCESS
    assert result.mutators_called == ("update_dut",)
    assert load_committed_snapshot(controller).vendor == "OnlyDut"


def test_preflight_rejects_invalid_method_zero_mutate(controller):
    committed = load_committed_snapshot(controller)
    draft = replace(committed, method="unknown123", vendor="X")
    result = apply_setup_draft(controller, draft, committed=committed)
    assert result.status is ApplyStatus.PREFLIGHT_REJECTED
    assert any(i.field == "method" for i in result.issues)
    assert load_committed_snapshot(controller).vendor == ""


def test_stale_locked_draft_option_a_restores_structural_keeps_dut(controller):
    controller.update_distance(distance_input=100.0, unit="mm")
    committed_before = load_committed_snapshot(controller)
    dirty = replace(
        committed_before,
        movement_mode=MOVEMENT_MODE_DIRECTIONAL_AXIS,
        distance_input=2.0,
        distance_unit="inch",
        vendor="KeepMe",
        notes="still dirty ok",
    )
    controller.session.add_synthetic_trial(configured_dpi=800, counts_x=1600, counts_y=0)
    committed_after = load_committed_snapshot(controller)
    recon = reconcile_stale_locked_draft(dirty, committed_after, controller)
    assert "movement_mode" in recon.restored_fields
    assert recon.draft.movement_mode == committed_after.movement_mode
    assert recon.draft.distance_unit == committed_after.distance_unit
    assert recon.draft.vendor == "KeepMe"
    assert recon.draft.notes == "still dirty ok"
    assert recon.notice is not None
    assert "restored" in recon.notice.lower()
    assert "ERROR" not in recon.notice


def test_revert_changes_means_draft_from_committed_not_defaults(controller):
    controller.update_dut(vendor="Acme", model="X1", notes="")
    committed = load_committed_snapshot(controller)
    dirty = replace(committed, vendor="Other", distance_input=50.0)
    assert is_dirty(dirty, committed)
    reverted = revert_draft_to_committed(committed)
    assert reverted.vendor == "Acme"
    assert reverted.model == "X1"
    assert reverted.distance_input == pytest.approx(committed.distance_input)


def test_commit_failed_restored_status():
    class _MutateThenBoomOnce:
        """Fails once on context write; restore path must succeed afterwards."""

        measurement_config_locked = False
        accuracy_criterion_locked = False

        def __init__(self, ctl: AppController) -> None:
            self._ctl = ctl
            self.session = ctl.session
            self._blow_up = True

        def set_movement_mode(self, mode):
            return self._ctl.set_movement_mode(mode)

        def update_distance(self, **kwargs):
            return self._ctl.update_distance(**kwargs)

        def set_accuracy_profile(self, mode):
            return self._ctl.set_accuracy_profile(mode)

        def update_measurement_context(self, **kwargs):
            self._ctl.update_measurement_context(**kwargs)
            if self._blow_up:
                self._blow_up = False
                raise RuntimeError("fail after context write")

        def update_dut(self, **kwargs):
            return self._ctl.update_dut(**kwargs)

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    ctl.update_measurement_context(surface="pad", notes="orig")
    committed = load_committed_snapshot(ctl)
    draft = replace(committed, ctx_notes="glass-dev", method="fixture")
    result = apply_setup_draft(_MutateThenBoomOnce(ctl), draft, committed=committed)
    assert result.status is ApplyStatus.COMMIT_FAILED_RESTORED
    assert result.error
    after = load_committed_snapshot(ctl)
    assert after.surface == "pad"
    assert after.ctx_notes == "orig"


def test_commit_failed_partial_when_restore_also_fails():
    class _WriteThenBlockRestore:
        measurement_config_locked = False
        accuracy_criterion_locked = False

        def __init__(self, ctl: AppController) -> None:
            self._ctl = ctl
            self.session = ctl.session
            self._phase = "commit"

        def set_movement_mode(self, mode):
            return self._ctl.set_movement_mode(mode)

        def update_distance(self, **kwargs):
            return self._ctl.update_distance(**kwargs)

        def set_accuracy_profile(self, mode):
            return self._ctl.set_accuracy_profile(mode)

        def update_measurement_context(self, **kwargs):
            if self._phase == "restore":
                raise RuntimeError("restore blocked before write")
            self._ctl.update_measurement_context(**kwargs)
            self._phase = "restore"
            raise RuntimeError("fail after context write")

        def update_dut(self, **kwargs):
            return self._ctl.update_dut(**kwargs)

    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    ctl.update_measurement_context(surface="pad", notes="orig")
    committed = load_committed_snapshot(ctl)
    draft = replace(committed, ctx_notes="partial-notes", method="fixture")
    result = apply_setup_draft(_WriteThenBlockRestore(ctl), draft, committed=committed)
    assert result.status is ApplyStatus.COMMIT_FAILED_PARTIAL
    assert result.error
    # Context write landed; restore blocked before compensating write.
    assert load_committed_snapshot(ctl).ctx_notes == "partial-notes"
    # Hidden surface must still be untouched by the fine-grained ordinary patch.
    assert load_committed_snapshot(ctl).surface == "pad"

def test_dirty_draft_does_not_affect_capture_committed_values(controller):
    """Amendment 5A: Capture must use committed Session, never draft."""
    controller.set_movement_mode(MOVEMENT_MODE_FIXTURE_VECTOR)
    controller.update_distance(distance_input=100.0, unit="mm")
    committed = load_committed_snapshot(controller)
    draft = replace(
        committed,
        movement_mode=MOVEMENT_MODE_DIRECTIONAL_AXIS,
        distance_input=2.0,
        distance_unit="inch",
    )
    assert is_dirty(draft, committed)
    vm = controller.capture_viewmodel()
    assert vm.movement_mode == MOVEMENT_MODE_FIXTURE_VECTOR
    assert vm.distance_input == pytest.approx(100.0)
    assert vm.distance_unit == "mm"
    assert vm.distance_mm == pytest.approx(100.0)
    assert controller.session.settings["movement_mode"] == MOVEMENT_MODE_FIXTURE_VECTOR


def test_load_committed_snapshot_does_not_mutate_dirty_draft_fields(controller):
    """Pure load/reconcile: re-reading committed must not alter an in-memory dirty draft.

    This does NOT exercise SetupPage.refresh / retranslate / theme (Phase 2 UI wiring).
    """
    committed = load_committed_snapshot(controller)
    dirty = replace(
        committed, vendor="DirtyVendor", movement_mode=MOVEMENT_MODE_DIRECTIONAL_AXIS
    )
    again = load_committed_snapshot(controller)
    assert dirty.vendor == "DirtyVendor"
    assert is_dirty(dirty, again)
    recon = reconcile_stale_locked_draft(dirty, again, controller)
    assert recon.restored_fields == ()
    assert recon.draft.vendor == "DirtyVendor"
    assert recon.draft.movement_mode == MOVEMENT_MODE_DIRECTIONAL_AXIS


def test_action_bar_mode_from_phase_and_flags():
    assert (
        resolve_action_bar_mode(CaptureTxnPhase.IDLE, can_admit=False, can_discard=False)
        is CaptureActionBarMode.IDLE
    )
    assert visible_actions_for_mode(CaptureActionBarMode.IDLE) == frozenset({"start"})

    assert (
        resolve_action_bar_mode(CaptureTxnPhase.ARMING, can_admit=False, can_discard=False)
        is CaptureActionBarMode.ARMING
    )
    assert (
        resolve_action_bar_mode(CaptureTxnPhase.RUNNING, can_admit=False, can_discard=False)
        is CaptureActionBarMode.RUNNING
    )
    assert visible_actions_for_mode(CaptureActionBarMode.RUNNING) == frozenset(
        {"stop", "cancel"}
    )

    assert (
        resolve_action_bar_mode(CaptureTxnPhase.STOPPING, can_admit=False, can_discard=False)
        is CaptureActionBarMode.STOPPING
    )
    assert (
        resolve_action_bar_mode(CaptureTxnPhase.DRAINING, can_admit=False, can_discard=False)
        is CaptureActionBarMode.STOPPING
    )

    assert (
        resolve_action_bar_mode(
            CaptureTxnPhase.REVIEW_READY, can_admit=True, can_discard=True
        )
        is CaptureActionBarMode.REVIEW_ADMITTABLE
    )
    assert visible_actions_for_mode(CaptureActionBarMode.REVIEW_ADMITTABLE) == frozenset(
        {"admit", "discard"}
    )
    assert "reject" not in visible_actions_for_mode(CaptureActionBarMode.REVIEW_ADMITTABLE)

    assert (
        resolve_action_bar_mode(CaptureTxnPhase.ERROR, can_admit=False, can_discard=True)
        is CaptureActionBarMode.REVIEW_DISCARD_ONLY
    )
    assert visible_actions_for_mode(CaptureActionBarMode.REVIEW_DISCARD_ONLY) == frozenset(
        {"discard"}
    )


def test_action_bar_mode_stable_when_only_live_values_change():
    m1 = resolve_action_bar_mode(CaptureTxnPhase.RUNNING, can_admit=False, can_discard=False)
    m2 = resolve_action_bar_mode(CaptureTxnPhase.RUNNING, can_admit=True, can_discard=True)
    assert m1 is m2 is CaptureActionBarMode.RUNNING


def test_action_bar_idle_ignores_spurious_can_discard():
    mode = resolve_action_bar_mode(
        CaptureTxnPhase.IDLE, can_admit=False, can_discard=True
    )
    assert mode is CaptureActionBarMode.IDLE
    assert visible_actions_for_mode(mode) == frozenset({"start"})


def test_action_bar_running_ignores_spurious_can_admit_discard():
    mode = resolve_action_bar_mode(
        CaptureTxnPhase.RUNNING, can_admit=True, can_discard=True
    )
    assert mode is CaptureActionBarMode.RUNNING
    assert "discard" not in visible_actions_for_mode(mode)
    assert "admit" not in visible_actions_for_mode(mode)


def test_f5_admit_next_still_tied_to_review_ready():
    phase = resolve_capture_txn_phase(
        engine_state="stopped",
        worker_op=None,
        worker_running=False,
        can_admit=True,
        can_discard=True,
        arming=False,
    )
    assert phase is CaptureTxnPhase.REVIEW_READY
    assert f5_action_for_phase(phase, can_admit=True) == "admit_next"
    mode = resolve_action_bar_mode(phase, can_admit=True, can_discard=True)
    assert mode is CaptureActionBarMode.REVIEW_ADMITTABLE


def test_discard_not_reject_in_action_contract():
    for mode in CaptureActionBarMode:
        actions = visible_actions_for_mode(mode)
        assert "reject" not in actions
        assert "reject_trial" not in actions


def test_results_empty_and_no_overall_unchanged():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from mouse_dpi_tool.ui.views.pages import ResultsPage

    QApplication.instance() or QApplication([])
    ctl = AppController(preferences={"theme": "dark", "locale": "en-US"})
    page = ResultsPage(ctl)
    page.refresh()
    assert page.empty_panel.isHidden() is False
    assert page.content_host.isHidden() is True
    assert page.v1_host.count() == 0
    assert not hasattr(page, "overall_status")
    text_blob = (page.empty_title.text() + page.empty_body.text()).lower()
    assert "overall" not in text_blob


def test_normalize_draft_unit_b_keep_number_semantics():
    d = normalize_draft(SetupDraft(distance_input=100.0, distance_unit="inch"))
    assert d.distance_input == pytest.approx(100.0)
    assert d.distance_unit == "inch"
    assert unit_b_preview(d).interpreted_mm == pytest.approx(2540.0)
