"""Presentation layout metrics — text-driven minimum sizes (no locale hardcodes)."""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFormLayout, QHeaderView, QLabel, QTableWidget, QWidget

# Vertical rhythm hierarchy (presentation only — not domain).
SPACE_FORM_WITHIN = 8
SPACE_FORM_ROW = 12
SPACE_FORM_GROUP = 22
SPACE_HELPER_AFTER = 10
SPACE_SECTION = 18
SPACE_CAPTURE_SUMMARY_GAP = 12
SPACE_CAPTURE_FILTER_GAP = 14
SPACE_CAPTURE_TAB_INNER = 6

# ---------------------------------------------------------------------------
# Workspace composition (Qt logical px) — Phase 3.1
# Do NOT derive these from ch; ch is for reading measure only.
# ---------------------------------------------------------------------------
SETUP_WORKSPACE_MAX_WIDTH = 1160
SETUP_TWO_COLUMN_MIN_WIDTH = 1040
SETTINGS_PANEL_MAX_WIDTH = 620
RESULTS_EMPTY_MAX_WIDTH = 720
USER_GUIDE_DEFAULT_WIDTH = 680
USER_GUIDE_DEFAULT_HEIGHT = 620
USER_GUIDE_MIN_WIDTH = 600
USER_GUIDE_MIN_HEIGHT = 500
CAPTURE_INSTRUCTION_MAX_WIDTH_CH = 88
CAPTURE_INSTRUCTION_MAX_WIDTH_PX = 760


def comfortable_form_max_width(widget: QWidget) -> int:
    """Reading-measure form width (~64ch). Not a workspace-shell measure."""
    ch = max(7, widget.fontMetrics().horizontalAdvance("0"))
    return int(ch * 64)


def comfortable_prose_max_width(widget: QWidget) -> int:
    """Long instruction / helper prose (~80–90ch), capped in logical px."""
    ch = max(7, widget.fontMetrics().horizontalAdvance("0"))
    return min(CAPTURE_INSTRUCTION_MAX_WIDTH_PX, int(ch * CAPTURE_INSTRUCTION_MAX_WIDTH_CH))


def comfortable_composition_max_width(widget: QWidget) -> int:
    """Deprecated alias — Setup workspace cap is logical px (Phase 3.1)."""
    del widget
    return SETUP_WORKSPACE_MAX_WIDTH


def setup_two_column_breakpoint(widget: QWidget) -> int:
    """Logical viewport width below which Setup stacks DUT above Measurement."""
    del widget
    return SETUP_TWO_COLUMN_MIN_WIDTH


def form_label_column_min_width(widget: QWidget) -> int:
    """Stable label column floor so bilingual labels do not jitter."""
    ch = max(7, widget.fontMetrics().horizontalAdvance("0"))
    return int(ch * 16)


def style_form_label(label: QLabel) -> None:
    """Scoped form-label role — text label, not a filled tag/cell."""
    label.setObjectName("FormLabel")
    label.setWordWrap(True)
    floor = form_label_column_min_width(label)
    if label.minimumWidth() < floor:
        label.setMinimumWidth(floor)


def configure_form_layout(form: QFormLayout, *, within_group: bool = False) -> None:
    """Consistent form spacing / label gap / growth policy."""
    form.setContentsMargins(0, 0, 0, 0)
    form.setHorizontalSpacing(16)
    form.setVerticalSpacing(SPACE_FORM_WITHIN if within_group else SPACE_FORM_ROW)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)


def header_min_section_widths(
    table: QTableWidget,
    *,
    padding_px: int = 20,
    sort_indicator_px: int = 28,
) -> list[int]:
    """Minimum widths so every localized header glyph fits (empty-model safe)."""
    header = table.horizontalHeader()
    fm = header.fontMetrics()
    dpr = float(table.devicePixelRatioF()) if hasattr(table, "devicePixelRatioF") else 1.0
    # Slight extra pad at higher display scaling so focus/borders do not clip glyphs.
    scale_pad = int(round(4 * max(1.0, dpr - 1.0)))
    widths: list[int] = []
    for col in range(table.columnCount()):
        item = table.horizontalHeaderItem(col)
        text = item.text() if item is not None else ""
        text_w = fm.boundingRect(text).width()
        widths.append(max(48, text_w + padding_px + sort_indicator_px + scale_pad))
    return widths


def apply_header_safe_widths(
    table: QTableWidget,
    *,
    refine_to_contents: bool = False,
) -> list[int]:
    """Size columns from header text; optionally refine with contents without shrinking below mins.

    Avoid calling this on a high-frequency timer. ``resizeColumnsToContents`` is
    expensive and must not run on every Capture live tick.
    """
    mins = header_min_section_widths(table)
    header = table.horizontalHeader()
    # Floor for Interactive drag — do not force every section to min every call.
    floor = max(40, min(mins) if mins else 40)
    if header.minimumSectionSize() < floor:
        header.setMinimumSectionSize(floor)
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    if refine_to_contents and table.rowCount() > 0:
        table.resizeColumnsToContents()
        for col, mn in enumerate(mins):
            if header.sectionSize(col) < mn:
                header.resizeSection(col, mn)
    else:
        # Empty / header-only: set explicit widths from localized header text.
        for col, mn in enumerate(mins):
            if header.sectionSize(col) < mn:
                header.resizeSection(col, mn)
    return mins


def combo_min_width_for_items(
    combo: QComboBox,
    *,
    padding_px: int = 24,
    dropdown_affordance_px: int = 36,
    focus_border_px: int = 4,
) -> int:
    """Minimum width for a non-editable combo so the closed label + arrow fit."""
    fm = combo.fontMetrics()
    texts: Iterable[str] = (combo.itemText(i) for i in range(combo.count()))
    widest = max((fm.boundingRect(text).width() for text in texts), default=0)
    dpr = float(combo.devicePixelRatioF()) if hasattr(combo, "devicePixelRatioF") else 1.0
    scale_pad = int(round(6 * max(1.0, dpr - 1.0)))
    return max(72, widest + padding_px + dropdown_affordance_px + focus_border_px + scale_pad)


def apply_combo_content_min_width(combo: QComboBox) -> int:
    """Remove hard max-width caps and apply content-derived minimum."""
    w = combo_min_width_for_items(combo)
    if combo.minimumWidth() != w:
        combo.setMinimumWidth(w)
    # Clear any previous max-width clamp so longer locales / scaling can grow.
    if combo.maximumWidth() < 1_000_000:
        combo.setMaximumWidth(16777215)
    return w


def apply_widget_text_min_width(widget: QWidget, text: str, *, padding_px: int = 28) -> int:
    fm = widget.fontMetrics()
    w = fm.boundingRect(text).width() + padding_px
    widget.setMinimumWidth(max(widget.minimumWidth(), w))
    return w
