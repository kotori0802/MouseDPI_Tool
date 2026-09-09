"""Offset-aware evidence timestamps (ISO-8601 with UTC offset or Z)."""

from __future__ import annotations

from datetime import datetime


def now_iso() -> str:
    """Local time with UTC offset, e.g. 2026-09-03T10:30:00+08:00."""
    return datetime.now().astimezone().isoformat(timespec="seconds")
