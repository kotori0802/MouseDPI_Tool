"""App controller — one-way boundary into domain APIs.

Qt views call this controller. Controllers never pass localized labels into
Session / Measurement / Findings. Units are canonical codes only.

Formal V1 Qt operator Sessions default to movement_mode = Vector Magnitude
(Fixture Vector geometry). Directional Axis (Axis Projection) remains selectable.

CaptureRunConfig freezes measurement-affecting settings at Start until
Admit / Cancel / next Start.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from mouse_dpi_tool.capture import CaptureEngine, VisualizationPathBuffer, create_windows_capture_engine
from mouse_dpi_tool.measurement.distance import (
    canonicalize_distance_unit,
    distance_to_mm,
    mm_to_distance_input,
)
from mouse_dpi_tool.path_quality import StreamingPathQualityAccumulator
from mouse_dpi_tool.capture.motion_timing import StreamingMotionTimingAccumulator
from mouse_dpi_tool.measurement.accuracy_profile import (
    DEFAULT_ACCURACY_PROFILE,
    resolve_operator_profile_from_settings,
    settings_patch_for_accuracy_profile,
)
from mouse_dpi_tool.session import Session
from mouse_dpi_tool.ui.capture_run_config import CaptureRunConfig, freeze_capture_run_config
from mouse_dpi_tool.ui.direction import axis_for_direction, canonicalize_direction
from mouse_dpi_tool.ui.i18n import I18n
from mouse_dpi_tool.ui.preferences import load_preferences, save_preferences
from mouse_dpi_tool.ui.presentation_invalidation import REVISIONS
from mouse_dpi_tool.ui.presentation_snapshot import (
    LastCapturePresentationSnapshot,
    poster_fields,
)
from mouse_dpi_tool.ui.theme import ThemeManager
from mouse_dpi_tool.ui.viewmodels import CapturePageVM, ResultsPageVM, build_capture_viewmodel, build_results_viewmodel

EngineFactory = Callable[..., CaptureEngine]
StatusListener = Callable[[str], None]

V1_OPERATOR_MOVEMENT_MODE = "Vector Magnitude"
MOVEMENT_MODE_FIXTURE_VECTOR = "Vector Magnitude"
MOVEMENT_MODE_DIRECTIONAL_AXIS = "Axis Projection"
ALLOWED_MOVEMENT_MODES: frozenset[str] = frozenset(
    {MOVEMENT_MODE_FIXTURE_VECTOR, MOVEMENT_MODE_DIRECTIONAL_AXIS}
)

# Sentinel: omit reference_uncertainty_pct → leave Session unchanged; None → clear.
_MEASUREMENT_CONTEXT_UNSET: object = object()


class AppController:
    def __init__(
        self,
        *,
        preferences: dict[str, Any] | None = None,
        engine_factory: EngineFactory | None = None,
    ) -> None:
        self.preferences = preferences or load_preferences()
        self.i18n = I18n(self.preferences.get("locale", "en-US"))
        self.theme = ThemeManager(self.preferences.get("theme", "system"))
        self.session = Session(
            dut={"vendor": "", "model": "", "notes": ""},
            measurement_context={"method": "unknown", "direction": ""},
            settings={
                "distance_mm": 100.0,
                "distance_unit": "mm",
                "distance_input": 100.0,
                "movement_mode": V1_OPERATOR_MOVEMENT_MODE,
                "tolerance_mode": "FIELD_STRICT",
                "cpi_error_pass_pct": 3.0,
                "cpi_error_fail_pct": 5.0,
            },
        )
        self._engine_factory: EngineFactory = engine_factory or create_windows_capture_engine
        self._engine: CaptureEngine | None = None
        self._pq: StreamingPathQualityAccumulator | None = None
        self._timing: StreamingMotionTimingAccumulator | None = None
        self._viz = VisualizationPathBuffer()
        self._status_listener: StatusListener | None = None
        self._last_status: str = ""
        self._configured_dpi: int = 800
        self._busy: bool = False
        self._busy_op: str | None = None
        self._admitted: bool = False
        self._direction: str = "X+"
        self._run_config: CaptureRunConfig | None = None
        # True only after EventSource start() returned successfully (usable RUNNING).
        self._run_started: bool = False
        self._operator_issue: str | None = None
        self._last_trial_summary: dict[str, Any] | None = None
        # Presentation-only finalized Capture surface (not Session evidence).
        self._presentation: LastCapturePresentationSnapshot | None = None

    def set_locale(self, locale: str) -> None:
        self.i18n.set_locale(locale)
        self.preferences["locale"] = self.i18n.locale
        save_preferences(self.preferences)

    def set_theme(self, theme: str) -> None:
        self.theme.set_mode(theme)
        self.preferences["theme"] = theme
        save_preferences(self.preferences)

    def set_system_is_dark(self, is_dark: bool) -> None:
        self.theme.set_system_is_dark(is_dark)

    def update_dut(self, *, vendor: str = "", model: str = "", notes: str = "") -> None:
        self.session.update_dut(vendor=vendor, model=model, notes=notes)

    def update_measurement_context(
        self,
        *,
        surface: str | None = None,
        fixture_type: str | None = None,
        method: str | None = None,
        notes: str | None = None,
        polling_rate_note: str | None = None,
        dpi_configuration_source: str | None = None,
        control_software_state: str | None = None,
        control_software_name: str | None = None,
        control_software_version: str | None = None,
        profile_note: str | None = None,
        measurement_system_uncertainty_note: str | None = None,
        reference_uncertainty_pct: float | None | object = _MEASUREMENT_CONTEXT_UNSET,
        configured_dpi_confirmation: str | None = None,
    ) -> None:
        """Update Session measurement_context (operator metadata; not auto-inferred).

        ``reference_uncertainty_pct``:
        - omit / default → leave Session value unchanged
        - ``float`` → set
        - ``None`` → clear (schema allows null)
        """
        patch: dict[str, Any] = {}
        if surface is not None:
            patch["surface"] = str(surface)
        if fixture_type is not None:
            patch["fixture_type"] = str(fixture_type)
        if method is not None:
            patch["method"] = str(method)
        if notes is not None:
            patch["notes"] = str(notes)
        if polling_rate_note is not None:
            patch["polling_rate_note"] = str(polling_rate_note)
        if dpi_configuration_source is not None:
            patch["dpi_configuration_source"] = str(dpi_configuration_source)
        if control_software_state is not None:
            patch["control_software_state"] = str(control_software_state)
        if control_software_name is not None:
            patch["control_software_name"] = str(control_software_name)
        if control_software_version is not None:
            patch["control_software_version"] = str(control_software_version)
        if profile_note is not None:
            patch["profile_note"] = str(profile_note)
        if measurement_system_uncertainty_note is not None:
            patch["measurement_system_uncertainty_note"] = str(
                measurement_system_uncertainty_note
            )
        if reference_uncertainty_pct is not _MEASUREMENT_CONTEXT_UNSET:
            if reference_uncertainty_pct is None:
                patch["reference_uncertainty_pct"] = None
            else:
                patch["reference_uncertainty_pct"] = float(reference_uncertainty_pct)
        if configured_dpi_confirmation is not None:
            patch["configured_dpi_confirmation"] = str(configured_dpi_confirmation)
        if patch:
            self.session.update_measurement_context(**patch)

    @property
    def capture_navigation_locked(self) -> bool:
        """True while Start/Run/Stop/Cancel worker activity must keep the operator on Capture."""
        if self._busy:
            return True
        if self._engine is None:
            return False
        return self._engine.snapshot().state == "running"

    @property
    def measurement_config_locked(self) -> bool:
        """True while a successfully started capture is active or pending admission.

        Failed Start releases the freeze immediately (no pending evidence to protect).
        ERROR after a successful Start keeps the freeze until Cancel/Admit/discard.
        """
        if self._run_config is None or self._admitted or not self._run_started:
            return False
        if self._engine is None:
            return False
        state = self._engine.snapshot().state
        return state in {"running", "stopped", "error"}

    def last_capture_presentation(self) -> LastCapturePresentationSnapshot | None:
        """Frozen pending/admitted Capture presentation (Gauge/Path/Poster)."""
        if self._presentation is None:
            return None
        return dict(self._presentation)  # type: ignore[return-value]

    def _clear_presentation(self) -> None:
        self._presentation = None
        self._last_trial_summary = None

    def _freeze_presentation_from_engine(self, *, phase: str, trial_id: int | None = None) -> None:
        """Build presentation snapshot from current engine + domain compute_trial."""
        if self._engine is None or self._run_config is None:
            return
        from mouse_dpi_tool.measurement.trial import compute_trial

        snap = self._engine.snapshot()
        cfg = self._run_config
        pq = self._pq.snapshot() if self._pq is not None else None
        preview = compute_trial(
            trial_id=int(trial_id or 0),
            distance_mm=cfg.distance_mm,
            axis=cfg.axis,
            direction=cfg.direction,
            counts_x=int(snap.net_counts_x),
            counts_y=int(snap.net_counts_y),
            configured_dpi=cfg.configured_dpi,
            movement_mode=cfg.movement_mode,
            distance_input=cfg.distance_input,
            distance_unit=cfg.distance_unit,
            tolerance_policy=self.session.settings,
        )
        vector = compute_trial(
            trial_id=0,
            distance_mm=cfg.distance_mm,
            axis=cfg.axis,
            direction=cfg.direction,
            counts_x=int(snap.net_counts_x),
            counts_y=int(snap.net_counts_y),
            configured_dpi=cfg.configured_dpi,
            movement_mode="Vector Magnitude",
            distance_input=cfg.distance_input,
            distance_unit=cfg.distance_unit,
            tolerance_policy=self.session.settings,
        )
        pq_status = None
        if pq is not None:
            pq_status = str(pq.get("status") or "") or None
        self._presentation = {
            "phase": phase,
            "trial_id": trial_id,
            "measured_cpi": preview.get("measured_cpi"),
            "configured_dpi": preview.get("configured_dpi"),
            "error_pct": preview.get("error_pct"),
            "status": preview.get("status"),
            "counts_x": preview.get("counts_x"),
            "counts_y": preview.get("counts_y"),
            "primary_counts": preview.get("primary_counts"),
            "vector_counts": vector.get("vector_counts"),
            "vector_cpi": vector.get("measured_cpi"),
            "distance_mm": preview.get("distance_mm"),
            "movement_mode": preview.get("movement_mode"),
            "direction": preview.get("direction"),
            "axis_leakage_pct": preview.get("axis_leakage_pct"),
            "path_quality_status": pq_status,
            "integrity_ok": bool(snap.is_valid_complete_capture and snap.integrity_ok),
            "net_counts_x": int(snap.net_counts_x),
            "net_counts_y": int(snap.net_counts_y),
            "path_points": tuple(self._viz.points()),
        }
        self._last_trial_summary = poster_fields(self._presentation)

    def _mark_presentation_admitted(self, trial: dict[str, Any]) -> None:
        """Promote pending snapshot to admitted without erasing Gauge/Path."""
        vector_counts = trial.get("vector_counts")
        if vector_counts is None:
            cx = abs(int(trial.get("counts_x") or 0))
            cy = abs(int(trial.get("counts_y") or 0))
            vector_counts = int(round((cx * cx + cy * cy) ** 0.5))
        inch = float(trial.get("distance_mm") or 0.0) / 25.4
        vector_cpi = (float(vector_counts) / inch) if inch else 0.0
        path_points = (
            tuple(self._presentation["path_points"])
            if self._presentation is not None
            else tuple(self._viz.points())
        )
        net_x = int(
            self._presentation["net_counts_x"]
            if self._presentation is not None
            else (trial.get("counts_x") or 0)
        )
        net_y = int(
            self._presentation["net_counts_y"]
            if self._presentation is not None
            else (trial.get("counts_y") or 0)
        )
        self._presentation = {
            "phase": "admitted",
            "trial_id": trial.get("trial_id"),
            "measured_cpi": trial.get("measured_cpi"),
            "configured_dpi": trial.get("configured_dpi"),
            "error_pct": trial.get("error_pct"),
            "status": trial.get("status") or trial.get("measurement_status"),
            "counts_x": trial.get("counts_x"),
            "counts_y": trial.get("counts_y"),
            "primary_counts": trial.get("primary_counts"),
            "vector_counts": int(vector_counts),
            "vector_cpi": round(vector_cpi, 4),
            "distance_mm": trial.get("distance_mm"),
            "movement_mode": trial.get("movement_mode"),
            "direction": trial.get("direction"),
            "axis_leakage_pct": trial.get("axis_leakage_pct"),
            "path_quality_status": trial.get("path_quality_status"),
            "integrity_ok": True,
            "net_counts_x": net_x,
            "net_counts_y": net_y,
            "path_points": path_points,
        }
        self._last_trial_summary = poster_fields(self._presentation)

    def _ensure_measurement_editable(self) -> None:
        if self.measurement_config_locked:
            raise RuntimeError(
                "measurement configuration is frozen for the pending capture; "
                "Admit, Cancel, or start a new capture after discarding"
            )

    def update_distance(self, *, distance_input: float, unit: str) -> None:
        self._ensure_measurement_editable()
        code = canonicalize_distance_unit(unit)
        self.session.update_settings(
            {
                "distance_input": float(distance_input),
                "distance_unit": code,
            }
        )

    def change_distance_unit_preserving_physical(self, unit: str) -> dict[str, float | str]:
        self._ensure_measurement_editable()
        code = canonicalize_distance_unit(unit)
        mm = float(self.session.settings["distance_mm"])
        display = mm_to_distance_input(mm, code)
        self.session.update_settings(
            {
                "distance_input": float(display),
                "distance_unit": code,
            }
        )
        settings = self.session.settings
        return {
            "distance_mm": float(settings["distance_mm"]),
            "distance_input": float(settings["distance_input"]),
            "distance_unit": str(settings["distance_unit"]),
        }

    def convert_distance_display(self, value: float, *, from_unit: str, to_unit: str) -> float:
        mm = distance_to_mm(value, from_unit)
        return float(mm_to_distance_input(mm, to_unit))

    def set_manual_observation(self, observation_id: str, *, status: str, notes: str | None = None) -> None:
        self.session.set_manual_observation(observation_id, status=status, notes=notes)

    def session_snapshot(self) -> dict[str, Any]:
        return self.session.to_session_dict()

    def results_viewmodel(self) -> ResultsPageVM:
        return build_results_viewmodel(self.session_snapshot(), self.i18n)

    def generate_test_report(self, dest_dir: str | Path):
        """HTML + Session JSON from Session snapshot only (presentation-invariant)."""
        from mouse_dpi_tool.reporting import generate_report_bundle

        return generate_report_bundle(self.session_snapshot(), dest_dir)

    def set_capture_status_listener(self, listener: StatusListener | None) -> None:
        self._status_listener = listener

    def set_configured_dpi(self, dpi: int) -> None:
        self._ensure_measurement_editable()
        self._configured_dpi = max(1, int(dpi))

    def set_direction(self, direction: str) -> None:
        self._ensure_measurement_editable()
        self._direction = canonicalize_direction(direction)

    def set_movement_mode(self, mode: str) -> None:
        """Set formal V1 geometry: Vector Magnitude (Fixture Vector) or Axis Projection."""
        self._ensure_measurement_editable()
        code = str(mode or "").strip()
        if code not in ALLOWED_MOVEMENT_MODES:
            raise ValueError(
                f"unsupported movement_mode: {mode!r}; "
                f"expected one of {sorted(ALLOWED_MOVEMENT_MODES)}"
            )
        self.session.update_settings({"movement_mode": code})

    @property
    def accuracy_criterion_locked(self) -> bool:
        """True after any Trial evidence exists (active/rejected/deleted/audit)."""
        m = self.session.metrics()
        return bool(
            m["active_trial_count"]
            or m["rejected_trial_count"]
            or m["deleted_trial_count"]
        )

    @property
    def accuracy_profile(self) -> str:
        return resolve_operator_profile_from_settings(self.session.settings)

    def set_accuracy_profile(self, mode: str) -> dict[str, Any]:
        """Apply operator Accuracy criterion (Effective CPI PASS/WARN/FAIL bands only)."""
        if self.accuracy_criterion_locked:
            raise RuntimeError(
                "acceptance criteria are locked after measurement evidence is created; "
                "start a new test Session to use a different criterion"
            )
        if self.measurement_config_locked:
            raise RuntimeError(
                "measurement configuration is frozen for the pending capture; "
                "Admit, Cancel, or discard before changing Accuracy criterion"
            )
        patch = settings_patch_for_accuracy_profile(mode)
        updated = self.session.update_settings(patch)
        REVISIONS.bump_session_analysis()
        return updated

    def reject_trial(self, trial_id: int, *, reason: str = "") -> dict[str, Any]:
        return self.session.reject_trial(int(trial_id), reason=reason)

    def restore_rejected_trial(self, trial_id: int) -> dict[str, Any]:
        return self.session.restore_rejected_trial(int(trial_id))

    def delete_trial(self, trial_id: int, *, reason: str = "") -> dict[str, Any]:
        return self.session.delete_trial(int(trial_id), reason=reason)

    def new_test_session(self, *, keep_dut: bool = True, keep_setup: bool = True) -> Session:
        """Start a new formal operator Session (previous evidence is not carried).

        Keeps DUT/setup defaults when requested. Accuracy profile follows current
        Session settings if keep_setup, otherwise Strict default.
        """
        if self.measurement_config_locked or self.capture_navigation_locked:
            raise RuntimeError("cannot start a new Session while a Capture is active or pending")
        dut = self.session.dut if keep_dut else {"vendor": "", "model": "", "notes": ""}
        if keep_setup:
            settings = dict(self.session.settings)
        else:
            settings = {
                "distance_mm": 100.0,
                "distance_unit": "mm",
                "distance_input": 100.0,
                "movement_mode": V1_OPERATOR_MOVEMENT_MODE,
                **settings_patch_for_accuracy_profile(DEFAULT_ACCURACY_PROFILE),
            }
        # Always unlock Accuracy for the new Session by starting empty evidence.
        self.session = Session(
            dut=dut,
            measurement_context={"method": "unknown", "direction": ""},
            settings=settings,
        )
        self._clear_presentation()
        self._engine = None
        self._pq = None
        self._timing = None
        self._viz.reset()
        self._run_config = None
        self._run_started = False
        self._admitted = False
        self._operator_issue = None
        self._last_status = ""
        return self.session

    def session_trial_summary(self) -> dict[str, Any]:
        """Compact presentation summary for Trial management (not Findings truth)."""
        m = self.session.metrics()
        groups = self.session.group_summaries
        dpi_groups = sorted(
            {
                int(g.get("configured_dpi") or g.get("target_dpi") or 0)
                for g in groups
                if g.get("configured_dpi") is not None or g.get("target_dpi") is not None
            }
        )
        return {
            "active_trial_count": m["active_trial_count"],
            "rejected_trial_count": m["rejected_trial_count"],
            "deleted_trial_count": m["deleted_trial_count"],
            "dpi_groups": dpi_groups,
            "group_count": m["group_count"],
            "accuracy_profile": self.accuracy_profile,
            "cpi_error_pass_pct": float(self.session.settings.get("cpi_error_pass_pct", 3.0)),
            "cpi_error_fail_pct": float(self.session.settings.get("cpi_error_fail_pct", 5.0)),
            "tolerance_mode": str(self.session.settings.get("tolerance_mode") or ""),
            "accuracy_locked": self.accuracy_criterion_locked,
        }

    @property
    def movement_mode(self) -> str:
        if self._run_config is not None and self.measurement_config_locked:
            return self._run_config.movement_mode
        return str(self.session.settings.get("movement_mode", V1_OPERATOR_MOVEMENT_MODE))

    @property
    def direction(self) -> str:
        if self._run_config is not None and self.measurement_config_locked:
            return self._run_config.direction
        return self._direction

    @property
    def axis(self) -> str:
        if self._run_config is not None and self.measurement_config_locked:
            return self._run_config.axis
        return axis_for_direction(self._direction)

    @property
    def configured_dpi(self) -> int:
        if self._run_config is not None and self.measurement_config_locked:
            return self._run_config.configured_dpi
        return self._configured_dpi

    @property
    def capture_busy(self) -> bool:
        return self._busy

    @property
    def run_config(self) -> CaptureRunConfig | None:
        return self._run_config

    @property
    def last_trial_summary(self) -> dict[str, Any] | None:
        return dict(self._last_trial_summary) if self._last_trial_summary else None

    @property
    def operator_issue(self) -> str | None:
        return self._operator_issue

    @property
    def run_started(self) -> bool:
        return self._run_started

    def capture_viewmodel(self) -> CapturePageVM:
        cfg = self._run_config
        settings = self.session.settings
        snap = self._engine.snapshot() if self._engine is not None else None
        pq = self._pq.snapshot() if self._pq is not None else None
        if cfg is not None and self.measurement_config_locked:
            direction = cfg.direction
            dpi = cfg.configured_dpi
            distance_mm = cfg.distance_mm
            distance_input = cfg.distance_input
            distance_unit = cfg.distance_unit
            movement_mode = cfg.movement_mode
        else:
            direction = self._direction
            dpi = self._configured_dpi
            distance_mm = float(settings.get("distance_mm", 100.0))
            distance_input = float(settings.get("distance_input", 100.0))
            distance_unit = str(settings.get("distance_unit", "mm"))
            movement_mode = str(settings.get("movement_mode", V1_OPERATOR_MOVEMENT_MODE))
        path_points = self._viz.points()
        # When not live-running, prefer frozen presentation path so refresh/Admit
        # cannot blank Gauge/Trace after engine release.
        if self._presentation is not None:
            live = snap is not None and str(snap.state) == "running"
            if not live:
                path_points = tuple(self._presentation["path_points"])
        return build_capture_viewmodel(
            capture_snapshot=snap,
            i18n=self.i18n,
            last_status=self._last_status,
            configured_dpi=dpi,
            busy=self._busy,
            busy_op=self._busy_op,
            admitted=self._admitted,
            direction=direction,
            distance_mm=distance_mm,
            distance_input=distance_input,
            distance_unit=distance_unit,
            movement_mode=movement_mode,
            path_quality=pq,
            path_points=path_points,
            config_locked=self.measurement_config_locked,
        )

    def _emit_status(self, message: str) -> None:
        self._last_status = str(message)
        if self._status_listener is not None:
            self._status_listener(self._last_status)

    def start_capture(self) -> None:
        if self._busy:
            raise RuntimeError("capture operation already in progress")
        if self._engine is not None and self._engine.snapshot().state == "running":
            return
        self._busy = True
        self._busy_op = "starting"
        self._operator_issue = None
        try:
            settings = self.session.settings
            direction = canonicalize_direction(self._direction)
            axis = axis_for_direction(direction)
            self._run_config = freeze_capture_run_config(
                configured_dpi=self._configured_dpi,
                direction=direction,
                axis=axis,
                settings=settings,
            )
            cfg = self._run_config
            self._pq = StreamingPathQualityAccumulator(
                fixture_noise_floor_counts=cfg.fixture_noise_floor_counts,
                straightness_fail_pct=cfg.straightness_fail_pct,
            )
            self._timing = StreamingMotionTimingAccumulator()
            self._timing.mark_arm_requested()
            self._timing.mark_capture_start()
            # Next Start clears prior live visualization; keep last admitted poster.
            self._viz.reset()
            self._engine = self._engine_factory(on_status=self._emit_status)
            self._engine.subscribe(self._pq.on_sample)
            self._engine.subscribe(self._timing.on_sample)
            self._engine.subscribe(self._viz.on_sample)
            self._last_status = ""
            self._admitted = False
            self._run_started = False
            self._engine.start()
            # Source start returns only after ready handshake (or raises).
            self._timing.mark_source_ready()
            # Only freeze for a usable running capture.
            self._run_started = True
            # Drop un-admitted pending presentation only after Start succeeds.
            if self._presentation is not None and self._presentation.get("phase") == "pending":
                self._clear_presentation()
            self._emit_status(self._last_status or "capture_running")
        except Exception as exc:
            # Source Start failure: no pending evidence — unlock measurement config.
            self._run_started = False
            self._run_config = None
            err = str(exc)
            if not self._last_status:
                self._emit_status(err)
            elif err and err not in self._last_status:
                self._emit_status(f"{self._last_status} | {err}")
            raise
        finally:
            self._busy = False
            self._busy_op = None

    def stop_capture(self) -> None:
        if self._engine is None:
            return
        if self._busy:
            raise RuntimeError("capture operation already in progress")
        self._busy = True
        self._busy_op = "stopping"
        try:
            if self._timing is not None:
                self._timing.mark_stop_requested()
            self._engine.stop()
            if self._timing is not None:
                self._timing.mark_capture_stop()
            snap = self._engine.snapshot()
            src = getattr(self._engine, "_source", None)
            path = getattr(src, "last_stop_path", None) if src is not None else None
            dur = self._engine.last_stop_duration_ms
            diag = ""
            if dur is not None:
                diag = f" stop_ms={dur:.0f}"
            if path:
                diag += f" stop_path={path}"
            # Freeze presentation first so any status-triggered UI refresh sees data.
            if snap.state == "stopped" and snap.is_valid_complete_capture:
                self._freeze_presentation_from_engine(phase="pending")
            if snap.state == "error":
                self._emit_status(
                    (snap.last_error or self._last_status or "capture_error_incomplete") + diag
                )
            else:
                self._emit_status((self._last_status or f"capture_{snap.state}") + diag)
        finally:
            self._busy = False
            self._busy_op = None

    def cancel_capture(self, *, reason: str | None = None) -> None:
        if self._engine is None:
            return
        if self._busy:
            raise RuntimeError("capture operation already in progress")
        self._busy = True
        self._busy_op = "cancelling"
        try:
            self._engine.cancel()
            self._admitted = False
            if self._pq is not None:
                self._pq.reset()
            if self._timing is not None:
                self._timing.reset()
            self._viz.reset()
            self._clear_presentation()
            self._run_config = None
            self._run_started = False
            snap = self._engine.snapshot()
            if reason:
                self._operator_issue = str(reason)
                self._emit_status(str(reason))
            elif snap.state == "error":
                # Do not label an integrity/source ERROR as a clean cancel.
                self._emit_status(snap.last_error or self._last_status or "capture_error_incomplete")
            else:
                self._operator_issue = None
                self._emit_status("capture_cancelled")
        finally:
            self._busy = False
            self._busy_op = None

    def discard_capture(self) -> None:
        """Discard pending/invalid capture and unlock measurement configuration.

        Always allocates a fresh CaptureEngine on the next Start when the prior
        source may have been faulted. Does not admit evidence.
        """
        if self._busy:
            raise RuntimeError("capture operation already in progress")
        self._busy = True
        self._busy_op = "discarding"
        try:
            prev = self._last_status
            if self._engine is not None:
                try:
                    if self._engine.snapshot().state == "running":
                        self._engine.cancel()
                except Exception:
                    pass
                src = getattr(self._engine, "_source", None)
                if src is not None and hasattr(src, "force_kill"):
                    try:
                        src.force_kill()
                    except Exception:
                        pass
            self._engine = None
            self._pq = None
            self._timing = None
            self._viz.reset()
            self._clear_presentation()
            self._run_config = None
            self._run_started = False
            self._admitted = False
            self._operator_issue = None
            self._emit_status(f"capture_discarded:{prev}" if prev else "capture_discarded")
        finally:
            self._busy = False
            self._busy_op = None

    def handle_application_deactivated(self) -> bool:
        """V1 policy: cancel RUNNING capture when the app loses foreground focus.

        Does not alter an already STOPPED pending capture.
        Returns True if a running capture was cancelled.
        """
        if self._busy or self._engine is None:
            return False
        if self._engine.snapshot().state != "running":
            return False
        self.cancel_capture(reason="APPLICATION_LOST_FOCUS")
        return True

    def admit_capture(self, *, configured_dpi: int | None = None) -> dict[str, Any]:
        if self._engine is None:
            raise RuntimeError("no capture engine")
        if self._admitted:
            raise RuntimeError("capture already admitted; start a new capture")
        cfg = self._run_config
        if cfg is None:
            raise RuntimeError("no frozen capture configuration; start capture first")
        # Ignore post-start mutations — admit only from frozen run config.
        _ = configured_dpi
        vm = self.capture_viewmodel()
        if not vm.can_admit:
            raise RuntimeError(
                vm.direction_issue_code
                or ("capture not eligible for admission" if not vm.is_valid_complete_capture else "cannot admit")
            )
        # Ensure Session structural settings match the freeze for trial computation.
        current = self.session.settings
        if (
            abs(float(current["distance_mm"]) - cfg.distance_mm) > 1e-9
            or str(current.get("distance_unit")) != cfg.distance_unit
            or str(current.get("movement_mode")) != cfg.movement_mode
        ):
            # Prefer restoring freeze when no conflicting trial geometry exists.
            self.session.update_settings(cfg.as_settings_patch())
        pq = self._pq.snapshot() if self._pq is not None else None
        timing = None
        if self._timing is not None:
            timing = self._timing.snapshot(distance_mm=cfg.distance_mm)
        trial = self.session.admit_valid_capture(
            self._engine,
            configured_dpi=cfg.configured_dpi,
            axis=cfg.axis,
            direction=cfg.direction,
            path_quality_snapshot=pq,
            motion_timing_snapshot=timing,
            source="raw_input",
        )
        self._admitted = True
        self._run_config = None
        self._run_started = False
        # Promote presentation to admitted BEFORE releasing engine; keep Gauge/Path.
        self._mark_presentation_admitted(trial)
        # Release engine so Capture returns to Ready for continuous trial 2+.
        # Do NOT reset _viz / presentation — operator keeps finalized visuals.
        self._engine = None
        self._pq = None
        self._timing = None
        self._admitted = False
        return trial

    def trial_result_poster(self) -> dict[str, Any] | None:
        """Latest pending/admitted TrialPoster fields from presentation snapshot."""
        if self._presentation is not None:
            return poster_fields(self._presentation)
        if self._last_trial_summary is not None:
            return dict(self._last_trial_summary)
        # Fallback: compute pending preview if Stop froze nothing yet (legacy path).
        if self._engine is None or self._run_config is None:
            return None
        snap = self._engine.snapshot()
        if str(snap.state) != "stopped" or not snap.is_valid_complete_capture:
            return None
        self._freeze_presentation_from_engine(phase="pending")
        if self._presentation is None:
            return None
        return poster_fields(self._presentation)

    def retain_invalid_capture(self, *, reason: str, configured_dpi: int | None = None) -> dict[str, Any]:
        if self._engine is None:
            raise RuntimeError("no capture engine")
        cfg = self._run_config
        dpi = int(
            cfg.configured_dpi
            if cfg is not None
            else (configured_dpi if configured_dpi is not None else self._configured_dpi)
        )
        axis = cfg.axis if cfg is not None else self.axis
        direction = cfg.direction if cfg is not None else self._direction
        pq = self._pq.snapshot() if self._pq is not None else None
        timing = None
        if self._timing is not None:
            self._timing.mark_capture_stop()
            timing = self._timing.snapshot(distance_mm=float(self.session.settings.get("distance_mm") or 0))
        return self.session.retain_invalid_capture(
            self._engine,
            configured_dpi=dpi,
            reason=reason,
            axis=axis,
            direction=direction,
            path_quality_snapshot=pq,
            motion_timing_snapshot=timing,
            source="raw_input",
        )

    def visualization_points(self) -> tuple[tuple[float, float], ...]:
        if self._engine is not None and self._engine.snapshot().state == "running":
            return self._viz.points()
        if self._presentation is not None:
            return tuple(self._presentation["path_points"])
        return self._viz.points()

    def runtime_diagnostics(self) -> dict[str, int] | None:
        """Presentation-only capture queue / source diagnostics (not Session evidence)."""
        if self._engine is None:
            return None
        snap = self._engine.snapshot()
        out: dict[str, int | float | str | bool | None] = {
            "queue_depth": int(snap.queue_depth),
            "max_queue_depth": int(snap.max_queue_depth),
            "dispatcher_processed_count": int(snap.dispatcher_processed_count),
            "stale_sample_count": int(snap.stale_sample_count),
            "published_count": int(snap.published_count),
        }
        src = getattr(self._engine, "_source", None)
        qual = getattr(src, "qualification_diagnostics", None)
        if callable(qual):
            for key, value in qual().items():
                out[f"source_{key}"] = value
        return out  # type: ignore[return-value]

    def shutdown_capture(self) -> None:
        """Best-effort stop/cancel for application close."""
        if self._engine is None:
            return
        try:
            state = self._engine.snapshot().state
            if state == "running":
                self._engine.cancel()
            elif state not in {"cancelled", "idle"}:
                try:
                    self._engine.stop()
                except Exception:
                    pass
        except Exception:
            pass
        self._engine = None
        self._pq = None
        self._timing = None
        self._viz.reset()
        self._run_config = None
        self._run_started = False
