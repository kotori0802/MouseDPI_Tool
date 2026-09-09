"""Contracts for Windows source-ZIP INSTALL / RUN scripts (no network install)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INSTALL = ROOT / "INSTALL_Mouse_DPI_Tool.cmd"
RUN = ROOT / "RUN_Mouse_DPI_Tool.cmd"
PYPROJECT = ROOT / "pyproject.toml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_install_and_run_scripts_exist():
    assert INSTALL.is_file()
    assert RUN.is_file()


def test_install_targets_ui_extra_not_dev():
    text = _read(INSTALL)
    assert 'pip install -e ".[ui]"' in text or "pip install -e \".[ui]\"" in text
    assert ".[dev]" not in text
    assert ".[dev,ui]" not in text
    assert "winget" not in text.lower()
    assert "curl " not in text.lower()
    assert "Invoke-WebRequest" not in text
    assert "Administrator" not in text or "does not" in text.lower()


def test_install_uses_repo_root_and_supported_python_range():
    text = _read(INSTALL)
    assert "%~dp0" in text
    assert "cd /d \"%~dp0\"" in text or "cd /d %~dp0" in text.replace('"', "")
    pyproject = _read(PYPROJECT)
    assert 'requires-python = ">=3.11,<3.14"' in pyproject
    assert "3.13" in text and "3.12" in text and "3.11" in text
    assert ">=3.11" in text or "^>=3.11" in text


def test_install_gates_existing_venv_python_version():
    """Static regression: existing .venv must be version-checked before reuse."""
    text = _read(INSTALL)
    assert "sys.version_info" in text
    assert "(3,11)" in text and "(3,14)" in text
    assert "Existing .venv uses an unsupported Python version" in text
    assert "Remove the existing .venv" in text
    # Must not auto-delete / recreate over an unsupported venv.
    assert "rmdir" not in text.lower()
    assert "/s /q" not in text.lower()


def test_install_creates_venv_and_verifies_without_capture():
    text = _read(INSTALL)
    assert "venv" in text
    assert "import mouse_dpi_tool" in text
    assert "PySide6" in text
    assert "mouse_dpi_tool version" in text or "-m mouse_dpi_tool version" in text
    assert "raw_input" not in text.lower()
    assert "CaptureEngine" not in text
    assert "Installation complete" in text
    # Success banner appears only after verification steps in script order.
    complete_at = text.index("Installation complete")
    assert text.index("pip install -e") < complete_at
    assert text.index("-m mouse_dpi_tool version") < complete_at


def test_run_prefers_venv_only_and_does_not_auto_install():
    text = _read(RUN)
    assert ".venv\\Scripts\\python.exe" in text or r".venv\Scripts\python.exe" in text
    assert "pip install" not in text.lower()
    assert "INSTALL_Mouse_DPI_Tool.cmd" in text
    assert "Mouse DPI Tool is not installed yet" in text
    # No system py/python discovery that shadows documented .venv workflow.
    assert "where py" not in text
    assert "where python" not in text


def test_run_uses_canonical_ui_entry():
    text = _read(RUN)
    assert "-m mouse_dpi_tool ui" in text
    assert "shared_runtime" not in text
    assert "C:\\Users\\" not in text
    assert "C:/Users/" not in text


def test_no_hardcoded_machine_paths_in_launchers():
    for path in (INSTALL, RUN):
        text = _read(path)
        assert "C:\\Users\\" not in text
        assert "C:/Users/" not in text
        assert "kotori" not in text.lower()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows CMD launcher behavior")
def test_run_cmd_fails_with_install_guidance_in_path_with_spaces(tmp_path: Path):
    """Behavioral: RUN with no .venv under a spaced path → non-zero + INSTALL hint."""
    dest = tmp_path / "Mouse DPI Tool"
    dest.mkdir()
    shutil.copy2(RUN, dest / "RUN_Mouse_DPI_Tool.cmd")
    # Feed newline so `pause` does not hang under redirected stdin.
    proc = subprocess.run(
        ["cmd.exe", "/c", str(dest / "RUN_Mouse_DPI_Tool.cmd")],
        input="\r\n",
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(tmp_path),
        env={**os.environ, "PROMPT": "$G"},
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode != 0
    assert "INSTALL_Mouse_DPI_Tool.cmd" in out
    assert "Mouse DPI Tool is not installed yet" in out
    assert "pip install" not in out.lower()
    assert "pip.exe" not in out.lower()
