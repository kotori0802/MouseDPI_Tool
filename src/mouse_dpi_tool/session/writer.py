"""Session JSON writer — schema + semantic validation + atomic replace."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from mouse_dpi_tool.resources import session_schema
from mouse_dpi_tool.session.semantics import validate_session_semantics


class SessionValidationError(ValueError):
    """Raised when a session object fails schema or semantic validation before write."""


def _contains_forbidden_key(obj: Any, key: str) -> bool:
    if isinstance(obj, dict):
        if key in obj:
            return True
        return any(_contains_forbidden_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(_contains_forbidden_key(v, key) for v in obj)
    return False


def validate_session(session: Mapping[str, Any]) -> dict[str, Any]:
    """Structural JSON Schema validation, then semantic evidence invariants."""
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("jsonschema is required to validate/export Session JSON") from exc

    payload = json.loads(json.dumps(session))  # normalize to JSON types
    schema = session_schema()
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    if errors:
        messages = []
        for err in errors[:8]:
            path = ".".join(str(p) for p in err.absolute_path) or "<root>"
            messages.append(f"{path}: {err.message}")
        raise SessionValidationError(
            "Session JSON failed schema validation:\n- " + "\n- ".join(messages)
        )
    if _contains_forbidden_key(payload, "target_dpi"):
        raise SessionValidationError("exported Session JSON must not contain target_dpi")

    semantic_errors = validate_session_semantics(payload)
    if semantic_errors:
        raise SessionValidationError(
            "Session JSON failed semantic validation:\n- " + "\n- ".join(semantic_errors[:12])
        )
    return payload


def write_session_json(session: Mapping[str, Any], path: str | os.PathLike[str]) -> Path:
    """Validate then atomically write Session JSON (temp file + os.replace)."""
    payload = validate_session(session)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, target)
    except Exception:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise
    return target


def load_session_json(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Load a Session JSON file and validate it (no legacy/Hub runtime required)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_session(data)
