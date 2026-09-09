"""Session layer — lifecycle store + Session JSON writer.

Owns: DUT metadata, trial lifecycle, rejected/deleted representation, run identity,
export-ready MOUSE_DPI_TOOL_SESSION_V1 evidence.

Does not: compute Path Quality, interpret Findings, or host Qt UI.
"""

from __future__ import annotations

from mouse_dpi_tool.session.capture_evidence import build_capture_evidence
from mouse_dpi_tool.session.model import (
    CaptureAdmissionError,
    Session,
    TrialLifecycleError,
    default_dut,
    default_measurement_context,
    new_session_id,
)
from mouse_dpi_tool.session.semantics import validate_session_semantics
from mouse_dpi_tool.session.writer import (
    SessionValidationError,
    load_session_json,
    validate_session,
    write_session_json,
)

TRIAL_LIFECYCLE_FLAGS = ("accepted", "rejected", "deleted")

__all__ = [
    "CaptureAdmissionError",
    "Session",
    "SessionValidationError",
    "TRIAL_LIFECYCLE_FLAGS",
    "TrialLifecycleError",
    "build_capture_evidence",
    "default_dut",
    "default_measurement_context",
    "load_session_json",
    "new_session_id",
    "validate_session",
    "validate_session_semantics",
    "write_session_json",
]
