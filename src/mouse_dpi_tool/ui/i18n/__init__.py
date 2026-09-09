"""I18n manager — maps canonical codes to localized display strings only."""

from __future__ import annotations

from mouse_dpi_tool.ui import SUPPORTED_LOCALES
from mouse_dpi_tool.ui.i18n.catalogs import (
    CATALOGS,
    LOCALE_DISPLAY_NAMES,
    SHELL_REQUIRED_KEYS,
)


class I18n:
    def __init__(self, locale: str = "en-US") -> None:
        self.set_locale(locale)

    def set_locale(self, locale: str) -> None:
        self.locale = locale if locale in SUPPORTED_LOCALES else "en-US"
        self._catalog = CATALOGS.get(self.locale, CATALOGS["en-US"])

    def t(self, key: str, *, default: str | None = None) -> str:
        if key in self._catalog:
            return self._catalog[key]
        en = CATALOGS["en-US"]
        if key in en:
            return en[key]
        return default if default is not None else key

    def status(self, code: str) -> str:
        return self.t(f"status.{code}", default=str(code))

    def finding(self, dimension: str) -> str:
        return self.t(f"finding.{dimension}", default=dimension)

    def issue(self, code: str) -> str:
        return self.t(f"issue.{code}", default=str(code))

    def observation(self, observation_id: str) -> str:
        return self.t(f"obs.{observation_id}", default=observation_id)

    def unit(self, code: str) -> str:
        return self.t(f"unit.{code}", default=str(code))

    def method(self, code: str) -> str:
        return self.t(f"method.{code}", default=str(code))

    def theme_label(self, mode: str) -> str:
        return self.t(f"theme.{mode}", default=str(mode))

    def direction(self, code: str) -> str:
        return self.t(f"direction.{code}", default=str(code))


def shell_i18n_gaps() -> dict[str, list[str]]:
    """Keys still equal to English (likely untranslated) per locale."""
    en = CATALOGS["en-US"]
    gaps: dict[str, list[str]] = {}
    for locale, catalog in CATALOGS.items():
        if locale == "en-US":
            continue
        gaps[locale] = [
            key
            for key in SHELL_REQUIRED_KEYS
            if catalog.get(key, en[key]) == en[key]
        ]
    return gaps


__all__ = [
    "CATALOGS",
    "I18n",
    "LOCALE_DISPLAY_NAMES",
    "SHELL_REQUIRED_KEYS",
    "shell_i18n_gaps",
]
