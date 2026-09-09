"""Legacy field adapters for golden-fixture comparison only.

Canonical V1 evidence uses configured_dpi.
Legacy MouseDPI_v0.4.1 used target_dpi as the same numeric concept.

Compatibility boundary:
- Ingest: target_dpi is accepted as an alias for configured_dpi.
- Canonical measurement/session objects emit configured_dpi only.
- Golden parity tests project through as_legacy_* before comparing frozen fixtures.
- Session JSON writers must not emit target_dpi.
"""

from __future__ import annotations


def resolve_configured_dpi(*, configured_dpi=None, target_dpi=None) -> int:
    if configured_dpi is not None and target_dpi is not None and int(configured_dpi) != int(target_dpi):
        raise ValueError("configured_dpi and target_dpi disagree; they are not independent fields")
    value = configured_dpi if configured_dpi is not None else target_dpi
    if value is None:
        raise TypeError("configured_dpi is required (legacy alias: target_dpi)")
    return int(value)


def trial_configured_dpi(trial: dict) -> int:
    """Read configured DPI from a trial, accepting legacy ingest alias."""
    if trial.get("configured_dpi") is not None:
        return int(trial["configured_dpi"])
    if trial.get("target_dpi") is not None:
        return int(trial["target_dpi"])
    raise KeyError("trial is missing configured_dpi")


def group_configured_dpi(group: dict) -> int:
    if group.get("configured_dpi") is not None:
        return int(group["configured_dpi"])
    if group.get("target_dpi") is not None:
        return int(group["target_dpi"])
    raise KeyError("group is missing configured_dpi")


def as_legacy_trial(trial: dict) -> dict:
    """Project a canonical trial onto legacy golden-fixture field names."""
    row = dict(trial)
    row["target_dpi"] = trial_configured_dpi(trial)
    row.pop("configured_dpi", None)
    return row


def as_legacy_group(group: dict) -> dict:
    row = dict(group)
    row["target_dpi"] = group_configured_dpi(group)
    row.pop("configured_dpi", None)
    return row
