"""Engineering visualization host — presentation only.

V1 exposes Radial Target Gauge + Path Trace. Future V1.5 views (Normalized Path
Residual, Raw Δ scatter, endpoint scatter, DPI sweep) can register here without
rebuilding CapturePage. Unimplemented views must not appear in the V1 UI.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QBoxLayout, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget

from mouse_dpi_tool.ui.components.path_canvas import PathCanvas
from mouse_dpi_tool.ui.components.radial_target_gauge import RadialTargetGauge
from mouse_dpi_tool.ui.theme.tokens import ThemeTokens

_NARROW_BREAKPOINT_PX = 720
_MIN_PLOT_H = 300
_MIN_PLOT_H_NARROW = 280


class EngineeringVisualizationHost(QWidget):
    """Large-screen workspace for Capture engineering plots."""

    # Documented future slots (architecture only — not shown in V1 UI).
    FUTURE_VIEW_IDS: tuple[str, ...] = (
        "normalized_path_residual",
        "raw_delta_scatter",
        "endpoint_scatter",
        "dpi_sweep_trend",
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._narrow = False
        self.gauge = RadialTargetGauge()
        self.canvas = PathCanvas()
        for w in (self.gauge, self.canvas):
            w.setMinimumHeight(_MIN_PLOT_H)
            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(12)
        # Path Trace dominant — Gauge subordinate (Phase 3.1).
        self._row.addWidget(self.gauge, 2)
        self._row.addWidget(self.canvas, 3)

        # Reserved stack for future V1.5 views — empty / hidden in V1.
        self._future = QStackedWidget()
        self._future.setVisible(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(self._row, 1)
        root.addWidget(self._future, 0)
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def apply_tokens(self, tokens: ThemeTokens) -> None:
        self.gauge.apply_tokens(tokens)
        self.canvas.apply_tokens(tokens)

    def set_fixture_vector_mode(self, enabled: bool) -> None:
        self.gauge.setVisible(bool(enabled))
        self.canvas.setVisible(True)

    def set_gauge_state(self, **kwargs) -> None:
        self.gauge.set_state(**kwargs)

    def set_path_points(self, points) -> None:
        self.canvas.set_points(points)

    def register_future_view(self, view_id: str, widget: QWidget) -> None:
        """V1.5 hook — registers a view without exposing unfinished V1 chrome."""
        if view_id not in self.FUTURE_VIEW_IDS:
            raise ValueError(f"unknown future view id: {view_id}")
        widget.setProperty("viz_view_id", view_id)
        self._future.addWidget(widget)
        # Intentionally keep _future hidden until a V1.5 release enables it.

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        narrow = self.width() < _NARROW_BREAKPOINT_PX
        if narrow == self._narrow:
            return
        self._narrow = narrow
        direction = (
            QBoxLayout.Direction.TopToBottom
            if narrow
            else QBoxLayout.Direction.LeftToRight
        )
        self._row.setDirection(direction)
        minh = _MIN_PLOT_H_NARROW if narrow else _MIN_PLOT_H
        self.gauge.setMinimumHeight(minh)
        self.canvas.setMinimumHeight(minh)
