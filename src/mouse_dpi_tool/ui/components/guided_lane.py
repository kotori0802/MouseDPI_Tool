"""Guided measurement lane — presentation only (never CPI ground truth)."""

from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from mouse_dpi_tool.ui.direction import canonicalize_direction, lane_orientation
from mouse_dpi_tool.ui.theme.tokens import ThemeTokens, tokens_for


class GuidedLane(QWidget):
    """START → TARGET visual that flips with X+/X-/Y+/Y-.

    Does not measure distance, counts, or CPI. Physical marked travel remains
    the operator reference. Colors come from ThemeTokens (not Session evidence).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._direction = "X+"
        self._start_label = "START"
        self._target_label = "TARGET"
        self._accent = QColor("#0071E3")
        self._muted = QColor("#6E6E73")
        self.apply_tokens(tokens_for("light"))
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setObjectName("GuidedLane")

    @property
    def direction(self) -> str:
        return self._direction

    @property
    def orientation(self) -> str:
        return lane_orientation(self._direction)

    @property
    def accent_color(self) -> str:
        return self._accent.name()

    @property
    def muted_color(self) -> str:
        return self._muted.name()

    def apply_tokens(self, tokens: ThemeTokens) -> None:
        self._accent = QColor(tokens.accent)
        self._muted = QColor(tokens.text_secondary)
        self.update()

    def set_direction(self, direction: str) -> None:
        self._direction = canonicalize_direction(direction)
        self.update()

    def set_endpoint_labels(self, *, start: str, target: str) -> None:
        self._start_label = str(start)
        self._target_label = str(target)
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 — Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(12, 10, -12, -10)
        pen = QPen(self._accent, 2.5)
        painter.setPen(pen)
        font = QFont(self.font())
        # pointSize() is -1 when the font is pixel-sized (triggers Qt warning).
        ps = font.pointSize()
        font.setPointSize(ps if ps > 0 else 9)
        painter.setFont(font)

        orient = self.orientation
        if orient.startswith("horizontal"):
            y = rect.center().y()
            left = QPointF(rect.left() + 8, y)
            right = QPointF(rect.right() - 8, y)
            painter.drawLine(left, right)
            if orient == "horizontal_ltr":
                self._arrow(painter, right, dx=1)
                self._label(painter, self._start_label, left.x(), y - 18, self._muted, align="left")
                self._label(painter, self._target_label, right.x(), y - 18, self._muted, align="right")
            else:
                self._arrow(painter, left, dx=-1)
                self._label(painter, self._target_label, left.x(), y - 18, self._muted, align="left")
                self._label(painter, self._start_label, right.x(), y - 18, self._muted, align="right")
        else:
            x = rect.center().x()
            top = QPointF(x, rect.top() + 8)
            bottom = QPointF(x, rect.bottom() - 8)
            painter.drawLine(top, bottom)
            if orient == "vertical_btt":
                self._arrow(painter, top, dy=-1)
                self._label(painter, self._target_label, x + 10, top.y() + 4, self._muted, align="left")
                self._label(painter, self._start_label, x + 10, bottom.y() - 4, self._muted, align="left")
            else:
                self._arrow(painter, bottom, dy=1)
                self._label(painter, self._start_label, x + 10, top.y() + 4, self._muted, align="left")
                self._label(painter, self._target_label, x + 10, bottom.y() - 4, self._muted, align="left")
        painter.end()

    def _arrow(self, painter: QPainter, tip: QPointF, *, dx: int = 0, dy: int = 0) -> None:
        size = 8.0
        if dx:
            painter.drawLine(tip, QPointF(tip.x() - dx * size, tip.y() - size * 0.6))
            painter.drawLine(tip, QPointF(tip.x() - dx * size, tip.y() + size * 0.6))
        elif dy:
            painter.drawLine(tip, QPointF(tip.x() - size * 0.6, tip.y() - dy * size))
            painter.drawLine(tip, QPointF(tip.x() + size * 0.6, tip.y() - dy * size))

    def _label(
        self,
        painter: QPainter,
        text: str,
        x: float,
        y: float,
        color: QColor,
        *,
        align: str,
    ) -> None:
        painter.setPen(color)
        metrics = painter.fontMetrics()
        width = metrics.horizontalAdvance(text)
        draw_x = x if align == "left" else x - width
        painter.drawText(int(draw_x), int(y), text)
