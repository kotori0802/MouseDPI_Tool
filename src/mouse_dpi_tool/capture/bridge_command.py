"""Resolve the Windows Raw Input helper launch command.

Development: ``python -m mouse_dpi_tool.capture.raw_input_bridge``
Frozen:      ``<app_dir>/MouseDPI_RawInputBridge.exe``

Never launch ``sys.executable`` with a ``.py`` script path under a frozen UI —
that re-opens the Qt application instead of the Raw Input helper.
"""

from __future__ import annotations

import sys
from pathlib import Path

FROZEN_HELPER_NAME = "MouseDPI_RawInputBridge.exe"


class BridgeHelperNotFoundError(RuntimeError):
    """Packaged Raw Input helper executable is missing."""


def is_frozen_runtime(frozen: bool | None = None) -> bool:
    if frozen is not None:
        return bool(frozen)
    return bool(getattr(sys, "frozen", False))


def frozen_app_dir(*, executable: str | None = None) -> Path:
    return Path(executable or sys.executable).resolve().parent


def resolve_bridge_command(
    *,
    frozen: bool | None = None,
    executable: str | None = None,
    app_dir: Path | str | None = None,
) -> list[str]:
    """Return argv for launching the Raw Input helper.

    Raises:
        BridgeHelperNotFoundError: frozen runtime and helper EXE is absent.
    """
    if is_frozen_runtime(frozen):
        base = Path(app_dir) if app_dir is not None else frozen_app_dir(executable=executable)
        helper = base / FROZEN_HELPER_NAME
        if not helper.is_file():
            raise BridgeHelperNotFoundError(
                f"Raw Input helper executable not found: {helper}"
            )
        return [str(helper)]
    # Module launch — do not depend on a sibling .py path beside a frozen EXE.
    return [sys.executable, "-m", "mouse_dpi_tool.capture.raw_input_bridge"]
