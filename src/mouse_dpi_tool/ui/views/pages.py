"""Shell pages — presentation only."""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, QObject, QThread, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from mouse_dpi_tool.contracts.measurement_method import (
    CANONICAL_MEASUREMENT_METHODS,
    MeasurementMethodError,
    is_canonical_measurement_method,
)
from mouse_dpi_tool.measurement.distance import distance_to_mm
from mouse_dpi_tool.session.writer import SessionValidationError
from mouse_dpi_tool.ui import SUPPORTED_LOCALES, THEME_MODES
from mouse_dpi_tool.ui.capture_transaction import (
    CaptureActionBarMode,
    CaptureTxnPhase,
    f5_action_for_phase,
    resolve_action_bar_mode,
    resolve_capture_txn_phase,
)
from mouse_dpi_tool.ui.components.capture_action_bar import CaptureActionBar
from mouse_dpi_tool.ui.views.setup_page import SetupPage
from mouse_dpi_tool.ui.chrome_motion import fade_widget, motion_enabled
from mouse_dpi_tool.ui.components.combo import combo_data, refill_combo
from mouse_dpi_tool.ui.layout_metrics import (
    SPACE_FORM_GROUP,
    SPACE_FORM_WITHIN,
    SPACE_HELPER_AFTER,
    SPACE_SECTION,
    RESULTS_EMPTY_MAX_WIDTH,
    SETTINGS_PANEL_MAX_WIDTH,
    comfortable_prose_max_width,
    configure_form_layout,
    style_form_label,
)
from mouse_dpi_tool.ui.components.dpi_field import ConfiguredDpiField
from mouse_dpi_tool.ui.components.engineering_viz_host import EngineeringVisualizationHost
from mouse_dpi_tool.ui.components.guided_lane import GuidedLane
from mouse_dpi_tool.ui.components.trial_workspace import TrialWorkspace
from mouse_dpi_tool.ui.controllers import (
    MOVEMENT_MODE_DIRECTIONAL_AXIS,
    MOVEMENT_MODE_FIXTURE_VECTOR,
    AppController,
)
from mouse_dpi_tool.ui.direction import CANONICAL_DIRECTIONS
from mouse_dpi_tool.ui.i18n import LOCALE_DISPLAY_NAMES
from mouse_dpi_tool.ui.presentation_invalidation import COUNTERS, REVISIONS
from mouse_dpi_tool.ui.viewmodels import CapturePageVM, ResultsPageVM
def _is_method_metadata_error(err: BaseException) -> bool:
    """True when export/validation failed due to measurement_context.method."""
    if isinstance(err, MeasurementMethodError):
        return True
    text = str(err)
    if isinstance(err, SessionValidationError) and "method" in text.lower():
        return True
    return "measurement_context.method" in text


# Presentation refresh (~30 Hz). Independent of Raw Input event rate.
_LIVE_REFRESH_MS = 33
# Secondary UX bounce guard only — phase barrier is the correctness mechanism.
_F5_ARMING_IGNORE_SEC = 0.45


def _card() -> QFrame:
    frame = QFrame()
    frame.setObjectName("Card")
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    return frame


def _settings_card() -> QFrame:
    """Intentional Preferences Card (Phase 3.1 bounded width)."""
    return _card()


class _CaptureWorker(QObject):
    finished = Signal(str, object)

    def __init__(self, controller: AppController, op: str) -> None:
        super().__init__()
        self.controller = controller
        self.op = op

    def run(self) -> None:
        err: object = None
        try:
            if self.op == "start":
                self.controller.start_capture()
            elif self.op == "stop":
                self.controller.stop_capture()
            elif self.op == "cancel":
                self.controller.cancel_capture()
            elif self.op == "discard":
                self.controller.discard_capture()
            else:
                raise RuntimeError(f"unknown capture op: {self.op}")
        except Exception as exc:  # noqa: BLE001
            err = exc
        self.finished.emit(self.op, err)


class CapturePage(QWidget):
    refresh_requested = Signal()
    nav_sync_needed = Signal()

    def __init__(self, controller: AppController, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._thread: QThread | None = None
        self._worker: _CaptureWorker | None = None
        self._pending_capture_op: str | None = None
        self._f5_arming_ignore_until: float = 0.0
        self._skip_heavy_chrome_once: bool = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # refresh_requested is handled by MainWindow (refresh + nav lock sync).

        self.title = QLabel()
        self.title.setObjectName("HeroTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("Muted")
        self.subtitle.setWordWrap(True)
        self._dpi_label = QLabel()
        self._geometry_label = QLabel()
        self._direction_label = QLabel()
        self.dpi = ConfiguredDpiField()
        self.dpi.setValue(controller.configured_dpi)
        self.dpi.valueChanged.connect(self._dpi_changed)
        self._dpi_hint = QLabel()
        self._dpi_hint.setObjectName("Hint")
        self._dpi_hint.setWordWrap(True)
        self._dpi_confirm_hint = QLabel()
        self._dpi_confirm_hint.setObjectName("Hint")
        self._dpi_confirm_hint.setWordWrap(True)
        self._dpi_confirm_hint.hide()
        self.geometry_summary = QLabel()
        self.geometry_summary.setObjectName("CommittedSummary")
        self.geometry_summary.setWordWrap(True)
        self.geometry_hint = QLabel()
        self.geometry_hint.setObjectName("PassiveHelper")
        self.geometry_hint.setWordWrap(True)
        self.direction = QComboBox()
        self.direction.currentIndexChanged.connect(self._direction_changed)
        self.lane = GuidedLane()
        self.viz = EngineeringVisualizationHost()
        self.viz.setObjectName("EvidenceCanvasHost")
        self.gauge = self.viz.gauge
        self.canvas = self.viz.canvas
        self.instruction = QLabel()
        self.instruction.setObjectName("Muted")
        self.instruction.setWordWrap(True)
        self.instruction.setMaximumWidth(comfortable_prose_max_width(self))
        self.instruction.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.instruction.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        self.action_bar = CaptureActionBar()
        self.action_bar.start_clicked.connect(self._on_start_clicked)
        self.action_bar.stop_clicked.connect(lambda: self._run_op("stop"))
        self.action_bar.cancel_clicked.connect(lambda: self._run_op("cancel"))
        self.action_bar.admit_clicked.connect(self._admit_and_start_next)
        self.action_bar.discard_clicked.connect(lambda: self._run_op("discard"))
        # Compat aliases for tests / older call sites
        self.start_btn = self.action_bar.start_btn
        self.stop_btn = self.action_bar.stop_btn
        self.cancel_btn = self.action_bar.cancel_btn
        self.admit_btn = self.action_bar.admit_btn
        self.discard_btn = self.action_bar.discard_btn
        self._action_bar_mode = CaptureActionBarMode.IDLE
        self.state_label = QLabel()
        self.ops_line = QLabel()
        self.ops_line.setObjectName("Muted")
        self.ops_line.setWordWrap(True)
        self.ready_banner = QLabel()
        self.ready_banner.setObjectName("ReadyBanner")
        self.ready_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ready_banner.setWordWrap(True)
        self.ready_banner.hide()
        self._awaiting_first_motion = False
        self.message_label = QLabel()
        self.message_label.setObjectName("Muted")
        self.message_label.setWordWrap(True)
        self._poster_fingerprint: str | None = None
        self._poster_placeholder = QLabel()
        self._poster_placeholder.setObjectName("Muted")
        self._poster_placeholder.setWordWrap(True)

        self.poster = QFrame()
        self.poster.setObjectName("TrialPoster")
        self.poster_title = QLabel()
        self.poster_title.setObjectName("SectionTitle")
        self.poster_cpi = QLabel()
        self.poster_cpi.setObjectName("PosterCpi")
        self.poster_status = QLabel()
        self.poster_status.setObjectName("SectionTitle")
        self.poster_error = QLabel()
        self.poster_hint = QLabel()
        self.poster_hint.setObjectName("Muted")
        self.poster_hint.setWordWrap(True)
        self.poster_metrics = QGridLayout()
        self.poster_metrics.setHorizontalSpacing(16)
        self.poster_metrics.setVerticalSpacing(6)
        self._poster_metric_labels: list[QLabel] = []
        head = QHBoxLayout()
        head.addWidget(self.poster_cpi, 1)
        head.addWidget(self.poster_status, 0)
        head.addWidget(self.poster_error, 0)
        poster_l = QVBoxLayout(self.poster)
        poster_l.setContentsMargins(16, 14, 16, 14)
        poster_l.setSpacing(8)
        poster_l.addWidget(self.poster_title)
        poster_l.addLayout(head)
        poster_l.addLayout(self.poster_metrics)
        poster_l.addWidget(self.poster_hint)

        self.tech_toggle = QToolButton()
        self.tech_toggle.setObjectName("TechToggle")
        self.tech_toggle.setCheckable(True)
        self.tech_toggle.setChecked(False)
        self.tech_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.tech_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.tech_toggle.toggled.connect(self._toggle_tech)
        self.tech_panel = QFrame()
        self.tech_panel.setObjectName("TechPanel")
        self.tech_panel.setVisible(False)
        self.status_label = QLabel()
        self.status_label.setObjectName("Muted")
        self.status_label.setWordWrap(True)
        self.kpi_label = QLabel()
        self.kpi_label.setObjectName("Muted")
        self.kpi_label.setWordWrap(True)
        tech_l = QVBoxLayout(self.tech_panel)
        tech_l.setContentsMargins(10, 8, 10, 8)
        tech_l.addWidget(self.status_label)
        tech_l.addWidget(self.kpi_label)
        self.fixture_diag_label = QLabel()
        self.fixture_diag_label.setObjectName("Muted")
        self.fixture_diag_label.setWordWrap(True)
        tech_l.addWidget(self.fixture_diag_label)

        row = QHBoxLayout()
        row.setContentsMargins(0, 8, 0, 4)
        row.setSpacing(8)
        row.addWidget(self.action_bar, 1)
        self.shortcut_hint = QLabel()
        self.shortcut_hint.setObjectName("CaptureCommandHint")
        self.shortcut_hint.setWordWrap(True)
        self.procedure_hint = QLabel()
        self.procedure_hint.setObjectName("CaptureCommandHint")
        self.procedure_hint.setWordWrap(True)
        self.measure_toggle = QToolButton()
        self.measure_toggle.setObjectName("TechToggle")
        self.measure_toggle.setCheckable(True)
        self.measure_toggle.setChecked(False)
        self.measure_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.measure_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.measure_guide = QLabel()
        self.measure_guide.setObjectName("Muted")
        self.measure_guide.setWordWrap(True)
        self.measure_guide.setTextFormat(Qt.TextFormat.RichText)
        self.measure_guide.setVisible(False)

        def _toggle_measure(checked: bool) -> None:
            self.measure_guide.setVisible(checked)
            self.measure_toggle.setArrowType(
                Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
            )

        self.measure_toggle.toggled.connect(_toggle_measure)
        form = QFormLayout()
        configure_form_layout(form)
        style_form_label(self._dpi_label)
        style_form_label(self._geometry_label)
        style_form_label(self._direction_label)
        form.addRow(self._dpi_label, self.dpi)
        form.addRow("", self._dpi_hint)
        form.addRow("", self._dpi_confirm_hint)
        form.addRow(self._geometry_label, self.geometry_summary)
        form.addRow("", self.geometry_hint)
        form.addRow(self._direction_label, self.direction)
        self.lane.setMaximumHeight(72)

        # Phase 3 hierarchy: run context → viz → short instruction → ActionBar → poster
        # → Trial Ledger → Technical details. Do not shrink viz to force ledger above fold.
        header = QFrame()
        header.setObjectName("CaptureHeader")
        header.setAutoFillBackground(False)
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header_l = QVBoxLayout(header)
        header_l.setContentsMargins(0, 0, 0, 0)
        header_l.setSpacing(6)
        header_l.addLayout(form)
        header_l.addWidget(self.lane)

        card = QFrame()
        # Intentional Capture workspace surface (not a nested black slab).
        # Structural children (header / ActionBar / scroll inner) stay transparent.
        card.setObjectName("CaptureShell")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        card_inner = QWidget()
        card_inner.setObjectName("TransparentSurface")
        card_inner.setAutoFillBackground(False)
        card_inner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        card_l = QVBoxLayout(card_inner)
        card_l.setContentsMargins(12, 12, 12, 12)
        card_l.setSpacing(10)
        card_l.addWidget(header)
        card_l.addWidget(self.viz, 1)
        card_l.addWidget(self.instruction, 0, Qt.AlignmentFlag.AlignLeft)
        card_l.addLayout(row)
        card_l.addWidget(self.shortcut_hint)
        card_l.addWidget(self.procedure_hint)
        card_l.addWidget(self.measure_toggle, alignment=Qt.AlignmentFlag.AlignLeft)
        card_l.addWidget(self.measure_guide)
        card_l.addWidget(self._poster_placeholder)
        card_l.addWidget(self.poster)
        self.trials = TrialWorkspace(controller)
        self.trials.changed.connect(self._on_trials_changed)
        card_l.addWidget(self.trials)
        card_l.addWidget(self.state_label)
        card_l.addWidget(self.ops_line)
        card_l.addWidget(self.ready_banner)
        card_l.addWidget(self.message_label)
        card_l.addWidget(self.tech_toggle, alignment=Qt.AlignmentFlag.AlignLeft)
        card_l.addWidget(self.tech_panel)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setWidget(card_inner)
        card_outer = QVBoxLayout(card)
        card_outer.setContentsMargins(0, 0, 0, 0)
        card_outer.addWidget(self.scroll)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 12, 20, 12)
        root.addWidget(self.title)
        root.addWidget(self.subtitle)
        root.addSpacing(4)
        root.addWidget(card, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(_LIVE_REFRESH_MS)
        self._timer.timeout.connect(self.refresh)

        # F5/ESC are owned by MainWindow (WindowShortcut) so they keep working
        # after Admit when focus is not on this page's children.
        self._shortcut_f5 = None
        self._shortcut_esc = None

        self.controller.set_capture_status_listener(self._on_status)
        self.retranslate()
        self.refresh()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        # Resume live viz only for a confirmed RUNNING generation (not stop/drain).
        if self._is_live_capture_running():
            self._timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802
        self._clear_pending_capture_op(reason="page_hide")
        self._timer.stop()
        super().hideEvent(event)

    def _clear_pending_capture_op(self, *, reason: str) -> None:
        """Drop stale pending Stop/Cancel — never carries across ownership boundaries."""
        _ = reason
        self._pending_capture_op = None

    def _worker_op(self) -> str | None:
        return self._worker.op if self._worker is not None else None

    def _is_finishing_worker(self) -> bool:
        """True while Stop/Cancel QThread is in flight (expensive drain presentation)."""
        return bool(
            self._thread is not None
            and self._thread.isRunning()
            and self._worker_op() in {"stop", "cancel"}
        )

    def _is_live_capture_running(self) -> bool:
        """Engine RUNNING and not in Stop/Cancel finishing worker."""
        vm = self.controller.capture_viewmodel()
        return vm.state == "running" and not self._is_finishing_worker()

    def _sync_live_timer(self, *, running: bool, busy: bool) -> None:
        """Presentation-only timer lifecycle — never owns Raw Input."""
        if self._is_finishing_worker():
            self._timer.stop()
            return
        if running:
            if not self._timer.isActive():
                self._timer.start()
            return
        if not busy and self._timer.isActive():
            self._timer.stop()

    def _txn_phase(self) -> CaptureTxnPhase:
        vm = self.controller.capture_viewmodel()
        worker_running = self._thread is not None and self._thread.isRunning()
        worker_op = self._worker_op()
        # ARMING while Start worker is in flight, or bounce window before RUNNING.
        if worker_running and worker_op == "start":
            arming = True
        elif time.monotonic() < self._f5_arming_ignore_until and vm.state != "running":
            arming = True
        else:
            arming = False
        return resolve_capture_txn_phase(
            engine_state=vm.state,
            worker_op=worker_op,
            worker_running=worker_running,
            can_admit=bool(vm.can_admit),
            can_discard=bool(vm.can_discard),
            arming=arming,
        )

    def _on_f5(self) -> None:
        """F5 is driven by capture transaction phase; debounce is UX-only."""
        vm = self.controller.capture_viewmodel()
        phase = self._txn_phase()
        action = f5_action_for_phase(phase, can_admit=bool(vm.can_admit))
        if action == "ignore":
            return
        if action == "stop":
            if self._thread is not None and self._thread.isRunning():
                # Only queue Stop for an already-RUNNING generation — never for ARMING.
                if phase is CaptureTxnPhase.RUNNING and self._pending_capture_op != "cancel":
                    self._pending_capture_op = "stop"
                return
            self._run_op("stop")
            return
        if action == "admit_next":
            self._admit_and_start_next()
            return
        if action == "start":
            if vm.busy:
                return
            self._run_op("start")

    def _admit_and_start_next(self) -> None:
        # Drop any stale Stop queued while the previous Start/Stop worker was busy.
        self._pending_capture_op = None
        self._f5_arming_ignore_until = time.monotonic() + _F5_ARMING_IGNORE_SEC
        try:
            trial = self.controller.admit_capture()
            self.message_label.setText(
                self.controller.i18n.t("capture.admitted_next").format(
                    trial_id=trial.get("trial_id")
                )
            )
        except Exception as exc:  # noqa: BLE001
            self.message_label.setText(str(exc))
            self._f5_arming_ignore_until = 0.0
            self.refresh()
            return
        REVISIONS.bump_trial_lifecycle()
        self._trials_fp = None
        self._fixture_diag_fp = None
        # Poster/buttons first; defer Trial table + fixture diag so Start arms promptly.
        self._skip_heavy_chrome_once = True
        try:
            self.refresh()
        finally:
            self._skip_heavy_chrome_once = False
        QTimer.singleShot(0, self._start_next_after_admit)

    def _start_next_after_admit(self) -> None:
        self._run_op("start")
        # Rebuild deferred chrome after Start worker is launched (non-blocking).
        self._trials_fp = None
        self._fixture_diag_fp = None
        QTimer.singleShot(0, self.refresh)

    def _on_esc(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            vm = self.controller.capture_viewmodel()
            if vm.state == "running" or (self._worker is not None and self._worker.op == "start"):
                self._pending_capture_op = "cancel"
            return
        if self.controller.capture_viewmodel().state == "running":
            self._run_op("cancel")

    def _dpi_changed(self, value: int) -> None:
        self._dpi_confirm_hint.setText(
            self.controller.i18n.t("capture.dpi_confirmation_recommended")
        )
        self._dpi_confirm_hint.show()
        if self.controller.measurement_config_locked:
            vm = self.controller.capture_viewmodel()
            # Changing DPI abandons a pending/failed run — do not force Admit.
            if vm.state != "running" and (vm.can_admit or vm.can_discard):
                try:
                    self.controller.discard_capture()
                    self.message_label.setText(
                        self.controller.i18n.t("capture.discarded_for_dpi")
                    )
                except Exception as exc:  # noqa: BLE001
                    self.message_label.setText(str(exc))
                    self.refresh()
                    return
            else:
                self.refresh()
                return
        try:
            self.controller.set_configured_dpi(int(value))
        except RuntimeError as exc:
            self.message_label.setText(str(exc))
            self.refresh()
            return
        self.refresh()

    def _direction_changed(self, _index: int = 0) -> None:
        if self.controller.measurement_config_locked:
            self.refresh()
            return
        code = combo_data(self.direction, self.controller.direction)
        try:
            self.controller.set_direction(code)
            self.lane.set_direction(code)
        except RuntimeError as exc:
            self.message_label.setText(str(exc))
        self.refresh()

    def _on_status(self, _message: str) -> None:
        # Engine/worker threads must not touch widgets directly — queue a GUI refresh.
        self.refresh_requested.emit()

    def _run_op(self, op: str) -> None:
        if self._thread is not None and self._thread.isRunning():
            # Never run Stop/Cancel synchronously on the GUI thread.
            # Legal pending values: "stop" | "cancel" only.
            # Start during STOPPING/DRAINING/ARMING wind-down is NOT queued
            # (no hidden Stop→auto-Start; only REVIEW admit_next starts the next run).
            if op in {"stop", "cancel"}:
                if op == "cancel" or self._pending_capture_op != "cancel":
                    self._pending_capture_op = op
            # Explicitly refuse pending Start — do not retain "just in case".
            return
        vm = self.controller.capture_viewmodel()
        if op == "start" and (
            vm.state == "running"
            or (vm.config_locked and not vm.can_admit)
            or (vm.can_discard and not vm.can_admit)
        ):
            return
        if op in {"stop", "cancel"} and vm.state != "running":
            return
        if op == "discard" and not vm.can_discard:
            return
        # Discard is local/cleanup — keep it synchronous so buttons never stick disabled.
        if op == "discard":
            self._clear_pending_capture_op(reason="discard")
            self.message_label.setText("")
            try:
                self.controller.discard_capture()
                self.message_label.setText(self.controller.i18n.t("capture.discarded"))
            except Exception as exc:  # noqa: BLE001
                self.message_label.setText(str(exc))
            self._timer.stop()
            self.refresh()
            return
        self.message_label.setText("")
        self._apply_capture_controls(busy=True)
        self._thread = QThread(self)
        self._worker = _CaptureWorker(self.controller, op)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_op_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.finished.connect(self._thread.deleteLater)
        # Live viz timer only while capturing. During Stop/Cancel drain, suppress
        # 30 Hz paint; status-driven refresh_requested keeps ActionBar/state alive.
        if op == "start":
            self._timer.start()
        elif op in {"stop", "cancel"}:
            self._timer.stop()
        self._thread.start()

    def _on_thread_finished(self) -> None:
        # Ignore stale finished signals from a prior QThread after a newer worker started.
        sender = self.sender()
        if sender is not None and self._thread is not None and sender is not self._thread:
            return
        self._thread = None
        self._worker = None
        pending = self._pending_capture_op
        self._pending_capture_op = None
        self.refresh()
        # Only Stop/Cancel may be replayed — and only onto a still-RUNNING generation.
        if pending in {"stop", "cancel"}:
            vm = self.controller.capture_viewmodel()
            if vm.state == "running":
                self._run_op(pending)
        # pending "start" is illegal and never dispatched.

    def _on_op_finished(self, op: str, err: object) -> None:
        # Ignore stale worker completions if a newer worker superseded this one.
        worker = self.sender()
        if (
            worker is not None
            and self._worker is not None
            and worker is not self._worker
        ):
            return
        if err is not None:
            self.message_label.setText(str(err))
            self._clear_pending_capture_op(reason="op_error")
        vm = self.controller.capture_viewmodel()
        if op == "stop" and err is None:
            if vm.direction_issue_code == "DIRECTION_MISMATCH":
                selected = self.controller.i18n.direction(vm.expected_direction)
                observed_code = vm.observed_direction or "—"
                observed = (
                    self.controller.i18n.direction(observed_code)
                    if observed_code in CANONICAL_DIRECTIONS
                    else observed_code
                )
                self.message_label.setText(
                    self.controller.i18n.t("capture.mismatch").format(
                        selected=selected, observed=observed
                    )
                )
            elif vm.direction_issue_code == "ZERO_PRIMARY_MOVEMENT":
                self.message_label.setText(self.controller.i18n.t("capture.zero_primary"))
            elif vm.can_admit:
                self.message_label.setText(self.controller.i18n.t("capture.ready_to_admit"))
            elif vm.last_error:
                self.message_label.setText(vm.last_error)
            # Terminal review / idle after Stop — drop any stale pending.
            self._clear_pending_capture_op(reason="stop_complete")
        elif op == "discard" and err is None:
            self.message_label.setText(self.controller.i18n.t("capture.discarded"))
        elif op == "cancel":
            self._clear_pending_capture_op(reason="cancel_complete")
        if self.controller.operator_issue == "APPLICATION_LOST_FOCUS":
            self.message_label.setText(self.controller.i18n.t("capture.focus_lost"))
        if op == "start" and err is None and vm.state == "running":
            # Authoritative ready = source handshake succeeded — not gauge centering.
            self._awaiting_first_motion = True
            self.ready_banner.setText(self.controller.i18n.t("capture.ready_move_now"))
            self.ready_banner.show()
        if op in {"stop", "cancel", "discard"} or err is not None:
            self._awaiting_first_motion = False
            self.ready_banner.hide()
        if vm.state != "running":
            self._timer.stop()
            self._awaiting_first_motion = False
            if op != "start":
                self.ready_banner.hide()
        elif not self._is_finishing_worker() and not self._timer.isActive():
            self._timer.start()
        # Refresh immediately so Poster/buttons update without waiting for another tick.
        self.refresh()

    def _on_start_clicked(self) -> None:
        vm = self.controller.capture_viewmodel()
        if vm.can_admit:
            self._admit_and_start_next()
            return
        self._run_op("start")

    def _admit(self) -> None:
        try:
            trial = self.controller.admit_capture()
            self.message_label.setText(
                self.controller.i18n.t("capture.admitted").format(trial_id=trial.get("trial_id"))
            )
        except Exception as exc:  # noqa: BLE001
            self.message_label.setText(str(exc))
        REVISIONS.bump_trial_lifecycle()
        self._trials_fp = None  # force Trial table rebuild after Admit
        self._fixture_diag_fp = None
        self.refresh()

    def _apply_capture_controls(self, *, busy: bool | None = None) -> None:
        """Single source of truth for capture button enablement."""
        vm: CapturePageVM = self.controller.capture_viewmodel()
        thread_busy = self._thread is not None and self._thread.isRunning()
        worker_op = self._worker.op if self._worker is not None else None
        running = vm.state == "running"
        locked = vm.config_locked
        # Blocking busy: domain busy OR worker in flight. After Start completes,
        # state is already "running" while the QThread is still quitting — must
        # NOT treat that as blocking Stop (that was the all-gray lock bug).
        if busy is not None:
            block_start = bool(busy)
        else:
            block_start = bool(vm.busy) or thread_busy
        stop_blocking = bool(vm.busy) or (
            thread_busy and worker_op in {"stop", "cancel"}
        )
        can_start = (
            not block_start
            and not running
            and (
                (not locked and not vm.can_admit and not vm.can_discard)
                or vm.can_admit
            )
        )
        self.start_btn.setEnabled(can_start)
        self.stop_btn.setEnabled(running and not stop_blocking)
        self.cancel_btn.setEnabled(running and not stop_blocking)
        self.admit_btn.setEnabled(not block_start and vm.can_admit)
        self.discard_btn.setEnabled(not block_start and vm.can_discard)
        editable = not block_start and not running and not locked
        # Pending/failed runs used to hard-lock DPI until Admit — allow DPI edit to
        # auto-discard instead of forcing a duplicate Admit path when switching DPI.
        pending_unlock = (not block_start) and (not running) and (vm.can_admit or vm.can_discard)
        self.dpi.setEnabled(editable or pending_unlock)
        fixture = vm.movement_mode == MOVEMENT_MODE_FIXTURE_VECTOR
        self.direction.setEnabled(editable and not fixture)
        self.direction.setVisible(not fixture)
        self._direction_label.setVisible(not fixture)
        self.lane.setVisible(not fixture)
        self.viz.set_fixture_vector_mode(fixture)
        phase = self._txn_phase()
        mode = resolve_action_bar_mode(
            phase, can_admit=bool(vm.can_admit), can_discard=bool(vm.can_discard)
        )
        switched = self.action_bar.set_mode(mode)
        if switched:
            self._action_bar_mode = mode
        self.action_bar.set_busy_enabled(
            can_start=can_start,
            can_stop=running and not stop_blocking,
            can_admit=not block_start and bool(vm.can_admit),
            can_discard=not block_start and bool(vm.can_discard),
        )
        self._update_progressive_help(mode)

    def _committed_geometry_label(self, movement_mode: str) -> str:
        t = self.controller.i18n.t
        if movement_mode == MOVEMENT_MODE_FIXTURE_VECTOR:
            return t("geometry.fixture_vector")
        if movement_mode == MOVEMENT_MODE_DIRECTIONAL_AXIS:
            return t("geometry.directional_axis")
        return str(movement_mode or "—")

    def _update_progressive_help(self, mode: CaptureActionBarMode) -> None:
        t = self.controller.i18n.t
        key = {
            CaptureActionBarMode.IDLE: "capture.help.idle",
            CaptureActionBarMode.ARMING: "capture.help.arming",
            CaptureActionBarMode.RUNNING: "capture.help.running",
            CaptureActionBarMode.STOPPING: "capture.help.stopping",
            CaptureActionBarMode.REVIEW_ADMITTABLE: "capture.help.review",
            CaptureActionBarMode.REVIEW_DISCARD_ONLY: "capture.help.discard_only",
        }.get(mode, "capture.procedure_hint")
        self.procedure_hint.setText(t(key))

    def _on_trials_changed(self) -> None:

        # Lifecycle mutations are Domain-owned; refresh Capture chrome once
        # (do not also emit refresh_requested — that would double-refresh).
        # New Session / admit / reject must not inherit a pending Stop/Cancel.
        self._clear_pending_capture_op(reason="trial_lifecycle")
        REVISIONS.bump_trial_lifecycle()
        self._trials_fp = None
        self._fixture_diag_fp = None
        self.refresh()
        self.nav_sync_needed.emit()

    def _toggle_tech(self, checked: bool) -> None:
        fade_widget(
            self.tech_panel,
            show=bool(checked),
            enabled=motion_enabled(self.controller.preferences),
        )
        self.tech_toggle.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )
        if checked:
            # Force KPI / fixture diag populate when opening (skipped on live path when closed).
            self._fixture_diag_fp = None
            self.refresh()

    def refresh(self) -> None:
        vm: CapturePageVM = self.controller.capture_viewmodel()
        t = self.controller.i18n.t
        running = vm.state == "running"
        busy = vm.busy or (self._thread is not None and self._thread.isRunning())
        # Timer lifecycle must not re-arm during Stop/Cancel drain (state may still
        # be "running" until engine.stop returns).
        self._sync_live_timer(running=running, busy=busy)
        if running:
            COUNTERS.live_timer_ticks += 1
            if self._awaiting_first_motion and (
                abs(int(vm.net_counts_x)) > 0
                or abs(int(vm.net_counts_y)) > 0
                or int(vm.published_count) > 0
            ):
                self._awaiting_first_motion = False
                self.ready_banner.hide()
        elif self._awaiting_first_motion:
            self._awaiting_first_motion = False
            self.ready_banner.hide()

        display_key = f"capture.display.{vm.display_state}"
        state_txt = f"{t('capture.state')}: {t(display_key, default=vm.display_state)}"
        if self.state_label.text() != state_txt:
            self.state_label.setText(state_txt)
        status_text = vm.last_status or "—"
        status_line = f"{t('capture.status')}: {status_text}"
        if self.status_label.text() != status_line:
            self.status_label.setText(status_line)
        devices = ", ".join(vm.device_ids) if vm.device_ids else "—"
        pq_raw = vm.path_quality_status or "—"
        if running:
            integrity = t("capture.integrity_pending")
            pq = f"{pq_raw} · {t('capture.live_provisional')}"
        elif vm.state == "cancelled":
            integrity = t("capture.integrity_na")
            pq = pq_raw
        elif vm.state == "idle":
            integrity = "—"
            pq = "—"
        else:
            integrity = "OK" if vm.integrity_ok else "FAIL"
            pq = pq_raw
        ops_txt = f"{t('capture.integrity')}: {integrity} · {t('capture.path_quality')}: {pq}"
        if self.ops_line.text() != ops_txt:
            self.ops_line.setText(ops_txt)
        diag = ""
        runtime = self.controller.runtime_diagnostics()
        if runtime and (runtime["queue_depth"] or runtime["max_queue_depth"]):
            diag = (
                f"\n{t('capture.runtime_diag')}: q={runtime['queue_depth']} "
                f"max_q={runtime['max_queue_depth']} disp={runtime['dispatcher_processed_count']}"
            )
        method = vm.movement_mode
        direction_txt = "—" if method == MOVEMENT_MODE_FIXTURE_VECTOR else vm.direction
        # Live 30 Hz: KPI when idle or tech open; fixture diag only when tech open
        # (idle continuous Admit must not deepcopy all trials for hidden diagnostics).
        tech_open = bool(self.tech_toggle.isChecked())
        # While Stop/Cancel worker is in flight, keep chrome light — status text +
        # ActionBar only. Source of truth: worker op (not CapturePageVM.busy_op).
        stopping = self._is_finishing_worker()
        skip_heavy = bool(self._skip_heavy_chrome_once) or stopping
        if tech_open or not running:
            kpi_txt = (
                f"{t('capture.physical_distance')}: {vm.distance_input:g} {vm.distance_unit} "
                f"({vm.distance_mm:g} mm)\n"
                f"{t('capture.direction')}: {direction_txt} · DPI {vm.configured_dpi} · {method}\n"
                f"{t('capture.nets')}: dx={vm.net_counts_x} dy={vm.net_counts_y} · "
                f"{t('capture.primary_counts')}: {vm.primary_counts}\n"
                f"{t('capture.events')}: {vm.published_count} · {t('capture.devices')}: {devices} "
                f"({vm.device_count}) · {t('capture.path_quality')}: {pq} · "
                f"{t('capture.integrity')}: {integrity}{diag}"
            )
            if self.kpi_label.text() != kpi_txt:
                self.kpi_label.setText(kpi_txt)
            if tech_open and not skip_heavy:
                from mouse_dpi_tool.reporting.fixture_motion import (
                    build_fixture_motion_diagnostics,
                    format_fixture_motion_lines,
                )

                # Fingerprint via revisions only — never deepcopy all trials just to compare.
                diag_fp = (
                    REVISIONS.locale,
                    REVISIONS.trial_lifecycle,
                    REVISIONS.session_analysis,
                )
                if diag_fp != getattr(self, "_fixture_diag_fp", None):
                    COUNTERS.fixture_diag_renders += 1
                    diag_model = build_fixture_motion_diagnostics(
                        self.controller.session.presentation_trials("active")
                    )
                    diag_txt = "\n".join(format_fixture_motion_lines(diag_model, t=t))
                    if self.fixture_diag_label.text() != diag_txt:
                        self.fixture_diag_label.setText(diag_txt)
                    self._fixture_diag_fp = diag_fp
        instr = (
            t("capture.instruction_fixture")
            if vm.movement_mode == MOVEMENT_MODE_FIXTURE_VECTOR
            else t("capture.instruction")
        )
        if self.instruction.text() != instr:
            self.instruction.setText(instr)
        if self.controller.operator_issue == "APPLICATION_LOST_FOCUS" and not self.message_label.text():
            self.message_label.setText(self.controller.i18n.t("capture.focus_lost"))
        if stopping:
            # Status / ActionBar only — freeze last painted gauge/path until stop finishes.
            self._apply_capture_controls()
            locked_now = bool(self.controller.capture_navigation_locked)
            if locked_now != getattr(self, "_nav_lock_fp", None):
                self._nav_lock_fp = locked_now
                self.nav_sync_needed.emit()
            return
        self.lane.set_direction(vm.direction)
        pass_pct = float(self.controller.session.settings.get("cpi_error_pass_pct", 3.0))
        pres = self.controller.last_capture_presentation()
        if running:
            gauge_dx = float(vm.net_counts_x)
            gauge_dy = float(vm.net_counts_y)
            gauge_dpi = int(vm.configured_dpi)
            gauge_dist = float(vm.distance_mm)
            path_pts = vm.path_points
        elif pres is not None:
            gauge_dx = float(pres["net_counts_x"])
            gauge_dy = float(pres["net_counts_y"])
            gauge_dpi = int(pres.get("configured_dpi") or vm.configured_dpi)
            gauge_dist = float(pres.get("distance_mm") or vm.distance_mm)
            path_pts = tuple(pres["path_points"])
        else:
            gauge_dx = float(vm.net_counts_x)
            gauge_dy = float(vm.net_counts_y)
            gauge_dpi = int(vm.configured_dpi)
            gauge_dist = float(vm.distance_mm)
            path_pts = vm.path_points
        self.viz.set_gauge_state(
            net_dx=gauge_dx,
            net_dy=gauge_dy,
            configured_dpi=gauge_dpi,
            distance_mm=gauge_dist,
            pass_pct=pass_pct,
        )
        self.viz.set_path_points(path_pts)
        self._update_poster(live_integrity=integrity, live_pq=pq, running=running)
        # Rebuild Trial tables on lifecycle revision or bucket-size change — not every tick.
        # metrics() reads lengths without deepcopying trial payloads.
        if not skip_heavy:
            bucket_counts = self.controller.session.metrics()
            trial_fp = (
                REVISIONS.locale,
                REVISIONS.trial_lifecycle,
                bucket_counts["active_trial_count"],
                bucket_counts["rejected_trial_count"],
                bucket_counts["deleted_trial_count"],
            )
            if trial_fp != getattr(self, "_trials_fp", None):
                self.trials.refresh()
                self._trials_fp = trial_fp
        self._apply_capture_controls()
        locked_now = bool(self.controller.capture_navigation_locked)
        if locked_now != getattr(self, "_nav_lock_fp", None):
            self._nav_lock_fp = locked_now
            self.nav_sync_needed.emit()
        if self.dpi.value() != vm.configured_dpi:
            self.dpi.blockSignals(True)
            self.dpi.setValue(vm.configured_dpi)
            self.dpi.blockSignals(False)
        geo_txt = self._committed_geometry_label(vm.movement_mode)
        if self.geometry_summary.text() != geo_txt:
            self.geometry_summary.setText(geo_txt)
        idx = self.direction.findData(vm.direction)
        if idx >= 0 and self.direction.currentIndex() != idx:
            self.direction.blockSignals(True)
            self.direction.setCurrentIndex(idx)
            self.direction.blockSignals(False)

    def _clear_poster_metrics(self) -> None:
        while self.poster_metrics.count():
            item = self.poster_metrics.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._poster_metric_labels.clear()

    def _add_poster_metric(self, row: int, col: int, label: str, value: str) -> None:
        cell = QLabel(f"<b>{label}</b><br/>{value}")
        cell.setObjectName("Muted")
        cell.setTextFormat(Qt.TextFormat.RichText)
        cell.setWordWrap(True)
        self.poster_metrics.addWidget(cell, row, col)
        self._poster_metric_labels.append(cell)

    def _update_poster(
        self,
        *,
        live_integrity: str = "—",
        live_pq: str = "—",
        running: bool = False,
    ) -> None:
        t = self.controller.i18n.t
        poster = self.controller.trial_result_poster()
        if self.poster.graphicsEffect() is not None:
            self.poster.setGraphicsEffect(None)
        if not poster:
            # Ready: compact placeholder — give space to visualization workspace.
            self.poster.setVisible(False)
            self._poster_placeholder.setVisible(True)
            self._poster_placeholder.setText(t("capture.poster.empty_body"))
            self._poster_fingerprint = None
            return
        phase = str(poster.get("phase") or "admitted")
        tid = poster.get("trial_id")
        cpi = float(poster.get("measured_cpi") or 0.0)
        status = str(poster.get("status") or "—")
        mode = str(poster.get("movement_mode") or "—")
        fixture = mode == MOVEMENT_MODE_FIXTURE_VECTOR
        direction = "—" if fixture else str(poster.get("direction") or "—")
        if phase == "pending":
            if poster.get("integrity_ok"):
                integrity_metric = "OK"
            elif live_integrity and live_integrity not in {"—"}:
                integrity_metric = live_integrity
            else:
                integrity_metric = "FAIL"
            pq_metric = str(poster.get("path_quality_status") or live_pq or "—")
        elif phase == "admitted":
            integrity_metric = "OK" if poster.get("integrity_ok", True) else "FAIL"
            pq_metric = str(poster.get("path_quality_status") or "—")
        else:
            integrity_metric = live_integrity
            pq_metric = live_pq
        # Skip full metric-grid rebuild when content is unchanged (esp. live RUNNING).
        fingerprint = (
            f"{REVISIONS.locale}:{phase}:{tid}:{cpi:.4f}:{status}:{poster.get('configured_dpi')}:"
            f"{poster.get('counts_x')}:{poster.get('counts_y')}:{poster.get('primary_counts')}:"
            f"{poster.get('distance_mm')}:{pq_metric}:{integrity_metric}:{mode}:{direction}:"
            f"{running}"
        )
        if fingerprint == getattr(self, "_poster_fingerprint", None) and self.poster.isVisible():
            return
        self._clear_poster_metrics()
        self._poster_placeholder.setVisible(False)
        self.poster.setVisible(True)
        if phase == "pending":
            self.poster_title.setText(t("capture.poster.pending"))
        elif running and phase == "admitted":
            self.poster_title.setText(t("capture.poster.last_admitted").format(trial_id=tid))
        else:
            self.poster_title.setText(t("capture.poster.admitted").format(trial_id=tid))
        status_label = t(f"status.{status}", default=status)
        self.poster_cpi.setText(f"{cpi:.1f} CPI")
        self.poster_status.setText(status_label)
        err = poster.get("error_pct")
        self.poster_error.setText(
            t("capture.poster.error").format(error=f"{float(err):+.2f}")
            if err is not None
            else ""
        )
        self._add_poster_metric(0, 0, t("capture.configured_dpi"), str(poster.get("configured_dpi")))
        self._add_poster_metric(0, 1, "dx", str(poster.get("counts_x")))
        self._add_poster_metric(0, 2, "dy", str(poster.get("counts_y")))
        self._add_poster_metric(
            0, 3, t("capture.primary_counts"), str(poster.get("primary_counts"))
        )
        dist_mm = poster.get("distance_mm")
        self._add_poster_metric(1, 0, t("capture.physical_distance"), f"{dist_mm} mm")
        self._add_poster_metric(1, 1, t("capture.path_quality"), pq_metric)
        self._add_poster_metric(1, 2, t("capture.integrity"), integrity_metric)
        self._add_poster_metric(
            1, 3, t("capture.geometry"), mode if not fixture else t("geometry.fixture_vector")
        )
        if not fixture:
            self._add_poster_metric(2, 0, t("capture.direction"), direction)
        if fixture:
            self.poster_hint.setText(t("capture.poster.fixture_hint"))
        elif poster.get("vector_cpi") is not None:
            self.poster_hint.setText(
                t("capture.poster.vector_ref").format(vector_cpi=f"{float(poster['vector_cpi']):.1f}")
            )
        else:
            self.poster_hint.setText("")
        self.poster.setProperty("status", status.lower() if status else "empty")
        self.poster.style().unpolish(self.poster)
        self.poster.style().polish(self.poster)
        self._poster_fingerprint = fingerprint

    def retranslate(self) -> None:
        t = self.controller.i18n.t
        self.title.setText(t("capture.title"))
        self.subtitle.setText(t("capture.subtitle"))
        self._dpi_label.setText(t("capture.configured_dpi"))
        self._dpi_hint.setText(t("capture.configured_dpi_hint"))
        self._geometry_label.setText(t("capture.geometry"))
        self.geometry_hint.setText(t("capture.geometry_readonly_hint"))
        self._direction_label.setText(t("capture.direction"))
        self.instruction.setText(t("capture.instruction"))
        self.instruction.setMaximumWidth(comfortable_prose_max_width(self))
        self.action_bar.retranslate(t)
        self.tech_toggle.setText(t("capture.tech_details"))
        self.shortcut_hint.setText(t("capture.shortcut_hint"))
        self.procedure_hint.setText(t("capture.procedure_hint"))
        self.measure_toggle.setText(t("capture.how_to_measure"))
        self.measure_guide.setText(t("capture.how_to_measure_body"))
        if self._dpi_confirm_hint.isVisible():
            self._dpi_confirm_hint.setText(t("capture.dpi_confirmation_recommended"))
        if self.ready_banner.isVisible():
            self.ready_banner.setText(t("capture.ready_move_now"))
        self.dpi.retranslate(
            presets_label=t("capture.dpi_presets"),
            spin_tip=t("capture.dpi_spin_tip"),
            combo_tip=t("capture.dpi_preset_tip"),
        )
        tokens = self.controller.theme.tokens
        self.lane.set_endpoint_labels(start=t("capture.lane.start"), target=t("capture.lane.target"))
        self.lane.apply_tokens(tokens)
        self.viz.apply_tokens(tokens)
        # Invalidate presentation skip-caches so locale strings rewrite even when
        # Trial counts/evidence are unchanged.
        self._trials_fp = None
        self._fixture_diag_fp = None
        self._poster_fingerprint = None
        self.trials.retranslate()
        self.geometry_summary.setText(
            self._committed_geometry_label(self.controller.movement_mode)
        )
        selected = self.controller.direction
        refill_combo(
            self.direction,
            [(self.controller.i18n.direction(code), code) for code in CANONICAL_DIRECTIONS],
            selected_data=selected,
        )
        self.lane.set_direction(combo_data(self.direction, selected))
        self.refresh()


class ResultsPage(QWidget):
    go_to_capture = Signal()
    open_user_guide = Signal()

    def __init__(self, controller: AppController, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.title = QLabel()
        self.title.setObjectName("HeroTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("Muted")
        self.subtitle.setWordWrap(True)
        self.summary = QLabel()
        self.summary.setObjectName("Muted")
        self.report_btn = QPushButton()
        self.report_btn.setObjectName("PrimaryButton")
        self.report_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.report_btn.clicked.connect(self._generate_report)
        self.report_msg = QLabel()
        self.report_msg.setObjectName("Muted")
        self.report_msg.setWordWrap(True)

        self.empty_panel = QFrame()
        self.empty_panel.setObjectName("Card")
        self.empty_panel.setMaximumWidth(RESULTS_EMPTY_MAX_WIDTH)
        self.empty_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.empty_title = QLabel()
        self.empty_title.setObjectName("EmptyStateTitle")
        self.empty_title.setWordWrap(True)
        self.empty_title.setAutoFillBackground(False)
        self.empty_title.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.empty_title.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.empty_body = QLabel()
        self.empty_body.setObjectName("PassiveHelper")
        self.empty_body.setWordWrap(True)
        self.empty_go_capture = QPushButton()
        self.empty_go_capture.setObjectName("PrimaryButton")
        self.empty_go_capture.setCursor(Qt.CursorShape.PointingHandCursor)
        self.empty_go_capture.clicked.connect(self.go_to_capture.emit)
        self.empty_open_guide = QPushButton()
        self.empty_open_guide.setCursor(Qt.CursorShape.PointingHandCursor)
        self.empty_open_guide.clicked.connect(self.open_user_guide.emit)
        empty_l = QVBoxLayout(self.empty_panel)
        empty_l.setContentsMargins(28, 32, 28, 32)
        empty_l.setSpacing(12)
        empty_l.addWidget(self.empty_title)
        empty_l.addWidget(self.empty_body)
        empty_cta = QHBoxLayout()
        empty_cta.addWidget(self.empty_go_capture, 0)
        empty_cta.addWidget(self.empty_open_guide, 0)
        empty_cta.addStretch(1)
        empty_l.addLayout(empty_cta)
        # Content-height driven — do not fill the viewport with empty stretch.

        self.content_host = QWidget()
        self.v1_host = QGridLayout()
        self.v1_host.setHorizontalSpacing(12)
        self.v1_host.setVerticalSpacing(12)
        self.research_host = QHBoxLayout()
        self.findings_title = QLabel()
        self.findings_title.setObjectName("SectionTitle")
        self.evidence_title = QLabel()
        self.evidence_title.setObjectName("SectionTitle")
        self.research_title = QLabel()
        self.research_title.setObjectName("SectionTitle")
        self.research_help = QLabel()
        self.research_help.setObjectName("PassiveHelper")
        self.research_help.setWordWrap(True)
        self.groups_title = QLabel()
        self.groups_title.setObjectName("FormGroupTitle")
        self.ratios_title = QLabel()
        self.ratios_title.setObjectName("FormGroupTitle")
        self.ratios_hint = QLabel()
        self.ratios_hint.setObjectName("PassiveHelper")
        self.ratios_hint.setWordWrap(True)
        self.scale_title = QLabel()
        self.scale_title.setObjectName("FormGroupTitle")
        self.scale_body = QLabel()
        self.scale_body.setObjectName("PassiveHelper")
        self.scale_body.setWordWrap(True)
        from mouse_dpi_tool.ui.components.engineering_diagnostics import EngineeringDiagnosticsPanel

        self.eng_diag = EngineeringDiagnosticsPanel()
        self.trends_title = QLabel()
        self.trends_title.setObjectName("SectionTitle")
        self.trends_hint = QLabel()
        self.trends_hint.setObjectName("PassiveHelper")
        self.trends_hint.setWordWrap(True)

        from mouse_dpi_tool.ui.components.dpi_trend_charts import DpiTrendCharts

        self.trends = DpiTrendCharts()
        self.groups_table = self._make_table(6)
        self.ratios_table = self._make_table(6)

        header = QHBoxLayout()
        header.addWidget(self.title, 1)
        header.addWidget(self.report_btn, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        # Hierarchy: Findings → Evidence Summary → Behavior Trends → Advanced Diagnostics
        content_l = QVBoxLayout(self.content_host)
        content_l.setContentsMargins(0, 0, 0, 0)
        content_l.setSpacing(0)
        content_l.addWidget(self.summary)
        content_l.addWidget(self.report_msg)
        content_l.addSpacing(SPACE_SECTION)
        content_l.addWidget(self.findings_title)
        content_l.addSpacing(8)
        content_l.addLayout(self.v1_host)
        content_l.addSpacing(SPACE_SECTION)
        content_l.addWidget(self.evidence_title)
        content_l.addSpacing(8)
        content_l.addWidget(self.groups_title)
        content_l.addWidget(self.groups_table)
        content_l.addSpacing(12)
        content_l.addWidget(self.ratios_title)
        content_l.addWidget(self.ratios_hint)
        content_l.addWidget(self.ratios_table)
        content_l.addSpacing(12)
        content_l.addWidget(self.scale_title)
        content_l.addWidget(self.scale_body)
        content_l.addSpacing(SPACE_SECTION)
        content_l.addWidget(self.trends_title)
        content_l.addWidget(self.trends_hint)
        content_l.addWidget(self.trends)
        content_l.addSpacing(SPACE_SECTION)
        content_l.addWidget(self.eng_diag)
        content_l.addSpacing(SPACE_SECTION)
        content_l.addWidget(self.research_title)
        content_l.addWidget(self.research_help)
        content_l.addLayout(self.research_host)
        content_l.addStretch(1)

        scroll_inner = QWidget()
        scroll_l = QVBoxLayout(scroll_inner)
        scroll_l.setContentsMargins(0, 0, 0, 0)
        scroll_l.addWidget(
            self.empty_panel, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        scroll_l.addWidget(self.content_host)
        scroll.setWidget(scroll_inner)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.addLayout(header)
        root.addWidget(self.subtitle)
        root.addSpacing(12)
        root.addWidget(scroll, 1)
        self.retranslate()
        self.refresh()

    def _set_empty_mode(self, empty: bool) -> None:
        self.empty_panel.setVisible(empty)
        self.content_host.setVisible(not empty)
        if empty:
            self._clear_layout(self.v1_host)
            self._clear_layout(self.research_host)
            self.groups_table.setRowCount(0)
            self.ratios_table.setRowCount(0)
            # Avoid chart/table work while empty — clear diagnostics inputs lightly.
            self.eng_diag.set_trials([])
            self.trends.set_from_session([], {})
            self.report_btn.setEnabled(False)

    @staticmethod
    def _make_table(cols: int) -> QTableWidget:
        from PySide6.QtWidgets import QTableWidget

        from mouse_dpi_tool.ui.layout_metrics import apply_header_safe_widths

        table = QTableWidget(0, cols)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(False)
        table.setMinimumHeight(120)
        table.setHorizontalHeaderLabels([f"C{i}" for i in range(cols)])
        apply_header_safe_widths(table, refine_to_contents=False)
        return table

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                # takeAt leaves the widget as a child; hide immediately so refresh
                # cannot stack overlapping finding cards before deleteLater runs.
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def _finding_card(
        self, card_vm, *, metrics_override: dict | None = None, secondary: bool = False
    ) -> QFrame:
        from mouse_dpi_tool.reporting.chart_cards import finding_metric_rows

        card = QFrame()
        card.setObjectName("ResultPosterSecondary" if secondary else "ResultPoster")
        card.setProperty("status", str(card_vm.canonical_status).lower())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        head = QHBoxLayout()
        title = QLabel(card_vm.title)
        title.setObjectName("SectionTitle")
        title.setWordWrap(True)
        status = QLabel(card_vm.status_label)
        status.setObjectName("FindingStatus")
        status.setProperty("status", str(card_vm.canonical_status).lower())
        if secondary:
            status.setProperty("secondary", "true")
        head.addWidget(title, 1)
        head.addWidget(status, 0)
        layout.addLayout(head)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("Muted")
        layout.addWidget(sep)
        metrics = metrics_override if metrics_override is not None else (card_vm.metrics or {})
        for key, value in finding_metric_rows(
            card_vm.dimension, metrics, t=self.controller.i18n.t
        ):
            row = QHBoxLayout()
            k = QLabel(key)
            k.setObjectName("MetricKey")
            v = QLabel(value)
            v.setObjectName("MetricValue")
            v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(k, 1)
            row.addWidget(v, 0)
            layout.addLayout(row)
        help_key = {
            "accuracy": "finding.help.accuracy",
            "repeatability": "finding.help.repeatability",
            "ratio": "finding.help.ratio",
            "path_quality": "finding.help.path_quality",
        }.get(card_vm.dimension)
        if help_key:
            help_lbl = QLabel(self.controller.i18n.t(help_key))
            help_lbl.setObjectName("PassiveHelper")
            help_lbl.setWordWrap(True)
            layout.addWidget(help_lbl)
        if card_vm.issue_labels:
            issues = QLabel("; ".join(card_vm.issue_labels))
            issues.setObjectName("PassiveHelper")
            issues.setWordWrap(True)
            layout.addWidget(issues)
        layout.addStretch(1)
        card.style().unpolish(card)
        card.style().polish(card)
        status.style().unpolish(status)
        status.style().polish(status)
        return card

    def _generate_report(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        t = self.controller.i18n.t
        folder = QFileDialog.getExistingDirectory(self, t("results.report.choose_folder"))
        if not folder:
            return
        self.report_btn.setEnabled(False)
        self.report_msg.setText(t("results.report.busy"))

        class _ReportWorker(QObject):
            finished = Signal(object, object)

            def __init__(self, controller, dest: str) -> None:
                super().__init__()
                self.controller = controller
                self.dest = dest

            def run(self) -> None:
                try:
                    art = self.controller.generate_test_report(self.dest)
                    self.finished.emit(art, None)
                except Exception as exc:  # noqa: BLE001
                    self.finished.emit(None, exc)

        self._report_thread = QThread(self)
        self._report_worker = _ReportWorker(self.controller, folder)
        self._report_worker.moveToThread(self._report_thread)
        self._report_thread.started.connect(self._report_worker.run)

        def _done(art, err) -> None:
            self._report_thread.quit()
            active = int(self.controller.session.metrics().get("active_trial_count") or 0)
            self.report_btn.setEnabled(active > 0)
            if err is not None:
                if _is_method_metadata_error(err):
                    self.report_msg.setText(t("results.report.method_invalid"))
                else:
                    self.report_msg.setText(t("results.report.failed").format(error=str(err)))
                return
            self.report_msg.setText(
                t("results.report.done").format(
                    html=art.html_path.name,
                    json=art.json_path.name,
                    folder=str(art.html_path.parent),
                )
            )

        self._report_worker.finished.connect(_done)
        self._report_worker.finished.connect(self._report_worker.deleteLater)
        self._report_thread.finished.connect(self._report_thread.deleteLater)
        self._report_thread.start()

    def refresh(self) -> None:
        from PySide6.QtWidgets import QTableWidgetItem

        # Lightweight empty gate — no Session snapshot / Findings chart build.
        active_n = int(self.controller.session.metrics().get("active_trial_count") or 0)
        if active_n == 0:
            self._set_empty_mode(True)
            return

        self._set_empty_mode(False)
        self._clear_layout(self.v1_host)
        self._clear_layout(self.research_host)
        vm: ResultsPageVM = self.controller.results_viewmodel()
        snap = self.controller.session_snapshot()
        t = self.controller.i18n.t
        self.summary.setText(
            t("results.summary").format(
                trials=vm.active_trial_count,
                groups=vm.group_count,
                ratios=vm.ratio_pair_count,
            )
        )
        self.report_btn.setEnabled(vm.active_trial_count > 0)

        groups = list(snap.get("group_summaries") or [])
        settings = dict(snap.get("settings") or {})
        from mouse_dpi_tool.reporting.chart_cards import build_v1_chart_cards

        chart_models = build_v1_chart_cards(groups, settings)
        rep_counts = chart_models["repeatability"].group_status_counts or {}

        v1_primary = [
            c
            for c in vm.finding_cards
            if c.dimension in {"accuracy", "repeatability", "path_quality"}
        ]
        # Stable primary order for Results hierarchy.
        order = {"accuracy": 0, "repeatability": 1, "path_quality": 2}
        v1_primary.sort(key=lambda c: order.get(c.dimension, 99))
        v1_secondary = [c for c in vm.finding_cards if c.dimension == "ratio"]
        research = [
            c
            for c in vm.finding_cards
            if c.dimension in {"linearity", "scaling_evidence", "native_capability"}
        ]
        for i, card_vm in enumerate(v1_primary):
            override = None
            if card_vm.dimension == "repeatability" and rep_counts:
                override = {
                    **dict(card_vm.metrics or {}),
                    "groups_pass": rep_counts.get("PASS", 0),
                    "groups_warn": rep_counts.get("WARN", 0),
                    "groups_fail": rep_counts.get("FAIL", 0),
                }
            self.v1_host.addWidget(
                self._finding_card(card_vm, metrics_override=override), i // 2, i % 2
            )
        for j, card_vm in enumerate(v1_secondary):
            # Relative DPI Scaling sits slightly secondary under primary Findings.
            self.v1_host.addWidget(
                self._finding_card(card_vm, secondary=True),
                (len(v1_primary) + j) // 2,
                (len(v1_primary) + j) % 2,
            )
        for card_vm in research:
            chip = QLabel(f"{card_vm.title}: {card_vm.status_label}")
            chip.setObjectName("PassiveHelper")
            chip.setWordWrap(True)
            self.research_host.addWidget(chip)
        self.research_host.addStretch(1)
        self.research_help.setText(t("finding.help.research"))

        self.groups_table.setHorizontalHeaderLabels(
            [
                t("results.group.dpi"),
                t("results.group.trials"),
                t("results.group.avg_cpi"),
                t("results.group.max_error"),
                t("results.group.cv"),
                t("results.group.status"),
            ]
        )
        from mouse_dpi_tool.ui.layout_metrics import apply_header_safe_widths

        self.groups_table.setRowCount(len(groups))
        for r, g in enumerate(groups):
            vals = [
                str(g.get("configured_dpi")),
                str(g.get("valid_trials")),
                f"{float(g['avg_measured_cpi']):.1f}" if g.get("avg_measured_cpi") is not None else "—",
                f"{float(g['max_abs_error_pct']):.2f}" if g.get("max_abs_error_pct") is not None else "—",
                f"{float(g['cpi_cv_pct']):.4f}" if g.get("cpi_cv_pct") is not None else "—",
                t(f"status.{g.get('status')}", default=str(g.get("status") or "—")),
            ]
            for c, text in enumerate(vals):
                self.groups_table.setItem(r, c, QTableWidgetItem(text))
        apply_header_safe_widths(self.groups_table, refine_to_contents=len(groups) > 0)

        ratios = list(snap.get("ratio_analysis") or [])
        self.ratios_table.setHorizontalHeaderLabels(
            [
                t("results.ratio.from"),
                t("results.ratio.to"),
                t("results.ratio.expected"),
                t("results.ratio.measured"),
                t("results.ratio.error"),
                t("results.ratio.status"),
            ]
        )
        self.ratios_table.setRowCount(len(ratios))
        for r, row in enumerate(ratios):
            vals = [
                str(row.get("from_dpi")),
                str(row.get("to_dpi")),
                f"{float(row['expected_ratio']):.4f}" if row.get("expected_ratio") is not None else "—",
                f"{float(row['measured_ratio']):.4f}" if row.get("measured_ratio") is not None else "—",
                f"{float(row['ratio_error_pct']):+.4f}" if row.get("ratio_error_pct") is not None else "—",
                t(f"status.{row.get('status')}", default=str(row.get("status") or "—")),
            ]
            for c, text in enumerate(vals):
                self.ratios_table.setItem(r, c, QTableWidgetItem(text))
        apply_header_safe_widths(self.ratios_table, refine_to_contents=len(ratios) > 0)

        from mouse_dpi_tool.reporting.scale_pattern import (
            build_cross_dpi_scale_pattern,
            format_cross_dpi_scale_lines,
            ratio_context_from_pairs,
        )

        scale = build_cross_dpi_scale_pattern(groups)
        scale_lines = format_cross_dpi_scale_lines(
            scale,
            ratio_ctx=ratio_context_from_pairs(ratios),
            t=t,
        )
        self.scale_body.setText("\n".join(scale_lines))

        trials = list(snap.get("trials") or [])
        self.eng_diag.set_localize(t)
        self.eng_diag.set_trials(trials)
        self.eng_diag.apply_tokens(self.controller.theme.tokens)

        self.trends.set_localize(self.controller.i18n.t)
        self.trends.set_from_session(groups, settings)
        self.trends.apply_tokens(self.controller.theme.tokens)

    def retranslate(self) -> None:
        t = self.controller.i18n.t
        self.title.setText(t("results.title"))
        self.subtitle.setText(t("results.subtitle"))
        self.report_btn.setText(t("results.report.generate"))
        self.empty_title.setText(t("results.empty_title"))
        self.empty_body.setText(t("results.empty_body"))
        self.empty_go_capture.setText(t("results.empty_go_capture"))
        self.empty_open_guide.setText(t("results.empty_open_guide"))
        self.findings_title.setText(t("results.findings_title"))
        self.evidence_title.setText(t("results.evidence_title"))
        self.research_title.setText(t("results.research"))
        self.groups_title.setText(t("results.groups_title"))
        self.ratios_title.setText(t("results.ratios_title"))
        self.ratios_hint.setText(t("results.ratios_hint"))
        self.scale_title.setText(t("results.scale_pattern_title"))
        self.trends_title.setText(t("results.trends_title"))
        self.trends_hint.setText(t("results.trends_hint"))
        self.eng_diag.set_localize(t)
        self.refresh()


class SettingsPage(QWidget):
    def __init__(self, controller: AppController, on_prefs_changed, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.on_prefs_changed = on_prefs_changed
        self.title = QLabel()
        self.title.setObjectName("HeroTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("Muted")
        self.subtitle.setWordWrap(True)
        self.locale = QComboBox()
        self._theme_label = QLabel()
        self._locale_label = QLabel()
        style_form_label(self._theme_label)
        style_form_label(self._locale_label)
        self._theme_buttons: dict[str, QPushButton] = {}
        seg = QFrame()
        seg.setObjectName("SegmentGroup")
        seg_l = QHBoxLayout(seg)
        seg_l.setContentsMargins(3, 3, 3, 3)
        seg_l.setSpacing(2)
        for mode in THEME_MODES:
            btn = QPushButton()
            btn.setObjectName("Segment")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, m=mode: self._theme_picked(m))
            self._theme_buttons[mode] = btn
            seg_l.addWidget(btn)
        self._segment = seg
        form = QFormLayout()
        configure_form_layout(form)
        form.addRow(self._theme_label, seg)
        form.addRow(self._locale_label, self.locale)
        self.guide_btn = QPushButton()
        self.guide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.guide_btn.clicked.connect(self._open_guide)
        self._form_card = _settings_card()
        self._form_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        card_l = QVBoxLayout(self._form_card)
        card_l.setContentsMargins(20, 20, 20, 20)
        card_l.setSpacing(SPACE_FORM_WITHIN)
        card_l.addLayout(form)
        card_l.addSpacing(SPACE_FORM_GROUP)
        card_l.addWidget(self.guide_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self._form_card.setMaximumWidth(SETTINGS_PANEL_MAX_WIDTH)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.addWidget(self.title)
        root.addWidget(self.subtitle)
        root.addSpacing(12)
        form_row = QHBoxLayout()
        form_row.setContentsMargins(0, 0, 0, 0)
        # Expand up to Settings panel max; trailing stretch absorbs surplus desktop width.
        form_row.addWidget(self._form_card, 1, Qt.AlignmentFlag.AlignTop)
        form_row.addStretch(1)
        root.addLayout(form_row)
        root.addStretch(1)
        self.locale.currentIndexChanged.connect(self._locale_changed)
        self.retranslate()

    def _open_guide(self) -> None:
        from mouse_dpi_tool.ui.components.user_guide_dialog import UserGuideDialog

        UserGuideDialog(self.controller, self).exec()

    def _theme_picked(self, mode: str) -> None:
        self.controller.set_theme(mode)
        self._sync_theme_buttons()
        self.on_prefs_changed()

    def _sync_theme_buttons(self) -> None:
        selected = str(self.controller.preferences.get("theme", "system"))
        for mode, btn in self._theme_buttons.items():
            on = mode == selected
            btn.setProperty("selected", "true" if on else "false")
            btn.setChecked(on)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _locale_changed(self, _index: int = 0) -> None:
        locale = combo_data(self.locale, "en-US")
        self.controller.set_locale(locale)
        self.on_prefs_changed()

    def retranslate(self) -> None:
        t = self.controller.i18n.t
        self.title.setText(t("settings.title"))
        self.subtitle.setText(t("settings.subtitle"))
        self._theme_label.setText(t("settings.theme"))
        self._locale_label.setText(t("settings.locale"))
        style_form_label(self._theme_label)
        style_form_label(self._locale_label)
        self.guide_btn.setText(t("help.guide.open"))
        self._form_card.setMaximumWidth(SETTINGS_PANEL_MAX_WIDTH)
        for mode, btn in self._theme_buttons.items():
            btn.setText(self.controller.i18n.theme_label(mode))
        self._sync_theme_buttons()
        locale_selected = str(self.controller.preferences.get("locale", "en-US"))
        refill_combo(
            self.locale,
            [(LOCALE_DISPLAY_NAMES[code], code) for code in SUPPORTED_LOCALES],
            selected_data=locale_selected,
        )
