"""Presentation layer — Qt UI only. Never imported by domain packages."""

from __future__ import annotations

__all__ = ["SUPPORTED_LOCALES", "THEME_MODES"]

SUPPORTED_LOCALES = (
    "en-US",
    "zh-TW",
    "zh-CN",
    "ja-JP",
    "ko-KR",
    "de-DE",
    "fr-FR",
    "es-ES",
)

THEME_MODES = ("light", "dark", "system")
