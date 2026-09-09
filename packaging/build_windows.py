"""Build Windows onedir UI + dedicated Raw Input helper executable.

Usage (from repo root):

    python packaging/build_windows.py

Output layout:

    dist/MouseDPI_Tool_UI/
      MouseDPI_Tool_UI.exe
      MouseDPI_RawInputBridge.exe
      _internal/...

Keep the entire folder together when distributing.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
UI_NAME = "MouseDPI_Tool_UI"
HELPER_NAME = "MouseDPI_RawInputBridge"
UI_DIR = DIST / UI_NAME


def _run(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.check_call(args, cwd=ROOT)


def main() -> int:
    py = sys.executable
    # 1) Slim console helper (stdout JSON protocol). Parent uses CREATE_NO_WINDOW.
    _run(
        [
            py,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--console",
            "--onefile",
            f"--name={HELPER_NAME}",
            "--paths",
            "src",
            "packaging/run_raw_input_bridge.py",
        ]
    )
    # 2) Windowed UI onedir (no console).
    _run(
        [
            py,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--windowed",
            "--onedir",
            f"--name={UI_NAME}",
            "--paths",
            "src",
            "--collect-all",
            "PySide6",
            "--collect-data",
            "mouse_dpi_tool",
            "packaging/run_ui.py",
        ]
    )
    helper_src = DIST / f"{HELPER_NAME}.exe"
    if not helper_src.is_file():
        raise SystemExit(f"helper build missing: {helper_src}")
    if not UI_DIR.is_dir():
        raise SystemExit(f"UI dist missing: {UI_DIR}")
    helper_dst = UI_DIR / f"{HELPER_NAME}.exe"
    shutil.copy2(helper_src, helper_dst)
    print(f"Copied helper -> {helper_dst}", flush=True)
    print("Build OK. Dist layout:", flush=True)
    print(f"  {UI_DIR / f'{UI_NAME}.exe'}", flush=True)
    print(f"  {helper_dst}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
