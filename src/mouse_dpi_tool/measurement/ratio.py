"""DPI step ratio analysis (legacy build_ratio_analysis math parity).

from_dpi / to_dpi are configured-DPI step labels, not a separate target_dpi field.
"""

from __future__ import annotations

from mouse_dpi_tool.measurement.legacy_compat import group_configured_dpi
from mouse_dpi_tool.measurement.settings import status_from_limits


def build_ratio_analysis(group_summaries: list[dict], settings: dict) -> list[dict]:
    from mouse_dpi_tool.measurement.group import (
        FIXTURE_VECTOR_AXIS,
        FIXTURE_VECTOR_DIRECTION,
        is_fixture_vector_mode,
    )

    buckets: dict = {}
    for g in group_summaries:
        mode = g.get("movement_mode", "Vector Magnitude")
        if is_fixture_vector_mode(mode):
            key = (FIXTURE_VECTOR_AXIS, FIXTURE_VECTOR_DIRECTION, g["distance_mm"], mode)
        else:
            key = (g["axis"], g["direction"], g["distance_mm"], mode)
        buckets.setdefault(key, []).append(g)

    rows = []
    for key, items in buckets.items():
        items = sorted(items, key=group_configured_dpi)
        for a, b in zip(items, items[1:]):
            if not a.get("avg_measured_cpi") or not b.get("avg_measured_cpi"):
                continue

            from_dpi = group_configured_dpi(a)
            to_dpi = group_configured_dpi(b)
            expected_ratio = to_dpi / from_dpi
            measured_ratio = b["avg_measured_cpi"] / a["avg_measured_cpi"]
            ratio_error_pct = (measured_ratio - expected_ratio) / expected_ratio * 100.0
            status = status_from_limits(
                abs(ratio_error_pct),
                settings["ratio_error_pass_pct"],
                settings["ratio_error_fail_pct"],
            )

            rows.append(
                {
                    "axis": key[0],
                    "direction": key[1],
                    "distance_mm": key[2],
                    "movement_mode": key[3],
                    "from_dpi": from_dpi,
                    "to_dpi": to_dpi,
                    "expected_ratio": round(expected_ratio, 6),
                    "measured_ratio": round(measured_ratio, 6),
                    "ratio_error_pct": round(ratio_error_pct, 4),
                    "status": status,
                    "issue_tags": "" if status == "PASS" else f"DPI_RATIO_{status}",
                }
            )
    return rows
