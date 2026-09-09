"""Configured-DPI control: one primary numeric field + compact presets."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QSpinBox, QWidget

from mouse_dpi_tool.ui.layout_metrics import apply_combo_content_min_width

DPI_PRESETS: tuple[int, ...] = (400, 800, 1600, 3200, 6400)


class ConfiguredDpiField(QWidget):
    """Primary spinbox is the on-screen source of truth; presets are a jump menu."""

    valueChanged = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._updating = False
        self.spin = QSpinBox()
        self.spin.setObjectName("DpiFineSpin")
        self.spin.setRange(1, 1_000_000)
        self.spin.setSingleStep(100)
        # Content-driven floor; no hard max — display scaling / large fonts must fit.
        self.spin.setMinimumWidth(112)
        self.spin.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.spin.setToolTip("Configured DPI (source of truth)")

        self.combo = QComboBox()
        self.combo.setObjectName("DpiPresetCombo")
        self.combo.setEditable(False)
        self.combo.setMaxVisibleItems(8)
        self.combo.setToolTip("Jump to a common configured DPI preset")
        self.combo.addItem("Presets", None)
        for value in DPI_PRESETS:
            self.combo.addItem(str(value), value)
        apply_combo_content_min_width(self.combo)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.spin, 0)
        layout.addWidget(self.combo, 0)
        layout.addStretch(1)
        self.combo.activated.connect(self._combo_activated)
        self.spin.valueChanged.connect(self._spin_changed)
        self.setValue(800)

    def retranslate(self, *, presets_label: str = "Presets", spin_tip: str = "", combo_tip: str = "") -> None:
        self.combo.setItemText(0, presets_label)
        if spin_tip:
            self.spin.setToolTip(spin_tip)
        if combo_tip:
            self.combo.setToolTip(combo_tip)
        apply_combo_content_min_width(self.combo)
        # Spin must fit largest range digits under current font/scaling.
        fm = self.spin.fontMetrics()
        sample = fm.boundingRect("1000000").width() + 48
        self.spin.setMinimumWidth(max(112, sample))

    def value(self) -> int:
        return int(self.spin.value())

    def setValue(self, value: int) -> None:  # noqa: N802 — Qt style
        value = max(1, min(1_000_000, int(value)))
        if self._updating:
            return
        self._updating = True
        try:
            self.spin.setValue(value)
            # Keep closed combo on "Presets" so the DPI value is not shown twice.
            self.combo.setCurrentIndex(0)
        finally:
            self._updating = False

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802
        super().setEnabled(enabled)
        self.combo.setEnabled(enabled)
        self.spin.setEnabled(enabled)

    def _emit(self, value: int) -> None:
        self.valueChanged.emit(int(value))

    def _combo_activated(self, index: int) -> None:
        if self._updating or index < 0:
            return
        data = self.combo.itemData(index)
        if data is None:
            self.combo.setCurrentIndex(0)
            return
        value = int(data)
        self._updating = True
        try:
            self.spin.setValue(value)
            self.combo.setCurrentIndex(0)
        finally:
            self._updating = False
        self._emit(value)

    def _spin_changed(self, value: int) -> None:
        if self._updating:
            return
        self._emit(int(value))
