"""Radial Target Gauge — presentation only (never Session evidence).

Expected radius in count space: R = configured_dpi × distance_inch.
Endpoint (dx, dy) is plotted against that ring for any-angle fixtures.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from mouse_dpi_tool.ui.theme.tokens import ThemeTokens, tokens_for


def expected_target_radius_counts(*, configured_dpi: int, distance_mm: float) -> float:
    """Ideal net vector magnitude for configured DPI over known physical distance."""
    inch = float(distance_mm) / 25.4
    if inch <= 0 or configured_dpi < 1:
        return 0.0
    return float(configured_dpi) * inch


def map_counts_to_gauge(
    dx: float,
    dy: float,
    *,
    target_radius: float,
    width: float,
    height: float,
    pad: float = 20.0,
    pass_pct: float = 5.0,
) -> dict[str, float | tuple[float, float]]:
    """Map count-space origin/endpoint into widget coords (presentation only).

    Scale so the outer tolerance ring fits inside the padded square.
    """
    w = max(width - 2 * pad, 1.0)
    h = max(height - 2 * pad, 1.0)
    half = min(w, h) / 2.0
    cx = width / 2.0
    cy = height / 2.0
    outer_r = float(target_radius) * (1.0 + max(0.0, float(pass_pct)) / 100.0)
    span = max(outer_r, abs(dx), abs(dy), 1.0)
    scale = half / span

    def to_widget(x: float, y: float) -> tuple[float, float]:
        # Raw Input +Y down matches Qt widget Y.
        return (cx + x * scale, cy + y * scale)

    return {
        "center": (cx, cy),
        "scale": scale,
        "ring_px": float(target_radius) * scale,
        "inner_px": float(target_radius) * (1.0 - max(0.0, float(pass_pct)) / 100.0) * scale,
        "outer_px": outer_r * scale,
        "endpoint": to_widget(float(dx), float(dy)),
        "vector_counts": math.sqrt(float(dx) * float(dx) + float(dy) * float(dy)),
    }


class RadialTargetGauge(QWidget):
    """Shows target radius ring vs live/net displacement endpoint."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._dx = 0.0
        self._dy = 0.0
        self._target_r = 0.0
        self._pass_pct = 5.0
        self._accent = QColor("#0071E3")
        self._muted = QColor("#6E6E73")
        self._surface = QColor("#FFFFFF")
        self._border = QColor("#D2D2D7")
        self._ok = QColor("#2F9E44")
        self._warn = QColor("#E8590C")
        self.apply_tokens(tokens_for("light"))
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setObjectName("RadialTargetGauge")

    def apply_tokens(self, tokens: ThemeTokens) -> None:
        self._accent = QColor(tokens.accent)
        self._muted = QColor(tokens.text_secondary)
        self._surface = QColor(tokens.surface)
        self._border = QColor(tokens.border)
        self.update()

    def set_state(
        self,
        *,
        net_dx: float,
        net_dy: float,
        configured_dpi: int,
        distance_mm: float,
        pass_pct: float = 5.0,
    ) -> None:
        dx = float(net_dx)
        dy = float(net_dy)
        target_r = expected_target_radius_counts(
            configured_dpi=int(configured_dpi), distance_mm=float(distance_mm)
        )
        pct = float(pass_pct)
        if (
            dx == self._dx
            and dy == self._dy
            and target_r == self._target_r
            and pct == self._pass_pct
        ):
            return
        from mouse_dpi_tool.ui.presentation_invalidation import COUNTERS

        COUNTERS.gauge_updates += 1
        self._dx = dx
        self._dy = dy
        self._target_r = target_r
        self._pass_pct = pct
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.fillRect(rect, self._surface)
        painter.setPen(QPen(self._border, 1))
        painter.drawRoundedRect(rect, 10, 10)

        mapped = map_counts_to_gauge(
            self._dx,
            self._dy,
            target_radius=self._target_r,
            width=float(self.width()),
            height=float(self.height()),
            pass_pct=self._pass_pct,
        )
        cx, cy = mapped["center"]  # type: ignore[misc]
        center = QPointF(float(cx), float(cy))
        ring = float(mapped["ring_px"])
        inner = float(mapped["inner_px"])
        outer = float(mapped["outer_px"])
        ex, ey = mapped["endpoint"]  # type: ignore[misc]
        endpoint = QPointF(float(ex), float(ey))

        # Tolerance band (presentation).
        if outer > 1.0:
            band = QColor(self._ok)
            band.setAlpha(36)
            painter.setBrush(band)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, outer, outer)
            painter.setBrush(self._surface)
            painter.drawEllipse(center, max(inner, 0.0), max(inner, 0.0))

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(self._muted, 1, Qt.PenStyle.DashLine))
        if ring > 1.0:
            painter.drawEllipse(center, ring, ring)

        # Crosshair origin.
        painter.setPen(QPen(self._muted, 1))
        painter.drawLine(QPointF(cx - 8, cy), QPointF(cx + 8, cy))
        painter.drawLine(QPointF(cx, cy - 8), QPointF(cx, cy + 8))

        # Displacement ray + endpoint.
        vector = float(mapped["vector_counts"])
        if vector > 0.5:
            hit = abs(vector - self._target_r) <= self._target_r * (self._pass_pct / 100.0)
            color = self._ok if hit else self._accent
            painter.setPen(QPen(color, 2.5))
            painter.drawLine(center, endpoint)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(endpoint, 5.0, 5.0)
