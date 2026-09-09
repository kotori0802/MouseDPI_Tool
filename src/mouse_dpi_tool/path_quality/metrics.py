"""Pure Path Quality metrics (legacy ui_tk path evidence, without UI/CPI merge).

Legacy source of truth (MouseDPI_v0.4.1 ui_tk.py):
- path_total_counts += hypot(dx, dy) only when hypot > fixture_noise_floor
- noise floor is never subtracted from net dx/dy / CPI
- straightness_pct = min(100, vector_counts / path_total_counts * 100) if path_total > 0 else 0
- reversal/jitter if vector > 0 and path_total > max(vector*1.25, vector+max(20, noise*3))
  and straightness < straightness_fail_pct

Intentional V1 divergence: classification does not rewrite measurement/CPI status.
"""

from __future__ import annotations

import math
from typing import Any


def step_hypot(dx: int, dy: int) -> float:
    return math.hypot(int(dx), int(dy))


def vector_counts_from_net(net_x: int, net_y: int) -> int:
    return int(round(math.hypot(int(net_x), int(net_y))))


def straightness_pct(vector_counts: int | float, path_total_counts: float) -> float:
    if path_total_counts <= 0:
        return 0.0
    return min(100.0, float(vector_counts) / float(path_total_counts) * 100.0)


def clamp_noise_floor(value: Any, default: int = 7) -> int:
    try:
        return max(0, min(25, int(float(value))))
    except (TypeError, ValueError):
        return default


def reversal_threshold(vector_counts: float, noise_floor: float) -> float:
    return max(vector_counts * 1.25, vector_counts + max(20.0, noise_floor * 3.0))


def classify_path_quality(
    *,
    vector_counts: int,
    path_total_counts: float,
    straightness: float,
    noise_floor: float,
    straightness_fail_pct: float,
    sample_count: int,
) -> tuple[str, list[str]]:
    """Return (status, issue_codes). Never uses CPI error.

    V1 semantic note: net movement with no steps above the noise floor yields
    NOT_EVALUATED + NO_PATH_EVIDENCE_ABOVE_NOISE_FLOOR (legacy add_current_trial
    rejected path_total<=0; CPI/net counts remain untouched here).
    """
    if sample_count <= 0:
        return "NOT_TESTED", []

    codes: list[str] = []
    if vector_counts <= 0:
        codes.append("NO_MOVEMENT")
        return "FAIL", codes

    if path_total_counts <= 0:
        codes.append("NO_PATH_EVIDENCE_ABOVE_NOISE_FLOOR")
        return "NOT_EVALUATED", codes

    if (
        path_total_counts > reversal_threshold(vector_counts, noise_floor)
        and straightness < straightness_fail_pct
    ):
        codes.append("PATH_REVERSAL_OR_JITTER_FAIL")
        return "FAIL", codes

    return "PASS", codes
