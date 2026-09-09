"""Theme manager — presentation only."""

from __future__ import annotations

from mouse_dpi_tool.ui.theme.tokens import ThemeTokens, stylesheet, tokens_for


class ThemeManager:
    def __init__(self, mode: str = "system", *, system_is_dark: bool = False) -> None:
        self.mode = mode
        self.system_is_dark = system_is_dark

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    def set_system_is_dark(self, is_dark: bool) -> None:
        self.system_is_dark = bool(is_dark)

    @property
    def tokens(self) -> ThemeTokens:
        return tokens_for(self.mode, system_is_dark=self.system_is_dark)

    def qss(self) -> str:
        return stylesheet(self.tokens)
