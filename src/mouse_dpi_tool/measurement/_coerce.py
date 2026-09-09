from __future__ import annotations


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default
