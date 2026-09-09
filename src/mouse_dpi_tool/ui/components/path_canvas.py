"""Relative path canvas — presentation only (never measurement evidence)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from mouse_dpi_tool.ui.theme.tokens import ThemeTokens, tokens_for


def map_raw_path_to_widget(
    points: tuple[tuple[float, float], ...] | list[tuple[float, float]],
    *,
    width: float,
    height: float,
    pad: float = 16.0,
) -> list[tuple[float, float]]:
    """Map Raw Input cumulative path into widget coordinates.

    Windows relative Raw Input and Qt both use +Y downward, so raw dy is NOT
    inverted again. Physical Y+ (bottom→top, raw dy<0) therefore renders upward.
    Pure horizontal/vertical traces are centered on the unused axis.
    """
    pts = list(points) if points else [(0.0, 0.0)]
    if len(pts) < 1:
        pts = [(0.0, 0.0)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max_x - min_x
    span_y = max_y - min_y
    w = max(width - 2 * pad, 1.0)
    h = max(height - 2 * pad, 1.0)
    # Avoid zero-span collapse: treat near-zero span as 1 count for scale, then center.
    scale_x = w / max(span_x, 1.0)
    scale_y = h / max(span_y, 1.0)
    scale = min(scale_x, scale_y)

    def map_one(x: float, y: float) -> tuple[float, float]:
        if span_x < 1e-9:
            mx = width / 2.0
        else:
            mx = pad + (x - min_x) * scale
        if span_y < 1e-9:
            my = height / 2.0
        else:
            # Same +Y-down convention as Raw Input / Qt — no second invert.
            my = pad + (y - min_y) * scale
        return (mx, my)

    return [map_one(x, y) for x, y in pts]


class PathCanvas(QWidget):
    """Draws a bounded relative path for operator feedback.

    Screen-fit normalization is display-only and must never be written back as
    engineering evidence.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._points: tuple[tuple[float, float], ...] = ((0.0, 0.0),)
        self._accent = QColor("#0071E3")
        self._muted = QColor("#6E6E73")
        self._surface = QColor("#FFFFFF")
        self._border = QColor("#D2D2D7")
        self.apply_tokens(tokens_for("light"))
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setObjectName("PathCanvas")

    def apply_tokens(self, tokens: ThemeTokens) -> None:
        self._accent = QColor(tokens.accent)
        self._muted = QColor(tokens.text_secondary)
        self._surface = QColor(tokens.surface)
        self._border = QColor(tokens.border)
        self.update()

    def set_points(self, points: tuple[tuple[float, float], ...] | list[tuple[float, float]]) -> None:
        pts = tuple(points) if points else ((0.0, 0.0),)
        # Skip no-op updates — live Capture polls at ~30 Hz.
        if pts is self._points:
            return
        if (
            len(pts) == len(self._points)
            and pts
            and self._points
            and pts[-1] == self._points[-1]
            and pts[0] == self._points[0]
        ):
            return
        from mouse_dpi_tool.ui.presentation_invalidation import COUNTERS

        COUNTERS.path_updates += 1
        self._points = pts
        self.update()

    @property
    def point_count(self) -> int:
        return len(self._points)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.fillRect(rect, self._surface)
        painter.setPen(QPen(self._border, 1))
        painter.drawRect(rect)

        pts = self._points
        if len(pts) < 2:
            painter.setPen(self._muted)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "—")
            painter.end()
            return

        mapped = map_raw_path_to_widget(pts, width=float(rect.width()), height=float(rect.height()))
        # Offset into rect
        origin = QPointF(rect.left(), rect.top())
        painter.setPen(QPen(self._accent, 2.0))
        for i in range(1, len(mapped)):
            a = origin + QPointF(*mapped[i - 1])
            b = origin + QPointF(*mapped[i])
            painter.drawLine(a, b)
        start = origin + QPointF(*mapped[0])
        end = origin + QPointF(*mapped[-1])
        painter.setBrush(self._muted)
        painter.drawEllipse(start, 3.5, 3.5)
        painter.setBrush(self._accent)
        painter.drawEllipse(end, 4.0, 4.0)
        painter.end()
