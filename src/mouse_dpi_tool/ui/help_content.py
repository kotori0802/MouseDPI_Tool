"""Presentation-only help / interpretation content (never Session evidence)."""

from __future__ import annotations

from typing import Sequence

# Ordered User Guide sections — values are i18n keys for title + body.
USER_GUIDE_SECTIONS: tuple[tuple[str, str], ...] = (
    ("help.section.quick_start", "help.body.quick_start"),
    ("help.section.shortcuts", "help.body.shortcuts"),
    ("help.section.methods", "help.body.methods"),
    ("help.section.findings", "help.body.findings"),
    ("help.section.trends", "help.body.trends"),
    ("help.section.criterion", "help.body.criterion"),
    ("help.section.limits", "help.body.limits"),
    ("help.section.fixture_motion", "help.body.fixture_motion"),
)

# Chart “direction of goodness” cue keys (one line under title).
CHART_CUE_KEYS: dict[str, str] = {
    "measured_cpi": "charts.measured_cpi.cue",
    "max_error": "charts.max_error.cue",
    "repeatability": "charts.repeatability.cue",
}

# English cues for HTML/SVG (Qt uses i18n keys above).
CHART_CUES_EN: dict[str, str] = {
    "measured_cpi": (
        "Closer to the grey 1:1 ideal line means Effective CPI is nearer the configured value."
    ),
    "max_error": (
        "Lower is better; PASS / WARN / FAIL bands follow this Session's Accuracy thresholds."
    ),
    "repeatability": (
        "Lower CV means repeated measurements at the same DPI are more consistent."
    ),
}

FINDING_HELP_KEYS: dict[str, str] = {
    "accuracy": "finding.help.accuracy",
    "repeatability": "finding.help.repeatability",
    "ratio": "finding.help.ratio",
    "path_quality": "finding.help.path_quality",
}

RESEARCH_HELP_KEY = "finding.help.research"

REPORT_INTERPRETATION_TITLE_EN = "How to read this report"
REPORT_INTERPRETATION_BODY_EN = (
    "Accuracy: absolute Effective CPI vs configured DPI (maximum individual Trial error). "
    "Relative DPI Scaling: measured CPI step ratios vs configured step ratios "
    "(relative scaling — not absolute CPI closeness). "
    "Absolute CPI values may share a common offset while relative DPI-step ratios remain "
    "consistent; these describe different properties. "
    "Repeatability: consistency within a DPI group (lower CPI CV is better). "
    "Path Quality: no V1 reversal/jitter anomaly when PASS; incomplete-coverage WARN means "
    "missing evaluable path evidence on some Trials — not necessarily a path failure. "
    "Cross-DPI Scale Pattern: descriptive group-mean scale factors — not a Finding and not a root cause. "
    "Measured CPI chart: closer to 1:1 ideal is better "
    "(group-average deviation ≠ Accuracy maximum individual Trial error). "
    "Error chart: lower is better; PASS/WARN/FAIL use Session thresholds. "
    "CV chart: lower means better repeatability."
)

FINDING_HELP_EN: dict[str, str] = {
    "accuracy": "How close measured Effective CPI is to configured DPI.",
    "repeatability": "How consistent repeated measurements are within the same DPI group.",
    "ratio": (
        "Compares measured CPI ratios between DPI steps with their configured ratios. "
        "Useful for relative-scaling review; it does not prove sensor linearity or "
        "native capability."
    ),
    "path_quality": (
        "No path-quality issue defined by the current V1 reversal/jitter rules was detected when PASS. "
        "Does not mean perfect physical fixture straightness or zero lateral motion. "
        "WARN with incomplete coverage means one or more Trials lacked evaluable path evidence "
        "(e.g. NOT_EVALUATED) — not that a path failure was detected. "
        "Not Tracking / Sensor / Native capability."
    ),
}

RESEARCH_HELP_EN = (
    "Reserved for future characterization; V1 does not infer these properties from Raw Input alone."
)


def guide_section_keys() -> Sequence[tuple[str, str]]:
    return USER_GUIDE_SECTIONS
