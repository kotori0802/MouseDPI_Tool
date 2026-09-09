"""Trial lifecycle workspace — presentation only; Session Domain is authoritative."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mouse_dpi_tool.reporting.html_report import accuracy_criterion_lines
from mouse_dpi_tool.ui.controllers import (
    MOVEMENT_MODE_FIXTURE_VECTOR,
    AppController,
)
from mouse_dpi_tool.ui.layout_metrics import (
    SPACE_CAPTURE_FILTER_GAP,
    SPACE_CAPTURE_SUMMARY_GAP,
    apply_combo_content_min_width,
    apply_header_safe_widths,
    style_form_label,
)
from mouse_dpi_tool.ui.presentation_invalidation import COUNTERS, REVISIONS

_BUCKETS = ("active", "rejected", "deleted")

_SORT_NEWEST = "newest"
_SORT_OLDEST = "oldest"
_SORT_DPI_ASC = "dpi_asc"
_SORT_DPI_DESC = "dpi_desc"
_SORT_ERROR = "abs_error"
_SORT_STATUS = "status"

_STATUS_RANK = {
    "FAIL": 0,
    "WARN": 1,
    "PASS": 2,
    "NOT_EVALUATED": 3,
    "NOT_TESTED": 4,
}


class _NumericItem(QTableWidgetItem):
    def __lt__(self, other: QTableWidgetItem) -> bool:  # type: ignore[override]
        try:
            a = self.data(Qt.ItemDataRole.UserRole)
            b = other.data(Qt.ItemDataRole.UserRole)
            if a is not None and b is not None:
                return float(a) < float(b)
        except (TypeError, ValueError):
            pass
        return super().__lt__(other)


_FLEX_COLUMN = 2  # Geometry — absorbs unused viewport width without bloating Direction


def _apply_trial_table_widths(table: QTableWidget, *, refine_to_contents: bool) -> None:
    """Header-safe mins + one flexible Geometry column (not stretch-last Direction)."""
    apply_header_safe_widths(table, refine_to_contents=refine_to_contents)
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    for col in range(table.columnCount()):
        if col == _FLEX_COLUMN:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        else:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)


class TrialWorkspace(QWidget):
    """Active / Rejected / Deleted Trial tables + Session summary."""

    changed = Signal()

    def __init__(self, controller: AppController, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TrialWorkspace")
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.controller = controller
        self._dpi_filter: int | None = None
        self._sort_mode = _SORT_NEWEST

        self.summary = QLabel()
        self.summary.setObjectName("Muted")
        self.summary.setWordWrap(True)

        self._dpi_label = QLabel()
        style_form_label(self._dpi_label)
        self.dpi_filter = QComboBox()
        self.dpi_filter.currentIndexChanged.connect(self._on_dpi_filter)

        self._sort_label = QLabel()
        style_form_label(self._sort_label)
        self.sort_combo = QComboBox()
        self.sort_combo.currentIndexChanged.connect(self._on_sort)

        self.new_session_btn = QPushButton()
        self.new_session_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_session_btn.clicked.connect(self._on_new_session)

        self.reject_btn = QPushButton()
        self.restore_btn = QPushButton()
        self.delete_btn = QPushButton()
        for btn in (self.reject_btn, self.restore_btn, self.delete_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reject_btn.clicked.connect(lambda: self._act("reject"))
        self.restore_btn.clicked.connect(lambda: self._act("restore"))
        self.delete_btn.clicked.connect(lambda: self._act("delete"))

        self.message = QLabel()
        self.message.setObjectName("Muted")
        self.message.setWordWrap(True)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("TrialTabs")
        self.tables: dict[str, QTableWidget] = {}
        for bucket in _BUCKETS:
            table = QTableWidget(0, 9)
            table.setObjectName("TrialTable")
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSortingEnabled(False)
            table.verticalHeader().setVisible(False)
            table.setAlternatingRowColors(True)
            table.itemSelectionChanged.connect(self._sync_actions)
            self.tables[bucket] = table
            self.tabs.addTab(table, bucket)
            # Placeholder headers so empty cold-start can size before retranslate.
            table.setHorizontalHeaderLabels(
                ["Trial #", "DPI", "Geometry", "Distance", "CPI", "Error", "Status", "PQ", "Dir"]
            )
            _apply_trial_table_widths(table, refine_to_contents=False)
        self.tabs.currentChanged.connect(self._sync_actions)

        filters = QHBoxLayout()
        filters.setContentsMargins(0, 0, 0, 0)
        filters.setSpacing(8)
        filters.addWidget(self._dpi_label)
        filters.addWidget(self.dpi_filter)
        filters.addSpacing(12)
        filters.addWidget(self._sort_label)
        filters.addWidget(self.sort_combo)
        filters.addStretch(1)
        filters.addWidget(self.new_session_btn)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.addWidget(self.reject_btn)
        actions.addWidget(self.restore_btn)
        actions.addWidget(self.delete_btn)
        actions.addStretch(1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 12, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.summary)
        root.addSpacing(SPACE_CAPTURE_SUMMARY_GAP)
        root.addLayout(filters)
        root.addSpacing(SPACE_CAPTURE_FILTER_GAP)
        root.addWidget(self.tabs, 1)
        root.addSpacing(8)
        root.addLayout(actions)
        root.addWidget(self.message)
        self.setMinimumHeight(220)

    def _bucket(self) -> str:
        return _BUCKETS[max(0, self.tabs.currentIndex())]

    def _selected_trial_id(self) -> int | None:
        table = self.tables[self._bucket()]
        rows = table.selectionModel().selectedRows()
        if not rows:
            return None
        item = table.item(rows[0].row(), 0)
        if item is None:
            return None
        try:
            return int(item.data(Qt.ItemDataRole.UserRole))
        except (TypeError, ValueError):
            return None

    def _on_dpi_filter(self, _index: int = 0) -> None:
        data = self.dpi_filter.currentData()
        self._dpi_filter = int(data) if data not in (None, "") else None
        self.refresh()

    def _on_sort(self, _index: int = 0) -> None:
        data = self.sort_combo.currentData()
        self._sort_mode = str(data or _SORT_NEWEST)
        self.refresh()

    def _sync_actions(self, *_args) -> None:
        bucket = self._bucket()
        has = self._selected_trial_id() is not None
        self.reject_btn.setVisible(bucket == "active")
        self.restore_btn.setVisible(bucket == "rejected")
        self.delete_btn.setVisible(bucket in {"active", "rejected"})
        self.reject_btn.setEnabled(bucket == "active" and has)
        self.restore_btn.setEnabled(bucket == "rejected" and has)
        self.delete_btn.setEnabled(bucket in {"active", "rejected"} and has)

    def _act(self, op: str) -> None:
        tid = self._selected_trial_id()
        if tid is None:
            self.message.setText(self.controller.i18n.t("trials.select_one"))
            return
        try:
            if op == "reject":
                self.controller.reject_trial(tid)
            elif op == "restore":
                self.controller.restore_rejected_trial(tid)
            elif op == "delete":
                self.controller.delete_trial(tid, reason="operator_archive")
            self.message.setText("")
        except Exception as exc:  # noqa: BLE001
            self.message.setText(str(exc))
        self.refresh()
        self.changed.emit()

    def _on_new_session(self) -> None:
        summary = self.controller.session_trial_summary()
        has_evidence = bool(
            summary["active_trial_count"]
            or summary["rejected_trial_count"]
            or summary["deleted_trial_count"]
        )
        if has_evidence:
            answer = QMessageBox.question(
                self,
                self.controller.i18n.t("trials.new_session"),
                self.controller.i18n.t("trials.new_session_confirm"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            self.controller.new_test_session(keep_dut=True, keep_setup=True)
            self.message.setText(self.controller.i18n.t("trials.new_session_done"))
        except Exception as exc:  # noqa: BLE001
            self.message.setText(str(exc))
        self.refresh()
        self.changed.emit()

    def _sorted_trials(self, trials: list[dict]) -> list[dict]:
        mode = self._sort_mode

        def tid(row: dict) -> int:
            return int(row.get("trial_id") or 0)

        def dpi(row: dict) -> int:
            return int(row.get("configured_dpi") or 0)

        def abs_err(row: dict) -> float:
            try:
                return abs(float(row.get("error_pct") or 0.0))
            except (TypeError, ValueError):
                return -1.0

        def status_key(row: dict) -> tuple[int, int]:
            st = str(row.get("status") or row.get("measurement_status") or "").upper()
            return (_STATUS_RANK.get(st, 9), -tid(row))

        if mode == _SORT_OLDEST:
            return sorted(trials, key=tid)
        if mode == _SORT_DPI_ASC:
            return sorted(trials, key=lambda r: (dpi(r), -tid(r)))
        if mode == _SORT_DPI_DESC:
            return sorted(trials, key=lambda r: (-dpi(r), -tid(r)))
        if mode == _SORT_ERROR:
            return sorted(trials, key=lambda r: (-abs_err(r), -tid(r)))
        if mode == _SORT_STATUS:
            return sorted(trials, key=status_key)
        # newest default
        return sorted(trials, key=tid, reverse=True)

    def retranslate(self) -> None:
        # Locale bump is owned by MainWindow.apply_presentation; ensure table
        # content fingerprints include current locale even if called alone.
        t = self.controller.i18n.t
        self.tabs.setTabText(0, t("trials.tab.active"))
        self.tabs.setTabText(1, t("trials.tab.rejected"))
        self.tabs.setTabText(2, t("trials.tab.deleted"))
        self.reject_btn.setText(t("trials.reject"))
        self.restore_btn.setText(t("trials.restore"))
        self.delete_btn.setText(t("trials.delete"))
        self.new_session_btn.setText(t("trials.new_session"))
        self._dpi_label.setText(t("trials.filter.dpi"))
        self._sort_label.setText(t("trials.sort.label"))
        style_form_label(self._dpi_label)
        style_form_label(self._sort_label)
        headers = [
            t("trials.col.id"),
            t("trials.col.dpi"),
            t("trials.col.geometry"),
            t("trials.col.distance"),
            t("trials.col.cpi"),
            t("trials.col.error"),
            t("trials.col.status"),
            t("trials.col.path_quality"),
            t("trials.col.direction"),
        ]
        # Explicit sort indicator on Trial # for newest/oldest.
        if self._sort_mode == _SORT_NEWEST:
            headers[0] = t("trials.col.id_desc")
        elif self._sort_mode == _SORT_OLDEST:
            headers[0] = t("trials.col.id_asc")
        for table in self.tables.values():
            table.setHorizontalHeaderLabels(headers)
            table._headers_dirty = True
            _apply_trial_table_widths(table, refine_to_contents=table.rowCount() > 0)
            table._headers_dirty = False
        apply_combo_content_min_width(self.dpi_filter)
        apply_combo_content_min_width(self.sort_combo)
        self.sort_combo.blockSignals(True)
        selected = self.sort_combo.currentData() or self._sort_mode
        self.sort_combo.clear()
        for key, label_key in (
            (_SORT_NEWEST, "trials.sort.newest"),
            (_SORT_OLDEST, "trials.sort.oldest"),
            (_SORT_DPI_ASC, "trials.sort.dpi_asc"),
            (_SORT_DPI_DESC, "trials.sort.dpi_desc"),
            (_SORT_ERROR, "trials.sort.abs_error"),
            (_SORT_STATUS, "trials.sort.status"),
        ):
            self.sort_combo.addItem(t(label_key), key)
        idx = self.sort_combo.findData(selected)
        self.sort_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.sort_combo.blockSignals(False)
        self.refresh()

    def refresh(self) -> None:
        t = self.controller.i18n.t
        summary = self.controller.session_trial_summary()
        profile = summary["accuracy_profile"]
        profile_key = {
            "FIELD_STRICT": "setup.accuracy.strict",
            "FIELD_MEDIUM": "setup.accuracy.medium",
            "FIELD_LENIENT": "setup.accuracy.lenient",
        }.get(profile, "setup.accuracy.strict")
        profile_label = t(profile_key)
        settings = {
            "cpi_error_pass_pct": summary["cpi_error_pass_pct"],
            "cpi_error_fail_pct": summary["cpi_error_fail_pct"],
            "tolerance_mode": profile,
        }
        bands = accuracy_criterion_lines(settings)
        # Drop "Mode:" line for compact summary; keep PASS/WARN/FAIL.
        band_txt = " · ".join(line for line in bands if not line.startswith("Mode:"))
        self.summary.setText(
            t("trials.summary").format(
                active=summary["active_trial_count"],
                rejected=summary["rejected_trial_count"],
                deleted=summary["deleted_trial_count"],
                groups=", ".join(str(d) for d in summary["dpi_groups"]) or "—",
                criterion=profile_label,
                bands=band_txt,
            )
        )
        current = self._dpi_filter
        self.dpi_filter.blockSignals(True)
        self.dpi_filter.clear()
        self.dpi_filter.addItem(t("trials.filter.all_dpi"), None)
        for dpi in summary["dpi_groups"]:
            self.dpi_filter.addItem(str(dpi), dpi)
        if current is not None:
            idx = self.dpi_filter.findData(current)
            self.dpi_filter.setCurrentIndex(idx if idx >= 0 else 0)
            if idx < 0:
                self._dpi_filter = None
        self.dpi_filter.blockSignals(False)
        apply_combo_content_min_width(self.dpi_filter)

        buckets = {
            "active": self.controller.session.presentation_trials("active"),
            "rejected": self.controller.session.presentation_trials("rejected"),
            "deleted": self.controller.session.presentation_trials("deleted"),
        }
        for name, trials in buckets.items():
            self._fill_table(self.tables[name], trials)
        self._sync_actions()

    def _fill_table(self, table: QTableWidget, trials: list[dict]) -> None:
        t = self.controller.i18n.t
        filtered = trials
        if self._dpi_filter is not None:
            filtered = [
                row
                for row in trials
                if int(row.get("configured_dpi") or 0) == int(self._dpi_filter)
            ]
        filtered = self._sorted_trials(list(filtered))
        content_fp = (
            REVISIONS.locale,
            self._sort_mode,
            self._dpi_filter,
            tuple(
                (
                    int(row.get("trial_id") or 0),
                    row.get("configured_dpi"),
                    row.get("measured_cpi"),
                    row.get("error_pct"),
                    row.get("status") or row.get("measurement_status"),
                    row.get("path_quality_status"),
                    row.get("lifecycle"),
                )
                for row in filtered
            ),
        )
        if content_fp == getattr(table, "_content_fp", None) and table.rowCount() == len(filtered):
            return
        COUNTERS.trial_table_rebuilds += 1
        table.setSortingEnabled(False)
        table.setRowCount(len(filtered))
        for r, trial in enumerate(filtered):
            mode = str(trial.get("movement_mode") or "")
            fixture = mode == MOVEMENT_MODE_FIXTURE_VECTOR
            geometry = (
                t("geometry.fixture_vector")
                if fixture
                else t("geometry.directional_axis")
            )
            direction = "—" if fixture else str(trial.get("direction") or "—")
            err = trial.get("error_pct")
            err_txt = f"{float(err):+.2f}%" if err is not None else "—"
            cpi = trial.get("measured_cpi")
            cpi_txt = f"{float(cpi):.1f}" if cpi is not None else "—"
            status = str(trial.get("status") or trial.get("measurement_status") or "—")
            pq = str(trial.get("path_quality_status") or "—")
            tid = int(trial.get("trial_id") or 0)
            dpi_v = int(trial.get("configured_dpi") or 0)
            cells: list[QTableWidgetItem] = [
                _NumericItem(str(tid)),
                _NumericItem(str(dpi_v)),
                QTableWidgetItem(geometry),
                QTableWidgetItem(f"{trial.get('distance_mm')} mm"),
                _NumericItem(cpi_txt),
                _NumericItem(err_txt),
                QTableWidgetItem(t(f"status.{status}", default=status)),
                QTableWidgetItem(pq),
                QTableWidgetItem(direction),
            ]
            cells[0].setData(Qt.ItemDataRole.UserRole, tid)
            cells[1].setData(Qt.ItemDataRole.UserRole, dpi_v)
            try:
                cells[4].setData(Qt.ItemDataRole.UserRole, float(cpi) if cpi is not None else None)
            except (TypeError, ValueError):
                cells[4].setData(Qt.ItemDataRole.UserRole, None)
            try:
                cells[5].setData(
                    Qt.ItemDataRole.UserRole, abs(float(err)) if err is not None else None
                )
            except (TypeError, ValueError):
                cells[5].setData(Qt.ItemDataRole.UserRole, None)
            for c, item in enumerate(cells):
                if c in {0, 1}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(r, c, item)
        table._content_fp = content_fp
        prev_rows = getattr(table, "_sized_rows", None)
        row_count_changed = prev_rows != len(filtered)
        headers_dirty = getattr(table, "_headers_dirty", True)
        # Expensive ResizeToContents only when rows appear/disappear or headers changed.
        if row_count_changed or headers_dirty or prev_rows is None:
            COUNTERS.header_resize_calls += 1
            _apply_trial_table_widths(
                table,
                refine_to_contents=len(filtered) > 0 and (row_count_changed or headers_dirty),
            )
            table._headers_dirty = False
        table._sized_rows = len(filtered)
