"""UI-only bounded path buffer. Never Path Quality or CPI evidence.

Uses collections.deque(maxlen=...) so append is O(1) and never stalls the
measurement dispatcher with list slicing/copies.

reset/on_sample/points are safe for concurrent dispatcher write + UI read.
"""

from __future__ import annotations

import threading
from collections import deque

from mouse_dpi_tool.contracts.movement import VISUALIZATION_PATH_MAX_POINTS, MovementSample


class VisualizationPathBuffer:
    def __init__(self, max_points: int = VISUALIZATION_PATH_MAX_POINTS) -> None:
        self.max_points = max(1, int(max_points))
        self._lock = threading.Lock()
        self._points: deque[tuple[float, float]] = deque([(0.0, 0.0)], maxlen=self.max_points)

    def reset(self) -> None:
        with self._lock:
            self._points = deque([(0.0, 0.0)], maxlen=self.max_points)

    def on_sample(self, sample: MovementSample) -> None:
        with self._lock:
            last_x, last_y = self._points[-1]
            self._points.append((last_x + sample.dx, last_y + sample.dy))

    def points(self) -> tuple[tuple[float, float], ...]:
        with self._lock:
            return tuple(self._points)
