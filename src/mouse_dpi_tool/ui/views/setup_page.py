"""Setup page — operator draft editor (Phase 1.5 + Phase 2 + Phase 3 composition)."""

from __future__ import annotations

from dataclasses import replace as dc_replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from mouse_dpi_tool.contracts.measurement_method import (
    CANONICAL_MEASUREMENT_METHODS,
    is_canonical_measurement_method,
)
from mouse_dpi_tool.measurement.distance import distance_to_mm
from mouse_dpi_tool.ui.components.combo import combo_data, refill_combo
from mouse_dpi_tool.ui.components.geometry_tiles import GeometryTileGroup
from mouse_dpi_tool.ui.controllers import AppController
from mouse_dpi_tool.ui.layout_metrics import (
    SPACE_FORM_GROUP,
    SPACE_FORM_WITHIN,
    SPACE_HELPER_AFTER,
    SETUP_TWO_COLUMN_MIN_WIDTH,
    SETUP_WORKSPACE_MAX_WIDTH,
    configure_form_layout,
    style_form_label,
)
from mouse_dpi_tool.ui.setup_draft import (
    ApplyStatus,
    SetupDraft,
    apply_setup_draft,
    is_operator_dirty,
    load_committed_snapshot,
    reconcile_stale_locked_draft,
)


def _card() -> QFrame:
    """Intentional Setup work surface. Internal section panels stay transparent."""
    frame = QFrame()
    frame.setObjectName("Card")
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    return frame


def _section_panel() -> QWidget:
    """Structural layout wrapper only — must not paint a nested slab."""
    panel = QWidget()
    panel.setObjectName("TransparentSurface")
    panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    panel.setAutoFillBackground(False)
    return panel


class SetupPage(QWidget):
    """SetupPage-owned draft. Ordinary refresh must not wipe unapplied edits."""

    def __init__(self, controller: AppController, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._draft: SetupDraft = load_committed_snapshot(controller)
        self._unit_code = str(self._draft.distance_unit or "mm")
        self._method_recovery_pending = False
        self._pushing = False
        self._two_column = True

        self.title = QLabel()
        self.title.setObjectName("HeroTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("Muted")
        self.subtitle.setWordWrap(True)
        self.vendor = QLineEdit()
        self.model = QLineEdit()
        self.method = QComboBox()
        self.method.setEditable(False)
        self.ctx_notes = QLineEdit()
        self.distance = QDoubleSpinBox()
        self.distance.setDecimals(6)
        self.distance.setRange(0.000001, 1_000_000.0)
        self.distance.setSingleStep(1.0)
        self.unit = QComboBox()
        self._vendor_label = QLabel()
        self._model_label = QLabel()
        self._method_label = QLabel()
        self._ctx_notes_label = QLabel()
        self._distance_label = QLabel()
        self._unit_label = QLabel()
        self._geometry_label = QLabel()
        self.geometry = GeometryTileGroup()
        self.geometry.currentChanged.connect(self._on_geometry_changed)
        self._accuracy_label = QLabel()
        self.accuracy = QComboBox()
        self.accuracy.currentIndexChanged.connect(self._on_accuracy_changed)
        self.accuracy_help = QLabel()
        self.accuracy_help.setObjectName("PassiveHelper")
        self.accuracy_help.setWordWrap(True)
        self.accuracy_lock = QLabel()
        self.accuracy_lock.setObjectName("Muted")
        self.accuracy_lock.setWordWrap(True)
        self.apply_btn = QPushButton()
        self.apply_btn.setObjectName("PrimaryButton")
        self.apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_btn.clicked.connect(self._apply)
        self.revert_btn = QPushButton()
        self.revert_btn.clicked.connect(self._revert)
        self.message_label = QLabel()
        self.message_label.setObjectName("Muted")
        self.message_label.setWordWrap(True)
        self.distance_mm_preview = QLabel()
        self.distance_mm_preview.setObjectName("PassiveHelper")
        self.distance_mm_preview.setWordWrap(True)
        self.distance_unit_hint = QLabel()
        self.distance_unit_hint.setObjectName("PassiveHelper")
        self.distance_unit_hint.setWordWrap(True)
        self._group_dut = QLabel()
        self._group_dut.setObjectName("FormGroupTitle")
        self._group_meas = QLabel()
        self._group_meas.setObjectName("FormGroupTitle")
        self._group_notes = QLabel()
        self._group_notes.setObjectName("FormGroupTitle")
        for lbl in (
            self._vendor_label,
            self._model_label,
            self._method_label,
            self._distance_label,
            self._geometry_label,
            self._accuracy_label,
            self._ctx_notes_label,
        ):
            style_form_label(lbl)

        dut_form = QFormLayout()
        configure_form_layout(dut_form)
        dut_form.addRow(self._vendor_label, self.vendor)
        dut_form.addRow(self._model_label, self.model)

        dist_block = QWidget()
        dist_v = QVBoxLayout(dist_block)
        dist_v.setContentsMargins(0, 0, 0, 0)
        dist_v.setSpacing(6)
        dist_row = QHBoxLayout()
        dist_row.setContentsMargins(0, 0, 0, 0)
        dist_row.setSpacing(8)
        self.distance.setMinimumWidth(120)
        dist_row.addWidget(self.distance, 0)
        dist_row.addWidget(self.unit, 0)
        dist_row.addStretch(1)
        dist_v.addLayout(dist_row)
        dist_v.addWidget(self.distance_mm_preview)
        dist_v.addSpacing(SPACE_HELPER_AFTER)
        dist_v.addWidget(self.distance_unit_hint)

        meas_form = QFormLayout()
        configure_form_layout(meas_form)
        meas_form.addRow(self._method_label, self.method)
        meas_form.addRow(self._distance_label, dist_block)
        meas_form.addRow(self._geometry_label, self.geometry)
        meas_form.addRow(self._accuracy_label, self.accuracy)
        meas_form.addRow("", self.accuracy_help)
        meas_form.addRow("", self.accuracy_lock)

        notes_form = QFormLayout()
        configure_form_layout(notes_form)
        notes_form.addRow(self._ctx_notes_label, self.ctx_notes)

        self._dut_panel = _section_panel()
        dut_l = QVBoxLayout(self._dut_panel)
        dut_l.setContentsMargins(0, 0, 0, 0)
        dut_l.setSpacing(0)
        dut_l.addWidget(self._group_dut)
        dut_l.addSpacing(SPACE_FORM_WITHIN)
        dut_l.addLayout(dut_form)
        dut_l.addStretch(1)

        self._meas_panel = _section_panel()
        meas_l = QVBoxLayout(self._meas_panel)
        meas_l.setContentsMargins(0, 0, 0, 0)
        meas_l.setSpacing(0)
        meas_l.addWidget(self._group_meas)
        meas_l.addSpacing(SPACE_FORM_WITHIN)
        meas_l.addLayout(meas_form)

        self._top_band = QWidget()
        self._top_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._top_band)
        self._top_layout.setContentsMargins(0, 0, 0, 0)
        self._top_layout.setSpacing(SPACE_FORM_GROUP)
        self._top_layout.addWidget(self._dut_panel, 2)
        self._top_layout.addWidget(self._meas_panel, 3)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(12)
        actions.addStretch(1)
        actions.addWidget(self.revert_btn, 0)
        actions.addWidget(self.apply_btn, 0)

        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._top_band)
        body.addSpacing(SPACE_FORM_GROUP)
        body.addWidget(self._group_notes)
        body.addSpacing(SPACE_FORM_WITHIN)
        body.addLayout(notes_form)
        body.addSpacing(SPACE_FORM_GROUP)
        body.addLayout(actions)
        body.addWidget(self.message_label)

        self._form_card = _card()
        # Expanding horizontally so the card consumes the composition band up to max.
        self._form_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        card_layout = QVBoxLayout(self._form_card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(0)
        card_layout.addLayout(body)
        self._form_card.setMaximumWidth(SETUP_WORKSPACE_MAX_WIDTH)

        # Vertical AlignTop only — do not PinLeft+stretch which keeps Preferred near sizeHint.
        scroll_inner = QWidget()
        scroll_row = QHBoxLayout(scroll_inner)
        scroll_row.setContentsMargins(0, 0, 0, 0)
        scroll_row.setSpacing(0)
        scroll_row.addWidget(self._form_card, 1, Qt.AlignmentFlag.AlignTop)
        scroll_row.addStretch(0)

        self._setup_scroll = QScrollArea()
        self._setup_scroll.setObjectName("SetupScroll")
        self._setup_scroll.setWidgetResizable(True)
        self._setup_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._setup_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._setup_scroll.setWidget(scroll_inner)
        self._scroll_row = scroll_row

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.addWidget(self.title)
        root.addWidget(self.subtitle)
        root.addSpacing(12)
        root.addWidget(self._setup_scroll, 1)

        self.unit.currentIndexChanged.connect(self._on_unit_changed)
        self.distance.valueChanged.connect(self._on_distance_changed)
        self.vendor.textChanged.connect(self._on_text_field_changed)
        self.model.textChanged.connect(self._on_text_field_changed)
        self.ctx_notes.textChanged.connect(self._on_text_field_changed)
        self.method.currentIndexChanged.connect(self._on_method_changed)

        self.retranslate()
        self.load_committed_into_editor()

    # --- composition -----------------------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_setup_composition()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._apply_setup_composition()

    def _apply_setup_composition(self) -> None:
        self._form_card.setMaximumWidth(SETUP_WORKSPACE_MAX_WIDTH)
        avail = int(self._setup_scroll.viewport().width())
        if avail <= 0:
            return
        # Expand into available logical width up to workspace max.
        if avail > SETUP_WORKSPACE_MAX_WIDTH:
            self._scroll_row.setStretch(0, 0)
            self._scroll_row.setStretch(1, 1)
            # Lock band width so trailing stretch cannot keep the card near sizeHint.
            self._form_card.setMinimumWidth(SETUP_WORKSPACE_MAX_WIDTH)
        else:
            self._scroll_row.setStretch(0, 1)
            self._scroll_row.setStretch(1, 0)
            self._form_card.setMinimumWidth(0)

        two_col = avail >= SETUP_TWO_COLUMN_MIN_WIDTH
        self._two_column = two_col
        direction = (
            QBoxLayout.Direction.LeftToRight
            if two_col
            else QBoxLayout.Direction.TopToBottom
        )
        if self._top_layout.direction() != direction:
            self._top_layout.setDirection(direction)
        # ~35–40% DUT / 60–65% Measurement when side-by-side.
        self._top_layout.setStretch(0, 2 if two_col else 0)
        self._top_layout.setStretch(1, 3 if two_col else 0)
        # Outer breakpoint owns readability — no brittle ch-based panel floors.
        self._dut_panel.setMinimumWidth(0)
        self._meas_panel.setMinimumWidth(0)

    # --- draft ownership -------------------------------------------------

    def load_committed_into_editor(self) -> None:
        """Explicit editor load from Session truth (init / Revert / successful Apply)."""
        self._draft = load_committed_snapshot(self.controller)
        method = self._draft.method
        if not is_canonical_measurement_method(method):
            self._draft = dc_replace(self._draft, method="unknown")
            self._method_recovery_pending = True
            self.message_label.setText(self.controller.i18n.t("setup.method_recovered"))
        else:
            self._method_recovery_pending = False
        self._push_draft_to_widgets()
        self._update_lock_chrome()
        self._sync_action_enabled()

    def refresh(self) -> None:
        """Ordinary presentation refresh — preserve operator draft."""
        self.refresh_presentation()

    def refresh_presentation(self) -> None:
        committed = load_committed_snapshot(self.controller)
        recon = reconcile_stale_locked_draft(self._draft, committed, self.controller)
        if recon.restored_fields:
            self._draft = recon.draft
            self._push_draft_to_widgets()
            if recon.notice:
                self.message_label.setText(recon.notice)
        self._update_lock_chrome()
        self._update_distance_mm_preview()
        self._sync_action_enabled()
        self._apply_setup_composition()

    def _push_draft_to_widgets(self) -> None:
        self._pushing = True
        try:
            d = self._draft
            self.vendor.setText(d.vendor)
            self.model.setText(d.model)
            self.ctx_notes.setText(d.ctx_notes)
            midx = self.method.findData(d.method)
            if midx >= 0 and self.method.currentIndex() != midx:
                self.method.setCurrentIndex(midx)
            self.distance.setValue(float(d.distance_input))
            self._unit_code = str(d.distance_unit)
            uidx = self.unit.findData(self._unit_code)
            if uidx >= 0 and self.unit.currentIndex() != uidx:
                self.unit.setCurrentIndex(uidx)
            self.geometry.set_current(d.movement_mode, emit=False)
            aidx = self.accuracy.findData(d.accuracy_profile)
            if aidx >= 0 and self.accuracy.currentIndex() != aidx:
                self.accuracy.setCurrentIndex(aidx)
            self._update_distance_mm_preview()
            self._update_accuracy_help()
        finally:
            self._pushing = False

    def _pull_widgets_to_draft(self) -> None:
        if self._pushing:
            return
        self._draft = dc_replace(
            self._draft,
            vendor=self.vendor.text().strip(),
            model=self.model.text().strip(),
            method=combo_data(self.method, self._draft.method),
            distance_input=float(self.distance.value()),
            distance_unit=combo_data(self.unit, self._unit_code),
            movement_mode=self.geometry.current(),
            accuracy_profile=combo_data(self.accuracy, self._draft.accuracy_profile),
            ctx_notes=self.ctx_notes.text().strip(),
        )

    def _sync_action_enabled(self) -> None:
        committed = load_committed_snapshot(self.controller)
        dirty = is_operator_dirty(self._draft, committed)
        self.apply_btn.setEnabled(dirty)
        self.revert_btn.setEnabled(dirty)

    def _update_lock_chrome(self) -> None:
        locked = self.controller.measurement_config_locked
        accuracy_locked = self.controller.accuracy_criterion_locked
        self.distance.setEnabled(not locked)
        self.unit.setEnabled(not locked)
        self.geometry.set_group_enabled(not locked)
        self.accuracy.setEnabled(not locked and not accuracy_locked)
        self.accuracy_lock.setText(
            (
                f"🔒 {self.controller.i18n.t('setup.accuracy_locked_short')} "
                f"{self.controller.i18n.t('setup.accuracy_locked')}"
            )
            if accuracy_locked
            else ""
        )
        lock_msg = self.controller.i18n.t("setup.measurement_locked")
        if locked:
            self.message_label.setText(lock_msg)
        elif self.message_label.text() == lock_msg:
            self.message_label.setText("")
        elif self._method_recovery_pending:
            self.message_label.setText(self.controller.i18n.t("setup.method_recovered"))

    def _update_accuracy_help(self) -> None:
        profile = self._draft.accuracy_profile
        self.accuracy_help.setText(
            self.controller.i18n.t(f"setup.accuracy.help.{profile}")
        )

    def _update_distance_mm_preview(self) -> None:
        t = self.controller.i18n.t
        try:
            mm = distance_to_mm(float(self._draft.distance_input), self._draft.distance_unit)
        except (TypeError, ValueError):
            mm = 0.0
        self.distance_mm_preview.setText(
            t("setup.physical_mm_preview").format(mm=f"{mm:g}")
        )

    # --- editors ---------------------------------------------------------

    def _on_text_field_changed(self, _text: str = "") -> None:
        if self._pushing:
            return
        self._pull_widgets_to_draft()
        self._sync_action_enabled()

    def _on_method_changed(self, _index: int = 0) -> None:
        if self._pushing:
            return
        self._pull_widgets_to_draft()
        self._sync_action_enabled()

    def _on_distance_changed(self, _value: float = 0.0) -> None:
        if self._pushing:
            return
        self._pull_widgets_to_draft()
        self._update_distance_mm_preview()
        self._sync_action_enabled()

    def _on_unit_changed(self, _index: int = 0) -> None:
        if self._pushing:
            return
        new_unit = combo_data(self.unit, self._unit_code)
        if new_unit == self._unit_code:
            self._sync_action_enabled()
            return
        # Unit B: keep typed number; reinterpret under new unit.
        self._unit_code = new_unit
        self._pull_widgets_to_draft()
        self._update_distance_mm_preview()
        t = self.controller.i18n.t
        self.message_label.setText(
            t("setup.unit_keep_number_hint").format(
                value=f"{float(self.distance.value()):g}",
                unit=self.controller.i18n.unit(new_unit),
            )
        )
        self._sync_action_enabled()

    def _on_geometry_changed(self, _mode: str = "") -> None:
        if self._pushing:
            return
        if self.controller.measurement_config_locked:
            # Restore tile to draft (which reconcile may have fixed).
            self.refresh_presentation()
            return
        self._pull_widgets_to_draft()
        self._sync_action_enabled()

    def _on_accuracy_changed(self, _index: int = 0) -> None:
        if self._pushing:
            return
        if self.controller.accuracy_criterion_locked or self.controller.measurement_config_locked:
            self.refresh_presentation()
            return
        self._pull_widgets_to_draft()
        self._update_accuracy_help()
        self._sync_action_enabled()

    def _revert(self) -> None:
        self.message_label.setText("")
        self.load_committed_into_editor()

    def _apply(self) -> None:
        self._pull_widgets_to_draft()
        committed = load_committed_snapshot(self.controller)
        if not is_operator_dirty(self._draft, committed):
            self.message_label.setText("")
            self._sync_action_enabled()
            return
        result = apply_setup_draft(self.controller, self._draft, committed=committed)
        t = self.controller.i18n.t
        if result.status is ApplyStatus.PREFLIGHT_REJECTED:
            reason = result.issues[0].reason if result.issues else t("setup.apply_failed")
            self.message_label.setText(reason)
            self.refresh_presentation()
            return
        if result.status in {
            ApplyStatus.COMMIT_FAILED_RESTORED,
            ApplyStatus.COMMIT_FAILED_PARTIAL,
        }:
            self.message_label.setText(result.error or t("setup.apply_failed"))
            self.load_committed_into_editor()
            return
        unit = self._draft.distance_unit
        dist = float(self._draft.distance_input)
        mm = distance_to_mm(dist, unit)
        self.message_label.setText(
            t("setup.applied_with_mm").format(
                distance=f"{dist:g}",
                unit=self.controller.i18n.unit(unit),
                mm=f"{mm:g}",
            )
        )
        self.load_committed_into_editor()

    def retranslate(self) -> None:
        t = self.controller.i18n.t
        self.title.setText(t("setup.title"))
        self.subtitle.setText(t("setup.subtitle"))
        self._vendor_label.setText(t("setup.vendor"))
        self._model_label.setText(t("setup.model"))
        self._method_label.setText(t("setup.method"))
        self._ctx_notes_label.setText(t("setup.notes_deviations"))
        self._distance_label.setText(t("setup.distance"))
        self._unit_label.setText(t("setup.unit"))
        self.distance_unit_hint.setText(t("setup.unit_keep_number_help"))
        self._group_dut.setText(t("setup.group.dut"))
        self._group_meas.setText(t("setup.group.measurement"))
        self._group_notes.setText(t("setup.group.notes"))
        self._geometry_label.setText(t("setup.geometry"))
        self._accuracy_label.setText(t("setup.accuracy"))
        self.apply_btn.setText(t("setup.apply"))
        self.revert_btn.setText(t("setup.revert"))
        self.geometry.retranslate(
            fixture_title=t("geometry.fixture_vector"),
            fixture_sub=t("geometry.tile.fixture_sub"),
            axis_title=t("geometry.directional_axis"),
            axis_sub=t("geometry.tile.axis_sub"),
        )
        for lbl in (
            self._vendor_label,
            self._model_label,
            self._method_label,
            self._distance_label,
            self._geometry_label,
            self._accuracy_label,
            self._ctx_notes_label,
        ):
            style_form_label(lbl)
        # Preserve draft selection while refreshing display strings.
        refill_combo(
            self.unit,
            [
                (self.controller.i18n.unit("mm"), "mm"),
                (self.controller.i18n.unit("cm"), "cm"),
                (self.controller.i18n.unit("inch"), "inch"),
            ],
            selected_data=self._draft.distance_unit,
        )
        refill_combo(
            self.method,
            [(t(f"method.{code}"), code) for code in CANONICAL_MEASUREMENT_METHODS],
            selected_data=self._draft.method,
        )
        refill_combo(
            self.accuracy,
            [
                (t("setup.accuracy.strict"), "FIELD_STRICT"),
                (t("setup.accuracy.medium"), "FIELD_MEDIUM"),
                (t("setup.accuracy.lenient"), "FIELD_LENIENT"),
            ],
            selected_data=self._draft.accuracy_profile,
        )
        # Labels/combos updated — keep draft values in editors (do not load committed).
        self._push_draft_to_widgets()
        self._update_lock_chrome()
        self._sync_action_enabled()
        self._apply_setup_composition()
