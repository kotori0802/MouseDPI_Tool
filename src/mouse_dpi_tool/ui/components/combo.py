"""ComboBox helpers — display labels vs canonical item data."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtWidgets import QComboBox


def refill_combo(
    combo: QComboBox,
    items: Sequence[tuple[str, str]],
    *,
    selected_data: str | None = None,
) -> None:
    """Rebuild combo items as (display_label, canonical_data), preserving selection."""
    current = selected_data
    if current is None:
        current = combo.currentData()
    combo.blockSignals(True)
    combo.clear()
    for label, data in items:
        combo.addItem(str(label), str(data))
    idx = combo.findData(current)
    if idx < 0 and combo.count():
        idx = 0
    if idx >= 0:
        combo.setCurrentIndex(idx)
    combo.blockSignals(False)


def combo_data(combo: QComboBox, default: str = "") -> str:
    data = combo.currentData()
    return str(data) if data is not None else default
