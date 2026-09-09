"""Geometry selection tiles — Setup-only movement_mode editor.

Keyboard: Tab moves focus between tiles; Left/Right arrows move selection;
Space/Enter activates the focused tile.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from mouse_dpi_tool.ui.controllers import (
    MOVEMENT_MODE_DIRECTIONAL_AXIS,
    MOVEMENT_MODE_FIXTURE_VECTOR,
)


class GeometryTile(QFrame):
    """Single selectable geometry option."""

    activated = Signal(str)

    def __init__(self, mode: str, parent=None) -> None:
        super().__init__(parent)
        self.mode = mode
        self.setObjectName("GeometryTile")
        self.setProperty("selected", False)
        self.setProperty("tileEnabled", True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.title = QLabel()
        self.title.setObjectName("GeometryTileTitle")
        self.title.setWordWrap(True)
        self.subtitle = QLabel()
        self.subtitle.setObjectName("GeometryTileSubtitle")
        self.subtitle.setWordWrap(True)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(4)
        root.addWidget(self.title)
        root.addWidget(self.subtitle)

    def set_texts(self, title: str, subtitle: str) -> None:
        self.title.setText(title)
        self.subtitle.setText(subtitle)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", bool(selected))
        self.style().unpolish(self)
        self.style().polish(self)

    def set_tile_enabled(self, enabled: bool) -> None:
        self.setProperty("tileEnabled", bool(enabled))
        self.setEnabled(bool(enabled))
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self.mode)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if self.isEnabled() and event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.activated.emit(self.mode)
            event.accept()
            return
        super().keyPressEvent(event)


class GeometryTileGroup(QWidget):
    """Two-tile group for Fixture Vector vs Directional Axis."""

    currentChanged = Signal(str)

    MODES: tuple[str, str] = (MOVEMENT_MODE_FIXTURE_VECTOR, MOVEMENT_MODE_DIRECTIONAL_AXIS)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("GeometryTileGroup")
        self._current = MOVEMENT_MODE_FIXTURE_VECTOR
        self._tiles: dict[str, GeometryTile] = {}
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        for mode in self.MODES:
            tile = GeometryTile(mode)
            tile.activated.connect(self._on_activated)
            self._tiles[mode] = tile
            row.addWidget(tile, 1)
        self._sync_selection()

    def current(self) -> str:
        return self._current

    def set_current(self, mode: str, *, emit: bool = False) -> None:
        if mode not in self._tiles:
            return
        if mode == self._current and not emit:
            self._sync_selection()
            return
        self._current = mode
        self._sync_selection()
        if emit:
            self.currentChanged.emit(mode)

    def set_group_enabled(self, enabled: bool) -> None:
        for tile in self._tiles.values():
            tile.set_tile_enabled(enabled)

    def retranslate(self, *, fixture_title: str, fixture_sub: str, axis_title: str, axis_sub: str) -> None:
        self._tiles[MOVEMENT_MODE_FIXTURE_VECTOR].set_texts(fixture_title, fixture_sub)
        self._tiles[MOVEMENT_MODE_DIRECTIONAL_AXIS].set_texts(axis_title, axis_sub)

    def _sync_selection(self) -> None:
        for mode, tile in self._tiles.items():
            tile.set_selected(mode == self._current)

    def _on_activated(self, mode: str) -> None:
        if not self._tiles[mode].isEnabled():
            return
        if mode == self._current:
            return
        self._current = mode
        self._sync_selection()
        self.currentChanged.emit(mode)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if not self.isEnabled():
            super().keyPressEvent(event)
            return
        key = event.key()
        modes = list(self.MODES)
        try:
            idx = modes.index(self._current)
        except ValueError:
            idx = 0
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Up):
            self.set_current(modes[(idx - 1) % len(modes)], emit=True)
            self._tiles[self._current].setFocus(Qt.FocusReason.TabFocusReason)
            event.accept()
            return
        if key in (Qt.Key.Key_Right, Qt.Key.Key_Down):
            self.set_current(modes[(idx + 1) % len(modes)], emit=True)
            self._tiles[self._current].setFocus(Qt.FocusReason.TabFocusReason)
            event.accept()
            return
        super().keyPressEvent(event)
