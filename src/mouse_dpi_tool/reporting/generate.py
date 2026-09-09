"""Generate Report — HTML + canonical Session JSON (atomic, Session-immutable)."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from mouse_dpi_tool.reporting.html_report import render_html_report
from mouse_dpi_tool.session.writer import validate_session, write_session_json


def _sanitize(run_id: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", str(run_id or "run").strip())
    return text[:80] or "run"


@dataclass(frozen=True)
class ReportArtifacts:
    html_path: Path
    json_path: Path
    session_id: str
    run_id: str


def report_run_id(session: Mapping[str, Any], *, when: datetime | None = None) -> str:
    stamp = (when or datetime.now(timezone.utc)).strftime("%Y%m%d_%H%M%S")
    sid = _sanitize(str(session.get("session_id") or "session"))
    return f"{sid}_{stamp}"


def html_report_filename(run_id: str) -> str:
    return f"Mouse_DPI_Report_{_sanitize(run_id)}.html"


def session_sidecar_filename(run_id: str) -> str:
    return f"Mouse_DPI_Session_{_sanitize(run_id)}.json"


def _atomic_write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise
    return path


def generate_report_bundle(
    session: Mapping[str, Any],
    dest_dir: str | Path,
    *,
    run_id: str | None = None,
    generated_at: str | None = None,
) -> ReportArtifacts:
    """Validate Session → write HTML + JSON sidecar. Does not mutate Session evidence."""
    payload = validate_session(session)
    rid = run_id or report_run_id(payload)
    out = Path(dest_dir)
    out.mkdir(parents=True, exist_ok=True)
    html_path = out / html_report_filename(rid)
    json_path = out / session_sidecar_filename(rid)

    html = render_html_report(payload, generated_at=generated_at)
    # Write HTML first to temp semantics; if JSON fails, remove HTML to avoid half bundle.
    try:
        _atomic_write_text(html_path, html)
        write_session_json(payload, json_path)
    except Exception:
        for p in (html_path, json_path):
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass
        raise

    return ReportArtifacts(
        html_path=html_path,
        json_path=json_path,
        session_id=str(payload.get("session_id") or ""),
        run_id=rid,
    )
