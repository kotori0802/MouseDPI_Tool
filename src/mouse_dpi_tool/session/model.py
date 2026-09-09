"""Session lifecycle — DUT metadata, trial admission, active/rejected/deleted sets.

Capture admission rule: only ``capture.is_valid_complete_capture`` may become an
active quantitative trial. Invalid/incomplete captures may be retained as
rejected evidence with a reason — never silently enter group/CPI statistics.
"""

from __future__ import annotations

import copy
import math
from typing import Any
from uuid import uuid4

from mouse_dpi_tool import __schema_version__, __version__
from mouse_dpi_tool.contracts.measurement_method import (
    MeasurementMethodError,
    require_canonical_measurement_method,
)
from mouse_dpi_tool.findings.builder import build_findings
from mouse_dpi_tool.measurement.distance import distance_to_mm
from mouse_dpi_tool.measurement.direction_evidence import (
    DirectionEvidenceError,
    DirectionMismatchError,
    assert_direction_matches_counts,
    axis_for_direction,
    require_canonical_direction,
)
from mouse_dpi_tool.measurement.group import build_group_summaries
from mouse_dpi_tool.measurement.ratio import build_ratio_analysis
from mouse_dpi_tool.measurement.settings import normalize_settings
from mouse_dpi_tool.measurement.timeutil import now_iso
from mouse_dpi_tool.measurement.trial import compute_trial, recompute_trial_from_evidence
from mouse_dpi_tool.path_quality.accumulator import attach_to_trial
from mouse_dpi_tool.capture.motion_timing import attach_motion_timing_to_trial
from mouse_dpi_tool.session.capture_evidence import CaptureEvidenceSource, build_capture_evidence

TOOL_NAME = "Mouse DPI Tool"

# Settings keys that freeze physical trial geometry — may not change once evidence exists.
_STRUCTURAL_SETTINGS_KEYS = frozenset(
    {"distance_mm", "distance_input", "distance_unit", "movement_mode"}
)

# UI presentation rows — scalars only; never capture_evidence / nested blobs.
_PRESENTATION_TRIAL_KEYS = (
    "trial_id",
    "report_trial_no",
    "configured_dpi",
    "measured_cpi",
    "error_pct",
    "status",
    "measurement_status",
    "path_quality_status",
    "movement_mode",
    "direction",
    "distance_mm",
    "accepted",
    "rejected",
    "deleted",
    "counts_x",
    "counts_y",
    "primary_counts",
    "vector_counts",
    "path_total_counts",
    "straightness_pct",
)

SETTINGS_EXPORT_KEYS = (
    "distance_mm",
    "distance_input",
    "distance_unit",
    "dpi_steps",
    "movement_mode",
    "trials_per_group",
    "min_valid_trials_per_group",
    "cpi_error_pass_pct",
    "cpi_error_fail_pct",
    "cpi_cv_pass_pct",
    "cpi_cv_fail_pct",
    "ratio_error_pass_pct",
    "ratio_error_fail_pct",
    "straightness_fail_pct",
    "fixture_noise_floor_counts",
    "tolerance_mode",
)

TRIAL_EXPORT_KEYS = (
    "trial_id",
    "session_trial_id",
    "report_trial_no",
    "created_at",
    "configured_dpi",
    "distance_mm",
    "distance_input",
    "distance_unit",
    "axis",
    "direction",
    "movement_mode",
    "counts_x",
    "counts_y",
    "vector_counts",
    "primary_counts",
    "secondary_counts",
    "measured_cpi",
    "error_pct",
    "axis_leakage_pct",
    "path_total_counts",
    "straightness_pct",
    "path_quality_status",
    "path_quality_issue_codes",
    "fixture_noise_floor_counts",
    "fixture_noise_floor_policy",
    "measurement_status",
    "cpi_error_pass_pct",
    "cpi_error_fail_pct",
    "tolerance_mode",
    "run_validity",
    "issue_tags",
    "issue_codes",
    "source",
    "note",
    "group_id",
    "accepted",
    "rejected",
    "deleted",
    "rejection_reason",
    "deletion_reason",
    "capture_evidence",
    "motion_timing",
)


class CaptureAdmissionError(ValueError):
    """Raised when a capture cannot be admitted as an active quantitative trial."""


class TrialLifecycleError(ValueError):
    """Raised for invalid trial lifecycle transitions."""


def new_session_id() -> str:
    stamp = now_iso().replace(":", "").replace("+", "p").replace("-", "")
    # Keep readable but unique; uuid suffix guarantees uniqueness within a host.
    return f"mds_{stamp[:15]}_{uuid4().hex[:8]}"


def default_dut(*, vendor: str = "", model: str = "", notes: str = "") -> dict[str, Any]:
    return {"vendor": vendor, "model": model, "notes": notes}


def default_measurement_context(
    *,
    method: str = "unknown",
    fixture_type: str = "",
    surface: str = "",
    direction: str = "",
    polling_rate_note: str = "",
    notes: str = "",
) -> dict[str, Any]:
    return {
        "method": method,
        "fixture_type": fixture_type,
        "surface": surface,
        "direction": direction,
        "polling_rate_note": polling_rate_note,
        "notes": notes,
    }


def _export_settings(settings: dict[str, Any]) -> dict[str, Any]:
    return {k: copy.deepcopy(settings[k]) for k in SETTINGS_EXPORT_KEYS if k in settings}


def _serialize_trial(trial: dict[str, Any], *, report_trial_no: int | None = None) -> dict[str, Any]:
    row = {k: copy.deepcopy(trial[k]) for k in TRIAL_EXPORT_KEYS if k in trial}
    # Map internal compute_trial()["status"] → canonical measurement_status only.
    if "measurement_status" not in row and trial.get("status") is not None:
        row["measurement_status"] = trial["status"]
    if report_trial_no is not None:
        row["report_trial_no"] = int(report_trial_no)
    # Hard guards: never emit legacy alias or duplicate trial status field.
    row.pop("target_dpi", None)
    row.pop("status", None)
    return row


def _find_trial(trials: list[dict[str, Any]], trial_id: int) -> dict[str, Any] | None:
    for trial in trials:
        if int(trial["trial_id"]) == int(trial_id):
            return trial
    return None


class Session:
    """In-memory session evidence store with stable trial IDs and analysis rebuild."""

    def __init__(
        self,
        *,
        dut: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
        measurement_context: dict[str, Any] | None = None,
        operator: str = "",
        session_id: str | None = None,
        created_at: str | None = None,
        manual_observations: list[dict[str, Any]] | None = None,
    ) -> None:
        self.session_id = session_id or new_session_id()
        self.created_at = created_at or now_iso()
        self.operator = str(operator or "")
        self._dut = self._normalize_dut(dut)
        self._measurement_context = self._normalize_context(measurement_context)
        self._settings = normalize_settings(settings)
        self._manual_observations: list[dict[str, Any]] = copy.deepcopy(list(manual_observations or []))
        self._next_trial_id = 1
        self._active: list[dict[str, Any]] = []
        self._rejected: list[dict[str, Any]] = []
        self._deleted: list[dict[str, Any]] = []
        self._group_summaries: list[dict[str, Any]] = []
        self._ratio_analysis: list[dict[str, Any]] = []
        self._rebuild_analysis()

    @staticmethod
    def _normalize_dut(dut: dict[str, Any] | None) -> dict[str, Any]:
        out = default_dut(
            vendor=str((dut or {}).get("vendor", "")),
            model=str((dut or {}).get("model", "")),
            notes=str((dut or {}).get("notes", "")),
        )
        if dut:
            for key in ("configured_dpi_stages", "sensor"):
                if key in dut:
                    out[key] = copy.deepcopy(dut[key])
        return out

    @staticmethod
    def _normalize_context(ctx: dict[str, Any] | None) -> dict[str, Any]:
        out = default_measurement_context()
        if not ctx:
            return out
        for key in out:
            if key in ctx:
                out[key] = ctx[key]
        # Optional provenance / uncertainty notes (schema-optional; never invent values).
        for key in (
            "acceptance_tolerance_note",
            "measurement_uncertainty_note",
            "measurement_system_uncertainty_note",
            "reference_uncertainty_pct",
            "dpi_configuration_source",
            "control_software_state",
            "control_software_name",
            "control_software_version",
            "profile_note",
            "configured_dpi_confirmation",
        ):
            if key in ctx:
                out[key] = ctx[key]
        # Fail closed: free-text method must never enter canonical Session storage.
        out["method"] = require_canonical_measurement_method(out.get("method", "unknown"))
        return out

    @property
    def dut(self) -> dict[str, Any]:
        return copy.deepcopy(self._dut)

    @property
    def measurement_context(self) -> dict[str, Any]:
        return copy.deepcopy(self._measurement_context)

    @property
    def settings(self) -> dict[str, Any]:
        return copy.deepcopy(self._settings)

    @property
    def manual_observations(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._manual_observations)

    @property
    def active_trials(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._active)

    @property
    def rejected_trials(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._rejected)

    @property
    def deleted_trials(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._deleted)

    def presentation_trials(self, bucket: str = "active") -> list[dict[str, Any]]:
        """Shallow rows for UI tables / fixture diag — omits heavy evidence blobs.

        Does not replace ``active_trials`` (full deepcopy boundary for mutability).
        """
        src = {
            "active": self._active,
            "rejected": self._rejected,
            "deleted": self._deleted,
        }.get(bucket)
        if src is None:
            raise ValueError(f"unknown trial bucket: {bucket!r}")
        return [{k: row[k] for k in _PRESENTATION_TRIAL_KEYS if k in row} for row in src]

    @property
    def group_summaries(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._group_summaries)

    @property
    def ratio_analysis(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._ratio_analysis)

    def update_dut(self, **fields: Any) -> dict[str, Any]:
        """Controlled DUT metadata update (deep-copied into Session-owned state)."""
        merged = {**self._dut, **fields}
        self._dut = self._normalize_dut(merged)
        return self.dut

    def update_measurement_context(self, **fields: Any) -> dict[str, Any]:
        if "method" in fields:
            fields = {
                **fields,
                "method": require_canonical_measurement_method(fields["method"]),
            }
        merged = {**self._measurement_context, **fields}
        self._measurement_context = self._normalize_context(merged)
        return self.measurement_context

    def update_settings(self, updates: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        """Normalize settings and rebuild group/ratio analysis.

        Structural keys (distance / movement_mode) cannot change once any trial
        evidence exists — existing trial distance_mm would otherwise diverge from
        top-level settings. Tolerance thresholds may change and rebuild analysis.
        """
        patch = {**(updates or {}), **kwargs}
        if bool(self._active or self._rejected or self._deleted):
            for key in _STRUCTURAL_SETTINGS_KEYS:
                if key not in patch:
                    continue
                old = self._settings.get(key)
                new = patch[key]
                if key in {"distance_mm", "distance_input"}:
                    if abs(float(old) - float(new)) > 1e-9:
                        raise ValueError(
                            f"cannot change structural setting '{key}' after trials exist; "
                            "start a new Session / new_dut() instead"
                        )
                elif new != old:
                    raise ValueError(
                        f"cannot change structural setting '{key}' after trials exist; "
                        "start a new Session / new_dut() instead"
                    )
        self._settings = normalize_settings({**self._settings, **patch})
        self._reevaluate_quantitative_trials()
        self._rebuild_analysis()
        return self.settings

    def _reevaluate_quantitative_trials(self) -> None:
        """Recompute Trial quantitative fields under current policy (Findings-0C).

        Does not alter raw counts, capture evidence, trial IDs, timestamps, or
        Path Quality evidence.
        """
        for bucket_name in ("_active", "_rejected", "_deleted"):
            bucket = getattr(self, bucket_name)
            setattr(
                self,
                bucket_name,
                [recompute_trial_from_evidence(trial, self._settings) for trial in bucket],
            )

    def set_manual_observation(
        self,
        observation_id: str,
        *,
        status: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Upsert one manual observation using the canonical template label.

        Presentation/UI must not pass localized labels into Session evidence.
        The observation ``id`` is the stable key; ``label`` is always the English
        canonical template label (or the id if unknown).
        """
        from mouse_dpi_tool.resources import manual_observation_template

        oid = str(observation_id)
        canonical_label = oid
        for row in manual_observation_template():
            if row.get("id") == oid:
                canonical_label = str(row.get("label") or oid)
                break

        for row in self._manual_observations:
            if row.get("id") == oid:
                row["status"] = str(status)
                row["label"] = canonical_label
                if notes is not None:
                    row["notes"] = str(notes)
                return copy.deepcopy(row)
        item = {
            "id": oid,
            "label": canonical_label,
            "status": str(status),
        }
        if notes is not None:
            item["notes"] = str(notes)
        self._manual_observations.append(item)
        return copy.deepcopy(item)

    def replace_manual_observations(self, observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._manual_observations = copy.deepcopy(list(observations or []))
        return self.manual_observations

    def new_dut(
        self,
        *,
        vendor: str = "",
        model: str = "",
        notes: str = "",
        settings: dict[str, Any] | None = None,
        measurement_context: dict[str, Any] | None = None,
        operator: str | None = None,
        keep_settings: bool = True,
    ) -> Session:
        """Start a new session lifecycle for a new DUT (previous evidence is not carried)."""
        return Session(
            dut={"vendor": vendor, "model": model, "notes": notes},
            settings=settings if settings is not None else (self._settings if keep_settings else None),
            measurement_context=measurement_context
            if measurement_context is not None
            else self._measurement_context,
            operator=self.operator if operator is None else operator,
        )

    def _allocate_trial_id(self) -> int:
        trial_id = self._next_trial_id
        self._next_trial_id += 1
        return trial_id

    def _build_trial_from_counts(
        self,
        *,
        counts_x: int,
        counts_y: int,
        configured_dpi: int,
        axis: str,
        direction: str,
        source: str,
        note: str,
        path_quality_snapshot: dict[str, Any] | None,
        motion_timing_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        trial = compute_trial(
            trial_id=self._allocate_trial_id(),
            distance_mm=float(self._settings["distance_mm"]),
            axis=axis,
            direction=direction,
            counts_x=int(counts_x),
            counts_y=int(counts_y),
            configured_dpi=int(configured_dpi),
            source=source,
            note=note,
            movement_mode=str(self._settings.get("movement_mode", "Vector Magnitude")),
            distance_input=float(self._settings.get("distance_input", self._settings["distance_mm"])),
            distance_unit=str(self._settings.get("distance_unit", "mm")),
            tolerance_policy=self._settings,
        )
        trial["measurement_status"] = trial.get("status")
        trial["issue_codes"] = []
        if path_quality_snapshot is not None:
            trial = attach_to_trial(trial, path_quality_snapshot)
            trial["measurement_status"] = trial.get("status")
        if motion_timing_snapshot is not None:
            trial = attach_motion_timing_to_trial(trial, motion_timing_snapshot)
        return trial

    def _require_direction_evidence(
        self,
        *,
        axis: str,
        direction: str,
        counts_x: int,
        counts_y: int,
    ) -> tuple[str, str]:
        """Fail-closed: canonical direction must match signed primary Raw Input counts."""
        try:
            code = require_canonical_direction(direction)
            expected_axis = axis_for_direction(code)
            if str(axis or "").upper() != expected_axis:
                raise CaptureAdmissionError(
                    f"axis/direction mismatch: axis={axis!r} direction={code!r} "
                    f"(expected axis {expected_axis})"
                )
            assert_direction_matches_counts(code, counts_x, counts_y)
        except DirectionMismatchError as exc:
            raise CaptureAdmissionError(str(exc)) from exc
        except DirectionEvidenceError as exc:
            raise CaptureAdmissionError(str(exc)) from exc
        return expected_axis, code

    def admit_valid_capture(
        self,
        capture: CaptureEvidenceSource,
        *,
        configured_dpi: int,
        axis: str = "X",
        direction: str = "X+",
        source: str = "raw_input",
        note: str = "",
        path_quality_snapshot: dict[str, Any] | None = None,
        motion_timing_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Admit capture as an active trial only when is_valid_complete_capture is True."""
        if not capture.is_valid_complete_capture:
            raise CaptureAdmissionError(
                "capture is not a valid complete capture; "
                "use retain_invalid_capture() to keep rejected evidence"
            )
        mode = str(self._settings.get("movement_mode", "Vector Magnitude"))
        counts_x = int(capture.net_counts_x)
        counts_y = int(capture.net_counts_y)
        if mode == "Vector Magnitude":
            # Fixture Vector: axis/direction are non-authoritative (N/A), not fake X+.
            vector = int(round(math.sqrt(counts_x * counts_x + counts_y * counts_y)))
            if vector <= 0:
                raise CaptureAdmissionError(
                    "ZERO_PRIMARY_MOVEMENT: no vector displacement for Fixture Vector admit"
                )
            from mouse_dpi_tool.measurement.group import FIXTURE_VECTOR_AXIS, FIXTURE_VECTOR_DIRECTION

            axis, direction = FIXTURE_VECTOR_AXIS, FIXTURE_VECTOR_DIRECTION
        else:
            axis, direction = self._require_direction_evidence(
                axis=axis,
                direction=direction,
                counts_x=counts_x,
                counts_y=counts_y,
            )
        trial = self._build_trial_from_counts(
            counts_x=counts_x,
            counts_y=counts_y,
            configured_dpi=configured_dpi,
            axis=axis,
            direction=direction,
            source=source,
            note=note,
            path_quality_snapshot=path_quality_snapshot,
            motion_timing_snapshot=motion_timing_snapshot,
        )
        trial["accepted"] = True
        trial["rejected"] = False
        trial["deleted"] = False
        trial["capture_evidence"] = build_capture_evidence(capture)
        self._active.append(trial)
        self._rebuild_analysis()
        return copy.deepcopy(trial)

    def retain_invalid_capture(
        self,
        capture: CaptureEvidenceSource,
        *,
        configured_dpi: int,
        reason: str,
        axis: str = "X",
        direction: str = "X+",
        source: str = "raw_input",
        note: str = "",
        path_quality_snapshot: dict[str, Any] | None = None,
        motion_timing_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Retain invalid/incomplete capture as rejected evidence (excluded from analysis)."""
        if capture.is_valid_complete_capture:
            raise CaptureAdmissionError(
                "capture is valid/complete; use admit_valid_capture() for active trials"
            )
        trial = self._build_trial_from_counts(
            counts_x=getattr(capture, "net_counts_x", 0),
            counts_y=getattr(capture, "net_counts_y", 0),
            configured_dpi=configured_dpi,
            axis=axis,
            direction=direction,
            source=source,
            note=note or reason,
            path_quality_snapshot=path_quality_snapshot,
            motion_timing_snapshot=motion_timing_snapshot,
        )
        trial["accepted"] = False
        trial["rejected"] = True
        trial["deleted"] = False
        trial["rejection_reason"] = str(reason)
        trial["capture_evidence"] = build_capture_evidence(capture)
        codes = list(trial.get("issue_codes") or [])
        codes.append("INVALID_CAPTURE_RETAINED")
        trial["issue_codes"] = codes
        self._rejected.append(trial)
        self._rebuild_analysis()
        return copy.deepcopy(trial)

    def add_synthetic_trial(
        self,
        *,
        configured_dpi: int,
        counts_x: int,
        counts_y: int = 0,
        axis: str = "X",
        direction: str = "X+",
        source: str = "synthetic",
        note: str = "",
        path_quality_snapshot: dict[str, Any] | None = None,
        motion_timing_snapshot: dict[str, Any] | None = None,
        capture_evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Admit a pre-validated synthetic/manual quantitative trial (tests / offline)."""
        axis, direction = self._require_direction_evidence(
            axis=axis,
            direction=direction,
            counts_x=int(counts_x),
            counts_y=int(counts_y),
        )
        trial = self._build_trial_from_counts(
            counts_x=counts_x,
            counts_y=counts_y,
            configured_dpi=configured_dpi,
            axis=axis,
            direction=direction,
            source=source,
            note=note,
            path_quality_snapshot=path_quality_snapshot,
            motion_timing_snapshot=motion_timing_snapshot,
        )
        trial["accepted"] = True
        trial["rejected"] = False
        trial["deleted"] = False
        if capture_evidence is not None:
            trial["capture_evidence"] = copy.deepcopy(capture_evidence)
        self._active.append(trial)
        self._rebuild_analysis()
        return copy.deepcopy(trial)

    def reject_trial(self, trial_id: int, *, reason: str = "") -> dict[str, Any]:
        trial = _find_trial(self._active, trial_id)
        if trial is None:
            raise TrialLifecycleError(f"active trial_id={trial_id} not found")
        self._active = [t for t in self._active if int(t["trial_id"]) != int(trial_id)]
        trial = dict(trial)
        trial["accepted"] = False
        trial["rejected"] = True
        trial["deleted"] = False
        if reason:
            trial["rejection_reason"] = str(reason)
        self._rejected.append(trial)
        self._rebuild_analysis()
        return copy.deepcopy(trial)

    def restore_rejected_trial(self, trial_id: int) -> dict[str, Any]:
        trial = _find_trial(self._rejected, trial_id)
        if trial is None:
            raise TrialLifecycleError(f"rejected trial_id={trial_id} not found")
        evidence = trial.get("capture_evidence")
        if isinstance(evidence, dict) and evidence.get("valid_complete_capture") is False:
            raise TrialLifecycleError(
                f"trial_id={trial_id} was retained as invalid capture evidence and cannot be restored to active analysis"
            )
        self._rejected = [t for t in self._rejected if int(t["trial_id"]) != int(trial_id)]
        trial = dict(trial)
        trial["accepted"] = True
        trial["rejected"] = False
        trial["deleted"] = False
        trial.pop("rejection_reason", None)
        self._active.append(trial)
        self._active.sort(key=lambda t: int(t["trial_id"]))
        self._rebuild_analysis()
        return copy.deepcopy(trial)

    def delete_trial(self, trial_id: int, *, reason: str = "") -> dict[str, Any]:
        trial = _find_trial(self._active, trial_id)
        bucket = "active"
        if trial is None:
            trial = _find_trial(self._rejected, trial_id)
            bucket = "rejected"
        if trial is None:
            raise TrialLifecycleError(f"trial_id={trial_id} not found in active or rejected sets")
        if bucket == "active":
            self._active = [t for t in self._active if int(t["trial_id"]) != int(trial_id)]
        else:
            self._rejected = [t for t in self._rejected if int(t["trial_id"]) != int(trial_id)]
        trial = dict(trial)
        trial["accepted"] = False
        trial["rejected"] = False
        trial["deleted"] = True
        if reason:
            trial["deletion_reason"] = str(reason)
        self._deleted.append(trial)
        self._rebuild_analysis()
        return copy.deepcopy(trial)

    def _rebuild_analysis(self) -> None:
        self._group_summaries = build_group_summaries(self._active, self._settings)
        self._ratio_analysis = build_ratio_analysis(self._group_summaries, self._settings)

    def metrics(self) -> dict[str, int]:
        return {
            "active_trial_count": len(self._active),
            "rejected_trial_count": len(self._rejected),
            "deleted_trial_count": len(self._deleted),
            "group_count": len(self._group_summaries),
            "ratio_pair_count": len(self._ratio_analysis),
        }

    def to_session_dict(self) -> dict[str, Any]:
        findings = build_findings(
            trials=self._active,
            settings=self._settings,
            manual_observations=self._manual_observations,
        )
        active_export = [
            _serialize_trial(t, report_trial_no=i)
            for i, t in enumerate(self._active, start=1)
        ]
        return {
            "schema_version": __schema_version__,
            "tool_name": TOOL_NAME,
            "tool_version": __version__,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "operator": self.operator,
            "dut": copy.deepcopy(self._dut),
            "measurement_context": copy.deepcopy(self._measurement_context),
            "settings": _export_settings(self._settings),
            "trials": active_export,
            "rejected_trials": [_serialize_trial(t) for t in self._rejected],
            "deleted_trials": [_serialize_trial(t) for t in self._deleted],
            "group_summaries": copy.deepcopy(self._group_summaries),
            "ratio_analysis": copy.deepcopy(self._ratio_analysis),
            "findings": findings,
            "metrics": self.metrics(),
        }
