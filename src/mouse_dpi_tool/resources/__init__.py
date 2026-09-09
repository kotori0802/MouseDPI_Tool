"""Runtime package resources (schema, templates).

Works under editable install, wheel install, and PyInstaller when datas are bundled.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any


def session_schema() -> dict[str, Any]:
    text = resources.files("mouse_dpi_tool.resources.schemas").joinpath(
        "mouse_dpi_tool_session_v1.json"
    ).read_text(encoding="utf-8")
    return json.loads(text)


def manual_observation_template() -> list[dict[str, Any]]:
    text = resources.files("mouse_dpi_tool.resources.templates").joinpath(
        "manual_observation_template.json"
    ).read_text(encoding="utf-8")
    return json.loads(text)
