"""UI preference store — separate from Session engineering evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mouse_dpi_tool.ui import SUPPORTED_LOCALES, THEME_MODES

DEFAULT_PREFS = {
    "theme": "system",
    "locale": "en-US",
    "window_width": 1180,
    "window_height": 760,
}


def preferences_path(app_root: Path | None = None) -> Path:
    root = app_root or Path.home() / ".mouse_dpi_tool"
    root.mkdir(parents=True, exist_ok=True)
    return root / "ui_preferences.json"


def load_preferences(path: Path | None = None) -> dict[str, Any]:
    target = path or preferences_path()
    data = dict(DEFAULT_PREFS)
    if target.exists():
        try:
            loaded = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass
    if data.get("theme") not in THEME_MODES:
        data["theme"] = "system"
    if data.get("locale") not in SUPPORTED_LOCALES:
        data["locale"] = "en-US"
    return data


def save_preferences(prefs: dict[str, Any], path: Path | None = None) -> Path:
    target = path or preferences_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "theme": prefs.get("theme", "system"),
        "locale": prefs.get("locale", "en-US"),
        "window_width": int(prefs.get("window_width", 1180)),
        "window_height": int(prefs.get("window_height", 760)),
    }
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
